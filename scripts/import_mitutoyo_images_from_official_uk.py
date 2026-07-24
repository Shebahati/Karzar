#!/usr/bin/env python3
"""Import Mitutoyo product images from official shop.mitutoyo.co.uk CDN.

Replaces dealer/watermarked sources. Very-high SKU match only via exact
filename containing the catalog order number on:
  https://shop.mitutoyo.co.uk/media/mitutoyoData/IM/bigweb/

Usage:
  .venv/bin/python scripts/import_mitutoyo_images_from_official_uk.py --dry-run
  .venv/bin/python scripts/import_mitutoyo_images_from_official_uk.py --replace
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
import time
from pathlib import Path

import httpx
from sqlalchemy import delete, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.logging import get_logger, setup_logging
from app.crud import product as crud_product
from app.db.database import async_session_maker
from app.db.models.product import Brand, Product, ProductImage

setup_logging()
logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "data" / "imports" / "mitutoyo"
IMPORTED_CSV = OUT_DIR / "phase3b_imported.csv"
REJECTED_CSV = OUT_DIR / "phase3b_rejected.csv"
PROBE_CSV = OUT_DIR / "phase3b_cdn_probe.csv"

CDN_BASE = "https://shop.mitutoyo.co.uk/media/mitutoyoData/IM/bigweb/"
USER_AGENT = "Mozilla/5.0 (compatible; KarzarCatalogBot/1.0; +https://www.karzartools.com)"
MIN_BYTES = 10_000


def candidate_names(sku: str) -> list[str]:
    """Prefer photographic catalog assets; BMP skipped (too small/noisy).

    Official CDN sometimes stores photos under `*_z_eps.webp` — keep those as
    last resort after jpg/png variants.
    """
    names: list[str] = []
    for s in dict.fromkeys([sku, sku.lower(), sku.upper()]):
        names.extend(
            [
                f"{s}_z1_jpg.webp",
                f"{s}_jpg.webp",
                f"{s}_z1_png.webp",
                f"{s}_png.webp",
                f"{s}_z1.jpg",
                f"{s}.jpg",
                f"{s}_z_eps.webp",
                f"{s}_ z_eps.webp",
            ]
        )
    return list(dict.fromkeys(names))


async def resolve_image(
    client: httpx.AsyncClient,
    sku: str,
    *,
    sem: asyncio.Semaphore,
) -> tuple[str | None, int, str | None]:
    async with sem:
        for name in candidate_names(sku):
            url = CDN_BASE + name
            try:
                resp = await client.head(url)
                size = int(resp.headers.get("content-length") or 0)
                if resp.status_code == 200 and size >= MIN_BYTES:
                    return url, size, name
                if resp.status_code in {403, 405, 501}:
                    resp = await client.get(url, headers={"Range": "bytes=0-128"})
                    if resp.status_code in {200, 206} and not resp.content.startswith(b"<"):
                        cr = resp.headers.get("content-range", "")
                        if "/" in cr:
                            try:
                                size = int(cr.rsplit("/", 1)[-1])
                            except ValueError:
                                size = 0
                        if size >= MIN_BYTES or (
                            resp.status_code == 200 and len(resp.content) >= MIN_BYTES
                        ):
                            # If Range returned body only, confirm with HEAD-less GET size via full GET later
                            if size < MIN_BYTES and resp.status_code == 200:
                                full = await client.get(url)
                                if full.status_code == 200 and len(full.content) >= MIN_BYTES:
                                    return url, len(full.content), name
                            elif size >= MIN_BYTES:
                                return url, size, name
            except Exception as exc:  # noqa: BLE001
                logger.debug("probe fail %s %s: %s", sku, name, type(exc).__name__)
            await asyncio.sleep(0.015)
    return None, 0, None


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


async def run(*, dry_run: bool, replace: bool, concurrency: int) -> None:
    started = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    async with async_session_maker() as session:
        brand_id = (
            await session.execute(
                select(Brand.id).where(Brand.name.ilike("%Mitutoyo%")).limit(1)
            )
        ).scalar_one()
        catalog = list(
            (
                await session.execute(
                    select(Product.id, Product.sku, Product.name)
                    .where(Product.brand_id == brand_id)
                    .where(Product.deleted_at.is_(None))
                    .order_by(Product.sku)
                )
            ).all()
        )
        product_ids = [p.id for p in catalog]

        if replace and not dry_run:
            del_result = await session.execute(
                delete(ProductImage).where(ProductImage.product_id.in_(product_ids))
            )
            await session.commit()
            logger.info("deleted existing Mitutoyo image rows: %s", del_result.rowcount)
        elif replace and dry_run:
            existing = (
                await session.execute(
                    select(ProductImage.id).where(ProductImage.product_id.in_(product_ids))
                )
            ).scalars().all()
            logger.info("dry-run would delete existing Mitutoyo image rows: %s", len(existing))

    sem = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    imported_rows: list[dict[str, str]] = []
    rejected_rows: list[dict[str, str]] = []
    probe_rows: list[dict[str, str]] = []
    inserted = 0

    async with httpx.AsyncClient(
        timeout=25.0,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
        limits=limits,
    ) as client:
        # Warm known-good assets
        for warm in ("103-137_z1_jpg.webp", "523-121_jpg.webp"):
            try:
                await client.head(CDN_BASE + warm)
            except Exception:  # noqa: BLE001
                pass

        results = await asyncio.gather(
            *[resolve_image(client, sku, sem=sem) for _pid, sku, _name in catalog]
        )

    async with async_session_maker() as session:
        for (product_id, sku, name), (url, size, filename) in zip(catalog, results, strict=True):
            if not url:
                rejected_rows.append(
                    {
                        "sku": sku,
                        "product_name": name or "",
                        "issue_codes": "no_official_cdn_asset",
                        "issue_fa": "عکس رسمی باکیفیت روی CDN بریتانیا پیدا نشد",
                        "detail_url": f"https://shop.mitutoyo.co.uk/web/mitutoyo/en_GB/all/PR/{sku}/datasheet.xhtml",
                        "image_url": "",
                    }
                )
                continue

            probe_rows.append(
                {
                    "sku": sku,
                    "image_url": url,
                    "bytes": str(size),
                    "filename": filename or "",
                }
            )
            imported_rows.append(
                {
                    "sku": sku,
                    "product_name": name or "",
                    "image_url": url,
                    "detail_url": f"https://shop.mitutoyo.co.uk/web/mitutoyo/en_GB/all/PR/{sku}/datasheet.xhtml",
                    "confidence": "very_high",
                    "bytes": str(size),
                    "filename": filename or "",
                }
            )
            if dry_run:
                inserted += 1
                continue
            try:
                await crud_product.add_product_image(
                    session, product_id, url, is_primary=True
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
                        "detail_url": "",
                        "image_url": url,
                    }
                )

        if not dry_run:
            await session.commit()

    write_csv(
        IMPORTED_CSV,
        imported_rows,
        ["sku", "product_name", "image_url", "detail_url", "confidence", "bytes", "filename"],
    )
    write_csv(
        REJECTED_CSV,
        rejected_rows,
        ["sku", "product_name", "issue_codes", "issue_fa", "detail_url", "image_url"],
    )
    write_csv(PROBE_CSV, probe_rows, ["sku", "image_url", "bytes", "filename"])

    elapsed = int(time.time() - started)
    print("=== Mitutoyo official UK image import ===")
    print(f"Mode: {'dry-run' if dry_run else 'live'} replace={replace}")
    print(f"Source: {CDN_BASE}")
    print(f"Min bytes: {MIN_BYTES} (photo webp/jpg only; no eps/bmp)")
    print(f"Catalog matched / inserted: {inserted}")
    print(f"Rejected / skipped: {len(rejected_rows)}")
    print(f"Elapsed: {elapsed}s")
    print(f"Imported CSV: {IMPORTED_CSV}")
    print(f"Rejected CSV: {REJECTED_CSV}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete all existing Mitutoyo product_images before insert",
    )
    parser.add_argument("--concurrency", type=int, default=12)
    args = parser.parse_args()
    if not args.dry_run and not args.replace:
        parser.error("Refusing live run without --replace (prevents mixing watermarked rows)")
    asyncio.run(
        run(dry_run=args.dry_run, replace=args.replace, concurrency=args.concurrency)
    )


if __name__ == "__main__":
    main()
