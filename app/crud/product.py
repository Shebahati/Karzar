# app/crud/product.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models.product import Product
from app.schemas.product import ProductCreate

async def create_product(db: AsyncSession, product_in: ProductCreate) -> Product:
    db_product = Product(
        sku=product_in.sku,
        name=product_in.name,
        category_slug=product_in.category_slug,
        brand=product_in.brand,
        base_price=product_in.base_price,
        stock_quantity=product_in.stock_quantity,
        is_active=product_in.is_active,
        specifications=product_in.specifications.model_dump()
    )
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product

async def get_products(db: AsyncSession):
    result = await db.execute(select(Product))
    return result.scalars().all()