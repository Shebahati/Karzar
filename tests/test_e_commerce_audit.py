"""Phase E commerce audit: cart lanes/merge, paid-cancel rule, inquiry status."""

from app.core.config import settings
from app.main import app
from app.services.payment_service import reset_payment_provider_for_tests
from fastapi.testclient import TestClient

from tests.conftest import customer_auth_headers

client = TestClient(app)


def _create_product(super_admin_headers, valid_product_data, *, sku: str, stock: str = "20"):
    response = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": sku, "stock_quantity": stock},
        headers=super_admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_cart_lanes_are_isolated(super_admin_headers, valid_product_data):
    product_id = _create_product(super_admin_headers, valid_product_data, sku="E-LANE")
    guest = "guest-cart-token-phase-e-lanes-32chars!"

    put_purchase = client.put(
        "/api/v1/cart/items",
        headers={"X-Cart-Token": guest},
        json={"lane": "purchase", "product_id": product_id, "quantity": 2},
    )
    assert put_purchase.status_code == 200

    put_inquiry = client.put(
        "/api/v1/cart/items",
        headers={"X-Cart-Token": guest},
        json={"lane": "inquiry", "product_id": product_id, "quantity": 1},
    )
    assert put_inquiry.status_code == 200

    purchase = client.get("/api/v1/cart?lane=purchase", headers={"X-Cart-Token": guest})
    inquiry = client.get("/api/v1/cart?lane=inquiry", headers={"X-Cart-Token": guest})
    assert purchase.json()["item_count"] == 2
    assert inquiry.json()["item_count"] == 1
    assert purchase.json()["lane"] == "purchase"
    assert inquiry.json()["lane"] == "inquiry"


def test_short_cart_token_rejected():
    response = client.get("/api/v1/cart", headers={"X-Cart-Token": "too-short"})
    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_FAILED"


def test_cart_merge_on_login(super_admin_headers, valid_product_data, monkeypatch):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    product_id = _create_product(super_admin_headers, valid_product_data, sku="E-MERGE")
    guest = "guest-cart-token-phase-e-merge-32chars!"

    upsert = client.put(
        "/api/v1/cart/items",
        headers={"X-Cart-Token": guest},
        json={"lane": "purchase", "product_id": product_id, "quantity": 3},
    )
    assert upsert.status_code == 200

    headers = customer_auth_headers("09125550101")
    merged = client.post(
        "/api/v1/cart/merge",
        json={"guest_token": guest, "lane": "purchase"},
        headers=headers,
    )
    assert merged.status_code == 200
    assert isinstance(merged.json(), list)
    assert any(cart["lane"] == "purchase" and cart["item_count"] == 3 for cart in merged.json())

    user_cart = client.get("/api/v1/cart?lane=purchase", headers=headers)
    assert user_cart.status_code == 200
    assert user_cart.json()["item_count"] == 3


def test_inquiry_checkout_starts_in_review(super_admin_headers, valid_product_data):
    product_id = _create_product(
        super_admin_headers, valid_product_data, sku="E-INQ", stock="0"
    )
    checkout = client.post(
        "/api/v1/checkout",
        json={
            "mode": "inquiry",
            "customer": {"full_name": "استعلام", "phone": "09124445566"},
            "items": [{"product_id": product_id, "quantity": 2}],
        },
    )
    assert checkout.status_code == 201
    assert checkout.json()["mode"] == "inquiry"
    assert checkout.json()["status"] == "inquiry_review"


def test_purchase_requires_shipping(super_admin_headers, valid_product_data, monkeypatch):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    product_id = _create_product(super_admin_headers, valid_product_data, sku="E-SHIP")
    headers = customer_auth_headers("09125550202")
    response = client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {"full_name": "خریدار", "phone": "09125550202"},
            "items": [{"product_id": product_id, "quantity": 1}],
        },
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "VALIDATION_FAILED"


def test_paid_cancel_blocked_until_refund(
    super_admin_headers, step_up_headers, valid_product_data, monkeypatch
):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()

    product_id = _create_product(super_admin_headers, valid_product_data, sku="E-PAID-CXL")
    headers = customer_auth_headers("09125550303")
    checkout = client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {"full_name": "خریدار", "phone": "09125550303"},
            "items": [{"product_id": product_id, "quantity": 1}],
            "shipping": {
                "province": "تهران",
                "city": "تهران",
                "postal_code": "1234567890",
                "address_line": "خیابان تست پلاک ۱۰ واحد ۱",
            },
        },
        headers=headers,
    )
    assert checkout.status_code == 201
    order_id = checkout.json()["order_id"]
    authority = checkout.json()["authority"]

    verify = client.post(
        "/api/v1/payments/verify",
        json={"order_id": order_id, "authority": authority, "status": "OK"},
        headers=headers,
    )
    assert verify.status_code == 200
    assert verify.json()["payment_status"] == "paid"

    blocked = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "cancelled"},
        headers=step_up_headers,
    )
    assert blocked.status_code == 409
    assert "refund" in blocked.json()["message"].lower()
