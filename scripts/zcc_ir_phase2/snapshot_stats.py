"""READ-ONLY Karzar catalog statistics by brand."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from catalog_target.core import CurrentProduct


def _is_deleted(product: CurrentProduct) -> bool:
    return bool(product.deleted_at)


def _has_price(product: CurrentProduct) -> bool:
    if product.base_price is None:
        return False
    try:
        return product.base_price > Decimal("0")
    except Exception:  # noqa: BLE001
        return False


def _has_image(product: CurrentProduct) -> bool:
    if product.primary_image_url:
        return True
    return bool(product.image_count and product.image_count > 0)


def _storefront_heuristic(product: CurrentProduct) -> bool:
    """Approximate storefront visibility: active, not deleted, not explicitly unavailable."""
    if _is_deleted(product):
        return False
    if product.is_active is False:
        return False
    if product.is_available is False:
        return False
    return True


def brand_catalog_stats(
    products: list[CurrentProduct],
    brand_keys: set[str],
) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[CurrentProduct]] = defaultdict(list)
    for product in products:
        key = product.brand_key or ""
        if key in brand_keys:
            buckets[key].append(product)
    out: dict[str, dict[str, Any]] = {}
    for key in sorted(brand_keys):
        rows = buckets.get(key, [])
        total = len(rows)
        deleted = sum(1 for p in rows if _is_deleted(p))
        active = sum(1 for p in rows if not _is_deleted(p) and p.is_active is True)
        inactive = sum(1 for p in rows if not _is_deleted(p) and p.is_active is False)
        unknown_active = total - deleted - active - inactive
        available = sum(1 for p in rows if p.is_available is True)
        unavailable = sum(1 for p in rows if p.is_available is False)
        with_price = sum(1 for p in rows if _has_price(p))
        with_image = sum(1 for p in rows if _has_image(p))
        storefront_visible = sum(1 for p in rows if _storefront_heuristic(p))
        out[key] = {
            "brand_key": key,
            "total": total,
            "active": active,
            "inactive": inactive,
            "unknown_active": unknown_active,
            "deleted": deleted,
            "available": available,
            "unavailable": unavailable,
            "availability_unknown": total - available - unavailable,
            "storefront_visible_heuristic": storefront_visible,
            "non_storefront_heuristic": total - storefront_visible,
            "with_price": with_price,
            "with_image": with_image,
        }
    return out
