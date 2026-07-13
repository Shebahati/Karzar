"""Brand database access for admin CRUD."""


from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.product import Brand, Product

logger = get_logger(__name__)


async def list_brands(db: AsyncSession) -> list[Brand]:
    result = await db.execute(select(Brand).order_by(Brand.name.asc()))
    return list(result.scalars().all())


async def get_brand_by_id(db: AsyncSession, brand_id: int) -> Brand | None:
    result = await db.execute(select(Brand).where(Brand.id == brand_id))
    return result.scalar_one_or_none()


async def get_brand_by_name(db: AsyncSession, name: str) -> Brand | None:
    result = await db.execute(select(Brand).where(Brand.name == name))
    return result.scalar_one_or_none()


async def create_brand(db: AsyncSession, *, name: str, country: str | None) -> Brand:
    from app.utils.slugify import ensure_unique_slug

    async def _exists(candidate: str) -> bool:
        return (
            await db.execute(select(Brand.id).where(Brand.slug == candidate))
        ).first() is not None

    slug = await ensure_unique_slug(
        name,
        exists=_exists,
        fallback_prefix="brand",
        max_length=200,
    )
    brand = Brand(name=name, country=country, slug=slug)
    db.add(brand)
    await db.flush()
    await db.refresh(brand)
    return brand


async def update_brand(
    db: AsyncSession,
    brand: Brand,
    *,
    name: str | None = None,
    country: str | None = None,
    unset_country: bool = False,
) -> Brand:
    if name is not None:
        brand.name = name
    if unset_country:
        brand.country = None
    elif country is not None:
        brand.country = country
    await db.flush()
    await db.refresh(brand)
    return brand


async def count_products_for_brand(db: AsyncSession, brand_id: int) -> int:
    result = await db.scalar(
        select(func.count())
        .select_from(Product)
        .where(Product.brand_id == brand_id, Product.deleted_at.is_(None))
    )
    return int(result or 0)


async def clear_brand_on_products(db: AsyncSession, brand_id: int) -> int:
    stmt = (
        update(Product)
        .where(Product.brand_id == brand_id, Product.deleted_at.is_(None))
        .values(brand_id=None)
    )
    result = await db.execute(stmt)
    return int(result.rowcount or 0)


async def delete_brand_row(db: AsyncSession, brand: Brand) -> None:
    await db.delete(brand)
    await db.flush()
