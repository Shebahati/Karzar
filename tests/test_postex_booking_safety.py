"""Booking idempotency, ambiguous writes, ready/cancel guards, schema parity."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
from app.db.models.commerce import Order, OrderMode, OrderStatus, PaymentStatus
from app.db.models.logistics import Shipment, ShipmentEvent, ShippingQuote
from app.db.models.product import Product
from app.main import app
from app.services.logistics.booking_worker import (
    _book_one,
    book_shipment,
    never_attempted_create,
    process_shipment_bookings,
)
from app.services.logistics.exceptions import (
    ProviderAmbiguousWriteError,
    ProviderTimeoutError,
    ProviderValidationError,
)
from app.services.logistics.fingerprints import canonical_cart_items, cart_fingerprint
from app.services.logistics.models import ParcelBooking, QuoteLine, ShipmentStatus
from app.services.logistics.money import toman_to_irr
from app.services.logistics.package_builder import build_package
from app.services.logistics.postex.client import PostexClient
from app.services.logistics.service import build_parcel_create_request
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text

from tests.conftest import USE_POSTGRES_TESTS, TestingSessionLocal, customer_auth_headers
from tests.test_postex_logistics import _enable_postex
from tests.test_postex_quotes_checkout import FakeProvider, _seed_parcel_product


@pytest.fixture
def fake_provider(monkeypatch):
    _enable_postex(monkeypatch)
    provider = FakeProvider()
    monkeypatch.setattr("app.services.logistics.service.get_provider", lambda: provider)
    monkeypatch.setattr("app.services.logistics.booking_worker.get_provider", lambda: provider)
    monkeypatch.setattr("app.services.logistics.tracking_worker.get_provider", lambda: provider)
    monkeypatch.setattr("app.api.endpoints.shipping.get_provider", lambda: provider)
    return provider


def _seed_order_shipment(
    *,
    status: str,
    parcel_no: str | None = None,
    booking_attempts: int = 0,
    provider_data: dict | None = None,
) -> tuple[int, int, str]:
    async def seed():
        async with TestingSessionLocal() as session:
            order = Order(
                tracking_code="KZ-BOOK",
                mode=OrderMode.PURCHASE,
                status=OrderStatus.PROCESSING.value,
                payment_status=PaymentStatus.PAID.value,
                customer_full_name="علی تست",
                customer_phone="09123333333",
                company_name=None,
                shipping={
                    "location_code": 8,
                    "city": "تهران",
                    "postal_code": "1234567890",
                    "address_line": "خیابان تست پلاک ۱۲",
                },
                shipping_provider="postex",
            )
            session.add(order)
            await session.flush()
            data = {"package": {"box_type_id": 1}}
            if provider_data:
                data.update(provider_data)
            shipment = Shipment(
                public_id=str(uuid4()),
                order_id=order.id,
                provider="postex",
                status=status,
                carrier_code="IR_POST",
                service_code="EXPRESS",
                provider_parcel_no=parcel_no,
                tracking_code="1234567890123" if parcel_no else None,
                package_length_cm=10,
                package_width_cm=8,
                package_height_cm=4,
                package_weight_grams=250,
                declared_value_irr=Decimal("1000000"),
                booking_attempts=booking_attempts,
                booking_next_attempt_at=datetime.now(UTC),
                provider_data=data,
            )
            session.add(shipment)
            await session.commit()
            return order.id, shipment.id, shipment.public_id

    return asyncio.run(seed())


def test_recipient_company_omits_origin_brand(fake_provider, override_database):
    async def body():
        async with TestingSessionLocal() as session:
            order = Order(
                tracking_code="KZ-CO",
                mode=OrderMode.PURCHASE,
                status=OrderStatus.PAID.value,
                payment_status=PaymentStatus.PAID.value,
                customer_full_name="علی تست",
                customer_phone="09123333333",
                company_name=None,
                shipping={
                    "location_code": 8,
                    "city": "تهران",
                    "postal_code": "1234567890",
                    "address_line": "خیابان تست پلاک ۱۲",
                },
            )
            session.add(order)
            await session.flush()
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            order = (
                (
                    await session.execute(
                        select(Order)
                        .where(Order.id == order.id)
                        .options(selectinload(Order.items))
                    )
                )
                .scalars()
                .one()
            )
            shipment = Shipment(
                public_id=str(uuid4()),
                order_id=order.id,
                provider="postex",
                status=ShipmentStatus.PENDING_BOOKING.value,
                carrier_code="IR_POST",
                service_code="EXPRESS",
                package_length_cm=10,
                package_width_cm=8,
                package_height_cm=4,
                package_weight_grams=250,
                declared_value_irr=Decimal("1000000"),
                provider_data={"package": {"box_type_id": 1}},
            )
            session.add(shipment)
            await session.flush()
            request = build_parcel_create_request(order, shipment)
            to_contact = request["parcels"][0]["to"]["contact"]
            from_contact = request["parcels"][0]["from"]["contact"]
            assert "company_name" not in to_contact
            assert to_contact["first_name"] == "علی"
            assert "Karzar" not in str(to_contact)
            assert from_contact.get("company_name") != to_contact.get("company_name")

    asyncio.run(body())


def test_admin_double_book_is_noop(fake_provider, override_database, super_admin_headers):
    order_id, shipment_id, _ = _seed_order_shipment(status=ShipmentStatus.PENDING_BOOKING.value)
    client = TestClient(app)
    first = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/book",
        headers=super_admin_headers,
    )
    second = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/book",
        headers=super_admin_headers,
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["status"] == "booked"
    assert second.json()["status"] == "booked"
    assert fake_provider.create_calls == 1


def test_book_one_on_booked_never_creates(fake_provider, override_database):
    order_id, shipment_id, _ = _seed_order_shipment(
        status=ShipmentStatus.BOOKED.value, parcel_no="1001"
    )

    async def body():
        async with TestingSessionLocal() as session:
            shipment = await session.get(Shipment, shipment_id)
            await _book_one(session, shipment)
            await session.commit()
            row = await session.get(Shipment, shipment_id)
            assert row.status == ShipmentStatus.BOOKED.value
            assert fake_provider.create_calls == 0

    asyncio.run(body())
    _ = order_id


def test_worker_does_not_rebook_booked(fake_provider, override_database):
    _seed_order_shipment(status=ShipmentStatus.BOOKED.value, parcel_no="1001")

    async def body():
        async with TestingSessionLocal() as session:
            processed = await process_shipment_bookings(session)
            await session.commit()
            assert processed == 0
            assert fake_provider.create_calls == 0

    asyncio.run(body())


@pytest.mark.skipif(not USE_POSTGRES_TESTS, reason="requires PostgreSQL row locking")
def test_concurrent_booking_creates_one_parcel(fake_provider, override_database):
    order_id, shipment_id, public_id = _seed_order_shipment(
        status=ShipmentStatus.PENDING_BOOKING.value
    )
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_create(request):
        fake_provider.create_calls += 1
        started.set()
        await release.wait()
        booking = ParcelBooking(
            provider_parcel_no="1001",
            tracking_code="1234567890123",
            carrier_code="IR_POST",
            service_code="EXPRESS",
            provider_status="registered",
            raw={},
        )
        fake_provider.parcels[request["parcels"][0]["custom_order_no"]] = booking
        return booking

    fake_provider.create_parcel = slow_create

    async def book_with_session():
        async with TestingSessionLocal() as session:
            shipment = await session.get(Shipment, shipment_id)
            await _book_one(session, shipment)
            await session.commit()

    async def body():
        task_a = asyncio.create_task(book_with_session())
        await started.wait()
        task_b = asyncio.create_task(book_with_session())
        await asyncio.sleep(0.3)
        assert fake_provider.create_calls == 1
        release.set()
        await asyncio.gather(task_a, task_b)
        async with TestingSessionLocal() as session:
            row = await session.get(Shipment, shipment_id)
            assert row.provider_parcel_no == "1001"
            assert row.status == ShipmentStatus.BOOKED.value
            assert fake_provider.create_calls == 1
            assert public_id in fake_provider.parcels

    asyncio.run(body())
    _ = order_id


def test_ambiguous_transport_does_not_retry_create(fake_provider, override_database):
    order_id, shipment_id, public_id = _seed_order_shipment(
        status=ShipmentStatus.PENDING_BOOKING.value
    )

    async def reset_create(request):
        fake_provider.create_calls += 1
        raise ProviderAmbiguousWriteError("connection reset after send")

    fake_provider.create_parcel = reset_create

    async def body():
        async with TestingSessionLocal() as session:
            await process_shipment_bookings(session)
            await session.commit()
            row = await session.get(Shipment, shipment_id)
            assert row.status == ShipmentStatus.CREATION_UNCERTAIN.value
            assert fake_provider.create_calls == 1
            row.booking_next_attempt_at = datetime.now(UTC)
            await session.commit()

        async with TestingSessionLocal() as session:
            await process_shipment_bookings(session)
            await session.commit()
            row = await session.get(Shipment, shipment_id)
            assert row.status == ShipmentStatus.CREATION_UNCERTAIN.value
            assert fake_provider.create_calls == 1

        fake_provider.parcels[public_id] = ParcelBooking(
            provider_parcel_no="1001",
            tracking_code="1234567890123",
            carrier_code="IR_POST",
            service_code="EXPRESS",
            provider_status="registered",
            raw={},
        )
        async with TestingSessionLocal() as session:
            row = await session.get(Shipment, shipment_id)
            row.booking_next_attempt_at = datetime.now(UTC)
            await session.commit()
        async with TestingSessionLocal() as session:
            await process_shipment_bookings(session)
            await session.commit()
            row = await session.get(Shipment, shipment_id)
            assert row.status == ShipmentStatus.BOOKED.value
            assert fake_provider.create_calls == 1

    asyncio.run(body())
    _ = order_id


def test_definitive_4xx_is_error_not_uncertain(fake_provider, override_database):
    _, shipment_id, _ = _seed_order_shipment(status=ShipmentStatus.PENDING_BOOKING.value)

    async def reject(request):
        fake_provider.create_calls += 1
        raise ProviderValidationError("bad payload", http_status=400)

    fake_provider.create_parcel = reject

    async def body():
        async with TestingSessionLocal() as session:
            await process_shipment_bookings(session)
            await session.commit()
            row = await session.get(Shipment, shipment_id)
            assert row.status == ShipmentStatus.ERROR.value
            assert row.last_error_code == "PROVIDER_VALIDATION"

    asyncio.run(body())


def test_reconciliation_not_found_requires_two_lookups(fake_provider, override_database):
    _, shipment_id, _ = _seed_order_shipment(status=ShipmentStatus.CREATION_UNCERTAIN.value)

    async def body():
        async with TestingSessionLocal() as session:
            await process_shipment_bookings(session)
            await session.commit()
            row = await session.get(Shipment, shipment_id)
            assert row.status == ShipmentStatus.CREATION_UNCERTAIN.value
            assert fake_provider.create_calls == 0
            row.booking_next_attempt_at = datetime.now(UTC)
            await session.commit()
        async with TestingSessionLocal() as session:
            await process_shipment_bookings(session)
            await session.commit()
            row = await session.get(Shipment, shipment_id)
            assert row.status == ShipmentStatus.BOOKED.value
            assert fake_provider.create_calls == 1

    asyncio.run(body())


def test_ready_does_not_regress_in_transit(fake_provider, override_database, super_admin_headers):
    order_id, shipment_id, _ = _seed_order_shipment(
        status=ShipmentStatus.IN_TRANSIT.value, parcel_no="1001"
    )
    client = TestClient(app)
    res = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/ready",
        headers=super_admin_headers,
    )
    assert res.status_code == 409
    assert res.json()["error_code"] == "SHIPMENT_STATE_INVALID"
    assert fake_provider.ready_calls == 0


@pytest.mark.parametrize(
    "status",
    [
        ShipmentStatus.PICKED_UP.value,
        ShipmentStatus.OUT_FOR_DELIVERY.value,
        ShipmentStatus.DELIVERED.value,
        ShipmentStatus.RETURNING.value,
        ShipmentStatus.RETURNED.value,
        ShipmentStatus.CANCELLED.value,
    ],
)
def test_ready_blocked_for_non_eligible(
    fake_provider, override_database, super_admin_headers, status
):
    order_id, shipment_id, _ = _seed_order_shipment(status=status, parcel_no="1001")
    client = TestClient(app)
    res = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/ready",
        headers=super_admin_headers,
    )
    assert res.status_code == 409
    assert fake_provider.ready_calls == 0


def test_ready_from_booked(fake_provider, override_database, super_admin_headers):
    order_id, shipment_id, _ = _seed_order_shipment(
        status=ShipmentStatus.BOOKED.value, parcel_no="1001"
    )
    client = TestClient(app)
    res = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/ready",
        headers=super_admin_headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "ready_for_pickup"
    assert fake_provider.ready_calls == 1


def test_cancel_already_delivered(fake_provider, override_database, step_up_headers):
    order_id, shipment_id, _ = _seed_order_shipment(
        status=ShipmentStatus.DELIVERED.value, parcel_no="1001"
    )
    client = TestClient(app)
    res = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/cancel",
        json={"reason": "too late"},
        headers=step_up_headers,
    )
    assert res.status_code == 409
    assert fake_provider.cancel_calls == 0


def test_cancel_provider_rejection(fake_provider, override_database, step_up_headers):
    from app.services.logistics.exceptions import ProviderValidationError

    async def reject(parcel_no, reason):
        raise ProviderValidationError("too late", http_status=400)

    fake_provider.cancel_parcel = reject
    order_id, shipment_id, _ = _seed_order_shipment(
        status=ShipmentStatus.BOOKED.value, parcel_no="1001"
    )
    client = TestClient(app)
    res = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/cancel",
        json={"reason": "customer_request"},
        headers=step_up_headers,
    )
    assert res.status_code == 409
    assert res.json()["error_code"] == "SHIPPING_PROVIDER_CUTOFF"

    async def check():
        async with TestingSessionLocal() as session:
            row = await session.get(Shipment, shipment_id)
            assert row.status == ShipmentStatus.BOOKED.value

    asyncio.run(check())


def test_cancel_confirmed_via_tracking(fake_provider, override_database, step_up_headers):
    from app.services.logistics.models import TrackingEvent
    from app.services.logistics.service import ingest_tracking_events

    order_id, shipment_id, _ = _seed_order_shipment(
        status=ShipmentStatus.BOOKED.value, parcel_no="1001"
    )
    client = TestClient(app)
    res = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/cancel",
        json={"reason": "customer_request"},
        headers=step_up_headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "cancellation_pending"

    async def confirm():
        async with TestingSessionLocal() as session:
            shipment = await session.get(Shipment, shipment_id)
            await ingest_tracking_events(
                session,
                shipment,
                [
                    TrackingEvent(
                        provider_status="cancelled",
                        provider_code="cancelled",
                        occurred_at=datetime.now(UTC),
                        description="لغو شد",
                        location=None,
                        payload={},
                    )
                ],
            )
            await session.commit()
            row = await session.get(Shipment, shipment_id)
            assert row.status == ShipmentStatus.CANCELLED.value
            assert row.cancelled_at is not None

    asyncio.run(confirm())


def _boom_client(exc: Exception):
    class Boom:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def request(self, *args, **kwargs):
            raise exc

    return Boom


def test_client_timeout_after_send_is_ambiguous(monkeypatch):
    monkeypatch.setattr(
        "app.services.logistics.postex.client.httpx.AsyncClient",
        _boom_client(httpx.TimeoutException("timeout")),
    )
    client = PostexClient(base_url="https://api.postex.ir/api/v1", api_key="k", timeout_seconds=1)
    with pytest.raises(ProviderTimeoutError) as exc:
        asyncio.run(client.post_json("/parcels/bulk", {}, operation="parcels_bulk", mutating=True))
    assert exc.value.ambiguous_write is True


def test_client_connection_reset_after_send_is_ambiguous(monkeypatch):
    monkeypatch.setattr(
        "app.services.logistics.postex.client.httpx.AsyncClient",
        _boom_client(httpx.ReadError("connection reset")),
    )
    client = PostexClient(base_url="https://api.postex.ir/api/v1", api_key="k", timeout_seconds=1)
    with pytest.raises(ProviderAmbiguousWriteError) as exc:
        asyncio.run(client.post_json("/parcels/bulk", {}, operation="parcels_bulk", mutating=True))
    assert exc.value.ambiguous_write is True


def test_client_generic_transport_failure_is_ambiguous(monkeypatch):
    monkeypatch.setattr(
        "app.services.logistics.postex.client.httpx.AsyncClient",
        _boom_client(httpx.RemoteProtocolError("peer closed connection")),
    )
    client = PostexClient(base_url="https://api.postex.ir/api/v1", api_key="k", timeout_seconds=1)
    with pytest.raises(ProviderAmbiguousWriteError) as exc:
        asyncio.run(client.post_json("/parcels/bulk", {}, operation="parcels_bulk", mutating=True))
    assert exc.value.ambiguous_write is True


def test_client_definitive_4xx_not_ambiguous(monkeypatch):
    class FakeResponse:
        status_code = 400
        content = b'{"isSuccess":false,"message":"bad"}'

        def json(self):
            return {"isSuccess": False, "message": "bad"}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def request(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("app.services.logistics.postex.client.httpx.AsyncClient", FakeAsyncClient)
    client = PostexClient(base_url="https://api.postex.ir/api/v1", api_key="k", timeout_seconds=1)
    with pytest.raises(ProviderValidationError) as exc:
        asyncio.run(client.post_json("/parcels/bulk", {}, operation="parcels_bulk", mutating=True))
    assert exc.value.ambiguous_write is False
    assert exc.value.http_status == 400


def test_duplicate_lines_share_fingerprint_and_package():
    dup = [
        {"product_id": 1, "quantity": 1},
        {"product_id": 1, "quantity": 1},
    ]
    merged = [{"product_id": 1, "quantity": 2}]
    assert canonical_cart_items(dup) == merged
    assert cart_fingerprint(dup) == cart_fingerprint(merged)

    def line(qty: int) -> QuoteLine:
        return QuoteLine(
            product_id=1,
            sku="SKU-1",
            quantity=qty,
            unit_price_toman=Decimal("1000"),
            weight_grams=Decimal("250"),
            length_cm=Decimal("10"),
            width_cm=Decimal("8"),
            height_cm=Decimal("4"),
            is_fragile=False,
            is_liquid=False,
            shipping_class="parcel",
            is_available=True,
            name="Tool",
        )

    pkg_dup = build_package([line(1), line(1)])
    pkg_merged = build_package([line(2)])
    assert (pkg_dup.length_cm, pkg_dup.width_cm, pkg_dup.height_cm, pkg_dup.weight_grams) == (
        pkg_merged.length_cm,
        pkg_merged.width_cm,
        pkg_merged.height_cm,
        pkg_merged.weight_grams,
    )
    assert toman_to_irr(Decimal("1000") * 2) == toman_to_irr(Decimal("1000") * 2)


def test_quote_duplicate_lines_match_merged_checkout(
    fake_provider, override_database, super_admin_headers
):
    client = TestClient(app)
    product = _seed_parcel_product(client, super_admin_headers, sku="PARCEL-DUP")
    headers = customer_auth_headers()
    quote = client.post(
        "/api/v1/shipping/quotes",
        json={
            "items": [
                {"product_id": product["id"], "quantity": 1},
                {"product_id": product["id"], "quantity": 1},
            ],
            "location_code": 8,
            "postal_code": "1234567890",
        },
        headers=headers,
    )
    assert quote.status_code == 200, quote.text
    token = quote.json()["options"][0]["quote_token"]
    checkout = client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {"full_name": "علی تست", "phone": "09123333333", "is_guest": False},
            "items": [{"product_id": product["id"], "quantity": 2}],
            "shipping": {
                "province": "تهران",
                "city": "تهران",
                "postal_code": "1234567890",
                "address_line": "خیابان آزادی پلاک ۱۲۳۴",
                "location_code": 8,
            },
            "shipping_quote_token": token,
        },
        headers={**headers, "Idempotency-Key": "dup-lines"},
    )
    assert checkout.status_code == 201, checkout.text


def test_quote_does_not_lock_products(fake_provider, override_database, super_admin_headers, monkeypatch):
    client = TestClient(app)
    product = _seed_parcel_product(client, super_admin_headers, sku="PARCEL-NLOCK")

    async def boom(*args, **kwargs):
        raise AssertionError("quote path must not SELECT FOR UPDATE")

    monkeypatch.setattr("app.crud.product.get_products_for_update", boom)
    res = client.post(
        "/api/v1/shipping/quotes",
        json={"items": [{"product_id": product["id"], "quantity": 1}], "location_code": 8},
        headers=customer_auth_headers(),
    )
    assert res.status_code == 200, res.text


def test_price_change_between_quote_and_checkout(
    fake_provider, override_database, super_admin_headers
):
    client = TestClient(app)
    product = _seed_parcel_product(client, super_admin_headers, sku="PARCEL-PRICE")
    headers = customer_auth_headers()
    quote = client.post(
        "/api/v1/shipping/quotes",
        json={
            "items": [{"product_id": product["id"], "quantity": 1}],
            "location_code": 8,
            "postal_code": "1234567890",
        },
        headers=headers,
    )
    assert quote.status_code == 200, quote.text
    token = quote.json()["options"][0]["quote_token"]
    updated = client.put(
        f"/api/v1/products/{product['id']}",
        json={"base_price": "250000"},
        headers=super_admin_headers,
    )
    assert updated.status_code == 200, updated.text
    checkout = client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {"full_name": "علی تست", "phone": "09123333333", "is_guest": False},
            "items": [{"product_id": product["id"], "quantity": 1}],
            "shipping": {
                "province": "تهران",
                "city": "تهران",
                "postal_code": "1234567890",
                "address_line": "خیابان آزادی پلاک ۱۲۳۴",
                "location_code": 8,
            },
            "shipping_quote_token": token,
        },
        headers={**headers, "Idempotency-Key": "price-stale"},
    )
    assert checkout.status_code == 409
    assert checkout.json()["error_code"] == "SHIPPING_QUOTE_STALE"


@pytest.mark.skipif(not USE_POSTGRES_TESTS, reason="schema parity requires PostgreSQL")
def test_logistics_schema_parity_postgres(override_database):
    from tests.conftest import test_engine

    async def body():
        async with test_engine.connect() as conn:

            def sync_check(sync_conn):
                inspector = inspect(sync_conn)
                quote_cols = {col["name"] for col in inspector.get_columns("shipping_quotes")}
                shipment_cols = {col["name"] for col in inspector.get_columns("shipments")}
                event_cols = {col["name"] for col in inspector.get_columns("shipment_events")}
                product_cols = {col["name"] for col in inspector.get_columns("products")}
                order_cols = {col["name"] for col in inspector.get_columns("orders")}
                assert "updated_at" in quote_cols
                assert "created_at" in quote_cols
                assert "updated_at" in event_cols
                assert "cancellation_requested_at" in shipment_cols
                assert quote_cols == set(ShippingQuote.__table__.columns.keys())
                assert shipment_cols == set(Shipment.__table__.columns.keys())
                assert event_cols == set(ShipmentEvent.__table__.columns.keys())
                for name in (
                    "package_length_cm",
                    "package_width_cm",
                    "package_height_cm",
                    "shipping_is_fragile",
                    "shipping_is_liquid",
                    "shipping_class",
                ):
                    assert name in product_cols
                    assert name in Product.__table__.columns.keys()
                for name in (
                    "shipping_provider",
                    "shipping_quote_id",
                    "shipping_customer_cost",
                    "shipping_provider_quoted_cost",
                    "shipping_carrier_code",
                    "shipping_service_code",
                ):
                    assert name in order_cols
                    assert name in Order.__table__.columns.keys()
                indexes = {idx["name"] for idx in inspector.get_indexes("shipments")}
                assert "uq_shipments_provider_parcel_no" in indexes
                assert "uq_shipments_provider_tracking_code" in indexes

            await conn.run_sync(sync_check)

    asyncio.run(body())


@pytest.mark.skipif(not USE_POSTGRES_TESTS, reason="requires PostgreSQL durability")
def test_process_death_after_provider_create_does_not_duplicate(
    fake_provider, override_database
):
    """A/B/C/D: crash after Postex create, before Karzar stores the response."""
    order_id, shipment_id, public_id = _seed_order_shipment(
        status=ShipmentStatus.PENDING_BOOKING.value
    )

    async def create_then_die(request):
        await FakeProvider.create_parcel(fake_provider, request)
        raise asyncio.CancelledError()

    fake_provider.create_parcel = create_then_die

    async def body():
        async with TestingSessionLocal() as session:
            with pytest.raises(asyncio.CancelledError):
                await book_shipment(session, shipment_id)

        async with TestingSessionLocal() as session:
            row = await session.get(Shipment, shipment_id)
            assert row.status == ShipmentStatus.BOOKING.value
            assert row.status != ShipmentStatus.PENDING_BOOKING.value
            assert (row.provider_data or {}).get("create_attempted") is True
            assert row.provider_parcel_no is None
            assert row.booking_attempts == 1
            assert public_id in fake_provider.parcels

        lookups_before_recovery = fake_provider.lookup_calls
        async with TestingSessionLocal() as session:
            await process_shipment_bookings(session)
            row = await session.get(Shipment, shipment_id)
            assert row.status == ShipmentStatus.BOOKED.value
            assert row.provider_parcel_no == "1001"
            assert fake_provider.create_calls == 1
            assert fake_provider.lookup_calls > lookups_before_recovery
            assert fake_provider.op_log[0] == "create"
            assert "lookup" in fake_provider.op_log
            assert fake_provider.op_log.count("create") == 1

    asyncio.run(body())
    _ = order_id


@pytest.mark.skipif(not USE_POSTGRES_TESTS, reason="requires PostgreSQL row locking")
def test_create_does_not_hold_row_lock_during_network(fake_provider, override_database):
    _, shipment_id, _ = _seed_order_shipment(status=ShipmentStatus.PENDING_BOOKING.value)
    lock_wait_ok = False

    async def create_and_probe(request):
        async with TestingSessionLocal() as other:
            await other.execute(text("SET lock_timeout TO '200ms'"))
            try:
                await other.execute(
                    select(Shipment).where(Shipment.id == shipment_id).with_for_update()
                )
            except Exception as exc:
                raise AssertionError(
                    "shipment row lock was held during Postex create HTTP"
                ) from exc
            await other.rollback()
        fake_provider.create_calls += 1
        fake_provider.op_log.append("create")
        booking = ParcelBooking(
            provider_parcel_no="1001",
            tracking_code="1234567890123",
            carrier_code="IR_POST",
            service_code="EXPRESS",
            provider_status="registered",
            raw={},
        )
        fake_provider.parcels[request["parcels"][0]["custom_order_no"]] = booking
        return booking

    fake_provider.create_parcel = create_and_probe

    async def body():
        nonlocal lock_wait_ok
        async with TestingSessionLocal() as session:
            await book_shipment(session, shipment_id)
            row = await session.get(Shipment, shipment_id)
            assert row.status == ShipmentStatus.BOOKED.value
        lock_wait_ok = True

    asyncio.run(body())
    assert lock_wait_ok
    assert fake_provider.create_calls == 1


@pytest.mark.skipif(not USE_POSTGRES_TESTS, reason="requires PostgreSQL row locking")
def test_admin_and_worker_race_creates_one_parcel(
    fake_provider, override_database, super_admin_headers
):
    order_id, shipment_id, public_id = _seed_order_shipment(
        status=ShipmentStatus.PENDING_BOOKING.value
    )
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_create(request):
        fake_provider.create_calls += 1
        fake_provider.op_log.append("create")
        started.set()
        await release.wait()
        booking = ParcelBooking(
            provider_parcel_no="1001",
            tracking_code="1234567890123",
            carrier_code="IR_POST",
            service_code="EXPRESS",
            provider_status="registered",
            raw={},
        )
        fake_provider.parcels[request["parcels"][0]["custom_order_no"]] = booking
        return booking

    fake_provider.create_parcel = slow_create

    async def worker():
        async with TestingSessionLocal() as session:
            await process_shipment_bookings(session)

    async def admin_book():
        # Same domain function as POST /orders/{id}/shipments/{id}/book
        async with TestingSessionLocal() as session:
            await book_shipment(session, shipment_id)

    async def body():
        worker_task = asyncio.create_task(worker())
        admin_task = asyncio.create_task(admin_book())
        await started.wait()
        await asyncio.sleep(0.3)
        assert fake_provider.create_calls == 1
        release.set()
        await asyncio.gather(admin_task, worker_task)
        async with TestingSessionLocal() as session:
            row = await session.get(Shipment, shipment_id)
            assert row.provider_parcel_no == "1001"
            assert row.status == ShipmentStatus.BOOKED.value
            assert fake_provider.create_calls == 1
            assert public_id in fake_provider.parcels
        client = TestClient(app)
        res = client.post(
            f"/api/v1/orders/{order_id}/shipments/{shipment_id}/book",
            headers=super_admin_headers,
        )
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "booked"
        assert fake_provider.create_calls == 1

    asyncio.run(body())


def test_cancel_never_attempted_is_local(fake_provider, override_database, step_up_headers):
    order_id, shipment_id, _ = _seed_order_shipment(status=ShipmentStatus.PENDING_BOOKING.value)
    client = TestClient(app)
    res = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/cancel",
        json={"reason": "customer_request"},
        headers=step_up_headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "cancelled"
    assert fake_provider.cancel_calls == 0
    assert fake_provider.create_calls == 0

    async def check():
        async with TestingSessionLocal() as session:
            row = await session.get(Shipment, shipment_id)
            assert row.status == ShipmentStatus.CANCELLED.value
            assert never_attempted_create(row) is False
            await process_shipment_bookings(session)
            row = await session.get(Shipment, shipment_id)
            assert row.status == ShipmentStatus.CANCELLED.value
            assert fake_provider.create_calls == 0

    asyncio.run(check())


def test_cancel_creation_uncertain_found_parcel_uses_cancel_request(
    fake_provider, override_database, step_up_headers
):
    order_id, shipment_id, public_id = _seed_order_shipment(
        status=ShipmentStatus.CREATION_UNCERTAIN.value,
        booking_attempts=1,
        provider_data={"create_attempted": True},
    )
    fake_provider.parcels[public_id] = ParcelBooking(
        provider_parcel_no="1001",
        tracking_code="1234567890123",
        carrier_code="IR_POST",
        service_code="EXPRESS",
        provider_status="registered",
        raw={},
    )
    client = TestClient(app)
    res = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/cancel",
        json={"reason": "customer_request"},
        headers=step_up_headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "cancellation_pending"
    assert res.json()["status"] != "cancelled"
    assert fake_provider.cancel_calls == 1
    assert fake_provider.lookup_calls >= 1

    async def check():
        async with TestingSessionLocal() as session:
            row = await session.get(Shipment, shipment_id)
            assert row.status == ShipmentStatus.CANCELLATION_PENDING.value
            assert row.provider_parcel_no == "1001"
            assert row.cancelled_at is None

    asyncio.run(check())


def test_cancel_creation_uncertain_lookup_unavailable_never_local_cancelled(
    fake_provider, override_database, step_up_headers
):
    order_id, shipment_id, _ = _seed_order_shipment(
        status=ShipmentStatus.CREATION_UNCERTAIN.value,
        booking_attempts=1,
        provider_data={"create_attempted": True},
    )

    async def lookup_down(custom_order_no):
        fake_provider.lookup_calls += 1
        fake_provider.op_log.append("lookup")
        raise RuntimeError("lookup unavailable")

    fake_provider.lookup_by_custom_order_no = lookup_down
    client = TestClient(app)
    res = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/cancel",
        json={"reason": "customer_request"},
        headers=step_up_headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "cancellation_pending"
    assert fake_provider.cancel_calls == 0

    async def check():
        async with TestingSessionLocal() as session:
            row = await session.get(Shipment, shipment_id)
            assert row.status != ShipmentStatus.CANCELLED.value
            assert row.status == ShipmentStatus.CANCELLATION_PENDING.value
            assert (row.provider_data or {}).get("cancellation_lookup_inconclusive") is True

    asyncio.run(check())


def test_cancel_booking_after_crash_found_parcel_uses_cancel_request(
    fake_provider, override_database, step_up_headers
):
    order_id, shipment_id, public_id = _seed_order_shipment(
        status=ShipmentStatus.BOOKING.value,
        booking_attempts=1,
        provider_data={
            "create_attempted": True,
            "create_started_at": datetime.now(UTC).isoformat(),
        },
    )
    fake_provider.parcels[public_id] = ParcelBooking(
        provider_parcel_no="1001",
        tracking_code="1234567890123",
        carrier_code="IR_POST",
        service_code="EXPRESS",
        provider_status="registered",
        raw={},
    )
    client = TestClient(app)
    res = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/cancel",
        json={"reason": "customer_request"},
        headers=step_up_headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "cancellation_pending"
    assert fake_provider.cancel_calls == 1

    async def check():
        async with TestingSessionLocal() as session:
            row = await session.get(Shipment, shipment_id)
            assert row.status == ShipmentStatus.CANCELLATION_PENDING.value
            assert row.provider_parcel_no == "1001"
            assert row.cancelled_at is None
            await process_shipment_bookings(session)
            row = await session.get(Shipment, shipment_id)
            assert fake_provider.create_calls == 0
            assert row.status != ShipmentStatus.CANCELLED.value

    asyncio.run(check())


def test_false_local_cancel_cannot_leave_provider_parcel_unnoticed(
    fake_provider, override_database, step_up_headers
):
    order_id, shipment_id, public_id = _seed_order_shipment(
        status=ShipmentStatus.CREATION_UNCERTAIN.value,
        booking_attempts=1,
        provider_data={"create_attempted": True},
    )
    client = TestClient(app)
    res = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/cancel",
        json={"reason": "customer_request"},
        headers=step_up_headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] != "cancelled"
    assert res.json()["status"] == "cancellation_pending"

    fake_provider.parcels[public_id] = ParcelBooking(
        provider_parcel_no="1001",
        tracking_code="1234567890123",
        carrier_code="IR_POST",
        service_code="EXPRESS",
        provider_status="registered",
        raw={},
    )

    async def recover():
        async with TestingSessionLocal() as session:
            row = await session.get(Shipment, shipment_id)
            row.booking_next_attempt_at = datetime.now(UTC)
            await session.commit()
        async with TestingSessionLocal() as session:
            await process_shipment_bookings(session)
            row = await session.get(Shipment, shipment_id)
            assert row.status != ShipmentStatus.CANCELLED.value
            assert row.provider_parcel_no == "1001"
            assert fake_provider.cancel_calls == 1
            assert fake_provider.create_calls == 0
            assert row.status == ShipmentStatus.CANCELLATION_PENDING.value

    asyncio.run(recover())
