"""P5: specification labels, filter options, and template endpoints."""

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


class TestSpecEndpoints:
    def test_spec_labels_public(self):
        response = client.get("/api/v1/categories/spec-labels")
        assert response.status_code == 200
        body = response.json()
        assert "labels" in body
        assert isinstance(body["labels"], dict)
        assert body["labels"]

    def test_spec_filter_options_for_leaf_category(self):
        response = client.get("/api/v1/categories/3/spec-filter-options")
        assert response.status_code == 200
        body = response.json()
        assert body["category_id"] == 3
        assert "technical_specs" in body
        assert isinstance(body["technical_specs"], dict)

    def test_spec_template_for_selectable_leaf(self):
        response = client.get("/api/v1/categories/3/spec-templates")
        assert response.status_code == 200
        body = response.json()
        assert body["category_id"] == 3
        assert "technical_specs" in body
        assert "features" in body
        assert "dimensions" in body
        assert "default_values" in body

    def test_spec_template_rejects_root_category(self):
        response = client.get("/api/v1/categories/1/spec-templates")
        assert response.status_code == 400
        assert response.json()["error_code"] == "BAD_REQUEST"

    def test_spec_filter_options_not_found(self):
        response = client.get("/api/v1/categories/99999/spec-filter-options")
        assert response.status_code == 404
