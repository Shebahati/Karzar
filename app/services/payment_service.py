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


class PaymentGatewayError(Exception):
    """Raised when the payment provider returns an unexpected or invalid response."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class PaymentGatewayTimeoutError(PaymentGatewayError):
    """Raised when the payment provider does not respond within the configured timeout."""


class PaymentVerifyFailedError(PaymentGatewayError):
    """Raised when gateway verification explicitly rejects the transaction."""


@dataclass(frozen=True)
class PaymentRefundResult:
    success: bool
    refund_id: str | None


class PaymentProvider(Protocol):
    async def init_payment(self, *, amount_rials: int, description: str, callback_url: str) -> PaymentInitResult:
        ...

    async def verify_payment(self, *, authority: str, amount_rials: int) -> PaymentVerifyResult:
        ...

    async def refund_payment(self, *, ref_id: str, amount_rials: int) -> PaymentRefundResult:
        ...


class MockPaymentProvider:
    async def init_payment(self, *, amount_rials: int, description: str, callback_url: str) -> PaymentInitResult:
        authority = f"MOCK-{secrets.token_hex(8)}"
        return PaymentInitResult(
            authority=authority,
            payment_url=f"{callback_url}?authority={authority}&status=OK",
        )

    async def verify_payment(self, *, authority: str, amount_rials: int) -> PaymentVerifyResult:
        if not authority.startswith("MOCK-"):
            raise PaymentVerifyFailedError("Invalid mock payment authority")
        return PaymentVerifyResult(success=True, ref_id=f"MOCKREF-{authority[-8:]}")

    async def refund_payment(self, *, ref_id: str, amount_rials: int) -> PaymentRefundResult:
        if not ref_id.startswith("MOCKREF-"):
            raise PaymentVerifyFailedError("Invalid mock refund reference")
        return PaymentRefundResult(success=True, refund_id=f"MOCKRF-{ref_id[-8:]}")


class ZarinpalProvider:
    async def init_payment(self, *, amount_rials: int, description: str, callback_url: str) -> PaymentInitResult:
        if not settings.ZARINPAL_MERCHANT_ID:
            raise PaymentGatewayError("ZARINPAL_MERCHANT_ID is required when PAYMENT_PROVIDER=zarinpal")
        payload = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": amount_rials,
            "description": description,
            "callback_url": callback_url,
        }
        try:
            async with httpx.AsyncClient(timeout=settings.PAYMENT_TIMEOUT_SECONDS) as client:
                response = await client.post(settings.ZARINPAL_REQUEST_URL, json={"data": payload})
                response.raise_for_status()
                body = response.json()
        except httpx.TimeoutException as exc:
            raise PaymentGatewayTimeoutError("Payment gateway request timed out") from exc
        except httpx.HTTPError as exc:
            raise PaymentGatewayError("Payment gateway request failed") from exc

        data = body.get("data", {})
        authority = data.get("authority")
        if not authority:
            errors = body.get("errors") or body.get("data", {}).get("message")
            raise PaymentGatewayError(f"Zarinpal did not return authority: {errors}")
        return PaymentInitResult(
            authority=authority,
            payment_url=f"https://www.zarinpal.com/pg/StartPay/{authority}",
        )

    async def verify_payment(self, *, authority: str, amount_rials: int) -> PaymentVerifyResult:
        if not settings.ZARINPAL_MERCHANT_ID:
            raise PaymentGatewayError("ZARINPAL_MERCHANT_ID is required when PAYMENT_PROVIDER=zarinpal")
        if not authority or not authority.strip():
            raise PaymentVerifyFailedError("Payment authority is missing or invalid")
        payload = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": amount_rials,
            "authority": authority,
        }
        try:
            async with httpx.AsyncClient(timeout=settings.PAYMENT_TIMEOUT_SECONDS) as client:
                response = await client.post(settings.ZARINPAL_VERIFY_URL, json={"data": payload})
                response.raise_for_status()
                body = response.json()
        except httpx.TimeoutException as exc:
            raise PaymentGatewayTimeoutError("Payment verification request timed out") from exc
        except httpx.HTTPError as exc:
            raise PaymentGatewayError("Payment verification request failed") from exc

        data = body.get("data", {})
        code = int(data.get("code", -1))
        if code in (100, 101):
            return PaymentVerifyResult(
                success=True,
                ref_id=str(data.get("ref_id")) if data.get("ref_id") else None,
            )
        raise PaymentVerifyFailedError(f"Zarinpal verification rejected transaction (code={code})")

    async def refund_payment(self, *, ref_id: str, amount_rials: int) -> PaymentRefundResult:
        if not settings.ZARINPAL_MERCHANT_ID:
            raise PaymentGatewayError("ZARINPAL_MERCHANT_ID is required when PAYMENT_PROVIDER=zarinpal")
        if not ref_id or not ref_id.strip():
            raise PaymentVerifyFailedError("Payment reference id is missing or invalid")
        payload = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "session_id": ref_id,
            "amount": amount_rials,
        }
        refund_url = settings.ZARINPAL_VERIFY_URL.replace("verify.json", "refund.json")
        try:
            async with httpx.AsyncClient(timeout=settings.PAYMENT_TIMEOUT_SECONDS) as client:
                response = await client.post(refund_url, json={"data": payload})
                response.raise_for_status()
                body = response.json()
        except httpx.TimeoutException as exc:
            raise PaymentGatewayTimeoutError("Payment refund request timed out") from exc
        except httpx.HTTPError as exc:
            raise PaymentGatewayError("Payment refund request failed") from exc

        data = body.get("data", {})
        code = int(data.get("code", -1))
        if code in (100, 101):
            return PaymentRefundResult(
                success=True,
                refund_id=str(data.get("id")) if data.get("id") else ref_id,
            )
        raise PaymentVerifyFailedError(f"Zarinpal refund rejected transaction (code={code})")


_provider: PaymentProvider | None = None


def get_payment_provider() -> PaymentProvider:
    global _provider
    if _provider is None:
        _provider = ZarinpalProvider() if settings.PAYMENT_PROVIDER == "zarinpal" else MockPaymentProvider()
    return _provider


def reset_payment_provider_for_tests() -> None:
    global _provider
    _provider = None


def extract_stored_authority(note: str | None) -> str | None:
    """Parse the last authority= token stored on the order note field."""
    if not note:
        return None
    for segment in reversed(note.split("|")):
        segment = segment.strip()
        if segment.startswith("authority="):
            return segment.split("=", 1)[1].strip() or None
    return None
