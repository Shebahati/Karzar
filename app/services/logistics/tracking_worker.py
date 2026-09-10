"""DB-backed Postex tracking poller for non-terminal shipments."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models.commerce import Order
from app.db.models.logistics import Shipment
from app.services.logistics.models import TERMINAL_SHIPMENT_STATUSES, ShipmentStatus
from app.services.logistics.service import (
    apply_tracking_to_order,
    as_utc,
    get_provider,
    ingest_tracking_events,
    postex_enabled,
)

logger = get_logger(__name__)

_ACTIVE = tuple(
    status.value
    for status in ShipmentStatus
    if status not in TERMINAL_SHIPMENT_STATUSES
    and status
    not in {
        ShipmentStatus.PENDING_BOOKING,
        ShipmentStatus.BOOKING,
        ShipmentStatus.ERROR,
        ShipmentStatus.CREATION_UNCERTAIN,
    }
)


async def process_tracking_sync(db: AsyncSession) -> int:
    if not postex_enabled():
        return 0
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.POSTEX_TRACKING_SYNC_INTERVAL_SECONDS)
    stmt = (
        select(Shipment)
        .where(
            Shipment.status.in_(_ACTIVE),
            or_(
                Shipment.provider_parcel_no.is_not(None),
                Shipment.tracking_code.is_not(None),
            ),
        )
        .order_by(Shipment.last_tracking_sync_at.nulls_first(), Shipment.id)
        .limit(10)
        .with_for_update(skip_locked=True)
    )
    shipments = list((await db.execute(stmt)).scalars().all())
    processed = 0
    provider = get_provider()
    for shipment in shipments:
        if (
            shipment.last_tracking_sync_at is not None
            and as_utc(shipment.last_tracking_sync_at) > cutoff
        ):
            continue
        try:
            if shipment.provider_parcel_no:
                events = await provider.tracking_events(str(shipment.provider_parcel_no))
            elif shipment.tracking_code and shipment.carrier_code:
                events = await provider.tracking_events_by_barcode(
                    shipment.carrier_code, shipment.tracking_code
                )
            else:
                continue
            await ingest_tracking_events(db, shipment, events)
            order = (
                (
                    await db.execute(
                        select(Order)
                        .where(Order.id == shipment.order_id)
                        .options(selectinload(Order.shipments), selectinload(Order.items))
                    )
                )
                .scalars()
                .first()
            )
            if order is not None:
                await apply_tracking_to_order(db, order)
            processed += 1
        except Exception:
            logger.exception(
                "postex tracking sync failed shipment_id=%s order_id=%s",
                shipment.id,
                shipment.order_id,
            )
            shipment.last_tracking_sync_at = datetime.now(UTC)
            await db.flush()
    return processed
