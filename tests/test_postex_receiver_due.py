"""Postex receiver-paid (پس‌کرایه) checkout, packing, and booking regressions."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from app.core.config import Settings, settings
from app.db.models.commerce import Order, OrderMode, OrderStatus, PaymentStatus
from app.db.models.logistics import Shipment
from app.main import app
from app.services.logistics.booking_worker import process_shipment_bookings
from app.services.logistics.models import ShipmentStatus
from app.services.logistics.service import (
    build_parcel_create_request,
    clear_reference_caches,
    ensure_shipment_for_paid_order,
)
from app.services.logistics.shipping_payment import (
    ShippingPaymentMode,
    mode_from_postex_payment_type,
    normalize_postex_payment_type,
    postex_payment_type_for_mode,
)
from app.services.payment_flow_service import order_amount_rials
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from tests.conftest import TestingSessionLocal, customer_auth_headers
from tests.test_postex_logistics import _enable_postex
from tests.test_postex_quotes_checkout import FakeProvider, _seed_parcel_product


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


def _settings(**overrides) -> Settings:
    values = {
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_SERVER": "localhost",
        "POSTGRES_DB": "test",
        "SECRET_KEY": "test-secret-key-with-at-least-32-characters",
        "ADMIN_STEP_UP_PIN": "93827461",
        "DEBUG": True,
        "REDIS_HOST": None,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _seed_product_without_logistics(
    client: TestClient,
    super_admin_headers: dict[str, str],
    *,
    sku: str = "RECEIVER-NO-DIMS",
    tax_percent: str = "10",
) -> dict:
    response = client.post(
        "/api/v1/products/",
        json={
            "sku": sku,
            "name": "Receiver Paid Tool",
            "category_id": 3,
            "brand_id": 1,
            "base_price": "100000",
            "tax_percent": tax_percent,
            "is_available": True,
            "stock_unit": "piece",
            "is_active": True,
        },
        headers=super_admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _purchase_payload(product_id: int, **overrides) -> dict:
    payload = {
        "mode": "purchase",
        "customer": {
            "full_name": "علی تست",
            "phone": "09123333333",
            "is_guest": False,
        },
        "items": [{"product_id": product_id, "quantity": 1}],
        "shipping": {
            "province": "تهران",
            "city": "تهران",
            "postal_code": "1234567890",
            "address_line": "خیابان آزادی پلاک ۱۲۳۴",
            "location_code": 8,
        },
    }
    payload.update(overrides)
    return payload


def _receiver_checkout(
    client: TestClient,
    super_admin_headers: dict[str, str],
    *,
    key: str,
    sku: str,
) -> dict:
    product = _seed_product_without_logistics(client, super_admin_headers, sku=sku)
    response = client.post(
        "/api/v1/checkout",
        json=_purchase_payload(product["id"]),
        headers={
            **customer_auth_headers(),
            "Idempotency-Key": key,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _ensure_paid_receiver_shipment(order_id: int) -> tuple[int, int]:
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


def _prepare_receiver_booking(
    client: TestClient,
    super_admin_headers: dict[str, str],
    *,
    key: str,
    sku: str,
) -> tuple[int, int, Decimal]:
    checkout = _receiver_checkout(
        client,
        super_admin_headers,
        key=key,
        sku=sku,
    )
    order_id, shipment_id = _ensure_paid_receiver_shipment(checkout["order_id"])
    original_total = Decimal(checkout["estimated_total"])

    package = client.post(
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
    assert package.status_code == 200, package.text
    quote = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/packed-quote",
        headers=super_admin_headers,
    )
    assert quote.status_code == 200, quote.text
    assert Decimal(quote.json()["order_estimated_total_unchanged"]) == original_total
    selected = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/select-service",
        json={"carrier_code": "IR_POST", "service_code": "EXPRESS"},
        headers=super_admin_headers,
    )
    assert selected.status_code == 200, selected.text
    prepared = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/schedule-booking",
        headers=super_admin_headers,
    )
    assert prepared.status_code == 200, prepared.text
    assert prepared.json()["status"] == ShipmentStatus.READY_TO_BOOK.value
    return order_id, shipment_id, original_total

def _seed_worker_shipment(*, status: str, complete: bool) -> tuple[int, int]:
    async def seed() -> tuple[int, int]:
        async with TestingSessionLocal() as session:
            order = Order(
                tracking_code=f"KZ-RCV-{uuid4().hex[:10]}",
                mode=OrderMode.PURCHASE,
                status=OrderStatus.PAID.value,
                payment_status=PaymentStatus.PAID.value,
                estimated_total=Decimal("100000"),
                customer_full_name="علی تست",
                customer_phone="09123333333",
                shipping={
                    "location_code": 8,
                    "city": "تهران",
                    "postal_code": "1234567890",
                    "address_line": "خیابان تست پلاک ۱۲",
                },
                shipping_provider="postex",
                shipping_payment_mode=ShippingPaymentMode.RECEIVER_DUE.value,
            )
            session.add(order)
            await session.flush()
            shipment = Shipment(
                public_id=str(uuid4()),
                order_id=order.id,
                provider="postex",
                status=status,
                shipping_payment_mode=ShippingPaymentMode.RECEIVER_DUE.value,
                booking_next_attempt_at=datetime.now(UTC),
                provider_data={"payment_mode": ShippingPaymentMode.RECEIVER_DUE.value},
            )
            if complete:
                shipment.package_length_cm = 10
                shipment.package_width_cm = 8
                shipment.package_height_cm = 4
                shipment.package_weight_grams = 250
                shipment.package_is_fragile = False
                shipment.package_is_liquid = False
                shipment.provider_box_type_id = 1
                shipment.declared_value_irr = Decimal("1000000")
                shipment.carrier_code = "IR_POST"
                shipment.service_code = "EXPRESS"
                shipment.provider_data = {
                    "payment_mode": ShippingPaymentMode.RECEIVER_DUE.value,
                    "package": {"box_type_id": 1},
                }
            session.add(shipment)
            await session.commit()
            return order.id, shipment.id

    return asyncio.run(seed())


def test_payment_type_normalization_and_domain_mapping():
    assert normalize_postex_payment_type(" sender ") == "SENDER"
    assert normalize_postex_payment_type("receiver") == "RECEIVER"
    assert mode_from_postex_payment_type("SENDER") == ShippingPaymentMode.SENDER_PREPAID
    assert mode_from_postex_payment_type(" receiver ") == ShippingPaymentMode.RECEIVER_DUE
    assert postex_payment_type_for_mode("sender_prepaid") == "SENDER"
    assert postex_payment_type_for_mode(ShippingPaymentMode.RECEIVER_DUE) == "RECEIVER"


@pytest.mark.parametrize("payment_type", ["COD", "cod", "FREE_SHIPPING", "", "unknown"])
def test_cod_free_shipping_and_unknown_payment_types_are_rejected(payment_type):
    with pytest.raises(ValueError, match="payment_type"):
        normalize_postex_payment_type(payment_type)
    with pytest.raises(ValidationError):
        _settings(POSTEX_DEFAULT_PAYMENT_TYPE=payment_type)


def test_settings_normalize_modes_and_keep_booking_safe_off():
    sender = _settings(POSTEX_DEFAULT_PAYMENT_TYPE=" sender ")
    receiver = _settings(
        POSTEX_DEFAULT_PAYMENT_TYPE="RECEIVER",
        POSTEX_SHIPPING_PAYMENT_MODE=" RECEIVER_DUE ",
    )
    assert sender.POSTEX_DEFAULT_PAYMENT_TYPE == "SENDER"
    assert sender.POSTEX_SHIPPING_PAYMENT_MODE == ""
    assert sender.POSTEX_BOOKING_ENABLED is False
    assert receiver.POSTEX_DEFAULT_PAYMENT_TYPE == "RECEIVER"
    assert receiver.POSTEX_SHIPPING_PAYMENT_MODE == "receiver_due"
    with pytest.raises(ValidationError, match="POSTEX_SHIPPING_PAYMENT_MODE"):
        _settings(POSTEX_SHIPPING_PAYMENT_MODE="cod")


def test_shipping_status_exposes_receiver_due_contract(fake_provider, override_database):
    response = TestClient(app).get("/api/v1/shipping/status")
    assert response.status_code == 200, response.text
    assert response.json() == {
        "enabled": True,
        "quote_ttl_seconds": settings.POSTEX_QUOTE_TTL_SECONDS,
        "shipping_payment_mode": "receiver_due",
        "checkout_quote_required": False,
        "booking_enabled": False,
    }


def test_receiver_checkout_needs_no_quote_or_product_logistics_and_excludes_shipping(
    fake_provider,
    override_database,
    super_admin_headers,
):
    client = TestClient(app)
    checkout = _receiver_checkout(
        client,
        super_admin_headers,
        key="receiver-money",
        sku="RECEIVER-MONEY",
    )
    assert Decimal(checkout["estimated_total"]) == Decimal("110000.00")
    assert checkout["shipping_payment_mode"] == "receiver_due"
    assert checkout["shipping_display"] == "receiver_due"
    assert fake_provider.quote_requests == []

    async def check() -> None:
        async with TestingSessionLocal() as session:
            order = await session.get(Order, checkout["order_id"])
            assert order is not None
            assert order.shipping_payment_mode == ShippingPaymentMode.RECEIVER_DUE.value
            assert order.shipping_quote_id is None
            assert order.shipping_customer_cost is None
            assert order.shipping_provider_quoted_cost is None
            assert order.shipping_carrier_code is None
            assert order.shipping_service_code is None
            assert order_amount_rials(order) == 1_100_000

    asyncio.run(check())


def test_receiver_checkout_rejects_unknown_positive_location_code(
    fake_provider,
    override_database,
    super_admin_headers,
):
    client = TestClient(app)
    product = _seed_product_without_logistics(
        client,
        super_admin_headers,
        sku="RECEIVER-BAD-CODE",
    )
    payload = _purchase_payload(product["id"])
    payload["shipping"]["location_code"] = 99
    response = client.post(
        "/api/v1/checkout",
        json=payload,
        headers={**customer_auth_headers(), "Idempotency-Key": "receiver-bad-code"},
    )
    assert response.status_code == 409
    assert response.json()["error_code"] == "SHIPPING_DESTINATION_INVALID"
    assert fake_provider.quote_requests == []
    assert fake_provider.create_calls == 0


def test_receiver_checkout_rejects_fake_city_text_with_invalid_code(
    fake_provider,
    override_database,
    super_admin_headers,
):
    client = TestClient(app)
    product = _seed_product_without_logistics(
        client,
        super_admin_headers,
        sku="RECEIVER-FAKE-CITY",
    )
    response = client.post(
        "/api/v1/checkout",
        json=_purchase_payload(
            product["id"],
            shipping={
                "province": "تهران",
                "city": "تهران",
                "postal_code": "1234567890",
                "address_line": "خیابان آزادی پلاک ۱۲۳۴",
                "location_code": 4242,
            },
        ),
        headers={**customer_auth_headers(), "Idempotency-Key": "receiver-fake-city"},
    )
    assert response.status_code == 409
    assert response.json()["error_code"] == "SHIPPING_DESTINATION_INVALID"


def test_receiver_checkout_city_reference_lookup_failure_fails_closed(
    fake_provider,
    override_database,
    super_admin_headers,
    monkeypatch,
):
    clear_reference_caches()

    async def boom(_provider):
        raise RuntimeError("city cache unavailable")

    monkeypatch.setattr("app.services.logistics.service._cached_cities", boom)
    client = TestClient(app)
    product = _seed_product_without_logistics(
        client,
        super_admin_headers,
        sku="RECEIVER-CITY-DOWN",
    )
    response = client.post(
        "/api/v1/checkout",
        json=_purchase_payload(product["id"]),
        headers={**customer_auth_headers(), "Idempotency-Key": "receiver-city-down"},
    )
    assert response.status_code == 409
    assert response.json()["error_code"] == "SHIPPING_DESTINATION_INVALID"
    assert fake_provider.create_calls == 0


def test_packed_quote_rejects_missing_width_before_provider_http(
    fake_provider,
    override_database,
    super_admin_headers,
):
    client = TestClient(app)
    checkout = _receiver_checkout(
        client,
        super_admin_headers,
        key="packed-missing-width",
        sku="PACKED-MISS-WIDTH",
    )
    order_id, shipment_id = _ensure_paid_receiver_shipment(checkout["order_id"])

    async def set_partial_package() -> None:
        async with TestingSessionLocal() as session:
            shipment = await session.get(Shipment, shipment_id)
            assert shipment is not None
            shipment.package_length_cm = 10
            shipment.package_width_cm = None
            shipment.package_height_cm = 4
            shipment.package_weight_grams = 250
            shipment.package_is_fragile = False
            shipment.package_is_liquid = False
            await session.commit()

    asyncio.run(set_partial_package())
    quote = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/packed-quote",
        headers=super_admin_headers,
    )
    assert quote.status_code == 422
    assert quote.json()["error_code"] == "SHIPPING_DATA_INCOMPLETE"
    assert fake_provider.quote_requests == []


def test_receiver_checkout_requires_location_code_and_has_no_cod_path(
    fake_provider,
    override_database,
    super_admin_headers,
):
    client = TestClient(app)
    product = _seed_product_without_logistics(
        client,
        super_admin_headers,
        sku="RECEIVER-LOCATION",
    )
    missing_location = _purchase_payload(product["id"])
    missing_location["shipping"]["location_code"] = None
    response = client.post(
        "/api/v1/checkout",
        json=missing_location,
        headers={**customer_auth_headers(), "Idempotency-Key": "receiver-no-location"},
    )
    assert response.status_code == 409
    assert response.json()["error_code"] == "SHIPPING_QUOTE_MISMATCH"

    forbidden_mode = client.post(
        "/api/v1/checkout",
        json=_purchase_payload(product["id"], shipping_payment_mode="receiver_due"),
        headers={**customer_auth_headers(), "Idempotency-Key": "receiver-forbid-mode"},
    )
    assert forbidden_mode.status_code == 422

    cod = client.post(
        "/api/v1/checkout",
        json=_purchase_payload(product["id"], shipping_payment_mode="cod"),
        headers={**customer_auth_headers(), "Idempotency-Key": "receiver-cod"},
    )
    assert cod.status_code == 422


def test_client_cannot_bypass_sender_prepaid_with_receiver_due_field(
    fake_provider,
    override_database,
    super_admin_headers,
    monkeypatch,
):
    monkeypatch.setattr(settings, "POSTEX_SHIPPING_PAYMENT_MODE", "sender_prepaid")
    client = TestClient(app)
    product = _seed_parcel_product(client, super_admin_headers, sku="BYPASS-MODE")
    # extra="forbid" rejects client authority field entirely.
    blocked = client.post(
        "/api/v1/checkout",
        json=_purchase_payload(product["id"], shipping_payment_mode="receiver_due"),
        headers={**customer_auth_headers(), "Idempotency-Key": "bypass-mode"},
    )
    assert blocked.status_code == 422

    # Without quote, sender_prepaid still requires shipping charge path.
    no_quote = client.post(
        "/api/v1/checkout",
        json=_purchase_payload(product["id"]),
        headers={**customer_auth_headers(), "Idempotency-Key": "sender-needs-quote"},
    )
    assert no_quote.status_code in {400, 422}
    assert no_quote.json()["error_code"] == "SHIPPING_QUOTE_REQUIRED"


def test_client_cannot_force_sender_prepaid_when_server_is_receiver_due(
    fake_provider,
    override_database,
    super_admin_headers,
):
    client = TestClient(app)
    product = _seed_product_without_logistics(
        client, super_admin_headers, sku="FORCE-SENDER"
    )
    response = client.post(
        "/api/v1/checkout",
        json=_purchase_payload(product["id"], shipping_payment_mode="sender_prepaid"),
        headers={**customer_auth_headers(), "Idempotency-Key": "force-sender"},
    )
    assert response.status_code == 422


def test_sender_prepaid_checkout_still_adds_shipping_once(
    fake_provider,
    override_database,
    super_admin_headers,
    monkeypatch,
):
    monkeypatch.setattr(settings, "POSTEX_SHIPPING_PAYMENT_MODE", "sender_prepaid")
    client = TestClient(app)
    product = _seed_parcel_product(client, super_admin_headers, sku="SENDER-MONEY")
    headers = customer_auth_headers()
    quote = client.post(
        "/api/v1/shipping/quotes",
        json={
            "items": [{"product_id": product["id"], "quantity": 1}],
            "location_code": 8,
            "postal_code": "1234567890",
            "city_name": "تهران",
            "province_name": "تهران",
        },
        headers=headers,
    )
    assert quote.status_code == 200, quote.text
    token = next(
        option["quote_token"]
        for option in quote.json()["options"]
        if option["service_code"] == "EXPRESS"
    )
    checkout = client.post(
        "/api/v1/checkout",
        json=_purchase_payload(
            product["id"],
            shipping_quote_token=token,
        ),
        headers={**headers, "Idempotency-Key": "sender-money"},
    )
    assert checkout.status_code == 201, checkout.text
    assert Decimal(checkout.json()["estimated_total"]) == Decimal("117000.00")
    assert checkout.json()["shipping_display"] == "prepaid"
    assert fake_provider.quote_requests[-1]["payment_type"] == "SENDER"

    async def check() -> None:
        async with TestingSessionLocal() as session:
            order = await session.get(Order, checkout.json()["order_id"])
            assert order is not None
            assert order.shipping_customer_cost == Decimal("17000.00")
            assert order.shipping_provider_quoted_cost == Decimal("17000.00")
            assert order_amount_rials(order) == 1_170_000

    asyncio.run(check())

def test_paid_receiver_order_waits_for_packaging_without_booking_schedule(
    fake_provider,
    override_database,
    super_admin_headers,
):
    checkout = _receiver_checkout(
        TestClient(app),
        super_admin_headers,
        key="receiver-paid",
        sku="RECEIVER-PAID",
    )
    _, shipment_id = _ensure_paid_receiver_shipment(checkout["order_id"])

    async def check() -> None:
        async with TestingSessionLocal() as session:
            shipment = await session.get(Shipment, shipment_id)
            assert shipment is not None
            assert shipment.status == ShipmentStatus.AWAITING_PACKAGING.value
            assert shipment.shipping_payment_mode == ShippingPaymentMode.RECEIVER_DUE.value
            assert shipment.booking_next_attempt_at is None
            assert shipment.quote_id is None
            assert shipment.customer_shipping_cost is None
            assert shipment.package_weight_grams is None

    asyncio.run(check())
    assert fake_provider.create_calls == 0


def test_admin_receiver_workflow_quotes_receiver_and_preserves_order_total(
    fake_provider,
    override_database,
    super_admin_headers,
):
    client = TestClient(app)
    order_id, shipment_id, original_total = _prepare_receiver_booking(
        client,
        super_admin_headers,
        key="receiver-admin",
        sku="RECEIVER-ADMIN",
    )
    assert fake_provider.quote_requests[-1]["payment_type"] == "RECEIVER"
    assert fake_provider.create_calls == 0

    async def check() -> None:
        async with TestingSessionLocal() as session:
            order = await session.get(Order, order_id)
            shipment = await session.get(Shipment, shipment_id)
            assert order is not None and shipment is not None
            assert order.estimated_total == original_total
            assert order.shipping_customer_cost is None
            assert shipment.status == ShipmentStatus.READY_TO_BOOK.value
            assert shipment.booking_next_attempt_at is None
            assert shipment.package_measured_at is not None
            assert shipment.provider_box_type_id == 1
            assert shipment.carrier_code == "IR_POST"
            assert shipment.service_code == "EXPRESS"
            assert shipment.customer_shipping_cost is None
            assert shipment.provider_quoted_cost == Decimal("17000.00")
            assert (shipment.provider_data or {}).get("packed_quote", {}).get(
                "package_fingerprint"
            )

    asyncio.run(check())


def test_package_remeasure_invalidates_quote_and_service(
    fake_provider,
    override_database,
    super_admin_headers,
):
    client = TestClient(app)
    order_id, shipment_id, _ = _prepare_receiver_booking(
        client,
        super_admin_headers,
        key="receiver-invalidate",
        sku="RECEIVER-INVALIDATE",
    )
    remasure = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/final-package",
        json={
            "length_cm": 12,
            "width_cm": 9,
            "height_cm": 5,
            "weight_grams": 300,
            "is_fragile": True,
            "is_liquid": False,
        },
        headers=super_admin_headers,
    )
    assert remasure.status_code == 200, remasure.text
    assert remasure.json()["status"] == ShipmentStatus.AWAITING_PACKAGING.value
    assert remasure.json()["carrier_code"] is None
    assert remasure.json()["package"]["provider_box_type_id"] is None

    stale = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/select-service",
        json={"carrier_code": "IR_POST", "service_code": "EXPRESS"},
        headers=super_admin_headers,
    )
    assert stale.status_code in {409, 422}


def test_quote_and_service_blocked_after_booked(
    fake_provider,
    override_database,
    super_admin_headers,
    monkeypatch,
):
    client = TestClient(app)
    order_id, shipment_id, _ = _prepare_receiver_booking(
        client,
        super_admin_headers,
        key="receiver-postbook",
        sku="RECEIVER-POSTBOOK",
    )
    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", True)
    booked = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/book",
        headers=super_admin_headers,
    )
    assert booked.status_code == 200, booked.text
    assert booked.json()["status"] == "booked"
    assert fake_provider.create_calls == 1

    quote = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/packed-quote",
        headers=super_admin_headers,
    )
    assert quote.status_code == 409
    select = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/select-service",
        json={"carrier_code": "IR_POST", "service_code": "EXPRESS"},
        headers=super_admin_headers,
    )
    assert select.status_code == 409


def test_prepared_receiver_not_auto_booked_when_write_flag_enabled(
    fake_provider,
    override_database,
    super_admin_headers,
    monkeypatch,
):
    client = TestClient(app)
    prepared: list[tuple[int, int]] = []
    for idx in range(3):
        order_id, shipment_id, _ = _prepare_receiver_booking(
            client,
            super_admin_headers,
            key=f"receiver-prep-{idx}",
            sku=f"RECEIVER-PREP-{idx}",
        )
        prepared.append((order_id, shipment_id))

    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", True)

    async def run_worker() -> None:
        async with TestingSessionLocal() as session:
            assert await process_shipment_bookings(session) == 0
            for _, shipment_id in prepared:
                row = await session.get(Shipment, shipment_id)
                assert row is not None
                assert row.status == ShipmentStatus.READY_TO_BOOK.value
                assert row.booking_attempts == 0
                assert row.provider_parcel_no is None

    asyncio.run(run_worker())
    assert fake_provider.create_calls == 0

    order_id, shipment_id = prepared[0]
    explicit = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/book",
        headers=super_admin_headers,
    )
    assert explicit.status_code == 200, explicit.text
    assert fake_provider.create_calls == 1


def test_freight_required_persists_after_oversized_quote(
    fake_provider,
    override_database,
    super_admin_headers,
    monkeypatch,
):
    from app.services.logistics.models import BoxType

    async def tiny_boxes(_provider):
        return [BoxType(id=1, name="Tiny", length_cm=5, width_cm=5, height_cm=5)]

    monkeypatch.setattr("app.services.logistics.service._cached_boxes", tiny_boxes)
    client = TestClient(app)
    checkout = _receiver_checkout(
        client, super_admin_headers, key="freight-persist", sku="FREIGHT-PERSIST"
    )
    order_id, shipment_id = _ensure_paid_receiver_shipment(checkout["order_id"])
    package = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/final-package",
        json={
            "length_cm": 100,
            "width_cm": 80,
            "height_cm": 60,
            "weight_grams": 5000,
            "is_fragile": False,
            "is_liquid": False,
        },
        headers=super_admin_headers,
    )
    assert package.status_code == 200, package.text
    quote = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/packed-quote",
        headers=super_admin_headers,
    )
    assert quote.status_code == 422
    assert quote.json()["error_code"] == "SHIPPING_FREIGHT_REQUIRED"

    async def check() -> None:
        async with TestingSessionLocal() as session:
            session.expire_all()
            row = await session.get(Shipment, shipment_id)
            assert row is not None
            assert row.status == ShipmentStatus.FREIGHT_REQUIRED.value

    asyncio.run(check())


def test_persisted_receiver_mode_drives_create_payload_via_explicit_book(
    fake_provider,
    override_database,
    super_admin_headers,
    monkeypatch,
):
    client = TestClient(app)
    order_id, shipment_id, _ = _prepare_receiver_booking(
        client,
        super_admin_headers,
        key="receiver-create",
        sku="RECEIVER-CREATE",
    )
    # Runtime config changing later must not rewrite the order/shipment snapshot.
    monkeypatch.setattr(settings, "POSTEX_SHIPPING_PAYMENT_MODE", "sender_prepaid")
    monkeypatch.setattr(settings, "POSTEX_DEFAULT_PAYMENT_TYPE", "SENDER")
    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", True)

    async def build_check() -> None:
        async with TestingSessionLocal() as session:
            order = (
                (
                    await session.execute(
                        select(Order)
                        .where(Order.id == order_id)
                        .options(selectinload(Order.items))
                    )
                )
                .scalars()
                .one()
            )
            shipment = await session.get(Shipment, shipment_id)
            assert shipment is not None
            request = build_parcel_create_request(order, shipment)
            assert request["parcels"][0]["courier"]["payment_type"] == "RECEIVER"

    asyncio.run(build_check())

    # Worker must still ignore ready_to_book.
    async def worker_noop() -> None:
        async with TestingSessionLocal() as session:
            assert await process_shipment_bookings(session) == 0

    asyncio.run(worker_noop())
    assert fake_provider.create_calls == 0

    booked = client.post(
        f"/api/v1/orders/{order_id}/shipments/{shipment_id}/book",
        headers=super_admin_headers,
    )
    assert booked.status_code == 200, booked.text
    assert fake_provider.create_calls == 1
    assert fake_provider.create_requests[0]["parcels"][0]["courier"]["payment_type"] == "RECEIVER"


def test_worker_never_claims_awaiting_packaging_or_ready_to_book(
    fake_provider,
    override_database,
    monkeypatch,
):
    _, awaiting_id = _seed_worker_shipment(
        status=ShipmentStatus.AWAITING_PACKAGING.value,
        complete=True,
    )
    _, ready_id = _seed_worker_shipment(
        status=ShipmentStatus.READY_TO_BOOK.value,
        complete=True,
    )
    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", True)

    async def run() -> None:
        async with TestingSessionLocal() as session:
            assert await process_shipment_bookings(session) == 0
            for shipment_id, status in (
                (awaiting_id, ShipmentStatus.AWAITING_PACKAGING.value),
                (ready_id, ShipmentStatus.READY_TO_BOOK.value),
            ):
                row = await session.get(Shipment, shipment_id)
                assert row is not None
                assert row.status == status
                assert row.booking_attempts == 0

    asyncio.run(run())
    assert fake_provider.create_calls == 0


def test_incomplete_pending_booking_fails_closed_before_postex_create(
    fake_provider,
    override_database,
    monkeypatch,
):
    _, shipment_id = _seed_worker_shipment(
        status=ShipmentStatus.PENDING_BOOKING.value,
        complete=False,
    )
    monkeypatch.setattr(settings, "POSTEX_BOOKING_ENABLED", True)

    async def run() -> None:
        async with TestingSessionLocal() as session:
            assert await process_shipment_bookings(session) == 1
            row = await session.get(Shipment, shipment_id)
            assert row is not None
            assert row.status == ShipmentStatus.ERROR.value
            assert row.last_error_code == "SHIPPING_DATA_INCOMPLETE"
            assert row.booking_attempts == 0
            assert row.booking_next_attempt_at is None

    asyncio.run(run())
    assert fake_provider.create_calls == 0


def test_booking_gate_disabled_causes_zero_worker_mutations(
    fake_provider,
    override_database,
):
    _, shipment_id = _seed_worker_shipment(
        status=ShipmentStatus.PENDING_BOOKING.value,
        complete=True,
    )

    async def run() -> None:
        async with TestingSessionLocal() as session:
            before = await session.get(Shipment, shipment_id)
            assert before is not None
            before_state = (
                before.status,
                before.booking_attempts,
                before.booking_next_attempt_at,
                before.last_error_code,
                before.provider_data,
            )
            assert await process_shipment_bookings(session) == 0
            session.expire_all()
            after = await session.get(Shipment, shipment_id)
            assert after is not None
            assert (
                after.status,
                after.booking_attempts,
                after.booking_next_attempt_at,
                after.last_error_code,
                after.provider_data,
            ) == before_state

    asyncio.run(run())
    assert settings.POSTEX_BOOKING_ENABLED is False
    assert fake_provider.create_calls == 0
    assert fake_provider.lookup_calls == 0
