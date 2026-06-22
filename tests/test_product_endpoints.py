# tests/test_product_endpoints.py
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestSystemEndpoints:
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_readiness_check_without_db(self):
        response = client.get("/ready")
        assert response.status_code == 503

    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "running"

    def test_api_info(self):
        response = client.get("/api/v1")
        data = response.json()
        assert data["api_version"] == "v1"
        assert "categories" in data["endpoints"]


class TestProductCreation:
    def test_create_product_requires_auth(self, valid_product_data):
        response = client.post("/api/v1/products/", json=valid_product_data)
        assert response.status_code == 401

    def test_create_product_success(self, valid_product_data, super_admin_headers):
        response = client.post(
            "/api/v1/products/",
            json=valid_product_data,
            headers=super_admin_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sku"] == "TEST-001"
        assert data["name"] == "Test Product"
        assert "pdf_catalog_url" in data
        assert "created_at" in data

    def test_create_product_invalid_price(self, valid_product_data, super_admin_headers):
        valid_product_data["base_price"] = "-10"
        response = client.post(
            "/api/v1/products/",
            json=valid_product_data,
            headers=super_admin_headers,
        )
        assert response.status_code == 422

    def test_create_product_invalid_stock_unit(self, valid_product_data, super_admin_headers):
        valid_product_data["stock_unit"] = "invalid"
        response = client.post(
            "/api/v1/products/",
            json=valid_product_data,
            headers=super_admin_headers,
        )
        assert response.status_code == 422


class TestProductRetrieval:
    def test_list_products_empty(self):
        response = client.get("/api/v1/products/")
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total_count"] == 0
        assert data["data"] == []

    def test_list_products_with_pagination(self):
        response = client.get("/api/v1/products/?skip=0&limit=50")
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["skip"] == 0
        assert data["meta"]["limit"] == 50

    def test_list_products_invalid_limit(self):
        response = client.get("/api/v1/products/?limit=2000")
        assert response.status_code == 422


class TestProductMutations:
    def test_update_nonexistent_product(self, super_admin_headers):
        response = client.put(
            "/api/v1/products/9999",
            json={"name": "Updated Name"},
            headers=super_admin_headers,
        )
        assert response.status_code == 404

    def test_delete_nonexistent_product(self, super_admin_headers):
        response = client.delete("/api/v1/products/9999", headers=super_admin_headers)
        assert response.status_code == 404


class TestStockManagement:
    def test_adjust_stock_nonexistent_product(self, super_admin_headers):
        response = client.post(
            "/api/v1/products/9999/stock/adjust?quantity_delta=10",
            headers=super_admin_headers,
        )
        assert response.status_code == 404

    def test_get_stock_status_nonexistent_product(self):
        response = client.get("/api/v1/products/9999/stock")
        assert response.status_code == 404


class TestCategoryEndpoints:
    def test_category_tree(self):
        response = client.get("/api/v1/categories/tree")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestAuthEndpoints:
    def test_register_and_login(self):
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "phone_number": "09123456789",
                "password": "securepass",
                "full_name": "Test User",
            },
        )
        assert register_response.status_code == 201

        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "09123456789", "password": "securepass"},
        )
        assert login_response.status_code == 200
        assert "access_token" in login_response.json()

    def test_register_invalid_phone(self):
        response = client.post(
            "/api/v1/auth/register",
            json={"phone_number": "123", "password": "securepass"},
        )
        assert response.status_code == 422

    def test_login_active_user(self):
        client.post(
            "/api/v1/auth/register",
            json={"phone_number": "09111111111", "password": "securepass"},
        )
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "09111111111", "password": "securepass"},
        )
        assert login_response.status_code == 200
