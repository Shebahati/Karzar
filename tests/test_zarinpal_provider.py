"""Zarinpal payment provider integration tests with mocked HTTP."""

import asyncio

import httpx
import pytest
from app.core.config import settings
from app.services.payment_service import (
    PaymentVerifyFailedError,
    ZarinpalProvider,
    reset_payment_provider_for_tests,
)


def test_zarinpal_init_payment_success(monkeypatch):
    class _MockResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": {"authority": "A000111"}}

    class _MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            assert "request.json" in url
            return _MockResponse()

    monkeypatch.setattr(settings, "ZARINPAL_MERCHANT_ID", "test-merchant")
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _MockClient())
    reset_payment_provider_for_tests()

    provider = ZarinpalProvider()
    result = asyncio.run(
        provider.init_payment(
            amount_rials=10000,
            description="test",
            callback_url="http://localhost/callback",
        )
    )
    assert result.authority == "A000111"
    assert "A000111" in result.payment_url


def test_zarinpal_verify_payment_success(monkeypatch):
    class _MockResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": {"code": 100, "ref_id": "999888"}}

    class _MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            assert "verify.json" in url
            return _MockResponse()

    monkeypatch.setattr(settings, "ZARINPAL_MERCHANT_ID", "test-merchant")
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _MockClient())
    provider = ZarinpalProvider()
    result = asyncio.run(provider.verify_payment(authority="A000111", amount_rials=10000))
    assert result.success is True
    assert result.ref_id == "999888"


def test_zarinpal_verify_payment_rejected(monkeypatch):
    class _MockResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": {"code": 9}}

    class _MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            return _MockResponse()

    monkeypatch.setattr(settings, "ZARINPAL_MERCHANT_ID", "test-merchant")
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _MockClient())
    provider = ZarinpalProvider()
    with pytest.raises(PaymentVerifyFailedError):
        asyncio.run(provider.verify_payment(authority="A000111", amount_rials=10000))
