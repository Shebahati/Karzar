"""Emalls export eligibility (separate from website publication contract)."""

from __future__ import annotations

from sqlalchemy.sql.elements import ColumnElement

from app.db.models.product import Product
from app.utils.public_catalog import (
    product_has_valid_public_image,
    product_passes_storefront_materialization_guard,
    public_image_exists_clause,
    storefront_public_product_filters,
)


def emalls_export_product_filters() -> list[ColumnElement[bool]]:
    """SQL filters for Emalls candidate pages (website visibility + marketplace image rule)."""
    return [
        *storefront_public_product_filters(),
        public_image_exists_clause(),
    ]


def product_eligible_for_emalls_export(product: Product) -> bool:
    """Python-side Emalls eligibility after SQL prefilter."""
    if product.deleted_at is not None or not product.is_active:
        return False
    if not product_has_valid_public_image(product):
        return False
    return product_passes_storefront_materialization_guard(product)


def filter_emalls_export_products(products: list[Product]) -> list[Product]:
    return [product for product in products if product_eligible_for_emalls_export(product)]
