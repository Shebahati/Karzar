"""Two-stage storefront scan with resume cache."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from .api_client import (
    DEFAULT_API_BASE,
    fetch_all_products,
    fetch_product_detail,
    parse_detail_images,
)
from .classify import classify_product
from .contracts import (
    AssetValidation,
    BaselineError,
    ProductClassification,
    ProductListItem,
    RunCounters,
    ScanResult,
)
from .http_transport import RateLimitedTransport, validate_asset


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")


async def _classify_one(
    item: ProductListItem,
    transport: RateLimitedTransport,
    *,
    api_base: str,
    api_cache: dict[str, Any],
    asset_cache: dict[str, AssetValidation],
    progress_dir: Path,
) -> ProductClassification:
    thumb = (item.thumbnail or "").strip() or None
    thumb_val: AssetValidation | None = None
    if thumb:
        thumb_val = await validate_asset(transport, thumb, cache=asset_cache)

    need_detail = False
    if not thumb:
        need_detail = True
    elif thumb_val is not None and not (
        thumb_val.decode_ok and not thumb_val.is_known_placeholder
    ):
        need_detail = True

    detail_images = None
    detail_fetched = False
    image_vals: dict[str, AssetValidation] = {}
    if thumb and thumb_val is not None:
        image_vals[thumb] = thumb_val

    if need_detail:
        detail_path = progress_dir / "details" / f"{item.product_id}.json"
        cached = _load_json(detail_path)
        if cached is not None:
            payload = cached
            api_cache.setdefault(
                f"{api_base.rstrip('/')}/api/v1/products/{item.product_id}", payload
            )
        else:
            payload = await fetch_product_detail(
                transport, item.product_id, api_base=api_base, cache=api_cache
            )
            _save_json(detail_path, payload)
        detail_fetched = True
        detail_images = parse_detail_images(payload)
        # Validate all detail images (deduped via asset_cache)
        for img in detail_images:
            image_vals[img.url] = await validate_asset(transport, img.url, cache=asset_cache)

    return classify_product(
        item,
        thumb_validation=thumb_val,
        detail_images=detail_images,
        image_validations=image_vals,
        detail_fetched=detail_fetched,
    )


async def run_scan(
    *,
    output_run_dir: Path,
    api_base: str = DEFAULT_API_BASE,
    page_size: int = 1000,
    api_concurrency: int = 4,
    asset_concurrency: int = 8,
    per_host_concurrency: int = 6,
    timeout_s: float = 20.0,
    retries: int = 2,
    sync_fetch=None,
    resume: bool = True,
) -> ScanResult:
    output_run_dir.mkdir(parents=True, exist_ok=True)
    progress_dir = output_run_dir / "cache"
    progress_dir.mkdir(parents=True, exist_ok=True)
    api_cache_path = progress_dir / "api_cache.json"
    asset_meta_path = progress_dir / "asset_cache.json"
    class_path = progress_dir / "classifications.json"

    api_cache: dict[str, Any] = {}
    if resume and api_cache_path.exists():
        loaded = _load_json(api_cache_path) or {}
        if isinstance(loaded, dict):
            api_cache = loaded

    asset_cache: dict[str, AssetValidation] = {}
    if resume and asset_meta_path.exists():
        raw = _load_json(asset_meta_path) or {}
        if isinstance(raw, dict):
            for k, v in raw.items():
                if isinstance(v, dict):
                    asset_cache[k] = AssetValidation(**v)

    counters = RunCounters()
    transport = RateLimitedTransport(
        counters=counters,
        timeout_s=timeout_s,
        retries=retries,
        api_concurrency=api_concurrency,
        asset_concurrency=asset_concurrency,
        per_host_concurrency=per_host_concurrency,
        sync_fetch=sync_fetch,
    )

    try:
        products, total = await fetch_all_products(
            transport, api_base=api_base, page_size=page_size, cache=api_cache
        )
        _save_json(api_cache_path, api_cache)

        # Resume completed classifications
        done: dict[int, ProductClassification] = {}
        if resume and class_path.exists():
            prev = _load_json(class_path) or []
            if isinstance(prev, list):
                for row in prev:
                    if isinstance(row, dict) and "product_id" in row:
                        done[int(row["product_id"])] = ProductClassification(**row)

        pending = [p for p in products if p.product_id not in done]
        sem = asyncio.Semaphore(api_concurrency)

        async def worker(item: ProductListItem) -> ProductClassification:
            async with sem:
                return await _classify_one(
                    item,
                    transport,
                    api_base=api_base,
                    api_cache=api_cache,
                    asset_cache=asset_cache,
                    progress_dir=progress_dir,
                )

        # Batch to allow periodic checkpoint
        batch_size = 50
        for i in range(0, len(pending), batch_size):
            chunk = pending[i : i + batch_size]
            results = await asyncio.gather(*[worker(p) for p in chunk])
            for c in results:
                done[c.product_id] = c
            _save_json(class_path, [c.__dict__ for c in done.values()])
            _save_json(
                asset_meta_path,
                {k: v.to_dict() for k, v in asset_cache.items()},
            )
            _save_json(api_cache_path, api_cache)

        ordered = [done[p.product_id] for p in products]
        if len(ordered) != total:
            raise BaselineError(
                "scan",
                f"classification count {len(ordered)} != catalog_total {total}",
            )

        return ScanResult(
            classifications=ordered,
            asset_validations=list(asset_cache.values()),
            counters=counters,
            catalog_total=total,
            unique_product_ids=[p.product_id for p in products],
            authority_notes={
                "authority_mode": "live_public_storefront_api",
                "api_base": api_base,
                "product_list_route": "/api/v1/products/",
                "product_detail_route": "/api/v1/products/{product_id}",
                "health_self_label_note": (
                    "api.karzartools.com /health may self-label Staging; "
                    "baseline uses public storefront exposure (operational debt)."
                ),
            },
        )
    finally:
        await transport.aclose()
