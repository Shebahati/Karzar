"""Brand_id mutation must emit ProductChangeLog; omit must preserve brand."""

import uuid

import pytest
from app.db.models.product import StockUnitEnum
from app.main import app
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("override_database")

client = TestClient(app)


def _create_branded_product(super_admin_headers, *, brand_id: int = 1) -> int:
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "sku": f"BRAND-AUD-{suffix}",
        "name": f"Brand Audit Product {suffix}",
        "category_id": 3,
        "brand_id": brand_id,
        "is_available": True,
        "stock_unit": StockUnitEnum.PIECE.value,
        "base_price": "150000",
        "tax_percent": "9",
        "is_active": True,
    }
    response = client.post("/api/v1/products/", json=payload, headers=super_admin_headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _change_logs(product_id: int, headers) -> list[dict]:
    logs = client.get(f"/api/v1/products/{product_id}/change-log", headers=headers)
    assert logs.status_code == 200, logs.text
    return logs.json()["data"]


def test_omitted_brand_id_preserves_existing_brand(super_admin_headers):
    product_id = _create_branded_product(super_admin_headers, brand_id=1)
    response = client.put(
        f"/api/v1/products/{product_id}",
        headers=super_admin_headers,
        json={"base_price": "160000"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["brand_id"] == 1
    assert body["base_price"] in ("160000", "160000.00", 160000, 160000.0)

    brand_logs = [row for row in _change_logs(product_id, super_admin_headers) if row["field_name"] == "brand_id"]
    assert brand_logs == []

    price_logs = [
        row for row in _change_logs(product_id, super_admin_headers) if row["field_name"] == "base_price"
    ]
    assert len(price_logs) == 1
    assert price_logs[0]["old_value"] in ("150000", "150000.00")
    assert price_logs[0]["new_value"] in ("160000", "160000.00")


def test_authorized_brand_change_emits_audit_log(super_admin_headers):
    product_id = _create_branded_product(super_admin_headers, brand_id=1)
    other = client.post(
        "/api/v1/brands/",
        json={"name": f"Other Brand {uuid.uuid4().hex[:6]}", "country": "CN"},
        headers=super_admin_headers,
    )
    assert other.status_code == 201, other.text
    other_brand_id = other.json()["id"]

    response = client.put(
        f"/api/v1/products/{product_id}",
        headers=super_admin_headers,
        json={"brand_id": other_brand_id},
    )
    assert response.status_code == 200, response.text
    assert response.json()["brand_id"] == other_brand_id

    brand_logs = [row for row in _change_logs(product_id, super_admin_headers) if row["field_name"] == "brand_id"]
    assert len(brand_logs) == 1
    assert brand_logs[0]["old_value"] == "1"
    assert brand_logs[0]["new_value"] == str(other_brand_id)
    assert brand_logs[0]["reason"] == "product_update"


def test_explicit_null_clears_brand_and_emits_audit_log(super_admin_headers):
    """Schema allows nullable brand_id; explicit null clears and must be audited."""
    product_id = _create_branded_product(super_admin_headers, brand_id=1)
    response = client.put(
        f"/api/v1/products/{product_id}",
        headers=super_admin_headers,
        json={"brand_id": None},
    )
    assert response.status_code == 200, response.text
    assert response.json()["brand_id"] is None

    brand_logs = [row for row in _change_logs(product_id, super_admin_headers) if row["field_name"] == "brand_id"]
    assert len(brand_logs) == 1
    assert brand_logs[0]["old_value"] == "1"
    assert brand_logs[0]["new_value"] is None
    assert brand_logs[0]["reason"] == "product_update"


def test_unrelated_field_update_does_not_log_brand_change(super_admin_headers):
    product_id = _create_branded_product(super_admin_headers, brand_id=1)
    response = client.put(
        f"/api/v1/products/{product_id}",
        headers=super_admin_headers,
        json={"name": "Renamed Without Brand Touch"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["brand_id"] == 1
    brand_logs = [row for row in _change_logs(product_id, super_admin_headers) if row["field_name"] == "brand_id"]
    assert brand_logs == []
