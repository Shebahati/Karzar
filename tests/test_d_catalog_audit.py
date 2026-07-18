"""Phase D catalog audit probes: inactive PDP, slugs, stock path, admin surfaces."""

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_inactive_product_hidden_on_public_pdp(valid_product_data, super_admin_headers):
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "D-INACT-PDP", "is_active": False},
        headers=super_admin_headers,
    )
    assert create.status_code == 201
    product_id = create.json()["id"]

    public = client.get(f"/api/v1/products/{product_id}")
    assert public.status_code == 404
    assert public.json()["error_code"] == "NOT_FOUND"

    admin = client.get(f"/api/v1/products/{product_id}", headers=super_admin_headers)
    assert admin.status_code == 200
    assert admin.json()["is_active"] is False


def test_category_and_brand_slug_lookup(super_admin_headers):
    categories = client.get("/api/v1/categories/").json()["data"]
    leaf = next(row for row in categories if row["is_selectable"])
    by_slug = client.get(f"/api/v1/categories/slug/{leaf['slug']}")
    assert by_slug.status_code == 200
    assert by_slug.json()["id"] == leaf["id"]
    assert by_slug.json()["slug"] == leaf["slug"]

    brand = client.post(
        "/api/v1/brands/",
        json={"name": "D Audit Brand", "country": "IR"},
        headers=super_admin_headers,
    )
    assert brand.status_code == 201
    brand_body = brand.json()
    fetched = client.get(f"/api/v1/brands/slug/{brand_body['slug']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == brand_body["id"]


def test_stock_quantity_update_blocked_on_put(valid_product_data, super_admin_headers):
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "D-STOCK-PUT"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    blocked = client.put(
        f"/api/v1/products/{product_id}",
        json={"stock_quantity": "999"},
        headers=super_admin_headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["error_code"] == "BAD_REQUEST"
    assert "stock adjust" in blocked.json()["message"].lower()


def test_statistics_and_change_log_require_admin(valid_product_data, super_admin_headers):
    from app.api.deps import get_current_super_admin
    from app.main import app as fastapi_app

    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "D-ADMIN-SURF"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]

    # super_admin_headers installs a dependency override; clear it to assert real auth gates.
    fastapi_app.dependency_overrides.pop(get_current_super_admin, None)

    assert client.get("/api/v1/products/statistics").status_code == 401
    assert client.get(f"/api/v1/products/{product_id}/change-log").status_code == 401

    stats = client.get("/api/v1/products/statistics", headers=super_admin_headers)
    assert stats.status_code == 200
    assert "total_products" in stats.json()

    log = client.get(
        f"/api/v1/products/{product_id}/change-log",
        headers=super_admin_headers,
    )
    assert log.status_code == 200
    assert "data" in log.json()


def test_product_api_does_not_expose_seo_fields_yet(valid_product_data, super_admin_headers):
    """DB has slug/meta_* but API contract currently omits them (known SEO debt)."""
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "D-SEO-DEBT"},
        headers=super_admin_headers,
    )
    assert create.status_code == 201
    body = create.json()
    for field in ("slug", "meta_title", "meta_description"):
        assert field not in body

    leaf = next(
        row for row in client.get("/api/v1/categories/").json()["data"] if row["is_selectable"]
    )
    category = client.get(f"/api/v1/categories/slug/{leaf['slug']}").json()
    assert "slug" in category
    assert "meta_title" not in category
    assert "meta_description" not in category
