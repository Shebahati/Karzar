"""P5: lightweight performance smoke checks (not load testing)."""

import time

import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.mark.slow
def test_product_list_responds_within_budget(valid_product_data, super_admin_headers):
    client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "P5-PERF"},
        headers=super_admin_headers,
    )

    started = time.perf_counter()
    response = client.get("/api/v1/products/?limit=50")
    elapsed = time.perf_counter() - started

    assert response.status_code == 200
    assert elapsed < 2.0, f"PLP took {elapsed:.2f}s"
