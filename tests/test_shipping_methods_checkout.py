"""Tipax / Chapar / Tehran Express checkout and shipping options."""

from decimal import Decimal

import pytest
from app.main import app
from app.services.payment_flow_service import order_amount_rials
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("enable_storefront_shipping_methods")


def _purchase_payload(method_code: str, *, province: str, city: str, product_id: int):
    return {
        "mode": "purchase",
        "customer": {"full_name": "کاربر تست", "phone": "09121234567", "is_guest": False},
        "items": [{"product_id": product_id, "quantity": 1}],
        "shipping": {
            "province": province,
            "city": city,
            "postal_code": "1234567890",
            "address_line": "خیابان تست، پلاک ۱۰، واحد ۲",
        },
        "shipping_method_code": method_code,
    }


def _seed_minimal_product(client, super_admin_headers, sku="SHIP-MVP"):
    payload = {
        "sku": sku,
        "name": "Shipping MVP",
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


@pytest.mark.parametrize(
    ("province", "city", "codes"),
    [
        ("تهران", "تهران", {"tehran_express", "tipax_standard", "chapar_standard"}),
        ("تهران", "شهریار", {"tipax_standard", "chapar_standard"}),
        ("تهران", "اسلامشهر", {"tipax_standard", "chapar_standard"}),
        ("البرز", "کرج", {"tipax_standard", "chapar_standard"}),
    ],
)
def test_shipping_options_eligibility(province, city, codes, override_database):
    client = TestClient(app)
    res = client.post(
        "/api/v1/shipping/options",
        json={"province": province, "city": city, "postal_code": "1234567890"},
    )
    assert res.status_code == 200, res.text
    got = {o["code"] for o in res.json()["options"]}
    assert got == codes


def test_checkout_tipax_receiver_due_totals(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    product = _seed_minimal_product(client, super_admin_headers)
    headers = purchase_customer_headers
    res = client.post(
        "/api/v1/checkout",
        json=_purchase_payload("tipax_standard", province="اصفهان", city="اصفهان", product_id=product["id"]),
        headers=headers,
    )
    assert res.status_code == 201, res.text
    body = res.json()
    # 100000 + 10% tax = 110000
    assert body["estimated_total"] in {"110000", "110000.00"}
    assert body["shipping_display"] == "receiver_due"


def test_checkout_rejects_tehran_express_outside_tehran(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    product = _seed_minimal_product(client, super_admin_headers, sku="SHIP-TEH-REJECT")
    headers = purchase_customer_headers
    res = client.post(
        "/api/v1/checkout",
        json=_purchase_payload(
            "tehran_express", province="خراسان رضوی", city="مشهد", product_id=product["id"]
        ),
        headers=headers,
    )
    assert res.status_code == 409
    payload = res.json()
    code = payload.get("error", {}).get("code") or payload.get("error_code")
    assert code == "SHIPPING_METHOD_DESTINATION_NOT_ELIGIBLE"


def test_checkout_missing_method_code(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    product = _seed_minimal_product(client, super_admin_headers, sku="SHIP-NO-METHOD")
    headers = purchase_customer_headers
    payload = _purchase_payload("tipax_standard", province="تهران", city="تهران", product_id=product["id"])
    del payload["shipping_method_code"]
    res = client.post("/api/v1/checkout", json=payload, headers=headers)
    assert res.status_code == 422
    payload = res.json()
    code = payload.get("error", {}).get("code") or payload.get("error_code")
    assert code == "SHIPPING_METHOD_REQUIRED"


def test_checkout_product_without_dimensions(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    payload = {
        "sku": "NO-DIM-SHIP",
        "name": "No dims",
        "category_id": 3,
        "brand_id": 1,
        "base_price": "50000",
        "is_available": True,
        "stock_unit": "piece",
        "is_active": True,
        "tax_percent": "0",
    }
    created = client.post("/api/v1/products/", json=payload, headers=super_admin_headers)
    assert created.status_code == 201
    product_id = created.json()["id"]
    headers = purchase_customer_headers
    res = client.post(
        "/api/v1/checkout",
        json=_purchase_payload("chapar_standard", province="تهران", city="تهران", product_id=product_id),
        headers=headers,
    )
    assert res.status_code == 201, res.text


def test_shipment_after_payment_tipax(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    product = _seed_minimal_product(client, super_admin_headers, sku="SHIP-PAID")
    headers = purchase_customer_headers
    checkout = client.post(
        "/api/v1/checkout",
        json=_purchase_payload("tipax_standard", province="تهران", city="تهران", product_id=product["id"]),
        headers=headers,
    )
    assert checkout.status_code == 201
    order_id = checkout.json()["order_id"]

    import asyncio

    from app.db.models.commerce import Order, OrderStatus, PaymentStatus
    from app.services.logistics.service import ensure_shipment_for_paid_order

    from tests.conftest import TestingSessionLocal

    async def _pay_and_ship():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            assert order is not None
            order.status = OrderStatus.PAID.value
            order.payment_status = PaymentStatus.PAID.value
            order.status = OrderStatus.PROCESSING.value
            shipment = await ensure_shipment_for_paid_order(session, order)
            await session.commit()
            return shipment

    shipment = asyncio.run(_pay_and_ship())
    assert shipment is not None
    assert shipment.provider == "tipax"
    assert shipment.shipping_payment_mode == "receiver_due"
    assert shipment.customer_shipping_cost is None


def test_sep_amount_excludes_shipping(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    product = _seed_minimal_product(client, super_admin_headers, sku="SEP-AMT")
    headers = purchase_customer_headers
    res = client.post(
        "/api/v1/checkout",
        json=_purchase_payload("tipax_standard", province="تهران", city="تهران", product_id=product["id"]),
        headers=headers,
    )
    assert res.status_code == 201
    order_id = res.json()["order_id"]

    import asyncio

    from app.db.models.commerce import Order

    from tests.conftest import TestingSessionLocal

    async def _load():
        async with TestingSessionLocal() as session:
            return await session.get(Order, order_id)

    order = asyncio.run(_load())
    assert order is not None
    assert order.shipping_customer_cost is None
    expected_toman = Decimal("110000")
    assert Decimal(str(order.estimated_total)) == expected_toman
    assert order_amount_rials(order) == int(expected_toman * 10)
