"""Hardening: fail-closed flags, no Postex fallback, status bypass guards."""

import asyncio

import pytest
from app.core.config import settings
from app.db.models.commerce import Order, OrderStatus, PaymentStatus
from app.main import app
from app.services.logistics.manual_fulfillment import (
    manual_handoff,
    manual_register,
)
from app.services.logistics.service import ensure_shipment_for_paid_order
from fastapi.testclient import TestClient

from tests.conftest import TestingSessionLocal

pytestmark = pytest.mark.usefixtures("purchase_customer_headers")


def test_shipping_flags_default_false():
    assert settings.SHIPPING_TIPAX_ENABLED is False
    assert settings.SHIPPING_CHAPAR_ENABLED is False
    assert settings.SHIPPING_TEHRAN_EXPRESS_ENABLED is False
    assert settings.SHIPPING_POSTEX_CHECKOUT_ENABLED is False


def _seed(client, super_admin_headers, sku="HARDEN"):
    payload = {
        "sku": sku,
        "name": "Harden",
        "category_id": 3,
        "brand_id": 1,
        "base_price": "50000",
        "is_available": True,
        "stock_unit": "piece",
        "is_active": True,
        "tax_percent": "0",
    }
    r = client.post("/api/v1/products/", json=payload, headers=super_admin_headers)
    assert r.status_code == 201
    return r.json()["id"]


def _checkout_body(product_id: int, method: str = "tipax_standard"):
    return {
        "mode": "purchase",
        "customer": {"full_name": "تست", "phone": "09121234567", "is_guest": False},
        "items": [{"product_id": product_id, "quantity": 1}],
        "shipping": {
            "province": "تهران",
            "city": "تهران",
            "postal_code": "1234567890",
            "address_line": "خیابان تست، پلاک ۱۰، واحد ۲",
        },
        "shipping_method_code": method,
    }


def test_purchase_rejected_when_no_shipping_enabled(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr(settings, "POSTEX_ENABLED", False)
    monkeypatch.setattr(settings, "SHIPPING_TIPAX_ENABLED", False)
    monkeypatch.setattr(settings, "SHIPPING_CHAPAR_ENABLED", False)
    monkeypatch.setattr(settings, "SHIPPING_TEHRAN_EXPRESS_ENABLED", False)
    monkeypatch.setattr(settings, "SHIPPING_POSTEX_CHECKOUT_ENABLED", False)
    client = TestClient(app)
    pid = _seed(client, super_admin_headers)
    res = client.post(
        "/api/v1/checkout",
        json=_checkout_body(pid),
        headers=purchase_customer_headers,
    )
    assert res.status_code == 503
    assert res.json()["error_code"] == "SHIPPING_UNAVAILABLE"


def test_postex_enabled_does_not_activate_checkout_without_explicit_flag(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    from tests.test_postex_logistics import _enable_postex

    _enable_postex(monkeypatch)
    monkeypatch.setattr(settings, "SHIPPING_POSTEX_CHECKOUT_ENABLED", False)
    monkeypatch.setattr(settings, "SHIPPING_TIPAX_ENABLED", False)
    monkeypatch.setattr(settings, "SHIPPING_CHAPAR_ENABLED", False)
    monkeypatch.setattr(settings, "SHIPPING_TEHRAN_EXPRESS_ENABLED", False)
    client = TestClient(app)
    pid = _seed(client, super_admin_headers, sku="POSTEX-NO-PUB")
    res = client.post(
        "/api/v1/checkout",
        json=_checkout_body(pid),
        headers=purchase_customer_headers,
    )
    assert res.status_code == 503
    assert res.json()["error_code"] == "SHIPPING_UNAVAILABLE"


def test_shipping_options_empty_when_flags_off(override_database, monkeypatch):
    monkeypatch.setattr(settings, "SHIPPING_TIPAX_ENABLED", False)
    monkeypatch.setattr(settings, "SHIPPING_CHAPAR_ENABLED", False)
    monkeypatch.setattr(settings, "SHIPPING_TEHRAN_EXPRESS_ENABLED", False)
    client = TestClient(app)
    res = client.post(
        "/api/v1/shipping/options",
        json={"province": "تهران", "city": "تهران"},
    )
    assert res.status_code == 503


def test_order_status_patch_blocked_with_active_tipax_shipment(
    override_database,
    super_admin_headers,
    purchase_customer_headers,
    enable_storefront_shipping_methods,
    monkeypatch,
):
    monkeypatch.setattr(settings, "POSTEX_ENABLED", False)
    client = TestClient(app)
    pid = _seed(client, super_admin_headers, sku="BYPASS-TIPAX")
    checkout = client.post(
        "/api/v1/checkout",
        json=_checkout_body(pid),
        headers=purchase_customer_headers,
    )
    assert checkout.status_code == 201
    order_id = checkout.json()["order_id"]

    async def setup():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.status = OrderStatus.PROCESSING.value
            order.payment_status = PaymentStatus.PAID.value
            await ensure_shipment_for_paid_order(session, order)
            await session.commit()

    asyncio.run(setup())

    patch = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "shipped", "postal_tracking_code": "1234567890123"},
        headers=super_admin_headers,
    )
    assert patch.status_code == 409
    assert patch.json()["error_code"] == "SHIPMENT_STATE_INVALID"


def test_manual_handoff_still_ships_order(
    override_database,
    super_admin_headers,
    purchase_customer_headers,
    enable_storefront_shipping_methods,
    monkeypatch,
):
    monkeypatch.setattr(settings, "POSTEX_ENABLED", False)
    client = TestClient(app)
    pid = _seed(client, super_admin_headers, sku="HANDOFF-OK")
    checkout = client.post(
        "/api/v1/checkout",
        json=_checkout_body(pid, "chapar_standard"),
        headers=purchase_customer_headers,
    )
    order_id = checkout.json()["order_id"]

    async def flow():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.status = OrderStatus.PROCESSING.value
            order.payment_status = PaymentStatus.PAID.value
            shipment = await ensure_shipment_for_paid_order(session, order)
            await manual_register(
                session,
                order=order,
                shipment=shipment,
                provider_reference="CHAPAR-REF-001",
            )
            await manual_handoff(session, order=order, shipment=shipment)
            await session.commit()
            return order.status

    assert asyncio.run(flow()) == OrderStatus.SHIPPED.value


def test_local_delivery_handoff_without_tracking(
    override_database,
    super_admin_headers,
    purchase_customer_headers,
    enable_storefront_shipping_methods,
    monkeypatch,
):
    monkeypatch.setattr(settings, "POSTEX_ENABLED", False)
    client = TestClient(app)
    pid = _seed(client, super_admin_headers, sku="LOCAL-HANDOFF")
    checkout = client.post(
        "/api/v1/checkout",
        json=_checkout_body(pid, "tehran_express"),
        headers=purchase_customer_headers,
    )
    order_id = checkout.json()["order_id"]

    async def flow():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.status = OrderStatus.PROCESSING.value
            order.payment_status = PaymentStatus.PAID.value
            shipment = await ensure_shipment_for_paid_order(session, order)
            await manual_register(
                session,
                order=order,
                shipment=shipment,
                courier_name="پیک تست",
                courier_phone="09121111111",
            )
            await manual_handoff(session, order=order, shipment=shipment)
            await session.commit()
            return shipment.tracking_code, order.status

    tracking, status = asyncio.run(flow())
    assert not tracking
    assert status == OrderStatus.SHIPPED.value


def test_checkout_snapshots_shipping_method_code(
    override_database,
    super_admin_headers,
    purchase_customer_headers,
    enable_storefront_shipping_methods,
    monkeypatch,
):
    monkeypatch.setattr(settings, "POSTEX_ENABLED", False)
    client = TestClient(app)
    pid = _seed(client, super_admin_headers, sku="SNAP-CODE")
    res = client.post(
        "/api/v1/checkout",
        json=_checkout_body(pid, "tipax_standard"),
        headers=purchase_customer_headers,
    )
    assert res.status_code == 201
    order_id = res.json()["order_id"]

    async def load():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            return (order.shipping or {}).get("shipping_method_code")

    assert asyncio.run(load()) == "tipax_standard"
