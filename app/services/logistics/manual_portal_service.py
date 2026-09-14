"""Manual Postex portal fulfillment — no external Postex HTTP."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.commerce import Order, OrderMode, OrderStatus, PaymentStatus
from app.db.models.logistics import Shipment
from app.services.logistics.exceptions import ShipmentStateError
from app.services.logistics.fulfillment_mode import (
    is_manual_portal_shipment,
    registration_source,
)
from app.services.logistics.models import ShipmentStatus
from app.services.logistics.shipping_payment import ShippingPaymentMode
from app.services.order_service import transition_order_status

_REGISTRATION_SOURCE = "manual_portal"

_MANUAL_TERMINAL = frozenset(
    {
        ShipmentStatus.CANCELLED.value,
        ShipmentStatus.DELIVERED.value,
        ShipmentStatus.RETURNED.value,
    }
)


def normalize_tracking_code(raw: str) -> str:
    code = (raw or "").strip()
    if len(code) < 10:
        raise ShipmentStateError(
            "کد رهگیری باید حداقل ۱۰ کاراکتر باشد.",
            error_code="VALIDATION_FAILED",
        )
    if len(code) > 64:
        raise ShipmentStateError(
            "کد رهگیری بیش از حد طولانی است.",
            error_code="VALIDATION_FAILED",
        )
    return code


def _registration_fingerprint(
    *,
    tracking_code: str,
    provider_parcel_no: str | None,
    carrier_code: str | None,
    service_code: str | None,
    internal_note: str | None,
) -> str:
    payload = {
        "tracking_code": tracking_code,
        "provider_parcel_no": (provider_parcel_no or "").strip() or None,
        "carrier_code": (carrier_code or "").strip() or None,
        "service_code": (service_code or "").strip() or None,
        "internal_note": (internal_note or "").strip() or None,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _stored_registration(shipment: Shipment) -> dict[str, Any]:
    data = shipment.provider_data or {}
    reg = data.get("manual_registration")
    return dict(reg) if isinstance(reg, dict) else {}


def _require_manual_receiver_shipment(order: Order, shipment: Shipment) -> None:
    if order.mode != OrderMode.PURCHASE:
        raise ShipmentStateError(
            "ثبت دستی فقط برای سفارش خرید است.",
            error_code="SHIPMENT_STATE_INVALID",
        )
    if order.payment_status != PaymentStatus.PAID.value:
        raise ShipmentStateError(
            "سفارش باید پرداخت شده باشد.",
            error_code="SHIPMENT_STATE_INVALID",
        )
    if order.status == OrderStatus.CANCELLED.value:
        raise ShipmentStateError(
            "سفارش لغو شده است.",
            error_code="SHIPMENT_STATE_INVALID",
        )
    if shipment.shipping_payment_mode != ShippingPaymentMode.RECEIVER_DUE.value:
        raise ShipmentStateError(
            "ثبت دستی فقط برای پس‌کرایه است.",
            error_code="SHIPMENT_STATE_INVALID",
        )
    if not is_manual_portal_shipment(shipment):
        raise ShipmentStateError(
            "این مرسوله در حالت ثبت دستی پستکس نیست.",
            error_code="SHIPMENT_STATE_INVALID",
        )


async def register_manual_portal_shipment(
    db: AsyncSession,
    *,
    order: Order,
    shipment: Shipment,
    tracking_code: str,
    provider_parcel_no: str | None = None,
    carrier_code: str | None = None,
    service_code: str | None = None,
    internal_note: str | None = None,
    actor_user_id: int | None = None,
) -> Shipment:
    from app.services.logistics.service import _append_event

    _require_manual_receiver_shipment(order, shipment)
    tracking = normalize_tracking_code(tracking_code)
    parcel = (provider_parcel_no or "").strip() or None
    carrier = (carrier_code or "").strip() or None
    service = (service_code or "").strip() or None
    note = (internal_note or "").strip() or None
    fingerprint = _registration_fingerprint(
        tracking_code=tracking,
        provider_parcel_no=parcel,
        carrier_code=carrier,
        service_code=service,
        internal_note=note,
    )

    existing = _stored_registration(shipment)
    if registration_source(shipment) == _REGISTRATION_SOURCE:
        if existing.get("fingerprint") == fingerprint:
            return shipment
        raise ShipmentStateError(
            "مرسوله قبلاً با اطلاعات متفاوت ثبت شده است.",
            error_code="SHIPMENT_STATE_INVALID",
        )

    if shipment.status != ShipmentStatus.AWAITING_PACKAGING.value:
        raise ShipmentStateError(
            "ثبت دستی فقط برای مرسوله در انتظار بسته‌بندی مجاز است.",
            error_code="SHIPMENT_STATE_INVALID",
        )
    if (shipment.tracking_code or "").strip() or (shipment.provider_parcel_no or "").strip():
        raise ShipmentStateError(
            "مرسوله قبلاً ثبت شده است.",
            error_code="SHIPMENT_STATE_INVALID",
        )

    data = dict(shipment.provider_data or {})
    data["registration_source"] = _REGISTRATION_SOURCE
    data["manual_registration"] = {
        "fingerprint": fingerprint,
        "tracking_code": tracking,
        "provider_parcel_no": parcel,
        "carrier_code": carrier,
        "service_code": service,
        "internal_note": note,
        "registered_at": datetime.now(UTC).isoformat(),
        "registered_by_user_id": actor_user_id,
    }
    shipment.provider_data = data
    shipment.tracking_code = tracking
    shipment.provider_parcel_no = parcel
    shipment.carrier_code = carrier
    shipment.service_code = service
    shipment.status = ShipmentStatus.BOOKED.value
    order.postal_tracking_code = tracking

    await _append_event(
        db,
        shipment,
        status=ShipmentStatus.BOOKED.value,
        description="ثبت دستی اطلاعات مرسوله در پنل پستکس",
        provider_status=None,
        provider_code="manual_portal",
        occurred_at=datetime.now(UTC),
        payload={
            "registration_source": _REGISTRATION_SOURCE,
            "tracking_code": tracking,
            "provider_parcel_no": parcel,
            "carrier_code": carrier,
            "service_code": service,
            "has_internal_note": bool(note),
        },
    )
    await db.flush()
    return shipment


async def confirm_manual_physical_handoff(
    db: AsyncSession,
    *,
    order: Order,
    shipment: Shipment,
    actor_user_id: int | None = None,
) -> tuple[Order, Shipment]:
    from app.services.logistics.service import _append_event

    _require_manual_receiver_shipment(order, shipment)
    if registration_source(shipment) != _REGISTRATION_SOURCE:
        raise ShipmentStateError(
            "ابتدا اطلاعات مرسوله را در پنل پستکس ثبت کنید.",
            error_code="SHIPMENT_STATE_INVALID",
        )
    tracking = (shipment.tracking_code or order.postal_tracking_code or "").strip()
    if len(tracking) < 10:
        raise ShipmentStateError(
            "کد رهگیری معتبر یافت نشد.",
            error_code="SHIPMENT_STATE_INVALID",
        )

    if (
        shipment.status == ShipmentStatus.PICKED_UP.value
        and order.status == OrderStatus.SHIPPED.value
    ):
        return order, shipment

    if shipment.status == ShipmentStatus.BOOKED.value and order.status == OrderStatus.PROCESSING.value:
        await transition_order_status(
            db,
            order,
            OrderStatus.SHIPPED.value,
            actor="admin",
            postal_tracking_code=tracking,
            event_description="تحویل فیزیکی مرسوله به پست (ثبت دستی)",
            allow_manual_portal_fulfillment=True,
        )
        shipment.status = ShipmentStatus.PICKED_UP.value
        if shipment.shipped_at is None:
            shipment.shipped_at = datetime.now(UTC)
        await _append_event(
            db,
            shipment,
            status=ShipmentStatus.PICKED_UP.value,
            description="تحویل فیزیکی به پست تأیید شد",
            provider_status=None,
            provider_code="manual_portal",
            occurred_at=datetime.now(UTC),
            payload={"registered_by_user_id": actor_user_id},
        )
        await db.flush()
        return order, shipment

    raise ShipmentStateError(
        "وضعیت سفارش/مرسوله برای تحویل فیزیکی مجاز نیست.",
        error_code="SHIPMENT_STATE_INVALID",
    )


async def confirm_manual_delivery(
    db: AsyncSession,
    *,
    order: Order,
    shipment: Shipment,
    actor_user_id: int | None = None,
) -> tuple[Order, Shipment]:
    from app.services.logistics.service import _append_event

    _require_manual_receiver_shipment(order, shipment)
    if registration_source(shipment) != _REGISTRATION_SOURCE:
        raise ShipmentStateError(
            "این مرسوله از مسیر ثبت دستی پستکس نیست.",
            error_code="SHIPMENT_STATE_INVALID",
        )

    if (
        shipment.status == ShipmentStatus.DELIVERED.value
        and order.status == OrderStatus.DELIVERED.value
    ):
        return order, shipment

    if shipment.status != ShipmentStatus.PICKED_UP.value:
        raise ShipmentStateError(
            "تحویل مشتری فقط پس از تحویل فیزیکی به پست مجاز است.",
            error_code="SHIPMENT_STATE_INVALID",
        )
    if order.status != OrderStatus.SHIPPED.value:
        raise ShipmentStateError(
            "سفارش باید در وضعیت ارسال‌شده باشد.",
            error_code="SHIPMENT_STATE_INVALID",
        )

    shipment.status = ShipmentStatus.DELIVERED.value
    if shipment.delivered_at is None:
        shipment.delivered_at = datetime.now(UTC)
    await _append_event(
        db,
        shipment,
        status=ShipmentStatus.DELIVERED.value,
        description="تحویل به مشتری تأیید شد (ثبت دستی)",
        provider_status=None,
        provider_code="manual_portal",
        occurred_at=datetime.now(UTC),
        payload={"confirmed_by_user_id": actor_user_id},
    )
    await transition_order_status(
        db,
        order,
        OrderStatus.DELIVERED.value,
        actor="admin",
        event_description="تحویل سفارش به مشتری (ثبت دستی)",
        allow_manual_portal_fulfillment=True,
    )
    await db.flush()
    return order, shipment


async def correct_manual_portal_registration(
    db: AsyncSession,
    *,
    order: Order,
    shipment: Shipment,
    tracking_code: str,
    update_fields: frozenset[str],
    provider_parcel_no: str | None = None,
    carrier_code: str | None = None,
    service_code: str | None = None,
    internal_note: str | None = None,
    actor_user_id: int | None = None,
) -> Shipment:
    from app.services.logistics.service import _append_event

    _require_manual_receiver_shipment(order, shipment)
    if registration_source(shipment) != _REGISTRATION_SOURCE:
        raise ShipmentStateError(
            "ابتدا ثبت اولیه مرسوله انجام شود.",
            error_code="SHIPMENT_STATE_INVALID",
        )
    if shipment.status != ShipmentStatus.BOOKED.value:
        raise ShipmentStateError(
            "اصلاح فقط قبل از تحویل فیزیکی به پست مجاز است.",
            error_code="SHIPMENT_STATE_INVALID",
        )
    if shipment.shipped_at is not None:
        raise ShipmentStateError(
            "پس از تحویل فیزیکی اصلاح مجاز نیست.",
            error_code="SHIPMENT_STATE_INVALID",
        )

    existing = _stored_registration(shipment)
    tracking = normalize_tracking_code(tracking_code)

    def _prior_str(key: str, fallback: str | None) -> str | None:
        raw = existing.get(key)
        if raw is not None:
            text = str(raw).strip()
            return text or None
        return (fallback or "").strip() or None

    if "provider_parcel_no" in update_fields:
        parcel = (provider_parcel_no or "").strip() or None
    else:
        parcel = _prior_str("provider_parcel_no", shipment.provider_parcel_no)

    if "carrier_code" in update_fields:
        carrier = (carrier_code or "").strip() or None
    else:
        carrier = _prior_str("carrier_code", shipment.carrier_code)

    if "service_code" in update_fields:
        service = (service_code or "").strip() or None
    else:
        service = _prior_str("service_code", shipment.service_code)

    if "internal_note" in update_fields:
        note = (internal_note or "").strip() or None
    else:
        note = _prior_str("internal_note", None)

    fingerprint = _registration_fingerprint(
        tracking_code=tracking,
        provider_parcel_no=parcel,
        carrier_code=carrier,
        service_code=service,
        internal_note=note,
    )
    if existing.get("fingerprint") == fingerprint:
        return shipment

    audit_changes: dict[str, object] = {}
    prior_tracking = _prior_str("tracking_code", shipment.tracking_code)
    if tracking != prior_tracking:
        audit_changes["tracking_code"] = {"before": prior_tracking, "after": tracking}
    for key, new_val, prior in (
        ("provider_parcel_no", parcel, _prior_str("provider_parcel_no", shipment.provider_parcel_no)),
        ("carrier_code", carrier, _prior_str("carrier_code", shipment.carrier_code)),
        ("service_code", service, _prior_str("service_code", shipment.service_code)),
    ):
        if key in update_fields and new_val != prior:
            audit_changes[key] = {"before": prior, "after": new_val}
    if "internal_note" in update_fields and note != _prior_str("internal_note", None):
        audit_changes["internal_note"] = {"changed": True}

    data = dict(shipment.provider_data or {})
    data["manual_registration"] = {
        "fingerprint": fingerprint,
        "tracking_code": tracking,
        "provider_parcel_no": parcel,
        "carrier_code": carrier,
        "service_code": service,
        "internal_note": note,
        "registered_at": existing.get("registered_at") or datetime.now(UTC).isoformat(),
        "corrected_at": datetime.now(UTC).isoformat(),
        "registered_by_user_id": existing.get("registered_by_user_id"),
        "corrected_by_user_id": actor_user_id,
    }
    shipment.provider_data = data
    shipment.tracking_code = tracking
    shipment.provider_parcel_no = parcel
    shipment.carrier_code = carrier
    shipment.service_code = service
    order.postal_tracking_code = tracking

    await _append_event(
        db,
        shipment,
        status=ShipmentStatus.BOOKED.value,
        description="اصلاح اطلاعات ثبت دستی مرسوله پستکس",
        provider_status=None,
        provider_code="manual_portal",
        occurred_at=datetime.now(UTC),
        payload={
            "corrected_by_user_id": actor_user_id,
            "changes": audit_changes,
        },
    )
    await db.flush()
    return shipment


def assert_api_fulfillment_path_allowed(shipment: Shipment) -> None:
    """Block packed-quote/booking API steps for manual-portal shipments."""
    from app.services.logistics.fulfillment_mode import (
        assert_provider_path_allowed_for_fulfillment_snapshot,
    )

    assert_provider_path_allowed_for_fulfillment_snapshot(shipment)
