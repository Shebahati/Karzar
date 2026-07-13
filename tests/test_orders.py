"""Order lifecycle API tests: admin management, tracking, and customer history."""

import asyncio
import re
from datetime import UTC, datetime, timedelta

from app.crud.stock_movement import list_stock_movements_for_reference
from app.main import app
from app.services import order_expiry_service
from fastapi.testclient import TestClient

from tests.conftest import TestingSessionLocal, customer_auth_headers

client = TestClient(app)


def _create_product(super_admin_headers, valid_product_data, *, sku, stock="20"):
    valid_product_data = {**valid_product_data, "sku": sku, "stock_quantity": stock}
    resp = client.post(
        "/api/v1/products/", json=valid_product_data, headers=super_admin_headers
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _checkout_purchase(product_id, quantity=2, phone="09123333333", headers=None):
    auth_headers = headers or customer_auth_headers(phone)
    return client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {"full_name": "رضا محمدی", "phone": phone},
            "items": [{"product_id": product_id, "quantity": quantity}],
            "shipping": {
                "province": "تهران",
                "city": "تهران",
                "postal_code": "1234567890",
                "address_line": "خیابان آزادی، پلاک ۱۰",
            },
        },
        headers=auth_headers,
    )


class TestAdminOrders:
    def test_list_and_detail(self, valid_product_data, super_admin_headers):
        product_id = _create_product(super_admin_headers, valid_product_data, sku="ORD-1")
        checkout = _checkout_purchase(product_id)
        assert checkout.status_code == 201
        order_id = checkout.json()["order_id"]

        listing = client.get("/api/v1/orders", headers=super_admin_headers)
        assert listing.status_code == 200
        body = listing.json()
        assert body["meta"]["total_count"] == 1
        assert body["data"][0]["status"] == "pending_payment"
        assert body["data"][0]["status_label"] == "در انتظار پرداخت"

        detail = client.get(f"/api/v1/orders/{order_id}", headers=super_admin_headers)
        assert detail.status_code == 200
        assert detail.json()["items"][0]["product_id"] == product_id
        assert "paid" in detail.json()["allowed_next_statuses"]

    def test_list_requires_admin(self):
        assert client.get("/api/v1/orders").status_code == 401

    def test_status_filter_validation(self, super_admin_headers):
        resp = client.get("/api/v1/orders?status=bogus", headers=super_admin_headers)
        assert resp.status_code == 422

    def test_valid_transition(self, valid_product_data, super_admin_headers, monkeypatch):
        from app.core.config import settings
        from app.services.payment_service import reset_payment_provider_for_tests

        monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
        monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
        reset_payment_provider_for_tests()

        product_id = _create_product(super_admin_headers, valid_product_data, sku="ORD-2")
        checkout = _checkout_purchase(product_id)
        order_id = checkout.json()["order_id"]
        authority = checkout.json()["authority"]
        headers = customer_auth_headers("09123333333")
        verify = client.post(
            "/api/v1/payments/verify",
            json={"order_id": order_id, "authority": authority, "status": "OK"},
            headers=headers,
        )
        assert verify.status_code == 200, verify.text

        resp = client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": "processing"},
            headers=super_admin_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "processing"

    def test_invalid_transition_rejected(self, valid_product_data, super_admin_headers):
        product_id = _create_product(super_admin_headers, valid_product_data, sku="ORD-3")
        order_id = _checkout_purchase(product_id).json()["order_id"]

        resp = client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": "delivered"},
            headers=super_admin_headers,
        )
        assert resp.status_code == 409

    def test_cancel_requires_step_up(self, valid_product_data, super_admin_headers):
        product_id = _create_product(super_admin_headers, valid_product_data, sku="ORD-4")
        order_id = _checkout_purchase(product_id).json()["order_id"]

        resp = client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": "cancelled"},
            headers=super_admin_headers,
        )
        assert resp.status_code == 403

    def test_cancel_with_step_up_restores_stock(
        self, valid_product_data, super_admin_headers, step_up_headers
    ):
        product_id = _create_product(
            super_admin_headers, valid_product_data, sku="ORD-5", stock="20"
        )
        order_id = _checkout_purchase(product_id, quantity=5).json()["order_id"]

        stock = client.get(
            f"/api/v1/products/{product_id}/stock", headers=super_admin_headers
        )
        assert float(stock.json()["stock_quantity"]) == 15.0

        resp = client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": "cancelled"},
            headers=step_up_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "cancelled"

        restored = client.get(
            f"/api/v1/products/{product_id}/stock", headers=super_admin_headers
        )
        assert float(restored.json()["stock_quantity"]) == 20.0

        async def fetch_movements():
            async with TestingSessionLocal() as db:
                return await list_stock_movements_for_reference(db, f"order:{order_id}")

        movements = asyncio.run(fetch_movements())
        assert len(movements) == 2
        assert movements[0].movement_type == "sale"
        assert float(movements[0].quantity_change) == -5.0
        assert movements[1].movement_type == "return"
        assert float(movements[1].quantity_change) == 5.0


class TestOrderTracking:
    def test_public_tracking(self, valid_product_data, super_admin_headers):
        product_id = _create_product(super_admin_headers, valid_product_data, sku="ORD-6")
        checkout = _checkout_purchase(product_id)
        body = checkout.json()
        tracking_code = body["tracking_code"]
        order_id = body["order_id"]

        assert tracking_code.startswith("KZ-")
        assert re.fullmatch(r"KZ-[0-9A-F]{12}", tracking_code)
        assert tracking_code != f"KZ-{order_id}"

        resp = client.get(f"/api/v1/orders/track/{tracking_code}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["tracking_code"] == tracking_code
        assert body["status_label"] == "در انتظار پرداخت"
        assert "customer_phone" not in body
        assert "shipping" not in body
        assert "customer_full_name" not in body
        assert "estimated_total" not in body
        assert "items" in body
        assert body["items"][0]["product_id"] == product_id
        assert len(body["timeline"]) >= 1
        assert body["timeline"][0]["status"] == "pending_payment"

    def test_tracking_not_found(self):
        assert client.get("/api/v1/orders/track/KZ-DEADBEEFCAFE").status_code == 404


class TestOrderExpiry:
    def test_expired_pending_payment_restocked(
        self, valid_product_data, super_admin_headers, monkeypatch
    ):
        product_id = _create_product(
            super_admin_headers, valid_product_data, sku="ORD-EXP", stock="20"
        )
        checkout = _checkout_purchase(product_id, quantity=5)
        assert checkout.status_code == 201

        stock = client.get(
            f"/api/v1/products/{product_id}/stock", headers=super_admin_headers
        )
        assert float(stock.json()["stock_quantity"]) == 15.0

        monkeypatch.setattr(
            order_expiry_service,
            "pending_payment_cutoff",
            lambda now=None: datetime.now(UTC) + timedelta(days=1),
        )

        async def sweep():
            async with TestingSessionLocal() as db:
                cancelled = await order_expiry_service.cancel_expired_pending_payment_orders(db)
                if cancelled:
                    await db.commit()
                return cancelled

        cancelled = asyncio.run(sweep())
        assert cancelled == 1

        restored = client.get(
            f"/api/v1/products/{product_id}/stock", headers=super_admin_headers
        )
        assert float(restored.json()["stock_quantity"]) == 20.0


class TestCustomerOrders:
    def test_my_orders_requires_auth(self):
        assert client.get("/api/v1/orders/me").status_code == 401

    def test_my_orders_lists_own(
        self, valid_product_data, super_admin_headers, monkeypatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
        product_id = _create_product(super_admin_headers, valid_product_data, sku="ORD-7")

        req = client.post("/api/v1/auth/otp/request", json={"phone": "09127777777"})
        code = req.json()["dev_code"]
        verify = client.post(
            "/api/v1/auth/otp/verify", json={"phone": "09127777777", "code": code}
        )
        token = verify.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        checkout = _checkout_purchase(product_id, headers=auth_headers)
        assert checkout.status_code == 201

        mine = client.get("/api/v1/orders/me", headers=auth_headers)
        assert mine.status_code == 200
        assert mine.json()["meta"]["total_count"] == 1
