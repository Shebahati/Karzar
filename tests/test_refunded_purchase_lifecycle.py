"""Refunded purchase orders may only advance to cancelled."""

from __future__ import annotations

import asyncio

import pytest
from app.db.models.commerce import Order, OrderMode, OrderStatus, OrderStatusEvent, PaymentStatus
from app.db.models.product import StockMovement, StockMovementType
from app.services.order_service import transition_order_status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from tests.conftest import TestingSessionLocal


async def _seed_purchase_order(
    *,
    status: str,
    payment_status: str = PaymentStatus.REFUNDED.value,
    tracking_suffix: str,
) -> int:
    async with TestingSessionLocal() as db:
        order = Order(
            tracking_code=f"KZ-REFUND-GUARD-{tracking_suffix}",
            mode=OrderMode.PURCHASE,
            status=status,
            payment_status=payment_status,
            payment_ref_id="PAY-REF-1",
            payment_refund_id="EXT-REF-GUARD",
            estimated_total=100_000,
            customer_phone="09120001111",
            customer_full_name="Test",
        )
        db.add(order)
        await db.flush()
        order_id = order.id
        await db.commit()
        return order_id


async def _counts(order_id: int) -> tuple[int, int]:
    async with TestingSessionLocal() as db:
        events = (
            await db.execute(
                select(func.count())
                .select_from(OrderStatusEvent)
                .where(OrderStatusEvent.order_id == order_id)
            )
        ).scalar_one()
        returns = (
            await db.execute(
                select(func.count())
                .select_from(StockMovement)
                .where(
                    StockMovement.reference_id == f"order:{order_id}",
                    StockMovement.movement_type == StockMovementType.RETURN.value,
                )
            )
        ).scalar_one()
        return events, returns


@pytest.mark.usefixtures("override_database")
def test_refunded_paid_cannot_advance_to_processing():
    order_id = asyncio.run(_seed_purchase_order(status=OrderStatus.PAID.value, tracking_suffix="PAID"))
    events_before, returns_before = asyncio.run(_counts(order_id))

    async def attempt():
        async with TestingSessionLocal() as db:
            order = await db.get(Order, order_id)
            with pytest.raises(ValueError, match="only transition to cancelled"):
                await transition_order_status(db, order, OrderStatus.PROCESSING.value)

    asyncio.run(attempt())
    events_after, returns_after = asyncio.run(_counts(order_id))
    assert events_after == events_before
    assert returns_after == returns_before


@pytest.mark.usefixtures("override_database")
def test_refunded_processing_cannot_advance_to_shipped():
    order_id = asyncio.run(
        _seed_purchase_order(status=OrderStatus.PROCESSING.value, tracking_suffix="PROC")
    )

    async def attempt():
        async with TestingSessionLocal() as db:
            order = await db.get(Order, order_id)
            with pytest.raises(ValueError, match="only transition to cancelled"):
                await transition_order_status(
                    db,
                    order,
                    OrderStatus.SHIPPED.value,
                    postal_tracking_code="12345678901234",
                )

    asyncio.run(attempt())


@pytest.mark.usefixtures("override_database")
def test_refunded_shipped_cannot_advance_to_delivered():
    order_id = asyncio.run(
        _seed_purchase_order(status=OrderStatus.SHIPPED.value, tracking_suffix="SHIP")
    )

    async def attempt():
        async with TestingSessionLocal() as db:
            order = await db.get(Order, order_id)
            with pytest.raises(ValueError, match="only transition to cancelled"):
                await transition_order_status(db, order, OrderStatus.DELIVERED.value)

    asyncio.run(attempt())


@pytest.mark.usefixtures("override_database")
def test_refunded_processing_can_cancel(monkeypatch):
    async def noop_notify(**_kwargs):
        return None

    monkeypatch.setattr(
        "app.services.order_service.notify_order_status_change",
        noop_notify,
    )
    order_id = asyncio.run(
        _seed_purchase_order(status=OrderStatus.PROCESSING.value, tracking_suffix="PCAN")
    )

    async def cancel():
        async with TestingSessionLocal() as db:
            order = (
                await db.execute(
                    select(Order).where(Order.id == order_id).options(selectinload(Order.items))
                )
            ).scalar_one()
            await transition_order_status(db, order, OrderStatus.CANCELLED.value)
            await db.commit()
            refreshed = await db.get(Order, order_id)
            assert refreshed.status == OrderStatus.CANCELLED.value

    asyncio.run(cancel())


@pytest.mark.usefixtures("override_database")
def test_refunded_shipped_can_cancel(monkeypatch):
    async def noop_notify(**_kwargs):
        return None

    monkeypatch.setattr(
        "app.services.order_service.notify_order_status_change",
        noop_notify,
    )
    order_id = asyncio.run(
        _seed_purchase_order(status=OrderStatus.SHIPPED.value, tracking_suffix="SCAN")
    )

    async def cancel():
        async with TestingSessionLocal() as db:
            order = (
                await db.execute(
                    select(Order).where(Order.id == order_id).options(selectinload(Order.items))
                )
            ).scalar_one()
            await transition_order_status(db, order, OrderStatus.CANCELLED.value)
            await db.commit()
            refreshed = await db.get(Order, order_id)
            assert refreshed.status == OrderStatus.CANCELLED.value

    asyncio.run(cancel())


@pytest.mark.usefixtures("override_database")
def test_refunded_delivered_can_cancel(monkeypatch):
    async def noop_notify(**_kwargs):
        return None

    monkeypatch.setattr(
        "app.services.order_service.notify_order_status_change",
        noop_notify,
    )
    order_id = asyncio.run(
        _seed_purchase_order(status=OrderStatus.DELIVERED.value, tracking_suffix="DCAN")
    )

    async def cancel():
        async with TestingSessionLocal() as db:
            order = (
                await db.execute(
                    select(Order).where(Order.id == order_id).options(selectinload(Order.items))
                )
            ).scalar_one()
            await transition_order_status(db, order, OrderStatus.CANCELLED.value)
            await db.commit()
            refreshed = await db.get(Order, order_id)
            assert refreshed.status == OrderStatus.CANCELLED.value

    asyncio.run(cancel())
