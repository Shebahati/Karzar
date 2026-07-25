"""Periodic re-push of failed/pending Hesabfa sale invoices (BE-07)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models.commerce import Order
from app.db.models.hesabfa import HesabfaInvoiceRecord
from app.services.hesabfa.invoices import create_invoice_for_paid_order

logger = get_logger(__name__)

# Cap retries to avoid infinite hammering of Hesabfa on permanent failures.
_MAX_ATTEMPTS = 8


def _backoff_seconds(attempt_count: int) -> int:
    """Exponential backoff: 60s, 120s, … capped at 1 hour."""
    return min(3600, 60 * (2 ** max(0, attempt_count - 1)))


async def retry_failed_hesabfa_invoices(db: AsyncSession, *, limit: int = 20) -> int:
    """Re-attempt invoice push for pending/failed records due for retry.

    Returns the number of records successfully created in this sweep.
    """
    if not settings.HESABFA_ENABLED or settings.HESABFA_TEST_MODE:
        return 0

    now = datetime.now(UTC)
    stmt = (
        select(HesabfaInvoiceRecord)
        .where(
            HesabfaInvoiceRecord.status.in_(("pending", "failed")),
            HesabfaInvoiceRecord.attempt_count < _MAX_ATTEMPTS,
            or_(
                HesabfaInvoiceRecord.next_attempt_at.is_(None),
                HesabfaInvoiceRecord.next_attempt_at <= now,
            ),
        )
        .order_by(HesabfaInvoiceRecord.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    records = list((await db.execute(stmt)).scalars().all())
    if not records:
        return 0

    created = 0
    for record in records:
        order = (
            await db.execute(
                select(Order)
                .where(Order.id == record.order_id)
                .options(selectinload(Order.items))
            )
        ).scalars().first()
        if order is None:
            record.status = "failed"
            record.error_message = "order_missing"
            record.attempt_count = _MAX_ATTEMPTS
            continue

        before = record.attempt_count
        result = await create_invoice_for_paid_order(db, order)
        # create_invoice_for_paid_order mutates the same record row.
        refreshed = (
            await db.execute(
                select(HesabfaInvoiceRecord).where(HesabfaInvoiceRecord.id == record.id)
            )
        ).scalars().first()
        if refreshed is None:
            continue

        if result.status == "created" or result.status == "already_created":
            created += 1
            continue

        refreshed.attempt_count = before + 1
        if refreshed.attempt_count >= _MAX_ATTEMPTS:
            refreshed.status = "failed"
            refreshed.next_attempt_at = None
            logger.warning(
                "Hesabfa invoice retry exhausted order_id=%s attempts=%s",
                order.id,
                refreshed.attempt_count,
            )
        else:
            refreshed.status = "failed"
            refreshed.next_attempt_at = now + timedelta(
                seconds=_backoff_seconds(refreshed.attempt_count)
            )
            logger.info(
                "Hesabfa invoice retry scheduled order_id=%s attempt=%s next=%s",
                order.id,
                refreshed.attempt_count,
                refreshed.next_attempt_at,
            )

    await db.flush()
    return created
