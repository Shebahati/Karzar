"""Unit tests for category depth and product-category validation rules."""

import pytest

from app.db.models.product import Category
from app.utils.category_depth import build_category_metadata, is_selectable_product_category


def _category(category_id: int, name: str, parent_id: int | None = None) -> Category:
    return Category(id=category_id, name=name, parent_id=parent_id)


class TestSelectableCategoryRules:
    def test_root_leaf_is_not_selectable(self):
        categories = [_category(1, "Root")]
        meta = build_category_metadata(categories)[1]
        assert meta["is_leaf"] is True
        assert is_selectable_product_category(meta) is False

    def test_depth_two_leaf_is_not_selectable(self):
        categories = [
            _category(1, "Root"),
            _category(2, "Leaf", 1),
        ]
        meta = build_category_metadata(categories)[2]
        assert meta["depth"] == 2
        assert is_selectable_product_category(meta) is False

    def test_depth_three_leaf_is_selectable(self):
        categories = [
            _category(1, "Root"),
            _category(2, "Branch", 1),
            _category(3, "Leaf", 2),
        ]
        meta = build_category_metadata(categories)[3]
        assert is_selectable_product_category(meta) is True

    def test_non_leaf_intermediate_is_not_selectable(self):
        categories = [
            _category(1, "Root"),
            _category(2, "Branch", 1),
            _category(3, "Leaf", 2),
        ]
        meta = build_category_metadata(categories)[2]
        assert meta["is_leaf"] is False
        assert is_selectable_product_category(meta) is False


class TestProductCategoryValidationEndpoint:
    def test_create_product_rejects_root_category(self, valid_product_data, super_admin_headers):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        valid_product_data["category_id"] = 1
        response = client.post(
            "/api/v1/products/",
            json=valid_product_data,
            headers=super_admin_headers,
        )
        assert response.status_code == 400
        body = response.json()
        assert body["error_code"] == "BAD_REQUEST"
        assert body["details"][0]["field"] == "category_id"

    def test_create_product_rejects_uncategorized(self, valid_product_data, super_admin_headers):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        payload = {**valid_product_data, "sku": "NO-CAT-001"}
        payload["category_id"] = None
        response = client.post(
            "/api/v1/products/",
            json=payload,
            headers=super_admin_headers,
        )
        assert response.status_code == 422

    def test_list_products_filters_category_subtree(
        self, valid_product_data, super_admin_headers
    ):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        valid_product_data["sku"] = "SUBTREE-001"
        valid_product_data["category_id"] = 3
        create = client.post(
            "/api/v1/products/",
            json=valid_product_data,
            headers=super_admin_headers,
        )
        assert create.status_code == 201

        by_leaf = client.get("/api/v1/products/?category_id=3")
        assert by_leaf.status_code == 200
        assert by_leaf.json()["meta"]["total_count"] == 1

        by_root = client.get("/api/v1/products/?category_id=1")
        assert by_root.status_code == 200
        assert by_root.json()["meta"]["total_count"] == 1

        by_branch = client.get("/api/v1/products/?category_id=2")
        assert by_branch.status_code == 200
        assert by_branch.json()["meta"]["total_count"] == 1
