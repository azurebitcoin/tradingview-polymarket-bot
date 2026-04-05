"""Environment-backed configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    app_name: str
    host: str
    port: int
    webhook_secret: str
    dry_run: bool
    database_path: Path | str
    log_file_path: Path | None
    initial_balance: float
    base_trade_amount: float
    progression_multiplier: float
    max_steps: int
    max_slippage: float
    polymarket_host: str
    polymarket_chain_id: int
    polymarket_signature_type: int
    polymarket_private_key: str
    polymarket_funder: str


def get_settings() -> Settings:
    """Build a Settings object and validate required fields."""

    dry_run = os.getenv("DRY_RUN", "true").strip().lower() in {"1", "true", "yes", "on"}
    webhook_secret = os.getenv("WEBHOOK_SECRET", "").strip()
    if not webhook_secret:
        raise ValueError("Missing WEBHOOK_SECRET in the environment.")

    private_key = os.getenv("POLYMARKET_PRIVATE_KEY", "").strip()
    funder = os.getenv("POLYMARKET_FUNDER", "").strip()
    if not dry_run and (not private_key or not funder):
        raise ValueError(
            "Live trading requires POLYMARKET_PRIVATE_KEY and POLYMARKET_FUNDER."
        )

    raw_database_path = os.getenv("DATABASE_PATH", "bot_state.db").strip() or "bot_state.db"
    database_path: Path | str = (
        raw_database_path if raw_database_path == ":memory:" else PROJECT_ROOT / raw_database_path
    )
    raw_log_file_path = os.getenv("LOG_FILE_PATH", "logs/bot.log").strip()
    log_file_path = PROJECT_ROOT / raw_log_file_path if raw_log_file_path else None

    return Settings(
        app_name=os.getenv("APP_NAME", "tv-polymarket-bot").strip() or "tv-polymarket-bot",
        host=os.getenv("APP_HOST", "0.0.0.0").strip() or "0.0.0.0",
        port=int(os.getenv("APP_PORT", "8000")),
        webhook_secret=webhook_secret,
        dry_run=dry_run,
        database_path=database_path,
        log_file_path=log_file_path,
        initial_balance=float(os.getenv("INITIAL_BALANCE", "1000")),
        base_trade_amount=float(os.getenv("BASE_TRADE_AMOUNT", "50")),
        progression_multiplier=float(os.getenv("PROGRESSION_MULTIPLIER", "3")),
        max_steps=int(os.getenv("MAX_STEPS", "4")),
        max_slippage=float(os.getenv("MAX_SLIPPAGE", "0.02")),
        polymarket_host=os.getenv("POLYMARKET_HOST", "https://clob.polymarket.com").strip(),
        polymarket_chain_id=int(os.getenv("POLYMARKET_CHAIN_ID", "137")),
        polymarket_signature_type=int(os.getenv("POLYMARKET_SIGNATURE_TYPE", "0")),
        polymarket_private_key=private_key,
        polymarket_funder=funder,
    )
