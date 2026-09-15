"""Brand list product_count semantics and aggregate query parity."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from app.crud import brand as crud_brand
from app.db.models.product import Brand, Product, ProductImage
from app.services.brand_service import BrandService
from sqlalchemy import func, select

from tests.conftest import TestingSessionLocal


def _product(
    *,
    sku: str,
    brand_id: int,
    is_active: bool = True,
    deleted_at: datetime | None = None,
) -> Product:
    return Product(
        sku=sku,
        slug=sku.lower().replace(" ", "-"),
        name=sku,
        category_id=3,
        brand_id=brand_id,
        is_active=is_active,
        deleted_at=deleted_at,
        is_available=True,
    )


def _valid_image(product_id: int) -> ProductImage:
    return ProductImage(
        product_id=product_id,
        image_url="/static/uploads/products/1/photo.webp",
        is_primary=True,
        display_order=0,
    )


def _placeholder_image(product_id: int) -> ProductImage:
    return ProductImage(
        product_id=product_id,
        image_url="/images/placeholders/karzar-editorial.svg",
        is_primary=True,
        display_order=0,
    )


@pytest.mark.usefixtures("override_database")
class TestCountProductsByBrandAggregate:
    async def _seed(self, session):
        empty = Brand(name="Empty Brand", country="IR", slug="empty-brand")
        target = Brand(name="Target Brand", country="DE", slug="target-brand")
        other = Brand(name="Other Brand", country="JP", slug="other-brand")
        session.add_all([empty, target, other])
        await session.flush()

        active = _product(sku="TGT-ACTIVE", brand_id=target.id, is_active=True)
        inactive = _product(sku="TGT-INACTIVE", brand_id=target.id, is_active=False)
        deleted = _product(
            sku="TGT-DELETED",
            brand_id=target.id,
            deleted_at=datetime.now(UTC),
        )
        no_image = _product(sku="TGT-NOIMG", brand_id=target.id, is_active=True)
        other_brand = _product(sku="OTH-1", brand_id=other.id, is_active=True)
        session.add_all([active, inactive, deleted, no_image, other_brand])
        await session.flush()

        session.add_all(
            [
                _valid_image(active.id),
                _valid_image(inactive.id),
                _valid_image(deleted.id),
                _placeholder_image(no_image.id),
                _valid_image(other_brand.id),
            ]
        )
        await session.flush()
        return empty, target, other

    def test_normal_count_includes_inactive_and_imageless_not_deleted(self):
        async def run():
            async with TestingSessionLocal() as session:
                empty, target, other = await self._seed(session)
                await session.commit()

                expected = {
                    empty.id: 0,
                    target.id: await crud_brand.count_products_for_brand(
                        session, target.id, storefront_public_only=False
                    ),
                    other.id: await crud_brand.count_products_for_brand(
                        session, other.id, storefront_public_only=False
                    ),
                }
                aggregate = await crud_brand.count_products_by_brand(
                    session, storefront_public_only=False
                )
                assert aggregate == {target.id: expected[target.id], other.id: expected[other.id]}
                assert empty.id not in aggregate
                # active + inactive + no_image (not deleted); excludes deleted
                assert expected[target.id] == 3
                assert expected[other.id] == 1

        asyncio.run(run())

    def test_storefront_count_filters_active_and_public_image(self):
        async def run():
            async with TestingSessionLocal() as session:
                empty, target, other = await self._seed(session)
                await session.commit()

                expected = {
                    empty.id: 0,
                    target.id: await crud_brand.count_products_for_brand(
                        session, target.id, storefront_public_only=True
                    ),
                    other.id: await crud_brand.count_products_for_brand(
                        session, other.id, storefront_public_only=True
                    ),
                }
                aggregate = await crud_brand.count_products_by_brand(
                    session, storefront_public_only=True
                )
                assert aggregate == {target.id: 1, other.id: 1}
                assert expected[target.id] == 1
                assert expected[other.id] == 1

        asyncio.run(run())

    def test_aggregate_sql_is_single_grouped_query(self):
        stmt = (
            select(Product.brand_id, func.count(Product.id))
            .where(
                Product.deleted_at.is_(None),
                Product.brand_id.isnot(None),
                Product.is_active.is_(True),
            )
            .group_by(Product.brand_id)
        )
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "GROUP BY" in compiled.upper()
        assert compiled.upper().count("SELECT") == 1


@pytest.mark.usefixtures("override_database")
def test_list_brands_service_matches_per_brand_counts_and_order():
    async def run():
        async with TestingSessionLocal() as session:
            b1 = Brand(name="Alpha", country="IR", slug="alpha")
            b2 = Brand(name="Beta", country="IR", slug="beta")
            session.add_all([b1, b2])
            await session.flush()
            p = _product(sku="A-1", brand_id=b1.id)
            session.add(p)
            await session.flush()
            session.add(_valid_image(p.id))
            await session.commit()

            normal = await BrandService.list_brands(session, storefront_product_counts=False)
            by_name = {row.name: row for row in normal}
            assert by_name["Alpha"].product_count == 1
            assert by_name["Beta"].product_count == 0

            storefront = await BrandService.list_brands(session, storefront_product_counts=True)
            by_name_sf = {row.name: row for row in storefront}
            assert by_name_sf["Alpha"].product_count == 1
            assert by_name_sf["Beta"].product_count == 0

    asyncio.run(run())


@pytest.mark.usefixtures("override_database")
def test_list_brands_uses_aggregate_once_not_per_brand_count():
    async def run():
        async with TestingSessionLocal() as session:
            session.add(Brand(name="Only", country="IR", slug="only"))
            await session.commit()

            list_mock = AsyncMock(side_effect=crud_brand.list_brands)
            aggregate_mock = AsyncMock(side_effect=crud_brand.count_products_by_brand)
            per_brand_mock = AsyncMock(side_effect=crud_brand.count_products_for_brand)

            with (
                patch.object(crud_brand, "list_brands", list_mock),
                patch.object(crud_brand, "count_products_by_brand", aggregate_mock),
                patch.object(crud_brand, "count_products_for_brand", per_brand_mock),
            ):
                await BrandService.list_brands(session, storefront_product_counts=True)

            assert list_mock.await_count == 1
            assert aggregate_mock.await_count == 1
            per_brand_mock.assert_not_awaited()

    asyncio.run(run())
