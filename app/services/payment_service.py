"""Payment gateway abstraction with mock and Zarinpal providers."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import settings


@dataclass(frozen=True)
class PaymentInitResult:
    authority: str
    payment_url: str


@dataclass(frozen=True)
class PaymentVerifyResult:
    success: bool
    ref_id: str | None


class PaymentProvider(Protocol):
    async def init_payment(self, *, amount_rials: int, description: str, callback_url: str) -> PaymentInitResult:
        ...

    async def verify_payment(self, *, authority: str, amount_rials: int) -> PaymentVerifyResult:
        ...


class MockPaymentProvider:
    async def init_payment(self, *, amount_rials: int, description: str, callback_url: str) -> PaymentInitResult:
        authority = f"MOCK-{secrets.token_hex(8)}"
        return PaymentInitResult(
            authority=authority,
            payment_url=f"{callback_url}?authority={authority}&status=OK",
        )

    async def verify_payment(self, *, authority: str, amount_rials: int) -> PaymentVerifyResult:
        return PaymentVerifyResult(success=authority.startswith("MOCK-"), ref_id=f"MOCKREF-{authority[-8:]}")


class ZarinpalProvider:
    async def init_payment(self, *, amount_rials: int, description: str, callback_url: str) -> PaymentInitResult:
        if not settings.ZARINPAL_MERCHANT_ID:
            raise ValueError("ZARINPAL_MERCHANT_ID is required when PAYMENT_PROVIDER=zarinpal")
        payload = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": amount_rials,
            "description": description,
            "callback_url": callback_url,
        }
        async with httpx.AsyncClient(timeout=settings.PAYMENT_TIMEOUT_SECONDS) as client:
            response = await client.post(settings.ZARINPAL_REQUEST_URL, json={"data": payload})
            response.raise_for_status()
            body = response.json()
        data = body.get("data", {})
        authority = data.get("authority")
        if not authority:
            raise ValueError("Zarinpal did not return authority")
        return PaymentInitResult(
            authority=authority,
            payment_url=f"https://www.zarinpal.com/pg/StartPay/{authority}",
        )

    async def verify_payment(self, *, authority: str, amount_rials: int) -> PaymentVerifyResult:
        if not settings.ZARINPAL_MERCHANT_ID:
            raise ValueError("ZARINPAL_MERCHANT_ID is required when PAYMENT_PROVIDER=zarinpal")
        payload = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": amount_rials,
            "authority": authority,
        }
        async with httpx.AsyncClient(timeout=settings.PAYMENT_TIMEOUT_SECONDS) as client:
            response = await client.post(settings.ZARINPAL_VERIFY_URL, json={"data": payload})
            response.raise_for_status()
            body = response.json()
        data = body.get("data", {})
        code = int(data.get("code", -1))
        return PaymentVerifyResult(success=code in (100, 101), ref_id=str(data.get("ref_id")) if data.get("ref_id") else None)


_provider: PaymentProvider | None = None


def get_payment_provider() -> PaymentProvider:
    global _provider
    if _provider is None:
        _provider = ZarinpalProvider() if settings.PAYMENT_PROVIDER == "zarinpal" else MockPaymentProvider()
    return _provider


def reset_payment_provider_for_tests() -> None:
    global _provider
    _provider = None
