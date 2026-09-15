"""Manual carrier lifecycle guards (Tipax/Chapar/local_delivery)."""

import asyncio

import pytest
from app.db.models.commerce import Order, OrderStatus, PaymentStatus
from app.main import app
from app.services.logistics.exceptions import ShipmentStateError
from app.services.logistics.manual_fulfillment import (
    manual_deliver,
    manual_handoff,
    manual_register,
)
from app.services.logistics.service import ensure_shipment_for_paid_order
from fastapi.testclient import TestClient

from tests.conftest import TestingSessionLocal
from tests.test_manual_fulfillment import _checkout_tipax

pytestmark = pytest.mark.usefixtures("enable_storefront_shipping_methods")


def test_handoff_from_paid_rejected(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    order_id = _checkout_tipax(client, super_admin_headers, purchase_customer_headers)

    async def flow():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.status = OrderStatus.PAID.value
            shipment = await ensure_shipment_for_paid_order(session, order)
            await manual_register(session, order=order, shipment=shipment, tracking_code="1234567890123")
            try:
                await manual_handoff(session, order=order, shipment=shipment)
                raise AssertionError("expected error")
            except ShipmentStateError as exc:
                assert exc.error_code == "SHIPMENT_STATE_INVALID"
            await session.refresh(order)
            await session.refresh(shipment)
            assert order.status == OrderStatus.PAID.value
            assert shipment.status == "booked"

    asyncio.run(flow())


def test_handoff_processing_booked_succeeds(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    order_id = _checkout_tipax(client, super_admin_headers, purchase_customer_headers)

    async def flow():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.status = OrderStatus.PROCESSING.value
            shipment = await ensure_shipment_for_paid_order(session, order)
            await manual_register(session, order=order, shipment=shipment, tracking_code="1234567890123")
            await manual_handoff(session, order=order, shipment=shipment)
            await session.commit()
            return order.status, shipment.status

    order_status, shipment_status = asyncio.run(flow())
    assert order_status == OrderStatus.SHIPPED.value
    assert shipment_status == "picked_up"


def test_deliver_from_booked_rejected(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    order_id = _checkout_tipax(client, super_admin_headers, purchase_customer_headers)

    async def flow():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.status = OrderStatus.PROCESSING.value
            shipment = await ensure_shipment_for_paid_order(session, order)
            await manual_register(session, order=order, shipment=shipment, tracking_code="1234567890123")
            try:
                await manual_deliver(session, order=order, shipment=shipment)
                raise AssertionError("expected error")
            except ShipmentStateError:
                pass
            assert shipment.status == "booked"
            assert order.status == OrderStatus.PROCESSING.value

    asyncio.run(flow())


def test_deliver_after_handoff_succeeds(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    order_id = _checkout_tipax(client, super_admin_headers, purchase_customer_headers)

    async def flow():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.status = OrderStatus.PROCESSING.value
            shipment = await ensure_shipment_for_paid_order(session, order)
            await manual_register(session, order=order, shipment=shipment, tracking_code="1234567890123")
            await manual_handoff(session, order=order, shipment=shipment)
            await manual_deliver(session, order=order, shipment=shipment)
            await session.commit()
            return order.status, shipment.status

    order_status, shipment_status = asyncio.run(flow())
    assert order_status == OrderStatus.DELIVERED.value
    assert shipment_status == "delivered"


def test_local_delivery_deliver_from_booked_rejected(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    from tests.test_shipping_hardening import _checkout_body, _seed

    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    pid = _seed(client, super_admin_headers, sku="LOCAL-DELIVER-BLOCK")
    order_id = client.post(
        "/api/v1/checkout",
        json=_checkout_body(pid, "tehran_express"),
        headers=purchase_customer_headers,
    ).json()["order_id"]

    async def flow():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.status = OrderStatus.PROCESSING.value
            shipment = await ensure_shipment_for_paid_order(session, order)
            await manual_register(session, order=order, shipment=shipment, courier_name="پیک")
            try:
                await manual_deliver(session, order=order, shipment=shipment)
                raise AssertionError("expected error")
            except ShipmentStateError:
                pass

    asyncio.run(flow())


def test_tipax_provider_reference_only_handoff(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    order_id = _checkout_tipax(client, super_admin_headers, purchase_customer_headers)

    async def flow():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.status = OrderStatus.PROCESSING.value
            shipment = await ensure_shipment_for_paid_order(session, order)
            await manual_register(session, order=order, shipment=shipment, provider_reference="TIP-42")
            await manual_handoff(session, order=order, shipment=shipment)
            await session.commit()
            ref = (shipment.provider_data or {}).get("manual", {}).get("provider_reference")
            return order.postal_tracking_code, ref, order.status

    postal, ref, status = asyncio.run(flow())
    assert ref == "TIP-42"
    assert postal is None
    assert status == OrderStatus.SHIPPED.value


def test_chapar_provider_reference_only_handoff(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    order_id = _checkout_tipax(client, super_admin_headers, purchase_customer_headers)

    async def flow():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.status = OrderStatus.PROCESSING.value
            shipment = await ensure_shipment_for_paid_order(session, order)
            shipment.provider = "chapar"
            await manual_register(session, order=order, shipment=shipment, provider_reference="CHAP-9")
            await manual_handoff(session, order=order, shipment=shipment)
            await session.commit()
            return order.postal_tracking_code

    assert asyncio.run(flow()) is None


def test_tracking_copied_to_postal_on_handoff(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    order_id = _checkout_tipax(client, super_admin_headers, purchase_customer_headers)

    async def flow():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.status = OrderStatus.PROCESSING.value
            shipment = await ensure_shipment_for_paid_order(session, order)
            await manual_register(session, order=order, shipment=shipment, tracking_code="1234567890123")
            await manual_handoff(session, order=order, shipment=shipment)
            await session.commit()
            return order.postal_tracking_code

    assert asyncio.run(flow()) == "1234567890123"


def test_inconsistent_handoff_replay_rejected(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    order_id = _checkout_tipax(client, super_admin_headers, purchase_customer_headers)

    async def flow():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.status = OrderStatus.PROCESSING.value
            shipment = await ensure_shipment_for_paid_order(session, order)
            await manual_register(session, order=order, shipment=shipment, tracking_code="1234567890123")
            shipment.status = "picked_up"
            await session.flush()
            try:
                await manual_handoff(session, order=order, shipment=shipment)
                raise AssertionError("expected error")
            except ShipmentStateError as exc:
                assert exc.error_code == "SHIPMENT_STATE_INVALID"

    asyncio.run(flow())


def test_inconsistent_delivery_replay_rejected(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    order_id = _checkout_tipax(client, super_admin_headers, purchase_customer_headers)

    async def flow():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.status = OrderStatus.SHIPPED.value
            shipment = await ensure_shipment_for_paid_order(session, order)
            shipment.status = "delivered"
            await session.flush()
            try:
                await manual_deliver(session, order=order, shipment=shipment)
                raise AssertionError("expected error")
            except ShipmentStateError:
                pass

    asyncio.run(flow())


def test_valid_duplicate_handoff_noop(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    order_id = _checkout_tipax(client, super_admin_headers, purchase_customer_headers)

    async def flow():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.status = OrderStatus.PROCESSING.value
            shipment = await ensure_shipment_for_paid_order(session, order)
            await manual_register(session, order=order, shipment=shipment, tracking_code="1234567890123")
            await manual_handoff(session, order=order, shipment=shipment)
            await manual_handoff(session, order=order, shipment=shipment)
            await session.commit()
            return order.status, shipment.status

    order_status, shipment_status = asyncio.run(flow())
    assert order_status == OrderStatus.SHIPPED.value
    assert shipment_status == "picked_up"


def test_valid_duplicate_deliver_noop(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    order_id = _checkout_tipax(client, super_admin_headers, purchase_customer_headers)

    async def flow():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.status = OrderStatus.PROCESSING.value
            shipment = await ensure_shipment_for_paid_order(session, order)
            await manual_register(session, order=order, shipment=shipment, tracking_code="1234567890123")
            await manual_handoff(session, order=order, shipment=shipment)
            await manual_deliver(session, order=order, shipment=shipment)
            await manual_deliver(session, order=order, shipment=shipment)
            await session.commit()
            return order.status, shipment.status

    order_status, shipment_status = asyncio.run(flow())
    assert order_status == OrderStatus.DELIVERED.value
    assert shipment_status == "delivered"


def test_handoff_rejected_when_order_cancelled(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    order_id = _checkout_tipax(client, super_admin_headers, purchase_customer_headers)

    async def flow():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.status = OrderStatus.CANCELLED.value
            order.payment_status = PaymentStatus.PAID.value
            shipment = await ensure_shipment_for_paid_order(session, order)
            await manual_register(session, order=order, shipment=shipment, tracking_code="1234567890123")
            status_before = shipment.status
            try:
                await manual_handoff(session, order=order, shipment=shipment)
                raise AssertionError("expected error")
            except ShipmentStateError as exc:
                assert exc.error_code == "SHIPMENT_STATE_INVALID"
            await session.refresh(shipment)
            assert shipment.status == status_before

    asyncio.run(flow())


def test_deliver_rejected_when_order_not_shipped(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    order_id = _checkout_tipax(client, super_admin_headers, purchase_customer_headers)

    async def flow():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.status = OrderStatus.PROCESSING.value
            shipment = await ensure_shipment_for_paid_order(session, order)
            await manual_register(session, order=order, shipment=shipment, tracking_code="1234567890123")
            await manual_handoff(session, order=order, shipment=shipment)
            order.status = OrderStatus.PROCESSING.value
            shipment.status = "picked_up"
            await session.flush()
            try:
                await manual_deliver(session, order=order, shipment=shipment)
                raise AssertionError("expected error")
            except ShipmentStateError:
                pass
            assert shipment.status == "picked_up"

    asyncio.run(flow())


def test_lock_order_and_shipment_orders_order_before_shipment():
    import inspect

    from app.services.logistics.manual_portal_guard import lock_order_and_shipment

    source = inspect.getsource(lock_order_and_shipment)
    order_pos = source.find("Order")
    shipment_pos = source.find("Shipment")
    assert order_pos >= 0 and shipment_pos > order_pos
    assert "with_for_update" in source


def test_duplicate_register_no_extra_event(
    override_database, super_admin_headers, purchase_customer_headers, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.POSTEX_ENABLED", False)
    client = TestClient(app)
    order_id = _checkout_tipax(client, super_admin_headers, purchase_customer_headers)

    async def flow():
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            order.status = OrderStatus.PROCESSING.value
            shipment = await ensure_shipment_for_paid_order(session, order)
            await manual_register(
                session,
                order=order,
                shipment=shipment,
                tracking_code="1234567890123",
            )
            await session.refresh(shipment, ["events"])
            count_after_first = len(shipment.events)
            registered_at = (shipment.provider_data or {}).get("manual", {}).get("registered_at")
            await manual_register(
                session,
                order=order,
                shipment=shipment,
                tracking_code="1234567890123",
            )
            await session.refresh(shipment, ["events"])
            registered_at2 = (shipment.provider_data or {}).get("manual", {}).get("registered_at")
            return count_after_first, len(shipment.events), registered_at, registered_at2

    count_first, count_second, t1, t2 = asyncio.run(flow())
    assert count_second == count_first
    assert t1 == t2
