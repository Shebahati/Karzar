"""Phase F payment audit: ownership, callback fail, refund ledger, rounding."""

import asyncio
from decimal import ROUND_HALF_UP, Decimal

from app.core.config import settings
from app.core.constants import TOMAN_TO_RIAL
from app.crud.payment_transaction import list_payment_transactions_for_order
from app.db.models.commerce import Order
from app.main import app
from app.services.payment_flow_service import order_amount_rials
from app.services.payment_service import reset_payment_provider_for_tests
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.conftest import TestingSessionLocal, customer_auth_headers

client = TestClient(app)


def _checkout(product_id: int, headers: dict, *, phone: str) -> dict:
    response = client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {"full_name": "پرداخت", "phone": phone},
            "items": [{"product_id": product_id, "quantity": 1}],
            "shipping": {
                "province": "تهران",
                "city": "تهران",
                "postal_code": "1234567890",
                "address_line": "خیابان تست پلاک ۱۰ واحد ۲",
            },
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_payment_init_requires_owner(valid_product_data, super_admin_headers, monkeypatch):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()

    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "F-OWN"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    owner = customer_auth_headers("09126660101")
    other = customer_auth_headers("09126660102")
    order_id = _checkout(product_id, owner, phone="09126660101")["order_id"]

    anon = client.post("/api/v1/payments/init", json={"order_id": order_id})
    assert anon.status_code == 401

    denied = client.post(
        "/api/v1/payments/init",
        json={"order_id": order_id},
        headers=other,
    )
    assert denied.status_code == 403
    assert denied.json()["error_code"] == "FORBIDDEN"

    ok = client.post(
        "/api/v1/payments/init",
        json={"order_id": order_id},
        headers=owner,
    )
    assert ok.status_code == 200


def test_payment_callback_failure_redirect(
    valid_product_data, super_admin_headers, monkeypatch
):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()

    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "F-CB-FAIL"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    headers = customer_auth_headers("09126660202")
    authority = _checkout(product_id, headers, phone="09126660202")["authority"]

    response = client.get(
        f"/api/v1/payments/callback?Authority={authority}&Status=NOK",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert settings.PAYMENT_FAILURE_REDIRECT_URL.split("?")[0] in response.headers["location"]


def test_refund_appends_ledger_and_cancels_order(
    valid_product_data, super_admin_headers, step_up_headers, monkeypatch
):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()

    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "F-REF-LEDGER"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    headers = customer_auth_headers("09126660303")
    checkout = _checkout(product_id, headers, phone="09126660303")
    order_id = checkout["order_id"]
    authority = checkout["authority"]

    verify = client.post(
        "/api/v1/payments/verify",
        json={"order_id": order_id, "authority": authority, "status": "OK"},
        headers=headers,
    )
    assert verify.status_code == 200

    refund = client.post(
        "/api/v1/payments/refund",
        json={"order_id": order_id},
        headers=step_up_headers,
    )
    assert refund.status_code == 200
    assert refund.json()["payment_status"] == "refunded"
    assert refund.json()["status"] == "cancelled"

    async def fetch():
        async with TestingSessionLocal() as db:
            rows = await list_payment_transactions_for_order(db, order_id)
            order = (
                await db.execute(select(Order).where(Order.id == order_id))
            ).scalar_one()
            return rows, order.status, order.payment_status

    rows, order_status, payment_status = asyncio.run(fetch())
    assert order_status == "cancelled"
    assert payment_status == "refunded"
    assert any(row.status == "refunded" for row in rows)
    assert any(row.status == "verified" for row in rows)
    assert any(row.status == "initiated" for row in rows)


def test_order_amount_rials_rounds_half_up():
    class _Order:
        estimated_total = Decimal("10.15")

    # 10.15 toman * 10 = 101.5 → ROUND_HALF_UP → 102
    assert order_amount_rials(_Order()) == int(
        (Decimal("10.15") * Decimal(TOMAN_TO_RIAL)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )
    assert order_amount_rials(_Order()) == 102
