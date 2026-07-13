"""
Import price-list CSV rows into the products table.

Only rows that pass strict quality checks are inserted. Rejected rows are
written to data/imports/products_not_imported.xlsx with Persian deficiency notes.

Usage (Docker):
    docker compose exec app python scripts/seed_products_from_csv.py

Local:
    python scripts/seed_products_from_csv.py
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.logging import get_logger, setup_logging
from app.db.database import async_session_maker
from app.db.models.product import Brand, Category, Product, StockUnitEnum
from app.utils.slugify import slugify
from app.utils.specifications import specifications_for_storage

setup_logging()
logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = PROJECT_ROOT / "data" / "imports" / "all_products.csv"
DEFAULT_REJECTED_XLSX = PROJECT_ROOT / "data" / "imports" / "products_not_imported.xlsx"
DEFAULT_REJECTED_CSV = PROJECT_ROOT / "data" / "imports" / "products_not_imported.csv"

BLOCKING_FLAGS = {
    "missing_price",
    "price_parse_failed",
    "inquiry_price",
    "duplicate_sku_in_pdf",
    "duplicate_sku_merged",
    "weak_name",
    "category_unmapped",
    "category_fallback",
    "multiple_sku_on_line",
    "size_corrected",
}

ISSUE_LABELS_FA: dict[str, str] = {
    "sku_missing": "کد کالا (SKU) در CSV خالی است",
    "name_invalid": "نام محصول خالی یا خیلی کوتاه است",
    "category_missing": "دسته‌بندی مشخص نشده",
    "brand_missing": "برند مشخص نشده",
    "price_missing": "قیمت معتبر (بیش از صفر) وجود ندارد",
    "missing_price": "قیمت در PDF استخراج نشد",
    "inquiry_price": "قیمت استعلامی است — عدد قطعی در PDF نیست",
    "duplicate_sku_in_pdf": "این SKU چند بار در PDF آمده — احتمال تداخل قیمت/مشخصات",
    "duplicate_sku_merged": "SKU تکراری در PDF ادغام شده — برای واردسازی قطعی مناسب نیست",
    "weak_name": "نام محصول ناقص است — توضیح کافی در PDF نیست",
    "category_unmapped": "دسته‌بندی از متن PDF قابل تشخیص نبود",
    "category_fallback": "دسته‌بندی با حدس به «قطعات یدکی» نسبت داده شد",
    "category_low_confidence": "دسته‌بندی با اطمینان پایین تشخیص داده شد",
    "multiple_sku_on_line": "چند SKU در یک خط PDF — استخراج مبهم",
    "size_corrected": "بازه اندازه از PDF ناقص بود و اصلاح شده — برای واردسازی ۱۰۰٪ قطعی نیست",
    "category_not_in_db": "شناسه دسته در دیتابیس وجود ندارد",
    "category_not_selectable": "دسته انتخاب‌پذیر نیست (باید زیردسته سطح ۲ باشد)",
    "brand_not_in_db": "شناسه برند در دیتابیس وجود ندارد",
    "sku_exists_in_db": "این SKU از قبل در دیتابیس ثبت شده",
    "sku_duplicate_in_csv": "این SKU در CSV بیش از یک بار آمده (احتمالاً برندهای مختلف) — یکتا نیست",
}


@dataclass
class ImportRow:
    data: dict[str, str]
    issues: list[str]

    @property
    def eligible(self) -> bool:
        return not self.issues

    def issues_fa(self) -> str:
        labels = [ISSUE_LABELS_FA.get(code, code) for code in self.issues]
        return "؛ ".join(labels)


def parse_flags(row: dict[str, str]) -> set[str]:
    return {flag for flag in row.get("parse_flags", "").split("|") if flag}


def parse_price_toman(row: dict[str, str]) -> Decimal | None:
    raw = (row.get("base_price_toman") or "").strip()
    if not raw:
        return None
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None
    if value <= 0:
        return None
    return value


def classify_rows(rows: list[dict[str, str]]) -> list[ImportRow]:
    sku_counts: dict[str, int] = {}
    for row in rows:
        sku = (row.get("sku") or "").strip()
        if sku:
            sku_counts[sku] = sku_counts.get(sku, 0) + 1

    classified: list[ImportRow] = []
    for row in rows:
        issues = assess_row(row)
        sku = (row.get("sku") or "").strip()
        if sku and sku_counts.get(sku, 0) > 1 and "sku_duplicate_in_csv" not in issues:
            issues.append("sku_duplicate_in_csv")
        classified.append(ImportRow(data=row, issues=issues))
    return classified


def assess_row(row: dict[str, str]) -> list[str]:
    issues: list[str] = []

    sku = (row.get("sku") or "").strip()
    name = (row.get("name") or "").strip()
    if not sku:
        issues.append("sku_missing")
    if not name or len(name) < 5:
        issues.append("name_invalid")
    if not (row.get("category_id") or "").strip():
        issues.append("category_missing")
    if not (row.get("brand_id") or "").strip():
        issues.append("brand_missing")

    if parse_price_toman(row) is None:
        issues.append("price_missing")

    flags = parse_flags(row)
    if "missing_price" in flags:
        issues.append("missing_price")
    if row.get("price_is_inquiry") == "true" or "inquiry_price" in flags:
        issues.append("inquiry_price")

    confidence = (row.get("category_confidence") or "").strip()
    if confidence in {"low", "fallback"}:
        issues.append("category_low_confidence")

    for flag in BLOCKING_FLAGS:
        if flag in flags and flag not in issues:
            issues.append(flag)

    return list(dict.fromkeys(issues))


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_specifications(raw: str) -> dict:
    if not raw.strip():
        return specifications_for_storage({})
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return specifications_for_storage({})
    if not isinstance(payload, dict):
        return specifications_for_storage({})
    return specifications_for_storage(payload)


def write_rejected_csv(path: Path, rejected: list[ImportRow]) -> None:
    fields = [
        "sku",
        "brand",
        "name",
        "category_name",
        "base_price_toman",
        "price_raw",
        "parse_flags",
        "deficiency_codes",
        "deficiency_fa",
        "source_file",
        "source_row_hint",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in rejected:
            row = item.data
            writer.writerow(
                {
                    "sku": row.get("sku", ""),
                    "brand": row.get("brand", ""),
                    "name": row.get("name", ""),
                    "category_name": row.get("category_name", ""),
                    "base_price_toman": row.get("base_price_toman", ""),
                    "price_raw": row.get("price_raw", ""),
                    "parse_flags": row.get("parse_flags", ""),
                    "deficiency_codes": "|".join(item.issues),
                    "deficiency_fa": item.issues_fa(),
                    "source_file": row.get("source_file", ""),
                    "source_row_hint": row.get("source_row_hint", ""),
                }
            )


def write_rejected_xlsx(path: Path, rejected: list[ImportRow]) -> bool:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font
    except ImportError:
        logger.warning("openpyxl not installed; skipping XLSX export")
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "وارد نشده"
    ws.sheet_view.rightToLeft = True

    headers = [
        "ردیف",
        "SKU",
        "برند",
        "نام",
        "دسته",
        "قیمت (تومان)",
        "قیمت خام PDF",
        "فلگ‌های پارس",
        "کدهای نقص",
        "شرح نقص (فارسی)",
        "فایل منبع",
        "محل در PDF",
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    for index, item in enumerate(rejected, start=1):
        row = item.data
        ws.append(
            [
                index,
                row.get("sku", ""),
                row.get("brand", ""),
                row.get("name", ""),
                row.get("category_name", ""),
                row.get("base_price_toman", ""),
                row.get("price_raw", ""),
                row.get("parse_flags", ""),
                "|".join(item.issues),
                item.issues_fa(),
                row.get("source_file", ""),
                row.get("source_row_hint", ""),
            ]
        )

    for column in ws.columns:
        max_len = 0
        column_letter = column[0].column_letter
        for cell in column:
            if cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[column_letter].width = min(max_len + 2, 60)

    wb.save(path)
    return True


async def import_products(
  csv_path: Path,
  *,
  dry_run: bool = False,
) -> tuple[list[ImportRow], list[ImportRow], int, int]:
    rows = load_csv_rows(csv_path)
    classified = classify_rows(rows)

    eligible = [item for item in classified if item.eligible]
    rejected = [item for item in classified if not item.eligible]

    inserted = 0
    skipped_existing = 0

    if dry_run:
        return eligible, rejected, inserted, skipped_existing

    async with async_session_maker() as session:
        category_ids = set(
            (
                await session.execute(
                    select(Category.id).where(Category.parent_id.is_not(None))
                )
            ).scalars()
        )
        brand_ids = set((await session.execute(select(Brand.id))).scalars())
        existing_skus = set((await session.execute(select(Product.sku))).scalars())

        final_eligible: list[ImportRow] = []
        for item in eligible:
            row = item.data
            try:
                category_id = int(row["category_id"])
            except (KeyError, TypeError, ValueError):
                item.issues.append("category_missing")
                rejected.append(item)
                continue
            try:
                brand_id = int(row["brand_id"])
            except (KeyError, TypeError, ValueError):
                item.issues.append("brand_missing")
                rejected.append(item)
                continue

            if category_id not in category_ids:
                item.issues.append("category_not_in_db")
                rejected.append(item)
                continue
            if brand_id not in brand_ids:
                item.issues.append("brand_not_in_db")
                rejected.append(item)
                continue
            if row["sku"] in existing_skus:
                item.issues.append("sku_exists_in_db")
                rejected.append(item)
                skipped_existing += 1
                continue

            final_eligible.append(item)

        for item in final_eligible:
            row = item.data
            price = parse_price_toman(row)
            assert price is not None

            product = Product(
                sku=row["sku"],
                slug=slugify(f"{row['name']}-{row['sku']}") or row["sku"].lower(),
                name=row["name"][:255],
                description=(row.get("description") or row["name"])[:5000] or None,
                category_id=int(row["category_id"]),
                brand_id=int(row["brand_id"]),
                base_price=price,
                original_price=None,
                stock_quantity=Decimal("0"),
                stock_unit=StockUnitEnum.PIECE,
                is_original=True,
                is_active=True,
                specifications=parse_specifications(row.get("specifications_json", "")),
            )
            session.add(product)
            existing_skus.add(row["sku"])
            inserted += 1
            if inserted % 200 == 0:
                await session.flush()

        await session.commit()

    return final_eligible, rejected, inserted, skipped_existing


async def main() -> None:
    parser = argparse.ArgumentParser(description="Import products from price-list CSV")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--rejected-xlsx", type=Path, default=DEFAULT_REJECTED_XLSX)
    parser.add_argument("--rejected-csv", type=Path, default=DEFAULT_REJECTED_CSV)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.csv.exists():
        raise SystemExit(f"CSV not found: {args.csv}")

    eligible, rejected, inserted, skipped_existing = await import_products(
        args.csv,
        dry_run=args.dry_run,
    )

    write_rejected_csv(args.rejected_csv, rejected)
    xlsx_ok = write_rejected_xlsx(args.rejected_xlsx, rejected)

    print("=== Product import summary ===")
    print(f"CSV rows: {len(eligible) + len(rejected)}")
    print(f"Eligible (strict): {len(eligible)}")
    print(f"Inserted: {inserted}")
    if skipped_existing:
        print(f"Skipped existing SKU in DB: {skipped_existing}")
    print(f"Rejected: {len(rejected)}")
    print(f"Rejected CSV: {args.rejected_csv}")
    if xlsx_ok:
        print(f"Rejected XLSX: {args.rejected_xlsx}")
    else:
        print("Rejected XLSX: not created (install openpyxl)")


if __name__ == "__main__":
    asyncio.run(main())
