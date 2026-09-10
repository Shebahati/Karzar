"""Postex/Karzar monetary conversion. Never use binary float for persisted money."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.core.constants import TOMAN_TO_RIAL

IRR = "IRR"
TOMAN = "TOMAN"


def as_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def irr_to_toman(amount_irr: Decimal | int | str) -> Decimal:
    """Official Postex documented money is Rial. Karzar site is Toman (10 Rial = 1 Toman)."""
    irr = as_decimal(amount_irr).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return (irr / Decimal(TOMAN_TO_RIAL)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def toman_to_irr(amount_toman: Decimal | int | str) -> Decimal:
    toman = as_decimal(amount_toman)
    return (toman * Decimal(TOMAN_TO_RIAL)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
