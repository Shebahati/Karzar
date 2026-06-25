"""Map ORM Product instances to frontend-facing Pydantic response models."""

from decimal import Decimal
from typing import Dict, List, Optional

from app.db.models.product import Product
from app.schemas.product import (
    BrandBrief,
    CategoryBrief,
    ProductDetailResponse,
    ProductImageResponse,
    ProductSummaryResponse,
)
from app.utils.category_depth import CategoryMeta
from app.utils.decimal_utils import to_decimal as _to_decimal

LOW_STOCK_THRESHOLD = Decimal("10.0")
HIERARCHY_SEPARATOR = " > "


def stock_status_from_quantity(quantity) -> str:
    """Derive in_stock / out_of_stock from a numeric quantity."""
    return "in_stock" if _to_decimal(quantity) > Decimal("0.0") else "out_of_stock"


def get_thumbnail_url(product: Product) -> Optional[str]:
    """Return the primary image URL, falling back to the first image."""
    if not product.images:
        return None
    primary = next((image for image in product.images if image.is_primary), None)
    return (primary or product.images[0]).image_url


def _category_brief(
    product: Product,
    category_metadata: Optional[Dict[int, CategoryMeta]] = None,
) -> Optional[CategoryBrief]:
    if product.category is None:
        return None

    breadcrumb: List[str] = []
    if category_metadata and product.category_id in category_metadata:
        breadcrumb = list(category_metadata[product.category_id]["breadcrumb"])
    else:
        breadcrumb = [product.category.name]

    hierarchy_label = HIERARCHY_SEPARATOR.join(breadcrumb) if breadcrumb else product.category.name

    return CategoryBrief(
        id=product.category.id,
        name=product.category.name,
        breadcrumb=breadcrumb,
        hierarchy_label=hierarchy_label,
    )


def _brand_brief(product: Product) -> Optional[BrandBrief]:
    if product.brand is None:
        return None
    return BrandBrief(id=product.brand.id, name=product.brand.name)


def _images(product: Product) -> List[ProductImageResponse]:
    """Map ORM images to response DTOs; primary image sorts first."""
    return [
        ProductImageResponse(
            id=image.id,
            url=image.image_url,
            is_primary=image.is_primary,
        )
        for image in sorted(product.images, key=lambda img: (not img.is_primary, img.id))
    ]


def to_product_summary(
    product: Product,
    category_metadata: Optional[Dict[int, CategoryMeta]] = None,
) -> ProductSummaryResponse:
    """Build the PLP card shape from a loaded Product ORM instance."""
    return ProductSummaryResponse(
        id=product.id,
        sku=product.sku,
        name=product.name,
        thumbnail=get_thumbnail_url(product),
        base_price=product.base_price,
        stock_status=stock_status_from_quantity(product.stock_quantity),
        category=_category_brief(product, category_metadata),
        brand=_brand_brief(product),
    )


def to_product_detail(
    product: Product,
    category_metadata: Optional[Dict[int, CategoryMeta]] = None,
) -> ProductDetailResponse:
    """Build the full PDP shape including computed stock fields."""
    quantity = _to_decimal(product.stock_quantity)
    return ProductDetailResponse(
        id=product.id,
        sku=product.sku,
        name=product.name,
        category_id=product.category_id,
        brand_id=product.brand_id,
        category=_category_brief(product, category_metadata),
        brand=_brand_brief(product),
        base_price=product.base_price,
        stock_quantity=quantity,
        stock_unit=product.stock_unit.value if hasattr(product.stock_unit, "value") else str(product.stock_unit),
        stock_status=stock_status_from_quantity(quantity),
        low_stock=quantity < LOW_STOCK_THRESHOLD,
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
