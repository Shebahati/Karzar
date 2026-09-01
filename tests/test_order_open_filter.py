"""Open-order filter contract tests."""

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_orders_open_filter_accepts_query(super_admin_headers):
    response = client.get(
        "/api/v1/orders",
        params={"mode": "purchase", "open": "true", "limit": 5},
        headers=super_admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "data" in body
    assert "meta" in body


def test_orders_open_inquiry_filter(super_admin_headers):
    response = client.get(
        "/api/v1/orders",
        params={"mode": "inquiry", "open": "true", "limit": 5},
        headers=super_admin_headers,
    )
    assert response.status_code == 200, response.text
