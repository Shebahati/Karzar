"""Payment endpoints for order payment initialization and verification."""

from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Header, Query, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_super_admin_with_step_up,
    get_optional_current_user,
)
from app.core.config import settings
from app.core.errors import ErrorCode, api_error
from app.core.payment_url import assert_allowed_payment_url
from app.core.rate_limit import get_rate_limiter
from app.crud import commerce as crud_commerce
from app.crud import platform as crud_platform
from app.db.database import get_db
from app.db.models.commerce import OrderStatus, PaymentStatus
from app.db.models.user import User
from app.schemas.payment import (
    PaymentInitRequest,
    PaymentInitResponse,
    PaymentRefundRequest,
    PaymentRefundResponse,
    PaymentVerifyRequest,
    PaymentVerifyResponse,
)
from app.services.audit_service import record_audit
from app.services.order_expiry_service import cancel_expired_pending_payment_orders
from app.services.order_service import transition_order_status
from app.services.payment_flow_service import (
    get_order_payment_authority,
    get_order_payment_ref_id,
    initialize_order_payment,
    order_amount_rials,
    verify_order_payment,
)
from app.services.payment_ledger_service import record_payment_refunded
from app.services.payment_service import (
    PaymentGatewayError,
    PaymentGatewayTimeoutError,
    PaymentVerifyFailedError,
    get_payment_provider,
)

router = APIRouter()

_PAYMENT_INIT_MAX_ATTEMPTS = 20
_PAYMENT_INIT_WINDOW_SECONDS = 300
_PUBLIC_VERIFY_MAX_ATTEMPTS = 30
_PUBLIC_VERIFY_WINDOW_SECONDS = 300


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


async def _check_public_verify_rate_limit(order_id: int) -> None:
    retry_after = await get_rate_limiter().retry_after_if_limited(
        f"payment_verify:{order_id}",
        _PUBLIC_VERIFY_MAX_ATTEMPTS,
        _PUBLIC_VERIFY_WINDOW_SECONDS,
    )
    if retry_after is not None:
        raise api_error(
            status.HTTP_429_TOO_MANY_REQUESTS,
            error_code=ErrorCode.RATE_LIMITED,
            message="Too many payment verification attempts. Please try again later.",
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
    if isinstance(exc, ValueError):
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.BAD_REQUEST,
            message=str(exc),
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


def _build_redirect_url(base_url: str, *, tracking_code: str, paid: bool) -> str:
    query = urlencode(
        {
            "ref": tracking_code,
            "mode": "purchase",
            "paid": "1" if paid else "0",
        }
    )
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{query}"


def _client_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    return request.client.host


@router.post("/init", response_model=PaymentInitResponse, summary="Initialize payment for an order")
async def payment_init(
    payload: PaymentInitRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    idempotency_scope = "payment_init:anonymous"
    if current_user is not None:
        idempotency_scope = f"payment_init:user:{current_user.id}"
    if idempotency_key and idempotency_key.strip():
        normalized_key = idempotency_key.strip()
        cached = await crud_platform.get_idempotency_record(
            db, scope=idempotency_scope, key=normalized_key
        )
        if cached is not None and cached.status_code > 0:
            return JSONResponse(status_code=cached.status_code, content=cached.response_body)
        reserved = await crud_platform.reserve_idempotency_record(
            db,
            scope=idempotency_scope,
            key=normalized_key,
            expires_at=datetime.now(UTC) + timedelta(hours=settings.IDEMPOTENCY_TTL_HOURS),
        )
        if not reserved:
            existing = await crud_platform.get_idempotency_record(
                db, scope=idempotency_scope, key=normalized_key
            )
            if existing is not None and existing.status_code > 0:
                return JSONResponse(status_code=existing.status_code, content=existing.response_body)
            raise api_error(
                status.HTTP_409_CONFLICT,
                error_code=ErrorCode.CONFLICT,
                message="Another request with this Idempotency-Key is currently in progress",
            )
        await db.commit()

    await cancel_expired_pending_payment_orders(db)

    order = await crud_commerce.get_order_by_id_for_update(db, payload.order_id)
    if not order:
        raise api_error(status.HTTP_404_NOT_FOUND, error_code=ErrorCode.NOT_FOUND, message="Order not found")
    if order.user_id is None:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.GUEST_ORDER_NOT_PAYABLE,
            message="برای پرداخت آنلاین باید وارد حساب کاربری شوید. لطفاً با شماره موبایل خود وارد شوید.",
        )
    if current_user is None:
        raise api_error(
            status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.UNAUTHORIZED,
            message="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    await _check_payment_init_rate_limit(current_user.id)
    _assert_order_payable_by_user(order, current_user)

    try:
        result = await initialize_order_payment(db, order, ip_address=_client_ip(request))
    except (PaymentGatewayError, PaymentGatewayTimeoutError, ValueError) as exc:
        if idempotency_key and idempotency_key.strip():
            await crud_platform.delete_idempotency_record(
                db,
                scope=idempotency_scope,
                key=idempotency_key.strip(),
            )
            await db.commit()
        await get_rate_limiter().record_failure(
            f"payment_init:{current_user.id}", _PAYMENT_INIT_WINDOW_SECONDS
        )
        _raise_gateway_error(exc)

    await get_rate_limiter().clear(f"payment_init:{current_user.id}")
    try:
        safe_url = assert_allowed_payment_url(result.payment_url)
    except ValueError as exc:
        _raise_gateway_error(exc)
    response = PaymentInitResponse(authority=result.authority, payment_url=safe_url)

    if idempotency_key and idempotency_key.strip():
        await crud_platform.finalize_idempotency_record(
            db,
            scope=idempotency_scope,
            key=idempotency_key.strip(),
            status_code=status.HTTP_200_OK,
            response_body=response.model_dump(mode="json"),
            expires_at=datetime.now(UTC) + timedelta(hours=settings.IDEMPOTENCY_TTL_HOURS),
        )
    await db.commit()
    return response


@router.get("/callback", summary="Public payment gateway callback (redirect)")
async def payment_callback(
    request: Request,
    Authority: str | None = Query(None),
    Status: str | None = Query(None),
    authority: str | None = Query(None),
    status_value: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    resolved_authority = Authority or authority
    resolved_status = Status or status_value

    if not resolved_authority:
        return RedirectResponse(settings.PAYMENT_FAILURE_REDIRECT_URL, status_code=status.HTTP_302_FOUND)

    order = await crud_commerce.get_order_by_payment_authority(db, resolved_authority)
    if order is None:
        return RedirectResponse(settings.PAYMENT_FAILURE_REDIRECT_URL, status_code=status.HTTP_302_FOUND)

    await _check_public_verify_rate_limit(order.id)

    try:
        await verify_order_payment(
            db,
            order,
            authority=resolved_authority,
            gateway_status=resolved_status,
            ip_address=_client_ip(request),
        )
        await db.commit()
        return RedirectResponse(
            _build_redirect_url(settings.PAYMENT_SUCCESS_REDIRECT_URL, tracking_code=order.tracking_code, paid=True),
            status_code=status.HTTP_302_FOUND,
        )
    except Exception:
        await db.commit()
        return RedirectResponse(
            _build_redirect_url(settings.PAYMENT_FAILURE_REDIRECT_URL, tracking_code=order.tracking_code, paid=False),
            status_code=status.HTTP_302_FOUND,
        )


@router.post("/verify", response_model=PaymentVerifyResponse, summary="Verify payment callback")
async def payment_verify(
    payload: PaymentVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    """
    Verify a gateway return by authority (order resolved server-side).
    Optional order_id must match the bound order when supplied.
    Auth is optional — authority is a capability token (same model as GET /callback).
    Authenticated owners are still ownership-checked when the order has a user_id.
    """
    authority = payload.authority.strip()
    if not authority:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.BAD_REQUEST,
            message="Payment authority is required",
        )

    order = await crud_commerce.get_order_by_payment_authority_for_update(db, authority)
    if not order:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Order not found for this payment authority",
        )

    if payload.order_id is not None and payload.order_id != order.id:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.BAD_REQUEST,
            message="Payment authority does not match this order",
        )

    await _check_public_verify_rate_limit(order.id)

    if current_user is not None and order.user_id is not None:
        _assert_order_payable_by_user(order, current_user)

    if order.payment_status == PaymentStatus.PAID.value:
        return PaymentVerifyResponse(
            order_id=order.id,
            payment_status=order.payment_status,
            status=order.status,
            ref_id=get_order_payment_ref_id(order),
            tracking_code=order.tracking_code,
        )

    try:
        result = await verify_order_payment(
            db,
            order,
            authority=authority,
            gateway_status=payload.status,
            ip_address=_client_ip(request),
        )
        await db.commit()
    except (PaymentGatewayError, PaymentGatewayTimeoutError, PaymentVerifyFailedError, ValueError) as exc:
        await db.commit()
        _raise_gateway_error(exc)

    refreshed = await crud_commerce.get_order_by_id(db, order.id)
    return PaymentVerifyResponse(
        order_id=refreshed.id,
        payment_status=refreshed.payment_status,
        status=refreshed.status,
        ref_id=result.ref_id,
        tracking_code=refreshed.tracking_code,
    )


@router.post("/refund", response_model=PaymentRefundResponse, summary="Refund a paid order via gateway")
async def payment_refund(
    payload: PaymentRefundRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_with_step_up),
):
    order = await crud_commerce.get_order_by_id_for_update(db, payload.order_id)
    if not order:
        raise api_error(status.HTTP_404_NOT_FOUND, error_code=ErrorCode.NOT_FOUND, message="Order not found")
    if order.payment_status != PaymentStatus.PAID.value:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Only paid orders can be refunded",
        )

    ref_id = get_order_payment_ref_id(order)
    if not ref_id:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.BAD_REQUEST,
            message="Payment reference id not found on order",
        )
    amount_rials = order_amount_rials(order)

    try:
        result = await get_payment_provider().refund_payment(ref_id=ref_id, amount_rials=amount_rials)
    except (PaymentGatewayError, PaymentGatewayTimeoutError, PaymentVerifyFailedError) as exc:
        _raise_gateway_error(exc)

    if result.success:
        order.payment_status = PaymentStatus.REFUNDED.value
        if result.refund_id:
            order.payment_refund_id = result.refund_id
        if order.status != OrderStatus.CANCELLED.value:
            await transition_order_status(
                db,
                order,
                OrderStatus.CANCELLED.value,
                actor="admin",
                event_description="سفارش پس از بازپرداخت لغو شد",
            )
        await record_payment_refunded(
            db,
            order,
            authority=get_order_payment_authority(order),
            ref_id=ref_id,
            refund_id=result.refund_id,
            ip_address=_client_ip(request),
        )
        await record_audit(
            db,
            actor_user_id=current_user.id,
            action="payment_refund",
            entity_type="order",
            entity_id=order.id,
            details={"refund_id": result.refund_id, "ref_id": ref_id},
        )
        await db.commit()

    refreshed = await crud_commerce.get_order_by_id(db, payload.order_id)
    return PaymentRefundResponse(
        order_id=refreshed.id,
        payment_status=refreshed.payment_status,
        status=refreshed.status,
        refund_id=result.refund_id,
    )
