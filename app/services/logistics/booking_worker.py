"""DB-backed Postex parcel booking worker. Never blindly retries ambiguous creates."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models.commerce import Order
from app.db.models.logistics import Shipment
from app.services.logistics.exceptions import (
    ProviderConflictError,
    ProviderError,
    ProviderTimeoutError,
    ProviderValidationError,
)
from app.services.logistics.models import BOOKING_CREATE_FORBIDDEN_STATUSES, ShipmentStatus
from app.services.logistics.service import (
    build_parcel_create_request,
    get_provider,
    postex_enabled,
)

logger = get_logger(__name__)

_CLAIMABLE = (
    ShipmentStatus.PENDING_BOOKING.value,
    ShipmentStatus.CREATION_UNCERTAIN.value,
    ShipmentStatus.ERROR.value,
    ShipmentStatus.BOOKING.value,
)

_RECONCILE_FIRST = frozenset(
    {
        ShipmentStatus.CREATION_UNCERTAIN.value,
        ShipmentStatus.BOOKING.value,
    }
)


async def process_shipment_bookings(db: AsyncSession) -> int:
    if not postex_enabled():
        return 0
    now = datetime.now(UTC)
    stmt = (
        select(Shipment)
        .where(
            Shipment.status.in_(_CLAIMABLE),
            or_(
                Shipment.booking_next_attempt_at.is_(None),
                Shipment.booking_next_attempt_at <= now,
            ),
        )
        .order_by(Shipment.id)
        .limit(10)
        .with_for_update(skip_locked=True)
    )
    shipments = list((await db.execute(stmt)).scalars().all())
    processed = 0
    for shipment in shipments:
        await _book_one(db, shipment)
        processed += 1
    return processed


async def _lock_shipment(db: AsyncSession, shipment_id: int) -> Shipment | None:
    return (
        (
            await db.execute(
                select(Shipment).where(Shipment.id == shipment_id).with_for_update()
            )
        )
        .scalars()
        .first()
    )


def _already_created(shipment: Shipment) -> bool:
    if (shipment.provider_parcel_no or "").strip():
        return True
    return shipment.status in {status.value for status in BOOKING_CREATE_FORBIDDEN_STATUSES}


async def _book_one(db: AsyncSession, shipment: Shipment) -> None:
    """Create at most one Postex parcel per shipment. Safe for admin and worker."""
    locked = await _lock_shipment(db, shipment.id)
    if locked is None:
        return
    shipment = locked

    if _already_created(shipment):
        if (shipment.provider_parcel_no or "").strip() and shipment.status in {
            ShipmentStatus.PENDING_BOOKING.value,
            ShipmentStatus.BOOKING.value,
            ShipmentStatus.CREATION_UNCERTAIN.value,
            ShipmentStatus.ERROR.value,
        }:
            shipment.status = ShipmentStatus.BOOKED.value
            shipment.last_error_code = None
            shipment.last_error_message = None
            shipment.booking_next_attempt_at = None
            await db.flush()
        return

    order = (
        (
            await db.execute(
                select(Order)
                .where(Order.id == shipment.order_id)
                .options(selectinload(Order.items))
            )
        )
        .scalars()
        .first()
    )
    if order is None:
        shipment.status = ShipmentStatus.ERROR.value
        shipment.last_error_code = "ORDER_MISSING"
        await db.flush()
        return

    original_status = shipment.status
    provider = get_provider()

    if original_status in _RECONCILE_FIRST:
        if await _reconcile_or_wait(db, shipment, provider):
            return

    try:
        shipment.booking_attempts += 1
        await db.flush()
        booking = await provider.create_parcel(build_parcel_create_request(order, shipment))
    except ProviderTimeoutError as exc:
        await _mark_uncertain(shipment, str(exc))
        logger.warning(
            "postex create ambiguous shipment_id=%s order_id=%s — marked creation_uncertain",
            shipment.id,
            order.id,
        )
        await db.flush()
        return
    except ProviderConflictError as exc:
        lookup = await _lookup_safe(provider, shipment.public_id)
        if lookup is not None and lookup.found and lookup.booking:
            _apply_booking(shipment, lookup.booking)
            await db.flush()
            return
        await _mark_uncertain(shipment, str(exc))
        await db.flush()
        return
    except ProviderValidationError as exc:
        shipment.status = ShipmentStatus.ERROR.value
        shipment.last_error_code = "PROVIDER_VALIDATION"
        shipment.last_error_message = str(exc)[:500]
        shipment.booking_next_attempt_at = datetime.now(UTC) + timedelta(minutes=15)
        logger.warning(
            "postex create rejected shipment_id=%s http_status=%s",
            shipment.id,
            getattr(exc, "http_status", None),
        )
        await db.flush()
        return
    except ProviderError as exc:
        if getattr(exc, "ambiguous_write", False):
            await _mark_uncertain(shipment, str(exc))
            await db.flush()
            return
        shipment.status = ShipmentStatus.ERROR.value
        shipment.last_error_code = "PROVIDER_ERROR"
        shipment.last_error_message = str(exc)[:500]
        shipment.booking_next_attempt_at = datetime.now(UTC) + timedelta(
            seconds=settings.POSTEX_BOOKING_INTERVAL_SECONDS * 3
        )
        logger.exception("postex create failed shipment_id=%s", shipment.id)
        await db.flush()
        return
    except Exception:
        shipment.status = ShipmentStatus.ERROR.value
        shipment.last_error_code = "PROVIDER_ERROR"
        shipment.last_error_message = "unexpected booking failure"
        shipment.booking_next_attempt_at = datetime.now(UTC) + timedelta(
            seconds=settings.POSTEX_BOOKING_INTERVAL_SECONDS * 3
        )
        logger.exception("postex create failed shipment_id=%s", shipment.id)
        await db.flush()
        return

    _apply_booking(shipment, booking)
    await db.flush()
    logger.info(
        "postex booked shipment_id=%s order_id=%s parcel=%s tracking=%s",
        shipment.id,
        order.id,
        shipment.provider_parcel_no,
        shipment.tracking_code,
    )


async def _lookup_safe(provider, custom_order_no: str):
    try:
        return await provider.lookup_by_custom_order_no(custom_order_no)
    except Exception:
        return None


async def _reconcile_or_wait(db: AsyncSession, shipment: Shipment, provider) -> bool:
    """Return True if the caller must not POST create."""
    try:
        lookup = await provider.lookup_by_custom_order_no(shipment.public_id)
    except Exception as exc:
        await _mark_uncertain(shipment, str(exc))
        logger.warning(
            "postex reconcile lookup failed shipment_id=%s — staying creation_uncertain",
            shipment.id,
        )
        await db.flush()
        return True
    if lookup.found and lookup.booking:
        _apply_booking(shipment, lookup.booking)
        await db.flush()
        logger.info(
            "postex reconciled shipment_id=%s parcel=%s",
            shipment.id,
            shipment.provider_parcel_no,
        )
        return True
    data = dict(shipment.provider_data or {})
    empty_lookups = int(data.get("uncertain_empty_lookups") or 0) + 1
    data["uncertain_empty_lookups"] = empty_lookups
    shipment.provider_data = data
    # Official spec has no idempotency key. A single 404 after timeout is not
    # proof the create never reached Postex — require two empty lookups.
    if empty_lookups < 2:
        await _mark_uncertain(shipment, "awaiting second empty custom-order lookup")
        await db.flush()
        return True
    return False


async def _mark_uncertain(shipment: Shipment, message: str) -> None:
    shipment.status = ShipmentStatus.CREATION_UNCERTAIN.value
    shipment.last_error_code = "CREATION_UNCERTAIN"
    shipment.last_error_message = message[:500]
    shipment.booking_next_attempt_at = datetime.now(UTC) + timedelta(seconds=60)


def _apply_booking(shipment: Shipment, booking) -> None:
    shipment.provider_parcel_no = booking.provider_parcel_no or shipment.provider_parcel_no
    shipment.tracking_code = booking.tracking_code or shipment.tracking_code
    if booking.carrier_code:
        shipment.carrier_code = booking.carrier_code
    if booking.service_code:
        shipment.service_code = booking.service_code
    shipment.status = ShipmentStatus.BOOKED.value
    shipment.last_error_code = None
    shipment.last_error_message = None
    shipment.booking_next_attempt_at = None
    data = dict(shipment.provider_data or {})
    data["create_response"] = booking.raw
    shipment.provider_data = data
