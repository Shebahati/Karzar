#!/usr/bin/env python3
"""Import primary product images from shopmilltools.com WC Store API.

High-confidence title/model matching for TERMA, SAN OU, ASTPOWER.
Does not invent images; unmatched SKUs go to rejected CSV.

Usage:
  .venv/bin/python scripts/import_shopmill_brand_images.py --brand terma --dry-run
  .venv/bin/python scripts/import_shopmill_brand_images.py --brand sanou
  .venv/bin/python scripts/import_shopmill_brand_images.py --brand astpower --replace-missing-only
  .venv/bin/python scripts/import_shopmill_brand_images.py --brand terma --refresh-index
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

import httpx
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.logging import get_logger, setup_logging
from app.crud import product as crud_product
from app.db.database import async_session_maker
from app.db.models.product import Brand, Product, ProductImage

setup_logging()
logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = PROJECT_ROOT / "data" / "imports"
SHOPMILL = "https://shopmilltools.com"
API = f"{SHOPMILL}/wp-json/wc/store/v1/products"
USER_AGENT = "Mozilla/5.0 (compatible; KarzarCatalogBot/1.0; +https://www.karzartools.com)"
MIN_BYTES = 8_000
PER_PAGE = 100

BRAND_CFG = {
    "terma": {
        "brand_ilike": "TERMA",
        "search_queries": ["ترما", "TERMA"],
        "out_dir": OUT_ROOT / "terma",
        "require_brand_tokens": ("ترما", "terma"),
    },
    "sanou": {
        "brand_ilike": "SAN OU",
        "search_queries": ["سانو", "SAN OU"],
        "out_dir": OUT_ROOT / "sanou",
        "require_brand_tokens": ("سانو", "san ou", "sanou"),
    },
    "astpower": {
        "brand_ilike": "ASTPOWER",
        "search_queries": ["ای اس تی پاور", "AST POWER"],
        "out_dir": OUT_ROOT / "astpower",
        "require_brand_tokens": ("ای اس تی", "ast power", "astpower", "ای.اس.تی"),
    },
    "dasqua": {
        "brand_ilike": "Dasqua",
        "search_queries": ["داسکوا", "Dasqua"],
        "out_dir": OUT_ROOT / "dasqua_shopmill",
        "require_brand_tokens": ("داسکوا", "dasqua"),
    },
}

MODEL_RE = re.compile(
    r"\b("
    r"\d{3,5}-\d{3,5}"
    r"|[A-Z]{1,6}\d{2,4}[A-Z]?(?:-[A-Z0-9]{1,10}){0,4}"
    r"|AST-[A-Z0-9/-]+"
    r"|D\d{2,4}"
    r"|00\d{4}"
    r"|K\d{1,2}-\d{2,4}"
    r")\b",
    re.IGNORECASE,
)


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def normalize_token(tok: str) -> str:
    return re.sub(r"\s+", "", tok.strip().upper().replace("ـ", ""))


def extract_models(text: str) -> list[str]:
    found = [normalize_token(m.group(1)) for m in MODEL_RE.finditer(text or "")]
    # Prefer longer / more specific tokens first when matching later
    return list(dict.fromkeys(sorted(found, key=len, reverse=True)))


def best_image(images: list[dict]) -> str | None:
    if not images:
        return None
    # Prefer largest declared size; fall back to first src
    ranked: list[tuple[int, str]] = []
    for img in images:
        src = (img.get("src") or "").strip()
        if not src.startswith("http"):
            continue
        w = int(img.get("width") or 0)
        h = int(img.get("height") or 0)
        ranked.append((w * h, src))
    if not ranked:
        return None
    ranked.sort(reverse=True)
    return ranked[0][1]


def upgrade_shopmill_url(url: str) -> str:
    """Prefer full-size uploads path if thumbnail-like suffixes appear."""
    # Woo often serves -300x300 etc; strip size suffixes before extension.
    return re.sub(r"-\d{2,4}x\d{2,4}(?=\.(?:jpg|jpeg|png|webp)$)", "", url, flags=re.I)


async def fetch_index(
    client: httpx.AsyncClient,
    queries: list[str],
    *,
    delay_s: float,
    cache_path: Path,
    refresh: bool,
) -> list[dict]:
    if cache_path.exists() and not refresh:
        return json.loads(cache_path.read_text(encoding="utf-8"))

    by_id: dict[int, dict] = {}
    for q in queries:
        page = 1
        while True:
            url = f"{API}?search={quote(q)}&per_page={PER_PAGE}&page={page}"
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.warning("shopmill search fail q=%s page=%s status=%s", q, page, resp.status_code)
                break
            batch = resp.json()
            if not isinstance(batch, list) or not batch:
                break
            for item in batch:
                pid = int(item.get("id") or 0)
                if not pid:
                    continue
                name = item.get("name") or ""
                img = best_image(item.get("images") or [])
                if img:
                    img = upgrade_shopmill_url(img)
                by_id[pid] = {
                    "id": pid,
                    "name": name,
                    "permalink": item.get("permalink") or "",
                    "sku": (item.get("sku") or "").strip(),
                    "image_url": img or "",
                    "models": extract_models(name),
                }
            total_pages = int(resp.headers.get("X-WP-TotalPages") or page)
            logger.info("shopmill q=%r page=%s/%s accumulated=%s", q, page, total_pages, len(by_id))
            if page >= total_pages:
                break
            page += 1
            await asyncio.sleep(delay_s)

    rows = list(by_id.values())
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return rows


def build_model_map(
    index: list[dict],
    require_brand_tokens: tuple[str, ...],
) -> tuple[dict[str, dict], dict[str, str]]:
    """model -> page; ambiguous models recorded separately."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    for page in index:
        name_l = (page.get("name") or "").lower()
        if not any(tok in name_l for tok in require_brand_tokens):
            continue
        if not page.get("image_url"):
            continue
        models = page.get("models") or extract_models(page.get("name") or "")
        for model in models:
            buckets[model].append(page)

    accepted: dict[str, dict] = {}
    ambiguous: dict[str, str] = {}
    for model, pages in buckets.items():
        urls = {p["image_url"] for p in pages}
        if len(urls) == 1:
            accepted[model] = pages[0]
            continue
        # Same product id variants OK
        ids = {p["id"] for p in pages}
        if len(ids) == 1:
            accepted[model] = pages[0]
            continue
        # Prefer the page whose title contains the model as a distinct token and
        # has the longest title match specificity (shorter name often = family hero).
        # Still ambiguous if image URLs differ across distinct products.
        ambiguous[model] = f"ambiguous_images:{len(urls)}:pages:{len(ids)}"
    return accepted, ambiguous


def find_by_sku_in_title(
    index: list[dict],
    sku: str,
    require_brand_tokens: tuple[str, ...],
) -> dict | None:
    """Highest confidence: catalog SKU appears in shopmill title."""
    sku_raw = sku.strip()
    if len(sku_raw) < 4:
        return None
    pat = re.compile(rf"(?<![A-Za-z0-9]){re.escape(sku_raw)}(?![A-Za-z0-9])", re.I)
    hits: list[dict] = []
    for page in index:
        name = page.get("name") or ""
        name_l = name.lower()
        if not any(tok in name_l for tok in require_brand_tokens):
            continue
        if not page.get("image_url"):
            continue
        if pat.search(name):
            hits.append(page)
    if not hits:
        return None
    urls = {p["image_url"] for p in hits}
    if len(urls) > 1 and len({p["id"] for p in hits}) > 1:
        return None
    return hits[0]


def catalog_match_keys(sku: str, name: str, brand_key: str) -> list[str]:
    keys: list[str] = []
    sku_n = normalize_token(sku)
    if brand_key == "sanou" and sku_n.startswith("SO-"):
        # Internal distributor id — do not use as model
        pass
    else:
        keys.append(sku_n)
    keys.extend(extract_models(f"{sku} {name}"))
    # AST numeric-only: try models from name only
    return list(dict.fromkeys([k for k in keys if k]))


async def probe_bytes(client: httpx.AsyncClient, url: str) -> int:
    try:
        resp = await client.head(url)
        size = int(resp.headers.get("content-length") or 0)
        if resp.status_code == 200 and size >= MIN_BYTES:
            return size
        if resp.status_code in {403, 405, 501} or size == 0:
            resp = await client.get(url, headers={"Range": "bytes=0-1023"})
            if resp.status_code in {200, 206}:
                cr = resp.headers.get("content-range", "")
                if "/" in cr:
                    try:
                        return int(cr.rsplit("/", 1)[-1])
                    except ValueError:
                        pass
                if resp.status_code == 200:
                    return len(resp.content)
    except Exception as exc:  # noqa: BLE001
        logger.debug("probe fail %s: %s", url, type(exc).__name__)
    return 0


async def run(
    *,
    brand_key: str,
    dry_run: bool,
    refresh_index: bool,
    replace_missing_only: bool,
    delay_s: float,
    limit: int | None,
) -> None:
    cfg = BRAND_CFG[brand_key]
    out_dir: Path = cfg["out_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    index_path = out_dir / "shopmill_index.json"
    imported_csv = out_dir / "imported.csv"
    rejected_csv = out_dir / "rejected.csv"
    started = time.time()

    async with httpx.AsyncClient(
        timeout=45.0,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
        limits=httpx.Limits(max_connections=8, max_keepalive_connections=4),
    ) as client:
        index = await fetch_index(
            client,
            list(cfg["search_queries"]),
            delay_s=delay_s,
            cache_path=index_path,
            refresh=refresh_index,
        )
        accepted, ambiguous = build_model_map(index, tuple(cfg["require_brand_tokens"]))
        logger.info(
            "index=%s accepted_models=%s ambiguous=%s",
            len(index),
            len(accepted),
            len(ambiguous),
        )

        imported_rows: list[dict[str, str]] = []
        rejected_rows: list[dict[str, str]] = []
        inserted = 0
        skipped_existing = 0

        async with async_session_maker() as session:
            brand_id = (
                await session.execute(
                    select(Brand.id).where(Brand.name.ilike(f"%{cfg['brand_ilike']}%")).limit(1)
                )
            ).scalar_one()
            products = list(
                (
                    await session.execute(
                        select(Product.id, Product.sku, Product.name)
                        .where(Product.brand_id == brand_id)
                        .where(Product.deleted_at.is_(None))
                        .order_by(Product.id)
                    )
                ).all()
            )
            if limit:
                products = products[:limit]

            existing_primary = set(
                (
                    await session.execute(
                        select(ProductImage.product_id).where(
                            ProductImage.product_id.in_([p.id for p in products]),
                            ProductImage.is_primary.is_(True),
                        )
                    )
                )
                .scalars()
                .all()
            )

            for product_id, sku, name in products:
                if product_id in existing_primary and replace_missing_only:
                    skipped_existing += 1
                    rejected_rows.append(
                        {
                            "sku": sku,
                            "product_name": name or "",
                            "issue_codes": "already_has_primary",
                            "issue_fa": "از قبل عکس اصلی دارد",
                            "detail_url": "",
                            "image_url": "",
                        }
                    )
                    continue

                keys = catalog_match_keys(sku, name or "", brand_key)
                hit = None
                used_key = ""

                # 1) Exact SKU in shopmill title (best)
                if not (brand_key == "sanou" and normalize_token(sku).startswith("SO-")):
                    hit = find_by_sku_in_title(
                        index, sku, tuple(cfg["require_brand_tokens"])
                    )
                    if hit:
                        used_key = f"sku_title:{normalize_token(sku)}"

                # 2) Model-token map
                if not hit:
                    for key in keys:
                        if key in ambiguous:
                            continue
                        if key in accepted:
                            hit = accepted[key]
                            used_key = key
                            break

                if not hit:
                    reason = "no_shopmill_model_match"
                    if any(k in ambiguous for k in keys):
                        reason = "ambiguous_shopmill_model"
                    rejected_rows.append(
                        {
                            "sku": sku,
                            "product_name": name or "",
                            "issue_codes": reason,
                            "issue_fa": "مدل در ایندکس شاپ‌میل پیدا نشد / مبهم بود",
                            "detail_url": "",
                            "image_url": "",
                        }
                    )
                    continue

                image_url = hit["image_url"]
                size = await probe_bytes(client, image_url)
                await asyncio.sleep(delay_s)
                if size < MIN_BYTES:
                    rejected_rows.append(
                        {
                            "sku": sku,
                            "product_name": name or "",
                            "issue_codes": "image_too_small_or_missing",
                            "issue_fa": f"حجم تصویر ناکافی ({size}B)",
                            "detail_url": hit.get("permalink") or "",
                            "image_url": image_url,
                        }
                    )
                    continue

                imported_rows.append(
                    {
                        "sku": sku,
                        "product_name": name or "",
                        "image_url": image_url,
                        "detail_url": hit.get("permalink") or "",
                        "confidence": "very_high",
                        "match_key": used_key,
                        "bytes": str(size),
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
                            "issue_fa": str(exc)[:200],
                            "detail_url": hit.get("permalink") or "",
                            "image_url": image_url,
                        }
                    )

            if not dry_run:
                await session.commit()

    write_csv(
        imported_csv,
        imported_rows,
        ["sku", "product_name", "image_url", "detail_url", "confidence", "match_key", "bytes"],
    )
    write_csv(
        rejected_csv,
        rejected_rows,
        ["sku", "product_name", "issue_codes", "issue_fa", "detail_url", "image_url"],
    )
    elapsed = int(time.time() - started)
    print(f"=== shopmill image import: {brand_key} ===")
    print(f"Mode: {'dry-run' if dry_run else 'live'} replace_missing_only={replace_missing_only}")
    print(f"Index pages: {len(index)} accepted_models={len(accepted)} ambiguous={len(ambiguous)}")
    print(f"Inserted/matched: {inserted}")
    print(f"Skipped existing: {skipped_existing}")
    print(f"Rejected rows: {len(rejected_rows)}")
    print(f"Elapsed: {elapsed}s")
    print(f"Imported: {imported_csv}")
    print(f"Rejected: {rejected_csv}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand", required=True, choices=sorted(BRAND_CFG))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--refresh-index", action="store_true")
    parser.add_argument(
        "--replace-missing-only",
        action="store_true",
        default=True,
        help="Skip products that already have a primary image (default)",
    )
    parser.add_argument(
        "--also-existing",
        action="store_true",
        help="Attempt products that already have a primary (still inserts only if CRUD allows)",
    )
    parser.add_argument("--delay", type=float, default=0.08)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    replace_missing_only = not args.also_existing
    asyncio.run(
        run(
            brand_key=args.brand,
            dry_run=args.dry_run,
            refresh_index=args.refresh_index,
            replace_missing_only=replace_missing_only,
            delay_s=args.delay,
            limit=args.limit,
        )
    )


if __name__ == "__main__":
    main()
