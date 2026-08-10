"""Deterministic brand-priority product ordering."""

from __future__ import annotations

from collections import Counter

from .contracts import RunProduct
from .identity import normalize_sku


def order_run_universe(products: list[RunProduct]) -> list[RunProduct]:
    brand_counts = Counter(p.brand_sort_key or "(none)" for p in products)

    def sort_key(p: RunProduct) -> tuple:
        return (
            -brand_counts[p.brand_sort_key or "(none)"],
            p.brand_sort_key or "(none)",
            normalize_sku(p.sku),
            p.product_id,
        )

    return sorted(products, key=sort_key)
