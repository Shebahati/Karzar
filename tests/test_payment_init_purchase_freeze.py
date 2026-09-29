"""Payment init must fail closed when purchase checkout is disabled.

Callback and verify stay available so in-flight SEP payments can still settle.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest
from app.core.config import settings
from app.core.purchase_checkout import PURCHASE_CHECKOUT_DISABLED_MESSAGE
from app.db.models.commerce import Order, OrderStatusEvent, PaymentTransaction
from app.db.models.platform import IdempotencyKey
from app.db.models.product import StockMovement
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tests.conftest import TestingSessionLocal, customer_auth_headers

pytestmark = pytest.mark.usefixtures("override_database", "enable_storefront_shipping_methods")

client = TestClient(app)


def _count_rows() -> tuple[int, int, int, int, int]:
    async def _count() -> tuple[int, int, int, int, int]:
        async with TestingSessionLocal() as session:
            orders = (await session.execute(select(func.count()).select_from(Order))).scalar_one()
            payments = (
                await session.execute(select(func.count()).select_from(PaymentTransaction))
            ).scalar_one()
            idem = (
                await session.execute(select(func.count()).select_from(IdempotencyKey))
            ).scalar_one()
            movements = (
                await session.execute(select(func.count()).select_from(StockMovement))
            ).scalar_one()
            events = (
                await session.execute(select(func.count()).select_from(OrderStatusEvent))
            ).scalar_one()
            return int(orders), int(payments), int(idem), int(movements), int(events)

    return asyncio.run(_count())


def _order_snapshot(order_id: int) -> tuple:
    async def _load() -> tuple:
        async with TestingSessionLocal() as session:
            order = (
                await session.execute(select(Order).where(Order.id == order_id))
            ).scalar_one()
            return (
                order.status,
                order.payment_status,
                str(order.estimated_total),
                order.payment_authority,
                order.payment_authority_expires_at,
                order.payment_verify_attempts,
                order.payment_ref_id,
            )

    return asyncio.run(_load())


def _checkout_order(product_id: int, headers: dict) -> int:
    checkout = client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {"full_name": "Ali", "phone": "09127770001"},
            "items": [{"product_id": product_id, "quantity": 1}],
            "shipping": {
                "province": "تهران",
                "city": "تهران",
                "postal_code": "1234567890",
                "address_line": "خیابان آزادی، پلاک ۱۰",
            },
            "shipping_method_code": "tipax_standard",
        },
        headers=headers,
    )
    assert checkout.status_code == 201, checkout.text
    return checkout.json()["order_id"]


def _block_gateway_network(monkeypatch) -> None:
    def _boom(*_args, **_kwargs):
        raise AssertionError("gateway network call")

    monkeypatch.setattr("app.services.sep_client.httpx.AsyncClient", _boom)
    monkeypatch.setattr("app.services.payment_service.httpx.AsyncClient", _boom)
    monkeypatch.setattr(
        "app.api.endpoints.payment.initialize_order_payment",
        AsyncMock(side_effect=AssertionError("payment init side effect")),
    )
    monkeypatch.setattr(
        "app.api.endpoints.payment.cancel_expired_pending_payment_orders",
        AsyncMock(side_effect=AssertionError("expiry mutation")),
    )
    monkeypatch.setattr(
        "app.api.endpoints.payment.crud_platform.reserve_idempotency_record",
        AsyncMock(side_effect=AssertionError("idempotency mutation")),
    )


def test_disabled_payment_init_does_not_mutate_or_call_gateway(
    valid_product_data, super_admin_headers, monkeypatch
):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    monkeypatch.setattr(settings, "PURCHASE_CHECKOUT_ENABLED", True)
    from app.services.payment_service import reset_payment_provider_for_tests

    reset_payment_provider_for_tests()

    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "PAY-FREEZE-1"},
        headers=super_admin_headers,
    )
    assert create.status_code == 201, create.text
    product_id = create.json()["id"]
    headers = customer_auth_headers("09127770001")
    order_id = _checkout_order(product_id, headers)

    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "sep")
    monkeypatch.setattr(settings, "PURCHASE_CHECKOUT_ENABLED", False)
    reset_payment_provider_for_tests()
    _block_gateway_network(monkeypatch)

    before_counts = _count_rows()
    before_order = _order_snapshot(order_id)

    response = client.post(
        "/api/v1/payments/init",
        json={"order_id": order_id},
        headers={**headers, "Idempotency-Key": "freeze-init-no-side-effect"},
    )
    assert response.status_code == 503
    body = response.json()
    assert body["error_code"] == "PURCHASE_CHECKOUT_TEMPORARILY_DISABLED"
    assert body["message"] == PURCHASE_CHECKOUT_DISABLED_MESSAGE

    assert _count_rows() == before_counts
    assert _order_snapshot(order_id) == before_order


def test_disabled_flag_still_allows_verify_and_blocks_only_new_init(
    valid_product_data, super_admin_headers, monkeypatch
):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    monkeypatch.setattr(settings, "PURCHASE_CHECKOUT_ENABLED", True)
    from app.services.payment_service import reset_payment_provider_for_tests

    reset_payment_provider_for_tests()

    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "PAY-FREEZE-2"},
        headers=super_admin_headers,
    )
    assert create.status_code == 201, create.text
    headers = customer_auth_headers("09127770002")
    order_id = _checkout_order(create.json()["id"], headers)
    init = client.post("/api/v1/payments/init", json={"order_id": order_id}, headers=headers)
    assert init.status_code == 200, init.text
    authority = init.json()["authority"]

    monkeypatch.setattr(settings, "PURCHASE_CHECKOUT_ENABLED", False)

    verify = client.post(
        "/api/v1/payments/verify",
        json={"order_id": order_id, "authority": authority},
        headers=headers,
    )
    assert verify.status_code == 200, verify.text
    verify_body = verify.json()
    assert verify_body["payment_status"] == "paid"
    assert verify_body.get("error_code") != "PURCHASE_CHECKOUT_TEMPORARILY_DISABLED"

    callback = client.get("/api/v1/payments/callback", follow_redirects=False)
    assert callback.status_code == 302
    assert callback.status_code != 503

    sep_callback = client.post("/api/v1/payments/callback/sep", data={}, follow_redirects=False)
    assert sep_callback.status_code == 303
    assert sep_callback.status_code != 503


def test_purchase_status_reports_disabled_message(monkeypatch):
    monkeypatch.setattr(settings, "PURCHASE_CHECKOUT_ENABLED", False)
    response = client.get("/api/v1/commerce/purchase-status")
    assert response.status_code == 200
    body = response.json()
    assert body["purchase_checkout_enabled"] is False
    assert body["message"] == PURCHASE_CHECKOUT_DISABLED_MESSAGE


def test_purchase_status_omits_message_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "PURCHASE_CHECKOUT_ENABLED", True)
    response = client.get("/api/v1/commerce/purchase-status")
    assert response.status_code == 200
    body = response.json()
    assert body["purchase_checkout_enabled"] is True
    assert body["message"] is None
