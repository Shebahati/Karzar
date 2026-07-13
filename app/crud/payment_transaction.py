"""Read helpers for the append-only payment transaction ledger."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.commerce import PaymentTransaction


async def list_payment_transactions_for_order(
    db: AsyncSession,
    order_id: int,
) -> list[PaymentTransaction]:
    stmt = (
        select(PaymentTransaction)
        .where(PaymentTransaction.order_id == order_id)
        .order_by(PaymentTransaction.id.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
