"""Owner-curated bestsellers: permission, order, optimistic locking and availability."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

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
