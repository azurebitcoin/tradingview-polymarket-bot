"""Application entry point."""

from __future__ import annotations

import uvicorn

from bot.api.app import create_app
from bot.config import get_settings
from bot.integrations.polymarket_client import PolymarketClient
from bot.logging_config import configure_logging
from bot.services.trading_engine import TradingEngine
from bot.storage.database import create_connection, initialize_database
from bot.storage.repository import StateRepository


def build_app():
    """Create the FastAPI application with all dependencies wired up."""

    settings = get_settings()
    configure_logging(settings)

    connection = create_connection(settings.database_path)
    initialize_database(connection)

    repository = StateRepository(connection, settings)
    polymarket_client = PolymarketClient(settings)
    trading_engine = TradingEngine(settings, repository, polymarket_client)
    return create_app(settings, repository, trading_engine)


app = build_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=False)
