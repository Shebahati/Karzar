"""Durable idempotency for order lifecycle notifications."""

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.commerce import OrderNotificationSent


async def claim_order_notification(
    db: AsyncSession,
    *,
    order_id: int,
    channel: str,
) -> bool:
    """Return True when this order/channel notification may be sent (first claim)."""
    channel_norm = channel.strip()
    if not channel_norm:
        return False
    bind = db.get_bind()
    dialect_name = bind.dialect.name if bind is not None else ""
    if dialect_name == "postgresql":
        stmt = (
            pg_insert(OrderNotificationSent)
            .values(order_id=order_id, channel=channel_norm)
            .on_conflict_do_nothing(index_elements=["order_id", "channel"])
        )
        result = await db.execute(stmt)
        await db.flush()
        return bool(result.rowcount)
    try:
        async with db.begin_nested():
            db.add(OrderNotificationSent(order_id=order_id, channel=channel_norm))
            await db.flush()
        return True
    except IntegrityError:
        return False
