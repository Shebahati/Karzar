"""Manual Postex portal receiver-due fulfillment (no Postex HTTP)."""

from __future__ import annotations

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
from app.services.logistics.booking_worker import book_shipment, process_shipment_bookings
from app.services.logistics.fulfillment_mode import PostexFulfillmentMode, shipment_fulfillment_mode
from app.services.logistics.models import ShipmentStatus
from app.services.logistics.service import ensure_shipment_for_paid_order
from app.services.logistics.tracking_worker import process_tracking_sync
from app.services.order_expiry_service import cancel_expired_pending_payment_orders
from app.services.payment_flow_service import order_amount_rials
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tests.conftest import TestingSessionLocal, customer_auth_headers
from tests.test_postex_logistics import _enable_postex
from tests.test_postex_quotes_checkout import FakeProvider
from tests.test_postex_receiver_due import (
    _purchase_payload,
    _receiver_checkout,
    _seed_product_without_logistics,
)


@pytest.fixture
def fake_provider(monkeypatch):
    _enable_postex(monkeypatch)
    monkeypatch.setattr(settings, "POSTEX_SHIPPING_PAYMENT_MODE", "receiver_due")
    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", False)
    provider = FakeProvider()
    provider.quote_requests = []
    provider.create_requests = []

    original_quote = provider.quote
    original_create = provider.create_parcel

    async def capture_quote(**kwargs):
        provider.quote_requests.append(kwargs)
        return await original_quote(**kwargs)

    async def capture_create(request):
        provider.create_requests.append(request)
        return await original_create(request)

    provider.quote = capture_quote
    provider.create_parcel = capture_create
    monkeypatch.setattr("app.services.logistics.service.get_provider", lambda: provider)
    monkeypatch.setattr("app.services.logistics.booking_worker.get_provider", lambda: provider)
    monkeypatch.setattr("app.services.logistics.tracking_worker.get_provider", lambda: provider)
    monkeypatch.setattr("app.api.endpoints.shipping.get_provider", lambda: provider)
    return provider


def _reset_provider_ops(provider: FakeProvider) -> None:
    provider.op_log.clear()
    provider.create_calls = 0
    provider.lookup_calls = 0
    provider.cancel_calls = 0
    provider.ready_calls = 0
    provider.update_calls = 0
    provider.label_calls = 0
    provider.whoami_calls = 0


def _provider_total_ops(provider: FakeProvider) -> int:
    return (
        provider.create_calls
        + provider.lookup_calls
        + provider.cancel_calls
        + provider.ready_calls
        + provider.update_calls
        + provider.label_calls
        + provider.whoami_calls
    )


def _corrupt_fulfillment_data() -> dict:
    return {"fulfillment_mode": "manual-poratl"}


async def _seed_corrupt_shipment(
    *,
    status: str,
    extra: dict | None = None,
) -> tuple[int, int]:
    async with TestingSessionLocal() as session:
        order = Order(
            tracking_code=f"KZ-BAD-{uuid4().hex[:10]}",
            mode=OrderMode.PURCHASE,
            status=OrderStatus.PAID.value,
            payment_status=PaymentStatus.PAID.value,
            estimated_total=Decimal("100000"),
            customer_full_name="تست",
            customer_phone="09127777777",
            shipping={"location_code": 8, "address_line": "x" * 12},
            shipping_provider="postex",
            shipping_payment_mode="receiver_due",
        )
        session.add(order)
        await session.flush()
        provider_data = dict(_corrupt_fulfillment_data())
        if extra:
            provider_data.update(extra)
        shipment = Shipment(
            public_id=str(uuid4()),
            order_id=order.id,
            provider="postex",
            status=status,
            shipping_payment_mode="receiver_due",
            tracking_code="123456789012",
            provider_parcel_no="PX-1",
            provider_data=provider_data,
        )
        session.add(shipment)
        await session.commit()
        return order.id, shipment.id


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
    super_admin_headers, manual_portal_env, monkeypatch
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
    assert ship.json()["error_code"] == "SHIPMENT_STATE_INVALID"


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
    assert deliver.json()["error_code"] == "SHIPMENT_STATE_INVALID"


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


def _fresh_step_up_headers(super_admin_headers: dict[str, str]) -> dict[str, str]:
    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/verify-pin",
        json={"pin": settings.ADMIN_STEP_UP_PIN},
        headers=super_admin_headers,
    )
    assert response.status_code == 200
    return {**super_admin_headers, "X-Step-Up-Token": response.json()["secure_token"]}


@pytest.mark.usefixtures("override_database")
def test_manual_correction_preserves_omitted_optional_fields(
    super_admin_headers, manual_portal_env, step_up_headers
):
    client = TestClient(app)
    checkout = _receiver_checkout(
        client, super_admin_headers, key=f"keep-{uuid4().hex}", sku="MP-KEEP"
    )
    order_id, shipment_id = _mark_paid(checkout["order_id"])
    reg = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/register",
        json={
            "tracking_code": "123456789012",
            "provider_parcel_no": "PX-KEEP",
            "carrier_code": "IR_POST",
            "service_code": "EXPRESS",
            "internal_note": "یادداشت اولیه",
        },
        headers=super_admin_headers,
    )
    assert reg.status_code == 200
    fixed = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/correct",
        json={"tracking_code": "123456789099"},
        headers=step_up_headers,
    )
    assert fixed.status_code == 200
    body = fixed.json()
    assert body["tracking_code"] == "123456789099"
    assert body["provider_parcel_no"] == "PX-KEEP"
    assert body["carrier_code"] == "IR_POST"
    assert body["service_code"] == "EXPRESS"


@pytest.mark.usefixtures("override_database")
def test_manual_correction_explicit_null_clears_parcel(
    super_admin_headers, manual_portal_env, step_up_headers
):
    client = TestClient(app)
    checkout = _receiver_checkout(
        client, super_admin_headers, key=f"clr-{uuid4().hex}", sku="MP-CLR"
    )
    order_id, shipment_id = _mark_paid(checkout["order_id"])
    client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/register",
        json={
            "tracking_code": "123456789012",
            "provider_parcel_no": "PX-CLR",
        },
        headers=super_admin_headers,
    )
    cleared = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/correct",
        json={"tracking_code": "123456789012", "provider_parcel_no": None},
        headers=_fresh_step_up_headers(super_admin_headers),
    )
    assert cleared.status_code == 200
    assert cleared.json()["provider_parcel_no"] is None


@pytest.mark.usefixtures("override_database")
def test_manual_correction_before_handoff_only(
    super_admin_headers, manual_portal_env, step_up_headers
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
        headers=step_up_headers,
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
        headers=_fresh_step_up_headers(super_admin_headers),
    )
    assert after.status_code == 409


@pytest.mark.usefixtures("override_database")
def test_corrupt_fulfillment_snapshot_rejects_generic_postex(
    super_admin_headers, manual_portal_env, monkeypatch
):
    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", True)

    async def seed():
        async with TestingSessionLocal() as session:
            order = Order(
                tracking_code=f"KZ-BAD-{uuid4().hex[:10]}",
                mode=OrderMode.PURCHASE,
                status=OrderStatus.PAID.value,
                payment_status=PaymentStatus.PAID.value,
                estimated_total=Decimal("100000"),
                customer_full_name="تست",
                customer_phone="09127777777",
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
                provider_data={"fulfillment_mode": "manual-poratl"},
            )
            session.add(shipment)
            await session.commit()
            return order.id, shipment.id

    order_id, shipment_id = asyncio.run(seed())
    manual_portal_env.create_requests.clear()
    client = TestClient(app)
    resp = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/book",
        headers=super_admin_headers,
    )
    assert resp.status_code == 409
    assert manual_portal_env.create_requests == []


@pytest.mark.parametrize("booking_enabled", [False, True])
@pytest.mark.usefixtures("override_database")
def test_manual_portal_book_409_regardless_of_booking_flag(
    super_admin_headers, manual_portal_env, monkeypatch, booking_enabled: bool
):
    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", booking_enabled)
    client = TestClient(app)
    checkout = _receiver_checkout(
        client, super_admin_headers, key=f"bk-{uuid4().hex}-{booking_enabled}", sku="MP-BK"
    )
    order_id, shipment_id = _mark_paid(checkout["order_id"])
    client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/register",
        json={"tracking_code": "123456789012"},
        headers=super_admin_headers,
    )
    _reset_provider_ops(manual_portal_env)
    resp = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/book",
        headers=super_admin_headers,
    )
    assert resp.status_code == 409
    assert _provider_total_ops(manual_portal_env) == 0


@pytest.mark.parametrize("booking_enabled", [False, True])
@pytest.mark.usefixtures("override_database")
def test_corrupt_snapshot_book_409_regardless_of_booking_flag(
    super_admin_headers, manual_portal_env, monkeypatch, booking_enabled: bool
):
    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", booking_enabled)
    order_id, shipment_id = asyncio.run(
        _seed_corrupt_shipment(status=ShipmentStatus.BOOKED.value)
    )
    _ = order_id
    _reset_provider_ops(manual_portal_env)
    client = TestClient(app)
    resp = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/book",
        headers=super_admin_headers,
    )
    assert resp.status_code == 409
    assert _provider_total_ops(manual_portal_env) == 0


@pytest.mark.usefixtures("override_database")
def test_corrupt_pending_booking_worker_zero_provider_calls(manual_portal_env, monkeypatch):
    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", True)
    asyncio.run(_seed_corrupt_shipment(status=ShipmentStatus.PENDING_BOOKING.value))
    _reset_provider_ops(manual_portal_env)

    async def run() -> None:
        async with TestingSessionLocal() as db:
            await process_shipment_bookings(db)

    asyncio.run(run())
    assert _provider_total_ops(manual_portal_env) == 0
    assert manual_portal_env.op_log == []


@pytest.mark.usefixtures("override_database")
def test_corrupt_booked_tracking_worker_zero_provider_calls(manual_portal_env, monkeypatch):
    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", True)
    asyncio.run(_seed_corrupt_shipment(status=ShipmentStatus.BOOKED.value))
    _reset_provider_ops(manual_portal_env)

    async def run() -> None:
        async with TestingSessionLocal() as db:
            await process_tracking_sync(db)

    asyncio.run(run())
    assert _provider_total_ops(manual_portal_env) == 0


@pytest.mark.usefixtures("override_database")
def test_corrupt_cancellation_reconcile_zero_provider_calls(manual_portal_env, monkeypatch):
    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", True)
    _order_id, _shipment_id = asyncio.run(
        _seed_corrupt_shipment(
            status=ShipmentStatus.CANCELLATION_PENDING.value,
            extra={
                "cancellation_requested": True,
                "cancellation_request_uncertain": False,
            },
        )
    )
    _reset_provider_ops(manual_portal_env)

    async def run() -> None:
        async with TestingSessionLocal() as db:
            await process_shipment_bookings(db)

    asyncio.run(run())
    assert manual_portal_env.cancel_calls == 0
    assert manual_portal_env.lookup_calls == 0
    assert manual_portal_env.create_calls == 0


@pytest.mark.usefixtures("override_database")
def test_corrupt_snapshot_direct_book_shipment_zero_provider_calls(
    manual_portal_env, monkeypatch
):
    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", True)
    shipment_id = asyncio.run(
        _seed_corrupt_shipment(status=ShipmentStatus.PENDING_BOOKING.value)
    )[1]
    _reset_provider_ops(manual_portal_env)

    async def run() -> None:
        async with TestingSessionLocal() as db:
            await book_shipment(db, shipment_id)

    asyncio.run(run())
    assert _provider_total_ops(manual_portal_env) == 0


@pytest.mark.usefixtures("override_database")
def test_missing_fulfillment_snapshot_not_treated_as_corrupt(manual_portal_env):
    async def seed() -> int:
        async with TestingSessionLocal() as session:
            order = Order(
                tracking_code=f"KZ-API-{uuid4().hex[:10]}",
                mode=OrderMode.PURCHASE,
                status=OrderStatus.PAID.value,
                payment_status=PaymentStatus.PAID.value,
                estimated_total=Decimal("100000"),
                customer_full_name="تست",
                customer_phone="09127777777",
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
                provider_data={},
            )
            session.add(shipment)
            await session.commit()
            return shipment.id

    from app.services.logistics.fulfillment_mode import (
        is_corrupt_fulfillment_snapshot,
        provider_automation_blocked,
    )

    async def assert_legacy_api() -> None:
        async with TestingSessionLocal() as session:
            shipment = await session.get(Shipment, shipment_id)
            assert shipment is not None
            assert is_corrupt_fulfillment_snapshot(shipment) is False
            assert provider_automation_blocked(shipment) is False

    shipment_id = asyncio.run(seed())
    asyncio.run(assert_legacy_api())


@pytest.mark.usefixtures("override_database")
def test_manual_portal_rejects_receiver_api_prep_paths(
    super_admin_headers, manual_portal_env, monkeypatch
):
    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", True)
    client = TestClient(app)
    checkout = _receiver_checkout(
        client, super_admin_headers, key=f"prep-{uuid4().hex}", sku="MP-PREP"
    )
    order_id, shipment_id = _mark_paid(checkout["order_id"])
    client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/manual-portal/register",
        json={"tracking_code": "123456789012"},
        headers=super_admin_headers,
    )
    manual_portal_env.create_requests.clear()
    paths = [
        (
            "post",
            f"/api/v1/orders/{order_id}/shipments/{shipment_id}/final-package",
            {
                "length_cm": 10,
                "width_cm": 10,
                "height_cm": 10,
                "weight_grams": 100,
                "is_fragile": False,
                "is_liquid": False,
            },
        ),
        ("post", f"/api/v1/orders/{order_id}/shipments/{shipment_id}/packed-quote", None),
        (
            "post",
            f"/api/v1/orders/{order_id}/shipments/{shipment_id}/select-service",
            {"carrier_code": "IR_POST", "service_code": "EXPRESS"},
        ),
        ("post", f"/api/v1/orders/{order_id}/shipments/{shipment_id}/schedule-booking", None),
    ]
    for method, url, body in paths:
        if method == "post":
            resp = client.post(url, json=body or {}, headers=super_admin_headers)
        else:
            resp = client.get(url, headers=super_admin_headers)
        assert resp.status_code == 409, (url, resp.text)
    assert manual_portal_env.create_requests == []


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
