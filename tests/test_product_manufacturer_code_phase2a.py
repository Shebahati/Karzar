"""Phase 2A — manufacturer_code schema, round-trip, and mutation-boundary tests."""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from app.db.models.product import Brand, Category, Product, StockUnitEnum
from app.domain.product_naming import build_product_name_v1
from app.schemas.product import ProductCreate, ProductDetailResponse, ProductUpdate
from app.utils.product_presenter import to_product_detail
from sqlalchemy import inspect, select, text

from tests.conftest import TestingSessionLocal

MIGRATION = Path("alembic/versions/u4v5w6x7y8z9_product_manufacturer_code.py")
ROUND_TRIP_CODES = [
    "1108-150",
    "500-196-30",
    "DCMT11T312-XM YBC203",
    "WNMG080408-PM",
    "K11-315MM",
    "GM-4E-D8.0",
    "SNMG120408-PM / YBC252",
    "X--Y.Z 1",
]


def test_migration_file_is_additive_nullable_no_backfill_no_unique():
    src = MIGRATION.read_text(encoding="utf-8")
    assert 'revision: str = "u4v5w6x7y8z9"' in src
    assert 'down_revision: str | None = "t3u4v5w6x7y8"' in src
    assert "manufacturer_code" in src
    assert "nullable=True" in src
    assert "unique=False" in src
    assert re.search(r"\bunique\s*=\s*True\b", src, re.I) is None
    assert not re.search(r"\bUPDATE\b", src, re.I)
    assert not re.search(r"\bINSERT\b", src, re.I)
    assert "manufacturer_code = sku" not in src
    assert "op.drop_column" in src


def test_product_orm_has_nullable_manufacturer_code():
    col = Product.__table__.c.manufacturer_code
    assert col.nullable is True
    assert getattr(col.type, "length", None) == 255
    for constraint in Product.__table__.constraints:
        cols = getattr(constraint, "columns", None)
        if cols is None:
            continue
        names = {c.name for c in cols}
        if "manufacturer_code" in names and getattr(constraint, "unique", False):
            pytest.fail(f"unexpected unique constraint involving manufacturer_code: {constraint}")
    index_names = {idx.name: idx for idx in Product.__table__.indexes}
    assert "ix_products_manufacturer_code" in index_names
    assert index_names["ix_products_manufacturer_code"].unique is False
    assert "ix_products_brand_id_manufacturer_code" in index_names
    assert index_names["ix_products_brand_id_manufacturer_code"].unique is False


def test_product_create_update_schemas_omit_manufacturer_code():
    assert "manufacturer_code" not in ProductCreate.model_fields
    assert "manufacturer_code" not in ProductUpdate.model_fields
    assert "manufacturer_code" in ProductDetailResponse.model_fields
    assert "product_type_id" in ProductDetailResponse.model_fields


def test_presenter_exposes_identity_to_admin_only():
    product = Product(
        id=1,
        sku="1108-150",
        slug="demo",
        name="کولیس تست",
        category_id=1,
        brand_id=1,
        product_type_id=42,
        manufacturer_code="1108-150",
        stock_unit=StockUnitEnum.PIECE,
        tax_percent=Decimal("0"),
        is_active=True,
        is_available=True,
        is_original=True,
        specifications={},
    )
    product.created_at = datetime.now(UTC)
    product.updated_at = datetime.now(UTC)
    product.images = []
    product.category = None
    product.brand = None

    admin = to_product_detail(product, audience="admin")
    assert admin.manufacturer_code == "1108-150"
    assert admin.product_type_id == 42

    storefront = to_product_detail(product, audience="storefront")
    assert storefront.manufacturer_code is None
    assert storefront.product_type_id is None


def test_round_trip_codes_preserved_exactly():
    for code in ROUND_TRIP_CODES:
        result = build_product_name_v1(
            product_type="اینسرت تراشکاری",
            brand="ZCC.CT",
            manufacturer_code=code,
            naming_profile="cutting.turning_insert.v1",
            preferred_brand_form="ZCC.CT",
            product_type_governed=True,
            manufacturer_code_governed=True,
        )
        assert result.name is not None
        assert code in result.name


@pytest.mark.usefixtures("override_database")
class TestManufacturerCodeDbBoundary:
    def test_column_nullable_no_unique_and_no_side_effects(self):
        async def run():
            async with TestingSessionLocal() as session:
                def _inspect(sync_conn):
                    insp = inspect(sync_conn)
                    cols = {c["name"]: c for c in insp.get_columns("products")}
                    assert "manufacturer_code" in cols
                    assert cols["manufacturer_code"]["nullable"] is True
                    for uq in insp.get_unique_constraints("products"):
                        if "manufacturer_code" in uq.get("column_names", []):
                            raise AssertionError(f"unexpected unique constraint: {uq}")
                    mc_indexes = [
                        i
                        for i in insp.get_indexes("products")
                        if "manufacturer_code" in i.get("column_names", [])
                    ]
                    assert mc_indexes
                    assert all(not i.get("unique") for i in mc_indexes)

                conn = await session.connection()
                await conn.run_sync(_inspect)

                cat = (
                    await session.execute(select(Category).order_by(Category.id.desc()).limit(1))
                ).scalar_one()
                brand = (await session.execute(select(Brand).limit(1))).scalar_one()

                product = Product(
                    sku="P2A-RT-001",
                    slug="p2a-rt-001",
                    name="محصول فاز دو آ",
                    category_id=cat.id,
                    brand_id=brand.id,
                    product_type_id=None,
                    manufacturer_code=None,
                    base_price=Decimal("1000.00"),
                    original_price=Decimal("1200.00"),
                    is_available=True,
                    is_active=True,
                    is_original=True,
                    stock_unit=StockUnitEnum.PIECE,
                    specifications={"model": "SHOULD_NOT_AUTO_COPY"},
                )
                session.add(product)
                await session.flush()
                await session.refresh(product)

                assert product.manufacturer_code is None
                assert product.sku == "P2A-RT-001"
                assert product.name == "محصول فاز دو آ"
                assert product.slug == "p2a-rt-001"
                assert product.base_price == Decimal("1000.00")
                assert product.original_price == Decimal("1200.00")
                assert product.is_available is True
                assert product.is_active is True
                assert product.product_type_id is None
                assert product.brand_id == brand.id
                assert product.category_id == cat.id
                assert product.specifications.get("model") == "SHOULD_NOT_AUTO_COPY"

                product.manufacturer_code = "DCMT11T312-XM YBC203"
                await session.flush()
                await session.refresh(product)
                assert product.manufacturer_code == "DCMT11T312-XM YBC203"
                assert product.sku == "P2A-RT-001"
                assert product.name == "محصول فاز دو آ"
                assert product.slug == "p2a-rt-001"
                assert product.base_price == Decimal("1000.00")
                assert product.is_available is True

                product.manufacturer_code = None
                await session.flush()
                row = (
                    await session.execute(
                        text(
                            "SELECT manufacturer_code, sku, name, slug, "
                            "base_price, is_available, product_type_id, brand_id "
                            "FROM products WHERE id = :id"
                        ),
                        {"id": product.id},
                    )
                ).one()
                assert row.manufacturer_code is None
                assert row.sku == "P2A-RT-001"
                assert row.name == "محصول فاز دو آ"
                assert row.slug == "p2a-rt-001"
                assert bool(row.is_available) is True
                assert row.product_type_id is None
                assert row.brand_id == brand.id

        asyncio.run(run())
