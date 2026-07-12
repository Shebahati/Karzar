"""Map ORM Product instances to frontend-facing Pydantic response models."""

from decimal import Decimal

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
from app.utils.specifications import normalize_specifications_for_api
from app.utils.storefront_catalog import (
    Audience,
    compute_discount_percent,
    decimal_to_api_string,
    hierarchy_separator,
    stock_status_label,
)

LOW_STOCK_THRESHOLD = Decimal("10.0")


def stock_status_from_quantity(quantity, *, audience: Audience = "admin") -> str:
    """Derive stock status label for admin or storefront audience."""
    return stock_status_label(quantity, audience=audience)


def get_thumbnail_url(product: Product) -> str | None:
    """Return the primary image URL, falling back to the first image."""
    if not product.images:
        return None
    primary = next((image for image in product.images if image.is_primary), None)
    return (primary or product.images[0]).image_url


def _category_brief(
    product: Product,
    category_metadata: dict[int, CategoryMeta] | None = None,
    *,
    audience: Audience = "storefront",
) -> CategoryBrief | None:
    if product.category is None:
        return None

    breadcrumb: list[str] = []
    if category_metadata and product.category_id in category_metadata:
        breadcrumb = list(category_metadata[product.category_id]["breadcrumb"])
    else:
        breadcrumb = [product.category.name]

    separator = hierarchy_separator(audience)
    hierarchy_label = separator.join(breadcrumb) if breadcrumb else product.category.name

    return CategoryBrief(
        id=product.category.id,
        name=product.category.name,
        breadcrumb=breadcrumb,
        hierarchy_label=hierarchy_label,
    )


def _brand_brief(product: Product) -> BrandBrief | None:
    if product.brand is None:
        return None
    return BrandBrief(
        id=product.brand.id,
        name=product.brand.name,
        country=product.brand.country,
    )


def _images(product: Product) -> list[ProductImageResponse]:
    """Map ORM images to response DTOs; primary image sorts first."""
    return [
        ProductImageResponse(
            id=image.id,
            url=image.image_url,
            is_primary=image.is_primary,
        )
        for image in sorted(product.images, key=lambda img: (not img.is_primary, img.display_order, img.id))
    ]


def to_product_summary(
    product: Product,
    category_metadata: dict[int, CategoryMeta] | None = None,
    *,
    audience: Audience = "storefront",
) -> ProductSummaryResponse:
    """Build the PLP card shape from a loaded Product ORM instance."""
    quantity = _to_decimal(product.stock_quantity)
    low_stock = quantity < LOW_STOCK_THRESHOLD
    return ProductSummaryResponse(
        id=product.id,
        sku=product.sku,
        name=product.name,
        thumbnail=get_thumbnail_url(product),
        base_price=decimal_to_api_string(product.base_price),
        original_price=decimal_to_api_string(product.original_price),
        discount_percent=compute_discount_percent(product.base_price, product.original_price),
        stock_status=stock_status_label(quantity, audience=audience, low_stock=low_stock),
        availability=bool(product.is_active and quantity > Decimal("0.0")),
        is_original=product.is_original,
        category=_category_brief(product, category_metadata, audience=audience),
        brand=_brand_brief(product),
    )


def to_product_detail(
    product: Product,
    category_metadata: dict[int, CategoryMeta] | None = None,
    *,
    audience: Audience = "storefront",
) -> ProductDetailResponse:
    """Build the full PDP shape including computed stock fields."""
    quantity = _to_decimal(product.stock_quantity)
    low_stock = quantity < LOW_STOCK_THRESHOLD
    return ProductDetailResponse(
        id=product.id,
        sku=product.sku,
        name=product.name,
        category_id=product.category_id,
        brand_id=product.brand_id,
        category=_category_brief(product, category_metadata, audience=audience),
        brand=_brand_brief(product),
        base_price=decimal_to_api_string(product.base_price),
        original_price=decimal_to_api_string(product.original_price),
        discount_percent=compute_discount_percent(product.base_price, product.original_price),
        stock_quantity=decimal_to_api_string(quantity) or "0",
        stock_unit=product.stock_unit.value if hasattr(product.stock_unit, "value") else str(product.stock_unit),
        stock_status=stock_status_label(quantity, audience=audience, low_stock=low_stock),
        low_stock=low_stock,
        availability=bool(product.is_active and quantity > Decimal("0.0")),
        warranty_text=product.warranty_text,
        weight_grams=decimal_to_api_string(product.weight_grams),
        is_original=product.is_original,
        tax_percent=decimal_to_api_string(product.tax_percent) or "0",
        is_active=product.is_active,
        pdf_catalog_url=product.pdf_catalog_url,
        description=product.description,
        thumbnail=get_thumbnail_url(product),
        images=_images(product),
        specifications=normalize_specifications_for_api(
            dict(product.specifications or {}),
            audience=audience,
        ),
        created_at=product.created_at,
        updated_at=product.updated_at,
    )
