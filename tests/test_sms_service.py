"""SMS provider routing tests. HTTP is blocked unless a test installs a fake client."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.config import settings
from app.main import app
from app.services import otp_service
from app.services.sms_service import (
    ConsoleSmsProvider,
    FarazSmsProvider,
    KavenegarSmsProvider,
    SmsDeliveryError,
    SmsEvent,
    SmsMessage,
    get_sms_provider,
    mask_phone,
    reset_sms_provider_for_tests,
)
from fastapi.testclient import TestClient

client = TestClient(app)


class _FakeProvider:
    def __init__(self):
        self.messages = []

    async def send(self, message):
        self.messages.append(message)


class _BlockedSmsClient:
    def __init__(self, *args, **kwargs):
        raise AssertionError("SMS tests must not open a real HTTP client")

    async def __aenter__(self):
        raise AssertionError("SMS tests must not open a real HTTP client")

    async def __aexit__(self, *args):
        return False


@pytest.fixture(autouse=True)
def _block_sms_network(monkeypatch):
    reset_sms_provider_for_tests()
    monkeypatch.setattr("app.services.sms_service.httpx.AsyncClient", _BlockedSmsClient)
    # The app logger does not propagate, so pytest's caplog would otherwise miss it.
    monkeypatch.setattr(logging.getLogger("app"), "propagate", True)


def _recording_client(monkeypatch):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"status": "success", "data": 1, "message": ""}
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.get = AsyncMock(return_value=mock_response)
    monkeypatch.setattr(
        "app.services.sms_service.httpx.AsyncClient",
        lambda *args, **kwargs: mock_client,
    )
    return mock_client


def _faraz_ready(monkeypatch, **overrides):
    monkeypatch.setattr(settings, "SMS_FARAZ_API_KEY", "test-key")
    monkeypatch.setattr(settings, "SMS_FARAZ_LINE_NUMBER", "90008361")
    monkeypatch.setattr(settings, "SMS_FARAZ_BASE_URL", "https://api.iranpayamak.com")
    monkeypatch.setattr(settings, "SMS_FARAZ_OTP_ATTR", "code")
    monkeypatch.setattr(settings, "SMS_FARAZ_ORDER_TRACKING_ATTR", "tracking_code")
    monkeypatch.setattr(settings, "SMS_FARAZ_LOGIN_OTP_PATTERN_CODE", None)
    monkeypatch.setattr(settings, "SMS_FARAZ_PASSWORD_RESET_PATTERN_CODE", None)
    monkeypatch.setattr(settings, "SMS_FARAZ_OTP_PATTERN_CODE", None)
    monkeypatch.setattr(settings, "SMS_FARAZ_ORDER_PAID_PATTERN_CODE", None)
    monkeypatch.setattr(settings, "SMS_FARAZ_INTERNAL_ORDER_PAID_PATTERN_CODE", None)
    monkeypatch.setattr(settings, "SMS_INTERNAL_ORDER_ALERT_RECIPIENTS", "")
    for name, value in overrides.items():
        monkeypatch.setattr(settings, name, value)


def _send(message: SmsMessage) -> None:
    asyncio.run(FarazSmsProvider().send(message))


def _posted_json(mock_client):
    assert mock_client.post.await_count == 1
    assert mock_client.get.await_count == 0
    return mock_client.post.await_args


def test_get_sms_provider_console_default(monkeypatch):
    monkeypatch.setattr(settings, "SMS_PROVIDER", "console")
    reset_sms_provider_for_tests()
    provider = get_sms_provider()
    assert isinstance(provider, ConsoleSmsProvider)


def test_get_sms_provider_faraz(monkeypatch):
    monkeypatch.setattr(settings, "SMS_PROVIDER", "faraz")
    reset_sms_provider_for_tests()
    provider = get_sms_provider()
    assert isinstance(provider, FarazSmsProvider)


def test_sms_message_rejects_template_token():
    with pytest.raises(TypeError):
        SmsMessage(
            receptor="09120000000",
            body="x",
            event=SmsEvent.ORDER_PAID,
            template_token="4321",
        )


def test_mask_phone():
    assert mask_phone("09123456789") == "0912***6789"
    assert mask_phone("12") == "***"


@pytest.mark.usefixtures("override_database")
def test_otp_request_sends_login_event(monkeypatch):
    fake = _FakeProvider()
    monkeypatch.setattr(otp_service, "get_sms_provider", lambda: fake)
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)

    response = client.post("/api/v1/auth/otp/request", json={"phone": "09122223333"})
    assert response.status_code == 200
    assert len(fake.messages) == 1
    message = fake.messages[0]
    assert message.receptor == "09122223333"
    assert message.event is SmsEvent.AUTH_LOGIN_OTP
    assert message.attributes["code"] == response.json()["dev_code"]


def test_login_otp_uses_login_pattern(monkeypatch):
    _faraz_ready(
        monkeypatch,
        SMS_FARAZ_LOGIN_OTP_PATTERN_CODE="LOGIN1",
        SMS_FARAZ_PASSWORD_RESET_PATTERN_CODE="RESET1",
        SMS_FARAZ_OTP_PATTERN_CODE="LEGACY",
    )
    mock_client = _recording_client(monkeypatch)
    _send(
        SmsMessage(
            receptor="09120000000",
            body="ignored",
            event=SmsEvent.AUTH_LOGIN_OTP,
            attributes={"code": "123456"},
        )
    )
    call = _posted_json(mock_client)
    assert call.args[0].endswith("/ws/v1/sms/pattern")
    assert call.kwargs["json"]["code"] == "LOGIN1"
    assert call.kwargs["json"]["attributes"] == {"code": "123456"}
    assert call.kwargs["headers"]["Api-Key"] == "test-key"


def test_password_reset_uses_reset_pattern(monkeypatch):
    _faraz_ready(
        monkeypatch,
        SMS_FARAZ_LOGIN_OTP_PATTERN_CODE="LOGIN1",
        SMS_FARAZ_PASSWORD_RESET_PATTERN_CODE="RESET1",
        SMS_FARAZ_OTP_PATTERN_CODE="LEGACY",
    )
    mock_client = _recording_client(monkeypatch)
    _send(
        SmsMessage(
            receptor="09120000000",
            body="کد بازیابی رمز عبور کارزار: 654321",
            event=SmsEvent.AUTH_PASSWORD_RESET,
            attributes={"code": "654321"},
        )
    )
    call = _posted_json(mock_client)
    assert call.args[0].endswith("/ws/v1/sms/pattern")
    assert call.kwargs["json"]["code"] == "RESET1"
    assert call.kwargs["json"]["attributes"] == {"code": "654321"}


def test_login_and_reset_patterns_are_independent(monkeypatch):
    _faraz_ready(
        monkeypatch,
        SMS_FARAZ_LOGIN_OTP_PATTERN_CODE="LOGIN1",
        SMS_FARAZ_PASSWORD_RESET_PATTERN_CODE="RESET9",
    )
    mock_client = _recording_client(monkeypatch)
    _send(
        SmsMessage(
            receptor="09120000000",
            body="login",
            event=SmsEvent.AUTH_LOGIN_OTP,
            attributes={"code": "111111"},
        )
    )
    _send(
        SmsMessage(
            receptor="09120000000",
            body="reset",
            event=SmsEvent.AUTH_PASSWORD_RESET,
            attributes={"code": "222222"},
        )
    )
    codes = [call.kwargs["json"]["code"] for call in mock_client.post.await_args_list]
    assert codes == ["LOGIN1", "RESET9"]


def test_legacy_pattern_fallback_is_auth_only(monkeypatch, caplog):
    _faraz_ready(monkeypatch, SMS_FARAZ_OTP_PATTERN_CODE="LEGACY")
    mock_client = _recording_client(monkeypatch)
    caplog.set_level(logging.WARNING)
    _send(
        SmsMessage(
            receptor="09120000000",
            body="login",
            event=SmsEvent.AUTH_LOGIN_OTP,
            attributes={"code": "111111"},
        )
    )
    _send(
        SmsMessage(
            receptor="09120000000",
            body="reset",
            event=SmsEvent.AUTH_PASSWORD_RESET,
            attributes={"code": "222222"},
        )
    )
    codes = [call.kwargs["json"]["code"] for call in mock_client.post.await_args_list]
    assert codes == ["LEGACY", "LEGACY"]
    assert "AUTH_LOGIN_OTP" in caplog.text
    assert "SMS_FARAZ_LOGIN_OTP_PATTERN_CODE" in caplog.text
    assert "AUTH_PASSWORD_RESET" in caplog.text
    assert "shared legacy pattern" in caplog.text


@pytest.mark.parametrize(
    "event",
    [SmsEvent.ORDER_SHIPPED, SmsEvent.INQUIRY_QUOTED],
)
def test_transactional_event_does_not_use_otp_pattern(monkeypatch, caplog, event):
    _faraz_ready(
        monkeypatch,
        SMS_FARAZ_LOGIN_OTP_PATTERN_CODE="LOGIN1",
        SMS_FARAZ_PASSWORD_RESET_PATTERN_CODE="RESET1",
        SMS_FARAZ_OTP_PATTERN_CODE="LEGACY",
    )
    caplog.set_level(logging.WARNING)
    _send(
        SmsMessage(
            receptor="09120000000",
            body="سفارش KZ-ABC ارسال شد.",
            event=event,
            attributes={"code": ""},
        )
    )
    assert event.value in caplog.text
    assert "skipped" in caplog.text


def test_password_reset_does_not_reuse_login_pattern(monkeypatch, caplog):
    _faraz_ready(monkeypatch, SMS_FARAZ_LOGIN_OTP_PATTERN_CODE="LOGIN1")
    mock_client = _recording_client(monkeypatch)
    caplog.set_level(logging.WARNING)
    body = "کد بازیابی رمز عبور کارزار: 654321"
    _send(
        SmsMessage(
            receptor="09120000000",
            body=body,
            event=SmsEvent.AUTH_PASSWORD_RESET,
            attributes={"code": "654321"},
        )
    )
    call = _posted_json(mock_client)
    assert call.args[0].endswith("/ws/v1/sms/simple")
    assert call.kwargs["json"]["text"] == body
    assert "LOGIN1" not in str(call.kwargs["json"])
    assert "AUTH_PASSWORD_RESET" in caplog.text


def test_order_paid_with_login_otp_configured_requires_paid_pattern(monkeypatch):
    _faraz_ready(
        monkeypatch,
        SMS_FARAZ_LOGIN_OTP_PATTERN_CODE="LOGIN1",
        SMS_FARAZ_ORDER_PAID_PATTERN_CODE=None,
    )
    with pytest.raises(SmsDeliveryError, match="ORDER_PAID"):
        _send(
            SmsMessage(
                receptor="09120000000",
                body="سفارش KZ-ABC پرداخت شد.",
                event=SmsEvent.ORDER_PAID,
                attributes={"tracking_code": "KZ-ABC"},
            )
        )


def test_order_paid_uses_dedicated_pattern_not_auth_otp(monkeypatch):
    _faraz_ready(
        monkeypatch,
        SMS_FARAZ_LOGIN_OTP_PATTERN_CODE="LOGIN1",
        SMS_FARAZ_PASSWORD_RESET_PATTERN_CODE="RESET1",
        SMS_FARAZ_OTP_PATTERN_CODE="LEGACY",
        SMS_FARAZ_ORDER_PAID_PATTERN_CODE="ORDERPAID1",
    )
    mock_client = _recording_client(monkeypatch)
    _send(
        SmsMessage(
            receptor="09120000000",
            body="سفارش KZ-ABC پرداخت شد.",
            event=SmsEvent.ORDER_PAID,
            attributes={"tracking_code": "KZ-ABC"},
        )
    )
    call = _posted_json(mock_client)
    assert call.kwargs["json"]["code"] == "ORDERPAID1"
    assert call.kwargs["json"]["attributes"] == {"tracking_code": "KZ-ABC"}
    assert "LOGIN1" not in str(call.kwargs["json"])
    assert "RESET1" not in str(call.kwargs["json"])
    assert "LEGACY" not in str(call.kwargs["json"])


def test_internal_order_paid_uses_internal_pattern(monkeypatch):
    _faraz_ready(
        monkeypatch,
        SMS_FARAZ_LOGIN_OTP_PATTERN_CODE="LOGIN1",
        SMS_FARAZ_INTERNAL_ORDER_PAID_PATTERN_CODE="INTPAID1",
    )
    mock_client = _recording_client(monkeypatch)
    _send(
        SmsMessage(
            receptor="09129998877",
            body="سفارش پرداخت‌شده: KZ-INT",
            event=SmsEvent.INTERNAL_ORDER_PAID,
            attributes={"tracking_code": "KZ-INT"},
        )
    )
    call = _posted_json(mock_client)
    assert call.kwargs["json"]["code"] == "INTPAID1"
    assert call.kwargs["json"]["attributes"] == {"tracking_code": "KZ-INT"}


def test_order_paid_missing_tracking_attribute_raises(monkeypatch):
    _faraz_ready(
        monkeypatch,
        SMS_FARAZ_ORDER_PAID_PATTERN_CODE="ORDERPAID1",
    )
    with pytest.raises(SmsDeliveryError, match="tracking"):
        _send(
            SmsMessage(
                receptor="09120000000",
                body="سفارش KZ-ABC پرداخت شد.",
                event=SmsEvent.ORDER_PAID,
                attributes={},
            )
        )


def test_order_events_use_simple_sms_when_no_otp_pattern_is_configured(monkeypatch):
    _faraz_ready(monkeypatch)
    mock_client = _recording_client(monkeypatch)
    body = "سفارش KZ-ABC123 ارسال شد."
    _send(
        SmsMessage(
            receptor="09121112222",
            body=body,
            event=SmsEvent.ORDER_SHIPPED,
        )
    )
    call = _posted_json(mock_client)
    assert call.args[0].endswith("/ws/v1/sms/simple")
    assert call.kwargs["json"]["text"] == body
    assert "code" not in call.kwargs["json"]


def test_auth_without_any_pattern_uses_simple_sms(monkeypatch):
    _faraz_ready(monkeypatch)
    mock_client = _recording_client(monkeypatch)
    _send(
        SmsMessage(
            receptor="09120000000",
            body="کد ورود شما به کارزار: 123456",
            event=SmsEvent.AUTH_LOGIN_OTP,
            attributes={"code": "123456"},
        )
    )
    call = _posted_json(mock_client)
    assert call.args[0].endswith("/ws/v1/sms/simple")
    assert call.kwargs["json"]["text"] == "کد ورود شما به کارزار: 123456"


def test_blocked_client_cannot_escape(monkeypatch):
    _faraz_ready(monkeypatch)
    with pytest.raises(SmsDeliveryError):
        _send(
            SmsMessage(
                receptor="09120000000",
                body="x",
                event=SmsEvent.AUTH_LOGIN_OTP,
                attributes={"code": "123456"},
            )
        )


def test_kavenegar_non_otp_does_not_use_verify_lookup(monkeypatch):
    monkeypatch.setattr(settings, "SMS_KAVENEGAR_API_KEY", "test-key")
    monkeypatch.setattr(settings, "SMS_KAVENEGAR_SENDER", "1000")
    monkeypatch.setattr(settings, "SMS_KAVENEGAR_OTP_TEMPLATE", "otp-template")
    mock_client = _recording_client(monkeypatch)
    asyncio.run(
        KavenegarSmsProvider().send(
            SmsMessage(
                receptor="09120000000",
                body="سفارش KZ-ABC پرداخت شد.",
                event=SmsEvent.ORDER_PAID,
                attributes={"code": "999999"},
            )
        )
    )
    assert mock_client.get.await_count == 0
    assert mock_client.post.await_count == 1
    url = mock_client.post.await_args.args[0]
    assert url.endswith("/sms/send.json")
    assert "verify/lookup" not in url
    assert mock_client.post.await_args.kwargs["data"]["message"] == "سفارش KZ-ABC پرداخت شد."


def test_kavenegar_login_otp_uses_verify_lookup(monkeypatch):
    monkeypatch.setattr(settings, "SMS_KAVENEGAR_API_KEY", "test-key")
    monkeypatch.setattr(settings, "SMS_KAVENEGAR_SENDER", "1000")
    monkeypatch.setattr(settings, "SMS_KAVENEGAR_OTP_TEMPLATE", "otp-template")
    mock_client = _recording_client(monkeypatch)
    asyncio.run(
        KavenegarSmsProvider().send(
            SmsMessage(
                receptor="09120000000",
                body="کد ورود شما به کارزار: 123456",
                event=SmsEvent.AUTH_LOGIN_OTP,
                attributes={"code": "123456"},
            )
        )
    )
    assert mock_client.post.await_count == 0
    assert mock_client.get.await_count == 1
    url = mock_client.get.await_args.args[0]
    assert "/verify/lookup.json" in url
    assert "template=otp-template" in url
    assert "token=123456" in url


def test_console_provider_does_not_log_otp(caplog):
    caplog.set_level(logging.INFO)
    code = "654321"
    phone = "09123456789"
    asyncio.run(
        ConsoleSmsProvider().send(
            SmsMessage(
                receptor=phone,
                body=f"کد ورود شما به کارزار: {code}",
                event=SmsEvent.AUTH_LOGIN_OTP,
                attributes={"code": code},
            )
        )
    )
    assert code not in caplog.text
    assert phone not in caplog.text
    assert "0912***6789" in caplog.text
    assert "AUTH_LOGIN_OTP" in caplog.text


def test_order_notification_maps_statuses(monkeypatch):
    from app.services import notification_service

    fake = _FakeProvider()
    monkeypatch.setattr(notification_service, "get_sms_provider", lambda: fake)
    monkeypatch.setattr(settings, "SMS_INTERNAL_ORDER_ALERT_RECIPIENTS", "09121110000")
    mapping = {
        "paid": (SmsEvent.ORDER_PAID, SmsEvent.INTERNAL_ORDER_PAID),
        "processing": (SmsEvent.ORDER_PROCESSING,),
        "shipped": (SmsEvent.ORDER_SHIPPED,),
        "delivered": (SmsEvent.ORDER_DELIVERED,),
        "inquiry_quoted": (SmsEvent.INQUIRY_QUOTED,),
        "cancelled": (SmsEvent.ORDER_CANCELLED,),
    }
    for status, events in mapping.items():
        before = len(fake.messages)
        asyncio.run(
            notification_service.notify_order_status_change(
                phone="09120000000",
                tracking_code="KZ-TEST",
                status=status,
            )
        )
        new_messages = fake.messages[before:]
        assert [m.event for m in new_messages] == list(events)
    before = len(fake.messages)
    asyncio.run(
        notification_service.notify_order_status_change(
            phone="09120000000",
            tracking_code="KZ-TEST",
            status="pending_payment",
        )
    )
    assert len(fake.messages) == before


def test_order_notification_failure_is_soft(monkeypatch, caplog):
    from app.services import notification_service

    class BoomProvider:
        async def send(self, message):
            raise SmsDeliveryError("Faraz SMS pattern was rejected")

    monkeypatch.setattr(notification_service, "get_sms_provider", lambda: BoomProvider())
    monkeypatch.setattr(settings, "SMS_INTERNAL_ORDER_ALERT_RECIPIENTS", "09121112233")
    caplog.set_level(logging.ERROR)
    asyncio.run(
        notification_service.notify_order_status_change(
            phone="09123456789",
            tracking_code="KZ-TESTSOFTFAIL",
            status="paid",
        )
    )
    assert "09123456789" not in caplog.text
    assert "09121112233" not in caplog.text
    assert "ORDER_PAID" in caplog.text
    assert "INTERNAL_ORDER_PAID" in caplog.text


def test_paid_customer_failure_still_attempts_internal(monkeypatch, caplog):
    from app.services import notification_service

    attempted: list[SmsEvent] = []

    class SelectiveBoom:
        async def send(self, message):
            attempted.append(message.event)
            if message.event is SmsEvent.ORDER_PAID:
                raise SmsDeliveryError("customer failed")

    monkeypatch.setattr(notification_service, "get_sms_provider", lambda: SelectiveBoom())
    monkeypatch.setattr(settings, "SMS_INTERNAL_ORDER_ALERT_RECIPIENTS", "09121110055")
    caplog.set_level(logging.ERROR)
    asyncio.run(
        notification_service.notify_purchase_paid(
            phone="09123456789",
            tracking_code="KZ-DUAL",
        )
    )
    assert attempted == [SmsEvent.ORDER_PAID, SmsEvent.INTERNAL_ORDER_PAID]


def test_internal_recipients_empty_skips_without_send(monkeypatch, caplog):
    from app.services import notification_service

    sent = []

    class Recorder:
        async def send(self, message):
            sent.append(message.event)

    monkeypatch.setattr(notification_service, "get_sms_provider", lambda: Recorder())
    monkeypatch.setattr(settings, "SMS_INTERNAL_ORDER_ALERT_RECIPIENTS", "")
    caplog.set_level(logging.WARNING)
    asyncio.run(notification_service.notify_internal_order_paid(tracking_code="KZ-NOOPS"))
    assert sent == []
    assert "no recipients configured" in caplog.text


@pytest.mark.usefixtures("override_database")
def test_password_reset_provider_failure_matches_unknown_phone(monkeypatch):
    async def _request(db, phone):
        if phone.endswith("99"):
            raise ValueError("No account found for this phone number")
        raise SmsDeliveryError("Faraz SMS delivery failed")

    monkeypatch.setattr("app.api.endpoints.auth.request_password_reset", _request)
    unknown = client.post(
        "/api/v1/auth/password-reset/request",
        json={"phone": "09120000099"},
    )
    failed = client.post(
        "/api/v1/auth/password-reset/request",
        json={"phone": "09120000088"},
    )
    assert unknown.status_code == 200
    assert failed.status_code == 200
    assert unknown.json().keys() == failed.json().keys()
    assert "dev_code" not in unknown.json() or unknown.json()["dev_code"] is None
    assert failed.json().get("dev_code") is None
    assert "Faraz" not in failed.text
    assert "delivery" not in failed.text.lower()
