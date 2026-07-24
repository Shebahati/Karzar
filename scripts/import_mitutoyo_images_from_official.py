#!/usr/bin/env python3
"""Import Mitutoyo product images from mitutoyoiran.com (authorized WC store).

Very-high SKU match only. One primary image per product.
Remote URLs are temporary — materialize_product_images.py writes files to disk.

Usage:
  .venv/bin/python scripts/import_mitutoyo_images_from_official.py --dry-run
  .venv/bin/python scripts/import_mitutoyo_images_from_official.py
  .venv/bin/python scripts/import_mitutoyo_images_from_official.py --refresh-index --limit 50
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.logging import get_logger, setup_logging
from app.crud import product as crud_product
from app.db.database import async_session_maker
from app.db.models.product import Brand, Product, ProductImage

setup_logging()
logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "data" / "imports" / "mitutoyo"
INDEX_JSONL = OUT_DIR / "phase3_source_index.jsonl"
IMPORTED_CSV = OUT_DIR / "phase3_imported.csv"
REJECTED_CSV = OUT_DIR / "phase3_rejected.csv"
INDEX_CSV = OUT_DIR / "phase3_site_index.csv"

STORE_API = "https://www.mitutoyoiran.com/wp-json/wc/store/v1/products"
USER_AGENT = "Mozilla/5.0 (compatible; KarzarCatalogBot/1.0; +https://www.karzartools.com)"

PLACEHOLDER_RE = re.compile(
    r"(woocommerce-placeholder|placeholder|default[-_]?(image|product)|logo[-_]?only|"
    r"/logo\.(?:png|jpg|jpeg|webp|svg))",
    re.IGNORECASE,
)


@dataclass
class SourceProduct:
    source_id: int
    sku: str
    name: str
    permalink: str
    image_url: str | None
    issues: list[str] = field(default_factory=list)


def normalize_sku(raw: str | None) -> str:
    return (raw or "").strip().upper()


def pick_image(images: list[dict]) -> str | None:
    for img in images or []:
        src = (img.get("src") or "").strip()
        if not src.startswith("http"):
            continue
        path = unquote(urlparse(src).path)
        name = (img.get("name") or "") + " " + path
        if PLACEHOLDER_RE.search(name) or PLACEHOLDER_RE.search(src):
            continue
        return src
    return None


async def fetch_page(
    client: httpx.AsyncClient, page: int, per_page: int
) -> tuple[list[dict], int, int]:
    resp = await client.get(
        STORE_API,
        params={"per_page": per_page, "page": page, "orderby": "id", "order": "asc"},
    )
    resp.raise_for_status()
    total = int(resp.headers.get("x-wp-total") or "0")
    total_pages = int(resp.headers.get("x-wp-totalpages") or "1")
    data = resp.json()
    if not isinstance(data, list):
        raise RuntimeError(f"unexpected Store API payload type: {type(data)}")
    return data, total, total_pages


def parse_item(item: dict) -> SourceProduct:
    sku = normalize_sku(item.get("sku"))
    name = (item.get("name") or "").strip()
    permalink = (item.get("permalink") or item.get("url") or "").strip()
    image = pick_image(item.get("images") or [])
    issues: list[str] = []
    if not sku:
        issues.append("no_sku")
    if not image:
        issues.append("no_product_image")
    return SourceProduct(
        source_id=int(item.get("id") or 0),
        sku=sku,
        name=name,
        permalink=permalink,
        image_url=image,
        issues=issues,
    )


async def crawl_store(
    *,
    per_page: int,
    delay_s: float,
    limit_pages: int | None,
) -> list[SourceProduct]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    products: list[SourceProduct] = []
    async with httpx.AsyncClient(
        timeout=90.0,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
    ) as client:
        page = 1
        total_pages = 1
        while page <= total_pages:
            if limit_pages is not None and page > limit_pages:
                break
            logger.info("store crawl page %s …", page)
            data, total, total_pages = await fetch_page(client, page, per_page)
            if page == 1:
                logger.info("store total_products≈%s total_pages=%s", total, total_pages)
            if not data:
                break
            for item in data:
                products.append(parse_item(item))
            await asyncio.sleep(delay_s)
            page += 1
    return products


def write_index_cache(products: list[SourceProduct]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with INDEX_JSONL.open("w", encoding="utf-8") as handle:
        for p in products:
            handle.write(
                json.dumps(
                    {
                        "source_id": p.source_id,
                        "sku": p.sku,
                        "name": p.name,
                        "permalink": p.permalink,
                        "image_url": p.image_url,
                        "issues": p.issues,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def load_index_cache() -> list[SourceProduct]:
    products: list[SourceProduct] = []
    for line in INDEX_JSONL.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        products.append(
            SourceProduct(
                source_id=int(row.get("source_id") or 0),
                sku=normalize_sku(row.get("sku")),
                name=(row.get("name") or "").strip(),
                permalink=(row.get("permalink") or "").strip(),
                image_url=row.get("image_url"),
                issues=list(row.get("issues") or []),
            )
        )
    return products


def build_sku_map(
    products: list[SourceProduct],
) -> tuple[dict[str, tuple[str, str, str]], dict[str, str]]:
    """Return sku -> (image_url, detail_url, title), and ambiguous reasons."""
    buckets: dict[str, list[SourceProduct]] = {}
    for p in products:
        if p.issues or not p.sku or not p.image_url:
            continue
        buckets.setdefault(p.sku, []).append(p)

    accepted: dict[str, tuple[str, str, str]] = {}
    ambiguous: dict[str, str] = {}
    for sku, group in buckets.items():
        img_counts = Counter(p.image_url for p in group)
        if len(img_counts) > 1:
            ambiguous[sku] = f"ambiguous_images:{len(img_counts)}"
            continue
        pick = min(group, key=lambda p: (len(p.permalink or ""), p.source_id))
        accepted[sku] = (pick.image_url or "", pick.permalink, pick.name)
    return accepted, ambiguous


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


async def run(
    *,
    dry_run: bool,
    refresh_index: bool,
    limit_pages: int | None,
    per_page: int,
    delay_s: float,
) -> None:
    started = time.time()
    if refresh_index or not INDEX_JSONL.exists():
        products = await crawl_store(
            per_page=per_page, delay_s=delay_s, limit_pages=limit_pages
        )
        write_index_cache(products)
    else:
        products = load_index_cache()
        logger.info("loaded cached index %s rows from %s", len(products), INDEX_JSONL)

    accepted, ambiguous = build_sku_map(products)

    index_rows: list[dict[str, str]] = []
    for sku, (image, detail, title) in sorted(accepted.items()):
        index_rows.append(
            {
                "sku": sku,
                "image_url": image,
                "detail_url": detail,
                "title": title,
                "status": "accepted",
            }
        )
    for sku, reason in sorted(ambiguous.items()):
        index_rows.append(
            {
                "sku": sku,
                "image_url": "",
                "detail_url": "",
                "title": "",
                "status": reason,
            }
        )
    write_csv(
        INDEX_CSV,
        index_rows,
        ["sku", "image_url", "detail_url", "title", "status"],
    )

    imported_rows: list[dict[str, str]] = []
    rejected_rows: list[dict[str, str]] = []
    inserted = 0

    async with async_session_maker() as session:
        brand_id = (
            await session.execute(
                select(Brand.id).where(Brand.name.ilike("%Mitutoyo%")).limit(1)
            )
        ).scalar_one()
        result = await session.execute(
            select(Product.id, Product.sku, Product.name)
            .where(Product.brand_id == brand_id)
            .where(Product.deleted_at.is_(None))
            .order_by(Product.id)
        )
        catalog = list(result.all())

        existing_ids = set(
            (
                await session.execute(
                    select(ProductImage.product_id).where(
                        ProductImage.product_id.in_([p.id for p in catalog])
                    )
                )
            )
            .scalars()
            .all()
        )

        for product_id, sku, name in catalog:
            code = normalize_sku(sku)
            if product_id in existing_ids:
                rejected_rows.append(
                    {
                        "sku": sku,
                        "product_name": name or "",
                        "issue_codes": "already_has_image",
                        "issue_fa": "از قبل تصویر دارد",
                        "detail_url": "",
                        "image_url": "",
                    }
                )
                continue
            if code in ambiguous:
                rejected_rows.append(
                    {
                        "sku": sku,
                        "product_name": name or "",
                        "issue_codes": ambiguous[code],
                        "issue_fa": "کد در چند محصول منبع با عکس متفاوت",
                        "detail_url": "",
                        "image_url": "",
                    }
                )
                continue
            hit = accepted.get(code)
            if not hit:
                rejected_rows.append(
                    {
                        "sku": sku,
                        "product_name": name or "",
                        "issue_codes": "no_official_match",
                        "issue_fa": "کد در فروشگاه مجاز پیدا نشد / بدون عکس",
                        "detail_url": "",
                        "image_url": "",
                    }
                )
                continue

            image_url, detail_url, _title = hit
            imported_rows.append(
                {
                    "sku": sku,
                    "product_name": name or "",
                    "image_url": image_url,
                    "detail_url": detail_url,
                    "confidence": "very_high",
                }
            )
            if dry_run:
                inserted += 1
                continue
            try:
                await crud_product.add_product_image(
                    session, product_id, image_url, is_primary=True
                )
                inserted += 1
            except Exception as exc:  # noqa: BLE001
                logger.exception("db error %s", sku)
                rejected_rows.append(
                    {
                        "sku": sku,
                        "product_name": name or "",
                        "issue_codes": "db_error",
                        "issue_fa": str(exc),
                        "detail_url": detail_url,
                        "image_url": image_url,
                    }
                )

        if not dry_run:
            await session.commit()

    write_csv(
        IMPORTED_CSV,
        imported_rows,
        ["sku", "product_name", "image_url", "detail_url", "confidence"],
    )
    write_csv(
        REJECTED_CSV,
        rejected_rows,
        ["sku", "product_name", "issue_codes", "issue_fa", "detail_url", "image_url"],
    )

    elapsed = int(time.time() - started)
    print("=== Mitutoyo image import summary ===")
    print(f"Mode: {'dry-run' if dry_run else 'live'}")
    print(f"Source products crawled/cached: {len(products)}")
    print(f"Official SKUs accepted: {len(accepted)}")
    print(f"Official SKUs ambiguous: {len(ambiguous)}")
    print(f"Catalog matched / inserted: {inserted}")
    print(f"Rejected / skipped: {len(rejected_rows)}")
    print(f"Elapsed: {elapsed}s")
    print(f"Imported CSV: {IMPORTED_CSV}")
    print(f"Rejected CSV: {REJECTED_CSV}")
    print(f"Site index CSV: {INDEX_CSV}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--refresh-index", action="store_true")
    parser.add_argument("--limit-pages", type=int, default=None)
    parser.add_argument("--per-page", type=int, default=50)
    parser.add_argument("--delay", type=float, default=0.4)
    args = parser.parse_args()
    asyncio.run(
        run(
            dry_run=args.dry_run,
            refresh_index=args.refresh_index,
            limit_pages=args.limit_pages,
            per_page=args.per_page,
            delay_s=args.delay,
        )
    )


if __name__ == "__main__":
    main()
