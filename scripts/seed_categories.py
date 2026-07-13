"""
Seed the categories table with the Karzar catalog tree.

Usage (Docker):
    docker compose exec app python scripts/seed_categories.py

Clears existing products (and images) before reseeding categories when products exist.
"""

import asyncio
import sys
from pathlib import Path

# Allow running as `python scripts/seed_categories.py` from project root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, func, select, text

from app.core.logging import get_logger, setup_logging
from app.db.database import async_session_maker
from app.db.models.product import Category, Product, ProductImage
from app.utils.slugify import slugify

setup_logging()
logger = get_logger(__name__)

# Root / branch template keys (decoupled from numeric ids in spec_template_service).
SPEC_TEMPLATE_KEYS: dict[int, str] = {
    2: "insert_holder",
    3: "insert",
    4: "end_mill",
    5: "drill",
    7: "measurement",
    33: "insert",
    34: "insert",
    57: "measurement",
    58: "measurement",
}

CATEGORIES: list[dict[str, object]] = [
    {"id": 1, "name": "ابزارگیر", "parent_id": None},
    {"id": 2, "name": "ابزار اینسرتی", "parent_id": None},
    {"id": 3, "name": "اینسرت", "parent_id": None},
    {"id": 4, "name": "ابزار انگشتی", "parent_id": None},
    {"id": 5, "name": "مته", "parent_id": None},
    {"id": 6, "name": "قلاویز", "parent_id": None},
    {"id": 7, "name": "اندازه گیری", "parent_id": None},
    {"id": 8, "name": "ابزار گیرشی", "parent_id": None},
    {"id": 9, "name": "دستگاه‌های صنعتی", "parent_id": None},
    {"id": 12, "name": "ابزارگیر فرز CNC", "parent_id": 1},
    {"id": 13, "name": "کولت BT و فشنگی و آچار", "parent_id": 12},
    {"id": 14, "name": "کولت SK و فشنگی و آچار", "parent_id": 12},
    {"id": 15, "name": "کولت OZ و فشنگی و آچار", "parent_id": 12},
    {"id": 16, "name": "کولت HSK و فشنگی و آچار", "parent_id": 12},
    {"id": 17, "name": "PULL STUD – پول استاد", "parent_id": 12},
    {"id": 18, "name": "ابزارگیر تراش CNC", "parent_id": 1},
    {"id": 19, "name": "بیس هولدر", "parent_id": 18},
    {"id": 20, "name": "کولت VDI", "parent_id": 18},
    {"id": 21, "name": "هولدر فرز CNC", "parent_id": 2},
    {"id": 22, "name": "کف تراش", "parent_id": 21},
    {"id": 23, "name": "هولدر انگشتی", "parent_id": 21},
    {"id": 24, "name": "هولدر تراش CNC", "parent_id": 2},
    {"id": 25, "name": "برش(Q CUT)", "parent_id": 24},
    {"id": 26, "name": "داخل تراش", "parent_id": 24},
    {"id": 27, "name": "رو تراش", "parent_id": 24},
    {"id": 28, "name": "هولدر U-Drill", "parent_id": 2},
    {"id": 29, "name": "U-Drill 2D", "parent_id": 28},
    {"id": 30, "name": "U-Drill 3D", "parent_id": 28},
    {"id": 31, "name": "U-Drill 4D", "parent_id": 28},
    {"id": 32, "name": "U-Drill 5D", "parent_id": 28},
    {"id": 33, "name": "اینسرت تراش CNC", "parent_id": 3},
    {"id": 34, "name": "اینسرت فرز CNC", "parent_id": 3},
    {"id": 35, "name": "انگشتی سرتخت کارباید", "parent_id": 4},
    {"id": 36, "name": "انگشتی سر گرد کارباید(بال نوز)", "parent_id": 4},
    {"id": 37, "name": "انگشتی تیپ کارباید", "parent_id": 4},
    {"id": 38, "name": "انگشتی HSS (تمامی فرم ها)", "parent_id": 4},
    {"id": 39, "name": "انگشتی پخ زن(45 درجه و 60 درجه)", "parent_id": 4},
    {"id": 40, "name": "انگشتی فرم کارباید", "parent_id": 4},
    {"id": 41, "name": "مته کارباید(الماس)", "parent_id": 5},
    {"id": 42, "name": "مته پشت گرد HSS Co (کبالت)", "parent_id": 5},
    {"id": 43, "name": "مته پشت گرد HSS", "parent_id": 5},
    {"id": 44, "name": "مته پشت کونیک HSS", "parent_id": 5},
    {"id": 45, "name": "مته سی ان سی(U_Drill)", "parent_id": 5},
    {"id": 46, "name": "مته مرغک", "parent_id": 5},
    {"id": 47, "name": "برقو", "parent_id": 5},
    {"id": 48, "name": "قلاویز ماشینی مارپیچ", "parent_id": 6},
    {"id": 49, "name": "قلاویز ماشینی صاف", "parent_id": 6},
    {"id": 50, "name": "قلاویز دستی", "parent_id": 6},
    {"id": 51, "name": "انگشتی تردمیل کارباید(Threadmill)", "parent_id": 6},
    {"id": 52, "name": "قلاویز چپ گرد", "parent_id": 6},
    {"id": 53, "name": "قلاویز لوله", "parent_id": 6},
    {"id": 54, "name": "حدیده", "parent_id": 6},
    {"id": 55, "name": "هلی‌کویل (helicoil)", "parent_id": 6},
    {"id": 56, "name": "اندازه گیری دقیق", "parent_id": 7},
    {"id": 57, "name": "انواع کولیس", "parent_id": 56},
    {"id": 58, "name": "انواع میکرومتر", "parent_id": 56},
    {"id": 59, "name": "ساعت اندیکاتور", "parent_id": 56},
    {"id": 60, "name": "ساعت شیطانکی", "parent_id": 56},
    {"id": 61, "name": "ترکمتر", "parent_id": 56},
    {"id": 62, "name": "عمق سنج", "parent_id": 56},
    {"id": 63, "name": "گیج داخل سیلندر", "parent_id": 56},
    {"id": 64, "name": "پایه ساعت", "parent_id": 56},
    {"id": 65, "name": "شابلون", "parent_id": 56},
    {"id": 66, "name": "راپورتر(گیج بلوک-گیج بلاک)", "parent_id": 56},
    {"id": 67, "name": "انواع گیج", "parent_id": 56},
    {"id": 68, "name": "زاویه سنج", "parent_id": 56},
    {"id": 69, "name": "ارتفاع سنج", "parent_id": 56},
    {"id": 70, "name": "شعاع سنج(R)", "parent_id": 56},
    {"id": 71, "name": "تراز صنعتی", "parent_id": 56},
    {"id": 72, "name": "پرگار صنعتی", "parent_id": 56},
    {"id": 73, "name": "فیلر", "parent_id": 56},
    {"id": 74, "name": "پایه میکرومتر", "parent_id": 56},
    {"id": 75, "name": "گونیا", "parent_id": 56},
    {"id": 76, "name": "خط کش", "parent_id": 56},
    {"id": 77, "name": "متر", "parent_id": 56},
    {"id": 78, "name": "گپ سنج", "parent_id": 56},
    {"id": 79, "name": "صفحه صافی گرانیتی", "parent_id": 56},
    {"id": 80, "name": "قطعات یدکی", "parent_id": 56},
    {"id": 81, "name": "CNC اندازه گیری", "parent_id": 7},
    {"id": 82, "name": "Z سنج عقربه ای", "parent_id": 81},
    {"id": 83, "name": "مماس یاب مکانیکی", "parent_id": 81},
    {"id": 84, "name": "مماس یاب نوری", "parent_id": 81},
    {"id": 85, "name": "ساعت 3D (فرز cnc)", "parent_id": 81},
    {"id": 86, "name": "خط کش دیجیتال", "parent_id": 81},
    {"id": 87, "name": "اندازه گیری آزمایشگاهی", "parent_id": 7},
    {"id": 88, "name": "میکروسکوپ", "parent_id": 87},
    {"id": 89, "name": "سختی سنج", "parent_id": 87},
    {"id": 90, "name": "سختی سنج فلزات", "parent_id": 87},
    {"id": 91, "name": "سختی سنج لاستیک", "parent_id": 87},
    {"id": 92, "name": "ترازو", "parent_id": 87},
    {"id": 93, "name": "زبری سنج", "parent_id": 87},
    {"id": 94, "name": "رطوبت سنج", "parent_id": 87},
    {"id": 95, "name": "نیرو سنج", "parent_id": 87},
    {"id": 96, "name": "وزنه", "parent_id": 87},
    {"id": 97, "name": "تاکومتر", "parent_id": 87},
    {"id": 98, "name": "گیرشی فرز cnc", "parent_id": 8},
    {"id": 99, "name": "گیره مکانیک", "parent_id": 98},
    {"id": 100, "name": "گیره هیدرولیک", "parent_id": 98},
    {"id": 101, "name": "گیره دقیق", "parent_id": 98},
    {"id": 102, "name": "صفحه گردان", "parent_id": 98},
    {"id": 103, "name": "تایکوپ", "parent_id": 98},
    {"id": 104, "name": "صفحه مگنت فرزکاری", "parent_id": 98},
    {"id": 105, "name": "ست روبند", "parent_id": 98},
    {"id": 106, "name": "روبند تک", "parent_id": 98},
    {"id": 107, "name": "بغل بند", "parent_id": 98},
    {"id": 108, "name": "انواع پیچ", "parent_id": 98},
    {"id": 109, "name": "پیچ دستی", "parent_id": 98},
    {"id": 110, "name": "مهره T و شش گوش و واشر", "parent_id": 98},
    {"id": 111, "name": "جک زیر سری(دستی)", "parent_id": 98},
    {"id": 112, "name": "زیر سری دقیق(زیرکاری)", "parent_id": 98},
    {"id": 113, "name": "وی بلوک", "parent_id": 98},
    {"id": 114, "name": "گیرشی تراش منوال و CNC", "parent_id": 8},
    {"id": 115, "name": "سه نظام هیدرولیک", "parent_id": 114},
    {"id": 116, "name": "سه نظام و لوازم جانبی", "parent_id": 114},
    {"id": 117, "name": "چهار نظام و لوازم جانبی", "parent_id": 114},
    {"id": 118, "name": "دو نظام و لوازم جانبی", "parent_id": 114},
    {"id": 119, "name": "مرغک مورس", "parent_id": 114},
    {"id": 120, "name": "کلاهک تبدیل مورس", "parent_id": 114},
    {"id": 121, "name": "دستگاه ابزار تیزکن", "parent_id": 9},
    {"id": 122, "name": "دستگاه قلاویز زن", "parent_id": 9},
    {"id": 123, "name": "دستگاه دریل مگنت", "parent_id": 9},
    {"id": 124, "name": "دستگاه اسپارک پرتابل", "parent_id": 9},
    {"id": 125, "name": "دستگاه کُر گیری (کُر دریل)", "parent_id": 9},
]


def _validate_tree(rows: list[dict[str, object]]) -> None:
    ids = {row["id"] for row in rows}
    if len(ids) != len(rows):
        raise ValueError("Duplicate category IDs in seed data")

    for row in rows:
        parent_id = row["parent_id"]
        if parent_id is None:
            continue
        if parent_id not in ids:
            raise ValueError(f"Category {row['id']} references missing parent {parent_id}")
        if parent_id == row["id"]:
            raise ValueError(f"Category {row['id']} cannot be its own parent")


async def seed_categories() -> None:
    _validate_tree(CATEGORIES)

    async with async_session_maker() as session:
        product_count = await session.scalar(select(func.count()).select_from(Product))
        if product_count:
            logger.warning("Deleting %s existing product(s) before reseeding categories", product_count)
            await session.execute(delete(ProductImage))
            await session.execute(delete(Product))

        category_count = await session.scalar(select(func.count()).select_from(Category))
        if category_count:
            logger.info("Removing %s existing categor(ies)", category_count)
            await session.execute(delete(Category))

        for row in CATEGORIES:
            category_id = int(row["id"])  # type: ignore[arg-type]
            session.add(
                Category(
                    id=category_id,
                    name=str(row["name"]),
                    slug=slugify(f"{row['name']}-{category_id}") or f"category-{category_id}",
                    parent_id=row["parent_id"],  # type: ignore[arg-type]
                    spec_template_key=SPEC_TEMPLATE_KEYS.get(category_id),
                )
            )

        await session.commit()

        max_id = await session.scalar(select(func.max(Category.id)))
        await session.execute(
            text("SELECT setval(pg_get_serial_sequence('categories', 'id'), :max_id, true)"),
            {"max_id": max_id},
        )
        await session.commit()

        total = await session.scalar(select(func.count()).select_from(Category))
        roots = await session.scalar(
            select(func.count()).select_from(Category).where(Category.parent_id.is_(None))
        )
        logger.info("Seeded %s categories (%s root nodes). Next auto id: %s", total, roots, max_id)


async def main() -> None:
    await seed_categories()
    print(f"OK: inserted {len(CATEGORIES)} categories.")


if __name__ == "__main__":
    asyncio.run(main())
