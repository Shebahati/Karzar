"""Automatic cancellation of abandoned unpaid purchase orders."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models.commerce import (
    Order,
    OrderMode,
    OrderStatus,
    PaymentStatus,
    PaymentTransaction,
    PaymentTransactionStatus,
)
from app.services.order_service import transition_order_status

logger = get_logger(__name__)


def pending_payment_cutoff(*, now: datetime | None = None) -> datetime:
    """Orders created before this instant are eligible for expiry."""
    reference = now or datetime.now(UTC)
    return reference - timedelta(minutes=settings.PENDING_PAYMENT_EXPIRE_MINUTES)


def _authority_expired(order: Order, *, now: datetime) -> bool:
    expires = order.payment_authority_expires_at
    if expires is None:
        return True
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    return expires <= now


async def _has_successful_payment_evidence(db: AsyncSession, order: Order) -> bool:
    if order.payment_status in {
        PaymentStatus.PAID.value,
        PaymentStatus.VERIFYING.value,
        PaymentStatus.RECONCILIATION_REQUIRED.value,
    }:
        return True
    if (order.payment_ref_id or "").strip():
        return True
    if order.payment_callback_received_at is not None:
        return True
    stmt = (
        select(PaymentTransaction.id)
        .where(
            PaymentTransaction.order_id == order.id,
            PaymentTransaction.status.in_(
                (
                    PaymentTransactionStatus.VERIFIED.value,
                    PaymentTransactionStatus.CALLBACK_RECEIVED.value,
                )
            ),
        )
        .limit(1)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    return row is not None


async def cancel_expired_pending_payment_orders(db: AsyncSession) -> int:
    """Cancel stale ``pending_payment`` purchase orders and restore reserved stock.

    Uses ``FOR UPDATE SKIP LOCKED`` and re-checks payment/status after lock
    acquisition so a concurrent verify cannot be overwritten (BE-21).

    Includes expired ``payment_status=failed`` rows when authority and order
    lifetime are both expired, without cancelling paid or in-flight verify rows.

    Returns the number of orders cancelled in this sweep.
    """
    now = datetime.now(UTC)
    cutoff = pending_payment_cutoff(now=now)
    stmt = (
        select(Order)
        .where(
            Order.status == OrderStatus.PENDING_PAYMENT.value,
            Order.mode == OrderMode.PURCHASE,
            Order.created_at < cutoff,
            Order.payment_status.in_(
                (PaymentStatus.UNPAID.value, PaymentStatus.FAILED.value)
            ),
            or_(
                Order.payment_authority_expires_at.is_(None),
                Order.payment_authority_expires_at <= now,
            ),
        )
        .options(selectinload(Order.items))
        .order_by(Order.id)
        .with_for_update(skip_locked=True)
    )
    result = await db.execute(stmt)
    orders = list(result.scalars().all())
    if not orders:
        return 0

    cancelled = 0
    for order in orders:
        if order.status != OrderStatus.PENDING_PAYMENT.value:
            logger.info(
                "Skipped expiry for order id=%s after lock (status=%s)",
                order.id,
                order.status,
            )
            continue
        if order.payment_status not in {
            PaymentStatus.UNPAID.value,
            PaymentStatus.FAILED.value,
        }:
            logger.info(
                "Skipped expiry for order id=%s after lock (payment=%s)",
                order.id,
                order.payment_status,
            )
            continue
        created_at = order.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if created_at >= cutoff:
            continue
        if not _authority_expired(order, now=now):
            logger.info(
                "Skipped expiry for order id=%s: payment authority still valid",
                order.id,
            )
            continue
        if await _has_successful_payment_evidence(db, order):
            logger.info(
                "Skipped expiry for order id=%s: payment evidence present",
                order.id,
            )
            continue
        try:
            await transition_order_status(
                db,
                order,
                OrderStatus.CANCELLED.value,
            )
            cancelled += 1
            logger.info(
                "Auto-cancelled expired pending_payment order id=%s tracking=%s payment=%s",
                order.id,
                order.tracking_code,
                order.payment_status,
            )
        except ValueError as exc:
            logger.warning(
                "Skipped expiry for order id=%s: %s",
                order.id,
                exc,
            )

    return cancelled
