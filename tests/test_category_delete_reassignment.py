"""Category delete must never reassign products to a non-selectable parent."""

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _make_leaf(headers, *, mid_name: str, leaf_name: str) -> tuple[int, int]:
    mid = client.post(
        "/api/v1/categories/",
        json={"name": mid_name, "parent_id": 1},
        headers=headers,
    )
    assert mid.status_code == 201, mid.text
    mid_id = mid.json()["id"]
    leaf = client.post(
        "/api/v1/categories/",
        json={"name": leaf_name, "parent_id": mid_id},
        headers=headers,
    )
    assert leaf.status_code == 201, leaf.text
    assert leaf.json()["is_selectable"] is True
    return mid_id, leaf.json()["id"]


class TestCategoryDeleteReassignment:
    def test_delete_empty_leaf_without_target(self, step_up_headers):
        create = client.post(
            "/api/v1/categories/",
            json={"name": "Delete Empty Leaf", "parent_id": 2},
            headers=step_up_headers,
        )
        assert create.status_code == 201, create.text
        category_id = create.json()["id"]

        deleted = client.delete(
            f"/api/v1/categories/{category_id}",
            headers=step_up_headers,
        )
        assert deleted.status_code == 200, deleted.text
        body = deleted.json()
        assert body["products_reassigned"] == 0
        assert body["new_category_id"] is None

    def test_delete_with_products_blocks_without_target_leaf(
        self, step_up_headers, super_admin_headers, valid_product_data
    ):
        _, leaf_id = _make_leaf(
            step_up_headers,
            mid_name="Delete Mid Branch",
            leaf_name="Delete Leaf With Product",
        )

        product = client.post(
            "/api/v1/products/",
            json={
                **valid_product_data,
                "sku": f"DEL-LEAF-{leaf_id}",
                "name": "محصول تست حذف دسته",
                "category_id": leaf_id,
            },
            headers=super_admin_headers,
        )
        assert product.status_code == 201, product.text

        blocked = client.delete(
            f"/api/v1/categories/{leaf_id}",
            headers=step_up_headers,
        )
        assert blocked.status_code == 400, blocked.text
        assert blocked.json()["error_code"] == "BAD_REQUEST"
        detail_fields = {
            d.get("field") for d in (blocked.json().get("details") or [])
        }
        assert "target_category_id" in detail_fields

    def test_delete_with_products_rejects_parent_as_target(
        self, step_up_headers, super_admin_headers, valid_product_data
    ):
        mid_id, leaf_id = _make_leaf(
            step_up_headers,
            mid_name="Reject Parent Mid",
            leaf_name="Reject Parent Leaf",
        )

        product = client.post(
            "/api/v1/products/",
            json={
                **valid_product_data,
                "sku": f"DEL-PARENT-{leaf_id}",
                "name": "محصول تست والد",
                "category_id": leaf_id,
            },
            headers=super_admin_headers,
        )
        assert product.status_code == 201, product.text

        blocked = client.delete(
            f"/api/v1/categories/{leaf_id}?target_category_id={mid_id}",
            headers=step_up_headers,
        )
        assert blocked.status_code == 400, blocked.text
        assert "target_category_id" in {
            d.get("field") for d in (blocked.json().get("details") or [])
        }

        listing = client.get("/api/v1/categories/")
        ids = [row["id"] for row in listing.json()["data"]]
        assert leaf_id in ids

    def test_delete_with_products_reassigns_to_selectable_leaf(
        self, step_up_headers, super_admin_headers, valid_product_data
    ):
        _, leaf_a = _make_leaf(
            step_up_headers,
            mid_name="Reassign Mid A",
            leaf_name="Reassign Leaf A",
        )
        _, leaf_b = _make_leaf(
            step_up_headers,
            mid_name="Reassign Mid B",
            leaf_name="Reassign Leaf B",
        )

        product = client.post(
            "/api/v1/products/",
            json={
                **valid_product_data,
                "sku": f"DEL-OK-{leaf_a}",
                "name": "محصول تست انتقال",
                "category_id": leaf_a,
            },
            headers=super_admin_headers,
        )
        assert product.status_code == 201, product.text
        product_id = product.json()["id"]

        deleted = client.delete(
            f"/api/v1/categories/{leaf_a}?target_category_id={leaf_b}",
            headers=step_up_headers,
        )
        assert deleted.status_code == 200, deleted.text
        body = deleted.json()
        assert body["products_reassigned"] == 1
        assert body["new_category_id"] == leaf_b

        moved = client.get(f"/api/v1/products/{product_id}", headers=super_admin_headers)
        assert moved.status_code == 200
        assert moved.json()["category_id"] == leaf_b
