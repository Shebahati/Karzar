"""P5: end-to-end purchase flow integration test."""

import re

import pytest
from app.core.config import settings
from app.main import app
from app.services.payment_service import reset_payment_provider_for_tests
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.mark.integration
def test_purchase_checkout_payment_verify_flow(
    valid_product_data, super_admin_headers, monkeypatch
):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()

    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "P5-E2E-001", "stock_quantity": "5"},
        headers=super_admin_headers,
    )
    assert create.status_code == 201
    product_id = create.json()["id"]

    otp_req = client.post("/api/v1/auth/otp/request", json={"phone": "09127770001"})
    code = otp_req.json()["dev_code"]
    otp_verify = client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": "09127770001", "code": code},
    )
    token = otp_verify.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    checkout = client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {"full_name": "E2E User", "phone": "09127770001"},
            "items": [{"product_id": product_id, "quantity": 1}],
            "shipping": {
                "province": "تهران",
                "city": "تهران",
                "postal_code": "1234567890",
                "address_line": "خیابان E2E پلاک ۱",
            },
        },
        headers=headers,
    )
    assert checkout.status_code == 201, checkout.text
    checkout_body = checkout.json()
    assert checkout_body["status"] == "pending_payment"
    assert checkout_body["payment_url"]
    assert re.fullmatch(r"KZ-[0-9A-F]{12}", checkout_body["tracking_code"])
    order_id = checkout_body["order_id"]
    authority = checkout_body["authority"]

    verify = client.post(
        "/api/v1/payments/verify",
        json={"order_id": order_id, "authority": authority},
        headers=headers,
    )
    assert verify.status_code == 200, verify.text
    paid = verify.json()
    assert paid["payment_status"] == "paid"
    assert paid["status"] == "paid"

    my_orders = client.get("/api/v1/orders/me", headers=headers)
    assert my_orders.status_code == 200
    ids = [row["id"] for row in my_orders.json()["data"]]
    assert order_id in ids

    track = client.get(f"/api/v1/orders/track/{checkout_body['tracking_code']}")
    assert track.status_code == 200
    assert track.json()["status"] == "paid"
