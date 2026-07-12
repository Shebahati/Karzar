"""Payment endpoint integration tests with mock provider."""

import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import update

from app.core.config import settings
from app.core.constants import TOMAN_TO_RIAL
from app.db.models.commerce import Order
from app.main import app
from app.services.payment_service import (
    PaymentGatewayTimeoutError,
    PaymentVerifyFailedError,
    reset_payment_provider_for_tests,
)
from tests.conftest import TestingSessionLocal, customer_auth_headers

client = TestClient(app)


def _auth_headers_for_phone(phone: str):
    return customer_auth_headers(phone)


def _clear_order_payment_authority(order_id: int) -> None:
    async def _clear() -> None:
        async with TestingSessionLocal() as session:
            await session.execute(
                update(Order).where(Order.id == order_id).values(payment_authority=None)
            )
            await session.commit()

    asyncio.run(_clear())


def _checkout_order(product_id: int, headers: dict) -> int:
    checkout = client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {"full_name": "Ali", "phone": "09128888888"},
            "items": [{"product_id": product_id, "quantity": 1}],
            "shipping": {
                "province": "تهران",
                "city": "تهران",
                "postal_code": "1234567890",
                "address_line": "خیابان آزادی، پلاک ۱۰",
            },
        },
        headers=headers,
    )
    assert checkout.status_code == 201
    return checkout.json()["order_id"]


def test_mock_payment_init_and_verify(valid_product_data, super_admin_headers, monkeypatch):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()

    create = client.post("/api/v1/products/", json=valid_product_data, headers=super_admin_headers)
    product_id = create.json()["id"]
    customer_headers = _auth_headers_for_phone("09128888888")
    order_id = _checkout_order(product_id, customer_headers)

    init = client.post("/api/v1/payments/init", json={"order_id": order_id}, headers=customer_headers)
    assert init.status_code == 200
    authority = init.json()["authority"]
    assert authority.startswith("MOCK-")

    verify = client.post(
        "/api/v1/payments/verify",
        json={"order_id": order_id, "authority": authority},
        headers=customer_headers,
    )
    assert verify.status_code == 200
    body = verify.json()
    assert body["payment_status"] == "paid"
    assert body["status"] == "paid"


def test_payment_amount_uses_toman_to_rial_conversion(
    valid_product_data, super_admin_headers, monkeypatch
):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()

    valid_product_data = {**valid_product_data, "sku": "PAY-RIAL", "base_price": "100.00", "tax_percent": "0"}
    create = client.post("/api/v1/products/", json=valid_product_data, headers=super_admin_headers)
    product_id = create.json()["id"]
    customer_headers = _auth_headers_for_phone("09129999999")

    captured: dict[str, int] = {}

    class SpyProvider:
        async def init_payment(self, *, amount_rials: int, description: str, callback_url: str):
            captured["amount_rials"] = amount_rials
            from app.services.payment_service import MockPaymentProvider

            return await MockPaymentProvider().init_payment(
                amount_rials=amount_rials,
                description=description,
                callback_url=callback_url,
            )

        async def verify_payment(self, *, authority: str, amount_rials: int):
            captured["verify_amount_rials"] = amount_rials
            from app.services.payment_service import MockPaymentProvider

            return await MockPaymentProvider().verify_payment(
                authority=authority,
                amount_rials=amount_rials,
            )

        async def refund_payment(self, *, ref_id: str, amount_rials: int):
            from app.services.payment_service import MockPaymentProvider

            return await MockPaymentProvider().refund_payment(ref_id=ref_id, amount_rials=amount_rials)

    monkeypatch.setattr("app.services.payment_flow_service.get_payment_provider", lambda: SpyProvider())

    order_id = _checkout_order(product_id, customer_headers)
    assert captured["amount_rials"] == 100 * TOMAN_TO_RIAL

    init = client.post("/api/v1/payments/init", json={"order_id": order_id}, headers=customer_headers)
    assert init.status_code == 200

    verify = client.post(
        "/api/v1/payments/verify",
        json={"order_id": order_id, "authority": init.json()["authority"]},
        headers=customer_headers,
    )
    assert verify.status_code == 200
    assert captured["verify_amount_rials"] == 100 * TOMAN_TO_RIAL


def test_payment_verify_is_idempotent(valid_product_data, super_admin_headers, monkeypatch):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()

    create = client.post("/api/v1/products/", json=valid_product_data, headers=super_admin_headers)
    product_id = create.json()["id"]
    customer_headers = _auth_headers_for_phone("09121111111")
    order_id = _checkout_order(product_id, customer_headers)

    init = client.post("/api/v1/payments/init", json={"order_id": order_id}, headers=customer_headers)
    authority = init.json()["authority"]

    first = client.post(
        "/api/v1/payments/verify",
        json={"order_id": order_id, "authority": authority},
        headers=customer_headers,
    )
    assert first.status_code == 200

    second = client.post(
        "/api/v1/payments/verify",
        json={"order_id": order_id, "authority": authority},
        headers=customer_headers,
    )
    assert second.status_code == 200
    assert second.json()["payment_status"] == "paid"
    assert second.json()["status"] == "paid"


def test_payment_init_is_idempotent_for_pending_order(
    valid_product_data, super_admin_headers, monkeypatch
):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()

    create = client.post("/api/v1/products/", json=valid_product_data, headers=super_admin_headers)
    product_id = create.json()["id"]
    customer_headers = _auth_headers_for_phone("09122221111")
    order_id = _checkout_order(product_id, customer_headers)

    first = client.post("/api/v1/payments/init", json={"order_id": order_id}, headers=customer_headers)
    second = client.post("/api/v1/payments/init", json={"order_id": order_id}, headers=customer_headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["authority"] == second.json()["authority"]


def test_guest_purchase_checkout_rejected(valid_product_data, super_admin_headers, monkeypatch):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()

    create = client.post("/api/v1/products/", json=valid_product_data, headers=super_admin_headers)
    product_id = create.json()["id"]

    checkout = client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {"full_name": "Guest", "phone": "09125555555", "is_guest": True},
            "items": [{"product_id": product_id, "quantity": 1}],
            "shipping": {
                "province": "تهران",
                "city": "تهران",
                "postal_code": "1234567890",
                "address_line": "خیابان آزادی، پلاک ۱۰",
            },
        },
    )
    assert checkout.status_code == 403
    assert checkout.json()["error_code"] == "PURCHASE_AUTH_REQUIRED"


def test_payment_gateway_timeout_returns_specific_error(
    valid_product_data, super_admin_headers, monkeypatch
):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    reset_payment_provider_for_tests()

    class TimeoutProvider:
        async def init_payment(self, *, amount_rials: int, description: str, callback_url: str):
            raise PaymentGatewayTimeoutError("Payment gateway request timed out")

        async def verify_payment(self, *, authority: str, amount_rials: int):
            raise PaymentGatewayTimeoutError("Payment verification request timed out")

    create = client.post("/api/v1/products/", json=valid_product_data, headers=super_admin_headers)
    product_id = create.json()["id"]
    customer_headers = _auth_headers_for_phone("09127777771")
    order_id = _checkout_order(product_id, customer_headers)
    _clear_order_payment_authority(order_id)

    monkeypatch.setattr("app.services.payment_flow_service.get_payment_provider", lambda: TimeoutProvider())

    init = client.post("/api/v1/payments/init", json={"order_id": order_id}, headers=customer_headers)
    assert init.status_code == 504
    assert init.json()["error_code"] == "PAYMENT_GATEWAY_TIMEOUT"


def test_payment_verify_failed_returns_specific_error(
    valid_product_data, super_admin_headers, monkeypatch
):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    reset_payment_provider_for_tests()

    class FailingVerifyProvider:
        async def init_payment(self, *, amount_rials: int, description: str, callback_url: str):
            from app.services.payment_service import MockPaymentProvider

            return await MockPaymentProvider().init_payment(
                amount_rials=amount_rials,
                description=description,
                callback_url=callback_url,
            )

        async def verify_payment(self, *, authority: str, amount_rials: int):
            raise PaymentVerifyFailedError("Invalid mock payment authority")

        async def refund_payment(self, *, ref_id: str, amount_rials: int):
            from app.services.payment_service import MockPaymentProvider

            return await MockPaymentProvider().refund_payment(ref_id=ref_id, amount_rials=amount_rials)

    monkeypatch.setattr("app.services.payment_flow_service.get_payment_provider", lambda: FailingVerifyProvider())

    create = client.post("/api/v1/products/", json=valid_product_data, headers=super_admin_headers)
    product_id = create.json()["id"]
    customer_headers = _auth_headers_for_phone("09127777772")
    order_id = _checkout_order(product_id, customer_headers)

    init = client.post("/api/v1/payments/init", json={"order_id": order_id}, headers=customer_headers)
    verify = client.post(
        "/api/v1/payments/verify",
        json={"order_id": order_id, "authority": init.json()["authority"]},
        headers=customer_headers,
    )
    assert verify.status_code == 400
    assert verify.json()["error_code"] == "PAYMENT_VERIFY_FAILED"
