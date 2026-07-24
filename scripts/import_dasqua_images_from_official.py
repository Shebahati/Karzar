#!/usr/bin/env python3
"""Import Dasqua product images from dasquatools.com (official), very-high SKU match only.

Pipeline:
  1) Load product URLs from sitemap cache (or refresh).
  2) Crawl pages; extract primary CODE + best image_product/og:image.
  3) Map CODE -> image; ambiguous codes skipped.
  4) Match catalog Dasqua SKUs exactly (NNNN-NNNN).
  5) Insert primary image URLs (materialize separately to disk).

Usage:
  .venv/bin/python scripts/import_dasqua_images_from_official.py --dry-run
  .venv/bin/python scripts/import_dasqua_images_from_official.py
  .venv/bin/python scripts/import_dasqua_images_from_official.py --refresh-sitemap --limit 50
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

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
OUT_DIR = PROJECT_ROOT / "data" / "imports" / "dasqua"
URL_CACHE = OUT_DIR / "product_urls.txt"
IMPORTED_CSV = OUT_DIR / "phase2_imported.csv"
REJECTED_CSV = OUT_DIR / "phase2_rejected.csv"
INDEX_CSV = OUT_DIR / "phase2_site_index.csv"

SITE = "https://www.dasquatools.com"
SITEMAPS = [
    f"{SITE}/product_sitemap.xml",
    f"{SITE}/product_2_sitemap.xml",
    f"{SITE}/product_3_sitemap.xml",
]
USER_AGENT = "Mozilla/5.0 (compatible; KarzarCatalogBot/1.0; +https://www.karzartools.com)"

CODE_RE = re.compile(r"\b(\d{3,5}-\d{3,5})(?:-[A-Za-z0-9]+|[A-Za-z])?\b")
TITLE_DASQUA_RE = re.compile(
    r"Dasqua\s+(\d{3,5}-\d{3,5})(?:-[A-Za-z0-9]+|[A-Za-z])?\b",
    re.IGNORECASE,
)
ITEM_NUMBER_RE = re.compile(
    r"(?:Item\s*Number|Item\s*No\.?|Order\s*No\.?|Art\.?\s*No\.?|Product\s*No\.?)\s*[:：]\s*"
    r"(\d{3,5}-\d{3,5})(?:-[A-Za-z0-9]+|[A-Za-z])?\b",
    re.IGNORECASE,
)
OG_IMAGE_RE = re.compile(
    r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']|'
    r'content=["\']([^"\']+)["\']\s+property=["\']og:image["\']',
    re.IGNORECASE,
)
IMAGE_PRODUCT_RE = re.compile(
    r"https://[^\"'\s]+image_product[^\"'\s]+\.(?:png|jpg|jpeg|webp)",
    re.IGNORECASE,
)


@dataclass
class PageExtract:
    url: str
    primary_code: str | None = None
    image_url: str | None = None
    title: str = ""
    issues: list[str] = field(default_factory=list)


def normalize_code(raw: str) -> str:
    """Strip trailing letter / -A style suffix → NNNN-NNNN catalog form when possible."""
    raw = raw.strip().upper()
    m = re.match(r"^(\d{3,5}-\d{3,5})", raw)
    return m.group(1) if m else raw


def refresh_sitemap_urls() -> list[str]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    urls: list[str] = []
    for sm in SITEMAPS:
        req = Request(sm, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=90) as resp:  # noqa: S310 — fixed official host
            xml = resp.read().decode("utf-8", "ignore")
        locs = re.findall(r"<loc>([^<]+)</loc>", xml)
        urls.extend(locs)
        logger.info("sitemap %s -> %s urls", sm, len(locs))
    deduped = list(dict.fromkeys(urls))
    URL_CACHE.write_text("\n".join(deduped) + "\n", encoding="utf-8")
    return deduped


def load_urls() -> list[str]:
    if not URL_CACHE.exists():
        return refresh_sitemap_urls()
    return [u.strip() for u in URL_CACHE.read_text(encoding="utf-8").splitlines() if u.strip()]


def extract_primary_code(title: str, url: str, html: str = "") -> str | None:
    # Highest confidence: explicit Item Number on the product page.
    if html:
        labeled = [normalize_code(c) for c in ITEM_NUMBER_RE.findall(html)]
        labeled = list(dict.fromkeys(labeled))
        if len(labeled) == 1:
            return labeled[0]
        if len(labeled) > 1:
            # Multiple item numbers usually means a family table — only accept if
            # title/slug already points to one of them.
            pass

    m = TITLE_DASQUA_RE.search(title)
    if m:
        return normalize_code(m.group(1))
    title_codes = [normalize_code(c) for c in CODE_RE.findall(title)]
    title_codes = list(dict.fromkeys(title_codes))
    if len(title_codes) == 1:
        return title_codes[0]

    path = unquote(urlparse(url).path).lower()
    m2 = re.search(r"dasqua-(\d{3,5}-\d{3,5})", path)
    if m2:
        return normalize_code(m2.group(1))
    slug_codes = [normalize_code(c) for c in CODE_RE.findall(path)]
    slug_codes = list(dict.fromkeys(slug_codes))
    if len(slug_codes) == 1:
        return slug_codes[0]

    if html:
        labeled = [normalize_code(c) for c in ITEM_NUMBER_RE.findall(html)]
        labeled = list(dict.fromkeys(labeled))
        if labeled:
            # If family table, prefer code that also appears in URL/title when possible.
            for code in labeled:
                if code.lower() in path or code in title:
                    return code
            if len(labeled) == 1:
                return labeled[0]
    return None


def extract_image(html: str) -> str | None:
    og = None
    m = OG_IMAGE_RE.search(html)
    if m:
        og = m.group(1) or m.group(2)
    if og and "image_product" in og:
        return og
    imgs = list(dict.fromkeys(IMAGE_PRODUCT_RE.findall(html)))
    if imgs:
        return imgs[0]
    return og


def parse_page(url: str, html: str) -> PageExtract:
    title_m = re.search(r"<title>([^<]+)", html, re.IGNORECASE)
    title = title_m.group(1).strip() if title_m else ""
    code = extract_primary_code(title, url, html)
    image = extract_image(html)
    page = PageExtract(url=url, primary_code=code, image_url=image, title=title)
    if not code:
        page.issues.append("no_primary_code")
    if not image:
        page.issues.append("no_product_image")
    return page


async def fetch(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        # httpx handles unicode URLs better than urllib
        resp = await client.get(url, follow_redirects=True)
        if resp.status_code != 200:
            return None
        return resp.text
    except Exception as exc:  # noqa: BLE001
        logger.warning("fetch failed %s: %s", url[-80:], type(exc).__name__)
        return None


async def crawl_index(
    urls: list[str],
    *,
    concurrency: int,
    delay_s: float,
) -> list[PageExtract]:
    sem = asyncio.Semaphore(concurrency)
    results: list[PageExtract] = []

    async with httpx.AsyncClient(
        timeout=45.0,
        headers={"User-Agent": USER_AGENT},
        limits=httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency),
    ) as client:

        async def one(url: str) -> PageExtract:
            async with sem:
                html = await fetch(client, url)
                await asyncio.sleep(delay_s)
                if not html:
                    return PageExtract(url=url, issues=["fetch_failed"])
                return parse_page(url, html)

        # chunk progress
        for i in range(0, len(urls), 50):
            chunk = urls[i : i + 50]
            batch = await asyncio.gather(*[one(u) for u in chunk])
            results.extend(batch)
            ok = sum(1 for p in batch if p.primary_code and p.image_url)
            logger.info(
                "crawl progress %s/%s chunk_ok=%s",
                min(i + 50, len(urls)),
                len(urls),
                ok,
            )
    return results


def build_code_map(
    pages: list[PageExtract],
) -> tuple[dict[str, tuple[str, str, str]], dict[str, str]]:
    """Return code -> (image_url, detail_url, title), and ambiguous reasons."""
    from collections import Counter

    buckets: dict[str, list[PageExtract]] = {}
    for page in pages:
        if not page.primary_code or not page.image_url or page.issues:
            continue
        buckets.setdefault(page.primary_code, []).append(page)

    accepted: dict[str, tuple[str, str, str]] = {}
    ambiguous: dict[str, str] = {}
    for code, group in buckets.items():
        img_counts = Counter(p.image_url for p in group)
        top_img, top_n = img_counts.most_common(1)[0]
        # Accept majority image (or unanimous / single).
        if top_n == 1 and len(img_counts) > 1:
            # No majority — try prefer URL containing the code.
            coded = [p for p in group if code.lower() in p.url.lower()]
            if len({p.image_url for p in coded}) == 1:
                pick = min(coded, key=lambda p: len(p.url))
                accepted[code] = (pick.image_url or "", pick.url, pick.title)
                continue
            ambiguous[code] = f"ambiguous_images:{len(img_counts)}"
            continue

        cands = [p for p in group if p.image_url == top_img]

        def score(p: PageExtract) -> tuple[int, int]:
            path = p.url.lower()
            in_url = 1 if code.lower() in path else 0
            # Prefer shorter canonical-ish URLs over long SEO doorways.
            return (in_url, -len(path))

        pick = max(cands, key=score)
        accepted[code] = (pick.image_url or "", pick.url, pick.title)
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
    refresh_sitemap: bool,
    limit: int | None,
    concurrency: int,
    delay_s: float,
) -> None:
    if refresh_sitemap or not URL_CACHE.exists():
        urls = refresh_sitemap_urls()
    else:
        urls = load_urls()
    if limit:
        urls = urls[:limit]

    started = time.time()
    pages = await crawl_index(urls, concurrency=concurrency, delay_s=delay_s)
    accepted, ambiguous = build_code_map(pages)

    index_rows = []
    for code, (image, detail, title) in sorted(accepted.items()):
        index_rows.append(
            {
                "code": code,
                "image_url": image,
                "detail_url": detail,
                "title": title,
                "status": "accepted",
            }
        )
    for code, reason in sorted(ambiguous.items()):
        index_rows.append(
            {
                "code": code,
                "image_url": "",
                "detail_url": "",
                "title": "",
                "status": reason,
            }
        )
    write_csv(
        INDEX_CSV,
        index_rows,
        ["code", "image_url", "detail_url", "title", "status"],
    )

    imported_rows: list[dict[str, str]] = []
    rejected_rows: list[dict[str, str]] = []
    inserted = 0

    async with async_session_maker() as session:
        brand_id = (
            await session.execute(
                select(Brand.id).where(Brand.name.ilike("%Dasqua%")).limit(1)
            )
        ).scalar_one()
        result = await session.execute(
            select(Product.id, Product.sku, Product.name)
            .where(Product.brand_id == brand_id)
            .where(Product.deleted_at.is_(None))
            .order_by(Product.id)
        )
        products = list(result.all())

        # existing images
        existing_ids = set(
            (
                await session.execute(
                    select(ProductImage.product_id).where(
                        ProductImage.product_id.in_([p.id for p in products])
                    )
                )
            )
            .scalars()
            .all()
        )

        for product_id, sku, name in products:
            code = normalize_code(sku)
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
                        "issue_fa": "کد در چند صفحه با عکس‌های متفاوت",
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
                        "issue_fa": "کد در سایت رسمی پیدا نشد / بدون کد صفحه",
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
    print("=== Dasqua image import summary ===")
    print(f"Mode: {'dry-run' if dry_run else 'live'}")
    print(f"Pages crawled: {len(pages)}")
    print(f"Official codes accepted: {len(accepted)}")
    print(f"Official codes ambiguous: {len(ambiguous)}")
    print(f"Catalog matched / inserted: {inserted}")
    print(f"Rejected / skipped: {len(rejected_rows)}")
    print(f"Elapsed: {elapsed}s")
    print(f"Imported CSV: {IMPORTED_CSV}")
    print(f"Rejected CSV: {REJECTED_CSV}")
    print(f"Site index CSV: {INDEX_CSV}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--refresh-sitemap", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=12)
    parser.add_argument("--delay", type=float, default=0.05)
    args = parser.parse_args()
    asyncio.run(
        run(
            dry_run=args.dry_run,
            refresh_sitemap=args.refresh_sitemap,
            limit=args.limit,
            concurrency=args.concurrency,
            delay_s=args.delay,
        )
    )


if __name__ == "__main__":
    main()
