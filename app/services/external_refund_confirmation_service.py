"""Record operator-confirmed external refunds (no gateway refund call)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.crud import commerce as crud_commerce
from app.db.models.commerce import Order, OrderMode, OrderStatus, PaymentStatus
from app.db.models.user import User
from app.schemas.payment import PaymentRefundMode
from app.services.audit_service import record_audit
from app.services.order_service import transition_order_status
from app.services.payment_capabilities_service import get_payment_capabilities
from app.services.payment_flow_service import get_order_payment_authority, get_order_payment_ref_id
from app.services.payment_ledger_service import record_payment_refunded

logger = get_logger(__name__)

EXTERNAL_REFERENCE_MAX_LENGTH = 64


class ExternalRefundProviderMismatch(Exception):
    """Active provider does not use external confirmation refunds."""


class ExternalRefundConflict(Exception):
    """Refund already recorded with different external evidence."""


class ExternalRefundInvalidState(Exception):
    """Order payment state does not allow external refund confirmation."""


@dataclass(frozen=True)
class ExternalRefundEvidenceResult:
    refund_id: str
    provider: str
    evidence_recorded: bool


@dataclass(frozen=True)
class ExternalRefundOutcome:
    order_id: int
    payment_status: str
    status: str
    refund_id: str
    cancelled: bool
    reconciliation_required: bool


def _provider_data_for_external(
    *,
    external_reference: str,
    evidence_note: str | None,
    had_payment_ref: bool,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "source": "external_confirmation",
        "external_reference": external_reference,
        "original_payment_ref_present": had_payment_ref,
    }
    if evidence_note:
        data["evidence_note"] = evidence_note
    return data


def _outcome_from_order(
    order: Order, *, refund_id: str, cancelled: bool, reconciliation_required: bool
) -> ExternalRefundOutcome:
    return ExternalRefundOutcome(
        order_id=order.id,
        payment_status=order.payment_status,
        status=order.status,
        refund_id=refund_id,
        cancelled=cancelled,
        reconciliation_required=reconciliation_required,
    )


def _assert_external_confirmation_provider() -> str:
    caps = get_payment_capabilities()
    if caps.refund_mode != PaymentRefundMode.EXTERNAL_CONFIRMATION:
        raise ExternalRefundProviderMismatch
    return caps.provider


async def persist_external_refund_evidence(
    db: AsyncSession,
    order: Order,
    *,
    external_reference: str,
    evidence_note: str | None,
    actor_user: User,
    ip_address: str | None,
) -> ExternalRefundEvidenceResult:
    """Phase 1: durable refund bookkeeping (commit required by caller before cancellation)."""
    provider = _assert_external_confirmation_provider()

    if order.mode != OrderMode.PURCHASE:
        raise ExternalRefundInvalidState("Only purchase orders support external refund confirmation")

    ext_ref = external_reference

    if order.payment_status == PaymentStatus.REFUNDED.value:
        if order.payment_refund_id == ext_ref:
            return ExternalRefundEvidenceResult(
                refund_id=ext_ref, provider=provider, evidence_recorded=False
            )
        raise ExternalRefundConflict("Order is already refunded with a different external reference")

    if order.payment_status != PaymentStatus.PAID.value:
        raise ExternalRefundInvalidState(
            f"External refund confirmation requires payment_status=paid (got {order.payment_status})"
        )

    payment_ref = get_order_payment_ref_id(order)
    if not payment_ref:
        raise ExternalRefundInvalidState("Payment reference id not found on order")

    previous_payment_status = order.payment_status

    order.payment_status = PaymentStatus.REFUNDED.value
    order.payment_refund_id = ext_ref
    provider_data = _provider_data_for_external(
        external_reference=ext_ref,
        evidence_note=evidence_note,
        had_payment_ref=True,
    )
    await record_payment_refunded(
        db,
        order,
        authority=get_order_payment_authority(order),
        ref_id=ext_ref,
        refund_id=ext_ref,
        ip_address=ip_address,
        provider_data=provider_data,
    )
    await record_audit(
        db,
        actor_user_id=actor_user.id,
        action="payment_external_refund_confirmed",
        entity_type="order",
        entity_id=order.id,
        details={
            "order_id": order.id,
            "provider": provider,
            "external_reference": ext_ref,
            "previous_payment_status": previous_payment_status,
            "resulting_payment_status": order.payment_status,
            "resulting_order_status": order.status,
        },
    )
    await db.flush()
    return ExternalRefundEvidenceResult(refund_id=ext_ref, provider=provider, evidence_recorded=True)


async def attempt_external_refund_order_cancellation(
    db: AsyncSession,
    order: Order,
    *,
    external_reference: str,
    provider: str,
    actor_user: User,
) -> ExternalRefundOutcome:
    """Phase 2: cancel order after refund evidence is committed (separate commit by caller)."""
    _assert_external_confirmation_provider()

    refund_id = external_reference
    if order.payment_status != PaymentStatus.REFUNDED.value or order.payment_refund_id != refund_id:
        raise ExternalRefundInvalidState("Order refund evidence does not match external reference")

    if order.status == OrderStatus.CANCELLED.value:
        return _outcome_from_order(
            order, refund_id=refund_id, cancelled=True, reconciliation_required=False
        )

    order_id = order.id
    try:
        async with db.begin_nested():
            await transition_order_status(
                db,
                order,
                OrderStatus.CANCELLED.value,
                actor="admin",
                event_description="سفارش پس از ثبت استرداد خارجی لغو شد",
            )
    except Exception as exc:
        logger.warning(
            "external refund recorded but order cancellation requires reconciliation order_id=%s: %s",
            order_id,
            exc,
        )
        await db.rollback()
        order = await crud_commerce.get_order_by_id_for_update(db, order_id)
        if order is None:
            raise ExternalRefundInvalidState("Order not found after cancellation rollback") from exc
        await record_audit(
            db,
            actor_user_id=actor_user.id,
            action="payment_external_refund_cancel_pending",
            entity_type="order",
            entity_id=order.id,
            details={
                "order_id": order.id,
                "provider": provider,
                "external_reference": refund_id,
                "current_status": order.status,
            },
        )
        await db.flush()
        return _outcome_from_order(
            order, refund_id=refund_id, cancelled=False, reconciliation_required=True
        )

    return _outcome_from_order(
        order, refund_id=refund_id, cancelled=True, reconciliation_required=False
    )
