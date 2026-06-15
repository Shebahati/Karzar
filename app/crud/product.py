# app/crud/product.py
from datetime import datetime
from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, func
from app.db.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_product(db: AsyncSession, product_in: ProductCreate) -> Product:
    """Create a new product."""
    try:
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
        logger.info(f"Created product with SKU: {product_in.sku}")
        return db_product
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating product: {str(e)}")
        raise


async def get_product_by_id(db: AsyncSession, product_id: UUID) -> Optional[Product]:
    """Get a product by ID, excluding soft-deleted products."""
    stmt = select(Product).where(
        and_(
            Product.id == product_id,
            Product.deleted_at.is_(None)
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_product_by_sku(db: AsyncSession, sku: str) -> Optional[Product]:
    """Get a product by SKU, excluding soft-deleted products."""
    stmt = select(Product).where(
        and_(
            Product.sku == sku,
            Product.deleted_at.is_(None)
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_products(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    category_slug: Optional[str] = None,
    brand: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
) -> Tuple[List[Product], int]:
    """Get products with filtering and pagination."""
    # Base query excluding soft-deleted products
    query = select(Product).where(Product.deleted_at.is_(None))
    
    # Apply filters
    filters = []
    
    if category_slug:
        filters.append(Product.category_slug == category_slug)
    
    if brand:
        filters.append(Product.brand == brand)
    
    if is_active is not None:
        filters.append(Product.is_active == is_active)
    
    if search:
        search_filter = or_(
            Product.name.ilike(f"%{search}%"),
            Product.sku.ilike(f"%{search}%"),
            Product.brand.ilike(f"%{search}%"),
        )
        filters.append(search_filter)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count using func.count for efficiency
    count_query = select(func.count(Product.id)).where(Product.deleted_at.is_(None))
    if filters:
        count_query = count_query.where(and_(*filters))
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Apply pagination and execute
    query = query.order_by(Product.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    products = result.scalars().all()
    
    logger.info(f"Retrieved {len(products)} products with skip={skip}, limit={limit}")
    return products, total


async def update_product(
    db: AsyncSession, product_id: UUID, product_in: ProductUpdate
) -> Optional[Product]:
    """Update a product."""
    db_product = await get_product_by_id(db, product_id)
    if not db_product:
        return None
    
    try:
        update_data = product_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "specifications" and value is not None:
                setattr(db_product, field, value.model_dump())
            else:
                setattr(db_product, field, value)
        
        await db.commit()
        await db.refresh(db_product)
        logger.info(f"Updated product with ID: {product_id}")
        return db_product
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating product: {str(e)}")
        raise


async def delete_product_soft(db: AsyncSession, product_id: UUID) -> bool:
    """Soft delete a product (mark as deleted without removing from DB)."""
    db_product = await get_product_by_id(db, product_id)
    if not db_product:
        return False
    
    try:
        db_product.deleted_at = datetime.utcnow()
        await db.commit()
        logger.info(f"Soft deleted product with ID: {product_id}")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting product: {str(e)}")
        raise


async def delete_product_hard(db: AsyncSession, product_id: UUID) -> bool:
    """Hard delete a product (permanently remove from DB)."""
    try:
        stmt = select(Product).where(Product.id == product_id)
        result = await db.execute(stmt)
        db_product = result.scalar_one_or_none()
        
        if not db_product:
            return False
        
        await db.delete(db_product)
        await db.commit()
        logger.info(f"Hard deleted product with ID: {product_id}")
        return True
    except Exception as e:
        await db.rollback()
        logger.error(f"Error hard deleting product: {str(e)}")
        raise


async def restore_product(db: AsyncSession, product_id: UUID) -> Optional[Product]:
    """Restore a soft-deleted product."""
    stmt = select(Product).where(Product.id == product_id)
    result = await db.execute(stmt)
    db_product = result.scalar_one_or_none()
    
    if not db_product or db_product.deleted_at is None:
        return None
    
    try:
        db_product.deleted_at = None
        await db.commit()
        await db.refresh(db_product)
        logger.info(f"Restored product with ID: {product_id}")
        return db_product
    except Exception as e:
        await db.rollback()
        logger.error(f"Error restoring product: {str(e)}")
        raise


async def get_stock_status(db: AsyncSession, product_id: UUID) -> Optional[dict]:
    """Get stock status for a product."""
    product = await get_product_by_id(db, product_id)
    if not product:
        return None
    
    status = "out_of_stock" if product.stock_quantity == 0 else "in_stock"
    return {
        "product_id": product.id,
        "sku": product.sku,
        "stock_quantity": product.stock_quantity,
        "status": status
    }


async def update_stock(db: AsyncSession, product_id: UUID, quantity_delta: int) -> Optional[Product]:
    """Update product stock by adding or subtracting quantity."""
    db_product = await get_product_by_id(db, product_id)
    if not db_product:
        return None
    
    try:
        new_quantity = db_product.stock_quantity + quantity_delta
        if new_quantity < 0:
            raise ValueError("Stock quantity cannot be negative")
        
        db_product.stock_quantity = new_quantity
        await db.commit()
        await db.refresh(db_product)
        logger.info(f"Updated stock for product {product_id}: {quantity_delta}")
        return db_product
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating stock: {str(e)}")
        raise
