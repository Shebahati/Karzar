"""Postex settings, client header injection, and quote/checkout integration."""

from decimal import Decimal

import pytest
from app.core.config import Settings, settings
from app.core.constants import TOMAN_TO_RIAL
from app.main import app
from app.services.logistics.exceptions import ProviderTimeoutError
from app.services.logistics.models import (
    BoxType,
)
from app.services.logistics.money import IRR, irr_to_toman
from app.services.logistics.postex.client import PostexClient
from app.services.logistics.postex.mapper import parse_quotes
from app.services.logistics.service import clear_reference_caches
from fastapi.testclient import TestClient

from tests.conftest import customer_auth_headers

QUOTE_FIXTURE = {
    "pickup_price": 20000,
    "shipping_prices": [
        {
            "custom_parcel_id": "checkout",
            "courier_code": "IR_POST",
            "service_price": [
                {
                    "service_type": "EXPRESS",
                    "service_name": "پست پیشتاز",
                    "totalPrice": 150000,
                    "initPrice": 140000,
                },
                {
                    "service_type": "STANDARD",
                    "service_name": "پست معمولی",
                    "totalPrice": 90000,
                    "initPrice": 80000,
                },
            ],
        }
    ],
}

BOXES = [BoxType(id=1, name="M", length_cm=40, width_cm=30, height_cm=20)]


def _enable_postex(monkeypatch):
    monkeypatch.setattr(settings, "POSTEX_ENABLED", True)
    monkeypatch.setattr(settings, "POSTEX_API_KEY", "test-key-not-real")
    monkeypatch.setattr(settings, "POSTEX_ORIGIN_CITY_CODE", 1)
    monkeypatch.setattr(settings, "POSTEX_ORIGIN_CITY_NAME", "تهران")
    monkeypatch.setattr(settings, "POSTEX_ORIGIN_POSTAL_CODE", "1234567890")
    monkeypatch.setattr(settings, "POSTEX_ORIGIN_ADDRESS", "خیابان تست پلاک ۱")
    monkeypatch.setattr(settings, "POSTEX_ORIGIN_FIRST_NAME", "کارزار")
    monkeypatch.setattr(settings, "POSTEX_ORIGIN_LAST_NAME", "تولز")
    monkeypatch.setattr(settings, "POSTEX_ORIGIN_MOBILE", "09120000000")
    monkeypatch.setattr(settings, "POSTEX_COLLECTION_TYPE", "pick_up")
    monkeypatch.setattr(settings, "POSTEX_DEFAULT_PAYMENT_TYPE", "SENDER")
    monkeypatch.setattr(settings, "POSTEX_BASE_URL", "https://api.postex.ir/api/v1")
    clear_reference_caches()


def test_postex_disabled_by_default():
    assert settings.POSTEX_ENABLED is False


def test_enabled_requires_origin(monkeypatch):
    monkeypatch.setenv("POSTGRES_USER", "test")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test")
    monkeypatch.setenv("POSTGRES_SERVER", "localhost")
    monkeypatch.setenv("POSTGRES_DB", "test")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-with-at-least-32-characters")
    monkeypatch.setenv("ADMIN_STEP_UP_PIN", "93827461")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("POSTEX_ENABLED", "true")
    monkeypatch.setenv("REDIS_HOST", "")
    with pytest.raises(ValueError, match="POSTEX_ENABLED=true requires"):
        Settings()


def test_quote_parser_converts_irr_to_toman():
    result = parse_quotes(QUOTE_FIXTURE)
    assert len(result.options) == 2
    express = next(o for o in result.options if o.service_code == "EXPRESS")
    assert express.provider_currency == IRR
    assert express.provider_amount == Decimal("150000")
    # pickup 20000 IRR + 150000 IRR = 170000 IRR → 17000 Toman
    assert express.customer_amount_toman == irr_to_toman(170000)
    assert express.customer_amount_toman == Decimal("17000.00")
    assert TOMAN_TO_RIAL == 10


def test_client_injects_api_key_header(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        content = b'{"id":1}'

        def json(self):
            return {"id": 1}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def request(self, method, url, headers=None, json=None, params=None):
            captured["headers"] = headers
            captured["url"] = url
            return FakeResponse()

    monkeypatch.setattr("app.services.logistics.postex.client.httpx.AsyncClient", FakeAsyncClient)
    client = PostexClient(
        base_url="https://api.postex.ir/api/v1", api_key="super-secret-key", timeout_seconds=5
    )
    import asyncio

    asyncio.run(client.whoami())
    assert captured["headers"]["x-api-key"] == "super-secret-key"
    assert captured["url"].endswith("/user/whoami")


def test_mutating_timeout_is_ambiguous():
    class Boom:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def request(self, *args, **kwargs):
            import httpx

            raise httpx.TimeoutException("timeout")

    import asyncio

    import app.services.logistics.postex.client as client_mod

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(client_mod.httpx, "AsyncClient", Boom)
    client = PostexClient(base_url="https://api.postex.ir/api/v1", api_key="k", timeout_seconds=1)
    with pytest.raises(ProviderTimeoutError) as exc:
        asyncio.run(client.post_json("/parcels/bulk", {}, operation="parcels_bulk", mutating=True))
    assert exc.value.ambiguous_write is True
    monkeypatch.undo()


def test_exception_text_does_not_include_api_key():
    from app.services.logistics.redaction import redact_secrets

    payload = {"x-api-key": "super-secret-key", "nested": {"token": "abc"}}
    redacted = redact_secrets(payload)
    assert "super-secret-key" not in str(redacted)
    assert redacted["x-api-key"] == "***REDACTED***"


def test_inquiry_checkout_unaffected(
    monkeypatch, override_database, super_admin_headers, valid_product_data
):
    _enable_postex(monkeypatch)
    client = TestClient(app)
    product = {**valid_product_data, "base_price": None, "sku": "INQ-SHIP"}
    created = client.post("/api/v1/products/", json=product, headers=super_admin_headers)
    assert created.status_code == 201, created.text
    pid = created.json()["id"]
    res = client.post(
        "/api/v1/checkout",
        json={
            "mode": "inquiry",
            "customer": {"full_name": "علی تست", "phone": "09123333333", "is_guest": True},
            "items": [{"product_id": pid, "quantity": 1}],
        },
        headers={"Idempotency-Key": "inq-ship-1"},
    )
    assert res.status_code == 201, res.text
    assert res.json()["mode"] == "inquiry"


def test_purchase_without_quote_token_when_enabled(
    monkeypatch, override_database, super_admin_headers, valid_product_data
):
    _enable_postex(monkeypatch)
    client = TestClient(app)
    product = {
        **valid_product_data,
        "sku": "SHIP-1",
        "weight_grams": "200",
        "package_length_cm": "10",
        "package_width_cm": "8",
        "package_height_cm": "4",
        "shipping_class": "parcel",
        "shipping_is_fragile": False,
        "shipping_is_liquid": False,
    }
    created = client.post("/api/v1/products/", json=product, headers=super_admin_headers)
    assert created.status_code == 201, created.text
    headers = customer_auth_headers()
    res = client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {"full_name": "علی تست", "phone": "09123333333", "is_guest": False},
            "items": [{"product_id": created.json()["id"], "quantity": 1}],
            "shipping": {
                "province": "تهران",
                "city": "تهران",
                "postal_code": "1234567890",
                "address_line": "خیابان آزادی پلاک ۱۲",
                "location_code": 1,
            },
        },
        headers={**headers, "Idempotency-Key": "no-quote"},
    )
    assert res.status_code == 400
    assert res.json()["error_code"] == "SHIPPING_QUOTE_REQUIRED"
