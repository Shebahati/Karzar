"""Map Karzar public products to the Emalls extraction product shape."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote

from app.core.config import settings
from app.db.models.product import Product
from app.schemas.emalls import EmallsProduct
from app.utils.product_presenter import absolutize_asset_url
from app.utils.public_catalog import is_placeholder_image_url
from app.utils.specifications import normalize_specifications_for_api
from app.utils.storefront_catalog import decimal_to_api_string, product_is_available

SKU_SPEC_KEY = "شناسه کالا"


def _iso8601(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        return value.isoformat() + "Z"
    return value.isoformat()


def _price_string(value: Decimal | None) -> str:
    """Pass-through TOMAN string. Null → empty string (no fabricated zero)."""
    if value is None:
        return ""
    text = decimal_to_api_string(value)
    return text if text is not None else ""


def _emalls_old_price(product: Product) -> str:
    """Map Emalls old_price to WooCommerce regular-price semantics.

    Karzar ``original_price`` is the strike-through/pre-discount value and is
    normally NULL when there is no discount. Official Emalls/WooCommerce
    ``get_regular_price()`` equals ``get_price()`` for non-sale products, so
    fall back to ``base_price`` only inside this adapter — do not mutate DB.
    """
    if product.original_price is not None:
        return _price_string(product.original_price)
    return _price_string(product.base_price)


def _availability_label(product: Product) -> str:
    return "instock" if product_is_available(product) else "outofstock"


def _page_url(product: Product) -> str:
    origin = (settings.EMALLS_PUBLIC_SITE_ORIGIN or "").rstrip("/")
    slug = (product.slug or "").strip()
    if not origin or not slug:
        return ""
    return f"{origin}/product/{quote(slug, safe='')}"


def _public_image_urls(product: Product) -> list[str]:
    rows = sorted(
        product.images or [],
        key=lambda image: (not image.is_primary, image.display_order, image.id),
    )
    urls: list[str] = []
    seen: set[str] = set()
    for image in rows:
        raw = (image.image_url or "").strip()
        if not raw or is_placeholder_image_url(raw):
            continue
        absolute = absolutize_asset_url(raw) or raw
        if absolute in seen:
            continue
        seen.add(absolute)
        urls.append(absolute)
    return urls


def _feature_value_string(value: Any) -> str | None:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _flatten_public_specs(product: Product) -> dict[str, str]:
    """Build a flat Emalls spec object from storefront-normalized specs only.

    Includes public ``technical_specs``, ``dimensions``, and scalar ``features``.
    Does not leak unknown root JSONB keys or optional_accessories.
    """
    normalized = normalize_specifications_for_api(
        dict(product.specifications or {}),
        audience="storefront",
    )
    flat: dict[str, str] = {}
    for section in ("technical_specs", "dimensions"):
        rows = normalized.get(section) or []
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            key = str(row.get("key") or "").strip()
            value = row.get("value")
            if not key or value is None:
                continue
            text = str(value).strip()
            if not text:
                continue
            if key not in flat:
                flat[key] = text

    features = normalized.get("features") or {}
    if isinstance(features, dict):
        for key, value in features.items():
            feature_key = str(key).strip()
            if not feature_key or feature_key in flat:
                continue
            text = _feature_value_string(value)
            if text is None:
                continue
            flat[feature_key] = text
    return flat


def build_emalls_spec(product: Product) -> list[dict[str, str]]:
    """Official-plugin shape: one-element array of a flat key/value object.

    Always include SKU as ``شناسه کالا`` when present. Do not invent technical specs.
    """
    spec = _flatten_public_specs(product)
    sku = (product.sku or "").strip()
    if sku:
        existing = spec.get(SKU_SPEC_KEY)
        if existing is None or not str(existing).strip():
            spec[SKU_SPEC_KEY] = sku
    if not spec:
        return []
    return [spec]


def present_emalls_product(product: Product) -> EmallsProduct:
    images = _public_image_urls(product)
    category_name = ""
    if product.category is not None and product.category.name:
        category_name = product.category.name

    return EmallsProduct(
        title=product.name or "",
        subtitle="",
        parent_id=0,
        page_unique=product.id,
        current_price=_price_string(product.base_price),
        old_price=_emalls_old_price(product),
        availability=_availability_label(product),
        category_name=category_name,
        image_link=images[0] if images else "",
        image_links=images,
        page_url=_page_url(product),
        short_desc=(product.short_description or "") if product.short_description else "",
        spec=build_emalls_spec(product),
        date_added=_iso8601(product.created_at),
        date_updated=_iso8601(product.updated_at),
        product_type="simple",
        registry="",
        guarantee=(product.warranty_text or "") if product.warranty_text else "",
    )


def present_emalls_products(products: list[Product]) -> list[EmallsProduct]:
    return [present_emalls_product(product) for product in products]


def redact_token_for_logs(token: str) -> str:
    """Never log the raw Emalls token."""
    del token
    return "[redacted]"


def safe_request_summary(*, page: int, limit: int, **extra: Any) -> dict[str, Any]:
    payload = {"integration": "emalls", "page": page, "limit": limit}
    payload.update(extra)
    return payload
