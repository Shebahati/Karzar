"""P5: storefront/admin API contract regression tests."""

from app.core.config import settings
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

CHECKOUT_REQUIRED_KEYS = {
    "order_id",
    "tracking_code",
    "mode",
    "status",
    "status_label",
    "estimated_total",
    "created_at",
    "payment_url",
    "authority",
}
ERROR_ENVELOPE_KEYS = {"error_code", "message", "details"}
AUTH_ME_KEYS = {"id", "phone_number", "full_name"}


class TestApiContractShapes:
    def test_error_envelope_shape(self):
        response = client.get("/api/v1/products/999999")
        assert response.status_code == 404
        body = response.json()
        assert ERROR_ENVELOPE_KEYS.issubset(body.keys())
        assert isinstance(body["details"], list)

    def test_checkout_purchase_contract_fields(
        self, valid_product_data, super_admin_headers, monkeypatch
    ):
        monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
        create = client.post(
            "/api/v1/products/",
            json={**valid_product_data, "sku": "P5-CONTRACT"},
            headers=super_admin_headers,
        )
        product_id = create.json()["id"]

        otp = client.post("/api/v1/auth/otp/request", json={"phone": "09126660002"})
        verify = client.post(
            "/api/v1/auth/otp/verify",
            json={"phone": "09126660002", "code": otp.json()["dev_code"]},
        )
        headers = {"Authorization": f"Bearer {verify.json()['access_token']}"}

        checkout = client.post(
            "/api/v1/checkout",
            json={
                "mode": "purchase",
                "customer": {"full_name": "Contract", "phone": "09126660002"},
                "items": [{"product_id": product_id, "quantity": 1}],
                "shipping": {
                    "province": "تهران",
                    "city": "تهران",
                    "postal_code": "1234567890",
                    "address_line": "خیابان قرارداد",
                },
            },
            headers=headers,
        )
        assert checkout.status_code == 201
        assert CHECKOUT_REQUIRED_KEYS.issubset(checkout.json().keys())

    def test_auth_me_contract(self, monkeypatch):
        monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
        otp = client.post("/api/v1/auth/otp/request", json={"phone": "09125550003"})
        verify = client.post(
            "/api/v1/auth/otp/verify",
            json={"phone": "09125550003", "code": otp.json()["dev_code"]},
        )
        headers = {"Authorization": f"Bearer {verify.json()['access_token']}"}
        me = client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 200
        assert AUTH_ME_KEYS.issubset(me.json().keys())

    def test_pagination_envelope(self, valid_product_data, super_admin_headers):
        client.post(
            "/api/v1/products/",
            json={**valid_product_data, "sku": "P5-PAGE"},
            headers=super_admin_headers,
        )
        response = client.get("/api/v1/products/?limit=5")
        body = response.json()
        assert "data" in body and "meta" in body
        meta = body["meta"]
        for key in ("total_count", "skip", "limit", "has_next", "has_prev"):
            assert key in meta

    def test_optional_auth_openapi_allows_anonymous(self):
        """Optional-Bearer routes must allow unauthenticated access in OpenAPI."""
        from app.main import app

        app.openapi_schema = None
        schema = app.openapi()
        checkout_security = schema["paths"]["/api/v1/checkout"]["post"]["security"]
        assert {} in checkout_security
        assert {"HTTPBearer": []} in checkout_security
        me_security = schema["paths"]["/api/v1/auth/me"]["get"]["security"]
        assert me_security == [{"OAuth2PasswordBearer": []}]
