# tests/test_product_endpoints.py
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestProductEndpoints:
    """Test suite for product endpoints."""

    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_readiness_check(self):
        """Test readiness check endpoint."""
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_root_endpoint(self):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["status"] == "running"

    def test_api_info(self):
        """Test API info endpoint."""
        response = client.get("/api/v1")
        assert response.status_code == 200
        data = response.json()
        assert data["api_version"] == "v1"
        assert "endpoints" in data


class TestProductCreation:
    """Test suite for product creation."""

    @pytest.fixture
    def valid_product_data(self):
        """Fixture for valid product data."""
        return {
            "sku": "TEST-001",
            "name": "Test Product",
            "category_slug": "digital-calipers",
            "brand": "TestBrand",
            "base_price": 99.99,
            "stock_quantity": 50,
            "is_active": True,
            "specifications": {
                "technical_specs": {
                    "range": "0-150mm",
                    "accuracy": "±0.02mm",
                    "resolution": "0.01mm",
                    "material": "Stainless steel",
                    "standard": "DIN862",
                    "battery_type": "CR2032",
                },
                "features": {
                    "waterproof": False,
                    "data_output": True,
                    "auto_power_off": True,
                    "buttons": ["on/off", "zero"],
                    "certification": "ISO certified",
                },
                "dimensions": {
                    "L_mm": 236,
                    "a_mm": 21,
                    "b_mm": 16,
                    "c_mm": 16,
                    "d_mm": 40,
                },
                "optional_accessories": ["Wireless transmitter", "Accessory set"],
            },
        }

    def test_create_product_success(self, valid_product_data):
        """Test successful product creation."""
        response = client.post("/api/v1/products/", json=valid_product_data)
        assert response.status_code == 201
        data = response.json()
        assert data["sku"] == "TEST-001"
        assert data["name"] == "Test Product"
        assert "id" in data
        assert "created_at" in data

    def test_create_product_invalid_price(self, valid_product_data):
        """Test product creation with negative price."""
        valid_product_data["base_price"] = -10
        response = client.post("/api/v1/products/", json=valid_product_data)
        assert response.status_code == 422  # Validation error

    def test_create_product_invalid_stock(self, valid_product_data):
        """Test product creation with negative stock."""
        valid_product_data["stock_quantity"] = -5
        response = client.post("/api/v1/products/", json=valid_product_data)
        assert response.status_code == 422  # Validation error


class TestProductRetrieval:
    """Test suite for product retrieval."""

    def test_list_products_empty(self):
        """Test listing products when none exist."""
        response = client.get("/api/v1/products/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_products_with_pagination(self):
        """Test listing products with pagination."""
        response = client.get("/api/v1/products/?skip=0&limit=50")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert data["skip"] == 0
        assert data["limit"] == 50

    def test_list_products_invalid_limit(self):
        """Test listing products with invalid limit."""
        response = client.get("/api/v1/products/?limit=2000")
        assert response.status_code == 422  # Validation error


class TestProductUpdate:
    """Test suite for product updates."""

    def test_update_nonexistent_product(self):
        """Test updating a product that doesn't exist."""
        non_existent_id = "00000000-0000-0000-0000-000000000000"
        response = client.put(
            f"/api/v1/products/{non_existent_id}",
            json={"name": "Updated Name"}
        )
        assert response.status_code == 404


class TestProductDeletion:
    """Test suite for product deletion."""

    def test_delete_nonexistent_product(self):
        """Test deleting a product that doesn't exist."""
        non_existent_id = "00000000-0000-0000-0000-000000000000"
        response = client.delete(f"/api/v1/products/{non_existent_id}")
        assert response.status_code == 404


class TestStockManagement:
    """Test suite for stock management."""

    def test_adjust_stock_nonexistent_product(self):
        """Test adjusting stock for non-existent product."""
        non_existent_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(
            f"/api/v1/products/{non_existent_id}/stock/adjust?quantity_delta=10"
        )
        assert response.status_code == 404

    def test_get_stock_status_nonexistent_product(self):
        """Test getting stock status for non-existent product."""
        non_existent_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/products/{non_existent_id}/stock")
        assert response.status_code == 404
