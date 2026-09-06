"""Admin abandoned-cart API contract tests."""

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_abandoned_carts_requires_admin(super_admin_headers):
    response = client.get("/api/v1/abandoned-carts", headers=super_admin_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body["data"], list)
    assert "total_count" in body["meta"]


def test_abandoned_carts_rejects_anonymous():
    response = client.get("/api/v1/abandoned-carts")
    assert response.status_code == 401
