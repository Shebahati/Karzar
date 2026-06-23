from decimal import Decimal
from typing import Union


def to_decimal(value: Union[Decimal, float, int, str, None]) -> Decimal:
    """Safely coerce any numeric value to Decimal.

    Even though the ORM now maps Numeric columns to Decimal, this helper
    guards against float leakage from raw SQL expressions or test fixtures.
    """
    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal("0")
    return Decimal(str(value))
