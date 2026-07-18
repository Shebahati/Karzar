"""Phase C security probes: refresh reuse, step-up single-use, customer authz."""

from app.core.config import settings
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_refresh_token_reuse_rejected():
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "09120000001", "password": "adminpass123"},
    )
    assert login.status_code == 200
    old_refresh = login.json()["refresh_token"]

    first = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert first.status_code == 200
    assert first.json()["refresh_token"] != old_refresh

    second = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert second.status_code == 401
    assert second.json()["error_code"] == "UNAUTHORIZED"


def test_step_up_token_single_use(super_admin_headers, step_up_headers, valid_product_data):
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "C-STEP-ONCE"},
        headers=super_admin_headers,
    )
    assert create.status_code == 201
    product_id = create.json()["id"]

    first = client.delete(f"/api/v1/products/{product_id}", headers=step_up_headers)
    assert first.status_code == 204

    create2 = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "C-STEP-ONCE-2"},
        headers=super_admin_headers,
    )
    assert create2.status_code == 201
    product_id_2 = create2.json()["id"]

    second = client.delete(f"/api/v1/products/{product_id_2}", headers=step_up_headers)
    assert second.status_code == 403
    assert second.json()["error_code"] in {"STEP_UP_INVALID", "STEP_UP_REQUIRED"}


def test_customer_cannot_access_admin_surfaces(monkeypatch):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    phone = "09129998877"
    request = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    assert request.status_code == 200
    code = request.json()["dev_code"]
    verify = client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "code": code},
    )
    assert verify.status_code == 200
    headers = {"Authorization": f"Bearer {verify.json()['access_token']}"}

    create = client.post(
        "/api/v1/products/",
        json={"sku": "cust-block", "name": "blocked", "category_id": 1},
        headers=headers,
    )
    assert create.status_code == 403
    assert client.get("/api/v1/orders", headers=headers).status_code == 403
    assert client.get("/api/v1/cms/articles", headers=headers).status_code == 403
    assert (
        client.post("/api/v1/auth/verify-pin", json={"pin": "000000"}, headers=headers).status_code
        == 403
    )
