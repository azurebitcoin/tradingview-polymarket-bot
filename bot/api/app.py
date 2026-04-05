"""FastAPI application factory."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException

from bot.api.schemas import StatusResponse, TradeResponse, TradingViewAlert
from bot.config import Settings
from bot.core.exceptions import BotError
from bot.services.trading_engine import TradingEngine
from bot.storage.repository import StateRepository


LOGGER = logging.getLogger(__name__)


def create_app(
    settings: Settings,
    repository: StateRepository,
    trading_engine: TradingEngine,
) -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(title=settings.app_name)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Simple liveness probe."""

        return {"status": "ok"}

    @app.get("/status", response_model=StatusResponse)
    def status() -> StatusResponse:
        """Expose the progression state and whether a trade is active."""

        state = repository.get_state()
        return StatusResponse(
            ok=True,
            dry_run=settings.dry_run,
            current_step=state.current_step,
            estimated_balance=state.estimated_balance,
            active_trade_id=state.active_trade_id,
            last_outcome=state.last_outcome,
        )

    @app.post("/webhooks/tradingview/{secret}", response_model=TradeResponse)
    def tradingview_webhook(secret: str, payload: TradingViewAlert) -> TradeResponse:
        """Receive TradingView alerts and route them to the trading engine."""

        if secret != settings.webhook_secret:
            raise HTTPException(status_code=401, detail="Invalid webhook secret.")

        try:
            return trading_engine.process_alert(payload)
        except BotError as exc:
            LOGGER.warning("Rejected alert: %s", exc)
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception as exc:
            LOGGER.exception("Unhandled error while processing TradingView alert")
            raise HTTPException(status_code=500, detail="Internal bot error.") from exc

    @app.post("/webhooks/tradingview/{secret}/close-loss", response_model=TradeResponse)
    def close_loss(secret: str) -> TradeResponse:
        """Force-close the active trade as a loss for dry-run testing."""

        if secret != settings.webhook_secret:
            raise HTTPException(status_code=401, detail="Invalid webhook secret.")

        try:
            return trading_engine.force_close_active_trade_for_test("LOSS")
        except BotError as exc:
            LOGGER.warning("Rejected forced loss close: %s", exc)
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception as exc:
            LOGGER.exception("Unhandled error while forcing a loss close")
            raise HTTPException(status_code=500, detail="Internal bot error.") from exc

    @app.post("/webhooks/tradingview/{secret}/close-win", response_model=TradeResponse)
    def close_win(secret: str) -> TradeResponse:
        """Force-close the active trade as a win for dry-run testing."""

        if secret != settings.webhook_secret:
            raise HTTPException(status_code=401, detail="Invalid webhook secret.")

        try:
            return trading_engine.force_close_active_trade_for_test("WIN")
        except BotError as exc:
            LOGGER.warning("Rejected forced win close: %s", exc)
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception as exc:
            LOGGER.exception("Unhandled error while forcing a win close")
            raise HTTPException(status_code=500, detail="Internal bot error.") from exc

    return app
