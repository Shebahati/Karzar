"""Payment endpoints for order payment initialization and verification."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.errors import ErrorCode, api_error
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
from app.services.payment_service import get_payment_provider

router = APIRouter()


@router.post("/init", response_model=PaymentInitResponse, summary="Initialize payment for an order")
async def payment_init(
    payload: PaymentInitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = await crud_commerce.get_order_by_id(db, payload.order_id)
    if not order:
        raise api_error(status.HTTP_404_NOT_FOUND, error_code=ErrorCode.NOT_FOUND, message="Order not found")
    if order.user_id != current_user.id:
        raise api_error(status.HTTP_403_FORBIDDEN, error_code=ErrorCode.FORBIDDEN, message="Access denied")
    if order.mode != OrderMode.PURCHASE:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.BAD_REQUEST,
            message="Payment is only available for purchase orders",
        )
    if order.status != OrderStatus.PENDING_PAYMENT.value:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Order is not in payable state",
        )
    if order.estimated_total is None:
        raise api_error(status.HTTP_400_BAD_REQUEST, error_code=ErrorCode.BAD_REQUEST, message="Order total is missing")

    callback_url = settings.PAYMENT_CALLBACK_URL or "http://localhost:8000/api/v1/payments/verify"
    amount_rials = int(order.estimated_total)
    result = await get_payment_provider().init_payment(
        amount_rials=amount_rials,
        description=f"Karzar order {order.tracking_code}",
        callback_url=callback_url,
    )
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
    if order.user_id != current_user.id:
        raise api_error(status.HTTP_403_FORBIDDEN, error_code=ErrorCode.FORBIDDEN, message="Access denied")
    if order.mode != OrderMode.PURCHASE:
        raise api_error(status.HTTP_400_BAD_REQUEST, error_code=ErrorCode.BAD_REQUEST, message="Invalid order mode")
    if order.estimated_total is None:
        raise api_error(status.HTTP_400_BAD_REQUEST, error_code=ErrorCode.BAD_REQUEST, message="Order total is missing")

    result = await get_payment_provider().verify_payment(
        authority=payload.authority,
        amount_rials=int(order.estimated_total),
    )
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
