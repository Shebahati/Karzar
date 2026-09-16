"""Admin Postex automation must not run for storefront matrix (manual) carriers."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from app.core.config import settings
from app.db.models.commerce import Order, OrderStatus, PaymentStatus
from app.main import app
from app.services.logistics.fulfillment_mode import PostexFulfillmentMode
from app.services.logistics.service import ensure_shipment_for_paid_order
from fastapi.testclient import TestClient

from tests.conftest import TestingSessionLocal
from tests.test_manual_fulfillment import _checkout_tipax

pytestmark = pytest.mark.usefixtures("enable_storefront_shipping_methods")


def _checkout_method(
    client: TestClient,
    super_admin_headers,
    purchase_customer_headers,
    method_code: str,
    sku: str,
):
    payload = {
        "sku": sku,
        "name": "Manual block",
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
    province, city = ("تهران", "تهران")
    if method_code == "post_pishtaz":
        province, city = "خراسان رضوی", "مشهد"
    res = client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {"full_name": "تست", "phone": "09121234567", "is_guest": False},
            "items": [{"product_id": pid, "quantity": 1}],
            "shipping": {
                "province": province,
                "city": city,
                "postal_code": "1234567890",
                "address_line": "خیابان تست، پلاک ۱۰، واحد ۲",
            },
            "shipping_method_code": method_code,
        },
        headers=purchase_customer_headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["order_id"]


async def _paid_shipment(order_id: int):
    async with TestingSessionLocal() as session:
        order = await session.get(Order, order_id)
        assert order is not None
        order.status = OrderStatus.PROCESSING.value
        order.payment_status = PaymentStatus.PAID.value
        shipment = await ensure_shipment_for_paid_order(session, order)
        await session.commit()
        assert shipment is not None
        return shipment.id


@pytest.mark.parametrize(
    ("method_code", "sku"),
    [
        ("tipax_standard", "BLK-TIPAX"),
        ("chapar_standard", "BLK-CHAPAR"),
        ("post_pishtaz", "BLK-POST"),
        ("tehran_motorcycle_48h", "BLK-MOTO"),
    ],
)
def test_packed_quote_rejected_for_manual_matrix_providers(
    override_database,
    super_admin_headers,
    purchase_customer_headers,
    monkeypatch,
    method_code,
    sku,
):
    monkeypatch.setattr(settings, "POSTEX_ENABLED", True)
    mock_provider = AsyncMock()
    monkeypatch.setattr(
        "app.services.logistics.service.get_provider",
        lambda: mock_provider,
    )
    client = TestClient(app)
    order_id = _checkout_method(
        client, super_admin_headers, purchase_customer_headers, method_code, sku
    )
    shipment_id = asyncio.run(_paid_shipment(order_id))

    async def assert_snapshot():
        async with TestingSessionLocal() as session:
            from app.db.models.logistics import Shipment

            shipment = await session.get(Shipment, shipment_id)
            assert shipment is not None
            assert (shipment.provider_data or {}).get("fulfillment_mode") == (
                PostexFulfillmentMode.MANUAL.value
            )

    asyncio.run(assert_snapshot())

    quote = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/packed-quote",
        headers=super_admin_headers,
    )
    assert quote.status_code == 409, quote.text
    body = quote.json()
    code = body.get("error", {}).get("code") or body.get("error_code")
    assert code == "SHIPMENT_STATE_INVALID"
    mock_provider.quote.assert_not_called()


def test_tipax_shipment_snapshots_manual_fulfillment_mode(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr(settings, "POSTEX_ENABLED", False)
    client = TestClient(app)
    order_id = _checkout_tipax(client, super_admin_headers, purchase_customer_headers)
    shipment_id = asyncio.run(_paid_shipment(order_id))

    async def assert_snapshot():
        async with TestingSessionLocal() as session:
            from app.db.models.logistics import Shipment

            shipment = await session.get(Shipment, shipment_id)
            assert (shipment.provider_data or {}).get("fulfillment_mode") == "manual"

    asyncio.run(assert_snapshot())
