"""SMS delivery used by OTP and order notifications.

Routing is by ``SmsEvent``. OTP pattern codes are consulted only for
``AUTH_LOGIN_OTP`` and ``AUTH_PASSWORD_RESET``. A transactional event cannot
reach an OTP pattern, including when a caller attaches a ``code`` attribute.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_legacy_pattern_warnings: set[str] = set()


class SmsEvent(StrEnum):
    AUTH_LOGIN_OTP = "AUTH_LOGIN_OTP"
    AUTH_PASSWORD_RESET = "AUTH_PASSWORD_RESET"
    ORDER_PAID = "ORDER_PAID"
    INTERNAL_ORDER_PAID = "INTERNAL_ORDER_PAID"
    ORDER_PROCESSING = "ORDER_PROCESSING"
    ORDER_SHIPPED = "ORDER_SHIPPED"
    ORDER_DELIVERED = "ORDER_DELIVERED"
    INQUIRY_QUOTED = "INQUIRY_QUOTED"
    ORDER_CANCELLED = "ORDER_CANCELLED"


AUTH_OTP_EVENTS = frozenset({SmsEvent.AUTH_LOGIN_OTP, SmsEvent.AUTH_PASSWORD_RESET})

# Faraz pattern-backed transactional events (#242). Other order events stay on simple SMS
# or legacy skip when only auth OTP patterns exist.
FARAZ_TRANSACTIONAL_PATTERN_EVENTS = frozenset(
    {SmsEvent.ORDER_PAID, SmsEvent.INTERNAL_ORDER_PAID}
)


class SmsDeliveryError(Exception):
    """SMS delivery failed. The message must not contain OTP values, phones, or payloads."""


def mask_phone(phone: str) -> str:
    """Mask an Iranian mobile for logs: ``09123456789`` → ``0912***6789``."""
    text = (phone or "").strip()
    if len(text) < 8:
        return "***"
    return f"{text[:4]}***{text[-4:]}"


@dataclass(frozen=True)
class SmsMessage:
    receptor: str
    body: str
    event: SmsEvent
    attributes: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.event, SmsEvent):
            raise TypeError("SmsMessage.event must be an SmsEvent")
        object.__setattr__(self, "attributes", dict(self.attributes))


class SmsProvider(Protocol):
    async def send(self, message: SmsMessage) -> None: ...


class ConsoleSmsProvider:
    """Local/dev provider. Logs the event and a masked phone, never the OTP."""

    async def send(self, message: SmsMessage) -> None:
        logger.info(
            "SMS(console) event=%s receptor=%s",
            message.event.value,
            mask_phone(message.receptor),
        )


class KavenegarSmsProvider:
    """Kavenegar. Verify Lookup is auth-OTP only."""

    base_url = "https://api.kavenegar.com/v1"

    async def send(self, message: SmsMessage) -> None:
        try:
            await self._dispatch(message)
        except SmsDeliveryError:
            raise
        except Exception as exc:
            logger.error(
                "Kavenegar SMS delivery failed event=%s error_type=%s",
                message.event.value,
                type(exc).__name__,
            )
            raise SmsDeliveryError("Kavenegar SMS delivery failed") from None

    async def _dispatch(self, message: SmsMessage) -> None:
        if not settings.SMS_KAVENEGAR_API_KEY:
            raise SmsDeliveryError("Kavenegar is not configured")
        template = (settings.SMS_KAVENEGAR_OTP_TEMPLATE or "").strip()
        if message.event in AUTH_OTP_EVENTS and template:
            await self._send_verify_lookup(message, template)
            return
        await self._send_plain_sms(message)

    async def _send_verify_lookup(self, message: SmsMessage, template: str) -> None:
        token = (message.attributes.get("code") or "").strip()
        if not token:
            raise SmsDeliveryError("OTP code attribute is missing")
        url = (
            f"{self.base_url}/{settings.SMS_KAVENEGAR_API_KEY}/verify/lookup.json"
            f"?receptor={message.receptor}&token={token}&template={template}"
        )
        async with httpx.AsyncClient(timeout=settings.SMS_TIMEOUT_SECONDS) as client:
            response = await client.get(url)
            response.raise_for_status()

    async def _send_plain_sms(self, message: SmsMessage) -> None:
        sender = settings.SMS_KAVENEGAR_SENDER
        if not sender:
            raise SmsDeliveryError("Kavenegar sender is not configured")
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
    """FarazSMS / IranPayamak (Api-Key header).

    Auth OTP uses a pattern send. Transactional events never use an OTP pattern.
    When any OTP pattern is configured and no transactional pattern exists, the
    transactional send is skipped. Simple SMS remains only when no OTP pattern
    is configured at all (legacy deployments).
    """

    async def send(self, message: SmsMessage) -> None:
        try:
            await self._dispatch(message)
        except SmsDeliveryError:
            raise
        except Exception as exc:
            logger.error(
                "Faraz SMS delivery failed event=%s error_type=%s",
                message.event.value,
                type(exc).__name__,
            )
            raise SmsDeliveryError("Faraz SMS delivery failed") from None

    async def _dispatch(self, message: SmsMessage) -> None:
        if not settings.SMS_FARAZ_API_KEY:
            raise SmsDeliveryError("Faraz SMS is not configured")
        line = (settings.SMS_FARAZ_LINE_NUMBER or "").strip()
        if not line:
            raise SmsDeliveryError("Faraz line number is not configured")

        if message.event in AUTH_OTP_EVENTS:
            pattern = _auth_pattern_code(message.event)
            if pattern:
                await self._send_pattern(message, line, pattern)
                return
            if _any_otp_pattern_configured():
                logger.warning(
                    "Auth SMS has no pattern for event=%s; sending simple SMS "
                    "instead of another event's OTP pattern",
                    message.event.value,
                )
            await self._send_simple(message, line)
            return

        if message.event in FARAZ_TRANSACTIONAL_PATTERN_EVENTS:
            pattern = _transactional_pattern_code(message.event)
            if pattern:
                await self._send_transactional_pattern(message, line, pattern)
                return
            if _any_otp_pattern_configured():
                raise SmsDeliveryError(
                    f"Faraz transactional pattern is not configured for event={message.event.value}"
                )
            await self._send_simple(message, line)
            return

        # Other transactional events: legacy skip when auth OTP patterns exist.
        if _any_otp_pattern_configured():
            logger.warning(
                "Transactional SMS skipped because no event-specific Faraz pattern "
                "is configured event=%s",
                message.event.value,
            )
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
            raise SmsDeliveryError(f"Faraz SMS {context} returned an unexpected response")
        status = str(payload.get("status", "")).lower()
        if status and status != "success":
            raise SmsDeliveryError(f"Faraz SMS {context} was rejected")

    async def _send_auth_otp_pattern(self, message: SmsMessage, line: str, pattern_code: str) -> None:
        if message.event not in AUTH_OTP_EVENTS:
            raise SmsDeliveryError("Faraz OTP pattern send is only valid for auth OTP events")
        token = (message.attributes.get("code") or "").strip()
        if not token:
            raise SmsDeliveryError("OTP code attribute is missing")
        attr_name = (settings.SMS_FARAZ_OTP_ATTR or "code").strip() or "code"
        await self._post_pattern(
            message,
            line,
            pattern_code,
            attributes={attr_name: token},
        )

    async def _send_transactional_pattern(
        self, message: SmsMessage, line: str, pattern_code: str
    ) -> None:
        if message.event not in FARAZ_TRANSACTIONAL_PATTERN_EVENTS:
            raise SmsDeliveryError("Faraz transactional pattern send event is not supported")
        attr_name = (settings.SMS_FARAZ_ORDER_TRACKING_ATTR or "tracking_code").strip()
        if not attr_name:
            raise SmsDeliveryError("Faraz order tracking attribute name is not configured")
        tracking = (message.attributes.get(attr_name) or message.attributes.get("tracking_code") or "").strip()
        if not tracking:
            raise SmsDeliveryError("Order tracking_code attribute is missing")
        await self._post_pattern(
            message,
            line,
            pattern_code,
            attributes={attr_name: tracking},
        )

    async def _post_pattern(
        self,
        message: SmsMessage,
        line: str,
        pattern_code: str,
        *,
        attributes: dict[str, str],
    ) -> None:
        payload = {
            "code": pattern_code,
            "recipient": message.receptor,
            "attributes": attributes,
            "line_number": line,
            "number_format": "english",
        }
        url = f"{self._base()}/ws/v1/sms/pattern"
        async with httpx.AsyncClient(timeout=settings.SMS_TIMEOUT_SECONDS) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
            response.raise_for_status()
            self._ensure_success(response.json(), context="pattern")

    async def _send_pattern(self, message: SmsMessage, line: str, pattern_code: str) -> None:
        await self._send_auth_otp_pattern(message, line, pattern_code)

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


def _setting_text(value: str | None) -> str:
    return (value or "").strip()


def _any_otp_pattern_configured() -> bool:
    return any(
        _setting_text(value)
        for value in (
            settings.SMS_FARAZ_LOGIN_OTP_PATTERN_CODE,
            settings.SMS_FARAZ_PASSWORD_RESET_PATTERN_CODE,
            settings.SMS_FARAZ_OTP_PATTERN_CODE,
        )
    )


def _warn_legacy_pattern_once(kind: str, text: str) -> None:
    if kind in _legacy_pattern_warnings:
        return
    _legacy_pattern_warnings.add(kind)
    logger.warning(text)


def _transactional_pattern_code(event: SmsEvent) -> str | None:
    if event == SmsEvent.ORDER_PAID:
        return _setting_text(settings.SMS_FARAZ_ORDER_PAID_PATTERN_CODE) or None
    if event == SmsEvent.INTERNAL_ORDER_PAID:
        return _setting_text(settings.SMS_FARAZ_INTERNAL_ORDER_PAID_PATTERN_CODE) or None
    return None


def parse_internal_order_alert_recipients() -> list[str]:
    """Operational SMS recipients for internal paid-order alerts (may be empty)."""
    raw = (settings.SMS_INTERNAL_ORDER_ALERT_RECIPIENTS or "").strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _auth_pattern_code(event: SmsEvent) -> str | None:
    """Resolve an auth OTP pattern. Returns None when simple SMS is the legacy path.

    Never call this for order or inquiry events.
    """
    if event not in AUTH_OTP_EVENTS:
        return None
    legacy = _setting_text(settings.SMS_FARAZ_OTP_PATTERN_CODE)
    if event == SmsEvent.AUTH_LOGIN_OTP:
        specific = _setting_text(settings.SMS_FARAZ_LOGIN_OTP_PATTERN_CODE)
        if specific:
            return specific
        if legacy:
            _warn_legacy_pattern_once(
                "login",
                "SMS_FARAZ_OTP_PATTERN_CODE is deprecated and is being used for "
                "AUTH_LOGIN_OTP. Set SMS_FARAZ_LOGIN_OTP_PATTERN_CODE.",
            )
            return legacy
        return None
    specific = _setting_text(settings.SMS_FARAZ_PASSWORD_RESET_PATTERN_CODE)
    if specific:
        return specific
    if legacy:
        _warn_legacy_pattern_once(
            "password_reset",
            "SMS_FARAZ_OTP_PATTERN_CODE is a shared legacy pattern and is being used "
            "for AUTH_PASSWORD_RESET. Set SMS_FARAZ_PASSWORD_RESET_PATTERN_CODE.",
        )
        return legacy
    return None


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
    _legacy_pattern_warnings.clear()
