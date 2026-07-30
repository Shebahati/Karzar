"""Brand endpoints: step-up delete + EPIC 1 meta exposure (RFC-005)."""

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


def test_brand_response_includes_meta_fields(super_admin_headers):
    """RFC-005: BrandResponse exposes meta_title / meta_description for hubs."""
    create = client.post(
        "/api/v1/brands/",
        json={"name": "Meta Hub Brand", "country": "JP"},
        headers=super_admin_headers,
    )
    assert create.status_code == 201
    body = create.json()
    assert "meta_title" in body
    assert "meta_description" in body
    assert body["slug"]
    # Newly created brands may have null meta; keys must still be present for hubs.
    assert body["meta_title"] is None or isinstance(body["meta_title"], str)

    by_slug = client.get(f"/api/v1/brands/slug/{body['slug']}")
    assert by_slug.status_code == 200
    data = by_slug.json()
    assert data["id"] == body["id"]
    assert "meta_title" in data
    assert "meta_description" in data


def test_brand_meta_roundtrip_via_update(super_admin_headers):
    """When meta is set via admin update, slug retrieve returns them (hub SEO)."""
    create = client.post(
        "/api/v1/brands/",
        json={"name": "INSIZE Hub Test", "country": "CN"},
        headers=super_admin_headers,
    )
    assert create.status_code == 201
    brand_id = create.json()["id"]
    slug = create.json()["slug"]

    update = client.put(
        f"/api/v1/brands/{brand_id}",
        json={
            "meta_title": "INSIZE | ابزار اندازه‌گیری",
            "meta_description": "هاب برند INSIZE برای کاتالوگ کارزار",
        },
        headers=super_admin_headers,
    )
    assert update.status_code == 200
    assert update.json()["meta_title"] == "INSIZE | ابزار اندازه‌گیری"

    response = client.get(f"/api/v1/brands/slug/{slug}")
    assert response.status_code == 200
    data = response.json()
    assert data["meta_title"] == "INSIZE | ابزار اندازه‌گیری"
    assert data["meta_description"] == "هاب برند INSIZE برای کاتالوگ کارزار"
