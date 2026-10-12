"""#450 — purchase/payment lifecycle concurrency and idempotency."""

from __future__ import annotations

import asyncio
import threading
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.crud.stock_movement import list_stock_movements_for_reference
from app.db.models.commerce import Order
from app.db.models.hesabfa import HesabfaInvoiceRecord
from app.db.models.product import StockMovement, StockMovementType
from app.main import app
from app.services import order_expiry_service
from app.services.payment_service import reset_payment_provider_for_tests
from app.services.stock_ledger_service import record_sale_movement
from fastapi.testclient import TestClient

from tests.conftest import TestingSessionLocal, USE_POSTGRES_TESTS, customer_auth_headers

pytestmark = pytest.mark.usefixtures("override_database")

client = TestClient(app)

_CHECKOUT_BODY = {
    "mode": "purchase",
    "customer": {"full_name": "رضا محمدی", "phone": "09123333333"},
    "items": [],
    "shipping": {
        "province": "تهران",
        "city": "تهران",
        "postal_code": "1234567890",
        "address_line": "خیابان آزادی",
    },
    "shipping_method_code": "tipax_standard",
}


def _create_product(super_admin_headers, valid_product_data, sku: str) -> int:
    payload = {**valid_product_data, "sku": sku, "is_available": True}
    resp = client.post("/api/v1/products/", json=payload, headers=super_admin_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _checkout(
    product_id: int,
    *,
    phone: str = "09123333333",
    quantity: int = 1,
    idempotency_key: str | None = None,
    headers: dict | None = None,
) -> dict:
    auth = headers or customer_auth_headers(phone)
    body = {
        **_CHECKOUT_BODY,
        "customer": {"full_name": "خریدار", "phone": phone},
        "items": [{"product_id": product_id, "quantity": quantity}],
    }
    hdrs = {**auth}
    if idempotency_key:
        hdrs["Idempotency-Key"] = idempotency_key
    resp = client.post("/api/v1/checkout", json=body, headers=hdrs)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _pay_order(checkout_body: dict, phone: str, monkeypatch) -> None:
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()
    headers = customer_auth_headers(phone)
    verify = client.post(
        "/api/v1/payments/verify",
        json={
            "order_id": checkout_body["order_id"],
            "authority": checkout_body["authority"],
            "status": "OK",
        },
        headers=headers,
    )
    assert verify.status_code == 200, verify.text


def _movements(order_id: int) -> list[StockMovement]:
    async def _load():
        async with TestingSessionLocal() as db:
            return await list_stock_movements_for_reference(db, f"order:{order_id}")

    return asyncio.run(_load())


def _step_up_headers(super_admin_headers: dict) -> dict:
    response = client.post(
        "/api/v1/auth/verify-pin",
        json={"pin": settings.ADMIN_STEP_UP_PIN},
        headers=super_admin_headers,
    )
    assert response.status_code == 200, response.text
    return {**super_admin_headers, "X-Step-Up-Token": response.json()["secure_token"]}


def _inject_legacy_pending_sale(order_id: int, product_id: int, quantity: int) -> None:
    async def _run():
        async with TestingSessionLocal() as db:
            await record_sale_movement(
                db, product_id=product_id, quantity=quantity, order_id=order_id
            )
            await db.commit()

    asyncio.run(_run())


@pytest.fixture
def mock_payment(monkeypatch):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()


def test_concurrent_two_customers_same_sku_checkout(
    valid_product_data, super_admin_headers, mock_payment, monkeypatch
):
    if not USE_POSTGRES_TESTS:
        pytest.skip("requires PostgreSQL row locking semantics")
    product_id = _create_product(super_admin_headers, valid_product_data, sku="CONC-SKU")
    results: list[dict] = []
    errors: list[Exception] = []
    barrier = threading.Barrier(2)

    def worker(phone: str):
        try:
            barrier.wait(timeout=10)
            results.append(
                _checkout(product_id, phone=phone, headers=customer_auth_headers(phone))
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    t1 = threading.Thread(target=worker, args=("09124000001",))
    t2 = threading.Thread(target=worker, args=("09124000002",))
    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)
    assert not errors, errors
    assert len(results) == 2
    assert results[0]["order_id"] != results[1]["order_id"]
    stock = client.get(
        f"/api/v1/products/{product_id}/stock", headers=super_admin_headers
    )
    assert stock.json()["is_available"] is True
    for body in results:
        assert _movements(body["order_id"]) == []
    for body, phone in zip(results, ("09124000001", "09124000002"), strict=True):
        _pay_order(body, phone, monkeypatch)
        sales = [m for m in _movements(body["order_id"]) if m.movement_type == "sale"]
        assert len(sales) == 1


def test_checkout_idempotency_same_key(valid_product_data, super_admin_headers, mock_payment):
    product_id = _create_product(super_admin_headers, valid_product_data, sku="IDEM-1")
    key = f"checkout-same-{uuid.uuid4().hex}"
    phone = "09125000001"
    first = _checkout(product_id, phone=phone, idempotency_key=key)
    second = client.post(
        "/api/v1/checkout",
        json={
            **_CHECKOUT_BODY,
            "customer": {"full_name": "خریدار", "phone": phone},
            "items": [{"product_id": product_id, "quantity": 1}],
        },
        headers={**customer_auth_headers(phone), "Idempotency-Key": key},
    )
    assert second.status_code == 201
    assert second.json()["order_id"] == first["order_id"]
    assert _movements(first["order_id"]) == []


def test_checkout_same_owner_different_key_creates_distinct_order(
    valid_product_data, super_admin_headers, mock_payment
):
    product_id = _create_product(super_admin_headers, valid_product_data, sku="IDEM-2")
    phone = "09125000002"
    a = _checkout(product_id, phone=phone, idempotency_key=f"k-a-{uuid.uuid4().hex}")
    b = _checkout(product_id, phone=phone, idempotency_key=f"k-b-{uuid.uuid4().hex}")
    assert a["order_id"] != b["order_id"]


def test_checkout_same_raw_key_different_owners_no_collision(
    valid_product_data, super_admin_headers, mock_payment
):
    product_id = _create_product(super_admin_headers, valid_product_data, sku="IDEM-3")
    shared = f"shared-{uuid.uuid4().hex}"
    a = _checkout(
        product_id, phone="09125000003", idempotency_key=shared, headers=customer_auth_headers("09125000003")
    )
    b = _checkout(
        product_id, phone="09125000004", idempotency_key=shared, headers=customer_auth_headers("09125000004")
    )
    assert a["order_id"] != b["order_id"]


def test_pending_checkout_does_not_create_sale_movement(
    valid_product_data, super_admin_headers, mock_payment
):
    product_id = _create_product(super_admin_headers, valid_product_data, sku="SALE-0")
    body = _checkout(product_id, phone="09125000005")
    assert _movements(body["order_id"]) == []


def test_paid_transition_creates_sale_exactly_once(
    valid_product_data, super_admin_headers, mock_payment, monkeypatch
):
    product_id = _create_product(super_admin_headers, valid_product_data, sku="SALE-1")
    body = _checkout(product_id, phone="09125000006", quantity=2)
    _pay_order(body, "09125000006", monkeypatch)
    movements = _movements(body["order_id"])
    sales = [m for m in movements if m.movement_type == StockMovementType.SALE.value]
    assert len(sales) == 1
    assert float(sales[0].quantity_change) == -2.0


def test_legacy_pending_sale_not_duplicated_when_paid(
    valid_product_data, super_admin_headers, mock_payment, monkeypatch
):
    product_id = _create_product(super_admin_headers, valid_product_data, sku="LEG-PAY")
    body = _checkout(product_id, phone="09125000007")
    _inject_legacy_pending_sale(body["order_id"], product_id, 1)
    _pay_order(body, "09125000007", monkeypatch)
    sales = [m for m in _movements(body["order_id"]) if m.movement_type == "sale"]
    assert len(sales) == 1


def test_new_pending_cancel_has_no_return(
    valid_product_data, super_admin_headers, mock_payment
):
    product_id = _create_product(super_admin_headers, valid_product_data, sku="CAN-NEW")
    body = _checkout(product_id, phone="09125000008")
    resp = client.patch(
        f"/api/v1/orders/{body['order_id']}/status",
        json={"status": "cancelled"},
        headers=_step_up_headers(super_admin_headers),
    )
    assert resp.status_code == 200
    assert _movements(body["order_id"]) == []


def test_legacy_pending_sale_cancel_gets_one_return(
    valid_product_data, super_admin_headers, mock_payment
):
    product_id = _create_product(super_admin_headers, valid_product_data, sku="CAN-LEG")
    body = _checkout(product_id, phone="09125000009", quantity=3)
    _inject_legacy_pending_sale(body["order_id"], product_id, 3)
    resp = client.patch(
        f"/api/v1/orders/{body['order_id']}/status",
        json={"status": "cancelled"},
        headers=_step_up_headers(super_admin_headers),
    )
    assert resp.status_code == 200
    movements = _movements(body["order_id"])
    assert len([m for m in movements if m.movement_type == "sale"]) == 1
    assert len([m for m in movements if m.movement_type == "return"]) == 1


def test_expiry_ledger_exactly_once(
    valid_product_data, super_admin_headers, mock_payment, monkeypatch
):
    product_id = _create_product(super_admin_headers, valid_product_data, sku="EXP-NEW")
    body = _checkout(product_id, phone="09125000010", quantity=2)
    monkeypatch.setattr(
        order_expiry_service,
        "pending_payment_cutoff",
        lambda now=None: datetime.now(UTC) + timedelta(days=1),
    )

    async def sweep_twice():
        async with TestingSessionLocal() as db:
            for _ in range(2):
                n = await order_expiry_service.cancel_expired_pending_payment_orders(db)
                if n:
                    await db.commit()

    asyncio.run(sweep_twice())
    assert _movements(body["order_id"]) == []

    body2 = _checkout(product_id, phone="09125000011", quantity=2)
    _inject_legacy_pending_sale(body2["order_id"], product_id, 2)
    monkeypatch.setattr(
        order_expiry_service,
        "pending_payment_cutoff",
        lambda now=None: datetime.now(UTC) + timedelta(days=1),
    )

    async def sweep_legacy():
        async with TestingSessionLocal() as db:
            for _ in range(2):
                await order_expiry_service.cancel_expired_pending_payment_orders(db)
                await db.commit()

    asyncio.run(sweep_legacy())
    returns = [m for m in _movements(body2["order_id"]) if m.movement_type == "return"]
    assert len(returns) == 1


def test_mock_verify_double_callback(valid_product_data, super_admin_headers, mock_payment, monkeypatch):
    product_id = _create_product(super_admin_headers, valid_product_data, sku="DBL-VRF")
    body = _checkout(product_id, phone="09125000012")
    headers = customer_auth_headers("09125000012")
    payload = {"order_id": body["order_id"], "authority": body["authority"], "status": "OK"}
    assert client.post("/api/v1/payments/verify", json=payload, headers=headers).status_code == 200
    assert client.post("/api/v1/payments/verify", json=payload, headers=headers).status_code == 200
    sales = [m for m in _movements(body["order_id"]) if m.movement_type == "sale"]
    assert len(sales) == 1


def test_notification_paid_idempotent(valid_product_data, super_admin_headers, mock_payment, monkeypatch):
    from app.services import notification_service
    from app.services.sms_service import SmsEvent

    class Recorder:
        def __init__(self):
            self.messages = []

        async def send(self, message):
            self.messages.append(message)

    fake = Recorder()
    monkeypatch.setattr(notification_service, "get_sms_provider", lambda: fake)
    monkeypatch.setattr(settings, "SMS_INTERNAL_ORDER_ALERT_RECIPIENTS", "09121110000")
    product_id = _create_product(super_admin_headers, valid_product_data, sku="NOTIF-C")
    body = _checkout(product_id, phone="09125000013")
    headers = customer_auth_headers("09125000013")
    payload = {"order_id": body["order_id"], "authority": body["authority"], "status": "OK"}
    client.post("/api/v1/payments/verify", json=payload, headers=headers)
    client.post("/api/v1/payments/verify", json=payload, headers=headers)
    paid_events = [m for m in fake.messages if m.event == SmsEvent.ORDER_PAID]
    assert len(paid_events) == 1


def test_internal_paid_notification_idempotent(
    valid_product_data, super_admin_headers, mock_payment, monkeypatch
):
    from app.services import notification_service
    from app.services.sms_service import SmsEvent

    class Recorder:
        def __init__(self):
            self.messages = []

        async def send(self, message):
            self.messages.append(message)

    fake = Recorder()
    monkeypatch.setattr(notification_service, "get_sms_provider", lambda: fake)
    monkeypatch.setattr(settings, "SMS_INTERNAL_ORDER_ALERT_RECIPIENTS", "09121110001")
    product_id = _create_product(super_admin_headers, valid_product_data, sku="NOTIF-I")
    body = _checkout(product_id, phone="09125000014")
    headers = customer_auth_headers("09125000014")
    payload = {"order_id": body["order_id"], "authority": body["authority"], "status": "OK"}
    client.post("/api/v1/payments/verify", json=payload, headers=headers)
    client.post("/api/v1/payments/verify", json=payload, headers=headers)
    internal = [m for m in fake.messages if m.event == SmsEvent.INTERNAL_ORDER_PAID]
    assert len(internal) == 1


def test_hesabfa_invoice_idempotent_on_double_verify(
    valid_product_data, super_admin_headers, mock_payment, monkeypatch
):
    from app.services.hesabfa.invoices import InvoiceSyncResult, maybe_create_invoice_after_payment

    calls = {"n": 0}

    async def counted_maybe(db, order):
        calls["n"] += 1
        return await maybe_create_invoice_after_payment(db, order)

    monkeypatch.setattr(
        "app.services.payment_flow_service.maybe_create_invoice_after_payment",
        counted_maybe,
    )
    product_id = _create_product(super_admin_headers, valid_product_data, sku="HES-1")
    body = _checkout(product_id, phone="09125000015")
    headers = customer_auth_headers("09125000015")
    payload = {"order_id": body["order_id"], "authority": body["authority"], "status": "OK"}
    client.post("/api/v1/payments/verify", json=payload, headers=headers)
    client.post("/api/v1/payments/verify", json=payload, headers=headers)
    assert calls["n"] == 1
    async def order_paid_once():
        async with TestingSessionLocal() as db:
            order = await db.get(Order, body["order_id"])
            return order.status, order.payment_status

    assert asyncio.run(order_paid_once()) == ("paid", "paid")


def _activate_sep(monkeypatch) -> None:
    monkeypatch.setattr(settings, "SEP_TERMINAL_ID", "2001")
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "sep")
    reset_payment_provider_for_tests()


def test_paid_refund_sale_return_balance(
    valid_product_data, super_admin_headers, mock_payment, monkeypatch
):
    product_id = _create_product(super_admin_headers, valid_product_data, sku="REF-BAL")
    body = _checkout(product_id, phone="09125000016", quantity=2)
    _pay_order(body, "09125000016", monkeypatch)
    sales = [m for m in _movements(body["order_id"]) if m.movement_type == "sale"]
    assert len(sales) == 1
    _activate_sep(monkeypatch)
    ext_ref = f"EXT-{uuid.uuid4().hex[:12]}"
    confirm = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json={
            "order_id": body["order_id"],
            "external_reference": ext_ref,
            "evidence_note": "test",
        },
        headers=_step_up_headers(super_admin_headers),
    )
    assert confirm.status_code == 200, confirm.text
    movements = _movements(body["order_id"])
    returns = [m for m in movements if m.movement_type == "return"]
    assert len(returns) == 1
    assert float(returns[0].quantity_change) == 2.0


def test_external_refund_idempotent(
    valid_product_data, super_admin_headers, mock_payment, monkeypatch
):
    product_id = _create_product(super_admin_headers, valid_product_data, sku="REF-IDEM")
    body = _checkout(product_id, phone="09125000017")
    _pay_order(body, "09125000017", monkeypatch)
    _activate_sep(monkeypatch)
    ext_ref = f"EXT-{uuid.uuid4().hex[:12]}"
    payload = {"external_reference": ext_ref, "evidence_note": "test"}
    payload["order_id"] = body["order_id"]
    first = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json=payload,
        headers=_step_up_headers(super_admin_headers),
    )
    second = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json=payload,
        headers=_step_up_headers(super_admin_headers),
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["refund_id"] == second.json()["refund_id"]
