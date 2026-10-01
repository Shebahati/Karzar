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

from tests.conftest import USE_POSTGRES_TESTS, TestingSessionLocal

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
    # Canonical PT taxonomy node: node_type=product_type, dimension=family
    # (assignment_role product_type_bridge is NOT a node_type).
    node = KnowledgeTaxonomyNode(
        node_id="p2b-caliper-syn",
        dimension="family",
        node_type="product_type",
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
        node_type="product_type",
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


class TestSynonymContractSafety:
    """Canonical PT node_type + string-element-only synonym matching."""

    def test_postgresql_sql_enforces_string_elements_and_pt_node_type(self):
        """Dialect compile proof: PG path must not cast-to-text whole JSON."""
        from sqlalchemy.dialects import postgresql

        clause = build_identity_search_filter("الماس", dialect_name="postgresql")
        assert clause is not None
        compiled = str(
            clause.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": False},
            )
        )
        assert "jsonb_array_elements" in compiled
        assert "jsonb_typeof" in compiled
        assert "string" in compiled
        assert "node_type" in compiled.lower() or "product_type" in compiled
        # Forbidden: whole-column cast-to-text ILIKE (matches inside objects).
        assert "CAST(knowledge_taxonomy_nodes.synonyms AS VARCHAR)" not in compiled
        assert "CAST(knowledge_taxonomy_nodes.synonyms AS TEXT)" not in compiled

    def test_wrong_node_type_and_non_string_shapes_do_not_match(self):
        async def run():
            from app.crud import product as crud_product

            async with TestingSessionLocal() as session:
                product, brand, pt = await _seed_search_fixture(session)
                # Wrong node_type with same PT + searchable-looking synonym
                wrong_type = KnowledgeTaxonomyNode(
                    node_id="p2b-wrong-ntype",
                    dimension="family",
                    node_type="tool_family",
                    slug="wrong-ntype-p2b",
                    name_fa="خانواده اشتباه",
                    status="active",
                    synonyms=["SHOULD_NOT_MATCH"],
                    product_type_id=pt.id,
                )
                # Object / nested / scalar non-strings on a valid PT node
                shape_node = KnowledgeTaxonomyNode(
                    node_id="p2b-shape-syn",
                    dimension="family",
                    node_type="product_type",
                    slug="shape-syn-p2b",
                    name_fa="شکل مترادف",
                    status="active",
                    synonyms=[
                        {"label": "OBJECT_ONLY_TERM"},
                        ["NESTED_ONLY_TERM"],
                        12345,
                        True,
                        None,
                    ],
                    product_type_id=pt.id,
                )
                # Non-array synonyms blob (must not error / must not match)
                non_array = KnowledgeTaxonomyNode(
                    node_id="p2b-nonarray-syn",
                    dimension="family",
                    node_type="product_type",
                    slug="nonarray-syn-p2b",
                    name_fa="غیرآرایه",
                    status="active",
                    synonyms={"label": "NON_ARRAY_TERM"},  # type: ignore[arg-type]
                    product_type_id=pt.id,
                )
                session.add_all([wrong_type, shape_node, non_array])
                await session.commit()

                # String synonym on canonical PT node still matches
                rows_ok, _ = await crud_product.get_products(
                    session, search="ورنیه", limit=50
                )
                assert any(p.id == product.id for p in rows_ok)

                for term in (
                    "SHOULD_NOT_MATCH",
                    "OBJECT_ONLY_TERM",
                    "NESTED_ONLY_TERM",
                    "12345",
                    "NON_ARRAY_TERM",
                ):
                    rows, total = await crud_product.get_products(
                        session, search=term, limit=50
                    )
                    assert all(p.id != product.id for p in rows), term
                    assert isinstance(total, int)

        asyncio.run(run())

    @pytest.mark.skipif(
        not USE_POSTGRES_TESTS,
        reason="PostgreSQL runtime proof for string-element synonym matching",
    )
    def test_postgres_runtime_object_synonym_does_not_match(self):
        """CI sets USE_POSTGRES_TESTS=1 — proves jsonb_typeof='string' gate live."""
        self.test_wrong_node_type_and_non_string_shapes_do_not_match()


class TestSearchOnSaleComposition:
    """Phase 2B identity search ∩ main on_sale facet (SQL before pagination)."""

    def test_search_and_on_sale_intersection_pagination_sort(self):
        async def run():
            from app.crud import product as crud_product

            async with TestingSessionLocal() as session:
                product, brand, pt = await _seed_search_fixture(session)
                # Search+sale hit (deeper discount)
                product.base_price = Decimal("800")
                product.original_price = Decimal("1000")
                # Search-only (not on sale)
                search_only = Product(
                    sku="SEARCH-ONLY-P2B",
                    slug="p2b-search-only",
                    name="کولیس فقط جستجو اینسایز",
                    category_id=product.category_id,
                    brand_id=brand.id,
                    product_type_id=pt.id,
                    manufacturer_code="1108-999",
                    base_price=Decimal("1000"),
                    original_price=None,
                    is_active=True,
                    is_available=True,
                    is_original=True,
                    stock_unit=StockUnitEnum.PIECE,
                    specifications={},
                )
                # Sale-only: different brand so brand-token search cannot hit it
                other_brand = Brand(
                    name="OTHERBRAND | دیگر", country="CN", slug="other-p2b-sale"
                )
                session.add(other_brand)
                await session.flush()
                sale_only = Product(
                    sku="SALE-ONLY-P2B",
                    slug="p2b-sale-only",
                    name="محصول حراج بدون هویت کولیس",
                    category_id=product.category_id,
                    brand_id=other_brand.id,
                    product_type_id=None,
                    manufacturer_code="ZZ-SALE-1",
                    base_price=Decimal("500"),
                    original_price=Decimal("1000"),
                    is_active=True,
                    is_available=True,
                    is_original=True,
                    stock_unit=StockUnitEnum.PIECE,
                    specifications={},
                )
                # Second search+sale hit (shallower discount) for pagination/sort
                both_b = Product(
                    sku="BOTH-B-P2B",
                    slug="p2b-both-b",
                    name="کولیس حراج دوم اینسایز",
                    category_id=product.category_id,
                    brand_id=brand.id,
                    product_type_id=pt.id,
                    manufacturer_code="1108-200",
                    base_price=Decimal("900"),
                    original_price=Decimal("1000"),
                    is_active=True,
                    is_available=True,
                    is_original=True,
                    stock_unit=StockUnitEnum.PIECE,
                    specifications={},
                )
                session.add_all([search_only, sale_only, both_b])
                await session.commit()

                # OEM search ∩ on_sale
                rows, total = await crud_product.get_products(
                    session, search="1108-150", on_sale=True, limit=50
                )
                ids = {p.id for p in rows}
                assert product.id in ids
                assert search_only.id not in ids
                assert sale_only.id not in ids
                assert total >= 1

                # Brand + OEM multi-token ∩ on_sale
                rows2, total2 = await crud_product.get_products(
                    session,
                    search="اینسایز 1108-150",
                    on_sale=True,
                    brand_id=brand.id,
                    limit=50,
                )
                assert any(p.id == product.id for p in rows2)
                assert all(p.id != search_only.id for p in rows2)
                assert all(p.id != sale_only.id for p in rows2)
                assert total2 >= 1

                # Product Type search ∩ on_sale
                rows3, _ = await crud_product.get_products(
                    session, search="Digital Caliper", on_sale=True, limit=50
                )
                hit_ids = {p.id for p in rows3}
                assert product.id in hit_ids
                assert both_b.id in hit_ids
                assert sale_only.id not in hit_ids
                assert search_only.id not in hit_ids

                # Synonym ∩ on_sale
                rows4, _ = await crud_product.get_products(
                    session, search="ورنیه", on_sale=True, limit=50
                )
                syn_ids = {p.id for p in rows4}
                assert product.id in syn_ids
                assert sale_only.id not in syn_ids

                # Pagination: intersection only; authoritative total; no post-filter
                page1, total_both = await crud_product.get_products(
                    session,
                    search="اینسایز",
                    on_sale=True,
                    sort="discount_desc",
                    skip=0,
                    limit=1,
                )
                page2, total_both2 = await crud_product.get_products(
                    session,
                    search="اینسایز",
                    on_sale=True,
                    sort="discount_desc",
                    skip=1,
                    limit=1,
                )
                assert total_both == total_both2
                assert total_both >= 2
                assert len(page1) == 1
                assert len(page2) == 1
                assert page1[0].id != page2[0].id
                page_ids = {page1[0].id, page2[0].id}
                assert product.id in page_ids
                assert both_b.id in page_ids
                assert search_only.id not in page_ids
                assert sale_only.id not in page_ids
                # deeper discount first (product 20% > both_b 10%)
                assert page1[0].id == product.id

                # stock_first still returns search hits
                rows5, total5 = await crud_product.get_products(
                    session, search="1108-150", sort="stock_first", limit=50
                )
                assert total5 >= 1
                assert any(p.id == product.id for p in rows5)

        asyncio.run(run())


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
