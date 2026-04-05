"""Progression strategy helpers."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


MONEY_PLACES = Decimal("0.01")
SIZE_PLACES = Decimal("0.0001")
PRICE_PLACES = Decimal("0.0001")


def money(value: float | Decimal) -> Decimal:
    """Round cash values to cents."""

    return Decimal(str(value)).quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def size(value: float | Decimal) -> Decimal:
    """Round token size to four decimal places."""

    return Decimal(str(value)).quantize(SIZE_PLACES, rounding=ROUND_HALF_UP)


def price(value: float | Decimal) -> Decimal:
    """Round prices to four decimal places."""

    return Decimal(str(value)).quantize(PRICE_PLACES, rounding=ROUND_HALF_UP)


def progression_amount(base_amount: float, multiplier: float, step_index: int) -> Decimal:
    """Compute the current trade notional for the active progression step."""

    base = Decimal(str(base_amount))
    factor = Decimal(str(multiplier)) ** step_index
    return money(base * factor)


def next_step_after_result(current_step: int, max_steps: int, won: bool) -> tuple[int, bool]:
    """Return the next step and whether the progression limit was exhausted."""

    if won:
        return 0, False

    next_step = current_step + 1
    if next_step >= max_steps:
        return 0, True

    return next_step, False
