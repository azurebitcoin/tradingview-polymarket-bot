"""Persistence helpers for bot state and trade history."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from bot.config import Settings


def utcnow() -> str:
    """Return an ISO-8601 timestamp in UTC."""

    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class BotState:
    """Current progression and balance state."""

    current_step: int
    estimated_balance: float
    max_steps: int
    base_trade_amount: float
    progression_multiplier: float
    active_trade_id: int | None
    last_outcome: str | None


@dataclass(frozen=True)
class TradeRecord:
    """Persisted trade row used by the strategy engine."""

    id: int
    token_id: str
    condition_id: str | None
    market_slug: str | None
    outcome: str | None
    status: str
    step_index: int
    requested_amount: float
    entry_price: float
    entry_size: float
    realized_pnl: float | None


class StateRepository:
    """Repository around the bot_state and trades tables."""

    def __init__(self, connection: sqlite3.Connection, settings: Settings) -> None:
        self.connection = connection
        self.settings = settings
        self.ensure_state_row()

    def ensure_state_row(self) -> None:
        """Insert the singleton bot state row on first boot."""

        row = self.connection.execute("SELECT id FROM bot_state WHERE id = 1").fetchone()
        if row:
            return

        self.connection.execute(
            """
            INSERT INTO bot_state (
                id, current_step, estimated_balance, max_steps,
                base_trade_amount, progression_multiplier, active_trade_id,
                last_outcome, updated_at
            ) VALUES (1, ?, ?, ?, ?, ?, NULL, NULL, ?)
            """,
            (
                0,
                self.settings.initial_balance,
                self.settings.max_steps,
                self.settings.base_trade_amount,
                self.settings.progression_multiplier,
                utcnow(),
            ),
        )
        self.connection.commit()

    def get_state(self) -> BotState:
        """Fetch the singleton bot state."""

        row = self.connection.execute("SELECT * FROM bot_state WHERE id = 1").fetchone()
        return BotState(
            current_step=row["current_step"],
            estimated_balance=row["estimated_balance"],
            max_steps=row["max_steps"],
            base_trade_amount=row["base_trade_amount"],
            progression_multiplier=row["progression_multiplier"],
            active_trade_id=row["active_trade_id"],
            last_outcome=row["last_outcome"],
        )

    def get_active_trade(self) -> TradeRecord | None:
        """Return the currently open trade, if any."""

        row = self.connection.execute(
            """
            SELECT t.*
            FROM trades t
            JOIN bot_state s ON s.active_trade_id = t.id
            WHERE s.id = 1 AND t.status = 'OPEN'
            """
        ).fetchone()
        if row is None:
            return None
        return self._row_to_trade(row)

    def create_open_trade(
        self,
        *,
        alert_id: str | None,
        market_slug: str | None,
        tv_symbol: str | None,
        token_id: str,
        condition_id: str | None,
        outcome: str | None,
        step_index: int,
        requested_amount: Decimal,
        entry_price: Decimal,
        entry_size: Decimal,
        entry_order_id: str | None,
        entry_status: str | None,
        note: str | None,
        raw_entry_response: dict,
    ) -> int:
        """Insert a new open trade and mark it as active."""

        now = utcnow()
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO trades (
                alert_id, market_slug, tv_symbol, token_id, condition_id, outcome,
                status, step_index, requested_amount, entry_price, entry_size,
                entry_order_id, entry_status, note, created_at, opened_at,
                raw_entry_response
            ) VALUES (?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert_id,
                market_slug,
                tv_symbol,
                token_id,
                condition_id,
                outcome,
                step_index,
                float(requested_amount),
                float(entry_price),
                float(entry_size),
                entry_order_id,
                entry_status,
                note,
                now,
                now,
                json.dumps(raw_entry_response, ensure_ascii=True),
            ),
        )
        trade_id = int(cursor.lastrowid)
        cursor.execute(
            """
            UPDATE bot_state
            SET active_trade_id = ?, updated_at = ?
            WHERE id = 1
            """,
            (trade_id, now),
        )
        self.connection.commit()
        return trade_id

    def close_active_trade(
        self,
        *,
        trade_id: int,
        exit_price: Decimal,
        exit_size: Decimal,
        exit_order_id: str | None,
        exit_status: str | None,
        realized_pnl: Decimal,
        result: str,
        next_step: int,
        new_balance: Decimal,
        raw_exit_response: dict,
        note: str | None,
    ) -> None:
        """Mark the active trade as closed and advance the progression."""

        now = utcnow()
        self.connection.execute(
            """
            UPDATE trades
            SET status = 'CLOSED',
                exit_price = ?,
                exit_size = ?,
                exit_order_id = ?,
                exit_status = ?,
                realized_pnl = ?,
                result = ?,
                note = COALESCE(?, note),
                closed_at = ?,
                raw_exit_response = ?
            WHERE id = ?
            """,
            (
                float(exit_price),
                float(exit_size),
                exit_order_id,
                exit_status,
                float(realized_pnl),
                result,
                note,
                now,
                json.dumps(raw_exit_response, ensure_ascii=True),
                trade_id,
            ),
        )
        self.connection.execute(
            """
            UPDATE bot_state
            SET current_step = ?,
                estimated_balance = ?,
                active_trade_id = NULL,
                last_outcome = ?,
                updated_at = ?
            WHERE id = 1
            """,
            (next_step, float(new_balance), result, now),
        )
        self.connection.commit()

    @staticmethod
    def _row_to_trade(row: sqlite3.Row) -> TradeRecord:
        """Convert a sqlite row to a strongly-typed TradeRecord."""

        return TradeRecord(
            id=row["id"],
            token_id=row["token_id"],
            condition_id=row["condition_id"],
            market_slug=row["market_slug"],
            outcome=row["outcome"],
            status=row["status"],
            step_index=row["step_index"],
            requested_amount=row["requested_amount"],
            entry_price=row["entry_price"],
            entry_size=row["entry_size"],
            realized_pnl=row["realized_pnl"],
        )
