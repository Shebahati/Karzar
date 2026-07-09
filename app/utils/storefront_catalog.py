"""Storefront-specific catalog helpers: Persian labels, pricing, and sorting."""

from decimal import Decimal
from typing import Literal, Optional

from sqlalchemy import asc, desc, nulls_last

from app.db.models.product import Product
from app.utils.decimal_utils import to_decimal as _to_decimal

Audience = Literal["admin", "storefront"]

LOW_STOCK_THRESHOLD = Decimal("10.0")
HIERARCHY_SEPARATOR_ADMIN = " > "
HIERARCHY_SEPARATOR_STOREFRONT = " › "

STOCK_STATUS_FA_IN = "موجود"
STOCK_STATUS_FA_LOW = "موجودی محدود"
STOCK_STATUS_FA_OUT = "ناموجود"


def hierarchy_separator(audience: Audience) -> str:
    return HIERARCHY_SEPARATOR_STOREFRONT if audience == "storefront" else HIERARCHY_SEPARATOR_ADMIN


def stock_status_label(quantity, *, audience: Audience = "storefront", low_stock: bool = False) -> str:
    qty = _to_decimal(quantity)
    if audience == "storefront":
        if qty <= Decimal("0.0"):
            return STOCK_STATUS_FA_OUT
        if qty < LOW_STOCK_THRESHOLD:
            return STOCK_STATUS_FA_LOW
        return STOCK_STATUS_FA_IN
    if qty <= Decimal("0.0"):
        return "out_of_stock"
    if low_stock or qty < LOW_STOCK_THRESHOLD:
        return "low_stock"
    return "in_stock"


def compute_discount_percent(
    base_price: Optional[Decimal],
    original_price: Optional[Decimal],
) -> Optional[int]:
    if base_price is None or original_price is None:
        return None
    base = _to_decimal(base_price)
    original = _to_decimal(original_price)
    if original <= Decimal("0.0") or base >= original:
        return None
    return int(round((1 - base / original) * 100))


def decimal_to_api_string(value: Optional[Decimal]) -> Optional[str]:
    if value is None:
        return None
    normalized = _to_decimal(value)
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


VALID_SORT_KEYS = frozenset(
    {"newest", "price_asc", "price_desc", "name_asc", "name_desc"}
)


def product_sort_clause(sort: Optional[str]):
    mapping = {
        "newest": Product.created_at.desc(),
        "price_asc": nulls_last(asc(Product.base_price)),
        "price_desc": nulls_last(desc(Product.base_price)),
        "name_asc": Product.name.asc(),
        "name_desc": Product.name.desc(),
    }
    return mapping.get(sort or "newest", Product.created_at.desc())
