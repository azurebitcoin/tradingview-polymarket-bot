"""Logging configuration helpers."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from bot.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure console and rotating file logging for the bot."""

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    if settings.log_file_path is None:
        root_logger.info("File logging disabled because LOG_FILE_PATH is empty.")
        return

    settings.log_file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        file_handler = RotatingFileHandler(
            settings.log_file_path,
            maxBytes=2_000_000,
            backupCount=3,
            encoding="utf-8",
        )
    except OSError as exc:
        root_logger.warning(
            "File logging disabled because %s could not be opened: %s",
            settings.log_file_path,
            exc,
        )
        return

    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
