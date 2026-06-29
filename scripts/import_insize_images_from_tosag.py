"""
Import INSIZE product images from tosag.ch with very-high-confidence matching.

Only inserts images when the exact SKU is confirmed on the product detail page
(variation list or single-SKU header) and the page is an Insize item.

Rejected / uncertain rows -> data/imports/insize_images_not_imported.xlsx

Usage:
    .venv/bin/python scripts/import_insize_images_from_tosag.py
    .venv/bin/python scripts/import_insize_images_from_tosag.py --dry-run --limit 10
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

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select

from app.core.logging import get_logger, setup_logging
from app.crud import product as crud_product
from app.db.database import async_session_maker
from app.db.models.product import Product, ProductImage

setup_logging()
logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "imports"
DEFAULT_REJECTED_XLSX = OUTPUT_DIR / "insize_images_not_imported.xlsx"
DEFAULT_REJECTED_CSV = OUTPUT_DIR / "insize_images_not_imported.csv"
DEFAULT_IMPORTED_CSV = OUTPUT_DIR / "insize_images_imported.csv"

TOSAG_BASE = "https://www.tosag.ch"
INSIZE_BRAND_ID = 3
USER_AGENT = (
    "Mozilla/5.0 (compatible; KarzarCatalogBot/1.0; +https://karzar.local/image-import)"
)

REASON_FA: dict[str, str] = {
    "fetch_search_failed": "صفحه جستجو بارگذاری نشد",
    "no_product_candidates": "هیچ صفحه محصولی در نتایج جستجو نبود",
    "fetch_detail_failed": "صفحه جزئیات محصول بارگذاری نشد",
    "not_insize_manufacturer": "سازنده Insize در صفحه تأیید نشد",
    "sku_not_on_detail_page": "SKU دقیق در لیست variations / هدر محصول نیست",
    "no_product_image": "عکس محصول در صفحه جزئیات یافت نشد",
    "already_has_primary_image": "از قبل عکس اصلی دارد",
    "image_url_too_long": "آدرس عکس از حد مجاز دیتابیس طولانی‌تر است",
    "db_error": "خطا هنگام ثبت در دیتابیس",
}

SKIP_LINK_PARTS = (
    "homepage",
    "Register",
    "Forgot-password",
    "Impressum",
    "Privacy",
    "rss.xml",
    "templates/",
    "plugins/",
)


@dataclass
class MatchResult:
    sku: str
    product_id: int
    product_name: str
    confidence: str
    image_url: str | None = None
    detail_url: str | None = None
    issues: list[str] = field(default_factory=list)

    @property
    def eligible(self) -> bool:
        return self.confidence == "very_high" and bool(self.image_url) and not self.issues

    def issues_fa(self) -> str:
        return "؛ ".join(REASON_FA.get(code, code) for code in self.issues)


def clean_html_text(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text)


def extract_search_product_links(html: str) -> list[str]:
    links: list[str] = []
    for block in re.split(r'id="result-wrapper_buy_form_', html)[1:]:
        if "Insize" not in block and "INSIZE" not in block:
            continue
        match = re.search(
            r'class="productbox-title[^"]*"[^>]*>\s*<a href="(https://www\.tosag\.ch/[^"?#]+)"',
            block,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            links.append(match.group(1))
    if not links:
        for match in re.finditer(
            r'class="productbox-title[^"]*"[^>]*>\s*<a href="(https://www\.tosag\.ch/[^"?#]+)"',
            html,
            re.IGNORECASE | re.DOTALL,
        ):
            links.append(match.group(1))
    deduped: list[str] = []
    seen: set[str] = set()
    for link in links:
        if any(part in link for part in SKIP_LINK_PARTS):
            continue
        if link not in seen:
            seen.add(link)
            deduped.append(link)
    return deduped[:8]


def is_insize_detail_page(html: str) -> bool:
    if re.search(r"Manufacturers:\s*</[^>]+>\s*Insize", html, re.IGNORECASE):
        return True
    if re.search(r"Manufacturers:.*?Insize", clean_html_text(html), re.IGNORECASE):
        return True
    if re.search(r"itemprop=\"brand\"[^>]*>.*?Insize", html, re.IGNORECASE | re.DOTALL):
        return True
    return bool(re.search(r"\bINSIZE\b", html) and "Measuring" in html)


def sku_confirmed_on_detail(html: str, sku: str) -> bool:
    patterns = [
        rf">\s*{re.escape(sku)}\s*-",
        rf"(?:^|[\s\-])\s*{re.escape(sku)}\s*-",
        rf"SKU:\s*{re.escape(sku)}\b",
        rf"data-sku-\d+=\"{re.escape(sku)}\"",
    ]
    return any(re.search(pattern, html, re.IGNORECASE) for pattern in patterns)


def extract_primary_image(html: str) -> str | None:
    images = re.findall(
        r"https://www\.tosag\.ch/media/image/product/\d+/lg/[^\"'\s>]+\.jpg",
        html,
    )
    if not images:
        images = re.findall(
            r"https://www\.tosag\.ch/media/image/product/\d+/md/[^\"'\s>]+\.jpg",
            html,
        )
    if not images:
        return None
    unique = sorted(set(images), key=lambda url: ("~2" in url, url))
    return unique[0]


async def fetch_text(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as exc:
        logger.warning("HTTP error for %s: %s", url, exc)
        return None


async def resolve_image_for_sku(
    client: httpx.AsyncClient,
    sku: str,
    *,
    delay_s: float,
) -> MatchResult:
    result = MatchResult(sku=sku, product_id=0, product_name="", confidence="rejected")

    search_url = f"{TOSAG_BASE}/?suche={sku}&lang=eng"
    search_html = await fetch_text(client, search_url)
    await asyncio.sleep(delay_s)
    if not search_html:
        result.issues.append("fetch_search_failed")
        return result

    candidates = extract_search_product_links(search_html)
    if not candidates:
        result.issues.append("no_product_candidates")
        return result

    for detail_url in candidates:
        detail_html = await fetch_text(client, f"{detail_url}?lang=eng")
        await asyncio.sleep(delay_s)
        if not detail_html:
            result.issues.append("fetch_detail_failed")
            continue
        if not is_insize_detail_page(detail_html):
            result.issues.append("not_insize_manufacturer")
            continue
        if not sku_confirmed_on_detail(detail_html, sku):
            result.issues.append("sku_not_on_detail_page")
            continue
        image_url = extract_primary_image(detail_html)
        if not image_url:
            result.issues.append("no_product_image")
            continue

        result.confidence = "very_high"
        result.image_url = image_url
        result.detail_url = detail_url
        result.issues = []
        return result

    if not result.issues:
        result.issues.append("sku_not_on_detail_page")
    return result


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_rejected_xlsx(path: Path, rows: list[dict[str, str]]) -> bool:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font
    except ImportError:
        logger.warning("openpyxl not installed; skipping XLSX export")
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "عکس وارد نشد"
    ws.sheet_view.rightToLeft = True

    headers = [
        "SKU",
        "نام محصول",
        "کدهای نقص",
        "شرح نقص (فارسی)",
        "آدرس جستجو",
        "آدرس صفحه محصول",
        "آدرس عکس پیشنهادی",
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    for row in rows:
        ws.append(
            [
                row.get("sku", ""),
                row.get("product_name", ""),
                row.get("issue_codes", ""),
                row.get("issue_fa", ""),
                row.get("search_url", ""),
                row.get("detail_url", ""),
                row.get("image_url", ""),
            ]
        )

    for column in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in column)
        ws.column_dimensions[column[0].column_letter].width = min(max_len + 2, 70)

    wb.save(path)
    return True


async def run_import(
    *,
    dry_run: bool,
    limit: int | None,
    delay_s: float,
    force: bool,
) -> tuple[int, int, list[dict[str, str]], list[dict[str, str]]]:
    imported_rows: list[dict[str, str]] = []
    rejected_rows: list[dict[str, str]] = []
    inserted = 0

    async with async_session_maker() as session:
        stmt = (
            select(Product.id, Product.sku, Product.name)
            .where(Product.brand_id == INSIZE_BRAND_ID, Product.deleted_at.is_(None))
            .order_by(Product.sku)
        )
        if limit:
            stmt = stmt.limit(limit)
        products = (await session.execute(stmt)).all()

        existing_primary: set[int] = set()
        if not force:
            existing_primary = set(
                (
                    await session.execute(
                        select(ProductImage.product_id).where(ProductImage.is_primary.is_(True))
                    )
                ).scalars()
            )

        timeout = httpx.Timeout(60.0, connect=20.0)
        async with httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
        ) as client:
            for index, (product_id, sku, name) in enumerate(products):
                if product_id in existing_primary:
                    rejected_rows.append(
                        {
                            "sku": sku,
                            "product_name": name,
                            "issue_codes": "already_has_primary_image",
                            "issue_fa": REASON_FA["already_has_primary_image"],
                            "search_url": f"{TOSAG_BASE}/?suche={sku}&lang=eng",
                            "detail_url": "",
                            "image_url": "",
                        }
                    )
                    continue

                if index:
                    await asyncio.sleep(delay_s)

                match = await resolve_image_for_sku(client, sku, delay_s=delay_s)
                match.product_id = product_id
                match.product_name = name

                if not match.eligible:
                    rejected_rows.append(
                        {
                            "sku": sku,
                            "product_name": name,
                            "issue_codes": "|".join(match.issues),
                            "issue_fa": match.issues_fa(),
                            "search_url": f"{TOSAG_BASE}/?suche={sku}&lang=eng",
                            "detail_url": match.detail_url or "",
                            "image_url": match.image_url or "",
                        }
                    )
                    logger.info("Rejected %s: %s", sku, match.issues_fa())
                    continue

                if len(match.image_url or "") > 500:
                    rejected_rows.append(
                        {
                            "sku": sku,
                            "product_name": name,
                            "issue_codes": "image_url_too_long",
                            "issue_fa": REASON_FA["image_url_too_long"],
                            "search_url": f"{TOSAG_BASE}/?suche={sku}&lang=eng",
                            "detail_url": match.detail_url or "",
                            "image_url": match.image_url or "",
                        }
                    )
                    continue

                imported_rows.append(
                    {
                        "sku": sku,
                        "product_name": name,
                        "image_url": match.image_url or "",
                        "detail_url": match.detail_url or "",
                        "confidence": match.confidence,
                    }
                )

                if dry_run:
                    inserted += 1
                    continue

                try:
                    await crud_product.add_product_image(
                        session,
                        product_id,
                        match.image_url or "",
                        is_primary=True,
                    )
                    inserted += 1
                except Exception as exc:
                    logger.exception("DB error for %s", sku)
                    rejected_rows.append(
                        {
                            "sku": sku,
                            "product_name": name,
                            "issue_codes": "db_error",
                            "issue_fa": f"{REASON_FA['db_error']}: {exc}",
                            "search_url": f"{TOSAG_BASE}/?suche={sku}&lang=eng",
                            "detail_url": match.detail_url or "",
                            "image_url": match.image_url or "",
                        }
                    )

        if not dry_run:
            await session.commit()

    return inserted, len(rejected_rows), imported_rows, rejected_rows


async def main() -> None:
    parser = argparse.ArgumentParser(description="Import INSIZE images from tosag.ch")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between requests")
    parser.add_argument("--force", action="store_true", help="Replace even if primary image exists")
    parser.add_argument("--rejected-xlsx", type=Path, default=DEFAULT_REJECTED_XLSX)
    parser.add_argument("--rejected-csv", type=Path, default=DEFAULT_REJECTED_CSV)
    parser.add_argument("--imported-csv", type=Path, default=DEFAULT_IMPORTED_CSV)
    args = parser.parse_args()

    started = time.time()
    inserted, rejected_count, imported_rows, rejected_rows = await run_import(
        dry_run=args.dry_run,
        limit=args.limit,
        delay_s=args.delay,
        force=args.force,
    )

    write_csv(
        args.imported_csv,
        imported_rows,
        ["sku", "product_name", "image_url", "detail_url", "confidence"],
    )
    write_csv(
        args.rejected_csv,
        rejected_rows,
        [
            "sku",
            "product_name",
            "issue_codes",
            "issue_fa",
            "search_url",
            "detail_url",
            "image_url",
        ],
    )
    xlsx_ok = write_rejected_xlsx(args.rejected_xlsx, rejected_rows)

    elapsed = int(time.time() - started)
    print("=== INSIZE image import summary ===")
    print(f"Mode: {'dry-run' if args.dry_run else 'live'}")
    print(f"Very-high imported: {inserted}")
    print(f"Rejected / skipped: {rejected_count}")
    print(f"Elapsed: {elapsed}s")
    print(f"Imported CSV: {args.imported_csv}")
    print(f"Rejected CSV: {args.rejected_csv}")
    if xlsx_ok:
        print(f"Rejected XLSX: {args.rejected_xlsx}")


if __name__ == "__main__":
    asyncio.run(main())
