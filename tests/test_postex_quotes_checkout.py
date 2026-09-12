"""Quote persistence, checkout totals, and booking safety with a fake Postex provider."""

from decimal import Decimal

import pytest
from app.db.models.logistics import Shipment
from app.main import app
from app.services.logistics.models import (
    BoxType,
    ParcelBooking,
    ParcelLookup,
    QuoteResult,
)
from app.services.payment_flow_service import order_amount_rials
from fastapi.testclient import TestClient

from tests.conftest import customer_auth_headers
from tests.test_postex_logistics import QUOTE_FIXTURE, _enable_postex


class FakeProvider:
    provider_id = "postex"

    def __init__(self):
        self.create_calls = 0
        self.lookup_calls = 0
        self.cancel_calls = 0
        self.ready_calls = 0
        self.update_calls = 0
        self.label_calls = 0
        self.whoami_calls = 0
        self.parcels: dict[str, ParcelBooking] = {}
        self.op_log: list[str] = []
        self.tracking: list = []

    async def list_boxes(self):
        return [BoxType(id=1, name="M", length_cm=40, width_cm=30, height_cm=20)]

    async def list_cities(self):
        from app.services.logistics.models import LocationCity

        return [LocationCity(code=8, name="تهران", province_code=1, province_name="تهران")]

    async def quote(self, **kwargs):
        from app.services.logistics.postex.mapper import parse_quotes

        parsed = parse_quotes(QUOTE_FIXTURE)
        return QuoteResult(
            options=parsed.options,
            package=kwargs["package"],
            declared_value_irr=kwargs["declared_value_irr"],
            raw_provider_response=QUOTE_FIXTURE,
            pickup_amount_toman=parsed.pickup_amount_toman,
        )

    async def create_parcel(self, request):
        self.create_calls += 1
        self.op_log.append("create")
        booking = ParcelBooking(
            provider_parcel_no="1001",
            tracking_code="1234567890123",
            carrier_code="IR_POST",
            service_code="EXPRESS",
            provider_status="registered",
            raw={
                "data": {
                    "shipments": [{"tracking": {"barcode": "1234567890123"}, "parcel_no": 1001}]
                }
            },
        )
        custom = request["parcels"][0]["custom_order_no"]
        self.parcels[custom] = booking
        return booking

    async def lookup_by_custom_order_no(self, custom_order_no):
        self.lookup_calls += 1
        self.op_log.append("lookup")
        booking = self.parcels.get(custom_order_no)
        if booking:
            return ParcelLookup(found=True, booking=booking)
        return ParcelLookup(found=False)

    async def fetch_label_pdf(self, parcel_no):
        self.label_calls += 1
        return b"%PDF-1.4 test-label"

    async def mark_ready(self, parcel_nos):
        self.ready_calls += 1
        return {"ok": True}

    async def cancel_parcel(self, parcel_no, reason):
        self.cancel_calls += 1
        return {"ok": True}

    async def update_parcel(self, parcel_no, body):
        self.update_calls += 1
        return {"ok": True}

    async def tracking_events(self, parcel_no):
        return list(self.tracking)

    async def whoami(self):
        self.whoami_calls += 1
        return {"id": 1}


@pytest.fixture
def fake_provider(monkeypatch):
    _enable_postex(monkeypatch)
    provider = FakeProvider()
    monkeypatch.setattr("app.services.logistics.service.get_provider", lambda: provider)
    monkeypatch.setattr("app.services.logistics.booking_worker.get_provider", lambda: provider)
    monkeypatch.setattr("app.services.logistics.tracking_worker.get_provider", lambda: provider)
    monkeypatch.setattr("app.api.endpoints.shipping.get_provider", lambda: provider)
    return provider


def _seed_parcel_product(client, super_admin_headers, sku="PARCEL-1"):
    payload = {
        "sku": sku,
        "name": "Parcel Tool",
        "category_id": 3,
        "brand_id": 1,
        "base_price": "100000",
        "is_available": True,
        "stock_unit": "piece",
        "is_active": True,
        "tax_percent": "0",
        "weight_grams": "250",
        "package_length_cm": "10",
        "package_width_cm": "8",
        "package_height_cm": "4",
        "shipping_class": "parcel",
        "shipping_is_fragile": False,
        "shipping_is_liquid": False,
    }
    created = client.post("/api/v1/products/", json=payload, headers=super_admin_headers)
    assert created.status_code == 201, created.text
    return created.json()


def test_incomplete_shipping_data(fake_provider, override_database, super_admin_headers):
    client = TestClient(app)
    payload = {
        "sku": "NO-DIM",
        "name": "No Dims",
        "category_id": 3,
        "brand_id": 1,
        "base_price": "1000",
        "is_available": True,
        "stock_unit": "piece",
        "is_active": True,
        "weight_grams": "100",
    }
    created = client.post("/api/v1/products/", json=payload, headers=super_admin_headers)
    assert created.status_code == 201
    headers = customer_auth_headers()
    res = client.post(
        "/api/v1/shipping/quotes",
        json={
            "items": [{"product_id": created.json()["id"], "quantity": 1}],
            "location_code": 8,
        },
        headers=headers,
    )
    assert res.status_code == 422
    assert res.json()["error_code"] == "SHIPPING_DATA_INCOMPLETE"


def test_quote_and_checkout_includes_shipping_once(
    fake_provider, override_database, super_admin_headers
):
    client = TestClient(app)
    product = _seed_parcel_product(client, super_admin_headers)
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
    options = quote.json()["options"]
    assert len(options) == 2
    chosen = next(o for o in options if o["service_code"] == "EXPRESS")
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
            "shipping_quote_token": chosen["quote_token"],
        },
        headers={**headers, "Idempotency-Key": "ship-once"},
    )
    assert checkout.status_code == 201, checkout.text
    body = checkout.json()
    # items 100000 + tax 0 + shipping 17000
    assert Decimal(body["estimated_total"]) == Decimal("117000.00")
    replay = client.post(
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
            "shipping_quote_token": chosen["quote_token"],
        },
        headers={**headers, "Idempotency-Key": "ship-once-2"},
    )
    assert replay.status_code == 409
    assert replay.json()["error_code"] == "SHIPPING_QUOTE_CONSUMED"

    from app.db.models.commerce import Order

    from tests.conftest import TestingSessionLocal

    async def _sep_amount():
        async with TestingSessionLocal() as session:
            order = (
                (await session.execute(select(Order).order_by(Order.id.desc()))).scalars().first()
            )
            assert order is not None
            assert order.shipping_customer_cost == Decimal("17000.00")
            assert order.shipping_provider_quoted_cost == Decimal("17000.00")
            assert order.shipping_provider_quoted_cost != Decimal("15000.00")
            assert order_amount_rials(order) == 1_170_000

    import asyncio

    from sqlalchemy import select

    asyncio.run(_sep_amount())


def test_quote_destination_mismatch(
    fake_provider, override_database, super_admin_headers, monkeypatch
):
    from app.services.logistics.models import LocationCity
    from app.services.logistics.service import clear_reference_caches

    async def two_valid_cities():
        return [
            LocationCity(code=8, name="تهران", province_code=1, province_name="تهران"),
            LocationCity(code=12, name="اصفهان", province_code=2, province_name="اصفهان"),
        ]

    monkeypatch.setattr(fake_provider, "list_cities", two_valid_cities)
    clear_reference_caches()
    client = TestClient(app)
    product = _seed_parcel_product(client, super_admin_headers, sku="PARCEL-DEST")
    headers = customer_auth_headers()
    quote = client.post(
        "/api/v1/shipping/quotes",
        json={"items": [{"product_id": product["id"], "quantity": 1}], "location_code": 8},
        headers=headers,
    )
    token = quote.json()["options"][0]["quote_token"]
    checkout = client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {"full_name": "علی تست", "phone": "09123333333", "is_guest": False},
            "items": [{"product_id": product["id"], "quantity": 1}],
            "shipping": {
                "province": "اصفهان",
                "city": "اصفهان",
                "postal_code": "1234567890",
                "address_line": "خیابان آزادی پلاک ۱۲۳۴",
                "location_code": 12,
            },
            "shipping_quote_token": token,
        },
        headers={**headers, "Idempotency-Key": "dest-mismatch"},
    )
    assert checkout.status_code == 409
    assert checkout.json()["error_code"] == "SHIPPING_QUOTE_MISMATCH"


def test_quote_ownership_mismatch(fake_provider, override_database, super_admin_headers):
    client = TestClient(app)
    product = _seed_parcel_product(client, super_admin_headers, sku="PARCEL-OWNER")
    owner = customer_auth_headers("09123333333")
    other = customer_auth_headers("09124444444")
    quote = client.post(
        "/api/v1/shipping/quotes",
        json={"items": [{"product_id": product["id"], "quantity": 1}], "location_code": 8},
        headers=owner,
    )
    assert quote.status_code == 200, quote.text
    token = quote.json()["options"][0]["quote_token"]
    checkout = client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {"full_name": "علی تست", "phone": "09124444444", "is_guest": False},
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
        headers={**other, "Idempotency-Key": "owner-mismatch"},
    )
    assert checkout.status_code == 409
    assert checkout.json()["error_code"] == "SHIPPING_QUOTE_MISMATCH"


def test_quote_cart_fingerprint_mismatch(fake_provider, override_database, super_admin_headers):
    client = TestClient(app)
    product = _seed_parcel_product(client, super_admin_headers, sku="PARCEL-CART")
    headers = customer_auth_headers()
    quote = client.post(
        "/api/v1/shipping/quotes",
        json={"items": [{"product_id": product["id"], "quantity": 1}], "location_code": 8},
        headers=headers,
    )
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
        headers={**headers, "Idempotency-Key": "cart-mismatch"},
    )
    assert checkout.status_code == 409
    assert checkout.json()["error_code"] == "SHIPPING_QUOTE_MISMATCH"


def test_quote_ttl_expiry(fake_provider, override_database, super_admin_headers):
    from datetime import UTC, datetime, timedelta

    from app.db.models.logistics import ShippingQuote
    from sqlalchemy import select

    from tests.conftest import TestingSessionLocal

    client = TestClient(app)
    product = _seed_parcel_product(client, super_admin_headers, sku="PARCEL-TTL")
    headers = customer_auth_headers()
    quote = client.post(
        "/api/v1/shipping/quotes",
        json={"items": [{"product_id": product["id"], "quantity": 1}], "location_code": 8},
        headers=headers,
    )
    token = quote.json()["options"][0]["quote_token"]

    import asyncio

    async def expire():
        async with TestingSessionLocal() as session:
            rows = (await session.execute(select(ShippingQuote))).scalars().all()
            for row in rows:
                row.expires_at = datetime.now(UTC) - timedelta(seconds=5)
            await session.commit()

    asyncio.run(expire())
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
        headers={**headers, "Idempotency-Key": "ttl-expired"},
    )
    assert checkout.status_code == 409
    assert checkout.json()["error_code"] == "SHIPPING_QUOTE_EXPIRED"


def test_freight_only_quote(fake_provider, override_database, super_admin_headers):
    client = TestClient(app)
    payload = {
        "sku": "FREIGHT-1",
        "name": "Heavy Tool",
        "category_id": 3,
        "brand_id": 1,
        "base_price": "1000",
        "is_available": True,
        "stock_unit": "piece",
        "is_active": True,
        "weight_grams": "100",
        "package_length_cm": "10",
        "package_width_cm": "8",
        "package_height_cm": "4",
        "shipping_class": "freight_only",
    }
    created = client.post("/api/v1/products/", json=payload, headers=super_admin_headers)
    assert created.status_code == 201
    res = client.post(
        "/api/v1/shipping/quotes",
        json={"items": [{"product_id": created.json()["id"], "quantity": 1}], "location_code": 8},
        headers=customer_auth_headers(),
    )
    assert res.status_code == 422
    assert res.json()["error_code"] == "SHIPPING_FREIGHT_REQUIRED"


def test_quote_provider_outage(fake_provider, override_database, super_admin_headers):
    from app.services.logistics.exceptions import ShippingUnavailableError

    async def boom(**kwargs):
        raise ShippingUnavailableError("down")

    fake_provider.quote = boom
    client = TestClient(app)
    product = _seed_parcel_product(client, super_admin_headers, sku="PARCEL-OUT")
    res = client.post(
        "/api/v1/shipping/quotes",
        json={"items": [{"product_id": product["id"], "quantity": 1}], "location_code": 8},
        headers=customer_auth_headers(),
    )
    assert res.status_code == 503
    assert res.json()["error_code"] == "SHIPPING_UNAVAILABLE"


def test_cities_normalized(fake_provider, override_database):
    client = TestClient(app)
    res = client.get("/api/v1/shipping/cities", headers=customer_auth_headers())
    assert res.status_code == 200
    assert res.json()["data"][0]["code"] == 8
    assert "x-api-key" not in str(res.json()).lower()


def test_ready_ignores_postex(monkeypatch, override_database):
    """Postex must not be a readiness dependency; core /ready stays DB+Redis only."""

    async def _ok() -> bool:
        return True

    monkeypatch.setattr("app.main.check_database_connection", _ok)
    monkeypatch.setattr("app.main.ping_redis", _ok)
    _enable_postex(monkeypatch)
    client = TestClient(app)
    res = client.get("/ready")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"


def test_booking_timeout_does_not_double_create(fake_provider, override_database):
    import asyncio
    from datetime import UTC, datetime
    from uuid import uuid4

    from app.db.models.commerce import Order, OrderMode, OrderStatus, PaymentStatus
    from app.services.logistics.booking_worker import process_shipment_bookings
    from app.services.logistics.exceptions import ProviderTimeoutError
    from app.services.logistics.models import ShipmentStatus

    from tests.conftest import TestingSessionLocal

    async def body():
        async def timeout_create(request):
            fake_provider.create_calls += 1
            raise ProviderTimeoutError("timeout", ambiguous_write=True)

        fake_provider.create_parcel = timeout_create

        async with TestingSessionLocal() as session:
            order = Order(
                tracking_code="KZ-TEST-BOOK",
                mode=OrderMode.PURCHASE,
                status=OrderStatus.PAID.value,
                payment_status=PaymentStatus.PAID.value,
                estimated_total=Decimal("117000"),
                customer_full_name="علی تست",
                customer_phone="09123333333",
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
                booking_next_attempt_at=datetime.now(UTC),
                provider_data={"package": {"box_type_id": 1}},
            )
            session.add(shipment)
            await session.commit()
            shipment_id = shipment.id
            public_id = shipment.public_id

        async with TestingSessionLocal() as session:
            await process_shipment_bookings(session)
            await session.commit()
            row = await session.get(Shipment, shipment_id)
            assert row.status == ShipmentStatus.CREATION_UNCERTAIN.value
            assert fake_provider.create_calls == 1
            row.booking_next_attempt_at = datetime.now(UTC)
            await session.commit()

        async def success_create(request):
            return await FakeProvider.create_parcel(fake_provider, request)

        fake_provider.create_parcel = success_create
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
            assert row.status == ShipmentStatus.BOOKED.value
            assert fake_provider.create_calls == 2
            assert public_id in fake_provider.parcels

    asyncio.run(body())


def test_admin_label_pdf(fake_provider, override_database, super_admin_headers):
    import asyncio
    from uuid import uuid4

    from app.db.models.commerce import Order, OrderMode, OrderStatus, PaymentStatus
    from app.services.logistics.models import ShipmentStatus

    from tests.conftest import TestingSessionLocal

    async def seed():
        async with TestingSessionLocal() as session:
            order = Order(
                tracking_code="KZ-LABEL",
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
            await session.commit()
            return order.id, shipment.id

    order_id, shipment_id = asyncio.run(seed())
    client = TestClient(app)
    res = client.get(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/label",
        headers=super_admin_headers,
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/pdf")
    assert res.content.startswith(b"%PDF")
    assert fake_provider.label_calls == 1


def test_admin_cancel_requires_step_up_and_cancels(
    fake_provider, override_database, step_up_headers
):
    import asyncio
    from uuid import uuid4

    from app.db.models.commerce import Order, OrderMode, OrderStatus, PaymentStatus
    from app.services.logistics.models import ShipmentStatus

    from tests.conftest import TestingSessionLocal

    async def seed():
        async with TestingSessionLocal() as session:
            order = Order(
                tracking_code="KZ-CANCEL",
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
            await session.commit()
            return order.id, shipment.id

    order_id, shipment_id = asyncio.run(seed())
    client = TestClient(app)
    denied = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/cancel",
        json={"reason": "customer_request"},
        headers={k: v for k, v in step_up_headers.items() if k != "X-Step-Up-Token"},
    )
    assert denied.status_code == 403
    res = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/cancel",
        json={"reason": "customer_request"},
        headers=step_up_headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "cancellation_pending"
    assert fake_provider.cancel_calls == 1


def test_ensure_shipment_not_duplicate(fake_provider, override_database):
    import asyncio

    from app.db.models.commerce import Order, OrderMode, OrderStatus, PaymentStatus
    from app.services.logistics.service import ensure_shipment_for_paid_order

    from tests.conftest import TestingSessionLocal

    async def run():
        async with TestingSessionLocal() as session:
            order = Order(
                tracking_code="KZ-DUP",
                mode=OrderMode.PURCHASE,
                status=OrderStatus.PAID.value,
                payment_status=PaymentStatus.PAID.value,
                customer_full_name="علی تست",
                customer_phone="09123333333",
                shipping_provider="postex",
            )
            session.add(order)
            await session.flush()
            first = await ensure_shipment_for_paid_order(session, order)
            second = await ensure_shipment_for_paid_order(session, order)
            await session.commit()
            assert first.id == second.id
            rows = (
                (await session.execute(select(Shipment).where(Shipment.order_id == order.id)))
                .scalars()
                .all()
            )
            assert len(rows) == 1

    from sqlalchemy import select

    asyncio.run(run())


def test_live_quote_provider_total_includes_pickup_on_order_and_shipment(
    fake_provider, override_database, super_admin_headers, monkeypatch
):
    """Live fixture: service 129800 + pickup 120000 = provider total 249800 Toman."""
    import asyncio
    import json
    from pathlib import Path

    from app.db.models.commerce import Order, OrderStatus, PaymentStatus
    from app.services.logistics.models import QuoteResult
    from app.services.logistics.postex.mapper import parse_quotes
    from app.services.logistics.service import ensure_shipment_for_paid_order
    from sqlalchemy import select

    from tests.conftest import TestingSessionLocal

    live = json.loads(
        (
            Path(__file__).resolve().parent / "fixtures/postex/live-quote-2026-09-10.json"
        ).read_text(encoding="utf-8")
    )

    async def _quote(**kwargs):
        parsed = parse_quotes(live)
        return QuoteResult(
            options=parsed.options,
            package=kwargs["package"],
            declared_value_irr=kwargs["declared_value_irr"],
            raw_provider_response=live,
            pickup_amount_toman=parsed.pickup_amount_toman,
        )

    monkeypatch.setattr(fake_provider, "quote", _quote)

    client = TestClient(app)
    product = _seed_parcel_product(client, super_admin_headers, sku="LIVE-PICKUP-1")
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
    options = quote.json()["options"]
    assert len(options) == 1
    chosen = options[0]
    assert Decimal(chosen["amount_toman"]) == Decimal("249800.00")

    checkout = client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {"full_name": "علی تست", "phone": "09125555555", "is_guest": False},
            "items": [{"product_id": product["id"], "quantity": 1}],
            "shipping": {
                "province": "تهران",
                "city": "تهران",
                "postal_code": "1234567890",
                "address_line": "خیابان آزادی پلاک ۱۲۳۴",
                "location_code": 8,
            },
            "shipping_quote_token": chosen["quote_token"],
        },
        headers={**headers, "Idempotency-Key": "live-pickup-total"},
    )
    assert checkout.status_code == 201, checkout.text
    body = checkout.json()
    # items 100000 + tax 0 + shipping 249800 — SEP/customer total unchanged by this fix
    assert Decimal(body["estimated_total"]) == Decimal("349800.00")

    async def _assert_snapshots():
        async with TestingSessionLocal() as session:
            order = (
                (await session.execute(select(Order).order_by(Order.id.desc()))).scalars().first()
            )
            assert order is not None
            assert order.shipping_customer_cost == Decimal("249800.00")
            assert order.shipping_provider_quoted_cost == Decimal("249800.00")
            # Prove provider total is not the service-only component
            assert order.shipping_provider_quoted_cost != Decimal("129800.00")
            assert order_amount_rials(order) == 3_498_000

            order.status = OrderStatus.PAID.value
            order.payment_status = PaymentStatus.PAID.value
            await session.flush()
            shipment = await ensure_shipment_for_paid_order(session, order)
            await session.commit()
            assert shipment.provider_quoted_cost == Decimal("249800.00")
            assert shipment.customer_shipping_cost == Decimal("249800.00")

    asyncio.run(_assert_snapshots())
