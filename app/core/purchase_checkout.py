"""Purchase-lane kill switch shared by checkout and payment init.

Inquiry checkout, SEP callback, and payment verify are not affected.
"""

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.errors import ErrorCode, api_error

PURCHASE_CHECKOUT_DISABLED_MESSAGE = (
    "خرید آنلاین موقتاً در حال به‌روزرسانی است. "
    "لطفاً کمی بعد دوباره تلاش کنید یا درخواست استعلام ثبت کنید."
)


def purchase_checkout_disabled_error() -> HTTPException:
    return api_error(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        error_code=ErrorCode.PURCHASE_CHECKOUT_TEMPORARILY_DISABLED,
        message=PURCHASE_CHECKOUT_DISABLED_MESSAGE,
    )


def raise_if_purchase_checkout_disabled() -> None:
    """Fail closed before any purchase checkout or payment-init side effect."""
    if not settings.PURCHASE_CHECKOUT_ENABLED:
        raise purchase_checkout_disabled_error()
