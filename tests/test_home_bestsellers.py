"""Owner-curated bestsellers: permission, order, optimistic locking and availability."""

import pytest
from app.main import app
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("override_database")
client = TestClient(app)
URL = "/api/v1/home-merchandising/bestsellers"


def test_unpublished_is_empty_and_public():
    r = client.get(URL)
    assert r.status_code == 200
    assert r.json() == {"product_ids": [], "revision": 0, "published_at": None}


def test_publish_requires_super_admin():
    r = client.put(URL, json={"product_ids": [], "expected_revision": 0})
    assert r.status_code == 401


def test_owner_publish_preserves_order_and_rejects_stale_or_duplicate(super_admin_headers, valid_product_data):
    ids = []
    for j in range(3):
        data = {**valid_product_data, "sku": f"MERCH-{j}"}
        r = client.post("/api/v1/products/", json=data, headers=super_admin_headers)
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])
    chosen = [ids[2], ids[0], ids[1]]
    r = client.put(URL, json={"product_ids": chosen, "expected_revision": 0}, headers=super_admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["product_ids"] == chosen
    assert r.json()["revision"] == 1
    assert r.json()["published_at"]
    assert client.get(URL).json()["product_ids"] == chosen
    stale = client.put(URL, json={"product_ids": [], "expected_revision": 0}, headers=super_admin_headers)
    assert stale.status_code == 409
    dup = client.put(URL, json={"product_ids": [ids[0], ids[0]], "expected_revision": 1}, headers=super_admin_headers)
    assert dup.status_code == 422
    assert client.get(URL).json()["revision"] == 1
    cleared = client.put(URL, json={"product_ids": [], "expected_revision": 1}, headers=super_admin_headers)
    assert cleared.status_code == 200
    assert cleared.json()["revision"] == 2
    assert client.get(URL).json()["product_ids"] == []


def test_publish_rejects_unavailable_and_unknown_products(super_admin_headers, valid_product_data):
    p = client.post("/api/v1/products/", json=valid_product_data, headers=super_admin_headers)
    assert p.status_code == 201
    id_ = p.json()["id"]
    bad = client.put(URL, json={"product_ids": [99999999], "expected_revision": 0}, headers=super_admin_headers)
    assert bad.status_code == 422
    changed = client.put(f"/api/v1/products/{id_}", json={"is_available": False}, headers=super_admin_headers)
    assert changed.status_code == 200, changed.text
    bad = client.put(URL, json={"product_ids": [id_], "expected_revision": 0}, headers=super_admin_headers)
    assert bad.status_code == 422
    assert client.get(URL).json()["revision"] == 0


def test_publish_forbidden_for_authenticated_non_super_admin(
    override_database, valid_product_data, monkeypatch,
):
    """Authenticated customers must not publish homepage bestsellers (403, no mutation)."""
    from app.api.deps import get_current_super_admin
    from app.core.config import settings
    from app.core.security import create_access_token

    from tests.conftest import ADMIN_PHONE, customer_auth_headers, override_super_admin

    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    app.dependency_overrides[get_current_super_admin] = override_super_admin
    admin_headers = {"Authorization": f"Bearer {create_access_token(subject=ADMIN_PHONE)}"}
    try:
        created = client.post("/api/v1/products/", json=valid_product_data, headers=admin_headers)
        assert created.status_code == 201
        product_id = created.json()["id"]
        published = client.put(
            URL,
            json={"product_ids": [product_id], "expected_revision": 0},
            headers=admin_headers,
        )
        assert published.status_code == 200
        before = client.get(URL).json()
        assert before["product_ids"] == [product_id]
        assert before["revision"] == 1
    finally:
        app.dependency_overrides.pop(get_current_super_admin, None)

    customer = customer_auth_headers("09125556677")
    denied = client.put(
        URL,
        json={"product_ids": [], "expected_revision": before["revision"]},
        headers=customer,
    )
    assert denied.status_code == 403
    after = client.get(URL).json()
    assert after == before


def test_integration_owner_publish_persists_and_public_read_matches(
    super_admin_headers, valid_product_data,
):
    """Super-admin publish survives reload reads; public GET returns ordered IDs."""
    ids = []
    for j in range(3):
        payload = {**valid_product_data, "sku": f"E2E-MERCH-{j}"}
        created = client.post("/api/v1/products/", json=payload, headers=super_admin_headers)
        assert created.status_code == 201, created.text
        ids.append(created.json()["id"])
    chosen = [ids[2], ids[0], ids[1]]
    publish = client.put(
        URL,
        json={"product_ids": chosen, "expected_revision": 0},
        headers=super_admin_headers,
    )
    assert publish.status_code == 200
    assert publish.json()["product_ids"] == chosen

    reload_admin_view = client.get(URL, headers=super_admin_headers)
    assert reload_admin_view.status_code == 200
    assert reload_admin_view.json()["product_ids"] == chosen

    public = client.get(URL)
    assert public.status_code == 200
    assert public.json()["product_ids"] == chosen

    listed = client.get(
        "/api/v1/products/",
        params={"ids": ",".join(str(i) for i in chosen), "in_stock": True, "limit": 10},
    )
    assert listed.status_code == 200
    returned_ids = {item["id"] for item in listed.json()["data"]}
    assert returned_ids == set(chosen)

    unavailable_id = ids[0]
    mark_unavailable = client.put(
        f"/api/v1/products/{unavailable_id}",
        json={"is_available": False},
        headers=super_admin_headers,
    )
    assert mark_unavailable.status_code == 200
    still_published = client.get(URL).json()
    assert still_published["product_ids"] == chosen
    reject_republish = client.put(
        URL,
        json={"product_ids": [unavailable_id], "expected_revision": still_published["revision"]},
        headers=super_admin_headers,
    )
    assert reject_republish.status_code == 422
