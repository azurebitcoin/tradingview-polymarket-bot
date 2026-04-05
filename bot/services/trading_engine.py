"""Trading orchestration for TradingView alerts and Polymarket execution."""

from __future__ import annotations

import logging
import threading
from decimal import Decimal

from bot.api.schemas import TradeResponse, TradingViewAlert
from bot.config import Settings
from bot.core.exceptions import BusyTradeError, InvalidAlertError, NoActiveTradeError
from bot.core.progression import money, next_step_after_result, price, progression_amount
from bot.integrations.polymarket_client import PolymarketClient
from bot.storage.repository import StateRepository


LOGGER = logging.getLogger(__name__)


class TradingEngine:
    """Coordinates progression state, order execution, and persistence."""

    def __init__(
        self,
        settings: Settings,
        repository: StateRepository,
        polymarket_client: PolymarketClient,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.polymarket_client = polymarket_client
        self._lock = threading.Lock()

    def process_alert(self, alert: TradingViewAlert) -> TradeResponse:
        """Process one webhook payload under a global lock."""

        with self._lock:
            if alert.action == "ENTER":
                return self._handle_entry(alert)
            return self._handle_exit(alert)

    def force_close_active_trade_for_test(self, force_result: str) -> TradeResponse:
        """Close the active trade with a synthetic result in dry-run mode."""

        if not self.settings.dry_run:
            raise InvalidAlertError("Forced close helpers are available only in dry_run mode.")

        if force_result not in {"WIN", "LOSS"}:
            raise InvalidAlertError("force_result must be WIN or LOSS.")

        with self._lock:
            state = self.repository.get_state()
            active_trade = self.repository.get_active_trade()
            if active_trade is None:
                raise NoActiveTradeError("No active trade is open. Forced close skipped.")

            entry_price = Decimal(str(active_trade.entry_price))
            entry_size = Decimal(str(active_trade.entry_size))
            if force_result == "WIN":
                exit_price_value = min(Decimal("0.99"), entry_price * Decimal("1.10"))
            else:
                exit_price_value = max(Decimal("0.01"), entry_price * Decimal("0.80"))

            exit_price = price(exit_price_value)
            exit_size = entry_size
            realized_pnl = money((exit_price * exit_size) - (entry_price * entry_size))
            won = force_result == "WIN"
            next_step, exhausted = next_step_after_result(
                active_trade.step_index,
                state.max_steps,
                won=won,
            )
            new_balance = money(Decimal(str(state.estimated_balance)) + realized_pnl)

            note = f"Forced {force_result.lower()} close for dry-run testing."
            if exhausted:
                note += " Progression exhausted: resetting to base step."

            raw_exit_response = {
                "mode": "dry-run-forced",
                "result": force_result,
                "token_id": active_trade.token_id,
                "price": float(exit_price),
                "size": float(exit_size),
            }

            self.repository.close_active_trade(
                trade_id=active_trade.id,
                exit_price=exit_price,
                exit_size=exit_size,
                exit_order_id=f"forced-{force_result.lower()}-{active_trade.id}",
                exit_status="SIMULATED_FILLED",
                realized_pnl=realized_pnl,
                result=force_result,
                next_step=next_step,
                new_balance=new_balance,
                raw_exit_response=raw_exit_response,
                note=note,
            )

            LOGGER.info(
                "Forced close trade %s | result=%s | pnl=%s | next_step=%s | balance=%s",
                active_trade.id,
                force_result,
                realized_pnl,
                next_step,
                new_balance,
            )

            refreshed_state = self.repository.get_state()
            return TradeResponse(
                ok=True,
                message=f"Forced {force_result.lower()} close processed successfully.",
                trade_id=active_trade.id,
                current_step=refreshed_state.current_step,
                estimated_balance=refreshed_state.estimated_balance,
                dry_run=self.settings.dry_run,
            )

    def _handle_entry(self, alert: TradingViewAlert) -> TradeResponse:
        """Enter one new trade if the bot is currently flat."""

        state = self.repository.get_state()
        if state.active_trade_id is not None:
            raise BusyTradeError("An active trade is already open. Entry skipped.")

        trade_amount = progression_amount(
            state.base_trade_amount,
            state.progression_multiplier,
            state.current_step,
        )
        if trade_amount > Decimal(str(state.estimated_balance)):
            raise InvalidAlertError("Estimated balance is below the required progression amount.")

        best_buy = self.polymarket_client.get_best_price(alert.token_id, "BUY")
        execution_price = self._resolve_entry_price(best_buy, alert.max_price)

        receipt = self.polymarket_client.buy_token(
            token_id=alert.token_id,
            condition_id=alert.condition_id,
            price=execution_price,
            stake_amount=trade_amount,
        )

        trade_id = self.repository.create_open_trade(
            alert_id=alert.alert_id,
            market_slug=alert.market_slug,
            tv_symbol=alert.tv_symbol,
            token_id=alert.token_id,
            condition_id=alert.condition_id,
            outcome=alert.outcome,
            step_index=state.current_step,
            requested_amount=trade_amount,
            entry_price=receipt.submitted_price,
            entry_size=receipt.submitted_size,
            entry_order_id=receipt.order_id,
            entry_status=receipt.status,
            note=alert.note,
            raw_entry_response=receipt.raw_response,
        )

        LOGGER.info(
            "Opened trade %s | step=%s | amount=%s | token=%s | price=%s | dry_run=%s",
            trade_id,
            state.current_step,
            trade_amount,
            alert.token_id,
            execution_price,
            self.settings.dry_run,
        )

        refreshed_state = self.repository.get_state()
        return TradeResponse(
            ok=True,
            message="Entry processed successfully.",
            trade_id=trade_id,
            current_step=refreshed_state.current_step,
            estimated_balance=refreshed_state.estimated_balance,
            dry_run=self.settings.dry_run,
        )

    def _handle_exit(self, alert: TradingViewAlert) -> TradeResponse:
        """Exit the active trade and advance the progression state."""

        state = self.repository.get_state()
        active_trade = self.repository.get_active_trade()
        if active_trade is None:
            raise NoActiveTradeError("No active trade is open. Exit skipped.")

        if active_trade.token_id != alert.token_id:
            raise InvalidAlertError(
                f"Exit token_id {alert.token_id} does not match active trade {active_trade.token_id}."
            )

        best_sell = self.polymarket_client.get_best_price(alert.token_id, "SELL")
        execution_price = self._resolve_exit_price(best_sell, alert.min_price)

        receipt = self.polymarket_client.sell_token(
            token_id=active_trade.token_id,
            condition_id=active_trade.condition_id,
            price=execution_price,
            token_size=Decimal(str(active_trade.entry_size)),
        )

        entry_notional = Decimal(str(active_trade.entry_price)) * Decimal(str(active_trade.entry_size))
        exit_notional = receipt.submitted_price * receipt.submitted_size
        realized_pnl = money(exit_notional - entry_notional)
        won = realized_pnl > Decimal("0")
        result = "WIN" if won else "LOSS"

        next_step, exhausted = next_step_after_result(
            active_trade.step_index,
            state.max_steps,
            won=won,
        )
        new_balance = money(Decimal(str(state.estimated_balance)) + realized_pnl)

        note = alert.note
        if exhausted:
            note = ((note + " | ") if note else "") + "Progression exhausted: resetting to base step."

        self.repository.close_active_trade(
            trade_id=active_trade.id,
            exit_price=receipt.submitted_price,
            exit_size=receipt.submitted_size,
            exit_order_id=receipt.order_id,
            exit_status=receipt.status,
            realized_pnl=realized_pnl,
            result=result,
            next_step=next_step,
            new_balance=new_balance,
            raw_exit_response=receipt.raw_response,
            note=note,
        )

        LOGGER.info(
            "Closed trade %s | result=%s | pnl=%s | next_step=%s | balance=%s",
            active_trade.id,
            result,
            realized_pnl,
            next_step,
            new_balance,
        )

        refreshed_state = self.repository.get_state()
        return TradeResponse(
            ok=True,
            message="Exit processed successfully.",
            trade_id=active_trade.id,
            current_step=refreshed_state.current_step,
            estimated_balance=refreshed_state.estimated_balance,
            dry_run=self.settings.dry_run,
        )

    def _resolve_entry_price(self, best_buy: Decimal, max_price_from_alert: float | None) -> Decimal:
        """Convert the best buy price into a marketable limit buy."""

        ceiling = Decimal(str(max_price_from_alert)) if max_price_from_alert is not None else Decimal("0.99")
        candidate = best_buy + Decimal(str(self.settings.max_slippage))
        return price(min(candidate, ceiling))

    def _resolve_exit_price(self, best_sell: Decimal, min_price_from_alert: float | None) -> Decimal:
        """Convert the best sell price into a marketable limit sell."""

        floor = Decimal(str(min_price_from_alert)) if min_price_from_alert is not None else Decimal("0.01")
        candidate = best_sell - Decimal(str(self.settings.max_slippage))
        return price(max(candidate, floor))
