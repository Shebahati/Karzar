"""Start-of-run storefront reconciliation against accepted seed."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from scripts.fast_image_coverage_baseline.api_client import (
    empty_counters,
    fetch_all_products,
    require_api_base,
)
from scripts.fast_image_coverage_baseline.contracts import ProductListItem
from scripts.fast_image_coverage_baseline.http_transport import (
    RateLimitedTransport,
    validate_asset,
)
from scripts.fast_image_coverage_baseline.placeholders import mark_placeholder

from .contracts import DriftRow, RunProduct, SeedProduct


def _thumb_usable(thumb_val) -> bool:
    if thumb_val is None:
        return False
    return bool(
        thumb_val.decode_ok
        and not thumb_val.is_known_placeholder
        and not mark_placeholder(thumb_val.url, thumb_val.sha256)
    )


async def reconcile_storefront(
    *,
    api_base: str,
    seed_products: list[SeedProduct],
    sync_fetch: Callable | None = None,
) -> tuple[list[DriftRow], list[RunProduct], dict[str, int]]:
    """Lightweight read-only reconciliation. Returns drift rows, run universe, counters."""
    base = require_api_base(api_base)
    transport = RateLimitedTransport(counters=empty_counters(), sync_fetch=sync_fetch)
    seed_by_id = {p.product_id: p for p in seed_products}
    seed_ids = set(seed_by_id)

    list_items, _total = await fetch_all_products(transport, api_base=base)
    live_by_id: dict[int, ProductListItem] = {int(x.product_id): x for x in list_items}

    drift: list[DriftRow] = []
    run_universe: list[RunProduct] = []
    counters = {
        "active_seed_missing": 0,
        "resolved_since_baseline": 0,
        "removed_since_baseline": 0,
        "new_missing_since_baseline": 0,
    }

    asset_cache: dict = {}

    async def live_has_usable_primary(item: ProductListItem) -> bool:
        if not item.thumbnail:
            return False
        thumb_val = await validate_asset(transport, item.thumbnail, cache=asset_cache)
        return _thumb_usable(thumb_val)

    for pid, seed in seed_by_id.items():
        live = live_by_id.get(pid)
        if live is None:
            drift.append(
                DriftRow(
                    product_id=pid,
                    sku=seed.sku,
                    brand_key=seed.brand_key,
                    drift_status="removed_since_baseline",
                    notes="product no longer in public storefront list",
                )
            )
            counters["removed_since_baseline"] += 1
            continue

        if await live_has_usable_primary(live):
            drift.append(
                DriftRow(
                    product_id=pid,
                    sku=seed.sku,
                    brand_key=seed.brand_key,
                    drift_status="resolved_since_baseline",
                    notes="storefront now has usable primary thumbnail",
                )
            )
            counters["resolved_since_baseline"] += 1
            continue

        drift.append(
            DriftRow(
                product_id=pid,
                sku=seed.sku,
                brand_key=seed.brand_key,
                drift_status="active_seed_missing",
                notes="still missing usable primary thumbnail on storefront list",
            )
        )
        counters["active_seed_missing"] += 1
        run_universe.append(
            RunProduct(
                product_id=pid,
                sku=seed.sku,
                brand_key=seed.brand_key,
                category_slug=seed.category_slug,
                product_name=seed.product_name,
                origin="active_seed_missing",
                brand_sort_key=seed.brand_key or "(none)",
            )
        )

    for pid, live in live_by_id.items():
        if pid in seed_ids:
            continue
        if await live_has_usable_primary(live):
            continue
        drift.append(
            DriftRow(
                product_id=pid,
                sku=live.sku,
                brand_key=live.brand_key or "",
                drift_status="new_missing_since_baseline",
                notes="new public product without usable primary thumbnail on list",
            )
        )
        counters["new_missing_since_baseline"] += 1
        run_universe.append(
            RunProduct(
                product_id=pid,
                sku=live.sku,
                brand_key=live.brand_key or "",
                category_slug=live.category_slug or "",
                product_name=live.name,
                origin="new_missing_since_baseline",
                brand_sort_key=live.brand_key or "(none)",
            )
        )

    return drift, run_universe, counters


def reconcile_storefront_sync(**kwargs):
    return asyncio.run(reconcile_storefront(**kwargs))
