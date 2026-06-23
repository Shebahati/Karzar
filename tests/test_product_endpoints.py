"""Integration tests for product CRUD, listing, auth, and step-up flows."""

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
        body = response.json()
        assert body["error_code"] == "UNAUTHORIZED"

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
        assert data["stock_status"] == "in_stock"
        assert "images" in data
        assert "specifications" in data

    def test_create_product_invalid_price(self, valid_product_data, super_admin_headers):
        valid_product_data["base_price"] = "-10"
        response = client.post(
            "/api/v1/products/",
            json=valid_product_data,
            headers=super_admin_headers,
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "VALIDATION_FAILED"
        assert isinstance(body["details"], list)

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
        assert data["meta"]["has_prev"] is False

    def test_list_products_with_pagination(self):
        response = client.get("/api/v1/products/?skip=0&limit=50")
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["skip"] == 0
        assert data["meta"]["limit"] == 50

    def test_list_products_invalid_limit(self):
        response = client.get("/api/v1/products/?limit=2000")
        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "VALIDATION_FAILED"

    def test_list_products_invalid_filters_json(self):
        response = client.get("/api/v1/products/?filters=not-json")
        assert response.status_code == 400
        body = response.json()
        assert body["error_code"] == "VALIDATION_FAILED"
        assert body["details"][0]["field"] == "filters"

    def test_product_detail_shape(self, valid_product_data, super_admin_headers):
        create_response = client.post(
            "/api/v1/products/",
            json=valid_product_data,
            headers=super_admin_headers,
        )
        product_id = create_response.json()["id"]

        response = client.get(f"/api/v1/products/{product_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["stock_status"] == "in_stock"
        assert data["availability"] is True
        assert "images" in data
        assert "specifications" in data
        assert data["specifications"]["technical_specs"]["range"] == "0-150mm"

    def test_product_detail_preserves_dynamic_specifications(
        self, valid_product_data, super_admin_headers
    ):
        valid_product_data["specifications"] = {
            "technical_specs": {"range": "0-150mm"},
            "custom_brand": "insize",
            "extra_section": {"voltage": "24V"},
        }
        create_response = client.post(
            "/api/v1/products/",
            json=valid_product_data,
            headers=super_admin_headers,
        )
        product_id = create_response.json()["id"]

        response = client.get(f"/api/v1/products/{product_id}")
        assert response.status_code == 200
        specs = response.json()["specifications"]
        assert specs["custom_brand"] == "insize"
        assert specs["extra_section"] == {"voltage": "24V"}
        assert specs["technical_specs"]["range"] == "0-150mm"

    def test_spec_filters_json(self, valid_product_data, super_admin_headers):
        client.post(
            "/api/v1/products/",
            json=valid_product_data,
            headers=super_admin_headers,
        )
        response = client.get(
            '/api/v1/products/?filters={"technical_specs.range":"0-150mm"}'
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total_count"] == 1
        assert data["data"][0]["sku"] == "TEST-001"

    def test_spec_prefixed_filter(self, valid_product_data, super_admin_headers):
        client.post(
            "/api/v1/products/",
            json=valid_product_data,
            headers=super_admin_headers,
        )
        response = client.get("/api/v1/products/?spec_technical_specs__range=0-150mm")
        assert response.status_code == 200
        assert response.json()["meta"]["total_count"] == 1


class TestProductMutations:
    def test_update_sku_success(self, valid_product_data, super_admin_headers):
        create_response = client.post(
            "/api/v1/products/",
            json=valid_product_data,
            headers=super_admin_headers,
        )
        product_id = create_response.json()["id"]

        response = client.put(
            f"/api/v1/products/{product_id}",
            json={"sku": "test-002"},
            headers=super_admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["sku"] == "TEST-002"

    def test_update_sku_conflict(self, valid_product_data, super_admin_headers):
        client.post(
            "/api/v1/products/",
            json=valid_product_data,
            headers=super_admin_headers,
        )
        second_product = valid_product_data.copy()
        second_product["sku"] = "TEST-002"
        create_two = client.post(
            "/api/v1/products/",
            json=second_product,
            headers=super_admin_headers,
        )
        product_two_id = create_two.json()["id"]

        response = client.put(
            f"/api/v1/products/{product_two_id}",
            json={"sku": "TEST-001"},
            headers=super_admin_headers,
        )
        assert response.status_code == 409
        assert response.json()["error_code"] == "CONFLICT"

    def test_update_nonexistent_product(self, super_admin_headers):
        response = client.put(
            "/api/v1/products/9999",
            json={"name": "Updated Name"},
            headers=super_admin_headers,
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "NOT_FOUND"

    def test_delete_requires_step_up(self, super_admin_headers):
        response = client.delete("/api/v1/products/9999", headers=super_admin_headers)
        assert response.status_code == 403
        assert response.json()["error_code"] == "STEP_UP_REQUIRED"

    def test_delete_nonexistent_product(self, step_up_headers):
        response = client.delete("/api/v1/products/9999", headers=step_up_headers)
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
    def test_category_tree_wrapper(self):
        response = client.get("/api/v1/categories/tree")
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert isinstance(body["data"], list)

    def test_category_tree_returns_unlimited_depth(self):
        response = client.get("/api/v1/categories/tree")
        assert response.status_code == 200

        tree = response.json()["data"]
        assert len(tree) == 1
        assert tree[0]["name"] == "Digital Calipers"

        level_two = tree[0]["subcategories"]
        assert len(level_two) == 1
        assert level_two[0]["name"] == "Standard Type"

        level_three = level_two[0]["subcategories"]
        assert len(level_three) == 1
        assert level_three[0]["name"] == "0-150mm Range"

        level_four = level_three[0]["subcategories"]
        assert len(level_four) == 1
        assert level_four[0]["name"] == "IP67 Series"
        assert level_four[0]["subcategories"] == []


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
        body = login_response.json()
        assert "access_token" in body
        assert "expires_in" in body

    def test_register_invalid_phone(self):
        response = client.post(
            "/api/v1/auth/register",
            json={"phone_number": "123", "password": "securepass"},
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "VALIDATION_FAILED"

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

    def test_verify_pin_success(self, super_admin_headers):
        response = client.post(
            "/api/v1/auth/verify-pin",
            json={"pin": "84729101"},
            headers=super_admin_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["token_type"] == "step_up"
        assert "secure_token" in body
        assert body["expires_in"] > 0

    def test_verify_pin_invalid(self, super_admin_headers):
        response = client.post(
            "/api/v1/auth/verify-pin",
            json={"pin": "000000"},
            headers=super_admin_headers,
        )
        assert response.status_code == 403
        assert response.json()["error_code"] == "STEP_UP_INVALID"
