"""Checkout shipping address: postal_code is optional but validated when present."""

import pytest
from app.core.config import settings
from app.main import app
from app.schemas.storefront import ShippingAddress
from fastapi.testclient import TestClient
from pydantic import ValidationError

pytestmark = pytest.mark.usefixtures("enable_storefront_shipping_methods")


def _seed_product(client, super_admin_headers, sku="POSTAL-OPT"):
    payload = {
        "sku": sku,
        "name": "Postal optional",
        "category_id": 3,
        "brand_id": 1,
        "base_price": "100000",
        "is_available": True,
        "stock_unit": "piece",
        "is_active": True,
        "tax_percent": "10",
    }
    created = client.post("/api/v1/products/", json=payload, headers=super_admin_headers)
    assert created.status_code == 201, created.text
    return created.json()


def _checkout_payload(product_id: int, shipping: dict):
    return {
        "mode": "purchase",
        "customer": {"full_name": "کاربر تست", "phone": "09121234567", "is_guest": False},
        "items": [{"product_id": product_id, "quantity": 1}],
        "shipping": {
            "province": "اصفهان",
            "city": "اصفهان",
            "address_line": "خیابان تست، پلاک ۱۰، واحد ۲",
            **shipping,
        },
        "shipping_method_code": "tipax_standard",
    }


@pytest.mark.parametrize(
    "postal_field",
    [
        {},
        {"postal_code": None},
        {"postal_code": ""},
        {"postal_code": "   "},
    ],
)
def test_checkout_without_postal_code_succeeds(
    postal_field,
    override_database,
    super_admin_headers,
    purchase_customer_headers,
    monkeypatch,
):
    monkeypatch.setattr(settings, "POSTEX_ENABLED", False)
    client = TestClient(app)
    product = _seed_product(client, super_admin_headers, sku=f"POSTAL-OMIT-{len(postal_field)}")
    res = client.post(
        "/api/v1/checkout",
        json=_checkout_payload(product["id"], postal_field),
        headers=purchase_customer_headers,
    )
    assert res.status_code == 201, res.text


def test_checkout_with_valid_postal_code_succeeds(
    override_database,
    super_admin_headers,
    purchase_customer_headers,
    monkeypatch,
):
    monkeypatch.setattr(settings, "POSTEX_ENABLED", False)
    client = TestClient(app)
    product = _seed_product(client, super_admin_headers, sku="POSTAL-VALID")
    res = client.post(
        "/api/v1/checkout",
        json=_checkout_payload(product["id"], {"postal_code": "1234567890"}),
        headers=purchase_customer_headers,
    )
    assert res.status_code == 201, res.text


@pytest.mark.parametrize(
    "bad_postal",
    [
        "12345",
        "12345678901",
        "123456789a",
        "۱۲۳۴۵۶۷۸۹۰",
        "123456789۰",
    ],
)
def test_checkout_with_invalid_postal_code_fails(
    bad_postal,
    override_database,
    super_admin_headers,
    purchase_customer_headers,
    monkeypatch,
):
    monkeypatch.setattr(settings, "POSTEX_ENABLED", False)
    client = TestClient(app)
    product = _seed_product(client, super_admin_headers, sku=f"POSTAL-BAD-{bad_postal[:4]}")
    res = client.post(
        "/api/v1/checkout",
        json=_checkout_payload(product["id"], {"postal_code": bad_postal}),
        headers=purchase_customer_headers,
    )
    assert res.status_code == 422


def test_shipping_address_schema_normalizes_empty_and_validates_digits():
    assert ShippingAddress(
        province="تهران",
        city="تهران",
        address_line="خیابان تست، پلاک ۱۰",
        postal_code="",
    ).postal_code is None
    assert ShippingAddress(
        province="تهران",
        city="تهران",
        address_line="خیابان تست، پلاک ۱۰",
        postal_code="1234567890",
    ).postal_code == "1234567890"
    with pytest.raises(ValidationError):
        ShippingAddress(
            province="تهران",
            city="تهران",
            address_line="خیابان تست، پلاک ۱۰",
            postal_code="12345",
        )
    with pytest.raises(ValidationError):
        ShippingAddress(
            province="تهران",
            city="تهران",
            address_line="خیابان تست، پلاک ۱۰",
            postal_code="۱۲۳۴۵۶۷۸۹۰",
        )
    with pytest.raises(ValidationError):
        ShippingAddress(
            province="تهران",
            city="تهران",
            address_line="خیابان تست، پلاک ۱۰",
            postal_code="123456789۰",
        )
