"""Domain-specific exceptions."""

from __future__ import annotations


class BotError(Exception):
    """Base exception for trading bot errors."""


class BusyTradeError(BotError):
    """Raised when a new entry alert arrives while another trade is open."""


class InvalidAlertError(BotError):
    """Raised when the webhook payload is valid JSON but not tradable."""


class NoActiveTradeError(BotError):
    """Raised when an exit signal arrives without an open trade."""


class ConfigurationError(BotError):
    """Raised when live integration configuration is incomplete."""
