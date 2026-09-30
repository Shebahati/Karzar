"""Direct Emalls PDF feed: eligibility, presentation, pagination (read-only).

Source of truth: Emalls PDF «راهنمای ایجاد صفحه معرفی محصولات به ایمالز».
Does not share response contracts with the WordPress `/products` adapter.
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlparse

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models.product import Product
from app.schemas.emalls_pdf_feed import (
    EMALLS_PDF_MAX_ITEM_PER_PAGE,
    EmallsPdfFeedResponse,
    EmallsPdfProduct,
)
from app.utils.product_presenter import absolutize_asset_url
from app.utils.public_catalog import (
    filter_storefront_public_products,
    get_first_valid_public_image_url,
    storefront_public_product_filters,
)
from app.utils.storefront_catalog import product_is_available

logger = get_logger(__name__)


class EmallsPdfFeedIntegrityError(ValueError):
    """Product cannot satisfy the PDF required field contract."""


def decimal_to_exact_toman_int(value: Decimal) -> int:
    """Convert a Decimal price to JSON integer Toman without truncation.

    Raises EmallsPdfFeedIntegrityError when the value is not an exact integer.
    """
    normalized = Decimal(value)
    if normalized != normalized.to_integral_value():
        raise EmallsPdfFeedIntegrityError("price has a fractional Toman component")
    as_int = int(normalized)
    if Decimal(as_int) != normalized:
        raise EmallsPdfFeedIntegrityError("price integer conversion failed")
    return as_int


def is_exact_positive_toman(value: Decimal | None) -> bool:
    if value is None:
        return False
    try:
        return decimal_to_exact_toman_int(value) > 0
    except EmallsPdfFeedIntegrityError:
        return False


def emalls_pdf_feed_filters() -> list[ColumnElement[bool]]:
    """SQL filters for PDF-feed eligibility (superset of storefront public).

    Required by Emalls PDF: price is mandatory → unpriced products are excluded.
    Availability is NOT an inclusion requirement.
    """
    filters = list(storefront_public_product_filters())
    filters.append(Product.base_price.isnot(None))
    filters.append(Product.base_price > 0)
    # Exact integer Toman: value equals its rounded integer form (no silent trunc).
    filters.append(Product.base_price == func.round(Product.base_price, 0))
    filters.append(func.length(func.trim(Product.name)) > 0)
    filters.append(func.length(func.trim(Product.slug)) > 0)
    filters.append(Product.category_id.isnot(None))
    return filters


def _is_public_https_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return False
    host = (parsed.hostname or "").lower()
    blocked = (
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
    )
    if host in blocked or host.endswith(".local"):
        return False
    if "staging" in host or "catalog-staging" in host:
        return False
    return True


def _product_url(product: Product) -> str:
    origin = (settings.EMALLS_PUBLIC_SITE_ORIGIN or "").rstrip("/")
    slug = (product.slug or "").strip()
    if not origin or not slug:
        raise EmallsPdfFeedIntegrityError("missing site origin or slug")
    url = f"{origin}/product/{quote(slug, safe='')}"
    if not _is_public_https_url(url):
        raise EmallsPdfFeedIntegrityError("product url is not a public HTTPS URL")
    return url


def _primary_image_url(product: Product) -> str:
    raw = get_first_valid_public_image_url(product)
    if not raw:
        raise EmallsPdfFeedIntegrityError("missing public image")
    absolute = absolutize_asset_url(raw) or raw
    if not _is_public_https_url(absolute):
        raise EmallsPdfFeedIntegrityError("image url is not a public HTTPS URL")
    return absolute


def product_satisfies_pdf_feed(product: Product) -> bool:
    """In-memory PDF eligibility (post SQL + optional materialization)."""
    if product.deleted_at is not None:
        return False
    if not product.is_active:
        return False
    name = (product.name or "").strip()
    slug = (product.slug or "").strip()
    if not name or not slug:
        return False
    if product.category is None or not (product.category.name or "").strip():
        return False
    if not is_exact_positive_toman(product.base_price):
        return False
    try:
        _primary_image_url(product)
        _product_url(product)
    except EmallsPdfFeedIntegrityError:
        return False
    return True


def present_emalls_pdf_product(product: Product) -> EmallsPdfProduct:
    title = (product.name or "").strip()
    if not title:
        raise EmallsPdfFeedIntegrityError("empty title")
    category_name = ""
    if product.category is not None:
        category_name = (product.category.name or "").strip()
    if not category_name:
        raise EmallsPdfFeedIntegrityError("missing category")

    price = decimal_to_exact_toman_int(product.base_price)  # type: ignore[arg-type]
    if price <= 0:
        raise EmallsPdfFeedIntegrityError("non-positive price")

    old_price: int | None = None
    if product.original_price is not None:
        try:
            old_price = decimal_to_exact_toman_int(product.original_price)
        except EmallsPdfFeedIntegrityError:
            # Optional field: never truncate fractional Toman; omit bad value.
            old_price = None
            logger.warning(
                "integration=emalls_pdf_feed product_id=%s fractional_old_price_omitted",
                product.id,
            )

    # Karzar has no canonical public color field on Product.
    color = ""

    return EmallsPdfProduct(
        title=title,
        id=str(product.id),
        price=price,
        old_price=old_price,
        category=category_name,
        image=_primary_image_url(product),
        color=color,
        guarantee=(product.warranty_text or "") if product.warranty_text else "",
        is_available=product_is_available(product),
        url=_product_url(product),
    )


def _load_options() -> tuple[Any, ...]:
    return (
        selectinload(Product.images),
        selectinload(Product.category),
    )


async def list_emalls_pdf_feed(
    db: AsyncSession,
    *,
    page: int,
    item_per_page: int,
) -> EmallsPdfFeedResponse:
    """Paginate PDF-eligible products ordered by Product.id DESC."""
    if page < 1:
        raise ValueError("page must be >= 1")
    if item_per_page < 1 or item_per_page > EMALLS_PDF_MAX_ITEM_PER_PAGE:
        raise ValueError("item_per_page out of range")

    filters = emalls_pdf_feed_filters()
    where_clause = and_(*filters)
    materialized = bool(settings.STOREFRONT_REQUIRE_MATERIALIZED_IMAGES)
    skip = (page - 1) * item_per_page

    if materialized:
        all_stmt = (
            select(Product)
            .where(where_clause)
            .options(*_load_options())
            .order_by(Product.id.desc())
        )
        candidates = list((await db.execute(all_stmt)).scalars().all())
        # Materialized image gate + PDF-required field surface.
        eligible = [
            product
            for product in filter_storefront_public_products(candidates)
            if product_satisfies_pdf_feed(product)
        ]
        total = len(eligible)
        page_rows = eligible[skip : skip + item_per_page]
    else:
        count_stmt = select(func.count(Product.id)).where(where_clause)
        total = int((await db.execute(count_stmt)).scalar() or 0)
        page_stmt = (
            select(Product)
            .where(where_clause)
            .options(*_load_options())
            .order_by(Product.id.desc())
            .offset(skip)
            .limit(item_per_page)
        )
        page_rows = list((await db.execute(page_stmt)).scalars().all())
        # Drop any rows that fail URL/image HTTPS presentation (rare).
        page_rows = [p for p in page_rows if product_satisfies_pdf_feed(p)]

    pages_count = math.ceil(total / item_per_page) if total > 0 else 0
    products: list[EmallsPdfProduct] = []
    for product in page_rows:
        try:
            products.append(present_emalls_pdf_product(product))
        except EmallsPdfFeedIntegrityError:
            continue

    logger.info(
        "integration=emalls_pdf_feed page=%s item_per_page=%s product_count=%s "
        "total_items=%s pages_count=%s",
        page,
        item_per_page,
        len(products),
        total,
        pages_count,
    )

    return EmallsPdfFeedResponse(
        success=True,
        products=products,
        total_items=total,
        pages_count=pages_count,
        item_per_page=item_per_page,
        page_num=page,
    )
