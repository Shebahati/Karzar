"""Storefront API integration tests."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


class TestStorefrontCatalog:
    def test_brands_envelope(self):
        response = client.get("/api/v1/brands/")
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert isinstance(body["data"], list)

    def test_public_products_default_active_only(
        self, valid_product_data, super_admin_headers
    ):
        valid_product_data["is_active"] = False
        client.post(
            "/api/v1/products/",
            json=valid_product_data,
            headers=super_admin_headers,
        )
        public = client.get("/api/v1/products/")
        assert public.json()["meta"]["total_count"] == 0

        admin = client.get("/api/v1/products/", headers=super_admin_headers)
        assert admin.json()["meta"]["total_count"] == 1

    def test_product_list_sort_and_filters(
        self, valid_product_data, super_admin_headers
    ):
        client.post(
            "/api/v1/products/",
            json=valid_product_data,
            headers=super_admin_headers,
        )
        response = client.get("/api/v1/products/?sort=price_asc&in_stock=true")
        assert response.status_code == 200
        item = response.json()["data"][0]
        assert item["stock_status"] == "موجود"
        assert item["availability"] is True


class TestStorefrontOtp:
    def test_otp_request_and_verify(self, monkeypatch):
        monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
        request = client.post(
            "/api/v1/auth/otp/request",
            json={"phone": "09122222222"},
        )
        assert request.status_code == 200
        body = request.json()
        assert body["phone"] == "09122222222"
        assert "dev_code" in body

        verify = client.post(
            "/api/v1/auth/otp/verify",
            json={"phone": "09122222222", "code": body["dev_code"]},
        )
        assert verify.status_code == 200
        token_body = verify.json()
        assert token_body["token_type"] == "bearer"
        assert token_body["customer"]["phone"] == "09122222222"


class TestStorefrontCheckout:
    def test_checkout_purchase(self, valid_product_data, super_admin_headers):
        create = client.post(
            "/api/v1/products/",
            json=valid_product_data,
            headers=super_admin_headers,
        )
        product_id = create.json()["id"]

        response = client.post(
            "/api/v1/checkout",
            json={
                "mode": "purchase",
                "customer": {
                    "full_name": "رضا محمدی",
                    "phone": "09123333333",
                    "is_guest": True,
                },
                "items": [{"product_id": product_id, "quantity": 2}],
                "shipping": {
                    "province": "تهران",
                    "city": "تهران",
                    "postal_code": "1234567890",
                    "address_line": "خیابان آزادی، پلاک ۱۰",
                },
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["mode"] == "purchase"
        assert body["tracking_code"].startswith("KZ-")
        assert body["estimated_total"] is not None

    def test_contact_form(self):
        response = client.post(
            "/api/v1/contact",
            json={
                "full_name": "رضا محمدی",
                "phone": "09124444444",
                "subject": "سوال فنی",
                "message": "لطفاً راهنمایی بفرمایید درباره محصول.",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["ticket"].startswith("TK-")


class TestStorefrontContent:
    def test_blog_hero_and_comments_empty(self):
        assert client.get("/api/v1/blog/").status_code == 200
        assert client.get("/api/v1/hero-slides/").status_code == 200
        assert client.get("/api/v1/products/1/comments").status_code == 404
