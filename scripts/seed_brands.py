"""
Seed the brands table with the Karzar official brand list.

Usage (Docker):
    docker compose exec app python scripts/seed_brands.py

Existing products keep their rows; brand_id is cleared before reseeding brands.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, func, select, text, update

from app.core.logging import get_logger, setup_logging
from app.db.database import async_session_maker
from app.db.models.product import Brand, Product

setup_logging()
logger = get_logger(__name__)

BRANDS: list[dict[str, object]] = [
    {"id": 1, "name": "EUROLOY | یورولوی"},
    {"id": 2, "name": "Mitutoyo | میتوتویو"},
    {"id": 3, "name": "INSIZE | اینسایز"},
    {"id": 4, "name": "Dasqua | داسکوا"},
    {"id": 5, "name": "TERMA | ترما"},
    {"id": 6, "name": "ASIMETO | آسیمتو"},
    {"id": 7, "name": "GUANGLU | گوانگلو"},
    {"id": 8, "name": "ZCC.CT | زد سی‌سی"},
    {"id": 9, "name": "DOHRE | دوهره"},
    {"id": 10, "name": "YOWAX | یواکس"},
    {"id": 11, "name": "HELIX | هلیکس"},
    {"id": 12, "name": "MAP | ام ای پی"},
    {"id": 13, "name": "ASTPOWER | ای اس تی پاور"},
    {"id": 14, "name": "Mighty Seven | مایتی سون"},
    {"id": 15, "name": "KORLOY | کورلوی"},
    {"id": 16, "name": "MILLER | میلر"},
    {"id": 17, "name": "Ronix | رونیکس"},
    {"id": 18, "name": "ACCKEE | ای‌سی‌سی‌کی"},
    {"id": 19, "name": "ARNO | آرنو"},
    {"id": 20, "name": "SAN OU | سانو"},
    {"id": 21, "name": "YTUM | یوتوم"},
    {"id": 22, "name": "TIGER TEC | تایگرتک"},
]


def _validate_brands(rows: list[dict[str, object]]) -> None:
    ids = {row["id"] for row in rows}
    names = {row["name"] for row in rows}
    if len(ids) != len(rows):
        raise ValueError("Duplicate brand IDs in seed data")
    if len(names) != len(rows):
        raise ValueError("Duplicate brand names in seed data")


async def seed_brands() -> None:
    _validate_brands(BRANDS)

    async with async_session_maker() as session:
        linked = await session.scalar(
            select(func.count()).select_from(Product).where(Product.brand_id.is_not(None))
        )
        if linked:
            logger.warning("Clearing brand_id on %s product(s) before reseeding brands", linked)
            await session.execute(update(Product).values(brand_id=None))

        brand_count = await session.scalar(select(func.count()).select_from(Brand))
        if brand_count:
            logger.info("Removing %s existing brand(s)", brand_count)
            await session.execute(delete(Brand))

        for row in BRANDS:
            session.add(
                Brand(
                    id=int(row["id"]),  # type: ignore[arg-type]
                    name=str(row["name"]),
                    country=None,
                )
            )

        await session.commit()

        max_id = await session.scalar(select(func.max(Brand.id)))
        await session.execute(
            text("SELECT setval(pg_get_serial_sequence('brands', 'id'), :max_id, true)"),
            {"max_id": max_id},
        )
        await session.commit()

        total = await session.scalar(select(func.count()).select_from(Brand))
        logger.info("Seeded %s brands. Next auto id: %s", total, max_id)


async def main() -> None:
    await seed_brands()
    print(f"OK: inserted {len(BRANDS)} brands.")


if __name__ == "__main__":
    asyncio.run(main())
