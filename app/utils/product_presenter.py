from decimal import Decimal
from typing import List, Optional

from app.db.models.product import Product
from app.schemas.product import (
    BrandBrief,
    CategoryBrief,
    ProductDetailResponse,
    ProductImageResponse,
    ProductSummaryResponse,
)


def _to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def stock_status_from_quantity(quantity) -> str:
    return "in_stock" if _to_decimal(quantity) > Decimal("0.0") else "out_of_stock"


def get_thumbnail_url(product: Product) -> Optional[str]:
    if not product.images:
        return None
    primary = next((image for image in product.images if image.is_primary), None)
    return (primary or product.images[0]).image_url


def _category_brief(product: Product) -> Optional[CategoryBrief]:
    if product.category is None:
        return None
    return CategoryBrief(id=product.category.id, name=product.category.name)


def _brand_brief(product: Product) -> Optional[BrandBrief]:
    if product.brand is None:
        return None
    return BrandBrief(id=product.brand.id, name=product.brand.name)


def _images(product: Product) -> List[ProductImageResponse]:
    return [
        ProductImageResponse(
            id=image.id,
            url=image.image_url,
            is_primary=image.is_primary,
        )
        for image in sorted(product.images, key=lambda img: (not img.is_primary, img.id))
    ]


def to_product_summary(product: Product) -> ProductSummaryResponse:
    return ProductSummaryResponse(
        id=product.id,
        sku=product.sku,
        name=product.name,
        thumbnail=get_thumbnail_url(product),
        base_price=product.base_price,
        stock_status=stock_status_from_quantity(product.stock_quantity),
        category=_category_brief(product),
        brand=_brand_brief(product),
    )


def to_product_detail(product: Product) -> ProductDetailResponse:
    quantity = _to_decimal(product.stock_quantity)
    return ProductDetailResponse(
        id=product.id,
        sku=product.sku,
        name=product.name,
        category_id=product.category_id,
        brand_id=product.brand_id,
        category=_category_brief(product),
        brand=_brand_brief(product),
        base_price=product.base_price,
        stock_quantity=quantity,
        stock_unit=product.stock_unit.value if hasattr(product.stock_unit, "value") else str(product.stock_unit),
        stock_status=stock_status_from_quantity(quantity),
        low_stock=quantity < Decimal("10.0"),
        availability=bool(product.is_active and quantity > Decimal("0.0")),
        warranty_text=product.warranty_text,
        weight_grams=product.weight_grams,
        is_original=product.is_original,
        tax_percent=product.tax_percent,
        is_active=product.is_active,
        pdf_catalog_url=product.pdf_catalog_url,
        thumbnail=get_thumbnail_url(product),
        images=_images(product),
        specifications=dict(product.specifications or {}),
        created_at=product.created_at,
        updated_at=product.updated_at,
    )

