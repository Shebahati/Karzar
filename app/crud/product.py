# app/crud/product.py
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List, Tuple
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, func, update
from sqlalchemy.orm import selectinload

from app.db.models.product import Product, Brand, StockUnitEnum
from app.schemas.product import ProductCreate, ProductUpdate
from app.core.logging import get_logger
from app.utils.jsonb_filters import build_specification_filters

logger = get_logger(__name__)


def _product_load_options():
    return (
        selectinload(Product.images),
        selectinload(Product.category),
        selectinload(Product.brand),
    )


def _to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


async def create_product(db: AsyncSession, product_in: ProductCreate) -> Product:
    """Create a new product."""
    try:
        product_data = product_in.model_dump(exclude={"specifications", "stock_unit"})
        product_data["stock_unit"] = StockUnitEnum(product_in.stock_unit)

        db_product = Product(
            **product_data,
            specifications=product_in.specifications,
        )
        db.add(db_product)
        await db.flush()
        await db.refresh(db_product)

        logger.info(f"Created product with SKU: {product_in.sku}")
        return db_product
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating product: {str(e)}")
        raise


async def get_product_by_id(db: AsyncSession, product_id: int) -> Optional[Product]:
    """Get a product by ID, excluding soft-deleted products."""
    stmt = (
        select(Product)
        .where(
            and_(
                Product.id == product_id,
                Product.deleted_at.is_(None),
            )
        )
        .options(*_product_load_options())
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_product_by_sku(db: AsyncSession, sku: str, *, include_deleted: bool = False) -> Optional[Product]:
    """Get a product by SKU."""
    stmt = select(Product).where(Product.sku == sku).options(*_product_load_options())
    if not include_deleted:
        stmt = stmt.where(Product.deleted_at.is_(None))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_products(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    category_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    max_stock: Optional[Decimal] = None,
    spec_filters: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Product], int]:
    """Get products with filtering and pagination."""
    query = select(Product).where(Product.deleted_at.is_(None))
    filters = []

    if category_id:
        filters.append(Product.category_id == category_id)
    if brand_id:
        filters.append(Product.brand_id == brand_id)
    if is_active is not None:
        filters.append(Product.is_active == is_active)
    if min_price is not None:
        filters.append(Product.base_price >= min_price)
    if max_price is not None:
        filters.append(Product.base_price <= max_price)
    if max_stock is not None:
        filters.append(Product.stock_quantity < max_stock)

    if search:
        search_filter = or_(
            Product.name.ilike(f"%{search}%"),
            Product.sku.ilike(f"%{search}%"),
            Product.brand.has(Brand.name.ilike(f"%{search}%")),
        )
        filters.append(search_filter)

    if spec_filters:
        dialect_name = db.get_bind().dialect.name
        try:
            filters.extend(build_specification_filters(spec_filters, dialect_name=dialect_name))
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

    if filters:
        query = query.where(and_(*filters))

    count_query = select(func.count(Product.id)).where(Product.deleted_at.is_(None))
    if filters:
        count_query = count_query.where(and_(*filters))
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    query = (
        query.options(*_product_load_options())
        .order_by(Product.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    products = result.scalars().all()

    logger.info(f"Retrieved {len(products)} products with skip={skip}, limit={limit}")
    return list(products), total


async def update_product(
    db: AsyncSession, product_id: int, product_in: ProductUpdate
) -> Optional[Product]:
    """Update a product."""
    db_product = await get_product_by_id(db, product_id)
    if not db_product:
        return None

    try:
        update_data = product_in.model_dump(exclude_unset=True)
        if "stock_unit" in update_data and update_data["stock_unit"] is not None:
            update_data["stock_unit"] = StockUnitEnum(update_data["stock_unit"])

        for field, value in update_data.items():
            setattr(db_product, field, value)

        await db.flush()
        logger.info(f"Updated product with ID: {product_id}")
        return db_product
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating product: {str(e)}")
        raise


async def delete_product_soft(db: AsyncSession, product_id: int) -> bool:
    """Soft delete a product."""
    db_product = await get_product_by_id(db, product_id)
    if not db_product:
        return False

    try:
        db_product.deleted_at = datetime.now(timezone.utc)
        db_product.is_active = False
        await db.flush()
        logger.info(f"Soft deleted product with ID: {product_id}")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting product: {str(e)}")
        raise


async def delete_product_hard(db: AsyncSession, product_id: int) -> bool:
    """Hard delete a product."""
    try:
        stmt = select(Product).where(Product.id == product_id)
        result = await db.execute(stmt)
        db_product = result.scalar_one_or_none()

        if not db_product:
            return False

        await db.delete(db_product)
        await db.flush()
        logger.info(f"Hard deleted product with ID: {product_id}")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"Error hard deleting product: {str(e)}")
        raise


async def restore_product(db: AsyncSession, product_id: int) -> Optional[Product]:
    """Restore a soft-deleted product."""
    stmt = select(Product).where(Product.id == product_id)
    result = await db.execute(stmt)
    db_product = result.scalar_one_or_none()

    if not db_product or db_product.deleted_at is None:
        return None

    try:
        db_product.deleted_at = None
        db_product.is_active = True
        await db.flush()
        logger.info(f"Restored product with ID: {product_id}")
        return db_product
    except Exception as e:
        await db.rollback()
        logger.error(f"Error restoring product: {str(e)}")
        raise


async def get_stock_status(db: AsyncSession, product_id: int) -> Optional[dict]:
    """Get stock status for a product."""
    product = await get_product_by_id(db, product_id)
    if not product:
        return None

    quantity = _to_decimal(product.stock_quantity)
    return {
        "product_id": product.id,
        "sku": product.sku,
        "stock_quantity": quantity,
        "stock_status": "out_of_stock" if quantity <= Decimal("0.0") else "in_stock",
    }


async def update_stock(
    db: AsyncSession, product_id: int, quantity_delta: Decimal
) -> Optional[Product]:
    """Atomic stock update to prevent race conditions."""
    try:
        stmt = (
            update(Product)
            .where(
                and_(
                    Product.id == product_id,
                    Product.deleted_at.is_(None),
                    Product.stock_quantity + quantity_delta >= Decimal("0.0"),
                )
            )
            .values(stock_quantity=Product.stock_quantity + quantity_delta)
            .returning(Product)
        )
        result = await db.execute(stmt)
        updated_product = result.scalar_one_or_none()

        if updated_product:
            await db.flush()
            logger.info(f"Updated stock for product {product_id}: delta={quantity_delta}")
            return updated_product

        await db.rollback()
        logger.warning(f"Failed to update stock for {product_id}. Insufficient stock or not found.")
        raise ValueError("Insufficient stock or product not found")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating stock: {str(e)}")
        raise


async def get_product_statistics(db: AsyncSession) -> dict:
    """High performance in-DB aggregation."""
    stmt = select(
        func.count(Product.id),
        func.sum(func.coalesce(Product.base_price, 0) * Product.stock_quantity),
        func.sum(Product.stock_quantity),
        func.count(Product.category_id.distinct()),
        func.count(Product.brand_id.distinct()),
    ).where(Product.deleted_at.is_(None))

    result = await db.execute(stmt)
    row = result.first()

    active_stmt = select(func.count(Product.id)).where(
        and_(Product.is_active == True, Product.deleted_at.is_(None))
    )
    active_count = (await db.execute(active_stmt)).scalar() or 0

    stats = {
        "total_products": row[0] or 0,
        "active_products": active_count,
        "total_stock_value": Decimal(str(row[1] or 0)),
        "total_stock_quantity": Decimal(str(row[2] or 0)),
        "categories": row[3] or 0,
        "brands": row[4] or 0,
    }
    logger.info(f"Product statistics retrieved: {stats}")
    return stats


async def check_sku_exists_absolutely(db: AsyncSession, sku: str, exclude_product_id: Optional[int] = None) -> bool:
    """Check if SKU exists in database, optionally excluding one product ID."""
    stmt = select(Product.id).where(Product.sku == sku)
    if exclude_product_id is not None:
        stmt = stmt.where(Product.id != exclude_product_id)
    result = await db.execute(stmt)
    return result.first() is not None
