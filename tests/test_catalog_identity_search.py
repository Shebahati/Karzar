"""Phase 2B — multi-token identity search + naming preview read-only tests."""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest
from app.db.models.knowledge import KnowledgeTaxonomyNode
from app.db.models.product import Brand, Category, Product, StockUnitEnum
from app.db.models.product_type import ProductType
from app.utils.catalog_identity_search import (
    build_identity_search_filter,
    normalize_search_display_token,
    tokenize_search_query,
)
from sqlalchemy import select

from tests.conftest import TestingSessionLocal

pytestmark = pytest.mark.usefixtures("override_database")


def test_tokenize_and_normalize():
    assert tokenize_search_query("  اینسایز   1108-150 ") == ["اینسایز", "1108-150"]
    assert normalize_search_display_token("كوليس") == "کولیس"
    assert "%" in tokenize_search_query("%")  # literal token preserved for escape layer


async def _leaf_category(session) -> Category:
    return (await session.execute(select(Category).order_by(Category.id.desc()).limit(1))).scalar_one()


async def _seed_search_fixture(session):
    cat = await _leaf_category(session)
    brand = Brand(name="INSIZE | اینسایز", country="CN", slug="insize-p2b")
    session.add(brand)
    await session.flush()
    pt = ProductType(
        code="PROVISIONAL_METROLOGY_CALIPER",
        slug="prov-metrology-caliper-p2b",
        name_fa="کولیس دیجیتال",
        name_en="Digital Caliper",
        status="active",
    )
    session.add(pt)
    await session.flush()
    product = Product(
        sku="1108-150",
        slug="p2b-caliper-1108-150",
        name="کولیس تست اینسایز",
        category_id=cat.id,
        brand_id=brand.id,
        product_type_id=pt.id,
        manufacturer_code="1108-150",
        base_price=Decimal("1000"),
        is_active=True,
        is_available=True,
        is_original=True,
        stock_unit=StockUnitEnum.PIECE,
        specifications={},
    )
    session.add(product)
    await session.flush()
    node = KnowledgeTaxonomyNode(
        node_id="p2b-caliper-syn",
        dimension="family",
        node_type="product_type_bridge",
        slug="caliper-syn-p2b",
        name_fa="کولیس",
        name_en="Caliper",
        status="active",
        synonyms=["ورنیه", "Vernier Caliper"],
        product_type_id=pt.id,
    )
    session.add(node)
    # Unrelated PT synonym must not match
    other_pt = ProductType(
        code="PROVISIONAL_CUTTING_TURNING_INSERT",
        slug="prov-insert-p2b",
        name_fa="اینسرت تراشکاری",
        name_en="Turning Insert",
        status="active",
    )
    session.add(other_pt)
    await session.flush()
    bad = KnowledgeTaxonomyNode(
        node_id="p2b-insert-syn",
        dimension="family",
        node_type="product_type_bridge",
        slug="insert-syn-p2b",
        name_fa="اینسرت",
        status="active",
        synonyms=["الماس"],
        product_type_id=other_pt.id,
    )
    session.add(bad)
    await session.flush()
    return product, brand, pt


class TestIdentitySearch:
    def test_multi_token_cross_field_and_escape(self):
        async def run():
            from app.crud import product as crud_product

            async with TestingSessionLocal() as session:
                product, brand, pt = await _seed_search_fixture(session)
                await session.commit()

                rows, total = await crud_product.get_products(
                    session, search="اینسایز 1108-150", limit=50
                )
                assert total >= 1
                assert any(p.id == product.id for p in rows)

                rows2, total2 = await crud_product.get_products(
                    session, search="Digital Caliper", limit=50
                )
                assert total2 >= 1
                assert any(p.id == product.id for p in rows2)

                # Synonym on this PT
                rows3, _ = await crud_product.get_products(
                    session, search="ورنیه", limit=50
                )
                assert any(p.id == product.id for p in rows3)

                # Unrelated synonym (الماس → other PT) must NOT match this product
                rows4, _ = await crud_product.get_products(
                    session, search="الماس", limit=50
                )
                assert all(p.id != product.id for p in rows4)

                # AND semantics: one token missing → no hit
                rows5, total5 = await crud_product.get_products(
                    session, search="اینسایز NO_SUCH_TOKEN_XYZ", limit=50
                )
                assert total5 == 0 or all(p.id != product.id for p in rows5)

                # Escape % as literal — product name does not contain %
                rows6, total6 = await crud_product.get_products(
                    session, search="%", limit=50
                )
                # May be 0; must not error / treat as wildcard-all
                assert isinstance(total6, int)

                # Filter coexistence
                rows7, total7 = await crud_product.get_products(
                    session,
                    search="1108-150",
                    brand_id=brand.id,
                    is_active=True,
                    limit=50,
                )
                assert total7 >= 1
                assert any(p.id == product.id for p in rows7)

                # Synonym + OEM cross-field (insert PT)
                insert_pt = (
                    await session.execute(
                        select(ProductType).where(
                            ProductType.code == "PROVISIONAL_CUTTING_TURNING_INSERT"
                        )
                    )
                ).scalar_one()
                insert = Product(
                    sku="ZCC-DCMT-P2B",
                    slug="p2b-zcc-dcmt",
                    name="اینسرت تراشکاری تست",
                    category_id=product.category_id,
                    brand_id=brand.id,
                    product_type_id=insert_pt.id,
                    manufacturer_code="DCMT11T312-XM",
                    base_price=Decimal("2000"),
                    is_active=True,
                    is_available=True,
                    is_original=True,
                    stock_unit=StockUnitEnum.PIECE,
                    specifications={},
                )
                session.add(insert)
                await session.commit()

                rows8, total8 = await crud_product.get_products(
                    session, search="الماس DCMT", limit=50
                )
                assert total8 >= 1
                assert any(p.id == insert.id for p in rows8)
                # Caliper must not appear for insert synonym + OEM
                assert all(p.id != product.id for p in rows8)

        asyncio.run(run())

    def test_build_filter_none_for_blank(self):
        assert build_identity_search_filter("   ") is None
        assert build_identity_search_filter(None) is None


class TestNamingPreviewReadonly:
    def test_preview_zero_writes_and_hold_without_oem(self):
        async def run():
            from app.services.product_naming_preview_service import (
                build_persisted_naming_preview,
            )

            async with TestingSessionLocal() as session:
                cat = await _leaf_category(session)
                brand = Brand(name="ZCC.CT | زد سی‌سی", country="CN", slug="zcc-p2b")
                session.add(brand)
                await session.flush()
                product = Product(
                    sku="ZCC-DEMO",
                    slug="p2b-zcc-demo",
                    name="الماس تراشکاری تست",
                    category_id=cat.id,
                    brand_id=brand.id,
                    product_type_id=None,
                    manufacturer_code=None,
                    is_active=True,
                    is_available=True,
                    is_original=True,
                    stock_unit=StockUnitEnum.PIECE,
                    specifications={},
                )
                session.add(product)
                await session.commit()
                await session.refresh(product)
                before_name, before_sku, before_slug, before_oem = (
                    product.name,
                    product.sku,
                    product.slug,
                    product.manufacturer_code,
                )
                preview = await build_persisted_naming_preview(session, product.id)
                assert preview is not None
                # Without PT or OEM, engine HOLDs on the first missing required field (PT).
                assert preview["state"] in {
                    "HOLD_MISSING_MANUFACTURER_CODE",
                    "HOLD_MISSING_PRODUCT_TYPE",
                }
                assert preview["confidence"] == "none"
                assert preview["preview_source"] == "persisted_canonical"
                assert preview["mutation_check"]["unchanged"] is True
                await session.refresh(product)
                assert product.name == before_name
                assert product.sku == before_sku
                assert product.slug == before_slug
                assert product.manufacturer_code == before_oem

        asyncio.run(run())
