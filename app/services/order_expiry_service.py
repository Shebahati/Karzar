"""Automatic cancellation of abandoned unpaid purchase orders."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models.commerce import Order, OrderMode, OrderStatus
from app.services.order_service import transition_order_status

logger = get_logger(__name__)


def pending_payment_cutoff(*, now: datetime | None = None) -> datetime:
    """Orders created before this instant are eligible for expiry."""
    reference = now or datetime.now(UTC)
    return reference - timedelta(minutes=settings.PENDING_PAYMENT_EXPIRE_MINUTES)


async def cancel_expired_pending_payment_orders(db: AsyncSession) -> int:
    """Cancel stale ``pending_payment`` purchase orders and restore reserved stock.

    Returns the number of orders cancelled in this sweep.
    """
    cutoff = pending_payment_cutoff()
    stmt = (
        select(Order)
        .where(
            Order.status == OrderStatus.PENDING_PAYMENT.value,
            Order.mode == OrderMode.PURCHASE,
            Order.created_at < cutoff,
        )
        .options(selectinload(Order.items))
        .order_by(Order.id)
    )
    result = await db.execute(stmt)
    orders = list(result.scalars().all())
    if not orders:
        return 0

    cancelled = 0
    for order in orders:
        try:
            await transition_order_status(
                db,
                order,
                OrderStatus.CANCELLED.value,
            )
            cancelled += 1
            logger.info(
                "Auto-cancelled expired pending_payment order id=%s tracking=%s",
                order.id,
                order.tracking_code,
            )
        except ValueError as exc:
            logger.warning(
                "Skipped expiry for order id=%s: %s",
                order.id,
                exc,
            )

    if cancelled:
        await db.commit()
    return cancelled
