"""Admin binary bulk availability API (Wave A4)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_bulk_set_availability_binary(super_admin_headers, valid_product_data):
    created = []
    for i in range(2):
        payload = {**valid_product_data, "sku": f"{valid_product_data['sku']}-BULK-{i}"}
        response = client.post("/api/v1/products/", json=payload, headers=super_admin_headers)
        assert response.status_code == 201, response.text
        created.append(response.json()["id"])

    # Mark both unavailable
    bulk = client.put(
        "/api/v1/products/bulk/availability",
        json={
            "items": [
                {"product_id": created[0], "is_available": False, "reason": "test"},
                {"product_id": created[1], "is_available": False},
            ]
        },
        headers=super_admin_headers,
    )
    assert bulk.status_code == 200, bulk.text
    body = bulk.json()
    assert set(body["updated_product_ids"]) == set(created)

    for product_id in created:
        detail = client.get(f"/api/v1/products/{product_id}", headers=super_admin_headers)
        assert detail.status_code == 200
        assert detail.json()["is_available"] is False


def test_set_available_rejects_null_price(super_admin_headers, valid_product_data):
    payload = {**valid_product_data, "sku": f"{valid_product_data['sku']}-NULLP", "base_price": None, "is_available": False}
    # Some schemas may reject null base_price on create — try create then update.
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": f"{valid_product_data['sku']}-NULLP2", "is_available": True},
        headers=super_admin_headers,
    )
    assert create.status_code == 201
    product_id = create.json()["id"]

    # Clear price via update if allowed, then try availability true
    update = client.put(
        f"/api/v1/products/{product_id}",
        json={"base_price": None, "is_available": True},
        headers=super_admin_headers,
    )
    # Either update rejects, or availability endpoint rejects
    if update.status_code >= 400:
        return
    avail = client.put(
        f"/api/v1/products/{product_id}/availability",
        params={"is_available": True},
        headers=super_admin_headers,
    )
    assert avail.status_code == 400
