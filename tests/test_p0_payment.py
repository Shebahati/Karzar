"""P0 critical payment flow tests."""

from app.core.config import settings
from app.main import app
from app.services.payment_service import reset_payment_provider_for_tests
from fastapi.testclient import TestClient

client = TestClient(app)


def _auth_headers_for_phone(phone: str):
    req = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    code = req.json()["dev_code"]
    verify = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "code": code})
    token = verify.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _checkout_payload(product_id: int):
    return {
        "mode": "purchase",
        "customer": {"full_name": "Ali", "phone": "09128888888"},
        "items": [{"product_id": product_id, "quantity": 1}],
        "shipping": {
            "province": "تهران",
            "city": "تهران",
            "postal_code": "1234567890",
            "address_line": "خیابان آزادی، پلاک ۱۰",
        },
    }


def test_checkout_returns_payment_url(valid_product_data, super_admin_headers, monkeypatch):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()

    create = client.post("/api/v1/products/", json=valid_product_data, headers=super_admin_headers)
    product_id = create.json()["id"]
    headers = _auth_headers_for_phone("09128888888")

    checkout = client.post("/api/v1/checkout", json=_checkout_payload(product_id), headers=headers)
    assert checkout.status_code == 201
    body = checkout.json()
    assert body.get("payment_url")
    assert body.get("authority", "").startswith("MOCK-")


def test_guest_purchase_checkout_rejected(valid_product_data, super_admin_headers):
    create = client.post("/api/v1/products/", json=valid_product_data, headers=super_admin_headers)
    product_id = create.json()["id"]

    checkout = client.post(
        "/api/v1/checkout",
        json={
            **_checkout_payload(product_id),
            "customer": {"full_name": "Guest", "phone": "09125555555", "is_guest": True},
        },
    )
    assert checkout.status_code == 403
    assert checkout.json()["error_code"] == "PURCHASE_AUTH_REQUIRED"


def test_public_payment_verify_without_jwt(valid_product_data, super_admin_headers, monkeypatch):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()

    create = client.post("/api/v1/products/", json=valid_product_data, headers=super_admin_headers)
    product_id = create.json()["id"]
    headers = _auth_headers_for_phone("09121112222")

    checkout = client.post("/api/v1/checkout", json=_checkout_payload(product_id), headers=headers)
    order_id = checkout.json()["order_id"]
    authority = checkout.json()["authority"]

    verify = client.post(
        "/api/v1/payments/verify",
        json={"order_id": order_id, "authority": authority, "status": "OK"},
    )
    assert verify.status_code == 200
    assert verify.json()["payment_status"] == "paid"


def test_payment_callback_redirect(valid_product_data, super_admin_headers, monkeypatch):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()

    create = client.post("/api/v1/products/", json=valid_product_data, headers=super_admin_headers)
    product_id = create.json()["id"]
    headers = _auth_headers_for_phone("09123334444")

    checkout = client.post("/api/v1/checkout", json=_checkout_payload(product_id), headers=headers)
    authority = checkout.json()["authority"]

    response = client.get(
        f"/api/v1/payments/callback?Authority={authority}&Status=OK",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert settings.PAYMENT_SUCCESS_REDIRECT_URL.split("?")[0] in response.headers["location"]


def test_otp_codes_are_hashed_in_db(valid_product_data, super_admin_headers, monkeypatch):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)

    client.post("/api/v1/auth/otp/request", json={"phone": "09124445555"})
    # Valid verification still works with plaintext input from user.
    req = client.post("/api/v1/auth/otp/request", json={"phone": "09124445555"})
    code = req.json()["dev_code"]
    verify = client.post("/api/v1/auth/otp/verify", json={"phone": "09124445555", "code": code})
    assert verify.status_code == 200

    bad = client.post("/api/v1/auth/otp/verify", json={"phone": "09124445555", "code": "00000"})
    assert bad.status_code == 401
