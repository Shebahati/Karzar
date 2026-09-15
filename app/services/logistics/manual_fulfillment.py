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

_POST_HANDOFF_DELIVERY_STATUSES = frozenset(
    {
        ShipmentStatus.PICKED_UP.value,
        ShipmentStatus.IN_TRANSIT.value,
        ShipmentStatus.OUT_FOR_DELIVERY.value,
    }
)


def is_manual_fulfillment_shipment(shipment: Shipment) -> bool:
    return (shipment.provider or "").strip() in MANUAL_FULFILLMENT_PROVIDERS


def _provider_data(shipment: Shipment) -> dict[str, Any]:
    return dict(shipment.provider_data or {})


def _manual_meta(shipment: Shipment) -> dict[str, Any]:
    return dict(_provider_data(shipment).get("manual") or {})


def _strip_opt(value: str | None) -> str | None:
    raw = (value or "").strip()
    return raw or None


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
    tracking = _strip_opt(tracking_code)
    new_ref = _strip_opt(provider_reference)
    if provider in {"tipax", "chapar"} and not tracking and not new_ref:
        raise ShipmentStateError("کد رهگیری یا شناسه مرجع حامل الزامی است.")

    data = _provider_data(shipment)
    manual = dict(data.get("manual") or {})
    prev_tracking = _strip_opt(manual.get("tracking_code") or shipment.tracking_code)
    prev_ref = _strip_opt(manual.get("provider_reference"))
    prev_courier_name = _strip_opt(manual.get("courier_name"))
    prev_courier_phone = _strip_opt(manual.get("courier_phone"))
    prev_mission = _strip_opt(manual.get("mission_reference"))
    prev_note = _strip_opt(manual.get("note"))

    if prev_tracking and tracking and prev_tracking != tracking:
        raise ShippingMethodConflictError("کد رهگیری قبلاً با مقدار دیگری ثبت شده است.")
    if prev_ref and new_ref and prev_ref != new_ref:
        raise ShippingMethodConflictError("شناسه مرجع قبلاً با مقدار دیگری ثبت شده است.")

    next_courier_name = _strip_opt(courier_name) if courier_name is not None else prev_courier_name
    next_courier_phone = _strip_opt(courier_phone) if courier_phone is not None else prev_courier_phone
    next_mission = _strip_opt(mission_reference) if mission_reference is not None else prev_mission
    next_note = _strip_opt(note) if note is not None else prev_note
    next_tracking = tracking or prev_tracking
    next_ref = new_ref or prev_ref

    unchanged = (
        shipment.status == ShipmentStatus.BOOKED.value
        and next_tracking == prev_tracking
        and next_ref == prev_ref
        and next_courier_name == prev_courier_name
        and next_courier_phone == prev_courier_phone
        and next_mission == prev_mission
        and next_note == prev_note
    )
    if unchanged:
        return shipment

    if next_courier_name:
        manual["courier_name"] = next_courier_name
    if next_courier_phone:
        manual["courier_phone"] = next_courier_phone
    if next_mission:
        manual["mission_reference"] = next_mission
    if next_note:
        manual["note"] = next_note
    if next_tracking:
        manual["tracking_code"] = next_tracking
        shipment.tracking_code = next_tracking
    if next_ref:
        manual["provider_reference"] = next_ref
    if "registered_at" not in manual:
        manual["registered_at"] = datetime.now(UTC).isoformat()
    if actor_user_id is not None:
        manual["registered_by_user_id"] = actor_user_id

    data["manual"] = manual
    shipment.provider_data = data
    became_booked = shipment.status == ShipmentStatus.AWAITING_PACKAGING.value
    if became_booked:
        shipment.status = ShipmentStatus.BOOKED.value

    await db.flush()
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
        if order.status == OrderStatus.SHIPPED.value:
            return shipment
        raise ShipmentStateError(
            "وضعیت سفارش با مرسوله برای تحویل به حامل هم‌خوان نیست.",
            error_code="SHIPMENT_STATE_INVALID",
        )

    if order.status != OrderStatus.PROCESSING.value:
        raise ShipmentStateError(
            "تحویل به حامل فقط برای سفارش در وضعیت «در حال پردازش» مجاز است.",
            error_code="SHIPMENT_STATE_INVALID",
        )
    if shipment.status != ShipmentStatus.BOOKED.value:
        raise ShipmentStateError(
            "تحویل به حامل فقط پس از ثبت اطلاعات ارسال (وضعیت ثبت‌شده) مجاز است.",
            error_code="SHIPMENT_STATE_INVALID",
        )

    if provider in {"tipax", "chapar"}:
        manual = _manual_meta(shipment)
        tracking = _strip_opt(shipment.tracking_code or manual.get("tracking_code"))
        reference = _strip_opt(manual.get("provider_reference"))
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

    manual = _manual_meta(shipment)
    tracking = _strip_opt(shipment.tracking_code or manual.get("tracking_code"))
    postal_for_order = tracking if tracking else None

    await transition_order_status(
        db,
        order,
        OrderStatus.SHIPPED.value,
        actor="admin",
        postal_tracking_code=postal_for_order,
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
        if order.status == OrderStatus.DELIVERED.value:
            return shipment
        raise ShipmentStateError(
            "وضعیت سفارش با مرسوله برای تحویل هم‌خوان نیست.",
            error_code="SHIPMENT_STATE_INVALID",
        )

    if order.status != OrderStatus.SHIPPED.value:
        raise ShipmentStateError(
            "ثبت تحویل فقط برای سفارش در وضعیت «ارسال‌شده» مجاز است.",
            error_code="SHIPMENT_STATE_INVALID",
        )
    if shipment.status not in _POST_HANDOFF_DELIVERY_STATUSES:
        raise ShipmentStateError(
            "ثبت تحویل فقط پس از تحویل به حامل مجاز است.",
            error_code="SHIPMENT_STATE_INVALID",
        )

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

    await transition_order_status(
        db,
        order,
        OrderStatus.DELIVERED.value,
        actor="admin",
        event_description="سفارش تحویل داده شد",
        via_shipment_lifecycle=True,
    )
    return shipment
