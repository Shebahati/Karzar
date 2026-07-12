"""Product business logic: validation, orchestration, and side effects."""

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.crud import platform as crud_platform
from app.crud import product as crud_product
from app.db.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate
from app.utils.category_validation import ensure_brand_exists, ensure_selectable_product_category
from app.utils.decimal_utils import to_decimal as _to_decimal
from app.utils.storefront_catalog import stock_status_label

logger = get_logger(__name__)


class ProductService:
    """Coordinates CRUD operations with domain validation."""

    @staticmethod
    async def create_product_with_validation(
        db: AsyncSession, product_data: ProductCreate
    ) -> Product:
        logger.info(f"Creating product: {product_data.sku}")

        if await crud_product.check_sku_exists(db, product_data.sku):
            raise ValueError(f"Product with SKU {product_data.sku} already exists")

        await ensure_selectable_product_category(db, product_data.category_id, required=True)
        await ensure_brand_exists(db, product_data.brand_id)

        product = await crud_product.create_product(db, product_data)
        await db.commit()
        logger.info(f"Product created successfully: {product.id}")

        return product

    @staticmethod
    async def get_product_details(db: AsyncSession, product_id: int) -> dict | None:
        product = await crud_product.get_product_by_id(db, product_id)
        if not product:
            return None

        quantity = _to_decimal(product.stock_quantity)
        return {
            "product": product,
            "stock_status": stock_status_label(quantity, audience="admin"),
            "low_stock": quantity > Decimal("0.0") and quantity < Decimal("10.0"),
            "availability": product.is_active and quantity > Decimal("0.0"),
        }

    @staticmethod
    async def search_products(
        db: AsyncSession,
        search: str | None = None,
        category_id: int | None = None,
        brand_id: int | None = None,
        is_active: bool | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        spec_filters: dict | None = None,
        country: str | None = None,
        in_stock: bool | None = None,
        sort: str | None = None,
        product_ids: list[int] | None = None,
        skip: int = 0,
        limit: int = 100,
        is_deleted: bool | None = None,
    ) -> tuple[list[Product], int]:
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
            country=country,
            in_stock=in_stock,
            sort=sort,
            product_ids=product_ids,
            is_deleted=is_deleted,
        )

    @staticmethod
    async def update_product_with_validation(
        db: AsyncSession,
        product_id: int,
        update_data: ProductUpdate,
    ) -> Product | None:
        logger.info(f"Updating product: {product_id}")

        product = await crud_product.get_product_by_id(db, product_id)
        if not product:
            return None

        if update_data.sku is not None and update_data.sku != product.sku:
            if await crud_product.check_sku_exists(
                db, update_data.sku, exclude_product_id=product_id
            ):
                raise ValueError(f"Product with SKU {update_data.sku} already exists")

        if "category_id" in update_data.model_fields_set:
            await ensure_selectable_product_category(
                db, update_data.category_id, required=True
            )
        if "brand_id" in update_data.model_fields_set:
            await ensure_brand_exists(db, update_data.brand_id)

        tracked_fields = ("base_price", "original_price", "stock_quantity")
        previous = {field: getattr(product, field, None) for field in tracked_fields}

        updated_product = await crud_product.update_product(db, product_id, update_data)
        for field in tracked_fields:
            if field not in update_data.model_fields_set:
                continue
            old_value = previous[field]
            new_value = getattr(updated_product, field)
            if old_value != new_value:
                await crud_platform.record_product_change(
                    db,
                    product_id=product_id,
                    field_name=field,
                    old_value=str(old_value) if old_value is not None else None,
                    new_value=str(new_value) if new_value is not None else None,
                    reason="product_update",
                )
        await db.commit()
        logger.info(f"Product updated successfully: {product_id}")
        return updated_product

    @staticmethod
    async def adjust_stock_with_validation(
        db: AsyncSession,
        product_id: int,
        quantity_delta: Decimal,
        reason: str | None = None,
        *,
        actor_user_id: int | None = None,
    ) -> Product | None:
        logger.info(
            f"Adjusting stock for product {product_id}: delta={quantity_delta}, reason={reason}"
        )

        product = await crud_product.get_product_by_id(db, product_id)
        if not product:
            return None

        old_stock = product.stock_quantity
        updated_product = await crud_product.update_stock(db, product_id, quantity_delta)
        if updated_product:
            await crud_platform.record_product_change(
                db,
                product_id=product_id,
                field_name="stock_quantity",
                old_value=str(old_stock),
                new_value=str(updated_product.stock_quantity),
                reason=reason,
                actor_user_id=actor_user_id,
            )
            await db.commit()
        return updated_product

    @staticmethod
    async def get_low_stock_products(
        db: AsyncSession, threshold: Decimal = Decimal("10.0"), limit: int = 100
    ) -> list[Product]:
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
    ) -> tuple[list[Product], int]:
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
    async def delete_product(
        db: AsyncSession,
        product_id: int,
        *,
        actor_user_id: int | None = None,
    ) -> bool:
        deleted = await crud_product.delete_product_soft(db, product_id)
        if deleted:
            await crud_platform.record_audit_log(
                db,
                actor_user_id=actor_user_id,
                action="soft_delete",
                entity_type="product",
                entity_id=str(product_id),
            )
            await db.commit()
        return deleted

    @staticmethod
    async def bulk_adjust_stock(
        db: AsyncSession,
        items: list[dict],
        *,
        actor_user_id: int | None = None,
    ) -> list[int]:
        updated_ids: list[int] = []
        for item in items:
            product = await ProductService.adjust_stock_with_validation(
                db,
                product_id=item["product_id"],
                quantity_delta=item["quantity_delta"],
                reason=item.get("reason") or "bulk_adjust",
                actor_user_id=actor_user_id,
            )
            if product is not None:
                updated_ids.append(product.id)
        return updated_ids

    @staticmethod
    async def restore_product(db: AsyncSession, product_id: int) -> Product | None:
        product = await crud_product.restore_product(db, product_id)
        if product:
            await db.commit()
        return product
