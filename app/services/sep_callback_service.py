"""SEP OnlinePG POST callback accept + verify (two-phase, double-spend safe)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from urllib.parse import urlencode

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.crud import commerce as crud_commerce
from app.db.models.commerce import Order, OrderMode, OrderStatus, PaymentStatus
from app.services.audit_service import record_audit
from app.services.hesabfa.invoices import maybe_create_invoice_after_payment
from app.services.order_service import transition_order_status
from app.services.payment_flow_service import order_amount_rials
from app.services.payment_ledger_service import (
    record_payment_callback_received,
    record_payment_failed,
    record_payment_reconciliation_required,
    record_payment_reversed,
    record_payment_verified,
    record_payment_verifying,
)
from app.services.payment_service import (
    PaymentAmountMismatchError,
    PaymentGatewayError,
    PaymentGatewayTimeoutError,
    PaymentVerifyContext,
    PaymentVerifyFailedError,
    PaymentVerifyResult,
    get_payment_provider,
)
from app.services.sep_client import SEP_CALLBACK_STATE_OK, SEP_CALLBACK_STATUS_OK

logger = get_logger(__name__)

RedirectOutcome = Literal["success", "failure", "verifying", "reconciliation"]

_MAX_RES_NUM_LEN = 50
_MAX_REF_NUM_LEN = 50
_VERIFY_BACKOFF_SECONDS = (5, 15, 30, 60)
_VERIFY_LEASE_SECONDS = 90


@dataclass(frozen=True)
class SepCallbackFields:
    token: str
    res_num: str
    ref_num: str
    state: str
    status: str
    terminal_id: str
    mid: str | None
    trace_no: str | None
    rrn: str | None
    amount: int | None
    secure_pan: str | None
    hashed_card_number: str | None
    sanitized: dict[str, Any]


@dataclass(frozen=True)
class SepCallbackResult:
    outcome: RedirectOutcome
    tracking_code: str
    order_id: int | None = None


@dataclass(frozen=True)
class SepVerifyClaim:
    order_id: int
    tracking_code: str
    authority: str
    ref_num: str
    amount_rials: int
    attempt: int


def _form_get(form: Any, *names: str) -> str | None:
    for name in names:
        raw = form.get(name)
        if raw is None:
            continue
        text = str(raw).strip()
        if text:
            return text
    return None


def parse_sep_callback_form(form: Any) -> SepCallbackFields | None:
    """Parse SEP POST form; returns None when critical fields are missing/invalid shape."""
    res_num = _form_get(form, "ResNum")
    if not res_num or len(res_num) > _MAX_RES_NUM_LEN:
        return None

    token = _form_get(form, "Token") or ""
    ref_num = _form_get(form, "RefNum") or ""
    state = (_form_get(form, "State") or "").strip().upper()
    status = (_form_get(form, "Status") or "").strip()
    terminal_id = _form_get(form, "TerminalId", "TerminalID") or ""
    mid = _form_get(form, "MID")
    trace_no = _form_get(form, "TraceNo", "StraceNo")
    rrn = _form_get(form, "RRN", "Rrn")
    amount_raw = _form_get(form, "Amount")
    amount: int | None = None
    if amount_raw is not None:
        try:
            amount = int(amount_raw)
        except ValueError:
            amount = -1  # signal non-integer

    secure_pan = _form_get(form, "SecurePan")
    hashed = _form_get(form, "HashedCardNumber", "HashedPan")

    sanitized = {
        "ResNum": res_num,
        "State": state,
        "Status": status,
        "TerminalId": terminal_id or None,
        "MID": mid,
        "TraceNo": trace_no,
        "RRN": rrn,
        "Amount": amount if amount is not None and amount >= 0 else None,
        "SecurePan": secure_pan,
        "HashedCardNumber": hashed,
        "RefNum": ref_num or None,
    }
    return SepCallbackFields(
        token=token,
        res_num=res_num,
        ref_num=ref_num,
        state=state,
        status=status,
        terminal_id=terminal_id,
        mid=mid,
        trace_no=trace_no,
        rrn=rrn,
        amount=amount,
        secure_pan=secure_pan,
        hashed_card_number=hashed,
        sanitized=sanitized,
    )


def build_sep_storefront_redirect(*, outcome: RedirectOutcome, tracking_code: str) -> str:
    """Build 303 Location from configured storefront bases only (no open redirect)."""
    if outcome == "success":
        base = settings.PAYMENT_SUCCESS_REDIRECT_URL
        query = urlencode({"ref": tracking_code, "mode": "purchase", "paid": "1"})
    elif outcome == "verifying":
        base = settings.PAYMENT_FAILURE_REDIRECT_URL
        query = urlencode({"ref": tracking_code, "reason": "verifying"})
    elif outcome == "reconciliation":
        base = settings.PAYMENT_FAILURE_REDIRECT_URL
        query = urlencode({"ref": tracking_code, "reason": "reconciliation"})
    else:
        base = settings.PAYMENT_FAILURE_REDIRECT_URL
        query = urlencode({"ref": tracking_code, "reason": "failed"})
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}{query}"


def next_verify_backoff_seconds(attempts: int) -> int:
    if attempts <= 0:
        return _VERIFY_BACKOFF_SECONDS[0]
    idx = min(attempts - 1, len(_VERIFY_BACKOFF_SECONDS) - 1)
    return _VERIFY_BACKOFF_SECONDS[idx]


def _expected_terminal() -> str:
    return (settings.SEP_TERMINAL_ID or "").strip()


async def _mark_failed(
    db: AsyncSession,
    order: Order,
    *,
    fields: SepCallbackFields,
    ip_address: str | None,
    reason: str,
) -> SepCallbackResult:
    order.payment_status = PaymentStatus.FAILED.value
    order.payment_last_error = reason[:255]
    order.payment_next_verify_at = None
    await record_payment_failed(
        db,
        order,
        authority=order.payment_authority,
        ref_id=fields.ref_num or None,
        ip_address=ip_address,
        provider_data=fields.sanitized,
    )
    await db.flush()
    return SepCallbackResult(outcome="failure", tracking_code=order.tracking_code, order_id=order.id)


async def _security_reject(
    db: AsyncSession,
    order: Order | None,
    *,
    tracking_code: str,
    details: dict[str, Any],
) -> SepCallbackResult:
    await record_audit(
        db,
        actor_user_id=None,
        action="payment_sep_security",
        entity_type="order",
        entity_id=order.id if order else None,
        details=details,
    )
    if order is not None and order.payment_status != PaymentStatus.PAID.value:
        order.payment_last_error = str(details.get("reason", "security"))[:255]
        await db.flush()
    return SepCallbackResult(
        outcome="failure",
        tracking_code=tracking_code,
        order_id=order.id if order else None,
    )


async def reserve_sep_callback(
    db: AsyncSession,
    fields: SepCallbackFields,
    *,
    ip_address: str | None = None,
) -> SepCallbackResult:
    """Transaction A: lock order, validate callback, reserve RefNum, set verifying."""
    order = await crud_commerce.get_order_by_tracking_code_for_update(db, fields.res_num)
    if order is None or order.deleted_at is not None:
        return SepCallbackResult(outcome="failure", tracking_code=fields.res_num)

    if order.mode != OrderMode.PURCHASE or order.status == OrderStatus.CANCELLED.value:
        return await _mark_failed(
            db, order, fields=fields, ip_address=ip_address, reason="order_not_payable"
        )

    if order.payment_status == PaymentStatus.PAID.value:
        stored_ref = (order.payment_ref_id or "").strip()
        if fields.ref_num and stored_ref and stored_ref == fields.ref_num:
            return SepCallbackResult(outcome="success", tracking_code=order.tracking_code, order_id=order.id)
        return await _security_reject(
            db,
            order,
            tracking_code=order.tracking_code,
            details={
                "reason": "paid_ref_mismatch",
                "res_num": fields.res_num,
                "incoming_ref_present": bool(fields.ref_num),
            },
        )

    if order.payment_status == PaymentStatus.RECONCILIATION_REQUIRED.value:
        return SepCallbackResult(
            outcome="reconciliation", tracking_code=order.tracking_code, order_id=order.id
        )

    if (
        order.payment_status == PaymentStatus.VERIFYING.value
        and order.payment_ref_id
        and fields.ref_num
        and order.payment_ref_id == fields.ref_num
    ):
        await record_payment_callback_received(
            db,
            order,
            authority=order.payment_authority,
            ref_id=fields.ref_num,
            ip_address=ip_address,
            provider_data=fields.sanitized,
        )
        await db.flush()
        return SepCallbackResult(outcome="verifying", tracking_code=order.tracking_code, order_id=order.id)

    if not fields.token:
        return await _mark_failed(db, order, fields=fields, ip_address=ip_address, reason="token_missing")

    if not order.payment_authority or order.payment_authority != fields.token:
        return await _security_reject(
            db,
            order,
            tracking_code=order.tracking_code,
            details={"reason": "token_mismatch", "res_num": fields.res_num},
        )

    expected_terminal = _expected_terminal()
    if not expected_terminal or fields.terminal_id != expected_terminal:
        return await _security_reject(
            db,
            order,
            tracking_code=order.tracking_code,
            details={"reason": "terminal_mismatch", "res_num": fields.res_num},
        )
    if fields.mid and fields.mid != expected_terminal:
        return await _security_reject(
            db,
            order,
            tracking_code=order.tracking_code,
            details={"reason": "mid_mismatch", "res_num": fields.res_num},
        )

    if fields.state != SEP_CALLBACK_STATE_OK or fields.status != SEP_CALLBACK_STATUS_OK:
        return await _mark_failed(
            db, order, fields=fields, ip_address=ip_address, reason="gateway_declined"
        )

    if not fields.ref_num or len(fields.ref_num) > _MAX_REF_NUM_LEN:
        return await _mark_failed(db, order, fields=fields, ip_address=ip_address, reason="ref_missing")

    if fields.amount == -1:
        return await _mark_failed(
            db, order, fields=fields, ip_address=ip_address, reason="amount_non_integer"
        )

    expected_rials = order_amount_rials(order)
    if fields.amount is not None and fields.amount != expected_rials:
        return await _security_reject(
            db,
            order,
            tracking_code=order.tracking_code,
            details={
                "reason": "callback_amount_mismatch",
                "expected_rials": expected_rials,
                "callback_amount": fields.amount,
            },
        )

    other = await crud_commerce.get_order_by_payment_ref_id(db, fields.ref_num)
    if other is not None and other.id != order.id:
        return await _security_reject(
            db,
            order,
            tracking_code=order.tracking_code,
            details={"reason": "ref_bound_to_other_order", "other_order_id": other.id},
        )

    now = datetime.now(UTC)
    order.payment_callback_received_at = now
    order.payment_verify_deadline = now + timedelta(minutes=settings.SEP_VERIFY_DEADLINE_MINUTES)
    order.payment_next_verify_at = now
    order.payment_last_error = None
    order.payment_status = PaymentStatus.VERIFYING.value
    order.payment_provider_data = fields.sanitized
    try:
        order.payment_ref_id = fields.ref_num
        await db.flush()
    except IntegrityError:
        # Concurrent reserve of the same RefNum — do not continue on this session.
        logger.warning("SEP RefNum unique race for ResNum=%s", fields.res_num)
        raise

    await record_payment_callback_received(
        db,
        order,
        authority=order.payment_authority,
        ref_id=fields.ref_num,
        ip_address=ip_address,
        provider_data=fields.sanitized,
    )
    await record_payment_verifying(
        db,
        order,
        authority=order.payment_authority,
        ref_id=fields.ref_num,
        ip_address=ip_address,
    )
    await db.flush()
    return SepCallbackResult(outcome="verifying", tracking_code=order.tracking_code, order_id=order.id)


async def claim_sep_verify_job(db: AsyncSession, order_id: int) -> SepVerifyClaim | None:
    """Lock verifying order, bump attempts, lease next_verify_at, return snapshot for network call."""
    order = await crud_commerce.get_order_by_id_for_update(db, order_id)
    if order is None:
        return None

    if order.payment_status == PaymentStatus.PAID.value:
        return None
    if order.payment_status != PaymentStatus.VERIFYING.value:
        return None

    ref_num = (order.payment_ref_id or "").strip()
    authority = (order.payment_authority or "").strip()
    if not ref_num or not authority:
        order.payment_status = PaymentStatus.FAILED.value
        order.payment_next_verify_at = None
        await record_payment_failed(db, order, authority=authority or None, ref_id=ref_num or None)
        await db.flush()
        return None

    deadline = order.payment_verify_deadline
    if deadline is not None:
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=UTC)
        if datetime.now(UTC) > deadline:
            order.payment_status = PaymentStatus.RECONCILIATION_REQUIRED.value
            order.payment_last_error = "verify_deadline_exceeded"
            order.payment_next_verify_at = None
            await record_payment_reconciliation_required(
                db,
                order,
                authority=authority,
                ref_id=ref_num,
                provider_data={"reason": "verify_deadline_exceeded"},
            )
            await db.flush()
            return None

    order.payment_verify_attempts = int(order.payment_verify_attempts or 0) + 1
    attempt = order.payment_verify_attempts
    order.payment_next_verify_at = datetime.now(UTC) + timedelta(seconds=_VERIFY_LEASE_SECONDS)
    await db.flush()
    return SepVerifyClaim(
        order_id=order.id,
        tracking_code=order.tracking_code,
        authority=authority,
        ref_num=ref_num,
        amount_rials=order_amount_rials(order),
        attempt=attempt,
    )


async def invoke_sep_verify_network(claim: SepVerifyClaim) -> PaymentVerifyResult:
    """External SEP Verify call — must run outside a DB transaction."""
    return await get_payment_provider().verify_payment(
        PaymentVerifyContext(
            authority=claim.authority,
            amount_rials=claim.amount_rials,
            ref_num=claim.ref_num,
        )
    )


async def apply_sep_verify_success(
    db: AsyncSession,
    claim: SepVerifyClaim,
    result: PaymentVerifyResult,
    *,
    ip_address: str | None = None,
) -> SepCallbackResult:
    order = await crud_commerce.get_order_by_id_for_update(db, claim.order_id)
    if order is None:
        return SepCallbackResult(outcome="failure", tracking_code=claim.tracking_code)

    if order.payment_status == PaymentStatus.PAID.value:
        return SepCallbackResult(outcome="success", tracking_code=order.tracking_code, order_id=order.id)

    if order.payment_status != PaymentStatus.VERIFYING.value:
        return SepCallbackResult(outcome="failure", tracking_code=order.tracking_code, order_id=order.id)

    if (order.payment_ref_id or "").strip() != claim.ref_num:
        return await _security_reject(
            db,
            order,
            tracking_code=order.tracking_code,
            details={"reason": "verify_ref_changed"},
        )

    if not result.success:
        order.payment_status = PaymentStatus.FAILED.value
        order.payment_next_verify_at = None
        await record_payment_failed(
            db, order, authority=claim.authority, ref_id=claim.ref_num, ip_address=ip_address
        )
        await db.flush()
        return SepCallbackResult(outcome="failure", tracking_code=order.tracking_code, order_id=order.id)

    if order.status == OrderStatus.PENDING_PAYMENT.value:
        await transition_order_status(db, order, OrderStatus.PAID.value)
    order.payment_status = PaymentStatus.PAID.value
    order.payment_next_verify_at = None
    order.payment_last_error = None
    provider_data = result.provider_data or {}
    await record_payment_verified(
        db,
        order,
        authority=claim.authority,
        ref_id=result.ref_id or claim.ref_num,
        ip_address=ip_address,
        provider_data=provider_data,
        result_code=0,
        trace_no=str(provider_data.get("StraceNo")) if provider_data.get("StraceNo") else None,
        rrn=str(provider_data.get("RRN")) if provider_data.get("RRN") else None,
    )
    await maybe_create_invoice_after_payment(db, order)
    await db.flush()
    return SepCallbackResult(outcome="success", tracking_code=order.tracking_code, order_id=order.id)


async def apply_sep_verify_failure(
    db: AsyncSession,
    claim: SepVerifyClaim,
    *,
    exc: Exception,
    ip_address: str | None = None,
) -> SepCallbackResult:
    order = await crud_commerce.get_order_by_id_for_update(db, claim.order_id)
    if order is None:
        return SepCallbackResult(outcome="failure", tracking_code=claim.tracking_code)

    if order.payment_status == PaymentStatus.PAID.value:
        return SepCallbackResult(outcome="success", tracking_code=order.tracking_code, order_id=order.id)

    if isinstance(exc, PaymentAmountMismatchError):
        return await _handle_amount_mismatch(
            db, order, ref_num=claim.ref_num, ip_address=ip_address, exc=exc
        )

    if isinstance(exc, PaymentVerifyFailedError):
        order.payment_status = PaymentStatus.FAILED.value
        order.payment_next_verify_at = None
        order.payment_last_error = "verify_rejected"
        await record_payment_failed(
            db,
            order,
            authority=claim.authority,
            ref_id=claim.ref_num,
            ip_address=ip_address,
            provider_data={"error": str(getattr(exc, "message", exc))[:200]},
        )
        await db.flush()
        return SepCallbackResult(outcome="failure", tracking_code=order.tracking_code, order_id=order.id)

    if isinstance(exc, PaymentGatewayTimeoutError | PaymentGatewayError):
        order.payment_last_error = (
            "verify_timeout" if isinstance(exc, PaymentGatewayTimeoutError) else "verify_gateway_error"
        )
        order.payment_next_verify_at = datetime.now(UTC) + timedelta(
            seconds=next_verify_backoff_seconds(claim.attempt)
        )
        await db.flush()
        return SepCallbackResult(outcome="verifying", tracking_code=order.tracking_code, order_id=order.id)

    order.payment_last_error = "verify_unexpected"
    order.payment_next_verify_at = datetime.now(UTC) + timedelta(
        seconds=next_verify_backoff_seconds(claim.attempt)
    )
    await db.flush()
    return SepCallbackResult(outcome="verifying", tracking_code=order.tracking_code, order_id=order.id)


async def run_sep_verify_for_order(
    db: AsyncSession,
    order_id: int,
    *,
    ip_address: str | None = None,
) -> SepCallbackResult:
    """Claim → network → apply. Commits must surround the network call when used from workers.

    For in-request use: claim+flush, commit, network, new lock+apply+commit (see payment endpoint).
    This helper is for the retry worker which uses the same session carefully:
    claim, commit via caller, then network outside, then apply in a new session.
    """
    claim = await claim_sep_verify_job(db, order_id)
    if claim is None:
        order = await crud_commerce.get_order_by_id(db, order_id)
        if order and order.payment_status == PaymentStatus.PAID.value:
            return SepCallbackResult(outcome="success", tracking_code=order.tracking_code, order_id=order.id)
        if order and order.payment_status == PaymentStatus.RECONCILIATION_REQUIRED.value:
            return SepCallbackResult(
                outcome="reconciliation", tracking_code=order.tracking_code, order_id=order.id
            )
        tracking = order.tracking_code if order else ""
        return SepCallbackResult(outcome="failure", tracking_code=tracking, order_id=order_id)

    await db.commit()
    try:
        result = await invoke_sep_verify_network(claim)
    except Exception as exc:  # noqa: BLE001 — classified in apply
        await db.rollback()
        return await apply_sep_verify_failure(db, claim, exc=exc, ip_address=ip_address)

    return await apply_sep_verify_success(db, claim, result, ip_address=ip_address)


async def _handle_amount_mismatch(
    db: AsyncSession,
    order: Order,
    *,
    ref_num: str,
    ip_address: str | None,
    exc: PaymentAmountMismatchError,
) -> SepCallbackResult:
    order.payment_status = PaymentStatus.RECONCILIATION_REQUIRED.value
    order.payment_next_verify_at = None
    order.payment_last_error = "amount_mismatch"
    await record_payment_reconciliation_required(
        db,
        order,
        authority=order.payment_authority,
        ref_id=ref_num,
        ip_address=ip_address,
        provider_data={"reason": "amount_mismatch"},
    )
    await record_audit(
        db,
        actor_user_id=None,
        action="payment_sep_amount_mismatch",
        entity_type="order",
        entity_id=order.id,
        details={"ref_present": True},
    )
    try:
        terminal = int(_expected_terminal())
        from app.services.sep_client import reverse_sep_transaction

        reverse_body = await reverse_sep_transaction(ref_num=ref_num, terminal_number=terminal)
        await record_payment_reversed(
            db,
            order,
            authority=order.payment_authority,
            ref_id=ref_num,
            ip_address=ip_address,
            provider_data=reverse_body,
            result_code=0,
        )
    except Exception as reverse_exc:  # noqa: BLE001
        logger.warning(
            "SEP reverse after amount mismatch failed order_id=%s: %s",
            order.id,
            reverse_exc,
        )
        order.payment_last_error = "amount_mismatch_reverse_failed"
    await db.flush()
    return SepCallbackResult(
        outcome="reconciliation", tracking_code=order.tracking_code, order_id=order.id
    )
