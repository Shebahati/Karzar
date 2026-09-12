"""Regression: logistics UNKNOWN must not be fabricated as parcel/false."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.db.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.logistics.exceptions import (
    ShippingDataIncompleteError,
    ShippingFreightRequiredError,
)
from app.services.logistics.models import QuoteLine
from app.services.logistics.package_builder import build_package
from app.utils.product_presenter import to_product_detail
from pydantic import ValidationError

from tests.conftest import USE_POSTGRES_TESTS


def _line(**kwargs) -> QuoteLine:
    base = dict(
        product_id=1,
        sku="SKU-1",
        quantity=1,
        unit_price_toman=Decimal("1000"),
        weight_grams=Decimal("250"),
        length_cm=Decimal("10"),
        width_cm=Decimal("8"),
        height_cm=Decimal("4"),
        is_fragile=False,
        is_liquid=False,
        shipping_class="parcel",
        is_available=True,
        name="Tool",
    )
    base.update(kwargs)
    return QuoteLine(**base)


def test_orm_logistics_columns_nullable_no_server_default():
    fragile = Product.__table__.c.shipping_is_fragile
    liquid = Product.__table__.c.shipping_is_liquid
    shipping_class = Product.__table__.c.shipping_class
    assert fragile.nullable is True
    assert liquid.nullable is True
    assert shipping_class.nullable is True
    assert fragile.server_default is None
    assert liquid.server_default is None
    assert shipping_class.server_default is None


def test_migration_file_preserves_unknown_nulls():
    text = Path("alembic/versions/i2j3k4l5m6n7_postex_logistics.py").read_text(encoding="utf-8")
    assert 'sa.Column("shipping_is_fragile", sa.Boolean(), nullable=True)' in text
    assert 'sa.Column("shipping_is_liquid", sa.Boolean(), nullable=True)' in text
    assert 'sa.Column("shipping_class", sa.String(length=32), nullable=True)' in text
    assert 'server_default="parcel"' not in text
    assert "package_length_cm > 0" in text
    assert "ck_products_package_length_positive" in text
    assert "shipping_class IS NULL OR shipping_class IN" in text
    assert "POSTEX_ENABLED=false" in text or "destructive" in text.lower()


def test_product_create_defaults_remain_unknown():
    payload = ProductCreate(
        sku="UNK-1",
        name="Unknown Logistics",
        category_id=1,
        stock_unit="piece",
    )
    assert payload.shipping_class is None
    assert payload.shipping_is_fragile is None
    assert payload.shipping_is_liquid is None
    assert payload.package_length_cm is None


@pytest.mark.parametrize("field", ["package_length_cm", "package_width_cm", "package_height_cm"])
def test_product_create_rejects_zero_and_negative_dims(field: str):
    with pytest.raises(ValidationError):
        ProductCreate(
            sku="BAD-0",
            name="Bad",
            category_id=1,
            stock_unit="piece",
            **{field: Decimal("0")},
        )
    with pytest.raises(ValidationError):
        ProductCreate(
            sku="BAD-NEG",
            name="Bad",
            category_id=1,
            stock_unit="piece",
            **{field: Decimal("-1")},
        )


def test_product_create_accepts_positive_decimal_dim():
    payload = ProductCreate(
        sku="OK-DIM",
        name="Ok",
        category_id=1,
        stock_unit="piece",
        package_length_cm=Decimal("10.5"),
        package_width_cm=Decimal("8.25"),
        package_height_cm=Decimal("4.1"),
    )
    assert payload.package_length_cm == Decimal("10.5")


@pytest.mark.parametrize("field", ["package_length_cm", "package_width_cm", "package_height_cm"])
def test_product_update_rejects_zero_dim(field: str):
    with pytest.raises(ValidationError):
        ProductUpdate(**{field: Decimal("0")})


def test_build_package_null_class_incomplete():
    with pytest.raises(ShippingDataIncompleteError) as exc:
        build_package([_line(shipping_class=None)])
    assert "shipping_class" in exc.value.products[0]["missing"]


def test_build_package_null_fragile_incomplete():
    with pytest.raises(ShippingDataIncompleteError) as exc:
        build_package([_line(is_fragile=None)])
    assert "shipping_is_fragile" in exc.value.products[0]["missing"]


def test_build_package_null_liquid_incomplete():
    with pytest.raises(ShippingDataIncompleteError) as exc:
        build_package([_line(is_liquid=None)])
    assert "shipping_is_liquid" in exc.value.products[0]["missing"]


def test_build_package_zero_weight_incomplete():
    with pytest.raises(ShippingDataIncompleteError) as exc:
        build_package([_line(weight_grams=Decimal("0"))])
    assert "weight_grams" in exc.value.products[0]["missing"]


def test_build_package_zero_dimension_incomplete():
    with pytest.raises(ShippingDataIncompleteError) as exc:
        build_package([_line(length_cm=Decimal("0"))])
    missing = exc.value.products[0]["missing"]
    assert "zero_dimension" in missing or "package_length_cm" in missing


def test_build_package_freight_only_blocks():
    with pytest.raises(ShippingFreightRequiredError):
        build_package([_line(shipping_class="freight_only")])


def test_build_package_explicit_ready_passes():
    pkg = build_package([_line()])
    assert pkg.weight_grams == 250
    assert pkg.length_cm == 10


def test_presenter_preserves_unknown_nulls():
    now = datetime.now(UTC)
    product = SimpleNamespace(
        id=1,
        sku="P1",
        slug="p1",
        name="P",
        category_id=1,
        brand_id=None,
        category=None,
        brand=None,
        base_price=None,
        original_price=None,
        stock_unit="piece",
        is_active=True,
        is_available=True,
        is_original=True,
        tax_percent=Decimal("0"),
        stock_quantity=Decimal("0"),
        warranty_text=None,
        weight_grams=None,
        package_length_cm=None,
        package_width_cm=None,
        package_height_cm=None,
        shipping_class=None,
        shipping_is_fragile=None,
        shipping_is_liquid=None,
        pdf_catalog_url=None,
        short_description=None,
        description=None,
        meta_title=None,
        meta_description=None,
        hesabfa_category_override_code=None,
        specifications={},
        images=[],
        created_at=now,
        updated_at=now,
    )
    detail = to_product_detail(product, audience="admin")
    assert detail.shipping_class is None
    assert detail.shipping_is_fragile is None
    assert detail.shipping_is_liquid is None


@pytest.mark.skipif(not USE_POSTGRES_TESTS, reason="nullable logistics defaults require PostgreSQL")
def test_new_product_persists_null_logistics(override_database, super_admin_headers):
    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    created = client.post(
        "/api/v1/products/",
        json={
            "sku": "NULL-LOG-1",
            "name": "Null Logistics",
            "category_id": 3,
            "brand_id": 1,
            "base_price": "1000",
            "is_available": True,
            "stock_unit": "piece",
            "is_active": True,
            "tax_percent": "0",
        },
        headers=super_admin_headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body.get("shipping_class") is None
    assert body.get("shipping_is_fragile") is None
    assert body.get("shipping_is_liquid") is None
    assert body.get("package_length_cm") is None
