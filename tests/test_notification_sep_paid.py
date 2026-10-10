"""SEP paid transition reaches purchase notifications once (mocked SMS)."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from app.core.config import settings
from app.services import notification_service
from app.services.payment_service import reset_payment_provider_for_tests

from tests.test_sep_payment import (
    TERMINAL,
    _auth,
    _checkout,
    _enable_sep,
    _get_order,
    _mock_verify_ok,
    _set_order_authority,
    _unique_ref,
    _unique_token,
    client,
)


@pytest.fixture
def sep_settings(monkeypatch):
    monkeypatch.setattr(settings, "SEP_TERMINAL_ID", TERMINAL)
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    monkeypatch.setattr(
        settings,
        "PAYMENT_CALLBACK_URL",
        "http://localhost:8000/api/v1/payments/callback/sep",
    )
    monkeypatch.setattr(settings, "PAYMENT_SUCCESS_REDIRECT_URL", "http://localhost:3000/checkout/success")
    monkeypatch.setattr(
        settings,
        "PAYMENT_FAILURE_REDIRECT_URL",
        "http://localhost:3000/checkout/payment/failed",
    )
    monkeypatch.setattr(settings, "PURCHASE_CHECKOUT_ENABLED", True)
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()
    yield
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()


@pytest.mark.usefixtures("override_database")
def test_sep_paid_callback_invokes_purchase_notifications_once(
    valid_product_data, super_admin_headers, monkeypatch, sep_settings
):
    paid_calls = AsyncMock()
    monkeypatch.setattr(notification_service, "notify_purchase_paid", paid_calls)

    token = _unique_token("NOTIFY")
    ref_num = _unique_ref("NOTIFY")
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "SEP-NOTIFY"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    headers = _auth("09121110077")
    body = _checkout(product_id, headers, phone="09121110077")
    order_id = body["order_id"]
    tracking = asyncio.run(_set_order_authority(order_id, token))
    from app.services.payment_flow_service import order_amount_rials

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
    first = client.post("/api/v1/payments/callback/sep", data=data, follow_redirects=False)
    assert first.status_code == 303
    second = client.post("/api/v1/payments/callback/sep", data=data, follow_redirects=False)
    assert second.status_code == 303

    assert paid_calls.await_count == 1
    kwargs = paid_calls.await_args.kwargs
    assert kwargs["tracking_code"] == tracking
    assert kwargs["phone"] == "09121110077"
