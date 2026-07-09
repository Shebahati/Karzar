"""Payment endpoints for order payment initialization and verification."""

import re

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.constants import TOMAN_TO_RIAL
from app.core.errors import ErrorCode, api_error
from app.core.rate_limit import get_rate_limiter
from app.crud import commerce as crud_commerce
from app.db.database import get_db
from app.db.models.commerce import OrderMode, OrderStatus, PaymentStatus
from app.db.models.user import User
from app.schemas.payment import (
    PaymentInitRequest,
    PaymentInitResponse,
    PaymentVerifyRequest,
    PaymentVerifyResponse,
)
from app.services.order_service import transition_order_status
from app.services.payment_service import (
    PaymentGatewayError,
    PaymentGatewayTimeoutError,
    PaymentVerifyFailedError,
    extract_stored_authority,
    get_payment_provider,
)

router = APIRouter()

_PAYMENT_INIT_MAX_ATTEMPTS = 20
_PAYMENT_INIT_WINDOW_SECONDS = 300


def _order_amount_rials(order) -> int:
    return int(order.estimated_total) * TOMAN_TO_RIAL


def _authority_matches_order(order, authority: str) -> bool:
    stored = extract_stored_authority(order.note)
    return stored is not None and stored == authority


async def _check_payment_init_rate_limit(user_id: int) -> None:
    retry_after = await get_rate_limiter().retry_after_if_limited(
        f"payment_init:{user_id}",
        _PAYMENT_INIT_MAX_ATTEMPTS,
        _PAYMENT_INIT_WINDOW_SECONDS,
    )
    if retry_after is not None:
        raise api_error(
            status.HTTP_429_TOO_MANY_REQUESTS,
            error_code=ErrorCode.RATE_LIMITED,
            message="Too many payment initialization attempts. Please try again later.",
            details=[
                {
                    "field": "order_id",
                    "message": f"Rate limited. Retry after {retry_after} seconds.",
                }
            ],
            headers={"Retry-After": str(retry_after)},
        )


def _raise_gateway_error(exc: Exception) -> None:
    if isinstance(exc, PaymentGatewayTimeoutError):
        raise api_error(
            status.HTTP_504_GATEWAY_TIMEOUT,
            error_code=ErrorCode.PAYMENT_GATEWAY_TIMEOUT,
            message=exc.message,
        ) from exc
    if isinstance(exc, PaymentVerifyFailedError):
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.PAYMENT_VERIFY_FAILED,
            message=exc.message,
        ) from exc
    if isinstance(exc, PaymentGatewayError):
        raise api_error(
            status.HTTP_502_BAD_GATEWAY,
            error_code=ErrorCode.PAYMENT_GATEWAY_ERROR,
            message=exc.message,
        ) from exc
    raise api_error(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code=ErrorCode.INTERNAL_ERROR,
        message="Unexpected payment processing error",
    ) from exc


def _assert_order_payable_by_user(order, current_user: User) -> None:
    if order.user_id is None:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.GUEST_ORDER_NOT_PAYABLE,
            message="برای پرداخت آنلاین باید وارد حساب کاربری شوید. لطفاً با شماره موبایل خود وارد شوید.",
        )
    if order.user_id != current_user.id:
        raise api_error(status.HTTP_403_FORBIDDEN, error_code=ErrorCode.FORBIDDEN, message="Access denied")


@router.post("/init", response_model=PaymentInitResponse, summary="Initialize payment for an order")
async def payment_init(
    payload: PaymentInitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    await _check_payment_init_rate_limit(current_user.id)

    order = await crud_commerce.get_order_by_id(db, payload.order_id)
    if not order:
        raise api_error(status.HTTP_404_NOT_FOUND, error_code=ErrorCode.NOT_FOUND, message="Order not found")
    _assert_order_payable_by_user(order, current_user)
    if order.mode != OrderMode.PURCHASE:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.BAD_REQUEST,
            message="Payment is only available for purchase orders",
        )
    if order.payment_status == PaymentStatus.PAID.value or order.status == OrderStatus.PAID.value:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Order is already paid",
        )
    if order.status != OrderStatus.PENDING_PAYMENT.value:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Order is not in payable state",
        )
    if order.estimated_total is None:
        raise api_error(status.HTTP_400_BAD_REQUEST, error_code=ErrorCode.BAD_REQUEST, message="Order total is missing")

    stored_authority = extract_stored_authority(order.note)
    if stored_authority:
        callback_url = settings.PAYMENT_CALLBACK_URL or "http://localhost:8000/api/v1/payments/verify"
        return PaymentInitResponse(
            authority=stored_authority,
            payment_url=f"{callback_url}?authority={stored_authority}&status=OK",
        )

    callback_url = settings.PAYMENT_CALLBACK_URL or "http://localhost:8000/api/v1/payments/verify"
    amount_rials = _order_amount_rials(order)
    try:
        result = await get_payment_provider().init_payment(
            amount_rials=amount_rials,
            description=f"Karzar order {order.tracking_code}",
            callback_url=callback_url,
        )
    except (PaymentGatewayError, PaymentGatewayTimeoutError) as exc:
        await get_rate_limiter().record_failure(
            f"payment_init:{current_user.id}", _PAYMENT_INIT_WINDOW_SECONDS
        )
        _raise_gateway_error(exc)

    await get_rate_limiter().clear(f"payment_init:{current_user.id}")
    order.note = f"{(order.note + ' | ') if order.note else ''}authority={result.authority}"
    await db.commit()
    return PaymentInitResponse(authority=result.authority, payment_url=result.payment_url)


@router.post("/verify", response_model=PaymentVerifyResponse, summary="Verify payment callback")
async def payment_verify(
    payload: PaymentVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = await crud_commerce.get_order_by_id(db, payload.order_id)
    if not order:
        raise api_error(status.HTTP_404_NOT_FOUND, error_code=ErrorCode.NOT_FOUND, message="Order not found")
    _assert_order_payable_by_user(order, current_user)
    if order.mode != OrderMode.PURCHASE:
        raise api_error(status.HTTP_400_BAD_REQUEST, error_code=ErrorCode.BAD_REQUEST, message="Invalid order mode")
    if order.estimated_total is None:
        raise api_error(status.HTTP_400_BAD_REQUEST, error_code=ErrorCode.BAD_REQUEST, message="Order total is missing")

    if order.payment_status == PaymentStatus.PAID.value:
        ref_match = re.search(r"ref_id=([^\s|]+)", order.note or "")
        return PaymentVerifyResponse(
            order_id=order.id,
            payment_status=order.payment_status,
            status=order.status,
            ref_id=ref_match.group(1) if ref_match else None,
        )

    if not _authority_matches_order(order, payload.authority):
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.PAYMENT_VERIFY_FAILED,
            message="Payment authority does not match this order",
        )

    amount_rials = _order_amount_rials(order)
    try:
        result = await get_payment_provider().verify_payment(
            authority=payload.authority,
            amount_rials=amount_rials,
        )
    except (PaymentGatewayError, PaymentGatewayTimeoutError, PaymentVerifyFailedError) as exc:
        order.payment_status = PaymentStatus.FAILED.value
        await db.commit()
        _raise_gateway_error(exc)

    if result.success:
        if order.status == OrderStatus.PENDING_PAYMENT.value:
            await transition_order_status(db, order, OrderStatus.PAID.value)
        order.payment_status = PaymentStatus.PAID.value
    else:
        order.payment_status = PaymentStatus.FAILED.value

    if result.ref_id:
        order.note = f"{(order.note + ' | ') if order.note else ''}ref_id={result.ref_id}"
    await db.commit()

    refreshed = await crud_commerce.get_order_by_id(db, payload.order_id)
    return PaymentVerifyResponse(
        order_id=refreshed.id,
        payment_status=refreshed.payment_status,
        status=refreshed.status,
        ref_id=result.ref_id,
    )
