"""Guards and row locks for manual Postex portal fulfillment."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.commerce import Order
from app.db.models.logistics import Shipment
from app.services.logistics.exceptions import ShipmentStateError
from app.services.logistics.fulfillment_mode import is_manual_portal_shipment
from app.services.logistics.models import ShipmentStatus

_MANUAL_TERMINAL = frozenset(
    {
        ShipmentStatus.CANCELLED.value,
        ShipmentStatus.DELIVERED.value,
        ShipmentStatus.RETURNED.value,
    }
)

_GENERIC_POSTEX_MESSAGE = (
    "این مرسوله از مسیر ثبت دستی پنل پستکس است؛ عملیات API پستکس مجاز نیست."
)


def is_active_manual_portal_shipment(shipment: Shipment) -> bool:
    if not is_manual_portal_shipment(shipment):
        return False
    return shipment.status not in _MANUAL_TERMINAL


def reject_generic_postex_provider_path(shipment: Shipment) -> None:
    """Fail closed before any Postex HTTP for manual-portal shipments."""
    if is_manual_portal_shipment(shipment):
        raise ShipmentStateError(
            _GENERIC_POSTEX_MESSAGE,
            error_code="SHIPMENT_STATE_INVALID",
        )


async def order_has_active_manual_portal_shipment(db: AsyncSession, order_id: int) -> bool:
    shipments = (
        await db.execute(select(Shipment).where(Shipment.order_id == order_id))
    ).scalars().all()
    return any(is_active_manual_portal_shipment(row) for row in shipments)


async def lock_order_and_shipment(
    db: AsyncSession,
    *,
    order_id: int,
    shipment_id: int,
) -> tuple[Order, Shipment]:
    """Lock order then shipment (consistent order) for manual portal mutations."""
    order = (
        await db.execute(select(Order).where(Order.id == order_id).with_for_update())
    ).scalar_one_or_none()
    if order is None:
        raise ShipmentStateError("سفارش یافت نشد.", error_code="SHIPMENT_NOT_FOUND")
    shipment = (
        await db.execute(
            select(Shipment)
            .where(Shipment.id == shipment_id, Shipment.order_id == order_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if shipment is None:
        raise ShipmentStateError("مرسوله یافت نشد.", error_code="SHIPMENT_NOT_FOUND")
    return order, shipment


async def lock_order_for_status_update(db: AsyncSession, order_id: int) -> Order | None:
    return (
        await db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items))
            .with_for_update()
        )
    ).scalar_one_or_none()
