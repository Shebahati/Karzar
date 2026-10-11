"""Forward fulfillment must fail closed when payment is refunded but order is not cancelled."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.core.config import settings
from app.db.models.commerce import Order, OrderMode, OrderStatus, PaymentStatus
from app.db.models.logistics import Shipment, ShipmentEvent
from app.main import app
from app.services.logistics.booking_worker import book_shipment, process_shipment_bookings
from app.services.logistics.exceptions import ShipmentStateError
from app.services.logistics.manual_fulfillment import (
    manual_deliver,
    manual_handoff,
    manual_register,
)
from app.services.logistics.models import ShipmentStatus, TrackingEvent
from app.services.logistics.service import apply_tracking_to_order, ingest_tracking_events
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tests.conftest import TestingSessionLocal, customer_auth_headers
from tests.test_postex_booking_safety import _seed_order_shipment
from tests.test_postex_logistics import _enable_postex
from tests.test_postex_quotes_checkout import FakeProvider


@pytest.fixture
def manual_portal_test_env(monkeypatch):
    _enable_postex(monkeypatch)
    monkeypatch.setattr(settings, "POSTEX_FULFILLMENT_MODE", "manual_portal")
    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", False)
    monkeypatch.setattr(settings, "POSTEX_SHIPPING_PAYMENT_MODE", "receiver_due")
    monkeypatch.setattr(settings, "SHIPPING_TIPAX_ENABLED", False)
    monkeypatch.setattr(settings, "SHIPPING_CHAPAR_ENABLED", False)
    monkeypatch.setattr(settings, "SHIPPING_POST_PISHTAZ_ENABLED", False)
    monkeypatch.setattr(settings, "SHIPPING_TEHRAN_MOTORCYCLE_48H_ENABLED", False)
    monkeypatch.setattr(settings, "SHIPPING_TEHRAN_EXPRESS_3H_ENABLED", False)
    monkeypatch.setattr(settings, "SHIPPING_POSTEX_CHECKOUT_ENABLED", True)


@pytest.fixture
def booking_fake_provider(monkeypatch):
    _enable_postex(monkeypatch)
    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", True)
    provider = FakeProvider()
    monkeypatch.setattr("app.services.logistics.service.get_provider", lambda: provider)
    monkeypatch.setattr("app.services.logistics.booking_worker.get_provider", lambda: provider)
    monkeypatch.setattr("app.services.logistics.tracking_worker.get_provider", lambda: provider)
    monkeypatch.setattr("app.api.endpoints.shipping.get_provider", lambda: provider)
    return provider


async def _mark_order_refunded(order_id: int) -> None:
    async with TestingSessionLocal() as session:
        order = await session.get(Order, order_id)
        assert order is not None
        order.payment_status = PaymentStatus.REFUNDED.value
        order.status = OrderStatus.PROCESSING.value
        await session.commit()


def test_book_shipment_blocks_refunded_before_create(booking_fake_provider, override_database):
    order_id, shipment_id, _ = _seed_order_shipment(
        status=ShipmentStatus.PENDING_BOOKING.value,
        booking_attempts=0,
    )
    asyncio.run(_mark_order_refunded(order_id))

    async def run():
        async with TestingSessionLocal() as session:
            before = await session.get(Shipment, shipment_id)
            attempts_before = int(before.booking_attempts or 0)
            status_before = before.status
            data_before = dict(before.provider_data or {})
            processed = await book_shipment(session, shipment_id)
            assert processed is False
            after = await session.get(Shipment, shipment_id)
            assert booking_fake_provider.create_calls == 0
            assert int(after.booking_attempts or 0) == attempts_before
            assert after.status == status_before
            assert after.status != ShipmentStatus.BOOKING.value
            assert not (after.provider_data or {}).get("create_attempted")
            assert data_before.get("create_attempted") == (after.provider_data or {}).get(
                "create_attempted"
            )

    asyncio.run(run())


def test_process_shipment_bookings_skips_refunded_claim(booking_fake_provider, override_database):
    order_id, shipment_id, _ = _seed_order_shipment(
        status=ShipmentStatus.PENDING_BOOKING.value,
        booking_attempts=0,
    )
    asyncio.run(_mark_order_refunded(order_id))

    async def run():
        async with TestingSessionLocal() as session:
            count = await process_shipment_bookings(session)
            assert count == 0
            row = await session.get(Shipment, shipment_id)
            assert row.status == ShipmentStatus.PENDING_BOOKING.value
            assert booking_fake_provider.create_calls == 0

    asyncio.run(run())


def test_admin_book_rejects_refunded_ready_to_book(
    booking_fake_provider, override_database, super_admin_headers
):
    order_id, shipment_id, _ = _seed_order_shipment(
        status=ShipmentStatus.READY_TO_BOOK.value,
        booking_attempts=0,
    )
    asyncio.run(_mark_order_refunded(order_id))
    client = TestClient(app)
    res = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/book",
        headers=super_admin_headers,
    )
    assert res.status_code == 409
    assert res.json()["error_code"] == "SHIPMENT_STATE_INVALID"
    assert booking_fake_provider.create_calls == 0

    async def check():
        async with TestingSessionLocal() as session:
            row = await session.get(Shipment, shipment_id)
            assert row.status == ShipmentStatus.READY_TO_BOOK.value

    asyncio.run(check())


def test_admin_ready_rejects_refunded_order(booking_fake_provider, override_database, super_admin_headers):
    order_id, shipment_id, _ = _seed_order_shipment(
        status=ShipmentStatus.BOOKED.value,
        parcel_no="1001",
    )
    asyncio.run(_mark_order_refunded(order_id))
    client = TestClient(app)
    res = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/ready",
        headers=super_admin_headers,
    )
    assert res.status_code == 409
    assert res.json()["error_code"] == "SHIPMENT_STATE_INVALID"
    assert booking_fake_provider.ready_calls == 0

    async def check():
        async with TestingSessionLocal() as session:
            row = await session.get(Shipment, shipment_id)
            assert row.status == ShipmentStatus.BOOKED.value
            assert row.ready_to_accept is not True

    asyncio.run(check())


def test_admin_edit_rejects_refunded_order(booking_fake_provider, override_database, super_admin_headers):
    order_id, shipment_id, _ = _seed_order_shipment(
        status=ShipmentStatus.BOOKED.value,
        parcel_no="1001",
    )
    asyncio.run(_mark_order_refunded(order_id))
    client = TestClient(app)
    res = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/edit",
        json={
            "address_line": "خیابان جدید",
            "postal_code": "1234567890",
            "first_name": "علی",
            "last_name": "تست",
            "mobile_no": "09123333333",
        },
        headers=super_admin_headers,
    )
    assert res.status_code == 409
    assert res.json()["error_code"] == "SHIPMENT_STATE_INVALID"
    assert booking_fake_provider.update_calls == 0


def test_final_package_rejects_refunded_order(booking_fake_provider, override_database, super_admin_headers):
    order_id, shipment_id, _ = _seed_order_shipment(
        status=ShipmentStatus.AWAITING_PACKAGING.value,
    )
    asyncio.run(_mark_order_refunded(order_id))
    client = TestClient(app)
    res = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/final-package",
        json={
            "length_cm": 10,
            "width_cm": 8,
            "height_cm": 4,
            "weight_grams": 250,
            "is_fragile": False,
            "is_liquid": False,
        },
        headers=super_admin_headers,
    )
    assert res.status_code == 409
    assert res.json()["error_code"] == "SHIPMENT_STATE_INVALID"


@pytest.mark.usefixtures("enable_storefront_shipping_methods")
def test_manual_handoff_and_deliver_blocked_when_refunded(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    from tests.test_manual_fulfillment import _checkout_tipax

    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    order_id = _checkout_tipax(client, super_admin_headers, purchase_customer_headers)

    async def flow():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.status = OrderStatus.PROCESSING.value
            order.payment_status = PaymentStatus.REFUNDED.value
            from app.services.logistics.service import ensure_shipment_for_paid_order

            shipment = await ensure_shipment_for_paid_order(session, order)
            await manual_register(
                session,
                order=order,
                shipment=shipment,
                tracking_code="1234567890123",
            )
            events_before = await session.scalar(
                select(func.count()).select_from(ShipmentEvent).where(
                    ShipmentEvent.shipment_id == shipment.id
                )
            )
            try:
                await manual_handoff(session, order=order, shipment=shipment)
                raise AssertionError("expected handoff block")
            except ShipmentStateError as exc:
                assert exc.error_code == "SHIPMENT_STATE_INVALID"
            shipment.status = ShipmentStatus.PICKED_UP.value
            order.status = OrderStatus.SHIPPED.value
            await session.flush()
            try:
                await manual_deliver(session, order=order, shipment=shipment)
                raise AssertionError("expected deliver block")
            except ShipmentStateError as exc:
                assert exc.error_code == "SHIPMENT_STATE_INVALID"
            events_after = await session.scalar(
                select(func.count()).select_from(ShipmentEvent).where(
                    ShipmentEvent.shipment_id == shipment.id
                )
            )
            assert events_after == events_before
            assert shipment.status == ShipmentStatus.PICKED_UP.value
            assert order.status == OrderStatus.SHIPPED.value

    asyncio.run(flow())


def test_cancel_still_allowed_on_refunded_order(
    booking_fake_provider, override_database, step_up_headers
):
    order_id, shipment_id, _ = _seed_order_shipment(
        status=ShipmentStatus.BOOKED.value,
        parcel_no="1001",
    )
    asyncio.run(_mark_order_refunded(order_id))
    client = TestClient(app)
    res = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/cancel",
        json={"reason": "customer_request"},
        headers=step_up_headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "cancellation_pending"
    assert booking_fake_provider.cancel_calls == 1


def test_tracking_ingestion_allowed_without_order_lifecycle_advance(override_database):
    async def body():
        async with TestingSessionLocal() as session:
            order = Order(
                tracking_code="KZ-REF-TRK",
                mode=OrderMode.PURCHASE,
                status=OrderStatus.PROCESSING.value,
                payment_status=PaymentStatus.REFUNDED.value,
                customer_full_name="علی",
                customer_phone="09123333333",
                shipping={
                    "location_code": 8,
                    "city": "تهران",
                    "postal_code": "1234567890",
                    "address_line": "خیابان تست",
                },
            )
            session.add(order)
            await session.flush()
            shipment = Shipment(
                public_id=str(uuid4()),
                order_id=order.id,
                provider="postex",
                status=ShipmentStatus.IN_TRANSIT.value,
                carrier_code="IR_POST",
                service_code="EXPRESS",
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
                        provider_status="delivered",
                        provider_code="delivered",
                        occurred_at=datetime.now(UTC),
                        description="تحویل شد",
                        location=None,
                        payload={},
                    )
                ],
            )
            await apply_tracking_to_order(session, order)
            await session.commit()
            assert shipment.status == ShipmentStatus.DELIVERED.value
            assert order.status == OrderStatus.PROCESSING.value
            assert order.payment_status == PaymentStatus.REFUNDED.value

    asyncio.run(body())


@pytest.mark.usefixtures("override_database")
def test_manual_portal_register_blocked_when_refunded(
    super_admin_headers, manual_portal_test_env
):
    from tests.test_manual_portal_fulfillment import _mark_paid
    from tests.test_postex_receiver_due import _purchase_payload, _seed_product_without_logistics

    client = TestClient(app)
    product = _seed_product_without_logistics(client, super_admin_headers, sku="MP-REF")
    checkout = client.post(
        "/api/v1/checkout",
        json=_purchase_payload(product["id"]),
        headers={**customer_auth_headers(), "Idempotency-Key": f"ref-mp-{uuid4().hex}"},
    )
    assert checkout.status_code == 201, checkout.text
    order_id, shipment_id = _mark_paid(checkout.json()["order_id"])

    async def refund_processing() -> None:
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.payment_status = PaymentStatus.REFUNDED.value
            order.status = OrderStatus.PROCESSING.value
            await session.commit()

    asyncio.run(refund_processing())

    async def snapshot_before():
        async with TestingSessionLocal() as session:
            sh = await session.get(Shipment, shipment_id)
            order = await session.get(Order, order_id)
            events = await session.scalar(
                select(func.count()).select_from(ShipmentEvent).where(
                    ShipmentEvent.shipment_id == shipment_id
                )
            )
            return (
                sh.status,
                sh.tracking_code,
                sh.provider_parcel_no,
                dict(sh.provider_data or {}),
                order.postal_tracking_code,
                events,
            )

    before = asyncio.run(snapshot_before())
    res = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/register",
        json={"tracking_code": "123456789012", "provider_parcel_no": "PX-9"},
        headers=super_admin_headers,
    )
    assert res.status_code == 409
    assert res.json()["error_code"] == "SHIPMENT_STATE_INVALID"
    after = asyncio.run(snapshot_before())
    assert after == before


@pytest.mark.usefixtures("override_database")
def test_manual_portal_correct_handoff_deliver_blocked_when_refunded(
    super_admin_headers, step_up_headers, manual_portal_test_env
):
    from tests.test_manual_portal_fulfillment import _mark_paid
    from tests.test_postex_receiver_due import _purchase_payload, _seed_product_without_logistics

    client = TestClient(app)
    product = _seed_product_without_logistics(client, super_admin_headers, sku="MP-REF2")
    checkout = client.post(
        "/api/v1/checkout",
        json=_purchase_payload(product["id"]),
        headers={**customer_auth_headers(), "Idempotency-Key": f"ref-mp2-{uuid4().hex}"},
    )
    assert checkout.status_code == 201, checkout.text
    order_id, shipment_id = _mark_paid(checkout.json()["order_id"])
    tracking = "123456789055"
    reg = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/register",
        json={"tracking_code": tracking},
        headers=super_admin_headers,
    )
    assert reg.status_code == 200, reg.text
    client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "processing"},
        headers=super_admin_headers,
    )

    async def refund_processing() -> None:
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.payment_status = PaymentStatus.REFUNDED.value
            await session.commit()

    asyncio.run(refund_processing())

    correct = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/correct",
        json={"tracking_code": "999999999999", "update_fields": ["tracking_code"]},
        headers=step_up_headers,
    )
    assert correct.status_code == 409

    handoff = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/handoff",
        headers=super_admin_headers,
    )
    assert handoff.status_code == 409

    async def set_shipped():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            shipment = await session.get(Shipment, shipment_id)
            order.status = OrderStatus.SHIPPED.value
            shipment.status = ShipmentStatus.PICKED_UP.value
            await session.commit()

    asyncio.run(set_shipped())

    deliver = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/deliver",
        headers=super_admin_headers,
    )
    assert deliver.status_code == 409

    async def final_state():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            shipment = await session.get(Shipment, shipment_id)
            return order.status, shipment.status

    assert asyncio.run(final_state()) == (OrderStatus.SHIPPED.value, ShipmentStatus.PICKED_UP.value)
