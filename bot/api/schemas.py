"""Pydantic schemas for webhook and status responses."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TradingViewAlert(BaseModel):
    """TradingView webhook body expected by this application."""

    action: Literal["ENTER", "EXIT"]
    token_id: str = Field(..., min_length=1)
    condition_id: str | None = None
    market_slug: str | None = None
    outcome: str | None = None
    alert_id: str | None = None
    tv_symbol: str | None = None
    max_price: float | None = Field(default=None, ge=0.01, le=0.99)
    min_price: float | None = Field(default=None, ge=0.01, le=0.99)
    note: str | None = None
    timestamp: datetime | None = None

    @field_validator("token_id", "condition_id", "market_slug", "outcome", "alert_id", "tv_symbol")
    @classmethod
    def strip_strings(cls, value: str | None) -> str | None:
        """Normalize optional string fields."""

        if value is None:
            return value
        stripped = value.strip()
        return stripped or None


class TradeResponse(BaseModel):
    """Compact response returned after processing a webhook."""

    ok: bool
    message: str
    trade_id: int | None = None
    current_step: int
    estimated_balance: float
    dry_run: bool


class StatusResponse(BaseModel):
    """Application status payload."""

    ok: bool
    dry_run: bool
    current_step: int
    estimated_balance: float
    active_trade_id: int | None
    last_outcome: str | None
