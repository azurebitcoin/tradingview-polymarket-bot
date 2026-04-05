"""Polymarket integration wrapper with dry-run support."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import requests

from bot.config import Settings
from bot.core.exceptions import ConfigurationError
from bot.core.progression import price as round_price
from bot.core.progression import size as round_size


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class MarketContext:
    """Metadata required to place a Polymarket order."""

    tick_size: str
    neg_risk: bool


@dataclass(frozen=True)
class OrderReceipt:
    """Normalized order execution response."""

    order_id: str
    status: str
    submitted_price: Decimal
    submitted_size: Decimal
    raw_response: dict[str, Any]


class PolymarketClient:
    """A thin wrapper over the official Polymarket SDK and public APIs."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._sdk_client = None

    def get_best_price(self, token_id: str, side: str) -> Decimal:
        """Fetch the best current buy or sell price for a token."""

        if self.settings.dry_run:
            return self._fake_price(token_id, side)

        response = requests.get(
            f"{self.settings.polymarket_host}/price",
            params={"token_id": token_id, "side": side},
            timeout=3,
        )
        response.raise_for_status()
        payload = response.json()
        value = payload["price"] if isinstance(payload, dict) and "price" in payload else payload
        return round_price(Decimal(str(value)))

    def get_market_context(self, condition_id: str | None) -> MarketContext:
        """Fetch tick size and neg-risk metadata required for order submission."""

        if self.settings.dry_run or not condition_id:
            return MarketContext(tick_size="0.01", neg_risk=False)

        client = self._get_sdk_client()
        market = client.get_market(condition_id)
        return MarketContext(
            tick_size=str(market["minimum_tick_size"]),
            neg_risk=bool(market["neg_risk"]),
        )

    def buy_token(
        self,
        *,
        token_id: str,
        condition_id: str | None,
        price: Decimal,
        stake_amount: Decimal,
    ) -> OrderReceipt:
        """Submit a fast marketable limit buy."""

        submitted_size = round_size(stake_amount / price)
        return self._submit_order(
            token_id=token_id,
            condition_id=condition_id,
            price=price,
            size=submitted_size,
            side="BUY",
        )

    def sell_token(
        self,
        *,
        token_id: str,
        condition_id: str | None,
        price: Decimal,
        token_size: Decimal,
    ) -> OrderReceipt:
        """Submit a fast marketable limit sell."""

        return self._submit_order(
            token_id=token_id,
            condition_id=condition_id,
            price=price,
            size=round_size(token_size),
            side="SELL",
        )

    def _submit_order(
        self,
        *,
        token_id: str,
        condition_id: str | None,
        price: Decimal,
        size: Decimal,
        side: str,
    ) -> OrderReceipt:
        """Submit a live or dry-run order and normalize the result."""

        if self.settings.dry_run:
            order_id = hashlib.sha1(f"{token_id}:{side}:{price}:{size}".encode()).hexdigest()[:12]
            raw_response = {
                "mode": "dry-run",
                "token_id": token_id,
                "side": side,
                "price": float(price),
                "size": float(size),
            }
            return OrderReceipt(
                order_id=order_id,
                status="SIMULATED_FILLED",
                submitted_price=price,
                submitted_size=size,
                raw_response=raw_response,
            )

        if not condition_id:
            raise ConfigurationError("Live orders require condition_id to fetch market metadata.")

        client = self._get_sdk_client()
        market_context = self.get_market_context(condition_id)

        from py_clob_client.clob_types import OrderArgs, OrderType
        from py_clob_client.order_builder.constants import BUY, SELL

        order_side = BUY if side == "BUY" else SELL
        response = client.create_and_post_order(
            OrderArgs(
                token_id=token_id,
                price=float(price),
                size=float(size),
                side=order_side,
                order_type=OrderType.FAK,
            ),
            options={
                "tick_size": market_context.tick_size,
                "neg_risk": market_context.neg_risk,
            },
        )
        return OrderReceipt(
            order_id=str(response.get("orderID", "")),
            status=str(response.get("status", "UNKNOWN")),
            submitted_price=price,
            submitted_size=size,
            raw_response=response,
        )

    def _get_sdk_client(self) -> Any:
        """Initialize the official Python client lazily."""

        if self._sdk_client is not None:
            return self._sdk_client

        if not self.settings.polymarket_private_key or not self.settings.polymarket_funder:
            raise ConfigurationError("Missing live Polymarket credentials.")

        try:
            from py_clob_client.client import ClobClient
        except ImportError as exc:
            raise ConfigurationError(
                "py-clob-client is not installed. Install requirements before live trading."
            ) from exc

        LOGGER.info("Initializing authenticated Polymarket client")
        temp_client = ClobClient(
            self.settings.polymarket_host,
            key=self.settings.polymarket_private_key,
            chain_id=self.settings.polymarket_chain_id,
        )
        api_creds = temp_client.create_or_derive_api_creds()
        self._sdk_client = ClobClient(
            self.settings.polymarket_host,
            key=self.settings.polymarket_private_key,
            chain_id=self.settings.polymarket_chain_id,
            creds=api_creds,
            signature_type=self.settings.polymarket_signature_type,
            funder=self.settings.polymarket_funder,
        )
        return self._sdk_client

    @staticmethod
    def _fake_price(token_id: str, side: str) -> Decimal:
        """Produce deterministic prices for dry-run mode without network access."""

        digest = hashlib.sha256(f"{token_id}:{side}".encode()).digest()
        base = Decimal("0.25") + (Decimal(digest[0]) / Decimal("255")) * Decimal("0.45")
        if side == "SELL":
            base -= Decimal("0.02")
        return round_price(max(Decimal("0.01"), min(base, Decimal("0.99"))))
