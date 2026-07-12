"""Product database access layer: CRUD, filtering, stock, and aggregations."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.crud import category as crud_category
from app.core.logging import get_logger
from app.db.models.product import Brand, Product, ProductImage, StockUnitEnum
from app.schemas.product import ProductCreate, ProductUpdate
from app.utils.decimal_utils import to_decimal as _to_decimal
from app.utils.jsonb_filters import build_specification_filters
from app.utils.specifications import specifications_for_storage
from app.utils.storefront_catalog import product_sort_clause

logger = get_logger(__name__)


def _product_load_options():
    """Eager-load relationships needed by API response presenters."""
    return (
        selectinload(Product.images),
        selectinload(Product.category),
        selectinload(Product.brand),
    )


async def create_product(db: AsyncSession, product_in: ProductCreate) -> Product:
    payload = product_in.model_dump(exclude={"specifications", "stock_unit"})
    db_product = Product(
        **payload,
        stock_unit=StockUnitEnum(product_in.stock_unit),
        specifications=specifications_for_storage(product_in.specifications),
    )
    try:
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


async def get_products_for_update(
    db: AsyncSession, product_ids: List[int]
) -> Dict[int, Product]:
    """Fetch active products locked FOR UPDATE, keyed by id (ordered to avoid deadlocks).

    The row locks are a no-op on SQLite (test engine) and enforced on PostgreSQL.
    """
    if not product_ids:
        return {}
    stmt = (
        select(Product)
        .where(and_(Product.id.in_(product_ids), Product.deleted_at.is_(None)))
        .order_by(Product.id)
        .with_for_update()
    )
    result = await db.execute(stmt)
    return {product.id: product for product in result.scalars().all()}


async def get_products_by_ids(db: AsyncSession, product_ids: List[int]) -> Dict[int, Product]:
    if not product_ids:
        return {}
    stmt = select(Product).where(
        and_(Product.id.in_(product_ids), Product.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    return {product.id: product for product in result.scalars().all()}


async def get_product_by_sku(
    db: AsyncSession, sku: str, *, include_deleted: bool = False
) -> Optional[Product]:
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
    country: Optional[str] = None,
    in_stock: Optional[bool] = None,
    sort: Optional[str] = None,
    product_ids: Optional[List[int]] = None,
    is_deleted: Optional[bool] = None,
) -> Tuple[List[Product], int]:
    if is_deleted:
        query = select(Product).where(Product.deleted_at.isnot(None))
    else:
        query = select(Product).where(Product.deleted_at.is_(None))
    filters = []

    if product_ids:
        filters.append(Product.id.in_(product_ids))
    if category_id:
        subtree_ids = await crud_category.get_category_subtree_ids(db, category_id)
        if subtree_ids:
            filters.append(Product.category_id.in_(subtree_ids))
        else:
            filters.append(Product.category_id == category_id)
    if brand_id:
        filters.append(Product.brand_id == brand_id)
    if country:
        filters.append(Product.brand.has(Brand.country == country))
    if in_stock:
        filters.append(
            and_(
                Product.is_active.is_(True),
                Product.stock_quantity > Decimal("0.0"),
            )
        )
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

    if is_deleted:
        count_query = select(func.count(Product.id)).where(Product.deleted_at.isnot(None))
    else:
        count_query = select(func.count(Product.id)).where(Product.deleted_at.is_(None))
    if filters:
        count_query = count_query.where(and_(*filters))
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    query = (
        query.options(*_product_load_options())
        .order_by(product_sort_clause(sort, dialect_name=db.get_bind().dialect.name))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    products = list(result.scalars().all())

    if product_ids:
        order_index = {product_id: index for index, product_id in enumerate(product_ids)}
        products.sort(key=lambda product: order_index.get(product.id, len(order_index)))

    logger.info(f"Retrieved {len(products)} products with skip={skip}, limit={limit}")
    return products, total


async def update_product(
    db: AsyncSession, product_id: int, product_in: ProductUpdate
) -> Optional[Product]:
    db_product = await get_product_by_id(db, product_id)
    if not db_product:
        return None

    try:
        update_data = product_in.model_dump(exclude_unset=True)
        if "stock_unit" in update_data and update_data["stock_unit"] is not None:
            update_data["stock_unit"] = StockUnitEnum(update_data["stock_unit"])
        if "specifications" in update_data and update_data["specifications"] is not None:
            update_data["specifications"] = specifications_for_storage(update_data["specifications"])

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
    """Atomically adjust stock; rejects deltas that would drive quantity below zero."""
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
    """Aggregate product counts and stock value entirely in the database."""
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


async def check_sku_exists(
    db: AsyncSession, sku: str, exclude_product_id: Optional[int] = None
) -> bool:
    """Check SKU uniqueness among active (non-deleted) products."""
    stmt = select(Product.id).where(
        Product.sku == sku,
        Product.deleted_at.is_(None),
    )
    if exclude_product_id is not None:
        stmt = stmt.where(Product.id != exclude_product_id)
    result = await db.execute(stmt)
    return result.first() is not None


async def check_sku_exists_absolutely(
    db: AsyncSession, sku: str, exclude_product_id: Optional[int] = None
) -> bool:
    """Backward-compatible alias for active SKU uniqueness checks."""
    return await check_sku_exists(db, sku, exclude_product_id=exclude_product_id)


async def get_related_products(
    db: AsyncSession,
    product_id: int,
    *,
    limit: int = 6,
) -> List[Product]:
    product = await get_product_by_id(db, product_id)
    if not product or not product.category_id:
        return []

    from app.crud import category as crud_category

    categories = await crud_category.get_all_categories(db)
    by_id = {category.id: category for category in categories}
    current = by_id.get(product.category_id)
    if not current:
        return []

    root_id = current.id
    while current.parent_id is not None:
        parent = by_id.get(current.parent_id)
        if parent is None:
            break
        root_id = parent.id
        current = parent

    subtree_ids = await crud_category.get_category_subtree_ids(db, root_id)
    if not subtree_ids:
        return []

    stmt = (
        select(Product)
        .where(
            and_(
                Product.deleted_at.is_(None),
                Product.is_active.is_(True),
                Product.id != product_id,
                Product.category_id.in_(subtree_ids),
            )
        )
        .options(*_product_load_options())
        .order_by(Product.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_product_images(db: AsyncSession, product_id: int) -> int:
    stmt = select(func.count()).select_from(ProductImage).where(ProductImage.product_id == product_id)
    return (await db.execute(stmt)).scalar_one()


async def add_product_image(
    db: AsyncSession,
    product_id: int,
    image_url: str,
    *,
    is_primary: bool = False,
) -> ProductImage:
    if is_primary:
        await db.execute(
            update(ProductImage)
            .where(ProductImage.product_id == product_id)
            .values(is_primary=False)
        )

    next_order_stmt = select(func.coalesce(func.max(ProductImage.display_order), -1)).where(
        ProductImage.product_id == product_id
    )
    next_order = (await db.execute(next_order_stmt)).scalar_one() + 1

    image = ProductImage(
        product_id=product_id,
        image_url=image_url,
        is_primary=is_primary,
        display_order=next_order,
    )
    db.add(image)
    await db.flush()
    await db.refresh(image)
    return image


async def reorder_product_images(
    db: AsyncSession, product_id: int, image_ids: List[int]
) -> List[ProductImage]:
    stmt = select(ProductImage).where(ProductImage.product_id == product_id)
    result = await db.execute(stmt)
    images = list(result.scalars().all())
    if not images:
        return []

    existing_ids = {image.id for image in images}
    if set(image_ids) != existing_ids:
        raise ValueError("image_ids must include every image for this product exactly once")

    by_id = {image.id: image for image in images}
    for index, image_id in enumerate(image_ids):
        by_id[image_id].display_order = index
    await db.flush()
    return [by_id[image_id] for image_id in image_ids]


async def delete_product_image(db: AsyncSession, product_id: int, image_id: int) -> bool:
    stmt = select(ProductImage).where(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id,
    )
    result = await db.execute(stmt)
    image = result.scalar_one_or_none()
    if not image:
        return False
    await db.delete(image)
    await db.flush()
    return True


async def set_primary_product_image(
    db: AsyncSession, product_id: int, image_id: int
) -> Optional[ProductImage]:
    stmt = select(ProductImage).where(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id,
    )
    result = await db.execute(stmt)
    image = result.scalar_one_or_none()
    if not image:
        return None

    await db.execute(
        update(ProductImage)
        .where(ProductImage.product_id == product_id)
        .values(is_primary=False)
    )
    image.is_primary = True
    await db.flush()
    return image
