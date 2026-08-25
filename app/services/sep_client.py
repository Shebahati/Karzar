"""Saman Kish (SEP) OnlinePG HTTP client — Token / Verify / Reverse.

Authority: official technical document v3.6 (مستند فنی نسخه 3.6).
Endpoint spelling conflict (VerifyTransaction vs VerifyTranscation) is resolved by
configurable env defaults preferring the PDF/Python spelling; no automatic fallback.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlencode, urlparse

import httpx

from app.core.config import settings
from app.services.payment_service import (
    PaymentGatewayError,
    PaymentGatewayTimeoutError,
    PaymentVerifyFailedError,
)

# Callback Status for successful card payment (table in v3.6).
SEP_CALLBACK_STATUS_OK = "2"
SEP_CALLBACK_STATE_OK = "OK"

# Verify / Reverse success ResultCode per v3.6.
SEP_RESULT_CODE_OK = 0

_PHONE_DIGITS = re.compile(r"\D+")


def normalize_sep_cell_number(phone: str | None) -> str | None:
    """Normalize IR mobile to SEP CellNumber form (e.g. 9121234567).

    Invalid numbers return None so callers can omit the optional field.
    """
    if not phone:
        return None
    digits = _PHONE_DIGITS.sub("", phone.strip())
    if digits.startswith("98") and len(digits) >= 12:
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10 and digits.startswith("9"):
        return digits
    return None


def build_sep_send_token_url(token: str) -> str:
    """Build SendToken redirect URL with proper encoding (never raw concat)."""
    base = settings.SEP_SEND_TOKEN_URL.rstrip("?")
    # Prefer query form documented as https://sep.shaparak.ir/OnlinePG/SendToken?token=...
    if "?" in base:
        return f"{base}&{urlencode({'token': token})}"
    return f"{base}?{urlencode({'token': token})}"


def assert_sep_https_host(url: str, *, label: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme != "https":
        raise ValueError(f"{label} must use HTTPS")
    host = (parsed.hostname or "").lower().rstrip(".")
    if host != "sep.shaparak.ir":
        # Allow override only when APP_ENV is development (tests may inject httpx mock URLs).
        if settings.APP_ENV == "development" and host in {"localhost", "127.0.0.1"}:
            return url.strip()
        raise ValueError(f"{label} host must be sep.shaparak.ir")
    return url.strip()


@dataclass(frozen=True)
class SepTokenResult:
    token: str


@dataclass(frozen=True)
class SepVerifyDetail:
    ref_num: str
    terminal_number: int
    original_amount: int
    affective_amount: int
    rrn: str | None
    strace_no: str | None
    masked_pan: str | None
    hashed_pan: str | None
    raw_sanitized: dict[str, Any]


def _sanitize_token_for_errors(token: str | None) -> str:
    if not token:
        return ""
    t = token.strip()
    if len(t) <= 8:
        return "***"
    return f"{t[:4]}…{t[-4:]}"


async def request_sep_token(
    *,
    amount_rials: int,
    res_num: str,
    redirect_url: str,
    cell_number: str | None,
    token_expiry_minutes: int,
) -> SepTokenResult:
    if amount_rials <= 0:
        raise PaymentGatewayError("SEP amount must be a positive integer in rials")
    terminal = (settings.SEP_TERMINAL_ID or "").strip()
    if not terminal:
        raise PaymentGatewayError("SEP_TERMINAL_ID is not configured")

    payload: dict[str, Any] = {
        "Action": "Token",
        "TerminalId": terminal,
        "Amount": int(amount_rials),
        "ResNum": res_num,
        "RedirectUrl": redirect_url,
        "TokenExpiryInMin": int(token_expiry_minutes),
    }
    if cell_number:
        payload["CellNumber"] = cell_number

    url = assert_sep_https_host(settings.SEP_TOKEN_URL, label="SEP_TOKEN_URL")
    try:
        async with httpx.AsyncClient(timeout=settings.PAYMENT_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()
    except httpx.TimeoutException as exc:
        raise PaymentGatewayTimeoutError("SEP token request timed out") from exc
    except httpx.HTTPError as exc:
        raise PaymentGatewayError("SEP token request failed") from exc
    except ValueError as exc:
        raise PaymentGatewayError("SEP token response was not valid JSON") from exc

    status_code = body.get("status")
    token = body.get("token")
    if status_code == 1 and isinstance(token, str) and token.strip():
        cleaned = token.strip()
        if not (8 <= len(cleaned) <= 128):
            raise PaymentGatewayError("SEP returned a token with unexpected length")
        return SepTokenResult(token=cleaned)

    # Never surface raw gateway prose to end users via this exception message path
    # for browser; callers map to generic errors.
    err_code = body.get("errorCode")
    raise PaymentGatewayError(f"SEP token request rejected (status={status_code}, errorCode={err_code})")


def _coerce_int(value: Any) -> int | None:
    if value is None or value is False:
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def parse_sep_verify_response(body: dict[str, Any], *, expected_ref_num: str) -> SepVerifyDetail:
    """Parse VerifyTransaction JSON; raise on non-success or amount/ref mismatch fields later."""
    result_code = _coerce_int(body.get("ResultCode"))
    success_raw = body.get("Success")
    if isinstance(success_raw, str):
        success = success_raw.strip().lower() in {"true", "1", "yes"}
    else:
        success = bool(success_raw)

    if result_code != SEP_RESULT_CODE_OK or not success:
        raise PaymentVerifyFailedError(
            f"SEP verification rejected (ResultCode={result_code}, Success={success_raw!r})"
        )

    detail = body.get("TransactionDetail")
    if not isinstance(detail, dict):
        raise PaymentGatewayError("SEP verification missing TransactionDetail")

    ref_num = str(detail.get("RefNum") or "").strip()
    if not ref_num or ref_num != expected_ref_num.strip():
        raise PaymentVerifyFailedError("SEP verification RefNum does not match callback")

    terminal_number = _coerce_int(detail.get("TerminalNumber"))
    # Official key is misspelled OrginalAmount; accept OriginalAmount as controlled fallback.
    original_amount = _coerce_int(detail.get("OrginalAmount"))
    if original_amount is None:
        original_amount = _coerce_int(detail.get("OriginalAmount"))
    affective_amount = _coerce_int(detail.get("AffectiveAmount"))
    if terminal_number is None or original_amount is None or affective_amount is None:
        raise PaymentGatewayError("SEP verification amounts/terminal incomplete")

    sanitized = {
        "ResultCode": result_code,
        "Success": True,
        "RefNum": ref_num,
        "TerminalNumber": terminal_number,
        "OrginalAmount": original_amount,
        "AffectiveAmount": affective_amount,
        "RRN": detail.get("RRN"),
        "StraceNo": detail.get("StraceNo"),
        "MaskedPan": detail.get("MaskedPan") or detail.get("MaskedPan"),
        "HashedPan": detail.get("HashedPan") or detail.get("HashedPan"),
    }
    return SepVerifyDetail(
        ref_num=ref_num,
        terminal_number=terminal_number,
        original_amount=original_amount,
        affective_amount=affective_amount,
        rrn=str(detail.get("RRN")).strip() if detail.get("RRN") else None,
        strace_no=str(detail.get("StraceNo")).strip() if detail.get("StraceNo") else None,
        masked_pan=str(detail.get("MaskedPan")).strip() if detail.get("MaskedPan") else None,
        hashed_pan=str(detail.get("HashedPan")).strip() if detail.get("HashedPan") else None,
        raw_sanitized=sanitized,
    )


async def verify_sep_transaction(*, ref_num: str, terminal_number: int) -> SepVerifyDetail:
    url = assert_sep_https_host(settings.SEP_VERIFY_URL, label="SEP_VERIFY_URL")
    payload = {"RefNum": ref_num, "TerminalNumber": int(terminal_number)}
    try:
        async with httpx.AsyncClient(timeout=settings.PAYMENT_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()
    except httpx.TimeoutException as exc:
        raise PaymentGatewayTimeoutError("SEP verification timed out") from exc
    except httpx.HTTPError as exc:
        raise PaymentGatewayError("SEP verification request failed") from exc
    except ValueError as exc:
        raise PaymentGatewayError("SEP verification response was not valid JSON") from exc

    if not isinstance(body, dict):
        raise PaymentGatewayError("SEP verification response invalid")
    return parse_sep_verify_response(body, expected_ref_num=ref_num)


async def reverse_sep_transaction(*, ref_num: str, terminal_number: int) -> dict[str, Any]:
    url = assert_sep_https_host(settings.SEP_REVERSE_URL, label="SEP_REVERSE_URL")
    payload = {"RefNum": ref_num, "TerminalNumber": int(terminal_number)}
    try:
        async with httpx.AsyncClient(timeout=settings.PAYMENT_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()
    except httpx.TimeoutException as exc:
        raise PaymentGatewayTimeoutError("SEP reverse timed out") from exc
    except httpx.HTTPError as exc:
        raise PaymentGatewayError("SEP reverse request failed") from exc
    except ValueError as exc:
        raise PaymentGatewayError("SEP reverse response was not valid JSON") from exc

    if not isinstance(body, dict):
        raise PaymentGatewayError("SEP reverse response invalid")
    result_code = _coerce_int(body.get("ResultCode"))
    success_raw = body.get("Success")
    success = (
        success_raw.strip().lower() in {"true", "1", "yes"}
        if isinstance(success_raw, str)
        else bool(success_raw)
    )
    if result_code != SEP_RESULT_CODE_OK or not success:
        raise PaymentVerifyFailedError(f"SEP reverse rejected (ResultCode={result_code})")
    return {
        "ResultCode": result_code,
        "Success": True,
        "RefNum": quote(ref_num, safe=""),  # not for URL — mark presence only
        "ref_num": ref_num,
    }
