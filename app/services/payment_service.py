"""Payment gateway abstraction: mock, Zarinpal, and SEP (Saman Kish)."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import settings


@dataclass(frozen=True)
class PaymentInitContext:
    amount_rials: int
    description: str
    callback_url: str
    merchant_reference: str
    payer_phone: str | None = None


@dataclass(frozen=True)
class PaymentVerifyContext:
    authority: str
    amount_rials: int
    ref_num: str | None = None


@dataclass(frozen=True)
class PaymentInitResult:
    authority: str
    payment_url: str


@dataclass(frozen=True)
class PaymentVerifyResult:
    success: bool
    ref_id: str | None
    provider_data: dict | None = None


class PaymentGatewayError(Exception):
    """Raised when the payment provider returns an unexpected or invalid response."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class PaymentGatewayTimeoutError(PaymentGatewayError):
    """Raised when the payment provider does not respond within the configured timeout."""


class PaymentVerifyFailedError(PaymentGatewayError):
    """Raised when gateway verification explicitly rejects the transaction."""


class PaymentAmountMismatchError(PaymentGatewayError):
    """Verify succeeded at gateway layer but amounts do not match the order."""

    def __init__(self, message: str, *, ref_num: str | None = None) -> None:
        super().__init__(message)
        self.ref_num = ref_num


class PaymentRefundUnsupportedError(PaymentGatewayError):
    """Raised when the active provider has no automated refund/reverse path."""


@dataclass(frozen=True)
class PaymentRefundResult:
    success: bool
    refund_id: str | None


class PaymentProvider(Protocol):
    async def init_payment(self, ctx: PaymentInitContext) -> PaymentInitResult:
        ...

    async def verify_payment(self, ctx: PaymentVerifyContext) -> PaymentVerifyResult:
        ...

    async def refund_payment(self, *, ref_id: str, amount_rials: int) -> PaymentRefundResult:
        ...


class MockPaymentProvider:
    async def init_payment(self, ctx: PaymentInitContext) -> PaymentInitResult:
        authority = f"MOCK-{secrets.token_hex(8)}"
        return PaymentInitResult(
            authority=authority,
            payment_url=f"{ctx.callback_url}?authority={authority}&status=OK",
        )

    async def verify_payment(self, ctx: PaymentVerifyContext) -> PaymentVerifyResult:
        if not ctx.authority.startswith("MOCK-"):
            raise PaymentVerifyFailedError("Invalid mock payment authority")
        return PaymentVerifyResult(success=True, ref_id=f"MOCKREF-{ctx.authority[-8:]}")

    async def refund_payment(self, *, ref_id: str, amount_rials: int) -> PaymentRefundResult:
        if not ref_id.startswith("MOCKREF-"):
            raise PaymentVerifyFailedError("Invalid mock refund reference")
        return PaymentRefundResult(success=True, refund_id=f"MOCKRF-{ref_id[-8:]}")


class ZarinpalProvider:
    async def init_payment(self, ctx: PaymentInitContext) -> PaymentInitResult:
        if not settings.ZARINPAL_MERCHANT_ID:
            raise PaymentGatewayError("ZARINPAL_MERCHANT_ID is required when PAYMENT_PROVIDER=zarinpal")
        payload = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": ctx.amount_rials,
            "description": ctx.description,
            "callback_url": ctx.callback_url,
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

    async def verify_payment(self, ctx: PaymentVerifyContext) -> PaymentVerifyResult:
        if not settings.ZARINPAL_MERCHANT_ID:
            raise PaymentGatewayError("ZARINPAL_MERCHANT_ID is required when PAYMENT_PROVIDER=zarinpal")
        if not ctx.authority or not ctx.authority.strip():
            raise PaymentVerifyFailedError("Payment authority is missing or invalid")
        payload = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": ctx.amount_rials,
            "authority": ctx.authority,
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


class SepPaymentProvider:
    """Saman Kish OnlinePG — Token init + Verify with RefNum."""

    async def init_payment(self, ctx: PaymentInitContext) -> PaymentInitResult:
        from app.services.sep_client import (
            build_sep_send_token_url,
            normalize_sep_cell_number,
            request_sep_token,
        )

        cell = normalize_sep_cell_number(ctx.payer_phone)
        token_result = await request_sep_token(
            amount_rials=ctx.amount_rials,
            res_num=ctx.merchant_reference,
            redirect_url=ctx.callback_url,
            cell_number=cell,
            token_expiry_minutes=settings.SEP_TOKEN_EXPIRY_MINUTES,
        )
        return PaymentInitResult(
            authority=token_result.token,
            payment_url=build_sep_send_token_url(token_result.token),
        )

    async def verify_payment(self, ctx: PaymentVerifyContext) -> PaymentVerifyResult:
        from app.services.sep_client import verify_sep_transaction

        if not ctx.ref_num or not ctx.ref_num.strip():
            raise PaymentVerifyFailedError("SEP verification requires RefNum")
        terminal = (settings.SEP_TERMINAL_ID or "").strip()
        if not terminal:
            raise PaymentGatewayError("SEP_TERMINAL_ID is not configured")
        try:
            terminal_number = int(terminal)
        except ValueError as exc:
            raise PaymentGatewayError("SEP_TERMINAL_ID must be numeric for Verify") from exc

        detail = await verify_sep_transaction(
            ref_num=ctx.ref_num.strip(),
            terminal_number=terminal_number,
        )
        if detail.terminal_number != terminal_number:
            raise PaymentVerifyFailedError("SEP verification TerminalNumber mismatch")
        if detail.original_amount != ctx.amount_rials or detail.affective_amount != ctx.amount_rials:
            raise PaymentAmountMismatchError(
                "SEP verification amount does not match order",
                ref_num=detail.ref_num,
            )
        return PaymentVerifyResult(
            success=True,
            ref_id=detail.ref_num,
            provider_data=detail.raw_sanitized,
        )

    async def refund_payment(self, *, ref_id: str, amount_rials: int) -> PaymentRefundResult:
        raise PaymentRefundUnsupportedError(
            "SEP automated refund is not supported via /payments/refund; "
            "use time-boxed ReverseTransaction only under a controlled reconciliation workflow"
        )


_provider: PaymentProvider | None = None


def get_payment_provider() -> PaymentProvider:
    global _provider
    if _provider is None:
        name = settings.PAYMENT_PROVIDER
        if name == "sep":
            _provider = SepPaymentProvider()
        elif name == "zarinpal":
            _provider = ZarinpalProvider()
        elif name == "mock":
            _provider = MockPaymentProvider()
        else:
            # Config validator should have rejected this; fail closed.
            raise RuntimeError(f"Unsupported PAYMENT_PROVIDER={name!r}")
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
