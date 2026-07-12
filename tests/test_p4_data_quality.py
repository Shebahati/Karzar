"""P4 data-quality and ops regression tests."""

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.utils.storefront_catalog import stock_status_label
from tests.conftest import customer_auth_headers

client = TestClient(app)


class TestStockStatusConsistency:
    def test_admin_stock_endpoint_uses_three_state_codes(
        self, valid_product_data, super_admin_headers
    ):
        create = client.post(
            "/api/v1/products/",
            json={**valid_product_data, "sku": "P4-STOCK", "stock_quantity": "5"},
            headers=super_admin_headers,
        )
        assert create.status_code == 201
        product_id = create.json()["id"]

        stock = client.get(
            f"/api/v1/products/{product_id}/stock",
            headers=super_admin_headers,
        )
        assert stock.status_code == 200
        assert stock.json()["stock_status"] == "low_stock"

    def test_stock_status_label_audience_split(self):
        assert stock_status_label(5, audience="admin") == "low_stock"
        assert stock_status_label(5, audience="storefront") == "موجودی محدود"


class TestCategoryDepthLimit:
    def test_rejects_fourth_layer_category(self, super_admin_headers):
        # Seed tree is depth 1→2→3 (ids 1,2,3). Parent=3 would create depth 4.
        response = client.post(
            "/api/v1/categories/",
            json={"name": "Too Deep", "parent_id": 3},
            headers=super_admin_headers,
        )
        assert response.status_code == 400
        assert response.json()["error_code"] == "BAD_REQUEST"


class TestCategoryRequiredOnCreate:
    def test_create_product_requires_category(self, valid_product_data, super_admin_headers):
        payload = {**valid_product_data, "sku": "P4-NOCAT"}
        payload.pop("category_id", None)
        response = client.post(
            "/api/v1/products/",
            json=payload,
            headers=super_admin_headers,
        )
        assert response.status_code == 422


class TestAdminNoteDoesNotOverwriteCustomerNote:
    def test_status_note_goes_to_admin_note(
        self, valid_product_data, super_admin_headers, monkeypatch
    ):
        monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
        product = client.post(
            "/api/v1/products/",
            json={**valid_product_data, "sku": "P4-NOTE"},
            headers=super_admin_headers,
        ).json()
        headers = customer_auth_headers("09121112233")
        checkout = client.post(
            "/api/v1/checkout",
            json={
                "mode": "purchase",
                "customer": {"full_name": "مشتری", "phone": "09121112233"},
                "items": [{"product_id": product["id"], "quantity": 1}],
                "note": "یادداشت مشتری",
                "shipping": {
                    "province": "تهران",
                    "city": "تهران",
                    "postal_code": "1234567890",
                    "address_line": "خیابان تست",
                },
            },
            headers=headers,
        )
        assert checkout.status_code == 201
        order_id = checkout.json()["order_id"]

        # Mark paid then processing so admin can add a note on a valid transition.
        paid = client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": "paid"},
            headers=super_admin_headers,
        )
        assert paid.status_code == 200

        updated = client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": "processing", "note": "یادداشت ادمین"},
            headers=super_admin_headers,
        )
        assert updated.status_code == 200
        body = updated.json()
        assert body["note"] == "یادداشت مشتری"
        assert body["admin_note"] == "یادداشت ادمین"


class TestAdminUserCreatedAt:
    def test_list_users_exposes_created_at(self, super_admin_headers):
        response = client.get("/api/v1/users", headers=super_admin_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data
        assert data[0]["created_at"] is not None
