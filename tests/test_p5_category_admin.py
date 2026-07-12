"""P5: category admin CRUD endpoint tests."""

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


class TestCategoryAdminCrud:
    def test_create_update_list_category(self, super_admin_headers):
        create = client.post(
            "/api/v1/categories/",
            json={"name": "P5 Admin Branch", "parent_id": 1},
            headers=super_admin_headers,
        )
        assert create.status_code == 201, create.text
        body = create.json()
        assert body["name"] == "P5 Admin Branch"
        assert body["depth"] == 2
        assert body["is_selectable"] is False
        category_id = body["id"]

        listing = client.get("/api/v1/categories/", headers=super_admin_headers)
        assert listing.status_code == 200
        names = [row["name"] for row in listing.json()["data"]]
        assert "P5 Admin Branch" in names

        updated = client.put(
            f"/api/v1/categories/{category_id}",
            json={"name": "P5 Admin Branch Updated"},
            headers=super_admin_headers,
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "P5 Admin Branch Updated"

    def test_delete_leaf_category_requires_step_up(self, super_admin_headers):
        create = client.post(
            "/api/v1/categories/",
            json={"name": "P5 Delete Me", "parent_id": 2},
            headers=super_admin_headers,
        )
        assert create.status_code == 201
        category_id = create.json()["id"]

        blocked = client.delete(
            f"/api/v1/categories/{category_id}",
            headers=super_admin_headers,
        )
        assert blocked.status_code == 403
        assert blocked.json()["error_code"] == "STEP_UP_REQUIRED"

    def test_delete_leaf_category_with_step_up(self, step_up_headers):
        create = client.post(
            "/api/v1/categories/",
            json={"name": "P5 Delete Leaf", "parent_id": 2},
            headers=step_up_headers,
        )
        assert create.status_code == 201
        category_id = create.json()["id"]

        deleted = client.delete(
            f"/api/v1/categories/{category_id}",
            headers=step_up_headers,
        )
        assert deleted.status_code == 200
        assert deleted.json()["id"] == category_id

        missing = client.get("/api/v1/categories/")
        ids = [row["id"] for row in missing.json()["data"]]
        assert category_id not in ids

    def test_create_category_requires_auth(self):
        response = client.post(
            "/api/v1/categories/",
            json={"name": "Unauthorized", "parent_id": 1},
        )
        assert response.status_code == 401
