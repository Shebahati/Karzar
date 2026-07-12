"""Brand deletion step-up authentication tests."""

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_delete_brand_requires_step_up(super_admin_headers):
    response = client.delete("/api/v1/brands/1", headers=super_admin_headers)
    assert response.status_code == 403
    assert response.json()["error_code"] == "STEP_UP_REQUIRED"


def test_delete_brand_with_step_up(super_admin_headers, step_up_headers):
    create = client.post(
        "/api/v1/brands/",
        json={"name": "Disposable Brand", "country": "DE"},
        headers=super_admin_headers,
    )
    assert create.status_code == 201
    brand_id = create.json()["id"]

    response = client.delete(f"/api/v1/brands/{brand_id}", headers=step_up_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == brand_id
    assert "products_cleared" in body
