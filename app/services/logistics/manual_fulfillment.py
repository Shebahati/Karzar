"""Provider-neutral manual shipment fulfillment (Tipax, Chapar, Tehran Express)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.commerce import Order, OrderStatus
from app.db.models.logistics import Shipment
from app.services.logistics.exceptions import (
    ShipmentStateError,
    ShippingMethodConflictError,
)
from app.services.logistics.models import ShipmentStatus
from app.services.logistics.service import _append_event
from app.services.logistics.shipping_methods import MANUAL_FULFILLMENT_PROVIDERS
from app.services.order_service import transition_order_status

_HANDOFF_DESCRIPTIONS: dict[str, str] = {
    "tipax": "بسته تحویل تیپاکس شد",
    "chapar": "بسته تحویل چاپار شد",
    "local_delivery": "بسته تحویل پیک شد",
}


def is_manual_fulfillment_shipment(shipment: Shipment) -> bool:
    return (shipment.provider or "").strip() in MANUAL_FULFILLMENT_PROVIDERS


def _provider_data(shipment: Shipment) -> dict[str, Any]:
    return dict(shipment.provider_data or {})


async def manual_register(
    db: AsyncSession,
    *,
    order: Order,
    shipment: Shipment,
    tracking_code: str | None = None,
    provider_reference: str | None = None,
    note: str | None = None,
    courier_name: str | None = None,
    courier_phone: str | None = None,
    mission_reference: str | None = None,
    actor_user_id: int | None = None,
) -> Shipment:
    if not is_manual_fulfillment_shipment(shipment):
        raise ShipmentStateError("این مرسوله از مسیر ثبت دستی پشتیبانی نمی‌شود.")
    if shipment.status not in {
        ShipmentStatus.AWAITING_PACKAGING.value,
        ShipmentStatus.BOOKED.value,
    }:
        raise ShipmentStateError("ثبت اطلاعات ارسال در این وضعیت مجاز نیست.")

    provider = (shipment.provider or "").strip()
    tracking = (tracking_code or "").strip() or None
    new_ref = (provider_reference or "").strip() or None
    if provider in {"tipax", "chapar"} and not tracking and not new_ref:
        raise ShipmentStateError("کد رهگیری یا شناسه مرجع حامل الزامی است.")

    data = _provider_data(shipment)
    manual = dict(data.get("manual") or {})
    prev_tracking = (manual.get("tracking_code") or shipment.tracking_code or "").strip() or None
    prev_ref = (manual.get("provider_reference") or "").strip() or None

    if prev_tracking and tracking and prev_tracking != tracking:
        raise ShippingMethodConflictError("کد رهگیری قبلاً با مقدار دیگری ثبت شده است.")
    if prev_ref and new_ref and prev_ref != new_ref:
        raise ShippingMethodConflictError("شناسه مرجع قبلاً با مقدار دیگری ثبت شده است.")

    if courier_name:
        manual["courier_name"] = courier_name.strip()
    if courier_phone:
        manual["courier_phone"] = courier_phone.strip()
    if mission_reference:
        manual["mission_reference"] = mission_reference.strip()
    if note:
        manual["note"] = note.strip()
    if tracking:
        manual["tracking_code"] = tracking
        shipment.tracking_code = tracking
    if new_ref:
        manual["provider_reference"] = new_ref
    manual["registered_at"] = datetime.now(UTC).isoformat()
    if actor_user_id is not None:
        manual["registered_by_user_id"] = actor_user_id

    data["manual"] = manual
    shipment.provider_data = data
    became_booked = shipment.status == ShipmentStatus.AWAITING_PACKAGING.value
    if became_booked:
        shipment.status = ShipmentStatus.BOOKED.value

    await db.flush()
    changed = (
        became_booked
        or (tracking and tracking != prev_tracking)
        or (new_ref and new_ref != prev_ref)
        or bool(courier_name or courier_phone or mission_reference)
    )
    if changed:
        await _append_event(
            db,
            shipment,
            status=shipment.status,
            description="اطلاعات ارسال ثبت شد",
            provider_status=None,
            provider_code=None,
            occurred_at=datetime.now(UTC),
            payload={"manual": {k: v for k, v in manual.items() if k != "note"}},
        )
    return shipment


async def manual_handoff(
    db: AsyncSession,
    *,
    order: Order,
    shipment: Shipment,
    actor_user_id: int | None = None,
) -> Shipment:
    if not is_manual_fulfillment_shipment(shipment):
        raise ShipmentStateError("این مرسوله از مسیر تحویل دستی پشتیبانی نمی‌شود.")
    provider = (shipment.provider or "").strip()
    if shipment.status == ShipmentStatus.PICKED_UP.value:
        return shipment
    if shipment.status not in {
        ShipmentStatus.BOOKED.value,
        ShipmentStatus.AWAITING_PACKAGING.value,
    }:
        raise ShipmentStateError("تحویل به حامل در این وضعیت مجاز نیست.")

    if provider in {"tipax", "chapar"}:
        manual = (_provider_data(shipment).get("manual") or {})
        tracking = (shipment.tracking_code or manual.get("tracking_code") or "").strip()
        reference = (manual.get("provider_reference") or "").strip()
        if not tracking and not reference:
            raise ShipmentStateError("ابتدا کد رهگیری یا شناسه مرجع حامل را ثبت کنید.")

    shipment.status = ShipmentStatus.PICKED_UP.value
    if shipment.shipped_at is None:
        shipment.shipped_at = datetime.now(UTC)
    await db.flush()
    await _append_event(
        db,
        shipment,
        status=ShipmentStatus.PICKED_UP.value,
        description=_HANDOFF_DESCRIPTIONS.get(provider, "بسته تحویل حامل شد"),
        provider_status=None,
        provider_code=None,
        occurred_at=datetime.now(UTC),
        payload={"actor_user_id": actor_user_id},
    )

    if order.status == OrderStatus.PROCESSING.value:
        if provider == "local_delivery":
            await transition_order_status(
                db,
                order,
                OrderStatus.SHIPPED.value,
                actor="admin",
                postal_tracking_code=shipment.tracking_code,
                event_description="مرسوله تحویل پیک شد",
                via_shipment_lifecycle=True,
            )
        else:
            manual = (_provider_data(shipment).get("manual") or {})
            tracking = (shipment.tracking_code or manual.get("tracking_code") or "").strip()
            reference = (manual.get("provider_reference") or "").strip()
            postal = tracking or reference
            await transition_order_status(
                db,
                order,
                OrderStatus.SHIPPED.value,
                actor="admin",
                postal_tracking_code=postal,
                event_description=_HANDOFF_DESCRIPTIONS.get(provider, "مرسوله ارسال شد"),
                via_shipment_lifecycle=True,
            )
    return shipment


async def manual_deliver(
    db: AsyncSession,
    *,
    order: Order,
    shipment: Shipment,
    actor_user_id: int | None = None,
) -> Shipment:
    if not is_manual_fulfillment_shipment(shipment):
        raise ShipmentStateError("این مرسوله از مسیر تحویل دستی پشتیبانی نمی‌شود.")
    if shipment.status == ShipmentStatus.DELIVERED.value:
        return shipment
    if shipment.status not in {
        ShipmentStatus.PICKED_UP.value,
        ShipmentStatus.IN_TRANSIT.value,
        ShipmentStatus.OUT_FOR_DELIVERY.value,
        ShipmentStatus.BOOKED.value,
    }:
        raise ShipmentStateError("ثبت تحویل در این وضعیت مجاز نیست.")

    shipment.status = ShipmentStatus.DELIVERED.value
    if shipment.delivered_at is None:
        shipment.delivered_at = datetime.now(UTC)
    await db.flush()
    await _append_event(
        db,
        shipment,
        status=ShipmentStatus.DELIVERED.value,
        description="تحویل به مشتری",
        provider_status=None,
        provider_code=None,
        occurred_at=datetime.now(UTC),
        payload={"actor_user_id": actor_user_id},
    )

    if order.status == OrderStatus.SHIPPED.value:
        await transition_order_status(
            db,
            order,
            OrderStatus.DELIVERED.value,
            actor="admin",
            event_description="سفارش تحویل داده شد",
            via_shipment_lifecycle=True,
        )
    elif order.status == OrderStatus.PROCESSING.value and shipment.provider == "local_delivery":
        await transition_order_status(
            db,
            order,
            OrderStatus.SHIPPED.value,
            actor="admin",
            event_description="مرسوله ارسال شد",
            via_shipment_lifecycle=True,
        )
        await transition_order_status(
            db,
            order,
            OrderStatus.DELIVERED.value,
            actor="admin",
            event_description="سفارش تحویل داده شد",
            via_shipment_lifecycle=True,
        )
    return shipment
