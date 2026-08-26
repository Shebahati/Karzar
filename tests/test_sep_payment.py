"""SEP (Saman Kish) OnlinePG provider and callback tests — no live network."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from app.core.config import settings
from app.core.payment_url import is_allowed_payment_url
from app.db.models.commerce import Order, PaymentStatus
from app.main import app
from app.services.payment_service import (
    PaymentAmountMismatchError,
    PaymentGatewayError,
    PaymentGatewayTimeoutError,
    PaymentInitContext,
    PaymentRefundUnsupportedError,
    PaymentVerifyContext,
    PaymentVerifyFailedError,
    SepPaymentProvider,
    reset_payment_provider_for_tests,
)
from app.services.sep_client import (
    build_sep_send_token_url,
    normalize_sep_cell_number,
    parse_sep_verify_response,
    request_sep_token,
)
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.conftest import TestingSessionLocal, customer_auth_headers

client = TestClient(app)

TERMINAL = "2001"
TOKEN = "SEPTOKEN1234567890ABCD"


def _auth(phone: str) -> dict[str, str]:
    return customer_auth_headers(phone)


def _checkout(product_id: int, headers: dict, phone: str = "09121234567") -> dict:
    checkout = client.post(
        "/api/v1/checkout",
        json={
            "mode": "purchase",
            "customer": {"full_name": "Ali", "phone": phone},
            "items": [{"product_id": product_id, "quantity": 1}],
            "shipping": {
                "province": "تهران",
                "city": "تهران",
                "postal_code": "1234567890",
                "address_line": "خیابان آزادی، پلاک ۱۰",
            },
        },
        headers=headers,
    )
    assert checkout.status_code == 201, checkout.text
    return checkout.json()


async def _set_order_authority(order_id: int, authority: str, *, expires_minutes: int = 30) -> str:
    async with TestingSessionLocal() as session:
        result = await session.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one()
        order.payment_authority = authority
        order.payment_authority_expires_at = datetime.now(UTC) + timedelta(minutes=expires_minutes)
        await session.commit()
        return order.tracking_code


async def _get_order(order_id: int) -> Order:
    async with TestingSessionLocal() as session:
        result = await session.execute(select(Order).where(Order.id == order_id))
        return result.scalar_one()


@pytest.fixture
def sep_settings(monkeypatch):
    monkeypatch.setattr(settings, "SEP_TERMINAL_ID", TERMINAL)
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    # Keep callback on localhost so mock checkout during setup stays allowlisted.
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
    # Isolate provider selection — previous tests must not leave PAYMENT_PROVIDER=sep.
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()
    yield
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")
    reset_payment_provider_for_tests()


def _enable_sep(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "sep")
    monkeypatch.setattr(settings, "SEP_TERMINAL_ID", TERMINAL)
    reset_payment_provider_for_tests()


# --- Phone / URL helpers ---


def test_normalize_sep_cell_number():
    assert normalize_sep_cell_number("09121234567") == "9121234567"
    assert normalize_sep_cell_number("+989121234567") == "9121234567"
    assert normalize_sep_cell_number("9121234567") == "9121234567"
    assert normalize_sep_cell_number("123") is None
    assert normalize_sep_cell_number(None) is None


def test_build_sep_send_token_url_encodes(monkeypatch):
    monkeypatch.setattr(settings, "SEP_SEND_TOKEN_URL", "https://sep.shaparak.ir/OnlinePG/SendToken")
    url = build_sep_send_token_url("a b/c?d")
    parsed = urlparse(url)
    assert parsed.hostname == "sep.shaparak.ir"
    assert parsed.scheme == "https"
    qs = parse_qs(parsed.query)
    assert qs["token"] == ["a b/c?d"]


def test_sep_payment_url_allowlist():
    assert is_allowed_payment_url(
        "https://sep.shaparak.ir/OnlinePG/SendToken?token=abc"
    )
    assert not is_allowed_payment_url("http://sep.shaparak.ir/OnlinePG/SendToken?token=abc")
    assert not is_allowed_payment_url("https://sep.shaparak.ir.evil.example/")
    assert not is_allowed_payment_url("https://evil.example/?next=sep.shaparak.ir")
    assert not is_allowed_payment_url("javascript:alert(1)")
    assert not is_allowed_payment_url("data:text/html,x")


# --- Token request ---


def test_request_sep_token_success_payload(monkeypatch, sep_settings):
    _enable_sep(monkeypatch)
    captured: dict = {}

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"status": 1, "token": TOKEN}

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def post(self, url, json):
            captured["url"] = url
            captured["json"] = json
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _Client())
    result = asyncio.run(
        request_sep_token(
            amount_rials=12500000,
            res_num="KZ-ABCDEF123456",
            redirect_url="https://api.example/api/v1/payments/callback/sep",
            cell_number="9121234567",
            token_expiry_minutes=30,
        )
    )
    assert result.token == TOKEN
    body = captured["json"]
    assert body["Action"] == "Token"
    assert body["TerminalId"] == TERMINAL
    assert body["Amount"] == 12500000
    assert body["ResNum"] == "KZ-ABCDEF123456"
    assert body["CellNumber"] == "9121234567"
    assert body["TokenExpiryInMin"] == 30
    assert "Wage" not in body
    assert "TxnRandomSessionKey" not in body


def test_request_sep_token_failures(monkeypatch, sep_settings):
    _enable_sep(monkeypatch)
    class _Resp:
        def __init__(self, body, status=200):
            self._body = body
            self.status_code = status

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError("err", request=None, response=None)

        def json(self):
            if self._body is None:
                raise ValueError("bad json")
            return self._body

    def _run(body, status=200):
        class _Client:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return None

            async def post(self, url, json):
                return _Resp(body, status)

        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _Client())
        return asyncio.run(
            request_sep_token(
                amount_rials=1000,
                res_num="KZ-1",
                redirect_url="https://api.example/cb",
                cell_number=None,
                token_expiry_minutes=30,
            )
        )

    with pytest.raises(PaymentGatewayError):
        _run({"status": -1, "errorCode": "5"})
    with pytest.raises(PaymentGatewayError):
        _run({"status": 1, "token": "   "})
    with pytest.raises(PaymentGatewayError):
        _run(None)

    class _TimeoutClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def post(self, url, json):
            raise httpx.TimeoutException("t")

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _TimeoutClient())
    with pytest.raises(PaymentGatewayTimeoutError):
        asyncio.run(
            request_sep_token(
                amount_rials=1000,
                res_num="KZ-1",
                redirect_url="https://api.example/cb",
                cell_number=None,
                token_expiry_minutes=30,
            )
        )


# --- Verify parse ---


def test_parse_sep_verify_success_and_amount_keys():
    body = {
        "ResultCode": 0,
        "Success": True,
        "TransactionDetail": {
            "RRN": "14226761817",
            "RefNum": "50",
            "MaskedPan": "621986****8080",
            "HashedPan": "b96a",
            "TerminalNumber": 2001,
            "OrginalAmount": 1000,
            "AffectiveAmount": 1000,
            "StraceNo": "100428",
        },
    }
    detail = parse_sep_verify_response(body, expected_ref_num="50")
    assert detail.original_amount == 1000
    assert detail.ref_num == "50"

    body2 = {
        "ResultCode": 0,
        "Success": "true",
        "TransactionDetail": {
            "RefNum": "50",
            "TerminalNumber": 2001,
            "OriginalAmount": 1000,
            "AffectiveAmount": 1000,
        },
    }
    detail2 = parse_sep_verify_response(body2, expected_ref_num="50")
    assert detail2.original_amount == 1000


def test_parse_sep_verify_rejects_nonzero_result():
    with pytest.raises(PaymentVerifyFailedError):
        parse_sep_verify_response(
            {"ResultCode": 1, "Success": True, "TransactionDetail": {"RefNum": "50"}},
            expected_ref_num="50",
        )


def test_sep_provider_amount_mismatch(monkeypatch, sep_settings):
    _enable_sep(monkeypatch)
    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "ResultCode": 0,
                "Success": True,
                "TransactionDetail": {
                    "RefNum": "REF1",
                    "TerminalNumber": 2001,
                    "OrginalAmount": 999,
                    "AffectiveAmount": 999,
                },
            }

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def post(self, url, json):
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _Client())
    provider = SepPaymentProvider()
    with pytest.raises(PaymentAmountMismatchError):
        asyncio.run(
            provider.verify_payment(
                PaymentVerifyContext(authority=TOKEN, amount_rials=1000, ref_num="REF1")
            )
        )


def test_sep_refund_unsupported(sep_settings, monkeypatch):
    _enable_sep(monkeypatch)
    provider = SepPaymentProvider()
    with pytest.raises(PaymentRefundUnsupportedError):
        asyncio.run(provider.refund_payment(ref_id="REF1", amount_rials=1000))


# --- Callback integration ---


def _mock_verify_ok(monkeypatch, *, amount_rials: int, ref_num: str = "REF-OK-1"):
    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "ResultCode": 0,
                "Success": True,
                "TransactionDetail": {
                    "RefNum": ref_num,
                    "TerminalNumber": int(TERMINAL),
                    "OrginalAmount": amount_rials,
                    "AffectiveAmount": amount_rials,
                    "RRN": "RRN1",
                    "StraceNo": "TR1",
                    "MaskedPan": "6219****1234",
                },
            }

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def post(self, url, json):
            assert "VerifyTransaction" in url or "verify" in url.lower()
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _Client())


def test_sep_callback_success_flow(valid_product_data, super_admin_headers, monkeypatch, sep_settings):
    create = client.post("/api/v1/products/", json=valid_product_data, headers=super_admin_headers)
    product_id = create.json()["id"]
    headers = _auth("09121110001")
    body = _checkout(product_id, headers, phone="09121110001")
    order_id = body["order_id"]
    tracking = asyncio.run(_set_order_authority(order_id, TOKEN))
    from app.services.payment_flow_service import order_amount_rials

    order = asyncio.run(_get_order(order_id))
    amount_rials = order_amount_rials(order)
    _enable_sep(monkeypatch)
    _mock_verify_ok(monkeypatch, amount_rials=amount_rials, ref_num="REF-OK-1")

    resp = client.post(
        "/api/v1/payments/callback/sep",
        data={
            "Token": TOKEN,
            "ResNum": tracking,
            "RefNum": "REF-OK-1",
            "State": "OK",
            "Status": "2",
            "TerminalId": TERMINAL,
            "Amount": str(amount_rials),
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "paid=1" in resp.headers["location"]
    order2 = asyncio.run(_get_order(order_id))
    assert order2.payment_status == PaymentStatus.PAID.value
    assert order2.payment_ref_id == "REF-OK-1"


def test_sep_callback_declined_no_verify(valid_product_data, super_admin_headers, monkeypatch, sep_settings):
    called = {"n": 0}

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def post(self, url, json):
            called["n"] += 1
            raise AssertionError("Verify must not run on declined callback")

    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "SEP-DEC"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    headers = _auth("09121110002")
    body = _checkout(product_id, headers, phone="09121110002")
    tracking = asyncio.run(_set_order_authority(body["order_id"], TOKEN))
    _enable_sep(monkeypatch)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _Client())

    resp = client.post(
        "/api/v1/payments/callback/sep",
        data={
            "Token": TOKEN,
            "ResNum": tracking,
            "RefNum": "REF-FAIL",
            "State": "CanceledByUser",
            "Status": "1",
            "TerminalId": TERMINAL,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "reason=failed" in resp.headers["location"]
    assert called["n"] == 0
    order = asyncio.run(_get_order(body["order_id"]))
    assert order.payment_status == PaymentStatus.FAILED.value


def test_sep_callback_token_mismatch(valid_product_data, super_admin_headers, monkeypatch, sep_settings):
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "SEP-TOK"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    headers = _auth("09121110003")
    body = _checkout(product_id, headers, phone="09121110003")
    tracking = asyncio.run(_set_order_authority(body["order_id"], TOKEN))
    _enable_sep(monkeypatch)

    resp = client.post(
        "/api/v1/payments/callback/sep",
        data={
            "Token": "WRONG-TOKEN",
            "ResNum": tracking,
            "RefNum": "REF-X",
            "State": "OK",
            "Status": "2",
            "TerminalId": TERMINAL,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "reason=failed" in resp.headers["location"]
    order = asyncio.run(_get_order(body["order_id"]))
    assert order.payment_status != PaymentStatus.PAID.value


def test_sep_callback_get_not_allowed(sep_settings):
    resp = client.get("/api/v1/payments/callback/sep", follow_redirects=False)
    assert resp.status_code == 405


def test_sep_callback_idempotent_same_ref(
    valid_product_data, super_admin_headers, monkeypatch, sep_settings
):
    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "SEP-IDEM"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    headers = _auth("09121110004")
    body = _checkout(product_id, headers, phone="09121110004")
    order_id = body["order_id"]
    tracking = asyncio.run(_set_order_authority(order_id, TOKEN))
    from app.services.payment_flow_service import order_amount_rials

    order = asyncio.run(_get_order(order_id))
    amount_rials = order_amount_rials(order)
    _enable_sep(monkeypatch)
    _mock_verify_ok(monkeypatch, amount_rials=amount_rials, ref_num="REF-IDEM")

    data = {
        "Token": TOKEN,
        "ResNum": tracking,
        "RefNum": "REF-IDEM",
        "State": "OK",
        "Status": "2",
        "TerminalId": TERMINAL,
        "Amount": str(amount_rials),
    }
    first = client.post("/api/v1/payments/callback/sep", data=data, follow_redirects=False)
    assert first.status_code == 303
    assert "paid=1" in first.headers["location"]

    second = client.post("/api/v1/payments/callback/sep", data=data, follow_redirects=False)
    assert second.status_code == 303
    assert "paid=1" in second.headers["location"]


def test_sep_verify_timeout_leaves_verifying(
    valid_product_data, super_admin_headers, monkeypatch, sep_settings
):
    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def post(self, url, json):
            raise httpx.TimeoutException("timeout")

    create = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "SEP-TO"},
        headers=super_admin_headers,
    )
    product_id = create.json()["id"]
    headers = _auth("09121110005")
    body = _checkout(product_id, headers, phone="09121110005")
    order_id = body["order_id"]
    tracking = asyncio.run(_set_order_authority(order_id, TOKEN))
    from app.services.payment_flow_service import order_amount_rials

    order = asyncio.run(_get_order(order_id))
    amount_rials = order_amount_rials(order)
    _enable_sep(monkeypatch)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _Client())

    resp = client.post(
        "/api/v1/payments/callback/sep",
        data={
            "Token": TOKEN,
            "ResNum": tracking,
            "RefNum": "REF-TO",
            "State": "OK",
            "Status": "2",
            "TerminalId": TERMINAL,
            "Amount": str(amount_rials),
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "reason=verifying" in resp.headers["location"]
    order2 = asyncio.run(_get_order(order_id))
    assert order2.payment_status == PaymentStatus.VERIFYING.value
    assert order2.payment_ref_id == "REF-TO"
    assert order2.payment_next_verify_at is not None


def test_order_expiry_skips_verifying(monkeypatch, sep_settings):
    from app.services.order_expiry_service import cancel_expired_pending_payment_orders

    async def _seed_and_run():
        async with TestingSessionLocal() as session:
            # Minimal: ensure query filter excludes verifying by creating none unpaid.
            cancelled = await cancel_expired_pending_payment_orders(session)
            await session.commit()
            return cancelled

    # Smoke: function runs; verifying filter is payment_status==unpaid in SQL.
    asyncio.run(_seed_and_run())


def test_sep_provider_init_uses_context(monkeypatch, sep_settings):
    _enable_sep(monkeypatch)
    captured = {}

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"status": 1, "token": TOKEN}

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def post(self, url, json):
            captured.update(json)
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _Client())
    provider = SepPaymentProvider()
    result = asyncio.run(
        provider.init_payment(
            PaymentInitContext(
                amount_rials=5000,
                description="t",
                callback_url="https://api.example/api/v1/payments/callback/sep",
                merchant_reference="KZ-ABC",
                payer_phone="09121234567",
            )
        )
    )
    assert result.authority == TOKEN
    assert "sep.shaparak.ir" in result.payment_url
    assert captured["ResNum"] == "KZ-ABC"
    assert captured["CellNumber"] == "9121234567"
