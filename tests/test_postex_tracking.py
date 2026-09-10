"""Tracking ingest, terminal protection, and multi-shipment completion."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from app.db.models.commerce import Order, OrderMode, OrderStatus, PaymentStatus
from app.db.models.logistics import Shipment, ShipmentEvent
from app.services.logistics.models import ShipmentStatus, TrackingEvent
from app.services.logistics.service import apply_tracking_to_order, ingest_tracking_events
from app.services.logistics.status_mapper import map_provider_status
from sqlalchemy import select

from tests.conftest import TestingSessionLocal


def test_duplicate_tracking_event_is_append_only(override_database):
    async def body():
        async with TestingSessionLocal() as session:
            order = Order(
                tracking_code="KZ-TRK-1",
                mode=OrderMode.PURCHASE,
                status=OrderStatus.PROCESSING.value,
                payment_status=PaymentStatus.PAID.value,
                customer_full_name="علی تست",
                customer_phone="09123333333",
            )
            session.add(order)
            await session.flush()
            shipment = Shipment(
                public_id=str(uuid4()),
                order_id=order.id,
                provider="postex",
                status=ShipmentStatus.BOOKED.value,
                provider_parcel_no="1001",
                tracking_code="1234567890123",
            )
            session.add(shipment)
            await session.flush()
            event = TrackingEvent(
                provider_status="picked_up",
                provider_code="picked_up",
                occurred_at=datetime(2026, 9, 10, tzinfo=UTC),
                description="جمع‌آوری شد",
                location="تهران",
                payload={"event_code": "picked_up"},
            )
            await ingest_tracking_events(session, shipment, [event, event])
            await session.commit()
            rows = (
                (
                    await session.execute(
                        select(ShipmentEvent).where(ShipmentEvent.shipment_id == shipment.id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(rows) == 1
            assert shipment.status == ShipmentStatus.PICKED_UP.value

    asyncio.run(body())


def test_out_of_order_delivered_does_not_regress(override_database):
    async def body():
        async with TestingSessionLocal() as session:
            order = Order(
                tracking_code="KZ-TRK-2",
                mode=OrderMode.PURCHASE,
                status=OrderStatus.SHIPPED.value,
                payment_status=PaymentStatus.PAID.value,
                customer_full_name="علی تست",
                customer_phone="09123333333",
                postal_tracking_code="1234567890123",
            )
            session.add(order)
            await session.flush()
            shipment = Shipment(
                public_id=str(uuid4()),
                order_id=order.id,
                provider="postex",
                status=ShipmentStatus.DELIVERED.value,
                provider_parcel_no="1001",
                tracking_code="1234567890123",
            )
            session.add(shipment)
            await session.flush()
            later = TrackingEvent(
                provider_status="in_transit",
                provider_code="in_transit",
                occurred_at=datetime(2026, 9, 11, tzinfo=UTC),
                description="در مسیر",
                location=None,
                payload={},
            )
            await ingest_tracking_events(session, shipment, [later])
            await apply_tracking_to_order(session, order)
            await session.commit()
            assert shipment.status == ShipmentStatus.DELIVERED.value
            # Shipment stays delivered; completing remaining required shipments may
            # advance SHIPPED → DELIVERED, but must never regress to in_transit.
            assert order.status == OrderStatus.DELIVERED.value
            await ingest_tracking_events(session, shipment, [later])
            await apply_tracking_to_order(session, order)
            assert shipment.status == ShipmentStatus.DELIVERED.value
            assert order.status == OrderStatus.DELIVERED.value

    asyncio.run(body())


def test_unknown_provider_status_never_delivered(override_database):
    mapped = map_provider_status(event_code="FUTURE_XYZ", event_name="وضعیت ناشناخته")
    assert mapped != ShipmentStatus.DELIVERED

    async def body():
        async with TestingSessionLocal() as session:
            order = Order(
                tracking_code="KZ-TRK-3",
                mode=OrderMode.PURCHASE,
                status=OrderStatus.PROCESSING.value,
                payment_status=PaymentStatus.PAID.value,
                customer_full_name="علی تست",
                customer_phone="09123333333",
            )
            session.add(order)
            await session.flush()
            shipment = Shipment(
                public_id=str(uuid4()),
                order_id=order.id,
                provider="postex",
                status=ShipmentStatus.BOOKED.value,
                provider_parcel_no="1001",
                tracking_code="1234567890123",
            )
            session.add(shipment)
            await session.flush()
            await ingest_tracking_events(
                session,
                shipment,
                [
                    TrackingEvent(
                        provider_status="وضعیت ناشناخته",
                        provider_code="FUTURE_XYZ",
                        occurred_at=datetime.now(UTC),
                        description="unknown",
                        location=None,
                        payload={"event_code": "FUTURE_XYZ"},
                    )
                ],
            )
            await session.commit()
            assert shipment.status == ShipmentStatus.IN_TRANSIT.value
            assert shipment.status != ShipmentStatus.DELIVERED.value

    asyncio.run(body())


def test_multi_shipment_delivered_only_when_all_done(override_database):
    async def body():
        async with TestingSessionLocal() as session:
            order = Order(
                tracking_code="KZ-TRK-4",
                mode=OrderMode.PURCHASE,
                status=OrderStatus.SHIPPED.value,
                payment_status=PaymentStatus.PAID.value,
                customer_full_name="علی تست",
                customer_phone="09123333333",
                postal_tracking_code="1234567890123",
            )
            session.add(order)
            await session.flush()
            a = Shipment(
                public_id=str(uuid4()),
                order_id=order.id,
                provider="postex",
                status=ShipmentStatus.DELIVERED.value,
                tracking_code="1234567890123",
            )
            b = Shipment(
                public_id=str(uuid4()),
                order_id=order.id,
                provider="postex",
                status=ShipmentStatus.IN_TRANSIT.value,
                tracking_code="1234567890999",
            )
            session.add_all([a, b])
            await session.flush()
            await apply_tracking_to_order(session, order)
            assert order.status == OrderStatus.SHIPPED.value
            b.status = ShipmentStatus.DELIVERED.value
            await apply_tracking_to_order(session, order)
            await session.commit()
            assert order.status == OrderStatus.DELIVERED.value

    asyncio.run(body())


def test_booking_barcode_does_not_mark_order_shipped(override_database):
    async def body():
        async with TestingSessionLocal() as session:
            order = Order(
                tracking_code="KZ-TRK-5",
                mode=OrderMode.PURCHASE,
                status=OrderStatus.PROCESSING.value,
                payment_status=PaymentStatus.PAID.value,
                customer_full_name="علی تست",
                customer_phone="09123333333",
            )
            session.add(order)
            await session.flush()
            shipment = Shipment(
                public_id=str(uuid4()),
                order_id=order.id,
                provider="postex",
                status=ShipmentStatus.BOOKED.value,
                provider_parcel_no="1001",
                tracking_code="1234567890123",
            )
            session.add(shipment)
            await session.flush()
            await apply_tracking_to_order(session, order)
            await session.commit()
            assert order.status == OrderStatus.PROCESSING.value
            assert order.postal_tracking_code == "1234567890123"

    asyncio.run(body())
