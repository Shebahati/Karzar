"""P2 platform feature tests: cart, auth refresh, audit, idempotency, soft delete."""

import uuid

import pytest
from app.db.models.product import StockUnitEnum
from app.main import app
from app.services import otp_service
from fastapi.testclient import TestClient

client = TestClient(app)


class _FakeSms:
    def __init__(self):
        self.messages = []

    async def send(self, message):
        self.messages.append(message)


@pytest.fixture
def fake_sms(monkeypatch):
    fake = _FakeSms()
    monkeypatch.setattr(otp_service, "get_sms_provider", lambda: fake)
    return fake


def _create_product(super_admin_headers):
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "sku": f"P2-{suffix}",
        "name": f"P2 Test Product {suffix}",
        "category_id": 3,
        "brand_id": 1,
        "stock_quantity": "20",
        "stock_unit": StockUnitEnum.PIECE.value,
        "base_price": "150000",
        "tax_percent": "9",
        "is_active": True,
    }
    response = client.post("/api/v1/products/", json=payload, headers=super_admin_headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_cart_guest_flow(super_admin_headers):
    product_id = _create_product(super_admin_headers)
    guest_token = "guest-cart-token-001"

    empty = client.get(
        "/api/v1/cart?lane=purchase",
        headers={"X-Cart-Token": guest_token},
    )
    assert empty.status_code == 200
    assert empty.json()["item_count"] == 0

    upsert = client.put(
        "/api/v1/cart/items",
        headers={"X-Cart-Token": guest_token},
        json={"lane": "purchase", "product_id": product_id, "quantity": 2},
    )
    assert upsert.status_code == 200
    assert upsert.json()["item_count"] == 2

    fetched = client.get(
        "/api/v1/cart?lane=purchase",
        headers={"X-Cart-Token": guest_token},
    )
    assert fetched.json()["items"][0]["product_id"] == product_id


def test_login_returns_refresh_token():
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "09120000001", "password": "adminpass123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_refresh_and_logout_revoke_access_token():
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "09120000001", "password": "adminpass123"},
    )
    tokens = login.json()

    refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh.status_code == 200
    refreshed = refresh.json()
    assert refreshed["refresh_token"] != tokens["refresh_token"]

    logout = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {refreshed['access_token']}"},
    )
    assert logout.status_code == 200

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refreshed['access_token']}"},
    )
    assert me.status_code == 401


def test_password_reset_flow(fake_sms):
    register = client.post(
        "/api/v1/auth/register",
        json={
            "phone_number": "09123334455",
            "password": "securepass123",
            "full_name": "Reset User",
        },
    )
    assert register.status_code == 201

    request = client.post(
        "/api/v1/auth/password-reset/request",
        json={"phone": "09123334455"},
    )
    assert request.status_code == 200
    assert len(fake_sms.messages) >= 1

    code = request.json().get("dev_code")
    assert code

    confirm = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "phone": "09123334455",
            "code": code,
            "new_password": "newsecurepass123",
        },
    )
    assert confirm.status_code == 200

    old_login = client.post(
        "/api/v1/auth/login",
        data={"username": "09123334455", "password": "securepass123"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login",
        data={"username": "09123334455", "password": "newsecurepass123"},
    )
    assert new_login.status_code == 200


def test_checkout_idempotency(super_admin_headers):
    product_id = _create_product(super_admin_headers)
    payload = {
        "mode": "inquiry",
        "customer": {
            "full_name": "Idem User",
            "phone": "09124445566",
            "is_guest": True,
        },
        "items": [{"product_id": product_id, "quantity": 1}],
    }
    headers = {"Idempotency-Key": "checkout-key-001"}

    first = client.post("/api/v1/checkout", json=payload, headers=headers)
    second = client.post("/api/v1/checkout", json=payload, headers=headers)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["order_id"] == second.json()["order_id"]


def test_product_change_log_on_stock_adjust(super_admin_headers):
    product_id = _create_product(super_admin_headers)
    adjust = client.post(
        f"/api/v1/products/{product_id}/stock/adjust?quantity_delta=5",
        headers=super_admin_headers,
    )
    assert adjust.status_code == 200

    logs = client.get(
        f"/api/v1/products/{product_id}/change-log",
        headers=super_admin_headers,
    )
    assert logs.status_code == 200
    data = logs.json()["data"]
    assert len(data) >= 1
    assert data[0]["field_name"] == "stock_quantity"


def test_bulk_stock_adjust(super_admin_headers):
    p1 = _create_product(super_admin_headers)
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "sku": f"P2-BULK-{suffix}",
        "name": "Bulk Product",
        "category_id": 3,
        "brand_id": 1,
        "stock_quantity": "10",
        "stock_unit": StockUnitEnum.PIECE.value,
        "is_active": True,
    }
    p2 = client.post("/api/v1/products/", json=payload, headers=super_admin_headers).json()["id"]

    response = client.post(
        "/api/v1/products/bulk/stock-adjust",
        headers=super_admin_headers,
        json={
            "items": [
                {"product_id": p1, "quantity_delta": "2", "reason": "bulk"},
                {"product_id": p2, "quantity_delta": "-1", "reason": "bulk"},
            ]
        },
    )
    assert response.status_code == 200
    assert set(response.json()["updated_product_ids"]) == {p1, p2}


def test_soft_delete_user_and_order(super_admin_headers, step_up_headers):
    user = client.post(
        "/api/v1/auth/register",
        json={
            "phone_number": "09125556677",
            "password": "securepass123",
            "full_name": "Delete Me",
        },
    ).json()

    delete_user = client.delete(
        f"/api/v1/users/{user['id']}",
        headers=step_up_headers,
    )
    assert delete_user.status_code == 204

    product_id = _create_product(super_admin_headers)
    order = client.post(
        "/api/v1/checkout",
        json={
            "mode": "inquiry",
            "customer": {
                "full_name": "Order Archive",
                "phone": "09126667788",
                "is_guest": True,
            },
            "items": [{"product_id": product_id, "quantity": 1}],
        },
    ).json()

    archive = client.delete(
        f"/api/v1/orders/{order['order_id']}",
        headers=step_up_headers,
    )
    assert archive.status_code == 204

    missing = client.get(
        f"/api/v1/orders/{order['order_id']}",
        headers=super_admin_headers,
    )
    assert missing.status_code == 404


def test_contact_submission_filters(super_admin_headers):
    client.post(
        "/api/v1/contact",
        json={
            "full_name": "Filter User",
            "phone": "09127778899",
            "subject": "Filter Subject",
            "message": "This is a filterable contact message.",
        },
    )
    filtered = client.get(
        "/api/v1/cms/contact-submissions?phone=09127778899",
        headers=super_admin_headers,
    )
    assert filtered.status_code == 200
    assert filtered.json()["meta"]["total_count"] >= 1


def test_b2b_registration_and_me():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "phone_number": "09128889900",
            "password": "securepass123",
            "full_name": "B2B Co",
            "company_name": "کارگاه نمونه",
        },
    )
    assert response.status_code == 201
    assert response.json()["role"] == "b2b_customer"

    login = client.post(
        "/api/v1/auth/login",
        data={"username": "09128889900", "password": "securepass123"},
    )
    token = login.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["is_b2b"] is True
    assert body["company_name"] == "کارگاه نمونه"


def test_payment_refund_mock_flow(super_admin_headers):
    product_id = _create_product(super_admin_headers)
    client.post(
        "/api/v1/auth/register",
        json={
            "phone_number": "09129990011",
            "password": "securepass123",
            "full_name": "Refund User",
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "09129990011", "password": "securepass123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    checkout = client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {
                "full_name": "Refund User",
                "phone": "09129990011",
                "is_guest": False,
            },
            "items": [{"product_id": product_id, "quantity": 1}],
            "shipping": {
                "province": "تهران",
                "city": "تهران",
                "postal_code": "1234567890",
                "address_line": "خیابان تست پلاک ۱۲ واحد ۳",
            },
        },
        headers=headers,
    )
    order_id = checkout.json()["order_id"]

    init = client.post(
        "/api/v1/payments/init",
        json={"order_id": order_id},
        headers=headers,
    )
    authority = init.json()["authority"]

    verify = client.post(
        "/api/v1/payments/verify",
        json={"order_id": order_id, "authority": authority, "status": "OK"},
        headers=headers,
    )
    assert verify.status_code == 200
    assert verify.json()["payment_status"] == "paid"

    refund = client.post(
        "/api/v1/payments/refund",
        json={"order_id": order_id},
        headers=headers,
    )
    assert refund.status_code == 200
    assert refund.json()["payment_status"] == "refunded"
