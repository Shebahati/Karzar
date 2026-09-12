"""DB-backed Postex parcel booking worker. Crash-safe: commit before create HTTP."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models.commerce import Order
from app.db.models.logistics import Shipment
from app.services.logistics.exceptions import (
    LogisticsError,
    ProviderConflictError,
    ProviderError,
    ProviderTimeoutError,
    ProviderValidationError,
    ShipmentStateError,
    ShippingDataIncompleteError,
)
from app.services.logistics.models import (
    BOOKING_CREATE_FORBIDDEN_STATUSES,
    ParcelBooking,
    ShipmentStatus,
)
from app.services.logistics.service import (
    build_parcel_create_request,
    get_provider,
    postex_enabled,
)
from app.services.logistics.shipping_payment import postex_booking_enabled

logger = get_logger(__name__)

_CLAIMABLE = (
    ShipmentStatus.PENDING_BOOKING.value,
    ShipmentStatus.CREATION_UNCERTAIN.value,
    ShipmentStatus.ERROR.value,
    ShipmentStatus.BOOKING.value,
)

_RECONCILE_BEFORE_CREATE = frozenset(
    {
        ShipmentStatus.CREATION_UNCERTAIN.value,
        ShipmentStatus.BOOKING.value,
    }
)

_CLAIMABLE_WITH_PARCEL = frozenset(
    {
        ShipmentStatus.PENDING_BOOKING.value,
        ShipmentStatus.BOOKING.value,
        ShipmentStatus.CREATION_UNCERTAIN.value,
        ShipmentStatus.ERROR.value,
    }
)

_LOCAL_CANCEL_SAFE_STATUSES = frozenset(
    {
        ShipmentStatus.AWAITING_PACKAGING.value,
        ShipmentStatus.READY_TO_BOOK.value,
        ShipmentStatus.FREIGHT_REQUIRED.value,
        ShipmentStatus.PENDING_BOOKING.value,
    }
)


def create_attempt_started(shipment: Shipment) -> bool:
    """True when a Postex create may already have been sent or durably started."""
    if (shipment.provider_parcel_no or "").strip():
        return True
    if shipment.status in {
        ShipmentStatus.BOOKING.value,
        ShipmentStatus.CREATION_UNCERTAIN.value,
    }:
        return True
    data = shipment.provider_data or {}
    if data.get("create_attempted"):
        return True
    return int(shipment.booking_attempts or 0) > 0


def never_attempted_create(shipment: Shipment) -> bool:
    """Local cancel is only safe when Karzar can prove no provider create was attempted."""
    if (shipment.provider_parcel_no or "").strip():
        return False
    if int(shipment.booking_attempts or 0) > 0:
        return False
    if (shipment.provider_data or {}).get("create_attempted"):
        return False
    if shipment.status not in _LOCAL_CANCEL_SAFE_STATUSES:
        return False
    return True


def _create_lease_active(shipment: Shipment) -> bool:
    """Another worker may still be inside the Postex create HTTP window."""
    if shipment.status != ShipmentStatus.BOOKING.value:
        return False
    started_raw = (shipment.provider_data or {}).get("create_started_at")
    if not started_raw:
        return False
    try:
        started_at = datetime.fromisoformat(str(started_raw).replace("Z", "+00:00"))
    except ValueError:
        return False
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=UTC)
    ttl = timedelta(seconds=max(60.0, float(settings.POSTEX_TIMEOUT_SECONDS) * 3))
    return datetime.now(UTC) < started_at + ttl


def _must_lookup_before_create(shipment: Shipment) -> bool:
    if shipment.status in _RECONCILE_BEFORE_CREATE:
        return True
    if shipment.last_error_code == "PROVIDER_VALIDATION":
        return False
    return create_attempt_started(shipment)


def _patch_provider_data(shipment: Shipment, **updates: Any) -> dict[str, Any]:
    data = dict(shipment.provider_data or {})
    data.update(updates)
    shipment.provider_data = data
    return data


async def process_shipment_bookings(db: AsyncSession) -> int:
    if not postex_enabled():
        return 0
    # Write gate: no parcel create / cancel mutations without POSTEX_BOOKING_ENABLED.
    # awaiting_packaging is never claimable (_CLAIMABLE excludes it).
    if not postex_booking_enabled():
        return 0
    now = datetime.now(UTC)
    stmt = (
        select(Shipment.id)
        .where(
            Shipment.status.in_(_CLAIMABLE),
            # Never claim awaiting_packaging / freight_required even if malformed.
            Shipment.status.notin_(
                (
                    ShipmentStatus.AWAITING_PACKAGING.value,
                    ShipmentStatus.READY_TO_BOOK.value,
                    ShipmentStatus.FREIGHT_REQUIRED.value,
                )
            ),
            or_(
                Shipment.booking_next_attempt_at.is_(None),
                Shipment.booking_next_attempt_at <= now,
            ),
        )
        .order_by(Shipment.id)
        .limit(10)
    )
    ids = list((await db.execute(stmt)).scalars().all())
    processed = 0
    for shipment_id in ids:
        await book_shipment(db, shipment_id)
        processed += 1
    processed += await _reconcile_pending_cancellations(db)
    return processed


async def _reconcile_pending_cancellations(db: AsyncSession) -> int:
    """Lookup/cancel-request for pending cancels that never reached a final provider cancel."""
    stmt = (
        select(Shipment.id)
        .where(Shipment.status == ShipmentStatus.CANCELLATION_PENDING.value)
        .order_by(Shipment.id)
        .limit(10)
    )
    ids = list((await db.execute(stmt)).scalars().all())
    processed = 0
    for shipment_id in ids:
        shipment = await db.get(Shipment, shipment_id)
        if shipment is None:
            continue
        data = shipment.provider_data or {}
        if (
            (shipment.provider_parcel_no or "").strip()
            and data.get("cancellation_requested")
            and not data.get("cancellation_request_uncertain")
            and not data.get("cancellation_lookup_inconclusive")
        ):
            continue
        try:
            await request_shipment_cancellation(db, shipment_id, "reconciliation")
        except Exception:
            logger.exception("postex cancel reconcile failed shipment_id=%s", shipment_id)
            continue
        processed += 1
    return processed


async def _lock_shipment(db: AsyncSession, shipment_id: int) -> Shipment | None:
    return (
        (
            await db.execute(
                select(Shipment)
                .where(Shipment.id == shipment_id)
                .options(selectinload(Shipment.events))
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .first()
    )


def _already_created(shipment: Shipment) -> bool:
    if (shipment.provider_parcel_no or "").strip():
        return True
    return shipment.status in {status.value for status in BOOKING_CREATE_FORBIDDEN_STATUSES}


def _maybe_promote_booked(shipment: Shipment) -> None:
    if not (shipment.provider_parcel_no or "").strip():
        return
    if shipment.status == ShipmentStatus.CANCELLATION_PENDING.value:
        return
    if shipment.status in _CLAIMABLE_WITH_PARCEL:
        shipment.status = ShipmentStatus.BOOKED.value
        shipment.last_error_code = None
        shipment.last_error_message = None
        shipment.booking_next_attempt_at = None


async def book_shipment(db: AsyncSession, shipment_id: int) -> None:
    """Create at most one Postex parcel. Used by the worker and admin book."""
    request = await _commit_create_attempt(db, shipment_id)
    if request is None:
        return
    await _execute_create(db, shipment_id, request)


async def _book_one(db: AsyncSession, shipment: Shipment) -> None:
    """Compat wrapper: tests and older callers pass a loaded shipment."""
    await book_shipment(db, shipment.id)


async def _commit_create_attempt(db: AsyncSession, shipment_id: int) -> dict[str, Any] | None:
    """TX A: durable BOOKING (+ attempt metadata) before any Postex create HTTP.

    Returns the create body only after COMMIT. Never holds FOR UPDATE across the network.
    """
    shipment = await _lock_shipment(db, shipment_id)
    if shipment is None:
        return None

    if _already_created(shipment):
        _maybe_promote_booked(shipment)
        await db.commit()
        return None

    if shipment.status == ShipmentStatus.CANCELLATION_PENDING.value:
        await db.commit()
        return None

    if _must_lookup_before_create(shipment):
        public_id = shipment.public_id
        await db.commit()
        lookup = await _lookup_safe(get_provider(), public_id)
        shipment = await _lock_shipment(db, shipment_id)
        if shipment is None:
            return None
        if _already_created(shipment):
            _maybe_promote_booked(shipment)
            await db.commit()
            await _maybe_issue_pending_cancel(db, shipment_id)
            return None
        if lookup is not None and lookup.found and lookup.booking:
            _apply_booking(shipment, lookup.booking)
            await db.commit()
            await _maybe_issue_pending_cancel(db, shipment_id)
            return None
        if lookup is None:
            await _mark_uncertain(shipment, "reconcile lookup failed")
            await db.commit()
            return None
        if _create_lease_active(shipment):
            await db.commit()
            return None
        data = dict(shipment.provider_data or {})
        empty_lookups = int(data.get("uncertain_empty_lookups") or 0) + 1
        data["uncertain_empty_lookups"] = empty_lookups
        shipment.provider_data = data
        if empty_lookups < 2:
            await _mark_uncertain(shipment, "awaiting second empty custom-order lookup")
            await db.commit()
            return None
        # Two empty lookups: fall through and durably start another create.

    if not postex_booking_enabled():
        shipment.last_error_code = "SHIPPING_BOOKING_DISABLED"
        shipment.last_error_message = "ثبت مرسوله پستکس غیرفعال است."
        shipment.booking_next_attempt_at = None
        await db.commit()
        return None

    if shipment.status == ShipmentStatus.AWAITING_PACKAGING.value:
        await db.commit()
        return None

    if shipment.status == ShipmentStatus.READY_TO_BOOK.value:
        # Prepared receiver parcels require explicit admin /book — never auto-create.
        await db.commit()
        return None

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
        await db.commit()
        return None

    try:
        request = build_parcel_create_request(order, shipment)
    except ShippingDataIncompleteError as exc:
        # Fail closed before any HTTP create — incomplete pending_booking must not mutate Postex.
        shipment.status = ShipmentStatus.ERROR.value
        shipment.last_error_code = "SHIPPING_DATA_INCOMPLETE"
        shipment.last_error_message = str(exc)[:500]
        shipment.booking_next_attempt_at = None
        await db.commit()
        logger.warning(
            "postex create blocked incomplete shipment_id=%s missing=%s",
            shipment.id,
            getattr(exc, "products", None),
        )
        return None

    shipment.booking_attempts = int(shipment.booking_attempts or 0) + 1
    shipment.status = ShipmentStatus.BOOKING.value
    _patch_provider_data(
        shipment,
        create_attempted=True,
        create_started_at=datetime.now(UTC).isoformat(),
        uncertain_empty_lookups=0,
    )
    await db.commit()
    logger.info(
        "postex create attempt committed shipment_id=%s order_id=%s attempt=%s",
        shipment.id,
        order.id,
        shipment.booking_attempts,
    )
    return request


async def _execute_create(db: AsyncSession, shipment_id: int, request: dict[str, Any]) -> None:
    """HTTP create with no row lock, then TX B persist."""
    provider = get_provider()
    booking: ParcelBooking | None = None
    try:
        booking = await provider.create_parcel(request)
    except ProviderTimeoutError as exc:
        await _persist_create_outcome(db, shipment_id, uncertain=str(exc))
        logger.warning(
            "postex create ambiguous shipment_id=%s — marked creation_uncertain",
            shipment_id,
        )
        return
    except ProviderConflictError as exc:
        shipment = await db.get(Shipment, shipment_id)
        public_id = shipment.public_id if shipment is not None else ""
        lookup = await _lookup_safe(provider, public_id)
        if lookup is not None and lookup.found and lookup.booking:
            await _persist_create_outcome(db, shipment_id, booking=lookup.booking)
            return
        await _persist_create_outcome(db, shipment_id, uncertain=str(exc))
        return
    except ProviderValidationError as exc:
        await _persist_create_outcome(
            db,
            shipment_id,
            error_code="PROVIDER_VALIDATION",
            error_message=str(exc)[:500],
        )
        logger.warning(
            "postex create rejected shipment_id=%s http_status=%s",
            shipment_id,
            getattr(exc, "http_status", None),
        )
        return
    except ProviderError as exc:
        if getattr(exc, "ambiguous_write", False):
            await _persist_create_outcome(db, shipment_id, uncertain=str(exc))
            return
        # After a durable create attempt, fail closed: the write may have reached Postex.
        await _persist_create_outcome(db, shipment_id, uncertain=str(exc))
        logger.exception("postex create failed shipment_id=%s", shipment_id)
        return
    except Exception:
        await _persist_create_outcome(db, shipment_id, uncertain="unexpected booking failure")
        logger.exception("postex create failed shipment_id=%s", shipment_id)
        return

    await _persist_create_outcome(db, shipment_id, booking=booking)
    logger.info("postex booked shipment_id=%s parcel persisted", shipment_id)
    await _maybe_issue_pending_cancel(db, shipment_id)


async def _persist_create_outcome(
    db: AsyncSession,
    shipment_id: int,
    *,
    booking: ParcelBooking | None = None,
    uncertain: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    """TX B: persist create result. Does not hold a lock during provider HTTP."""
    shipment = await _lock_shipment(db, shipment_id)
    if shipment is None:
        return
    if booking is not None:
        _apply_booking(shipment, booking)
        await db.commit()
        return
    if error_code == "PROVIDER_VALIDATION":
        shipment.status = ShipmentStatus.ERROR.value
        shipment.last_error_code = error_code
        shipment.last_error_message = error_message
        shipment.booking_next_attempt_at = datetime.now(UTC) + timedelta(minutes=15)
        await db.commit()
        return
    await _mark_uncertain(shipment, uncertain or "creation uncertain")
    await db.commit()


async def _lookup_safe(provider: Any, custom_order_no: str):
    try:
        return await provider.lookup_by_custom_order_no(custom_order_no)
    except Exception:
        return None


async def _mark_uncertain(shipment: Shipment, message: str) -> None:
    shipment.status = ShipmentStatus.CREATION_UNCERTAIN.value
    shipment.last_error_code = "CREATION_UNCERTAIN"
    shipment.last_error_message = message[:500]
    shipment.booking_next_attempt_at = datetime.now(UTC) + timedelta(seconds=60)


def _apply_identifiers(shipment: Shipment, booking: ParcelBooking) -> None:
    shipment.provider_parcel_no = booking.provider_parcel_no or shipment.provider_parcel_no
    shipment.tracking_code = booking.tracking_code or shipment.tracking_code
    if booking.carrier_code:
        shipment.carrier_code = booking.carrier_code
    if booking.service_code:
        shipment.service_code = booking.service_code
    data = dict(shipment.provider_data or {})
    data["create_response"] = booking.raw
    shipment.provider_data = data


def _apply_booking(shipment: Shipment, booking: ParcelBooking) -> None:
    _apply_identifiers(shipment, booking)
    if shipment.status == ShipmentStatus.CANCELLATION_PENDING.value:
        return
    shipment.status = ShipmentStatus.BOOKED.value
    shipment.last_error_code = None
    shipment.last_error_message = None
    shipment.booking_next_attempt_at = None


async def request_shipment_cancellation(
    db: AsyncSession, shipment_id: int, reason: str
) -> Shipment:
    """Cancel without claiming provider-side success while a parcel may exist.

    Never holds SELECT FOR UPDATE across lookup or cancel-request HTTP.
    """
    shipment = await _lock_shipment(db, shipment_id)
    if shipment is None:
        raise ShipmentStateError("مرسوله یافت نشد.")
    if shipment.status in {
        ShipmentStatus.DELIVERED.value,
        ShipmentStatus.RETURNED.value,
        ShipmentStatus.CANCELLED.value,
    }:
        await db.commit()
        raise ShipmentStateError("این مرسوله قابل انصراف نیست.")

    data = shipment.provider_data or {}
    if (
        shipment.status == ShipmentStatus.CANCELLATION_PENDING.value
        and (shipment.provider_parcel_no or "").strip()
        and data.get("cancellation_requested")
        and not data.get("cancellation_request_uncertain")
        and not data.get("cancellation_lookup_inconclusive")
    ):
        await db.commit()
        return shipment

    if never_attempted_create(shipment):
        shipment.status = ShipmentStatus.CANCELLED.value
        shipment.cancelled_at = datetime.now(UTC)
        await db.commit()
        return shipment

    if not postex_booking_enabled():
        await db.commit()
        raise LogisticsError(
            "ثبت مرسوله پستکس غیرفعال است.",
            error_code="SHIPPING_BOOKING_DISABLED",
        )

    public_id = shipment.public_id
    parcel_no = (shipment.provider_parcel_no or "").strip() or None
    await db.commit()

    if not parcel_no:
        lookup = await _lookup_safe(get_provider(), public_id)
        shipment = await _lock_shipment(db, shipment_id)
        if shipment is None:
            raise ShipmentStateError("مرسوله یافت نشد.")
        if never_attempted_create(shipment):
            shipment.status = ShipmentStatus.CANCELLED.value
            shipment.cancelled_at = datetime.now(UTC)
            await db.commit()
            return shipment
        if lookup is not None and lookup.found and lookup.booking:
            _apply_identifiers(shipment, lookup.booking)
            parcel_no = (shipment.provider_parcel_no or "").strip() or None
            shipment.status = ShipmentStatus.CANCELLATION_PENDING.value
            shipment.cancellation_requested_at = datetime.now(UTC)
            _patch_provider_data(shipment, cancellation_lookup_inconclusive=False)
            await db.commit()
        elif lookup is None:
            shipment.status = ShipmentStatus.CANCELLATION_PENDING.value
            shipment.cancellation_requested_at = datetime.now(UTC)
            _patch_provider_data(shipment, cancellation_lookup_inconclusive=True)
            await db.commit()
            logger.warning(
                "postex cancel lookup inconclusive shipment_id=%s — cancellation_pending",
                shipment_id,
            )
            return shipment
        else:
            shipment.status = ShipmentStatus.CANCELLATION_PENDING.value
            shipment.cancellation_requested_at = datetime.now(UTC)
            _patch_provider_data(shipment, cancellation_lookup_empty=True)
            await db.commit()
            logger.warning(
                "postex cancel lookup empty after create attempt shipment_id=%s",
                shipment_id,
            )
            return shipment

    await _issue_cancel_request(db, shipment_id, reason=reason)
    shipment = await db.get(Shipment, shipment_id)
    if shipment is None:
        raise ShipmentStateError("مرسوله یافت نشد.")
    return shipment


async def _maybe_issue_pending_cancel(db: AsyncSession, shipment_id: int) -> None:
    shipment = await db.get(Shipment, shipment_id)
    if shipment is None:
        return
    if shipment.status != ShipmentStatus.CANCELLATION_PENDING.value:
        return
    if not (shipment.provider_parcel_no or "").strip():
        return
    await _issue_cancel_request(db, shipment_id)


async def _issue_cancel_request(
    db: AsyncSession, shipment_id: int, reason: str = "reconciliation"
) -> None:
    shipment = await _lock_shipment(db, shipment_id)
    if shipment is None:
        return
    if shipment.status in {
        ShipmentStatus.DELIVERED.value,
        ShipmentStatus.RETURNED.value,
        ShipmentStatus.CANCELLED.value,
    }:
        await db.commit()
        return
    parcel_no = (shipment.provider_parcel_no or "").strip()
    if not parcel_no:
        await db.commit()
        return
    data = shipment.provider_data or {}
    if data.get("cancellation_requested") and not data.get("cancellation_request_uncertain"):
        await db.commit()
        return
    await db.commit()
    try:
        await get_provider().cancel_parcel(parcel_no, reason)
    except ProviderError as exc:
        if getattr(exc, "http_status", None) in {400, 409, 422}:
            raise
        shipment = await _lock_shipment(db, shipment_id)
        if shipment is None:
            return
        shipment.status = ShipmentStatus.CANCELLATION_PENDING.value
        shipment.cancellation_requested_at = datetime.now(UTC)
        if getattr(exc, "ambiguous_write", False):
            _patch_provider_data(shipment, cancellation_request_uncertain=True)
        await db.commit()
        if getattr(exc, "ambiguous_write", False):
            return
        raise
    shipment = await _lock_shipment(db, shipment_id)
    if shipment is None:
        return
    shipment.status = ShipmentStatus.CANCELLATION_PENDING.value
    shipment.cancellation_requested_at = datetime.now(UTC)
    _patch_provider_data(
        shipment,
        cancellation_requested=True,
        cancellation_request_uncertain=False,
        cancellation_lookup_inconclusive=False,
    )
    await db.commit()
