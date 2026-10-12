"""Durable dispatch state for order lifecycle SMS (application-level dedup)."""

from __future__ import annotations

from enum import Enum

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.commerce import OrderNotificationDispatch, OrderNotificationDispatchStatus


class DispatchBeginResult(str, Enum):
    """Whether the caller should invoke the SMS provider for this attempt."""

    SEND = "send"
    SKIP_ALREADY_DISPATCHED = "skip_dispatched"
    SKIP_IN_FLIGHT = "skip_in_flight"


async def begin_notification_dispatch(
    db: AsyncSession,
    *,
    order_id: int,
    channel: str,
) -> DispatchBeginResult:
    """Reserve a dispatch attempt or skip when already dispatched / in flight.

    Failed rows may be retried by moving ``failed`` → ``dispatching``.
    Does not imply provider delivery; see ``complete_notification_dispatch_*``.
    """
    channel_norm = channel.strip()
    if not channel_norm:
        return DispatchBeginResult.SKIP_ALREADY_DISPATCHED

    bind = db.get_bind()
    dialect_name = bind.dialect.name if bind is not None else ""

    if dialect_name == "postgresql":
        stmt = (
            pg_insert(OrderNotificationDispatch)
            .values(
                order_id=order_id,
                channel=channel_norm,
                status=OrderNotificationDispatchStatus.DISPATCHING.value,
                attempt_count=1,
            )
            .on_conflict_do_nothing(
                index_elements=["order_id", "channel"],
            )
        )
        result = await db.execute(stmt)
        await db.flush()
        if result.rowcount:
            return DispatchBeginResult.SEND

        row = (
            await db.execute(
                select(OrderNotificationDispatch).where(
                    OrderNotificationDispatch.order_id == order_id,
                    OrderNotificationDispatch.channel == channel_norm,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return DispatchBeginResult.SKIP_IN_FLIGHT
        if row.status == OrderNotificationDispatchStatus.DISPATCHED.value:
            return DispatchBeginResult.SKIP_ALREADY_DISPATCHED
        if row.status == OrderNotificationDispatchStatus.DISPATCHING.value:
            return DispatchBeginResult.SKIP_IN_FLIGHT
        if row.status == OrderNotificationDispatchStatus.FAILED.value:
            upd = (
                update(OrderNotificationDispatch)
                .where(
                    OrderNotificationDispatch.id == row.id,
                    OrderNotificationDispatch.status
                    == OrderNotificationDispatchStatus.FAILED.value,
                )
                .values(
                    status=OrderNotificationDispatchStatus.DISPATCHING.value,
                    attempt_count=OrderNotificationDispatch.attempt_count + 1,
                    last_error=None,
                )
            )
            retry = await db.execute(upd)
            await db.flush()
            return (
                DispatchBeginResult.SEND if retry.rowcount else DispatchBeginResult.SKIP_IN_FLIGHT
            )
        return DispatchBeginResult.SKIP_ALREADY_DISPATCHED

    # SQLite tests: insert or handle conflict explicitly.
    row = OrderNotificationDispatch(
        order_id=order_id,
        channel=channel_norm,
        status=OrderNotificationDispatchStatus.DISPATCHING.value,
        attempt_count=1,
    )
    try:
        async with db.begin_nested():
            db.add(row)
            await db.flush()
        return DispatchBeginResult.SEND
    except IntegrityError:
        existing = (
            await db.execute(
                select(OrderNotificationDispatch).where(
                    OrderNotificationDispatch.order_id == order_id,
                    OrderNotificationDispatch.channel == channel_norm,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            return DispatchBeginResult.SKIP_IN_FLIGHT
        if existing.status == OrderNotificationDispatchStatus.DISPATCHED.value:
            return DispatchBeginResult.SKIP_ALREADY_DISPATCHED
        if existing.status == OrderNotificationDispatchStatus.DISPATCHING.value:
            return DispatchBeginResult.SKIP_IN_FLIGHT
        if existing.status == OrderNotificationDispatchStatus.FAILED.value:
            existing.status = OrderNotificationDispatchStatus.DISPATCHING.value
            existing.attempt_count = int(existing.attempt_count or 0) + 1
            existing.last_error = None
            await db.flush()
            return DispatchBeginResult.SEND
        return DispatchBeginResult.SKIP_ALREADY_DISPATCHED


async def complete_notification_dispatch_success(
    db: AsyncSession,
    *,
    order_id: int,
    channel: str,
) -> None:
    channel_norm = channel.strip()
    await db.execute(
        update(OrderNotificationDispatch)
        .where(
            OrderNotificationDispatch.order_id == order_id,
            OrderNotificationDispatch.channel == channel_norm,
        )
        .values(
            status=OrderNotificationDispatchStatus.DISPATCHED.value,
            last_error=None,
        )
    )
    await db.flush()


async def complete_notification_dispatch_failure(
    db: AsyncSession,
    *,
    order_id: int,
    channel: str,
    error: str,
) -> None:
    channel_norm = channel.strip()
    await db.execute(
        update(OrderNotificationDispatch)
        .where(
            OrderNotificationDispatch.order_id == order_id,
            OrderNotificationDispatch.channel == channel_norm,
        )
        .values(
            status=OrderNotificationDispatchStatus.FAILED.value,
            last_error=error[:500],
        )
    )
    await db.flush()


async def get_notification_dispatch(
    db: AsyncSession,
    *,
    order_id: int,
    channel: str,
) -> OrderNotificationDispatch | None:
    return (
        await db.execute(
            select(OrderNotificationDispatch).where(
                OrderNotificationDispatch.order_id == order_id,
                OrderNotificationDispatch.channel == channel,
            )
        )
    ).scalar_one_or_none()
