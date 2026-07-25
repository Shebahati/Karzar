"""API tests for megamenu nav-groups admin + public endpoints."""

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _valid_payload(root_id: int = 1) -> dict:
    return {
        "groups": [
            {
                "slug": "metrology",
                "label": "اندازه‌گیری",
                "sort_order": 0,
                "is_enabled": True,
                "highlight": True,
                "root_category_ids": [root_id],
            },
            {
                "slug": "cutting",
                "label": "براده‌برداری",
                "sort_order": 1,
                "is_enabled": True,
                "highlight": False,
                "root_category_ids": [],
            },
        ]
    }


class TestNavGroupsAdmin:
    def test_list_requires_auth(self):
        assert client.get("/api/v1/cms/nav-groups").status_code == 401

    def test_replace_and_list(self, super_admin_headers):
        replaced = client.put(
            "/api/v1/cms/nav-groups",
            json=_valid_payload(root_id=1),
            headers=super_admin_headers,
        )
        assert replaced.status_code == 200, replaced.text
        body = replaced.json()
        assert len(body["data"]) == 2
        assert body["data"][0]["slug"] == "metrology"
        assert body["data"][0]["root_category_ids"] == [1]
        assert body["data"][0]["highlight"] is True

        listed = client.get("/api/v1/cms/nav-groups", headers=super_admin_headers)
        assert listed.status_code == 200
        assert [g["slug"] for g in listed.json()["data"]] == ["metrology", "cutting"]

    def test_rejects_duplicate_root_across_groups(self, super_admin_headers):
        payload = {
            "groups": [
                {
                    "slug": "a",
                    "label": "گروه الف",
                    "sort_order": 0,
                    "is_enabled": True,
                    "highlight": False,
                    "root_category_ids": [1],
                },
                {
                    "slug": "b",
                    "label": "گروه ب",
                    "sort_order": 1,
                    "is_enabled": True,
                    "highlight": False,
                    "root_category_ids": [1],
                },
            ]
        }
        response = client.put(
            "/api/v1/cms/nav-groups",
            json=payload,
            headers=super_admin_headers,
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "VALIDATION_FAILED"
        messages = " ".join(d["message"] for d in response.json().get("details", []))
        assert "1" in messages

    def test_rejects_non_l1_root(self, super_admin_headers):
        # Seeded tree: id 1 = L1, id 2 = L2, id 3 = L3
        payload = _valid_payload(root_id=2)
        response = client.put(
            "/api/v1/cms/nav-groups",
            json=payload,
            headers=super_admin_headers,
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "VALIDATION_FAILED"

    def test_rejects_unknown_category_id(self, super_admin_headers):
        payload = _valid_payload(root_id=99999)
        response = client.put(
            "/api/v1/cms/nav-groups",
            json=payload,
            headers=super_admin_headers,
        )
        assert response.status_code == 422

    def test_rejects_duplicate_slugs(self, super_admin_headers):
        payload = {
            "groups": [
                {
                    "slug": "same",
                    "label": "الف",
                    "sort_order": 0,
                    "is_enabled": True,
                    "highlight": False,
                    "root_category_ids": [],
                },
                {
                    "slug": "same",
                    "label": "ب",
                    "sort_order": 1,
                    "is_enabled": True,
                    "highlight": False,
                    "root_category_ids": [],
                },
            ]
        }
        response = client.put(
            "/api/v1/cms/nav-groups",
            json=payload,
            headers=super_admin_headers,
        )
        assert response.status_code == 422


class TestNavGroupsPublic:
    def test_public_lists_enabled_only(self, super_admin_headers):
        payload = {
            "groups": [
                {
                    "slug": "on",
                    "label": "فعال",
                    "sort_order": 0,
                    "is_enabled": True,
                    "highlight": False,
                    "root_category_ids": [1],
                },
                {
                    "slug": "off",
                    "label": "غیرفعال",
                    "sort_order": 1,
                    "is_enabled": False,
                    "highlight": False,
                    "root_category_ids": [],
                },
            ]
        }
        assert (
            client.put(
                "/api/v1/cms/nav-groups",
                json=payload,
                headers=super_admin_headers,
            ).status_code
            == 200
        )

        public = client.get("/api/v1/nav-groups/")
        assert public.status_code == 200
        data = public.json()["data"]
        assert [g["slug"] for g in data] == ["on"]
        assert "is_enabled" not in data[0]
        assert data[0]["root_category_ids"] == [1]
