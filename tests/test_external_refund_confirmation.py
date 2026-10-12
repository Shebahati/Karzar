"""Wave C1: payment capabilities and external refund confirmation."""

from __future__ import annotations

import asyncio

import pytest
from app.core.config import settings
from app.crud.payment_transaction import list_payment_transactions_for_order
from app.db.models.commerce import Order, OrderStatus, OrderStatusEvent, PaymentStatus
from app.db.models.platform import AdminAuditLog
from app.db.models.product import StockMovement, StockMovementType
from app.main import app
from app.services.payment_service import reset_payment_provider_for_tests
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tests.conftest import TestingSessionLocal, customer_auth_headers

client = TestClient(app)


def _step_up_headers(super_admin_headers: dict) -> dict:
    response = client.post(
        "/api/v1/auth/verify-pin",
        json={"pin": settings.ADMIN_STEP_UP_PIN},
        headers=super_admin_headers,
    )
    assert response.status_code == 200, response.text
    return {**super_admin_headers, "X-Step-Up-Token": response.json()["secure_token"]}


def _checkout(product_id: int, headers: dict, *, phone: str) -> dict:
    response = client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {"full_name": "پرداخت", "phone": phone},
            "items": [{"product_id": product_id, "quantity": 1}],
            "shipping": {
                "province": "تهران",
                "city": "تهران",
                "postal_code": "1234567890",
                "address_line": "خیابان تست پلاک ۱۰ واحد ۲",
            },
            "shipping_method_code": "tipax_standard",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _pay_order_mock(order_id: int, authority: str, owner_headers: dict) -> None:
    verify = client.post(
        "/api/v1/payments/verify",
        json={"order_id": order_id, "authority": authority, "status": "OK"},
        headers=owner_headers,
    )
    assert verify.status_code == 200


def _mark_order_paid(order_id: int, ref_id: str | None = None) -> None:
    async def _run() -> None:
        from sqlalchemy.orm import selectinload

        from app.services.stock_ledger_service import ensure_order_sale_movements

        async with TestingSessionLocal() as db:
            order = (
                await db.execute(
                    select(Order).where(Order.id == order_id).options(selectinload(Order.items))
                )
            ).scalar_one()
            order.payment_status = PaymentStatus.PAID.value
            order.status = OrderStatus.PAID.value
            order.payment_ref_id = ref_id or f"SEP-PAID-REF-{order_id}"
            if not order.payment_authority:
                order.payment_authority = "SEP-AUTH-TEST"
            await ensure_order_sale_movements(db, order)
            await db.commit()

    asyncio.run(_run())


def _activate_mock_checkout(monkeypatch) -> None:
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()


def _activate_sep(monkeypatch) -> None:
    monkeypatch.setattr(settings, "SEP_TERMINAL_ID", "2001")
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "sep")
    reset_payment_provider_for_tests()


@pytest.fixture
def sep_provider(monkeypatch):
    _activate_sep(monkeypatch)
    yield
    reset_payment_provider_for_tests()


@pytest.mark.usefixtures("override_database")
def test_capabilities_sep_returns_external_confirmation(super_admin_headers, sep_provider):
    response = client.get("/api/v1/payments/capabilities", headers=super_admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "sep"
    assert body["automated_refund_supported"] is False
    assert body["external_refund_confirmation_supported"] is True
    assert body["refund_mode"] == "external_confirmation"


@pytest.mark.usefixtures("override_database")
def test_capabilities_mock_returns_automated(super_admin_headers, monkeypatch):
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()
    response = client.get("/api/v1/payments/capabilities", headers=super_admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["refund_mode"] == "automated"
    assert body["automated_refund_supported"] is True


@pytest.mark.usefixtures("override_database")
def test_capabilities_requires_super_admin(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()
    anon = client.get("/api/v1/payments/capabilities")
    assert anon.status_code == 401
    user = customer_auth_headers("09127770001")
    denied = client.get("/api/v1/payments/capabilities", headers=user)
    assert denied.status_code == 403


@pytest.mark.usefixtures("override_database")
def test_external_confirmation_auth_guards(valid_product_data, super_admin_headers, monkeypatch):
    _activate_mock_checkout(monkeypatch)
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "C1-AUTH"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    owner = customer_auth_headers("09127770002")
    order_id = _checkout(product_id, owner, phone="09127770002")["order_id"]
    _mark_order_paid(order_id)
    _activate_sep(monkeypatch)

    payload = {"order_id": order_id, "external_reference": "EXT-REF-001"}
    anon = client.post("/api/v1/payments/refund/external-confirmation", json=payload)
    assert anon.status_code in (401, 403)
    assert (
        client.post(
            "/api/v1/payments/refund/external-confirmation",
            json=payload,
            headers=customer_auth_headers("09127779999"),
        ).status_code
        == 403
    )
    missing_step_up = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json=payload,
        headers=super_admin_headers,
    )
    assert missing_step_up.status_code == 403
    assert missing_step_up.json()["error_code"] == "STEP_UP_REQUIRED"


@pytest.mark.usefixtures("override_database")
def test_external_confirmation_validation(
    valid_product_data, super_admin_headers, step_up_headers, monkeypatch
):
    _activate_mock_checkout(monkeypatch)
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "C1-VAL"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    owner = customer_auth_headers("09127770003")
    checkout = _checkout(product_id, owner, phone="09127770003")
    order_id = checkout["order_id"]
    order_64 = _checkout(product_id, customer_auth_headers("09127770032"), phone="09127770032")
    other_order = _checkout(product_id, customer_auth_headers("09127770033"), phone="09127770033")
    _mark_order_paid(order_id)
    _mark_order_paid(order_64["order_id"])
    _mark_order_paid(other_order["order_id"])
    _activate_sep(monkeypatch)
    missing_ref = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json={"order_id": order_id, "external_reference": "  "},
        headers=_step_up_headers(super_admin_headers),
    )
    assert missing_ref.status_code == 422

    long_ref = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json={"order_id": order_id, "external_reference": "x" * 65},
        headers=_step_up_headers(super_admin_headers),
    )
    assert long_ref.status_code == 422

    ref_64 = "r" * 64
    ok_64 = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json={"order_id": order_64["order_id"], "external_reference": ref_64},
        headers=_step_up_headers(super_admin_headers),
    )
    assert ok_64.status_code == 200

    long_note = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json={
            "order_id": other_order["order_id"],
            "external_reference": "EXT-OK-002",
            "evidence_note": "n" * 501,
        },
        headers=_step_up_headers(super_admin_headers),
    )
    assert long_note.status_code == 422


@pytest.mark.usefixtures("override_database")
def test_external_confirmation_rejects_non_paid_states(
    valid_product_data, super_admin_headers, step_up_headers, monkeypatch
):
    _activate_mock_checkout(monkeypatch)
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "C1-STATE"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    owner = customer_auth_headers("09127770004")
    checkout = _checkout(product_id, owner, phone="09127770004")
    order_id = checkout["order_id"]
    _activate_sep(monkeypatch)

    async def set_payment_status(status: str) -> None:
        async with TestingSessionLocal() as db:
            order = await db.get(Order, order_id)
            order.payment_status = status
            order.payment_ref_id = "REF-TEST"
            await db.commit()

    for status in (
        PaymentStatus.UNPAID.value,
        PaymentStatus.FAILED.value,
        PaymentStatus.VERIFYING.value,
        PaymentStatus.RECONCILIATION_REQUIRED.value,
    ):
        asyncio.run(set_payment_status(status))
        response = client.post(
            "/api/v1/payments/refund/external-confirmation",
            json={"order_id": order_id, "external_reference": "EXT-STATE-001"},
            headers=_step_up_headers(super_admin_headers),
        )
        assert response.status_code == 409


@pytest.mark.usefixtures("override_database")
def test_external_confirmation_happy_path_sep(
    valid_product_data, super_admin_headers, step_up_headers, monkeypatch
):
    _activate_mock_checkout(monkeypatch)
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "C1-HAPPY"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    owner = customer_auth_headers("09127770005")
    checkout = _checkout(product_id, owner, phone="09127770005")
    order_id = checkout["order_id"]
    _mark_order_paid(order_id)
    _activate_sep(monkeypatch)

    ext_ref = "BANK-REF-C1-HAPPY"
    response = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json={"order_id": order_id, "external_reference": ext_ref, "evidence_note": "ticket 42"},
        headers=step_up_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["payment_status"] == "refunded"
    assert body["status"] == "cancelled"
    assert body["refund_id"] == ext_ref
    assert body["cancelled"] is True
    assert body["reconciliation_required"] is False

    async def fetch():
        async with TestingSessionLocal() as db:
            order = await db.get(Order, order_id)
            rows = await list_payment_transactions_for_order(db, order_id)
            refunded = [r for r in rows if r.status == "refunded"]
            audit = (
                await db.execute(
                    select(AdminAuditLog).where(
                        AdminAuditLog.action == "payment_external_refund_confirmed",
                        AdminAuditLog.entity_id == str(order_id),
                    )
                )
            ).scalars().all()
            returns = (
                await db.execute(
                    select(func.count())
                    .select_from(StockMovement)
                    .where(
                        StockMovement.reference_id == f"order:{order_id}",
                        StockMovement.movement_type == StockMovementType.RETURN.value,
                    )
                )
            ).scalar_one()
            return order, refunded, audit, returns

    order, refunded_rows, audit_rows, return_count = asyncio.run(fetch())
    assert order.payment_refund_id == ext_ref
    assert len(refunded_rows) == 1
    assert refunded_rows[0].provider_data["source"] == "external_confirmation"
    assert len(audit_rows) == 1
    assert return_count == 1


@pytest.mark.usefixtures("override_database")
def test_external_confirmation_idempotent_replay(
    valid_product_data, super_admin_headers, step_up_headers, monkeypatch
):
    _activate_mock_checkout(monkeypatch)
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "C1-IDEM"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    owner = customer_auth_headers("09127770006")
    checkout = _checkout(product_id, owner, phone="09127770006")
    order_id = checkout["order_id"]
    _mark_order_paid(order_id)
    _activate_sep(monkeypatch)
    ext_ref = "BANK-REF-IDEM"
    payload = {"order_id": order_id, "external_reference": ext_ref}

    first = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json=payload,
        headers=step_up_headers,
    )
    assert first.status_code == 200
    second = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json=payload,
        headers=_step_up_headers(super_admin_headers),
    )
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["refund_id"] == ext_ref
    assert second_body["cancelled"] is True
    assert second_body["reconciliation_required"] is False

    async def counts():
        async with TestingSessionLocal() as db:
            return_count = (
                await db.execute(
                    select(func.count())
                    .select_from(StockMovement)
                    .where(
                        StockMovement.reference_id == f"order:{order_id}",
                        StockMovement.movement_type == StockMovementType.RETURN.value,
                    )
                )
            ).scalar_one()
            rows = await list_payment_transactions_for_order(db, order_id)
            audit_count = (
                await db.execute(
                    select(func.count())
                    .select_from(AdminAuditLog)
                    .where(
                        AdminAuditLog.action == "payment_external_refund_confirmed",
                        AdminAuditLog.entity_id == str(order_id),
                    )
                )
            ).scalar_one()
            return return_count, len([r for r in rows if r.status == "refunded"]), audit_count

    return_count, refunded_ledger, audit_count = asyncio.run(counts())
    assert return_count == 1
    assert refunded_ledger == 1
    assert audit_count == 1


@pytest.mark.usefixtures("override_database")
def test_external_confirmation_conflicting_reference_409(
    valid_product_data, super_admin_headers, step_up_headers, monkeypatch
):
    _activate_mock_checkout(monkeypatch)
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "C1-CONF"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    owner = customer_auth_headers("09127770007")
    checkout = _checkout(product_id, owner, phone="09127770007")
    order_id = checkout["order_id"]
    _mark_order_paid(order_id)
    _activate_sep(monkeypatch)

    client.post(
        "/api/v1/payments/refund/external-confirmation",
        json={"order_id": order_id, "external_reference": "REF-FIRST"},
        headers=step_up_headers,
    )
    conflict = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json={"order_id": order_id, "external_reference": "REF-OTHER"},
        headers=_step_up_headers(super_admin_headers),
    )
    assert conflict.status_code == 409


@pytest.mark.usefixtures("override_database")
def test_external_confirmation_partial_cancel_state(
    valid_product_data,
    super_admin_headers,
    step_up_headers,
    monkeypatch,
):
    _activate_mock_checkout(monkeypatch)
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "C1-PART"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    owner = customer_auth_headers("09127770008")
    checkout = _checkout(product_id, owner, phone="09127770008")
    order_id = checkout["order_id"]
    _mark_order_paid(order_id)
    _activate_sep(monkeypatch)

    async def fail_transition(*_args, **_kwargs):
        raise RuntimeError("simulated cancel block")

    monkeypatch.setattr(
        "app.services.external_refund_confirmation_service.transition_order_status",
        fail_transition,
    )

    ext_ref = "REF-PARTIAL"
    response = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json={"order_id": order_id, "external_reference": ext_ref},
        headers=step_up_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["payment_status"] == "refunded"
    assert body["cancelled"] is False
    assert body["reconciliation_required"] is True

    async def fetch():
        async with TestingSessionLocal() as db:
            order = await db.get(Order, order_id)
            rows = await list_payment_transactions_for_order(db, order_id)
            returns = (
                await db.execute(
                    select(func.count())
                    .select_from(StockMovement)
                    .where(
                        StockMovement.reference_id == f"order:{order_id}",
                        StockMovement.movement_type == StockMovementType.RETURN.value,
                    )
                )
            ).scalar_one()
            pending_audit = (
                await db.execute(
                    select(func.count())
                    .select_from(AdminAuditLog)
                    .where(
                        AdminAuditLog.action == "payment_external_refund_cancel_pending",
                        AdminAuditLog.entity_id == str(order_id),
                    )
                )
            ).scalar_one()
            return order, rows, returns, pending_audit

    order, rows, return_count, pending_audit = asyncio.run(fetch())
    assert order.payment_status == "refunded"
    assert order.payment_refund_id == ext_ref
    assert order.status != OrderStatus.CANCELLED.value
    assert len([r for r in rows if r.status == "refunded"]) == 1
    assert return_count == 0
    assert pending_audit == 1


@pytest.mark.usefixtures("override_database")
def test_external_confirmation_partial_replay_completes_cancel(
    valid_product_data, super_admin_headers, monkeypatch
):
    _activate_mock_checkout(monkeypatch)
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "C1-RECOV"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    owner = customer_auth_headers("09127770088")
    checkout = _checkout(product_id, owner, phone="09127770088")
    order_id = checkout["order_id"]
    _mark_order_paid(order_id)
    _activate_sep(monkeypatch)

    from app.services import order_service as order_service_module

    attempts = {"count": 0}
    real_transition = order_service_module.transition_order_status

    async def flaky_transition(db, order, target, **kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("first cancel attempt failed")
        return await real_transition(db, order, target, **kwargs)

    monkeypatch.setattr(
        "app.services.external_refund_confirmation_service.transition_order_status",
        flaky_transition,
    )

    ext_ref = "REF-RECOVER"
    payload = {"order_id": order_id, "external_reference": ext_ref}
    first = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json=payload,
        headers=_step_up_headers(super_admin_headers),
    )
    assert first.status_code == 200
    assert first.json()["cancelled"] is False
    assert first.json()["reconciliation_required"] is True

    second = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json=payload,
        headers=_step_up_headers(super_admin_headers),
    )
    assert second.status_code == 200
    assert second.json()["cancelled"] is True
    assert second.json()["reconciliation_required"] is False

    async def counts():
        async with TestingSessionLocal() as db:
            order = await db.get(Order, order_id)
            rows = await list_payment_transactions_for_order(db, order_id)
            returns = (
                await db.execute(
                    select(func.count())
                    .select_from(StockMovement)
                    .where(
                        StockMovement.reference_id == f"order:{order_id}",
                        StockMovement.movement_type == StockMovementType.RETURN.value,
                    )
                )
            ).scalar_one()
            confirmed = (
                await db.execute(
                    select(func.count())
                    .select_from(AdminAuditLog)
                    .where(
                        AdminAuditLog.action == "payment_external_refund_confirmed",
                        AdminAuditLog.entity_id == str(order_id),
                    )
                )
            ).scalar_one()
            return order.status, len([r for r in rows if r.status == "refunded"]), returns, confirmed

    status, refunded_n, return_n, confirmed_n = asyncio.run(counts())
    assert status == OrderStatus.CANCELLED.value
    assert refunded_n == 1
    assert return_n == 1
    assert confirmed_n == 1


@pytest.mark.usefixtures("override_database")
def test_external_confirmation_cancel_rolls_back_after_return_flush(
    valid_product_data, super_admin_headers, monkeypatch
):
    _activate_mock_checkout(monkeypatch)
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "C1-ATOMIC"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    owner = customer_auth_headers("09127770055")
    checkout = _checkout(product_id, owner, phone="09127770055")
    order_id = checkout["order_id"]
    _mark_order_paid(order_id)
    _activate_sep(monkeypatch)

    from app.services import order_service as order_service_module

    real_record = order_service_module.crud_commerce.record_status_event
    cancel_event_attempts = {"n": 0}

    async def flaky_record_status_event(db, **kwargs):
        if kwargs.get("status") == OrderStatus.CANCELLED.value:
            cancel_event_attempts["n"] += 1
            if cancel_event_attempts["n"] == 1:
                raise RuntimeError("failure after return flush")
        return await real_record(db, **kwargs)

    monkeypatch.setattr(
        order_service_module.crud_commerce,
        "record_status_event",
        flaky_record_status_event,
    )

    async def noop_notify(**_kwargs):
        return None

    monkeypatch.setattr(
        "app.services.order_service.notify_order_status_change",
        noop_notify,
    )

    ext_ref = "REF-ATOMIC-ROLLBACK"
    payload = {"order_id": order_id, "external_reference": ext_ref}

    first = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json=payload,
        headers=_step_up_headers(super_admin_headers),
    )
    assert first.status_code == 200
    assert first.json()["cancelled"] is False
    assert first.json()["reconciliation_required"] is True

    async def snapshot():
        async with TestingSessionLocal() as db:
            order = await db.get(Order, order_id)
            rows = await list_payment_transactions_for_order(db, order_id)
            returns = (
                await db.execute(
                    select(func.count())
                    .select_from(StockMovement)
                    .where(
                        StockMovement.reference_id == f"order:{order_id}",
                        StockMovement.movement_type == StockMovementType.RETURN.value,
                    )
                )
            ).scalar_one()
            cancelled_events = (
                await db.execute(
                    select(func.count())
                    .select_from(OrderStatusEvent)
                    .where(
                        OrderStatusEvent.order_id == order_id,
                        OrderStatusEvent.status == OrderStatus.CANCELLED.value,
                    )
                )
            ).scalar_one()
            confirmed = (
                await db.execute(
                    select(func.count())
                    .select_from(AdminAuditLog)
                    .where(
                        AdminAuditLog.action == "payment_external_refund_confirmed",
                        AdminAuditLog.entity_id == str(order_id),
                    )
                )
            ).scalar_one()
            pending = (
                await db.execute(
                    select(func.count())
                    .select_from(AdminAuditLog)
                    .where(
                        AdminAuditLog.action == "payment_external_refund_cancel_pending",
                        AdminAuditLog.entity_id == str(order_id),
                    )
                )
            ).scalar_one()
            return order, rows, returns, cancelled_events, confirmed, pending

    order, rows, returns, cancelled_events, confirmed, pending = asyncio.run(snapshot())
    assert order.payment_status == PaymentStatus.REFUNDED.value
    assert order.payment_refund_id == ext_ref
    assert order.status == OrderStatus.PAID.value
    assert len([r for r in rows if r.status == "refunded"]) == 1
    assert returns == 0
    assert cancelled_events == 0
    assert confirmed == 1
    assert pending == 1

    second = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json=payload,
        headers=_step_up_headers(super_admin_headers),
    )
    assert second.status_code == 200
    assert second.json()["cancelled"] is True
    assert second.json()["reconciliation_required"] is False

    third = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json=payload,
        headers=_step_up_headers(super_admin_headers),
    )
    assert third.status_code == 200
    assert third.json()["cancelled"] is True

    order, rows, returns, cancelled_events, confirmed, pending = asyncio.run(snapshot())
    assert order.status == OrderStatus.CANCELLED.value
    assert len([r for r in rows if r.status == "refunded"]) == 1
    assert returns == 1
    assert cancelled_events == 1
    assert confirmed == 1
    assert pending == 1


@pytest.mark.usefixtures("override_database")
def test_external_confirmation_trim_validation(
    valid_product_data, super_admin_headers, monkeypatch
):
    _activate_mock_checkout(monkeypatch)
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "C1-TRIM"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    owner = customer_auth_headers("09127770044")
    checkout = _checkout(product_id, owner, phone="09127770044")
    order_id = checkout["order_id"]
    order_ws = _checkout(product_id, customer_auth_headers("09127770045"), phone="09127770045")
    order_len = _checkout(product_id, customer_auth_headers("09127770047"), phone="09127770047")
    order_note = _checkout(product_id, customer_auth_headers("09127770046"), phone="09127770046")
    order_note_bad = _checkout(product_id, customer_auth_headers("09127770048"), phone="09127770048")
    _mark_order_paid(order_id)
    _mark_order_paid(order_ws["order_id"])
    _mark_order_paid(order_len["order_id"])
    _mark_order_paid(order_note["order_id"])
    _mark_order_paid(order_note_bad["order_id"])
    _activate_sep(monkeypatch)

    trimmed = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json={"order_id": order_id, "external_reference": "  ABC  "},
        headers=_step_up_headers(super_admin_headers),
    )
    assert trimmed.status_code == 200
    async def ref_id():
        async with TestingSessionLocal() as db:
            order = await db.get(Order, order_id)
            return order.payment_refund_id
    assert asyncio.run(ref_id()) == "ABC"

    ref64 = "r" * 64
    padded = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json={"order_id": order_ws["order_id"], "external_reference": f"  {ref64}  "},
        headers=_step_up_headers(super_admin_headers),
    )
    assert padded.status_code == 200

    async def ref64_id():
        async with TestingSessionLocal() as db:
            order = await db.get(Order, order_ws["order_id"])
            return order.payment_refund_id

    assert asyncio.run(ref64_id()) == ref64
    assert len(asyncio.run(ref64_id())) == 64

    over = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json={"order_id": order_len["order_id"], "external_reference": "y" * 65},
        headers=_step_up_headers(super_admin_headers),
    )
    assert over.status_code == 422

    note_ok = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json={
            "order_id": order_note["order_id"],
            "external_reference": "NOTE-OK",
            "evidence_note": f"  {'n' * 500}  ",
        },
        headers=_step_up_headers(super_admin_headers),
    )
    assert note_ok.status_code == 200

    note_bad = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json={
            "order_id": order_note_bad["order_id"],
            "external_reference": "NOTE-BAD",
            "evidence_note": "x" * 501,
        },
        headers=_step_up_headers(super_admin_headers),
    )
    assert note_bad.status_code == 422


@pytest.mark.usefixtures("override_database")
def test_external_confirmation_success_may_notify_cancelled(
    valid_product_data, super_admin_headers, monkeypatch
):
    _activate_mock_checkout(monkeypatch)
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "C1-NOTIFY"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    owner = customer_auth_headers("09127770077")
    checkout = _checkout(product_id, owner, phone="09127770077")
    order_id = checkout["order_id"]
    _mark_order_paid(order_id)
    _activate_sep(monkeypatch)

    notified: list[dict] = []

    async def spy_notify(**kwargs):
        notified.append(kwargs)

    monkeypatch.setattr(
        "app.services.order_service.notify_order_status_change",
        spy_notify,
    )

    response = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json={"order_id": order_id, "external_reference": "REF-NOTIFY-1"},
        headers=_step_up_headers(super_admin_headers),
    )
    assert response.status_code == 200
    assert response.json()["cancelled"] is True
    assert len(notified) == 1
    assert notified[0]["status"] == OrderStatus.CANCELLED.value


@pytest.mark.usefixtures("override_database")
def test_external_confirmation_rejected_for_mock_automated_provider(
    valid_product_data, super_admin_headers, step_up_headers, monkeypatch
):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()

    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "C1-MOCK-GATE"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    owner = customer_auth_headers("09127770009")
    checkout = _checkout(product_id, owner, phone="09127770009")
    order_id = checkout["order_id"]
    _pay_order_mock(order_id, checkout["authority"], owner)

    response = client.post(
        "/api/v1/payments/refund/external-confirmation",
        json={"order_id": order_id, "external_reference": "SHOULD-NOT"},
        headers=step_up_headers,
    )
    assert response.status_code == 409
    assert "automated refund workflow" in response.json()["message"]


@pytest.mark.usefixtures("override_database")
def test_sep_automated_refund_endpoint_400_no_mutation(
    valid_product_data, super_admin_headers, step_up_headers, monkeypatch
):
    from app.services import sep_client

    reverse_calls = 0

    async def _reverse_spy(**_kwargs):
        nonlocal reverse_calls
        reverse_calls += 1
        return {}

    monkeypatch.setattr(sep_client, "reverse_sep_transaction", _reverse_spy)

    _activate_mock_checkout(monkeypatch)
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "C1-SEP-REF"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    owner = customer_auth_headers("09127770010")
    checkout = _checkout(product_id, owner, phone="09127770010")
    order_id = checkout["order_id"]
    _mark_order_paid(order_id)
    _activate_sep(monkeypatch)

    async def snapshot():
        async with TestingSessionLocal() as db:
            order = await db.get(Order, order_id)
            rows = await list_payment_transactions_for_order(db, order_id)
            return order.payment_status, order.status, len(rows)

    before = asyncio.run(snapshot())

    response = client.post(
        "/api/v1/payments/refund",
        json={"order_id": order_id},
        headers=step_up_headers,
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "BAD_REQUEST"

    after = asyncio.run(snapshot())
    assert before == after
    assert reverse_calls == 0


@pytest.mark.usefixtures("override_database")
def test_mock_automated_refund_still_works(
    valid_product_data, super_admin_headers, step_up_headers, monkeypatch
):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()

    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "C1-MOCK-REF"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    owner = customer_auth_headers("09127770011")
    checkout = _checkout(product_id, owner, phone="09127770011")
    order_id = checkout["order_id"]
    _pay_order_mock(order_id, checkout["authority"], owner)

    response = client.post(
        "/api/v1/payments/refund",
        json={"order_id": order_id},
        headers=step_up_headers,
    )
    assert response.status_code == 200
    assert response.json()["payment_status"] == "refunded"
    assert response.json()["status"] == "cancelled"
