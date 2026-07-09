"""SMS delivery service used by OTP flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class SmsMessage:
    receptor: str
    body: str
    template_token: str | None = None


class SmsProvider(Protocol):
    async def send(self, message: SmsMessage) -> None:
        ...


class ConsoleSmsProvider:
    """Local/dev provider: log OTPs instead of sending externally."""

    async def send(self, message: SmsMessage) -> None:
        logger.info("SMS(console) receptor=%s body=%s", message.receptor, message.body)


class KavenegarSmsProvider:
    """Kavenegar provider using their Verify Lookup API."""

    base_url = "https://api.kavenegar.com/v1"

    async def send(self, message: SmsMessage) -> None:
        if not settings.SMS_KAVENEGAR_API_KEY:
            raise ValueError("SMS_KAVENEGAR_API_KEY is required for kavenegar provider")

        if settings.SMS_KAVENEGAR_OTP_TEMPLATE:
            await self._send_verify_lookup(message)
            return

        await self._send_plain_sms(message)

    async def _send_verify_lookup(self, message: SmsMessage) -> None:
        template = settings.SMS_KAVENEGAR_OTP_TEMPLATE
        url = (
            f"{self.base_url}/{settings.SMS_KAVENEGAR_API_KEY}/verify/lookup.json"
            f"?receptor={message.receptor}&token={message.template_token or ''}&template={template}"
        )
        async with httpx.AsyncClient(timeout=settings.SMS_TIMEOUT_SECONDS) as client:
            response = await client.get(url)
            response.raise_for_status()

    async def _send_plain_sms(self, message: SmsMessage) -> None:
        sender = settings.SMS_KAVENEGAR_SENDER
        if not sender:
            raise ValueError(
                "SMS_KAVENEGAR_SENDER is required when SMS_KAVENEGAR_OTP_TEMPLATE is not set"
            )
        url = f"{self.base_url}/{settings.SMS_KAVENEGAR_API_KEY}/sms/send.json"
        payload = {
            "receptor": message.receptor,
            "sender": sender,
            "message": message.body,
        }
        async with httpx.AsyncClient(timeout=settings.SMS_TIMEOUT_SECONDS) as client:
            response = await client.post(url, data=payload)
            response.raise_for_status()


_provider: SmsProvider | None = None


def get_sms_provider() -> SmsProvider:
    global _provider
    if _provider is None:
        if settings.SMS_PROVIDER == "kavenegar":
            _provider = KavenegarSmsProvider()
        else:
            _provider = ConsoleSmsProvider()
    return _provider


def reset_sms_provider_for_tests() -> None:
    global _provider
    _provider = None
