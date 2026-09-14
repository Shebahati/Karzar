"""Worker batch eligibility: manual/corrupt snapshots must not starve API rows."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from app.core.config import settings
from app.db.models.commerce import Order, OrderMode, OrderStatus, PaymentStatus
from app.db.models.logistics import Shipment
from app.services.logistics.booking_worker import book_shipment, process_shipment_bookings
from app.services.logistics.fulfillment_mode import (
    shipment_provider_automation_eligible,
    shipment_provider_automation_eligible_clause,
)
from app.services.logistics.models import ShipmentStatus, TrackingEvent
from app.services.logistics.tracking_worker import process_tracking_sync
from sqlalchemy import select

from tests.conftest import USE_POSTGRES_TESTS, TestingSessionLocal
from tests.test_postex_logistics import _enable_postex
from tests.test_postex_quotes_checkout import FakeProvider, provider_network_op_total


@pytest.fixture
def worker_fake_provider(monkeypatch):
    _enable_postex(monkeypatch)
    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", True)
    provider = FakeProvider()
    provider.tracking = [
        TrackingEvent(
            provider_status="registered",
            provider_code="REGISTERED",
            occurred_at=datetime.now(UTC),
            description="test",
            location=None,
        )
    ]
    monkeypatch.setattr("app.services.logistics.service.get_provider", lambda: provider)
    monkeypatch.setattr("app.services.logistics.booking_worker.get_provider", lambda: provider)
    monkeypatch.setattr("app.services.logistics.tracking_worker.get_provider", lambda: provider)
    return provider


async def _seed_order() -> Order:
    order = Order(
        tracking_code=f"KZ-{uuid4().hex[:10]}",
        mode=OrderMode.PURCHASE,
        status=OrderStatus.PROCESSING.value,
        payment_status=PaymentStatus.PAID.value,
        estimated_total=Decimal("100000"),
        customer_full_name="تست",
        customer_phone="09127777777",
        shipping={
            "location_code": 8,
            "city": "تهران",
            "postal_code": "1234567890",
            "address_line": "خیابان تست پلاک ۱۲",
        },
        shipping_provider="postex",
        shipping_payment_mode="receiver_due",
    )
    return order


@pytest.mark.usefixtures("override_database")
def test_tracking_worker_processes_api_shipment_behind_manual_portal_rows(
    worker_fake_provider,
):
    async def seed() -> int:
        async with TestingSessionLocal() as session:
            for i in range(10):
                order = await _seed_order()
                session.add(order)
                await session.flush()
                session.add(
                    Shipment(
                        public_id=str(uuid4()),
                        order_id=order.id,
                        provider="postex",
                        status=ShipmentStatus.BOOKED.value,
                        shipping_payment_mode="receiver_due",
                        tracking_code=f"1234567890{i:02d}",
                        provider_data={"fulfillment_mode": "manual_portal"},
                        last_tracking_sync_at=None,
                    )
                )
            api_order = await _seed_order()
            session.add(api_order)
            await session.flush()
            api_shipment = Shipment(
                public_id=str(uuid4()),
                order_id=api_order.id,
                provider="postex",
                status=ShipmentStatus.BOOKED.value,
                shipping_payment_mode="receiver_due",
                provider_parcel_no="9001",
                tracking_code="123456789099",
                provider_data={"fulfillment_mode": "api"},
                last_tracking_sync_at=None,
            )
            session.add(api_shipment)
            await session.commit()
            return api_shipment.id

    api_id = asyncio.run(seed())

    async def run() -> int:
        async with TestingSessionLocal() as db:
            count = await process_tracking_sync(db)
            await db.commit()
            return count

    processed = asyncio.run(run())
    assert processed == 1
    assert worker_fake_provider.tracking_events_calls == 1
    assert worker_fake_provider.tracking_events_by_barcode_calls == 0
    assert provider_network_op_total(worker_fake_provider) == 1

    async def assert_api_synced() -> None:
        async with TestingSessionLocal() as session:
            shipment = await session.get(Shipment, api_id)
            assert shipment is not None
            assert shipment.last_tracking_sync_at is not None

    asyncio.run(assert_api_synced())


@pytest.mark.usefixtures("override_database")
def test_booking_worker_reaches_api_pending_booking_behind_corrupt_rows(worker_fake_provider):
    async def seed() -> None:
        async with TestingSessionLocal() as session:
            for _ in range(10):
                order = await _seed_order()
                session.add(order)
                await session.flush()
                session.add(
                    Shipment(
                        public_id=str(uuid4()),
                        order_id=order.id,
                        provider="postex",
                        status=ShipmentStatus.PENDING_BOOKING.value,
                        shipping_payment_mode="receiver_due",
                        carrier_code="IR_POST",
                        service_code="EXPRESS",
                        package_length_cm=10,
                        package_width_cm=8,
                        package_height_cm=4,
                        package_weight_grams=250,
                        declared_value_irr=Decimal("1000000"),
                        package_is_fragile=False,
                        package_is_liquid=False,
                        booking_next_attempt_at=datetime.now(UTC),
                        provider_data={"fulfillment_mode": "manual-poratl"},
                    )
                )
            api_order = await _seed_order()
            session.add(api_order)
            await session.flush()
            session.add(
                Shipment(
                    public_id=str(uuid4()),
                    order_id=api_order.id,
                    provider="postex",
                    status=ShipmentStatus.PENDING_BOOKING.value,
                    shipping_payment_mode="receiver_due",
                    carrier_code="IR_POST",
                    service_code="EXPRESS",
                    package_length_cm=10,
                    package_width_cm=8,
                    package_height_cm=4,
                    package_weight_grams=250,
                    declared_value_irr=Decimal("1000000"),
                    package_is_fragile=False,
                    package_is_liquid=False,
                    booking_next_attempt_at=datetime.now(UTC),
                    provider_data={"package": {"box_type_id": 1}},
                )
            )
            await session.commit()

    asyncio.run(seed())

    async def run() -> int:
        async with TestingSessionLocal() as db:
            count = await process_shipment_bookings(db)
            await db.commit()
            return count

    processed = asyncio.run(run())
    assert worker_fake_provider.create_calls == 1
    assert worker_fake_provider.lookup_calls == 0
    assert processed == 1
    assert provider_network_op_total(worker_fake_provider) == 1


@pytest.mark.usefixtures("override_database")
def test_cancel_reconcile_reaches_api_behind_corrupt_cancellation_pending(worker_fake_provider):
    async def seed() -> None:
        async with TestingSessionLocal() as session:
            for _ in range(10):
                order = await _seed_order()
                session.add(order)
                await session.flush()
                session.add(
                    Shipment(
                        public_id=str(uuid4()),
                        order_id=order.id,
                        provider="postex",
                        status=ShipmentStatus.CANCELLATION_PENDING.value,
                        shipping_payment_mode="receiver_due",
                        provider_parcel_no="PX-BAD",
                        provider_data={"fulfillment_mode": "manual-poratl"},
                    )
                )
            api_order = await _seed_order()
            session.add(api_order)
            await session.flush()
            session.add(
                Shipment(
                    public_id=str(uuid4()),
                    order_id=api_order.id,
                    provider="postex",
                    status=ShipmentStatus.CANCELLATION_PENDING.value,
                    shipping_payment_mode="receiver_due",
                    provider_parcel_no="PX-OK",
                    booking_attempts=1,
                    provider_data={"create_attempted": True},
                )
            )
            await session.commit()

    asyncio.run(seed())

    async def run() -> int:
        async with TestingSessionLocal() as db:
            count = await process_shipment_bookings(db)
            await db.commit()
            return count

    processed = asyncio.run(run())
    assert worker_fake_provider.cancel_calls == 1
    assert worker_fake_provider.lookup_calls == 0
    assert processed == 1
    assert provider_network_op_total(worker_fake_provider) == 1


@pytest.mark.usefixtures("override_database")
def test_blocked_book_shipment_not_counted_as_processed(worker_fake_provider):
    async def seed() -> int:
        async with TestingSessionLocal() as session:
            order = await _seed_order()
            session.add(order)
            await session.flush()
            shipment = Shipment(
                public_id=str(uuid4()),
                order_id=order.id,
                provider="postex",
                status=ShipmentStatus.PENDING_BOOKING.value,
                shipping_payment_mode="receiver_due",
                provider_data={"fulfillment_mode": "manual-poratl"},
                booking_next_attempt_at=datetime.now(UTC),
            )
            session.add(shipment)
            await session.commit()
            return shipment.id

    shipment_id = asyncio.run(seed())

    async def run() -> tuple[bool, int]:
        async with TestingSessionLocal() as db:
            booked = await book_shipment(db, shipment_id)
            worker_processed = await process_shipment_bookings(db)
            return booked, worker_processed

    booked, worker_processed = asyncio.run(run())
    assert booked is False
    assert worker_processed == 0
    assert provider_network_op_total(worker_fake_provider) == 0


@pytest.mark.skipif(not USE_POSTGRES_TESTS, reason="PostgreSQL JSONB semantics")
@pytest.mark.usefixtures("override_database")
def test_eligibility_sql_matches_python_on_postgres():
    async def exercise() -> None:
        async with TestingSessionLocal() as session:
            cases: list[tuple[dict | None, bool]] = [
                (None, True),
                ({}, True),
                ({"fulfillment_mode": None}, True),
                ({"fulfillment_mode": ""}, True),
                ({"fulfillment_mode": "api"}, True),
                ({"fulfillment_mode": " manual_portal "}, False),
                ({"fulfillment_mode": "manual-poratl"}, False),
            ]
            for idx, (data, _expected) in enumerate(cases):
                order = await _seed_order()
                session.add(order)
                await session.flush()
                session.add(
                    Shipment(
                        public_id=str(uuid4()),
                        order_id=order.id,
                        provider="postex",
                        status=ShipmentStatus.BOOKED.value,
                        provider_data=data,
                        tracking_code=f"1234567890{idx}",
                    )
                )
            await session.commit()

            async with TestingSessionLocal() as session:
                rows = sorted(
                    list((await session.execute(select(Shipment))).scalars().all()),
                    key=lambda row: row.id,
                )
                assert len(rows) == len(cases)
                for shipment, (_, expected) in zip(rows, cases, strict=True):
                    py = shipment_provider_automation_eligible(shipment)
                    sql_hit = (
                        await session.execute(
                            select(Shipment.id).where(
                                Shipment.id == shipment.id,
                                shipment_provider_automation_eligible_clause(),
                            )
                        )
                    ).scalar_one_or_none()
                    assert py == expected
                    assert (sql_hit is not None) == expected

    asyncio.run(exercise())
