"""Safe coercion of heterogeneous numeric values to Decimal."""

from decimal import Decimal
from typing import Union


def to_decimal(value: Union[Decimal, float, int, str, None]) -> Decimal:
    """Coerce a value to Decimal, guarding against float leakage from raw SQL."""
    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal("0")
    return Decimal(str(value))
