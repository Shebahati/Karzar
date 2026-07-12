"""Regression tests for P1 storefront/admin contract fixes."""

from app.core.config import settings
from app.main import app
from fastapi.testclient import TestClient

from tests.conftest import customer_auth_headers

client = TestClient(app)


class TestP1StorefrontContract:
    def test_category_tree_has_icon_and_product_count(self):
        response = client.get("/api/v1/categories/tree")
        assert response.status_code == 200
        tree = response.json()
        assert isinstance(tree, list)
        if tree:
            root = tree[0]
            assert "icon" in root
            assert "product_count" in root

    def test_flat_categories_have_product_count(self):
        response = client.get("/api/v1/categories/")
        assert response.status_code == 200
        rows = response.json()["data"]
        assert rows
        assert "product_count" in rows[0]
        assert "is_selectable" in rows[0]

    def test_brands_include_product_count(self):
        response = client.get("/api/v1/brands/")
        assert response.status_code == 200
        brands = response.json()["data"]
        if brands:
            assert "product_count" in brands[0]

    def test_in_stock_accepts_string_one(self, valid_product_data, super_admin_headers):
        client.post(
            "/api/v1/products/",
            json={**valid_product_data, "sku": "P1-STOCK-1"},
            headers=super_admin_headers,
        )
        response = client.get("/api/v1/products/?in_stock=1")
        assert response.status_code == 200
        assert response.json()["meta"]["total_count"] >= 1

    def test_articles_alias_matches_blog(self):
        blog = client.get("/api/v1/blog/")
        articles = client.get("/api/v1/articles/")
        assert blog.status_code == 200
        assert articles.status_code == 200
        assert blog.json() == articles.json()


class TestP1AdminContract:
    def test_product_statistics_endpoint(self, super_admin_headers):
        response = client.get("/api/v1/products/statistics", headers=super_admin_headers)
        assert response.status_code == 200
        body = response.json()
        assert "total_products" in body
        assert "active_products" in body

    def test_issue_quote_endpoint(self, valid_product_data, super_admin_headers):
        product_resp = client.post(
            "/api/v1/products/",
            json={**valid_product_data, "sku": "P1-QUOTE", "base_price": None},
            headers=super_admin_headers,
        )
        assert product_resp.status_code == 201
        product_id = product_resp.json()["id"]

        checkout = client.post(
            "/api/v1/checkout",
            json={
                "mode": "inquiry",
                "customer": {"full_name": "استعلام", "phone": "09124444444"},
                "items": [{"product_id": product_id, "quantity": 1}],
            },
        )
        assert checkout.status_code == 201
        order_id = checkout.json()["order_id"]

        quote = client.post(
            f"/api/v1/orders/{order_id}/quote",
            headers=super_admin_headers,
            json={
                "items": [{"product_id": product_id, "unit_price": "1500000", "quantity": 1}],
                "note": "پیش‌فاکتور تست",
            },
        )
        assert quote.status_code == 200, quote.text
        body = quote.json()
        assert body["status"] == "inquiry_quoted"
        assert body["invoice"] is not None
        assert body["timeline"]

    def test_create_product_comment(self, valid_product_data, super_admin_headers):
        product_resp = client.post(
            "/api/v1/products/",
            json={**valid_product_data, "sku": "P1-COMMENT"},
            headers=super_admin_headers,
        )
        product_id = product_resp.json()["id"]
        response = client.post(
            f"/api/v1/products/{product_id}/comments",
            json={
                "author_name": "کاربر تست",
                "rating": 5,
                "body": "محصول عالی بود",
                "is_verified_buyer": True,
            },
        )
        assert response.status_code == 201
        assert response.json()["rating"] == 5

    def test_cms_article_crud(self, super_admin_headers):
        create = client.post(
            "/api/v1/cms/articles",
            headers=super_admin_headers,
            json={
                "slug": "p1-test-article",
                "title": "مقاله تست",
                "excerpt": "خلاصه",
                "published_at": "2026-06-01T10:00:00Z",
                "reading_minutes": 3,
            },
        )
        assert create.status_code == 201
        article_id = create.json()["id"]

        listing = client.get("/api/v1/cms/articles", headers=super_admin_headers)
        assert listing.status_code == 200
        assert listing.json()["meta"]["total_count"] >= 1

        delete = client.delete(f"/api/v1/cms/articles/{article_id}", headers=super_admin_headers)
        assert delete.status_code == 204

    def test_order_search_param(self, valid_product_data, super_admin_headers, monkeypatch):
        monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
        product_resp = client.post(
            "/api/v1/products/",
            json={**valid_product_data, "sku": "P1-SEARCH"},
            headers=super_admin_headers,
        )
        product_id = product_resp.json()["id"]
        auth_headers = customer_auth_headers("09125555555")
        checkout = client.post(
            "/api/v1/checkout",
            json={
                "mode": "purchase",
                "customer": {"full_name": "جستجو", "phone": "09125555555"},
                "items": [{"product_id": product_id, "quantity": 1}],
                "shipping": {
                    "province": "تهران",
                    "city": "تهران",
                    "postal_code": "1234567890",
                    "address_line": "خیابان جستجو پلاک ۱۲",
                },
            },
            headers=auth_headers,
        )
        tracking_code = checkout.json()["tracking_code"]
        response = client.get(
            f"/api/v1/orders?search={tracking_code}",
            headers=super_admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["meta"]["total_count"] >= 1
