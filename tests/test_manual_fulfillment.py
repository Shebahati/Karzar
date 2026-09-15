"""Manual fulfillment register / handoff / deliver for Tipax."""

import asyncio

import pytest
from app.db.models.commerce import Order, OrderStatus, PaymentStatus
from app.main import app
from app.services.logistics.manual_fulfillment import (
    manual_deliver,
    manual_handoff,
    manual_register,
)
from app.services.logistics.service import ensure_shipment_for_paid_order
from fastapi.testclient import TestClient

from tests.conftest import TestingSessionLocal

pytestmark = pytest.mark.usefixtures("enable_storefront_shipping_methods")


def _checkout_tipax(client, super_admin_headers, purchase_customer_headers):
    payload = {
        "sku": "MANUAL-TIPAX",
        "name": "Manual",
        "category_id": 3,
        "brand_id": 1,
        "base_price": "10000",
        "is_available": True,
        "stock_unit": "piece",
        "is_active": True,
        "tax_percent": "0",
    }
    created = client.post("/api/v1/products/", json=payload, headers=super_admin_headers)
    assert created.status_code == 201
    pid = created.json()["id"]
    res = client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {"full_name": "تست", "phone": "09121234567", "is_guest": False},
            "items": [{"product_id": pid, "quantity": 1}],
            "shipping": {
                "province": "تهران",
                "city": "تهران",
                "postal_code": "1234567890",
                "address_line": "خیابان تست، پلاک ۱۰، واحد ۲",
            },
            "shipping_method_code": "tipax_standard",
        },
        headers=purchase_customer_headers,
    )
    assert res.status_code == 201
    return res.json()["order_id"]


def test_register_conflict_on_different_tracking(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    from app.services.logistics.exceptions import ShippingMethodConflictError

    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    order_id = _checkout_tipax(client, super_admin_headers, purchase_customer_headers)

    async def flow():
        async with TestingSessionLocal() as session:
            from app.db.models.commerce import Order, OrderStatus, PaymentStatus

            order = await session.get(Order, order_id)
            order.status = OrderStatus.PROCESSING.value
            order.payment_status = PaymentStatus.PAID.value
            shipment = await ensure_shipment_for_paid_order(session, order)
            await manual_register(
                session,
                order=order,
                shipment=shipment,
                tracking_code="1234567890123",
            )
            try:
                await manual_register(
                    session,
                    order=order,
                    shipment=shipment,
                    tracking_code="9999999999999",
                )
                raise AssertionError("expected conflict")
            except ShippingMethodConflictError:
                pass
            await session.commit()

    asyncio.run(flow())


def test_manual_fulfillment_idempotent_register(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    order_id = _checkout_tipax(client, super_admin_headers, purchase_customer_headers)

    async def flow():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            assert order is not None
            order.status = OrderStatus.PROCESSING.value
            order.payment_status = PaymentStatus.PAID.value
            shipment = await ensure_shipment_for_paid_order(session, order)
            assert shipment is not None
            await manual_register(
                session,
                order=order,
                shipment=shipment,
                tracking_code="1234567890123",
                actor_user_id=1,
            )
            await manual_register(
                session,
                order=order,
                shipment=shipment,
                tracking_code="1234567890123",
                actor_user_id=1,
            )
            await session.commit()
            return shipment.status

    status = asyncio.run(flow())
    assert status == "booked"


def test_manual_handoff_and_deliver(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    order_id = _checkout_tipax(client, super_admin_headers, purchase_customer_headers)

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
                tracking_code="1234567890123",
            )
            await manual_handoff(session, order=order, shipment=shipment)
            await manual_deliver(session, order=order, shipment=shipment)
            await session.commit()
            return order.status, shipment.status

    order_status, shipment_status = asyncio.run(flow())
    assert order_status == OrderStatus.DELIVERED.value
    assert shipment_status == "delivered"
