"""SMS provider and OTP delivery integration tests."""

from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import settings
from app.main import app
from app.services import otp_service
from app.services.sms_service import (
    ConsoleSmsProvider,
    FarazSmsProvider,
    SmsMessage,
    get_sms_provider,
    reset_sms_provider_for_tests,
)
from fastapi.testclient import TestClient

client = TestClient(app)


class _FakeProvider:
    def __init__(self):
        self.messages = []

    async def send(self, message):
        self.messages.append(message)


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


def test_otp_request_sends_sms(monkeypatch):
    fake = _FakeProvider()
    monkeypatch.setattr(otp_service, "get_sms_provider", lambda: fake)
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)

    response = client.post("/api/v1/auth/otp/request", json={"phone": "09122223333"})
    assert response.status_code == 200
    assert len(fake.messages) == 1
    assert fake.messages[0].receptor == "09122223333"
    assert fake.messages[0].template_token is not None


def test_faraz_pattern_send(monkeypatch):
    import asyncio

    monkeypatch.setattr(settings, "SMS_FARAZ_API_KEY", "test-key")
    monkeypatch.setattr(settings, "SMS_FARAZ_LINE_NUMBER", "90008361")
    monkeypatch.setattr(settings, "SMS_FARAZ_OTP_PATTERN_CODE", "PAT123")
    monkeypatch.setattr(settings, "SMS_FARAZ_OTP_ATTR", "code")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"status": "success", "data": 1, "message": ""}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("app.services.sms_service.httpx.AsyncClient", return_value=mock_client):
        asyncio.run(
            FarazSmsProvider().send(
                SmsMessage(receptor="09120000000", body="x", template_token="4321")
            )
        )

    kwargs = mock_client.post.await_args.kwargs
    assert kwargs["json"]["code"] == "PAT123"
    assert kwargs["json"]["recipient"] == "09120000000"
    assert kwargs["json"]["attributes"] == {"code": "4321"}
    assert kwargs["headers"]["Api-Key"] == "test-key"
