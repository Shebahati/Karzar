"""BE-03: gateway verify timeout must mark payment_status UNKNOWN (not FAILED)."""

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.db.models.commerce import Order, PaymentTransaction
from app.main import app
from app.services.payment_service import (
    PaymentGatewayTimeoutError,
    reset_payment_provider_for_tests,
)
from tests.conftest import TestingSessionLocal, customer_auth_headers
from tests.test_payments import _checkout_order

client = TestClient(app)


def test_verify_timeout_sets_payment_status_unknown(
    valid_product_data, super_admin_headers, monkeypatch
):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    reset_payment_provider_for_tests()

    class TimeoutOnVerify:
        async def init_payment(self, *, amount_rials: int, description: str, callback_url: str):
            from app.services.payment_service import MockPaymentProvider

            return await MockPaymentProvider().init_payment(
                amount_rials=amount_rials,
                description=description,
                callback_url=callback_url,
            )

        async def verify_payment(self, *, authority: str, amount_rials: int):
            raise PaymentGatewayTimeoutError("Payment verification request timed out")

    create = client.post("/api/v1/products/", json=valid_product_data, headers=super_admin_headers)
    product_id = create.json()["id"]
    customer_headers = customer_auth_headers("09127770001")
    order_id = _checkout_order(product_id, customer_headers)

    monkeypatch.setattr(
        "app.services.payment_flow_service.get_payment_provider",
        lambda: TimeoutOnVerify(),
    )

    init = client.post(
        "/api/v1/payments/init", json={"order_id": order_id}, headers=customer_headers
    )
    assert init.status_code == 200
    authority = init.json()["authority"]

    verify = client.post(
        "/api/v1/payments/verify",
        json={"order_id": order_id, "authority": authority},
        headers=customer_headers,
    )
    assert verify.status_code == 504
    assert verify.json()["error_code"] == "PAYMENT_GATEWAY_TIMEOUT"

    async def fetch():
        async with TestingSessionLocal() as session:
            order = (
                await session.execute(select(Order).where(Order.id == order_id))
            ).scalars().first()
            rows = (
                await session.execute(
                    select(PaymentTransaction)
                    .where(PaymentTransaction.order_id == order_id)
                    .order_by(PaymentTransaction.id)
                )
            ).scalars().all()
            return order.status, order.payment_status, [r.status for r in rows]

    order_status, payment_status, tx_statuses = asyncio.run(fetch())
    assert order_status == "pending_payment"
    assert payment_status == "unknown"
    assert "unknown" in tx_statuses

    # Re-verify must still be allowed after UNKNOWN (order remains payable).
    reset_payment_provider_for_tests()
    monkeypatch.setattr(
        "app.services.payment_flow_service.get_payment_provider",
        lambda: __import__(
            "app.services.payment_service", fromlist=["MockPaymentProvider"]
        ).MockPaymentProvider(),
    )
    # Clear authority reuse path by keeping authority; mock verify succeeds.
    retry = client.post(
        "/api/v1/payments/verify",
        json={"order_id": order_id, "authority": authority},
        headers=customer_headers,
    )
    assert retry.status_code == 200
    assert retry.json()["payment_status"] == "paid"
