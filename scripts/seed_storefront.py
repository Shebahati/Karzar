"""Seed storefront demo content: sample products, blog, hero slides, comments."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.db.database import async_session_maker
from app.db.models.content import Article, HeroSlide, ProductComment
from app.db.models.product import Brand, Category, Product, ProductImage, StockUnitEnum


async def seed() -> None:
    async with async_session_maker() as session:
        brand = (await session.execute(select(Brand).limit(1))).scalar_one_or_none()
        if brand is None:
            brand = Brand(name="بوش", country="آلمان", slug="bosch")
            session.add(brand)
            await session.flush()

        category = (
            await session.execute(
                select(Category).where(Category.parent_id.is_not(None)).limit(1)
            )
        ).scalar_one_or_none()
        if category is None:
            print("No categories found. Run scripts/seed_categories.py first.")
            return

        existing = (
            await session.execute(select(Product).where(Product.sku == "DEMO-DRILL-01"))
        ).scalar_one_or_none()
        if existing is None:
            product = Product(
                sku="DEMO-DRILL-01",
                slug="demo-drill-01",
                name="دریل چکشی بوش مدل GSB 13 RE",
                category_id=category.id,
                brand_id=brand.id,
                base_price=Decimal("4850000"),
                original_price=Decimal("5400000"),
                stock_quantity=Decimal("18"),
                stock_unit=StockUnitEnum.PIECE,
                description="دریل چکشی حرفه‌ای مناسب کارگاه و پروژه‌های ساختمانی.",
                warranty_text="۱۸ ماه گارانتی شرکتی",
                weight_grams=Decimal("1800"),
                is_original=True,
                tax_percent=Decimal("9"),
                specifications={
                    "technical_specs": {"توان موتور": "۶۰۰ وات", "ولتاژ": "۲۲۰ ولت"},
                    "dimensions": {"طول": "280"},
                    "features": {"چپ‌گرد و راست‌گرد": True, "نوع گیربکس": "فلزی"},
                },
            )
            session.add(product)
            await session.flush()
            session.add(
                ProductImage(
                    product_id=product.id,
                    image_url="https://picsum.photos/seed/karzar-drill/800/600",
                    is_primary=True,
                )
            )
            session.add(
                ProductComment(
                    product_id=product.id,
                    author_name="رضا محمدی",
                    rating=5,
                    body="کیفیت ساخت عالی و ارسال سریع بود.",
                    is_verified_buyer=True,
                )
            )
            product_id = product.id
        else:
            product_id = existing.id

        article = (
            await session.execute(select(Article).where(Article.slug == "how-to-choose-drill"))
        ).scalar_one_or_none()
        if article is None:
            session.add(
                Article(
                    slug="how-to-choose-drill",
                    title="راهنمای کامل انتخاب دریل مناسب",
                    excerpt="نکات کلیدی برای انتخاب دریل برقی متناسب با نیاز شما.",
                    cover_image="https://picsum.photos/seed/karzar-blog/1200/630",
                    published_at=datetime.now(timezone.utc),
                    reading_minutes=6,
                    tags=["دریل", "ابزار برقی"],
                    related_product_ids=[product_id],
                    blocks=[
                        {"type": "paragraph", "text": "انتخاب دریل مناسب به نوع کار شما بستگی دارد."},
                        {"type": "heading", "text": "توان موتور"},
                        {"type": "list", "items": ["کارگاهی", "خانگی", "صنعتی"]},
                    ],
                )
            )

        slide = (await session.execute(select(HeroSlide).limit(1))).scalar_one_or_none()
        if slide is None:
            session.add(
                HeroSlide(
                    title="ابزار حرفه‌ای، کیفیت بی‌رقیب",
                    subtitle="تجهیزات اصل از برندهای معتبر جهانی",
                    cta_label="مشاهده محصولات",
                    cta_href="/catalog",
                    image="https://picsum.photos/seed/karzar-hero/1600/700",
                    accent="#C22026",
                    sort_order=1,
                )
            )

        await session.commit()
        print("Storefront demo content seeded.")


if __name__ == "__main__":
    asyncio.run(seed())
