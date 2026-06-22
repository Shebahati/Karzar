# app/services/product_service.py
from typing import Optional, List, Tuple
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate
from app.crud import product as crud_product
from app.core.logging import get_logger
from app.services.notion_service import NotionService

logger = get_logger(__name__)


def _to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class ProductService:
    """Business logic service for product operations."""

    @staticmethod
    async def create_product_with_validation(
        db: AsyncSession, product_data: ProductCreate
    ) -> Product:
        logger.info(f"Creating product: {product_data.sku}")

        if await crud_product.check_sku_exists_absolutely(db, product_data.sku):
            raise ValueError(
                f"Product with SKU {product_data.sku} already exists (including deleted products)"
            )

        product = await crud_product.create_product(db, product_data)
        await db.commit()
        logger.info(f"Product created successfully: {product.id}")

        try:
            notion = NotionService()
            await notion.update_endpoint_status("Get Products List", "Done")
        except Exception as e:
            logger.error(f"Notion integration failed: {str(e)}")

        return product

    @staticmethod
    async def get_product_details(db: AsyncSession, product_id: int) -> Optional[dict]:
        product = await crud_product.get_product_by_id(db, product_id)
        if not product:
            return None

        quantity = _to_decimal(product.stock_quantity)
        stock_status = "in_stock" if quantity > Decimal("0.0") else "out_of_stock"
        low_stock = quantity < Decimal("10.0")

        return {
            "product": product,
            "stock_status": stock_status,
            "low_stock": low_stock,
            "availability": product.is_active and quantity > Decimal("0.0"),
        }

    @staticmethod
    async def search_products(
        db: AsyncSession,
        search: Optional[str] = None,
        category_id: Optional[int] = None,
        brand_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        spec_filters: Optional[dict] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Product], int]:
        logger.info(f"Searching products: search={search}, category_id={category_id}")
        return await crud_product.get_products(
            db=db,
            skip=skip,
            limit=limit,
            category_id=category_id,
            brand_id=brand_id,
            is_active=is_active,
            search=search,
            min_price=min_price,
            max_price=max_price,
            spec_filters=spec_filters,
        )

    @staticmethod
    async def update_product_with_validation(
        db: AsyncSession,
        product_id: int,
        update_data: ProductUpdate,
    ) -> Optional[Product]:
        logger.info(f"Updating product: {product_id}")

        product = await crud_product.get_product_by_id(db, product_id)
        if not product:
            return None

        updated_product = await crud_product.update_product(db, product_id, update_data)
        await db.commit()
        logger.info(f"Product updated successfully: {product_id}")
        return updated_product

    @staticmethod
    async def adjust_stock_with_validation(
        db: AsyncSession,
        product_id: int,
        quantity_delta: Decimal,
        reason: Optional[str] = None,
    ) -> Optional[Product]:
        logger.info(
            f"Adjusting stock for product {product_id}: delta={quantity_delta}, reason={reason}"
        )

        product = await crud_product.get_product_by_id(db, product_id)
        if not product:
            return None

        updated_product = await crud_product.update_stock(db, product_id, quantity_delta)
        if updated_product:
            await db.commit()
        return updated_product

    @staticmethod
    async def get_low_stock_products(
        db: AsyncSession, threshold: Decimal = Decimal("10.0"), limit: int = 100
    ) -> List[Product]:
        logger.info(f"Retrieving low stock products (threshold: {threshold})")
        products, _ = await crud_product.get_products(
            db=db,
            skip=0,
            limit=limit,
            max_stock=threshold,
        )
        logger.info(f"Found {len(products)} products with low stock")
        return products

    @staticmethod
    async def get_products_by_brand(
        db: AsyncSession, brand_id: int, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Product], int]:
        logger.info(f"Retrieving products for brand ID: {brand_id}")
        return await crud_product.get_products(
            db=db,
            skip=skip,
            limit=limit,
            brand_id=brand_id,
        )

    @staticmethod
    async def get_product_statistics(db: AsyncSession) -> dict:
        logger.info("Retrieving product statistics")
        return await crud_product.get_product_statistics(db)

    @staticmethod
    async def delete_product(db: AsyncSession, product_id: int) -> bool:
        deleted = await crud_product.delete_product_soft(db, product_id)
        if deleted:
            await db.commit()
        return deleted

    @staticmethod
    async def restore_product(db: AsyncSession, product_id: int) -> Optional[Product]:
        product = await crud_product.restore_product(db, product_id)
        if product:
            await db.commit()
        return product
