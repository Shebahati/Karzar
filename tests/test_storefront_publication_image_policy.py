"""Regression: missing product images must not gate website publication."""

import asyncio

import pytest
from app.db.models.product import Product, ProductImage
from app.utils.public_catalog import (
    is_product_storefront_public,
    product_has_storefront_public_image,
    storefront_public_product_filters,
)
from tests.conftest import TestingSessionLocal
from app.crud import brand as crud_brand
from app.crud import product as crud_product


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
    assert product_has_storefront_public_image(product) is True


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


def test_inactive_with_valid_image_not_public():
    product = _product(is_active=False)
    product.images = [
        ProductImage(product_id=1, image_url="/media/p/1.webp", is_primary=True)
    ]
    assert is_product_storefront_public(product) is False


def test_soft_deleted_without_image_not_public():
    from datetime import UTC, datetime

    product = _product()
    product.deleted_at = datetime.now(UTC)
    product.images = []
    assert is_product_storefront_public(product) is False


@pytest.mark.usefixtures("override_database")
def test_brand_storefront_count_includes_imageless_active():
    async def run():
        from app.db.models.brand import Brand

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
        from app.db.models.category import Category

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
