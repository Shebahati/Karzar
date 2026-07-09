"""Payment endpoint integration tests with mock provider."""

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def _auth_headers_for_phone(phone: str):
    req = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    code = req.json()["dev_code"]
    verify = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "code": code})
    token = verify.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_mock_payment_init_and_verify(valid_product_data, super_admin_headers, monkeypatch):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")

    create = client.post("/api/v1/products/", json=valid_product_data, headers=super_admin_headers)
    product_id = create.json()["id"]
    customer_headers = _auth_headers_for_phone("09128888888")

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
        headers=customer_headers,
    )
    assert checkout.status_code == 201
    order_id = checkout.json()["order_id"]

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
