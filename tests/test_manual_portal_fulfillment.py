"""Manual Postex portal receiver-due fulfillment (no Postex HTTP)."""

from __future__ import annotations

pytest_plugins = ["tests.test_postex_receiver_due"]

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from app.core.config import settings
from app.db.models.commerce import Order, OrderMode, OrderStatus, PaymentStatus
from app.db.models.logistics import Shipment
from app.db.models.product import StockMovement, StockMovementType
from app.main import app
from app.services.logistics.booking_worker import process_shipment_bookings
from app.services.logistics.fulfillment_mode import PostexFulfillmentMode, shipment_fulfillment_mode
from app.services.logistics.models import ShipmentStatus
from app.services.logistics.service import ensure_shipment_for_paid_order
from app.services.logistics.tracking_worker import process_tracking_sync
from app.services.order_expiry_service import cancel_expired_pending_payment_orders
from app.services.payment_flow_service import order_amount_rials
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tests.conftest import TestingSessionLocal, customer_auth_headers
from tests.test_postex_receiver_due import (
    _purchase_payload,
    _receiver_checkout,
    _seed_product_without_logistics,
)


@pytest.fixture
def manual_portal_env(fake_provider, monkeypatch):
    monkeypatch.setattr(settings, "POSTEX_FULFILLMENT_MODE", "manual_portal")
    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", False)
    return fake_provider


def _mark_paid(order_id: int) -> tuple[int, int]:
    async def body() -> tuple[int, int]:
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            assert order is not None
            order.status = OrderStatus.PAID.value
            order.payment_status = PaymentStatus.PAID.value
            shipment = await ensure_shipment_for_paid_order(session, order)
            assert shipment is not None
            await session.commit()
            return order.id, shipment.id

    return asyncio.run(body())


@pytest.mark.usefixtures("override_database")
def test_manual_portal_checkout_and_shipment_snapshot(
    super_admin_headers, manual_portal_env
):
    client = TestClient(app)
    product = _seed_product_without_logistics(client, super_admin_headers, sku="MP-NOPKG")
    checkout = client.post(
        "/api/v1/checkout",
        json=_purchase_payload(product["id"]),
        headers={**customer_auth_headers(), "Idempotency-Key": f"mp-{uuid4().hex}"},
    )
    assert checkout.status_code == 201
    body = checkout.json()
    assert body["shipping_payment_mode"] == "receiver_due"
    assert body["shipping_display"] == "receiver_due"

    async def order_shipping_cost():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, body["order_id"])
            assert order.shipping_customer_cost is None

    asyncio.run(order_shipping_cost())
    assert order_amount_rials(
        type("O", (), {"estimated_total": Decimal(body["estimated_total"])})()
    ) == int(Decimal(body["estimated_total"]) * 10)

    order_id, shipment_id = _mark_paid(body["order_id"])
    async def read_shipment():
        async with TestingSessionLocal() as session:
            sh = await session.get(Shipment, shipment_id)
            assert sh is not None
            assert shipment_fulfillment_mode(sh) == PostexFulfillmentMode.MANUAL_PORTAL
            assert sh.status == ShipmentStatus.AWAITING_PACKAGING.value

    asyncio.run(read_shipment())

    status = client.get("/api/v1/shipping/status")
    assert status.json()["fulfillment_mode"] == "manual_portal"


@pytest.mark.usefixtures("override_database")
def test_manual_register_no_postex_calls(
    super_admin_headers, manual_portal_env
):
    client = TestClient(app)
    checkout = _receiver_checkout(
        client, super_admin_headers, key=f"mp-reg-{uuid4().hex}", sku="MP-REG"
    )
    order_id, shipment_id = _mark_paid(checkout["order_id"])
    tracking = "123456789012"
    reg = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/register",
        json={"tracking_code": tracking, "provider_parcel_no": "PX-1001"},
        headers=super_admin_headers,
    )
    assert reg.status_code == 200, reg.text
    assert reg.json()["status"] == "booked"
    assert reg.json()["tracking_code"] == tracking
    assert reg.json()["registration_source"] == "manual_portal"
    assert manual_portal_env.create_requests == []

    replay = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/register",
        json={"tracking_code": tracking, "provider_parcel_no": "PX-1001"},
        headers=super_admin_headers,
    )
    assert replay.status_code == 200

    conflict = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/register",
        json={"tracking_code": "999999999999"},
        headers=super_admin_headers,
    )
    assert conflict.status_code == 409


@pytest.mark.usefixtures("override_database")
def test_manual_handoff_and_delivery(
    super_admin_headers, manual_portal_env
):
    client = TestClient(app)
    checkout = _receiver_checkout(
        client, super_admin_headers, key=f"mp-hd-{uuid4().hex}", sku="MP-HD"
    )
    order_id, shipment_id = _mark_paid(checkout["order_id"])
    tracking = "123456789099"
    client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/register",
        json={"tracking_code": tracking},
        headers=super_admin_headers,
    )
    proc = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "processing"},
        headers=super_admin_headers,
    )
    assert proc.status_code == 200, proc.text
    handoff = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/handoff",
        headers=super_admin_headers,
    )
    assert handoff.status_code == 200, handoff.text
    assert handoff.json()["status"] == "picked_up"

    async def order_state():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            assert order is not None
            assert order.status == OrderStatus.SHIPPED.value
            assert order.postal_tracking_code == tracking

    asyncio.run(order_state())

    deliver = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/deliver",
        headers=super_admin_headers,
    )
    assert deliver.status_code == 200
    assert deliver.json()["status"] == "delivered"

    async def final():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            assert order.status == OrderStatus.DELIVERED.value

    asyncio.run(final())


@pytest.mark.usefixtures("override_database")
def test_api_fulfillment_mode_unchanged(
    super_admin_headers, fake_provider, monkeypatch
):
    client = TestClient(app)
    monkeypatch.setattr(settings, "POSTEX_FULFILLMENT_MODE", "api")
    checkout = _receiver_checkout(
        client, super_admin_headers, key=f"api-{uuid4().hex}", sku="MP-API"
    )
    order_id, shipment_id = _mark_paid(checkout["order_id"])

    async def mode():
        async with TestingSessionLocal() as session:
            sh = await session.get(Shipment, shipment_id)
            assert shipment_fulfillment_mode(sh) == PostexFulfillmentMode.API

    asyncio.run(mode())

    blocked = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/register",
        json={"tracking_code": "123456789012"},
        headers=super_admin_headers,
    )
    assert blocked.status_code == 409


@pytest.mark.usefixtures("override_database")
def test_workers_ignore_manual_portal_shipments(manual_portal_env, monkeypatch):
    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", True)

    async def seed_and_run():
        async with TestingSessionLocal() as session:
            order = Order(
                tracking_code=f"KZ-MP-{uuid4().hex[:10]}",
                mode=OrderMode.PURCHASE,
                status=OrderStatus.PAID.value,
                payment_status=PaymentStatus.PAID.value,
                estimated_total=Decimal("100000"),
                customer_full_name="تست",
                customer_phone="09123333333",
                shipping={"location_code": 8, "address_line": "x" * 12},
                shipping_provider="postex",
                shipping_payment_mode="receiver_due",
            )
            session.add(order)
            await session.flush()
            shipment = Shipment(
                public_id=str(uuid4()),
                order_id=order.id,
                provider="postex",
                status=ShipmentStatus.BOOKED.value,
                shipping_payment_mode="receiver_due",
                tracking_code="123456789012",
                provider_data={
                    "fulfillment_mode": "manual_portal",
                    "registration_source": "manual_portal",
                },
            )
            session.add(shipment)
            await session.commit()
            return shipment.id

    asyncio.run(seed_and_run())
    manual_portal_env.create_requests.clear()

    async def workers():
        async with TestingSessionLocal() as session:
            booked = await process_shipment_bookings(session)
            tracked = await process_tracking_sync(session)
            await session.commit()
            return booked, tracked

    booked, tracked = asyncio.run(workers())
    assert booked == 0
    assert tracked == 0
    assert manual_portal_env.create_requests == []


@pytest.mark.usefixtures("override_database")
def test_expired_failed_with_stock_restock_once(
    super_admin_headers, monkeypatch
):
    client = TestClient(app)
    checkout = _receiver_checkout(
        client, super_admin_headers, key=f"fail-{uuid4().hex}", sku="MP-FAIL"
    )
    order_id = checkout["order_id"]

    async def fail_order():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.payment_status = PaymentStatus.FAILED.value
            order.payment_authority_expires_at = datetime.now(UTC) - timedelta(minutes=1)
            order.created_at = datetime.now(UTC) - timedelta(hours=2)
            await session.commit()

    asyncio.run(fail_order())
    monkeypatch.setattr(
        "app.services.order_expiry_service.pending_payment_cutoff",
        lambda now=None: datetime.now(UTC) + timedelta(days=1),
    )

    async def sweep():
        async with TestingSessionLocal() as session:
            n = await cancel_expired_pending_payment_orders(session)
            await session.commit()
            return n

    assert asyncio.run(sweep()) == 1
    assert asyncio.run(sweep()) == 0

    async def returns():
        async with TestingSessionLocal() as session:
            count = (
                await session.execute(
                    select(func.count())
                    .select_from(StockMovement)
                    .where(
                        StockMovement.reference_id == f"order:{order_id}",
                        StockMovement.movement_type == StockMovementType.RETURN.value,
                    )
                )
            ).scalar_one()
            order = await session.get(Order, order_id)
            assert order.status == OrderStatus.CANCELLED.value
            return count

    assert asyncio.run(returns()) == 1


@pytest.mark.usefixtures("override_database")
def test_expiry_skips_late_callback_evidence(monkeypatch):
    async def seed():
        async with TestingSessionLocal() as session:
            order = Order(
                tracking_code=f"KZ-LATE-{uuid4().hex[:10]}",
                mode=OrderMode.PURCHASE,
                status=OrderStatus.PENDING_PAYMENT.value,
                payment_status=PaymentStatus.FAILED.value,
                estimated_total=Decimal("50000"),
                customer_full_name="تست",
                customer_phone="09125555555",
                shipping={"location_code": 8, "address_line": "x" * 12},
                created_at=datetime.now(UTC) - timedelta(hours=2),
                payment_authority_expires_at=datetime.now(UTC) - timedelta(minutes=5),
                payment_callback_received_at=datetime.now(UTC) - timedelta(minutes=10),
            )
            session.add(order)
            await session.commit()
            return order.id

    order_id = asyncio.run(seed())
    monkeypatch.setattr(
        "app.services.order_expiry_service.pending_payment_cutoff",
        lambda now=None: datetime.now(UTC) + timedelta(days=1),
    )

    async def sweep():
        async with TestingSessionLocal() as session:
            n = await cancel_expired_pending_payment_orders(session)
            await session.commit()
            order = await session.get(Order, order_id)
            assert order.status == OrderStatus.PENDING_PAYMENT.value
            return n

    assert asyncio.run(sweep()) == 0


@pytest.mark.usefixtures("override_database")
def test_generic_order_ship_blocked_for_manual_portal(
    super_admin_headers, manual_portal_env
):
    client = TestClient(app)
    checkout = _receiver_checkout(
        client, super_admin_headers, key=f"bypass-{uuid4().hex}", sku="MP-BYPASS"
    )
    order_id, _ = _mark_paid(checkout["order_id"])
    client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "processing"},
        headers=super_admin_headers,
    )
    ship = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "shipped", "postal_tracking_code": "123456789012"},
        headers=super_admin_headers,
    )
    assert ship.status_code == 409


@pytest.mark.usefixtures("override_database")
def test_generic_order_deliver_blocked_for_manual_portal(
    super_admin_headers, manual_portal_env
):
    client = TestClient(app)
    checkout = _receiver_checkout(
        client, super_admin_headers, key=f"del-{uuid4().hex}", sku="MP-DEL"
    )
    order_id, shipment_id = _mark_paid(checkout["order_id"])
    client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/register",
        json={"tracking_code": "123456789012"},
        headers=super_admin_headers,
    )
    client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "processing"},
        headers=super_admin_headers,
    )
    client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/handoff",
        headers=super_admin_headers,
    )
    deliver = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "delivered"},
        headers=super_admin_headers,
    )
    assert deliver.status_code == 409


@pytest.mark.usefixtures("override_database")
def test_manual_handoff_requires_processing(
    super_admin_headers, manual_portal_env
):
    client = TestClient(app)
    checkout = _receiver_checkout(
        client, super_admin_headers, key=f"proc-{uuid4().hex}", sku="MP-PROC"
    )
    order_id, shipment_id = _mark_paid(checkout["order_id"])
    client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/register",
        json={"tracking_code": "123456789012"},
        headers=super_admin_headers,
    )
    handoff = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/handoff",
        headers=super_admin_headers,
    )
    assert handoff.status_code == 409


@pytest.mark.usefixtures("override_database")
def test_failed_after_callback_not_auto_cancelled(monkeypatch):
    async def seed():
        async with TestingSessionLocal() as session:
            order = Order(
                tracking_code=f"KZ-FAILCB-{uuid4().hex[:10]}",
                mode=OrderMode.PURCHASE,
                status=OrderStatus.PENDING_PAYMENT.value,
                payment_status=PaymentStatus.FAILED.value,
                estimated_total=Decimal("50000"),
                customer_full_name="تست",
                customer_phone="09126666666",
                shipping={"location_code": 8, "address_line": "x" * 12},
                created_at=datetime.now(UTC) - timedelta(hours=2),
                payment_authority_expires_at=datetime.now(UTC) - timedelta(minutes=5),
                payment_callback_received_at=datetime.now(UTC) - timedelta(minutes=30),
                payment_last_error="verify_rejected",
            )
            session.add(order)
            await session.commit()
            return order.id

    order_id = asyncio.run(seed())
    monkeypatch.setattr(
        "app.services.order_expiry_service.pending_payment_cutoff",
        lambda now=None: datetime.now(UTC) + timedelta(days=1),
    )

    async def sweep():
        async with TestingSessionLocal() as session:
            n = await cancel_expired_pending_payment_orders(session)
            await session.commit()
            order = await session.get(Order, order_id)
            assert order.status == OrderStatus.PENDING_PAYMENT.value
            return n

    assert asyncio.run(sweep()) == 0


@pytest.mark.usefixtures("override_database")
def test_generic_postex_endpoints_reject_manual_portal(
    super_admin_headers, manual_portal_env, monkeypatch
):
    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", True)
    client = TestClient(app)
    checkout = _receiver_checkout(
        client, super_admin_headers, key=f"postex-{uuid4().hex}", sku="MP-NOHTTP"
    )
    order_id, shipment_id = _mark_paid(checkout["order_id"])
    tracking = "123456789011"
    client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/register",
        json={"tracking_code": tracking, "provider_parcel_no": "PX-9"},
        headers=super_admin_headers,
    )
    manual_portal_env.create_requests.clear()
    assert (
        client.post(
            f"/api/v1/orders/{order_id}/shipments/{shipment_id}/book",
            headers=super_admin_headers,
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/orders/{order_id}/shipments/{shipment_id}/ready",
            headers=super_admin_headers,
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/orders/{order_id}/shipments/{shipment_id}/refresh-tracking",
            headers=super_admin_headers,
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/orders/{order_id}/shipments/{shipment_id}/edit",
            json={"address_line": "x" * 12},
            headers=super_admin_headers,
        ).status_code
        == 409
    )
    label = client.get(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/label",
        headers=super_admin_headers,
    )
    assert label.status_code == 409
    assert manual_portal_env.create_requests == []


@pytest.mark.usefixtures("override_database")
def test_generic_cancel_rejects_manual_portal(
    super_admin_headers, manual_portal_env, step_up_headers, monkeypatch
):
    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", True)
    client = TestClient(app)
    checkout = _receiver_checkout(
        client, super_admin_headers, key=f"cncl-{uuid4().hex}", sku="MP-CNCL"
    )
    order_id, shipment_id = _mark_paid(checkout["order_id"])
    client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/register",
        json={"tracking_code": "123456789012", "provider_parcel_no": "PX-C"},
        headers=super_admin_headers,
    )
    manual_portal_env.create_requests.clear()
    resp = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/cancel",
        json={"reason": "test"},
        headers=step_up_headers,
    )
    assert resp.status_code == 409
    assert manual_portal_env.create_requests == []


@pytest.mark.usefixtures("override_database")
def test_manual_correction_before_handoff_only(
    super_admin_headers, manual_portal_env
):
    client = TestClient(app)
    checkout = _receiver_checkout(
        client, super_admin_headers, key=f"corr-{uuid4().hex}", sku="MP-CORR"
    )
    order_id, shipment_id = _mark_paid(checkout["order_id"])
    client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/register",
        json={"tracking_code": "123456789012"},
        headers=super_admin_headers,
    )
    fixed = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/correct",
        json={"tracking_code": "123456789099"},
        headers=super_admin_headers,
    )
    assert fixed.status_code == 200
    assert fixed.json()["tracking_code"] == "123456789099"
    client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "processing"},
        headers=super_admin_headers,
    )
    client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/handoff",
        headers=super_admin_headers,
    )
    after = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/correct",
        json={"tracking_code": "123456789088"},
        headers=super_admin_headers,
    )
    assert after.status_code == 409


def test_settings_reject_manual_portal_without_receiver_due():
    from pydantic import ValidationError

    from tests.test_postex_receiver_due import _settings

    with pytest.raises(ValidationError):
        _settings(
            POSTEX_FULFILLMENT_MODE="manual_portal",
            POSTEX_SHIPPING_PAYMENT_MODE="sender_prepaid",
        )


@pytest.mark.usefixtures("override_database")
def test_handoff_emits_single_shipped_notification(
    super_admin_headers, manual_portal_env, monkeypatch
):
    calls: list[str] = []

    async def _capture(phone, *, tracking_code, status):
        calls.append(status)

    monkeypatch.setattr(
        "app.services.order_service.notify_order_status_change",
        _capture,
    )
    client = TestClient(app)
    checkout = _receiver_checkout(
        client, super_admin_headers, key=f"sms-{uuid4().hex}", sku="MP-SMS"
    )
    order_id, shipment_id = _mark_paid(checkout["order_id"])
    client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/register",
        json={"tracking_code": "123456789012"},
        headers=super_admin_headers,
    )
    client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "processing"},
        headers=super_admin_headers,
    )
    handoff = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/handoff",
        headers=super_admin_headers,
    )
    assert handoff.status_code == 200
    assert calls.count("shipped") == 1
