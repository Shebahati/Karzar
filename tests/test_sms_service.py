"""SMS provider and OTP delivery integration tests."""

from app.core.config import settings
from app.main import app
from app.services import otp_service
from app.services.sms_service import (
    ConsoleSmsProvider,
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


def test_otp_request_sends_sms(monkeypatch):
    fake = _FakeProvider()
    monkeypatch.setattr(otp_service, "get_sms_provider", lambda: fake)
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)

    response = client.post("/api/v1/auth/otp/request", json={"phone": "09122223333"})
    assert response.status_code == 200
    assert len(fake.messages) == 1
    assert fake.messages[0].receptor == "09122223333"
    assert fake.messages[0].template_token is not None
