"""SQLite bootstrap and connection helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS bot_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    current_step INTEGER NOT NULL,
    estimated_balance REAL NOT NULL,
    max_steps INTEGER NOT NULL,
    base_trade_amount REAL NOT NULL,
    progression_multiplier REAL NOT NULL,
    active_trade_id INTEGER NULL,
    last_outcome TEXT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NULL,
    market_slug TEXT NULL,
    tv_symbol TEXT NULL,
    token_id TEXT NOT NULL,
    condition_id TEXT NULL,
    outcome TEXT NULL,
    status TEXT NOT NULL,
    step_index INTEGER NOT NULL,
    requested_amount REAL NOT NULL,
    entry_price REAL NOT NULL,
    entry_size REAL NOT NULL,
    entry_order_id TEXT NULL,
    entry_status TEXT NULL,
    exit_price REAL NULL,
    exit_size REAL NULL,
    exit_order_id TEXT NULL,
    exit_status TEXT NULL,
    realized_pnl REAL NULL,
    result TEXT NULL,
    note TEXT NULL,
    created_at TEXT NOT NULL,
    opened_at TEXT NOT NULL,
    closed_at TEXT NULL,
    raw_entry_response TEXT NOT NULL,
    raw_exit_response TEXT NULL
);
"""


def create_connection(database_path: Path | str) -> sqlite3.Connection:
    """Create a SQLite connection configured for row access."""

    if database_path != ":memory:":
        assert isinstance(database_path, Path)
        database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    """Create tables if they do not yet exist."""

    connection.executescript(SCHEMA_SQL)
    connection.commit()
