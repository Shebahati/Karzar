"""SMS notifications for order lifecycle events."""

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models.commerce import OrderStatus
from app.services.sms_service import (
    SmsEvent,
    SmsMessage,
    get_sms_provider,
    mask_phone,
    parse_internal_order_alert_recipients,
)

logger = get_logger(__name__)

_NOTIFY_STATUSES = frozenset(
    {
        OrderStatus.PAID.value,
        OrderStatus.PROCESSING.value,
        OrderStatus.SHIPPED.value,
        OrderStatus.DELIVERED.value,
        OrderStatus.INQUIRY_QUOTED.value,
        OrderStatus.CANCELLED.value,
    }
)

_STATUS_TEMPLATES: dict[str, str] = {
    OrderStatus.PAID.value: "سفارش {tracking_code} پرداخت شد.",
    OrderStatus.PROCESSING.value: "سفارش {tracking_code} در حال آماده‌سازی است.",
    OrderStatus.SHIPPED.value: "سفارش {tracking_code} ارسال شد.",
    OrderStatus.DELIVERED.value: "سفارش {tracking_code} تحویل داده شد.",
    OrderStatus.INQUIRY_QUOTED.value: "پیش‌فاکتور استعلام {tracking_code} صادر شد.",
    OrderStatus.CANCELLED.value: "سفارش {tracking_code} لغو شد.",
}

_STATUS_EVENTS: dict[str, SmsEvent] = {
    OrderStatus.PAID.value: SmsEvent.ORDER_PAID,
    OrderStatus.PROCESSING.value: SmsEvent.ORDER_PROCESSING,
    OrderStatus.SHIPPED.value: SmsEvent.ORDER_SHIPPED,
    OrderStatus.DELIVERED.value: SmsEvent.ORDER_DELIVERED,
    OrderStatus.INQUIRY_QUOTED.value: SmsEvent.INQUIRY_QUOTED,
    OrderStatus.CANCELLED.value: SmsEvent.ORDER_CANCELLED,
}

_INTERNAL_PAID_TEMPLATE = "سفارش پرداخت‌شده: {tracking_code}"


def _order_tracking_attributes(tracking_code: str) -> dict[str, str]:
    attr_name = (settings.SMS_FARAZ_ORDER_TRACKING_ATTR or "tracking_code").strip() or "tracking_code"
    return {attr_name: tracking_code}


async def _send_order_sms_soft(
    *,
    receptor: str,
    body: str,
    event: SmsEvent,
    tracking_code: str,
    log_context: str,
) -> None:
    try:
        await get_sms_provider().send(
            SmsMessage(
                receptor=receptor,
                body=body,
                event=event,
                attributes=_order_tracking_attributes(tracking_code),
            )
        )
    except Exception as exc:
        logger.error(
            "%s SMS failed tracking=%s event=%s receptor=%s provider=%s error_type=%s",
            log_context,
            tracking_code,
            event.value,
            mask_phone(receptor),
            settings.SMS_PROVIDER,
            type(exc).__name__,
        )


async def notify_internal_order_paid(*, tracking_code: str) -> None:
    """Internal/admin alert for a newly paid purchase order (soft-failing)."""
    recipients = parse_internal_order_alert_recipients()
    if not recipients:
        logger.warning(
            "Internal order paid SMS skipped: no recipients configured tracking=%s",
            tracking_code,
        )
        return
    body = _INTERNAL_PAID_TEMPLATE.format(tracking_code=tracking_code)
    for receptor in recipients:
        await _send_order_sms_soft(
            receptor=receptor,
            body=body,
            event=SmsEvent.INTERNAL_ORDER_PAID,
            tracking_code=tracking_code,
            log_context="Internal order",
        )


async def notify_purchase_paid(*, phone: str, tracking_code: str) -> None:
    """Customer + internal paid notifications; failures do not propagate."""
    template = _STATUS_TEMPLATES.get(OrderStatus.PAID.value)
    if not template:
        return
    body = template.format(tracking_code=tracking_code)
    await _send_order_sms_soft(
        receptor=phone,
        body=body,
        event=SmsEvent.ORDER_PAID,
        tracking_code=tracking_code,
        log_context="Order status",
    )
    await notify_internal_order_paid(tracking_code=tracking_code)


async def notify_order_status_change(
    *,
    phone: str,
    tracking_code: str,
    status: str,
) -> None:
    if status == OrderStatus.PAID.value:
        await notify_purchase_paid(phone=phone, tracking_code=tracking_code)
        return

    event = _STATUS_EVENTS.get(status)
    if event is None or status not in _NOTIFY_STATUSES:
        return
    template = _STATUS_TEMPLATES.get(status)
    if not template:
        return
    body = template.format(tracking_code=tracking_code)
    await _send_order_sms_soft(
        receptor=phone,
        body=body,
        event=event,
        tracking_code=tracking_code,
        log_context="Order status",
    )
