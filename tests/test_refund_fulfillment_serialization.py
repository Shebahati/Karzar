"""Refund ↔ forward fulfillment serialization (order locks, booking fence)."""

from __future__ import annotations

import asyncio
import threading
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.core.config import settings
from app.crud import commerce as crud_commerce
from app.db.models.commerce import Order, OrderStatus, PaymentStatus
from app.db.models.logistics import Shipment
from app.db.models.platform import AdminAuditLog
from app.main import app
from app.services.logistics.models import ShipmentStatus
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.conftest import USE_POSTGRES_TESTS, TestingSessionLocal, customer_auth_headers
from tests.test_external_refund_confirmation import (
    _activate_mock_checkout,
    _activate_sep,
    _checkout,
    _mark_order_paid,
)
from tests.test_postex_booking_safety import _seed_order_shipment
from tests.test_postex_logistics import _enable_postex
from tests.test_postex_quotes_checkout import FakeProvider

client = TestClient(app)


@pytest.fixture
def fake_provider(monkeypatch):
    _enable_postex(monkeypatch)
    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", True)
    provider = FakeProvider()
    monkeypatch.setattr("app.services.logistics.service.get_provider", lambda: provider)
    monkeypatch.setattr("app.services.logistics.booking_worker.get_provider", lambda: provider)
    monkeypatch.setattr("app.api.endpoints.shipping.get_provider", lambda: provider)
    return provider


def _post_external_refund(order_id: int, headers: dict, ref: str = "EXT-BUSY-001") -> int:
    res = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json={"order_id": order_id, "external_reference": ref},
        headers=headers,
    )
    return res.status_code


@pytest.mark.usefixtures("override_database")
def test_external_refund_rejected_when_booking_fence_active(
    valid_product_data, super_admin_headers, step_up_headers, monkeypatch
):
    _activate_mock_checkout(monkeypatch)
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "C1-BUSY"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    owner = customer_auth_headers("09127770100")
    checkout = _checkout(product_id, owner, phone="09127770100")
    order_id = checkout["order_id"]
    _mark_order_paid(order_id)
    _activate_sep(monkeypatch)

    async def seed_booking_fence() -> int:
        async with TestingSessionLocal() as db:
            order = await crud_commerce.get_order_by_id(db, order_id)
            shipment = order.shipments[0] if order and order.shipments else None
            if shipment is None:
                shipment = Shipment(
                    public_id=str(uuid4()),
                    order_id=order_id,
                    provider="postex",
                    status=ShipmentStatus.BOOKING.value,
                    carrier_code="IR_POST",
                    service_code="EXPRESS",
                    booking_attempts=1,
                    provider_data={"create_attempted": True, "create_started_at": datetime.now(UTC).isoformat()},
                )
                db.add(shipment)
            else:
                shipment.status = ShipmentStatus.BOOKING.value
                shipment.booking_attempts = 1
                shipment.provider_data = {
                    **(shipment.provider_data or {}),
                    "create_attempted": True,
                    "create_started_at": datetime.now(UTC).isoformat(),
                }
            await db.commit()
            return shipment.id

    asyncio.run(seed_booking_fence())

    status = _post_external_refund(order_id, step_up_headers)
    assert status == 409

    async def assert_unchanged():
        async with TestingSessionLocal() as db:
            order = await db.get(Order, order_id)
            assert order.payment_status == PaymentStatus.PAID.value
            assert order.payment_refund_id is None
            audits = (
                await db.execute(
                    select(AdminAuditLog).where(
                        AdminAuditLog.action == "payment_external_refund_confirmed",
                        AdminAuditLog.entity_id == str(order_id),
                    )
                )
            ).scalars().all()
            assert len(audits) == 0

    asyncio.run(assert_unchanged())


@pytest.mark.skipif(not USE_POSTGRES_TESTS, reason="requires PostgreSQL row locking")
@pytest.mark.usefixtures("override_database")
def test_mark_ready_holds_order_lock_until_provider_returns(
    fake_provider, super_admin_headers, step_up_headers, monkeypatch, valid_product_data
):
    _activate_sep(monkeypatch)
    order_id, shipment_id, _ = _seed_order_shipment(
        status=ShipmentStatus.BOOKED.value, parcel_no="1001"
    )

    async def mark_paid() -> None:
        async with TestingSessionLocal() as db:
            order = await db.get(Order, order_id)
            order.status = OrderStatus.PROCESSING.value
            order.payment_status = PaymentStatus.PAID.value
            order.payment_ref_id = "SEP-REF-LOCK"
            order.payment_authority = "SEP-AUTH-LOCK"
            await db.commit()

    asyncio.run(mark_paid())

    ready_started = threading.Event()
    release_ready = threading.Event()
    original_ready = fake_provider.mark_ready

    async def slow_mark_ready(parcel_nos):
        ready_started.set()
        release_ready.wait(timeout=30)
        return await original_ready(parcel_nos)

    fake_provider.mark_ready = slow_mark_ready

    ready_status: list[int] = []
    refund_status: list[int] = []

    def run_ready():
        res = client.post(
            f"/api/v1/orders/{order_id}/shipments/{shipment_id}/ready",
            headers=super_admin_headers,
        )
        ready_status.append(res.status_code)

    def run_refund():
        ready_started.wait(timeout=30)
        refund_status.append(_post_external_refund(order_id, step_up_headers, ref="EXT-AFTER-READY"))

    t_ready = threading.Thread(target=run_ready)
    t_refund = threading.Thread(target=run_refund)
    t_ready.start()
    t_refund.start()
    assert ready_started.wait(timeout=10)
    assert not refund_status, "refund should block until mark_ready completes"
    release_ready.set()
    t_ready.join(timeout=30)
    t_refund.join(timeout=30)
    assert ready_status == [200]
    assert refund_status == [200]
