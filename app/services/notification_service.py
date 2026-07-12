"""SMS notifications for order lifecycle events."""

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models.commerce import OrderStatus
from app.services.sms_service import SmsMessage, get_sms_provider

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


async def notify_order_status_change(
    *,
    phone: str,
    tracking_code: str,
    status: str,
) -> None:
    if status not in _NOTIFY_STATUSES:
        return
    template = _STATUS_TEMPLATES.get(status)
    if not template:
        return
    body = template.format(tracking_code=tracking_code)
    try:
        await get_sms_provider().send(SmsMessage(receptor=phone, body=body))
    except Exception:
        logger.exception(
            "Order status SMS failed tracking=%s status=%s provider=%s",
            tracking_code,
            status,
            settings.SMS_PROVIDER,
        )
