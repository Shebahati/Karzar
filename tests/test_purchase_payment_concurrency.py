"""#450 — purchase/payment lifecycle concurrency and idempotency."""

from __future__ import annotations

import asyncio
import threading
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.core.config import settings
from app.crud.stock_movement import list_stock_movements_for_reference
from app.db.models.commerce import Order
from app.db.models.product import StockMovement, StockMovementType
from app.main import app
from app.services import order_expiry_service
from app.services.payment_service import reset_payment_provider_for_tests
from app.services.stock_ledger_service import record_sale_movement
from fastapi.testclient import TestClient

from tests.conftest import USE_POSTGRES_TESTS, TestingSessionLocal, customer_auth_headers

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


@pytest.fixture
def sep_settings(monkeypatch):
    from tests.test_sep_payment import TERMINAL

    monkeypatch.setattr(settings, "SEP_TERMINAL_ID", TERMINAL)
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(
        settings,
        "PAYMENT_CALLBACK_URL",
        "http://localhost:8000/api/v1/payments/callback/sep",
    )
    monkeypatch.setattr(
        settings, "PAYMENT_SUCCESS_REDIRECT_URL", "http://localhost:3000/checkout/success"
    )
    monkeypatch.setattr(
        settings,
        "PAYMENT_FAILURE_REDIRECT_URL",
        "http://localhost:3000/checkout/payment/failed",
    )
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()
    yield


def test_concurrent_two_customers_same_sku_checkout(
    valid_product_data, super_admin_headers, mock_payment, monkeypatch
):
    if not USE_POSTGRES_TESTS:
        pytest.skip("requires PostgreSQL row locking semantics")
    product_id = _create_product(super_admin_headers, valid_product_data, sku="CONC-SKU")
    results_by_phone: dict[str, dict] = {}
    errors: list[tuple[str, BaseException]] = []
    barrier = threading.Barrier(2)
    phones = ("09124000001", "09124000002")

    def worker(phone: str) -> None:
        try:
            barrier.wait(timeout=10)
            thread_client = TestClient(app)
            auth = customer_auth_headers(phone)
            body = {
                **_CHECKOUT_BODY,
                "customer": {"full_name": "خریدار", "phone": phone},
                "items": [{"product_id": product_id, "quantity": 1}],
            }
            resp = thread_client.post("/api/v1/checkout", json=body, headers=auth)
            assert resp.status_code == 201, resp.text
            results_by_phone[phone] = resp.json()
        except BaseException as exc:  # noqa: BLE001
            errors.append((phone, exc))

    threads = [threading.Thread(target=worker, args=(phone,)) for phone in phones]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
        assert not thread.is_alive(), "checkout worker thread did not finish"
    assert not errors, errors
    assert set(results_by_phone.keys()) == set(phones)
    order_ids = {results_by_phone[p]["order_id"] for p in phones}
    assert len(order_ids) == 2
    stock = client.get(f"/api/v1/products/{product_id}/stock", headers=super_admin_headers)
    assert stock.json()["is_available"] is True
    for phone in phones:
        body = results_by_phone[phone]
        assert _movements(body["order_id"]) == []
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
        product_id,
        phone="09125000003",
        idempotency_key=shared,
        headers=customer_auth_headers("09125000003"),
    )
    b = _checkout(
        product_id,
        phone="09125000004",
        idempotency_key=shared,
        headers=customer_auth_headers("09125000004"),
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


def test_new_pending_cancel_has_no_return(valid_product_data, super_admin_headers, mock_payment):
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


def test_mock_verify_double_callback(
    valid_product_data, super_admin_headers, mock_payment, monkeypatch
):
    product_id = _create_product(super_admin_headers, valid_product_data, sku="DBL-VRF")
    body = _checkout(product_id, phone="09125000012")
    headers = customer_auth_headers("09125000012")
    payload = {"order_id": body["order_id"], "authority": body["authority"], "status": "OK"}
    assert client.post("/api/v1/payments/verify", json=payload, headers=headers).status_code == 200
    assert client.post("/api/v1/payments/verify", json=payload, headers=headers).status_code == 200
    sales = [m for m in _movements(body["order_id"]) if m.movement_type == "sale"]
    assert len(sales) == 1


def test_notification_paid_idempotent(
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
    from app.services.hesabfa.invoices import maybe_create_invoice_after_payment

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


def _dispatch_status(order_id: int, channel: str) -> str | None:
    from app.crud.order_notification import get_notification_dispatch

    async def _load():
        async with TestingSessionLocal() as db:
            row = await get_notification_dispatch(db, order_id=order_id, channel=channel)
            return row.status if row else None

    return asyncio.run(_load())


def test_customer_paid_sms_failure_persists_failed_then_retry_succeeds(
    valid_product_data, super_admin_headers, mock_payment, monkeypatch
):
    from app.db.models.commerce import OrderNotificationDispatchStatus
    from app.services import notification_service
    from app.services.sms_service import SmsDeliveryError

    class FailOnce:
        def __init__(self):
            self.calls = 0

        async def send(self, message):
            self.calls += 1
            if self.calls == 1:
                raise SmsDeliveryError("fail")
            return None

    fake = FailOnce()
    monkeypatch.setattr(notification_service, "get_sms_provider", lambda: fake)
    product_id = _create_product(super_admin_headers, valid_product_data, sku="NOTIF-FAIL")
    body = _checkout(product_id, phone="09125000020")
    headers = customer_auth_headers("09125000020")
    payload = {"order_id": body["order_id"], "authority": body["authority"], "status": "OK"}
    client.post("/api/v1/payments/verify", json=payload, headers=headers)
    assert (
        _dispatch_status(body["order_id"], notification_service.CHANNEL_CUSTOMER_PAID)
        == OrderNotificationDispatchStatus.FAILED.value
    )

    async def retry_dispatch():
        async with TestingSessionLocal() as db:
            order = await db.get(Order, body["order_id"])
            await notification_service.notify_purchase_paid(
                phone="09125000020",
                tracking_code=order.tracking_code,
                db=db,
                order_id=order.id,
            )
            await db.commit()

    asyncio.run(retry_dispatch())
    assert (
        _dispatch_status(body["order_id"], notification_service.CHANNEL_CUSTOMER_PAID)
        == OrderNotificationDispatchStatus.DISPATCHED.value
    )
    assert fake.calls == 2


def test_internal_paid_sms_failure_persists_failed(
    valid_product_data, super_admin_headers, mock_payment, monkeypatch
):
    from app.db.models.commerce import OrderNotificationDispatchStatus
    from app.services import notification_service
    from app.services.sms_service import SmsDeliveryError

    class Boom:
        async def send(self, message):
            raise SmsDeliveryError("internal fail")

    monkeypatch.setattr(notification_service, "get_sms_provider", lambda: Boom())
    monkeypatch.setattr(settings, "SMS_INTERNAL_ORDER_ALERT_RECIPIENTS", "09121110002")
    product_id = _create_product(super_admin_headers, valid_product_data, sku="NOTIF-IFAIL")
    body = _checkout(product_id, phone="09125000021")
    headers = customer_auth_headers("09125000021")
    payload = {"order_id": body["order_id"], "authority": body["authority"], "status": "OK"}
    client.post("/api/v1/payments/verify", json=payload, headers=headers)
    assert (
        _dispatch_status(body["order_id"], notification_service.CHANNEL_INTERNAL_PAID)
        == OrderNotificationDispatchStatus.FAILED.value
    )


def test_internal_paid_no_recipient_leaves_no_dispatch_row(
    valid_product_data, super_admin_headers, mock_payment, monkeypatch
):
    from app.services import notification_service

    monkeypatch.setattr(settings, "SMS_INTERNAL_ORDER_ALERT_RECIPIENTS", "")
    product_id = _create_product(super_admin_headers, valid_product_data, sku="NOTIF-NOREC")
    body = _checkout(product_id, phone="09125000022")
    headers = customer_auth_headers("09125000022")
    payload = {"order_id": body["order_id"], "authority": body["authority"], "status": "OK"}
    client.post("/api/v1/payments/verify", json=payload, headers=headers)
    assert _dispatch_status(body["order_id"], notification_service.CHANNEL_INTERNAL_PAID) is None


def test_paid_dispatch_success_persists_dispatched_state(
    valid_product_data, super_admin_headers, mock_payment, monkeypatch
):
    from app.db.models.commerce import OrderNotificationDispatchStatus
    from app.services import notification_service
    from app.services.sms_service import SmsEvent

    class Recorder:
        def __init__(self):
            self.messages = []

        async def send(self, message):
            self.messages.append(message)

    fake = Recorder()
    monkeypatch.setattr(notification_service, "get_sms_provider", lambda: fake)
    monkeypatch.setattr(settings, "SMS_INTERNAL_ORDER_ALERT_RECIPIENTS", "09121110003")
    product_id = _create_product(super_admin_headers, valid_product_data, sku="NOTIF-OK")
    body = _checkout(product_id, phone="09125000023")
    headers = customer_auth_headers("09125000023")
    payload = {"order_id": body["order_id"], "authority": body["authority"], "status": "OK"}
    client.post("/api/v1/payments/verify", json=payload, headers=headers)
    assert (
        _dispatch_status(body["order_id"], notification_service.CHANNEL_CUSTOMER_PAID)
        == OrderNotificationDispatchStatus.DISPATCHED.value
    )
    assert (
        _dispatch_status(body["order_id"], notification_service.CHANNEL_INTERNAL_PAID)
        == OrderNotificationDispatchStatus.DISPATCHED.value
    )
    assert len([m for m in fake.messages if m.event == SmsEvent.ORDER_PAID]) == 1
    assert len([m for m in fake.messages if m.event == SmsEvent.INTERNAL_ORDER_PAID]) == 1


@pytest.mark.usefixtures("override_database")
def test_sep_concurrent_duplicate_callbacks(
    valid_product_data, super_admin_headers, monkeypatch, sep_settings
):
    if not USE_POSTGRES_TESTS:
        pytest.skip("requires PostgreSQL")
    from app.db.models.commerce import OrderStatus, PaymentStatus
    from app.services.payment_flow_service import order_amount_rials

    from tests.test_sep_payment import (
        TERMINAL,
        _auth,
        _enable_sep,
        _get_order,
        _mock_verify_ok,
        _set_order_authority,
        _unique_ref,
        _unique_token,
    )
    from tests.test_sep_payment import (
        _checkout as sep_checkout,
    )

    token = _unique_token("CONCSEP")
    ref_num = _unique_ref("CONCSEP")
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "SEP-CONC-CB"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    headers = _auth("09126000001")
    body = sep_checkout(product_id, headers, phone="09126000001")
    order_id = body["order_id"]
    tracking = asyncio.run(_set_order_authority(order_id, token))
    order = asyncio.run(_get_order(order_id))
    amount_rials = order_amount_rials(order)
    _enable_sep(monkeypatch)
    _mock_verify_ok(monkeypatch, amount_rials=amount_rials, ref_num=ref_num)
    data = {
        "Token": token,
        "ResNum": tracking,
        "RefNum": ref_num,
        "State": "OK",
        "Status": "2",
        "TerminalId": TERMINAL,
        "Amount": str(amount_rials),
    }
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def post_callback():
        try:
            barrier.wait(timeout=10)
            c = TestClient(app)
            return c.post("/api/v1/payments/callback/sep", data=data, follow_redirects=False)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)
            return None

    t1 = threading.Thread(target=post_callback)
    t2 = threading.Thread(target=post_callback)
    t1.start()
    t2.start()
    t1.join(timeout=60)
    t2.join(timeout=60)
    assert not t1.is_alive() and not t2.is_alive()
    assert not errors, errors
    order = asyncio.run(_get_order(order_id))
    assert order.payment_status == PaymentStatus.PAID.value
    assert order.status == OrderStatus.PAID.value
    assert order.payment_ref_id == ref_num
    sales = [m for m in _movements(order_id) if m.movement_type == "sale"]
    assert len(sales) == 1


@pytest.mark.usefixtures("override_database")
def test_callback_wins_safely_against_expiry(
    valid_product_data, super_admin_headers, monkeypatch, sep_settings
):
    if not USE_POSTGRES_TESTS:
        pytest.skip("requires PostgreSQL")
    from app.db.models.commerce import Order, OrderStatus, PaymentStatus
    from app.services import order_service
    from app.services.order_expiry_service import cancel_expired_pending_payment_orders
    from app.services.payment_flow_service import order_amount_rials

    from tests.test_sep_payment import (
        TERMINAL,
        _auth,
        _enable_sep,
        _get_order,
        _mock_verify_ok,
        _set_order_authority,
        _unique_ref,
        _unique_token,
    )
    from tests.test_sep_payment import (
        _checkout as sep_checkout,
    )

    token = _unique_token("RACEEXP")
    ref_num = _unique_ref("RACEEXP")
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "SEP-RACE-EXP"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    headers = _auth("09126000002")
    body = sep_checkout(product_id, headers, phone="09126000002")
    order_id = body["order_id"]
    tracking = asyncio.run(_set_order_authority(order_id, token))
    order = asyncio.run(_get_order(order_id))
    amount_rials = order_amount_rials(order)
    _enable_sep(monkeypatch)
    _mock_verify_ok(monkeypatch, amount_rials=amount_rials, ref_num=ref_num)

    async def age_order():
        async with TestingSessionLocal() as session:
            row = await session.get(Order, order_id)
            row.created_at = datetime.now(UTC) - timedelta(hours=2)
            row.payment_authority_expires_at = datetime.now(UTC) - timedelta(minutes=1)
            await session.commit()

    asyncio.run(age_order())
    monkeypatch.setattr(
        order_expiry_service,
        "pending_payment_cutoff",
        lambda now=None: datetime.now(UTC) + timedelta(days=1),
    )
    callback_finished = threading.Event()
    start_gate = threading.Barrier(2)
    real_transition = order_service.transition_order_status

    async def gated_cancel_transition(db, order, target_status, **kwargs):
        if target_status == OrderStatus.CANCELLED.value:
            callback_finished.wait(timeout=30)
        return await real_transition(db, order, target_status, **kwargs)

    monkeypatch.setattr(order_service, "transition_order_status", gated_cancel_transition)

    def run_expiry():
        start_gate.wait(timeout=15)

        async def sweep():
            async with TestingSessionLocal() as session:
                return await cancel_expired_pending_payment_orders(session)

        return asyncio.run(sweep())

    def run_callback():
        start_gate.wait(timeout=15)
        c = TestClient(app)
        resp = c.post(
            "/api/v1/payments/callback/sep",
            data={
                "Token": token,
                "ResNum": tracking,
                "RefNum": ref_num,
                "State": "OK",
                "Status": "2",
                "TerminalId": TERMINAL,
                "Amount": str(amount_rials),
            },
            follow_redirects=False,
        )
        callback_finished.set()
        return resp

    t_exp = threading.Thread(target=run_expiry)
    t_cb = threading.Thread(target=run_callback)
    t_exp.start()
    t_cb.start()
    t_exp.join(timeout=60)
    t_cb.join(timeout=60)
    assert not t_exp.is_alive() and not t_cb.is_alive()
    assert callback_finished.is_set()
    order = asyncio.run(_get_order(order_id))
    assert order.status == OrderStatus.PAID.value
    assert order.payment_status == PaymentStatus.PAID.value
    returns = [m for m in _movements(order_id) if m.movement_type == "return"]
    assert returns == []


@pytest.mark.usefixtures("override_database")
def test_cancel_unpaid_while_callback_in_flight(
    valid_product_data, super_admin_headers, monkeypatch, sep_settings
):
    if not USE_POSTGRES_TESTS:
        pytest.skip("requires PostgreSQL")
    from app.db.models.commerce import OrderStatus, PaymentStatus
    from app.services import sep_callback_service
    from app.services.payment_flow_service import order_amount_rials

    from tests.test_sep_payment import (
        TERMINAL,
        _auth,
        _enable_sep,
        _get_order,
        _mock_verify_ok,
        _set_order_authority,
        _unique_ref,
        _unique_token,
    )
    from tests.test_sep_payment import (
        _checkout as sep_checkout,
    )

    token = _unique_token("RACECAN")
    ref_num = _unique_ref("RACECAN")
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "SEP-RACE-CAN"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    headers = _auth("09126000003")
    body = sep_checkout(product_id, headers, phone="09126000003")
    order_id = body["order_id"]
    tracking = asyncio.run(_set_order_authority(order_id, token))
    order = asyncio.run(_get_order(order_id))
    amount_rials = order_amount_rials(order)
    _enable_sep(monkeypatch)
    _mock_verify_ok(monkeypatch, amount_rials=amount_rials, ref_num=ref_num)
    gate = threading.Barrier(2)
    real_reserve = sep_callback_service.reserve_sep_callback

    async def gated_reserve(db, fields, **kwargs):
        gate.wait(timeout=15)
        return await real_reserve(db, fields, **kwargs)

    monkeypatch.setattr(sep_callback_service, "reserve_sep_callback", gated_reserve)

    def admin_cancel():
        gate.wait(timeout=15)
        return client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": "cancelled"},
            headers=_step_up_headers(super_admin_headers),
        )

    def sep_callback():
        c = TestClient(app)
        return c.post(
            "/api/v1/payments/callback/sep",
            data={
                "Token": token,
                "ResNum": tracking,
                "RefNum": ref_num,
                "State": "OK",
                "Status": "2",
                "TerminalId": TERMINAL,
                "Amount": str(amount_rials),
            },
            follow_redirects=False,
        )

    t1 = threading.Thread(target=admin_cancel)
    t2 = threading.Thread(target=sep_callback)
    t1.start()
    t2.start()
    t1.join(timeout=60)
    t2.join(timeout=60)
    order = asyncio.run(_get_order(order_id))
    assert order.payment_ref_id == ref_num
    assert order.payment_status in {
        PaymentStatus.PAID.value,
        PaymentStatus.VERIFYING.value,
        PaymentStatus.RECONCILIATION_REQUIRED.value,
    }
    assert order.status in {
        OrderStatus.PAID.value,
        OrderStatus.PENDING_PAYMENT.value,
        OrderStatus.CANCELLED.value,
    }
    if order.status == OrderStatus.PAID.value:
        assert order.payment_status == PaymentStatus.PAID.value


@pytest.mark.usefixtures("override_database")
def test_payment_ref_id_collision_second_order(
    valid_product_data, super_admin_headers, monkeypatch, sep_settings
):
    if not USE_POSTGRES_TESTS:
        pytest.skip("requires PostgreSQL")
    from app.db.models.commerce import PaymentStatus
    from app.services.payment_flow_service import order_amount_rials

    from tests.test_sep_payment import (
        TERMINAL,
        _auth,
        _enable_sep,
        _get_order,
        _mock_verify_ok,
        _set_order_authority,
        _unique_ref,
        _unique_token,
    )
    from tests.test_sep_payment import (
        _checkout as sep_checkout,
    )

    ref_num = _unique_ref("COLLIDE")
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "SEP-COL-A"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    headers_a = _auth("09126000004")
    headers_b = _auth("09126000005")
    body_a = sep_checkout(product_id, headers_a, phone="09126000004")
    body_b = sep_checkout(product_id, headers_b, phone="09126000005")
    token_a = _unique_token("COLA")
    token_b = _unique_token("COLB")
    tracking_a = asyncio.run(_set_order_authority(body_a["order_id"], token_a))
    tracking_b = asyncio.run(_set_order_authority(body_b["order_id"], token_b))
    order_a = asyncio.run(_get_order(body_a["order_id"]))
    order_b = asyncio.run(_get_order(body_b["order_id"]))
    amount_a = order_amount_rials(order_a)
    amount_b = order_amount_rials(order_b)
    _enable_sep(monkeypatch)
    _mock_verify_ok(monkeypatch, amount_rials=amount_a, ref_num=ref_num)
    resp_a = client.post(
        "/api/v1/payments/callback/sep",
        data={
            "Token": token_a,
            "ResNum": tracking_a,
            "RefNum": ref_num,
            "State": "OK",
            "Status": "2",
            "TerminalId": TERMINAL,
            "Amount": str(amount_a),
        },
        follow_redirects=False,
    )
    assert resp_a.status_code == 303
    assert "paid=1" in resp_a.headers["location"]

    _mock_verify_ok(monkeypatch, amount_rials=amount_b, ref_num=ref_num)
    resp_b = client.post(
        "/api/v1/payments/callback/sep",
        data={
            "Token": token_b,
            "ResNum": tracking_b,
            "RefNum": ref_num,
            "State": "OK",
            "Status": "2",
            "TerminalId": TERMINAL,
            "Amount": str(amount_b),
        },
        follow_redirects=False,
    )
    assert resp_b.status_code == 303
    assert "paid=1" not in resp_b.headers.get("location", "")
    order_b = asyncio.run(_get_order(body_b["order_id"]))
    assert order_b.payment_status != PaymentStatus.PAID.value
    order_a = asyncio.run(_get_order(body_a["order_id"]))
    assert order_a.payment_status == PaymentStatus.PAID.value
    assert order_a.payment_ref_id == ref_num
