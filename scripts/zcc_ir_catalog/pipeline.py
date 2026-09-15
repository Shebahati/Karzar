"""Orchestrate read-only discovery, crawl, parse, quality, and reconciliation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from zcc_ir_catalog import PARSER_VERSION
from zcc_ir_catalog.categories import category_mapping_rows
from zcc_ir_catalog.crawl import ReadOnlyFetcher
from zcc_ir_catalog.discover import discover_universe, fetch_robots
from zcc_ir_catalog.karzar_snapshot import load_karzar_snapshot
from zcc_ir_catalog.models import DiscoveryUrl, SourceProduct
from zcc_ir_catalog.output import build_summary, write_artifacts, write_json
from zcc_ir_catalog.parse import parse_product_html
from zcc_ir_catalog.quality import quality_report
from zcc_ir_catalog.reconcile import brand_inventory, reconcile_products

ProgressFn = Callable[[str], None]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _checkpoint_path(output_dir: Path) -> Path:
    return output_dir / "checkpoint_urls.json"


def load_checkpoint(output_dir: Path) -> set[str]:
    path = _checkpoint_path(output_dir)
    if not path.is_file():
        return set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    return set(payload.get("completed_urls") or [])


def save_checkpoint(output_dir: Path, completed: set[str]) -> None:
    write_json(_checkpoint_path(output_dir), {"completed_urls": sorted(completed)})


def crawl_products(
    fetcher: ReadOnlyFetcher,
    seeds: list[DiscoveryUrl],
    *,
    output_dir: Path,
    limit: int | None = None,
    progress: ProgressFn | None = None,
) -> tuple[list[SourceProduct], list[dict[str, Any]]]:
    log = progress or (lambda _m: None)
    completed = load_checkpoint(output_dir)
    products: list[SourceProduct] = []
    failures: list[dict[str, Any]] = []
    # Reload parsed products from cache-only re-parse of completed URLs.
    targets = seeds[:limit] if limit is not None else seeds
    for i, seed in enumerate(targets, start=1):
        log(f"product {i}/{len(targets)} {seed.url}")
        result = fetcher.fetch(seed.url)
        if not result.ok:
            failures.append(
                {
                    "url": seed.url,
                    "status": result.status,
                    "error": result.error,
                    "phase": "product",
                }
            )
            continue
        try:
            product = parse_product_html(
                result.body,
                source_url=seed.url,
                sitemap_lastmod=seed.lastmod,
                sitemap_images=seed.sitemap_image_urls,
                crawl_timestamp=_now(),
            )
        except Exception as exc:  # noqa: BLE001
            failures.append(
                {
                    "url": seed.url,
                    "status": result.status,
                    "error": f"parse:{exc}",
                    "phase": "product_parse",
                }
            )
            continue
        products.append(product)
        completed.add(seed.url)
        if i % 25 == 0:
            save_checkpoint(output_dir, completed)
    save_checkpoint(output_dir, completed)
    return products, failures


def run_phase1(
    *,
    output_dir: Path,
    cache_dir: Path,
    sleep_s: float = 0.8,
    timeout_s: float = 45.0,
    retries: int = 4,
    limit: int | None = None,
    include_listings: bool = True,
    fetch_karzar_public: bool = True,
    snapshot_csv: str | None = None,
    products_json: str | None = None,
    read_db: bool = False,
    karzar_categories: list[dict[str, Any]] | None = None,
    opener=None,
    progress: ProgressFn | None = None,
) -> dict[str, Any]:
    log = progress or (lambda m: print(m, flush=True))
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    fetcher = ReadOnlyFetcher(
        cache_dir=cache_dir,
        robots_rules={"disallow": [], "allow": [], "sitemaps": []},
        timeout_s=timeout_s,
        retries=retries,
        sleep_s=sleep_s,
        opener=opener,
    )
    robots = fetch_robots(fetcher)
    fetcher.robots_rules = robots
    log("robots loaded")

    discovery = discover_universe(fetcher, include_listings=include_listings, progress=log)
    grouped = discovery["grouped"]
    seeds: list[DiscoveryUrl] = list(discovery["products"])  # type: ignore[arg-type]
    log(f"discovered products={len(seeds)}")

    products, failures = crawl_products(
        fetcher,
        seeds,
        output_dir=output_dir,
        limit=limit,
        progress=log,
    )
    log(f"parsed products={len(products)} failures={len(failures)}")

    quality = quality_report(products)

    karzar_products, karzar_meta = load_karzar_snapshot(
        snapshot_csv=snapshot_csv,
        products_json=products_json,
        read_db=read_db,
        fetch_public=fetch_karzar_public and not (snapshot_csv or products_json or read_db),
    )
    cats = karzar_categories
    if cats is None:
        cats = list(karzar_meta.get("categories") or [])
    brands_payload = []
    raw_brands = karzar_meta.get("brands") or {}
    if isinstance(raw_brands, dict) and "all_counts" in raw_brands:
        for name, info in (raw_brands.get("all_counts") or {}).items():
            brands_payload.append({"name": name, "id": (info or {}).get("id")})
    brand_rows = brand_inventory(products, brands_payload)
    cat_rows = category_mapping_rows(products, cats)
    rec_rows, karzar_only_products = reconcile_products(products, karzar_products)

    extra = {
        "parser_version": PARSER_VERSION,
        "discovery_method": "sitemap+listing_html+jsonld_product",
        "robots_sitemaps": robots.get("sitemaps"),
        "sitemap_product_urls": len(
            [u for u in (grouped.get("product") or []) if "/product/" in getattr(u, "url", "")]
        ),
        "listing_pages_scanned": discovery.get("listing_pages_scanned"),
        "wc_store_api_not_used": True,
        "wc_store_api_reason": "robots.txt Disallow: /wp-json/",
        "karzar_snapshot": {
            "scope": karzar_meta.get("scope"),
            "provenance": karzar_meta.get("provenance"),
            "product_count": len(karzar_products),
            "brands": raw_brands,
        },
        "source_catalog_complete": limit is None and not failures,
        "fetcher_stats": fetcher.stats,
    }
    summary = build_summary(
        products=products,
        brands=brand_rows,
        categories=cat_rows,
        reconcile_rows=rec_rows,
        karzar_only=len(karzar_only_products),
        failures=failures,
        quality=quality,
        extra=extra,
    )
    paths = write_artifacts(
        output_dir,
        products=products,
        brands=brand_rows,
        categories=cat_rows,
        reconcile_rows=rec_rows,
        karzar_only=[
            {
                "id": p.id,
                "sku": p.sku,
                "brand": p.brand,
                "brand_key": p.brand_key,
                "name": p.name,
                "base_price": str(p.base_price) if p.base_price is not None else "",
                "is_available": p.is_available,
            }
            for p in karzar_only_products
        ],
        failures=failures,
        quality=quality,
        summary=summary,
    )
    write_json(output_dir / "zcc_ir_discovery_index.json", {
        "products": [s.url for s in seeds],
        "brands": [s.url for s in (grouped.get("brand") or [])],
        "categories": [s.url for s in (grouped.get("category") or [])],
    })
    log(f"artifacts written under {output_dir}")
    return {"summary": summary, "paths": paths, "products": products, "failures": failures}
