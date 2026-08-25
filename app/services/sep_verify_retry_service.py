"""DB-backed SEP verify retry worker (survives process restart)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.commerce import Order, PaymentStatus
from app.services.sep_callback_service import (
    apply_sep_verify_failure,
    apply_sep_verify_success,
    claim_sep_verify_job,
    invoke_sep_verify_network,
)

logger = get_logger(__name__)

_BATCH_SIZE = 20


async def list_order_ids_due_for_sep_verify(db: AsyncSession) -> list[int]:
    now = datetime.now(UTC)
    stmt = (
        select(Order.id)
        .where(
            Order.deleted_at.is_(None),
            Order.payment_status == PaymentStatus.VERIFYING.value,
            Order.payment_next_verify_at.is_not(None),
            Order.payment_next_verify_at <= now,
        )
        .order_by(Order.payment_next_verify_at.asc())
        .limit(_BATCH_SIZE)
    )
    result = await db.execute(stmt)
    return [int(row[0]) for row in result.all()]


async def process_sep_verify_retries(db: AsyncSession) -> int:
    """Process due verifying orders. Returns number of orders attempted.

    Pattern: claim+commit → network (no DB lock) → apply+commit.
    """
    due_ids = await list_order_ids_due_for_sep_verify(db)
    await db.commit()
    processed = 0
    for order_id in due_ids:
        try:
            claim = await claim_sep_verify_job(db, order_id)
            await db.commit()
            if claim is None:
                continue
            try:
                result = await invoke_sep_verify_network(claim)
                await apply_sep_verify_success(db, claim, result)
                await db.commit()
            except Exception as exc:  # noqa: BLE001
                await db.rollback()
                await apply_sep_verify_failure(db, claim, exc=exc)
                await db.commit()
            processed += 1
        except Exception:
            logger.exception("SEP verify retry failed for order_id=%s", order_id)
            await db.rollback()
    return processed
