"""Central predicates for public storefront catalog visibility and ordering."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sqlalchemy import and_, case, exists, func, or_, select
from sqlalchemy.sql.elements import ColumnElement

from app.core.config import settings
from app.db.models.product import Product, ProductImage

if TYPE_CHECKING:
    from sqlalchemy.orm import InstrumentedAttribute

# Known generic placeholders — never treat as a real public product image.
# Keep SQL ILIKE tokens in sync with these patterns (see public_image_exists_clause).
_PLACEHOLDER_ILIKE_TOKENS = (
    "placeholder",
    "woocommerce-placeholder",
    "no-image",
    "no_image",
    "noimage",
    "default-image",
    "default_image",
    "default-product",
    "default_product",
    "karzar-editorial",
    "/images/placeholders/",
)

_PLACEHOLDER_PATTERNS = (
    re.compile(r"placeholder", re.I),
    re.compile(r"woocommerce-placeholder", re.I),
    re.compile(r"no[-_]?image", re.I),
    re.compile(r"default[-_]?(image|product)", re.I),
    re.compile(r"karzar-editorial\.svg", re.I),
    re.compile(r"/images/placeholders/", re.I),
)

VALID_IMAGE_URL_EXPR = and_(
    ProductImage.image_url.isnot(None),
    func.length(func.trim(ProductImage.image_url)) > 0,
)


def is_placeholder_image_url(url: str | None) -> bool:
    if not url or not str(url).strip():
        return True
    normalized = str(url).strip()
    return any(pattern.search(normalized) for pattern in _PLACEHOLDER_PATTERNS)


def product_has_valid_public_image(product: Product) -> bool:
    """True when the product has at least one non-placeholder public image."""
    return get_first_valid_public_image_url(product) is not None


def get_first_valid_public_image_url(product: Product) -> str | None:
    """Return the best non-placeholder image URL for storefront display."""
    if not product.images:
        return None
    ordered = sorted(
        product.images,
        key=lambda image: (not image.is_primary, image.display_order, image.id),
    )
    for image in ordered:
        url = (image.image_url or "").strip()
        if url and not is_placeholder_image_url(url):
            return url
    return None


def local_upload_relative_path(url: str | None) -> str | None:
    """Map a public upload URL to a path under ``data/uploads/`` when possible."""
    if not url:
        return None
    normalized = str(url).strip()
    marker = "/static/uploads/"
    idx = normalized.find(marker)
    if idx < 0:
        marker = "static/uploads/"
        idx = normalized.find(marker)
    if idx < 0:
        return None
    relative = normalized[idx + len(marker) :].lstrip("/")
    return relative or None


def product_image_materialized_on_disk(url: str | None) -> bool:
    """True when the upload file exists locally (no remote HTTP probe)."""
    relative = local_upload_relative_path(url)
    if relative is None:
        return True
    from app.utils.file_storage import UPLOAD_ROOT

    return (UPLOAD_ROOT / relative).is_file()


def product_has_materialized_public_image(product: Product) -> bool:
    url = get_first_valid_public_image_url(product)
    if not url:
        return False
    return product_image_materialized_on_disk(url)


def product_has_storefront_public_image(product: Product) -> bool:
    """URL/placeholder guard plus optional on-disk materialization in DEBUG/local."""
    if not product_has_valid_public_image(product):
        return False
    if settings.STOREFRONT_REQUIRE_MATERIALIZED_IMAGES:
        return product_has_materialized_public_image(product)
    return True


def filter_storefront_public_products(products: list[Product]) -> list[Product]:
    return [product for product in products if product_has_storefront_public_image(product)]


def public_image_exists_clause() -> ColumnElement[bool]:
    """SQL EXISTS for products with a real (non-placeholder) image row."""
    return exists(
        select(ProductImage.id).where(
            ProductImage.product_id == Product.id,
            VALID_IMAGE_URL_EXPR,
            *[
                ~ProductImage.image_url.ilike(f"%{token}%", escape="\\")
                for token in _PLACEHOLDER_ILIKE_TOKENS
            ],
        )
    )


def availability_rank_clause() -> InstrumentedAttribute:
    """0 = available (active + is_available), 1 = unavailable — primary list partition."""
    return case(
        (
            and_(Product.is_active.is_(True), Product.is_available.is_(True)),
            0,
        ),
        else_=1,
    )


def storefront_public_product_filters() -> list[ColumnElement[bool]]:
    """Filters applied to every public product list/detail guard."""
    return [
        Product.deleted_at.is_(None),
        Product.is_active.is_(True),
        public_image_exists_clause(),
    ]
