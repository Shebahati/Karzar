"""Regression: missing product images must not gate website publication."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from app.core.config import settings
from app.crud import brand as crud_brand
from app.crud import product as crud_product
from app.db.models.product import Brand, Category, Product, ProductImage
from app.services.emalls.eligibility import product_eligible_for_emalls_export
from app.utils.public_catalog import (
    filter_storefront_public_products,
    is_product_storefront_public,
    product_passes_storefront_materialization_guard,
    storefront_public_product_filters,
)
from tests.conftest import TestingSessionLocal


def _product(**kwargs) -> Product:
    defaults = {
        "sku": "IMG-POLICY-1",
        "name": "Policy test",
        "category_id": 3,
        "is_active": True,
        "is_available": True,
        "base_price": 1000,
        "slug": "policy-test",
    }
    defaults.update(kwargs)
    return Product(**defaults)


def test_storefront_filters_exclude_only_active_not_deleted():
    assert len(storefront_public_product_filters()) == 2


def test_active_without_image_is_storefront_public():
    product = _product()
    product.images = []
    assert is_product_storefront_public(product) is True
    assert product in filter_storefront_public_products([product])


def test_active_placeholder_only_is_storefront_public():
    product = _product()
    product.images = [
        ProductImage(
            product_id=1,
            image_url="/images/placeholders/karzar-editorial.svg",
            is_primary=True,
        )
    ]
    assert is_product_storefront_public(product) is True


def test_active_missing_disk_file_still_public(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "STOREFRONT_REQUIRE_MATERIALIZED_IMAGES", True)
    upload_root = tmp_path / "uploads"
    upload_root.mkdir(parents=True)
    monkeypatch.setattr("app.utils.file_storage.UPLOAD_ROOT", upload_root)

    product = _product()
    product.images = [
        ProductImage(
            product_id=1,
            image_url="/static/uploads/products/1/missing.webp",
            is_primary=True,
        )
    ]
    assert is_product_storefront_public(product) is True
    assert product_passes_storefront_materialization_guard(product) is False


def test_inactive_with_valid_image_not_public():
    product = _product(is_active=False)
    product.images = [
        ProductImage(product_id=1, image_url="/media/p/1.webp", is_primary=True)
    ]
    assert is_product_storefront_public(product) is False


def test_soft_deleted_without_image_not_public():
    product = _product()
    product.deleted_at = datetime.now(UTC)
    product.images = []
    assert is_product_storefront_public(product) is False


def test_emalls_export_still_requires_image():
    product = _product()
    product.images = []
    assert is_product_storefront_public(product) is True
    assert product_eligible_for_emalls_export(product) is False


@pytest.mark.usefixtures("override_database")
def test_brand_storefront_count_includes_imageless_active():
    async def run():
        async with TestingSessionLocal() as session:
            brand = Brand(name="ImgPolicyBrand", country="IR", slug="img-policy-brand")
            session.add(brand)
            await session.flush()
            with_image = _product(sku="WP-IMG", brand_id=brand.id, slug="with-img")
            no_image = _product(sku="NO-IMG", brand_id=brand.id, slug="no-img")
            session.add_all([with_image, no_image])
            await session.flush()
            session.add_all(
                [
                    ProductImage(
                        product_id=with_image.id,
                        image_url="/media/p/w.webp",
                        is_primary=True,
                    ),
                ]
            )
            await session.commit()
            count = await crud_brand.count_products_for_brand(
                session, brand.id, storefront_public_only=True
            )
            assert count == 2

    asyncio.run(run())


@pytest.mark.usefixtures("override_database")
def test_related_products_include_imageless_peer():
    async def run():
        async with TestingSessionLocal() as session:
            cat = Category(name="ImgPolicyCat", slug="img-policy-cat")
            session.add(cat)
            await session.flush()
            anchor = _product(
                sku="ANCHOR",
                category_id=cat.id,
                slug="anchor-product",
            )
            peer = _product(
                sku="PEER-NOIMG",
                category_id=cat.id,
                slug="peer-no-img",
            )
            session.add_all([anchor, peer])
            await session.flush()
            session.add(
                ProductImage(
                    product_id=anchor.id,
                    image_url="/media/p/a.webp",
                    is_primary=True,
                )
            )
            await session.commit()
            related = await crud_product.get_related_products(session, anchor.id, limit=6)
            related_ids = {p.id for p in related}
            assert peer.id in related_ids

    asyncio.run(run())


@pytest.mark.usefixtures("override_database")
def test_sql_python_storefront_eligibility_agree():
    async def run():
        async with TestingSessionLocal() as session:
            active_no_img = _product(sku="SQL-PY-1", slug="sql-py-1")
            session.add(active_no_img)
            await session.commit()
            await session.refresh(active_no_img)
            assert is_product_storefront_public(active_no_img) is True
            listed, total = await crud_product.get_products(
                session,
                skip=0,
                limit=50,
                storefront_public_only=True,
                product_ids=[active_no_img.id],
            )
            assert total == 1
            assert len(listed) == 1

    asyncio.run(run())
