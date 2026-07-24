"""SMS delivery service used by OTP flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

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


class FarazSmsProvider:
    """FarazSMS / IranPayamak REST API (Api-Key header).

    Prefer pattern send for OTP (instant). Falls back to simple SMS when no
    pattern code is configured. Docs: https://docs.farazsms.com
    """

    async def send(self, message: SmsMessage) -> None:
        if not settings.SMS_FARAZ_API_KEY:
            raise ValueError("SMS_FARAZ_API_KEY is required for faraz provider")
        line = (settings.SMS_FARAZ_LINE_NUMBER or "").strip()
        if not line:
            raise ValueError("SMS_FARAZ_LINE_NUMBER is required for faraz provider")

        if (settings.SMS_FARAZ_OTP_PATTERN_CODE or "").strip():
            await self._send_pattern(message, line)
            return
        await self._send_simple(message, line)

    def _headers(self) -> dict[str, str]:
        return {
            "Api-Key": settings.SMS_FARAZ_API_KEY or "",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _base(self) -> str:
        return (settings.SMS_FARAZ_BASE_URL or "https://api.iranpayamak.com").rstrip("/")

    @staticmethod
    def _ensure_success(payload: Any, *, context: str) -> None:
        if not isinstance(payload, dict):
            raise RuntimeError(f"Faraz SMS {context}: unexpected response type")
        status = str(payload.get("status", "")).lower()
        if status and status != "success":
            raise RuntimeError(
                f"Faraz SMS {context} failed: {payload.get('message') or payload}"
            )

    async def _send_pattern(self, message: SmsMessage, line: str) -> None:
        attr_name = (settings.SMS_FARAZ_OTP_ATTR or "code").strip() or "code"
        token = message.template_token or ""
        payload = {
            "code": settings.SMS_FARAZ_OTP_PATTERN_CODE,
            "recipient": message.receptor,
            "attributes": {attr_name: token},
            "line_number": line,
            "number_format": "english",
        }
        url = f"{self._base()}/ws/v1/sms/pattern"
        async with httpx.AsyncClient(timeout=settings.SMS_TIMEOUT_SECONDS) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
            response.raise_for_status()
            self._ensure_success(response.json(), context="pattern")

    async def _send_simple(self, message: SmsMessage, line: str) -> None:
        payload = {
            "text": message.body,
            "recipients": [message.receptor],
            "line_number": line,
            "number_format": "english",
        }
        url = f"{self._base()}/ws/v1/sms/simple"
        async with httpx.AsyncClient(timeout=settings.SMS_TIMEOUT_SECONDS) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
            response.raise_for_status()
            self._ensure_success(response.json(), context="simple")


_provider: SmsProvider | None = None


def get_sms_provider() -> SmsProvider:
    global _provider
    if _provider is None:
        if settings.SMS_PROVIDER == "kavenegar":
            _provider = KavenegarSmsProvider()
        elif settings.SMS_PROVIDER == "faraz":
            _provider = FarazSmsProvider()
        else:
            _provider = ConsoleSmsProvider()
    return _provider


def reset_sms_provider_for_tests() -> None:
    global _provider
    _provider = None
