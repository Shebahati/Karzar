"""Storefront-specific catalog helpers: Persian labels, pricing, and sorting."""

from decimal import Decimal
from typing import Literal

from sqlalchemy import asc, case, desc, literal, nulls_last

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
    base_price: Decimal | None,
    original_price: Decimal | None,
) -> int | None:
    if base_price is None or original_price is None:
        return None
    base = _to_decimal(base_price)
    original = _to_decimal(original_price)
    if original <= Decimal("0.0") or base >= original:
        return None
    return int(round((1 - base / original) * 100))


def decimal_to_api_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    normalized = _to_decimal(value)
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


VALID_SORT_KEYS = frozenset(
    {
        "newest",
        "price_asc",
        "price_desc",
        "discount_desc",
        "stock_first",
        # Legacy keys kept for older clients / bookmarks
        "name_asc",
        "name_desc",
    }
)


def product_sort_clause(sort: str | None, *, dialect_name: str = "postgresql"):
    """Return an ORDER BY clause tuple for storefront product listing.

    Name sorts use plain column order (no locale collation) so listings work on
    databases that lack fa_IR / ICU collations.
    """
    del dialect_name  # Reserved for dialect-specific sorts; name sort is portable.
    key = sort if sort in VALID_SORT_KEYS else "newest"

    if key == "discount_desc":
        discount_ratio = case(
            (
                (Product.original_price.isnot(None))
                & (Product.base_price.isnot(None))
                & (Product.original_price > Product.base_price)
                & (Product.original_price > 0),
                (Product.original_price - Product.base_price) / Product.original_price,
            ),
            else_=literal(0),
        )
        return (desc(discount_ratio), Product.created_at.desc(), Product.id.desc())

    if key == "stock_first":
        # In-stock first, then higher quantity, then newest.
        out_of_stock = case((Product.stock_quantity > 0, 0), else_=1)
        return (asc(out_of_stock), desc(Product.stock_quantity), Product.created_at.desc())

    mapping = {
        "newest": (Product.created_at.desc(), Product.id.desc()),
        "price_asc": (nulls_last(asc(Product.base_price)), Product.id.asc()),
        "price_desc": (nulls_last(desc(Product.base_price)), Product.id.desc()),
        "name_asc": (Product.name.asc(), Product.id.asc()),
        "name_desc": (Product.name.desc(), Product.id.desc()),
    }
    return mapping.get(key, mapping["newest"])


def escape_ilike_pattern(value: str) -> str:
    """Escape ``\\``, ``%``, and ``_`` so ILIKE treats them as literals."""
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def parse_in_stock_filter(value: str | None) -> bool | None:
    """Accept storefront contract values: true/false/1/0.

    Raises ``ValueError`` for non-empty unrecognized values (callers should 422).
    """
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized == "":
        return None
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    raise ValueError(
        "in_stock must be one of: true, false, 1, 0"
    )


def parse_int_id_list(
    values: list[int] | list[str] | int | str | None,
) -> list[int] | None:
    """Normalize brand/category-style ID filters to a deduped list.

    Accepts FastAPI repeated query params (``brand_id=1&brand_id=2``), a single
    int, or a comma-separated string (``brand_id=1,2``). Empty → ``None``.
    """
    if values is None:
        return None
    raw_items: list[str] = []
    if isinstance(values, int | str):
        raw_items = [str(values)]
    else:
        for item in values:
            raw_items.append(str(item))

    result: list[int] = []
    seen: set[int] = set()
    for item in raw_items:
        for part in item.split(","):
            token = part.strip()
            if not token:
                continue
            try:
                parsed = int(token)
            except ValueError as exc:
                raise ValueError(f"invalid integer id: {token}") from exc
            if parsed not in seen:
                seen.add(parsed)
                result.append(parsed)
    return result or None


def parse_string_list(
    values: list[str] | str | None,
) -> list[str] | None:
    """Normalize multi-value string filters (e.g. countries).

    Accepts repeated query params or a comma-separated string. Empty → ``None``.
    """
    if values is None:
        return None
    raw_items: list[str] = [values] if isinstance(values, str) else list(values)

    result: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        for part in item.split(","):
            token = part.strip()
            if not token:
                continue
            if token not in seen:
                seen.add(token)
                result.append(token)
    return result or None


def _flatten_csv_tokens(values: list[str] | None) -> list[str]:
    """Expand repeated query params and comma-separated tokens into a flat list."""
    if not values:
        return []
    tokens: list[str] = []
    for raw in values:
        if raw is None:
            continue
        for part in str(raw).split(","):
            token = part.strip()
            if token:
                tokens.append(token)
    return tokens


def parse_int_list_param(values: list[str] | None) -> list[int] | None:
    """Parse multi-value int filters (``brand_id=1&brand_id=2`` or ``brand_id=1,2``).

    Returns ``None`` when no values are provided. Raises ``ValueError`` on bad ints.
    """
    tokens = _flatten_csv_tokens(values)
    if not tokens:
        return None
    try:
        parsed = [int(token) for token in tokens]
    except ValueError as exc:
        raise ValueError("must be a list of integers") from exc
    # Preserve order, drop duplicates.
    seen: set[int] = set()
    unique: list[int] = []
    for item in parsed:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def parse_str_list_param(values: list[str] | None) -> list[str] | None:
    """Parse multi-value string filters (``country=a&country=b`` or ``country=a,b``).

    Returns ``None`` when no values are provided. Deduplicates while preserving order.
    """
    tokens = _flatten_csv_tokens(values)
    if not tokens:
        return None
    seen: set[str] = set()
    unique: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            unique.append(token)
    return unique
