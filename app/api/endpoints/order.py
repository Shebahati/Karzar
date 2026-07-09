"""Order endpoints: admin management, customer history, and public tracking."""

from typing import Optional

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_current_super_admin
from app.core.errors import ErrorCode, api_error
from app.core.security import verify_step_up_token
from app.crud import commerce as crud_commerce
from app.db.database import get_db
from app.db.models.commerce import Order, OrderMode, OrderStatus
from app.db.models.user import User
from app.schemas.common import build_pagination_meta, resolve_pagination
from app.schemas.order import (
    OrderDetailResponse,
    OrderItemResponse,
    OrderListResponse,
    OrderStatusUpdateRequest,
    OrderSummary,
    OrderTrackingItemResponse,
    OrderTrackingResponse,
)
from app.services.order_service import (
    allowed_next_statuses,
    payment_status_label,
    status_label,
    transition_order_status,
)
from app.utils.storefront_catalog import decimal_to_api_string

router = APIRouter()

_VALID_ORDER_SORTS = frozenset({"newest", "oldest", "total_asc", "total_desc"})

# Statuses that require a step-up token because they are irreversible/financial.
_SENSITIVE_STATUSES = frozenset({OrderStatus.CANCELLED.value})


def _to_summary(order: Order) -> OrderSummary:
    return OrderSummary(
        id=order.id,
        tracking_code=order.tracking_code,
        mode=order.mode.value if isinstance(order.mode, OrderMode) else str(order.mode),
        status=order.status,
        status_label=status_label(order.status),
        payment_status=order.payment_status,
        payment_status_label=payment_status_label(order.payment_status),
        estimated_total=decimal_to_api_string(order.estimated_total),
        customer_full_name=order.customer_full_name,
        customer_phone=order.customer_phone,
        company_name=order.company_name,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


def _to_detail(order: Order) -> OrderDetailResponse:
    summary = _to_summary(order)
    return OrderDetailResponse(
        **summary.model_dump(),
        customer_is_guest=order.customer_is_guest,
        note=order.note,
        shipping=order.shipping,
        user_id=order.user_id,
        items=[
            OrderItemResponse(
                id=item.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=decimal_to_api_string(item.unit_price),
            )
            for item in order.items
        ],
        allowed_next_statuses=allowed_next_statuses(order.status),
    )


@router.get(
    "/me",
    response_model=OrderListResponse,
    summary="List the authenticated customer's orders",
)
async def list_my_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    orders, total = await crud_commerce.list_orders(
        db, skip=skip, limit=limit, user_id=current_user.id
    )
    return {
        "data": [_to_summary(order) for order in orders],
        "meta": build_pagination_meta(total_count=total, skip=skip, limit=limit),
    }


@router.get(
    "/track/{tracking_code}",
    response_model=OrderTrackingResponse,
    summary="Public order tracking by code",
)
async def track_order(tracking_code: str, db: AsyncSession = Depends(get_db)):
    order = await crud_commerce.get_order_by_tracking_code(db, tracking_code.strip())
    if not order:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Order '{tracking_code}' not found",
        )
    return OrderTrackingResponse(
        tracking_code=order.tracking_code,
        mode=order.mode.value if isinstance(order.mode, OrderMode) else str(order.mode),
        status=order.status,
        status_label=status_label(order.status),
        estimated_total=decimal_to_api_string(order.estimated_total),
        created_at=order.created_at,
        items=[
            OrderTrackingItemResponse(
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=decimal_to_api_string(item.unit_price),
            )
            for item in order.items
        ],
    )


@router.get(
    "",
    response_model=OrderListResponse,
    summary="List orders (admin)",
)
async def list_orders(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    page: Optional[int] = Query(None, ge=1, description="1-based page number (alternative to skip)"),
    page_size: Optional[int] = Query(None, ge=1, le=200, description="Page size (alternative to limit)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status code"),
    mode: Optional[str] = Query(None, description="Filter by mode: purchase or inquiry"),
    payment_status: Optional[str] = Query(None, description="Filter by payment status"),
    phone: Optional[str] = Query(None, description="Filter by customer phone"),
    sort: str = Query("newest", description="Sort key: newest, oldest, total_asc, total_desc"),
):
    if sort not in _VALID_ORDER_SORTS:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Invalid sort key",
            details=[{"field": "sort", "message": f"must be one of: {', '.join(sorted(_VALID_ORDER_SORTS))}"}],
        )

    resolved_skip, resolved_limit = resolve_pagination(
        page=page, page_size=page_size, skip=skip, limit=limit
    )

    if status_filter is not None:
        try:
            status_filter = OrderStatus(status_filter).value
        except ValueError:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="Invalid status filter",
                details=[{"field": "status", "message": "unknown status code"}],
            )

    mode_enum: Optional[OrderMode] = None
    if mode is not None:
        try:
            mode_enum = OrderMode(mode)
        except ValueError:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="Invalid mode filter",
                details=[{"field": "mode", "message": "must be 'purchase' or 'inquiry'"}],
            )

    orders, total = await crud_commerce.list_orders(
        db,
        skip=resolved_skip,
        limit=resolved_limit,
        status=status_filter,
        mode=mode_enum,
        payment_status=payment_status,
        phone=phone,
        sort=sort,
    )
    return {
        "data": [_to_summary(order) for order in orders],
        "meta": build_pagination_meta(total_count=total, skip=resolved_skip, limit=resolved_limit),
    }


@router.get(
    "/{order_id}",
    response_model=OrderDetailResponse,
    summary="Get order detail (admin)",
)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    order = await crud_commerce.get_order_by_id(db, order_id)
    if not order:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Order '{order_id}' not found",
        )
    return _to_detail(order)


@router.patch(
    "/{order_id}/status",
    response_model=OrderDetailResponse,
    summary="Update order status (admin)",
)
async def update_order_status(
    order_id: int,
    payload: OrderStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
    x_step_up_token: Optional[str] = Header(None, alias="X-Step-Up-Token"),
):
    order = await crud_commerce.get_order_by_id(db, order_id)
    if not order:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Order '{order_id}' not found",
        )

    # Cancellation is irreversible and may trigger refunds/restock — require step-up.
    if payload.status in _SENSITIVE_STATUSES:
        if not x_step_up_token:
            raise api_error(
                status.HTTP_403_FORBIDDEN,
                error_code=ErrorCode.STEP_UP_REQUIRED,
                message="Step-up authentication required to cancel an order",
                details=[{"field": "X-Step-Up-Token", "message": "Missing step-up token"}],
            )
        step_up_payload = verify_step_up_token(x_step_up_token)
        if step_up_payload.get("sub") != current_user.phone_number:
            raise api_error(
                status.HTTP_403_FORBIDDEN,
                error_code=ErrorCode.STEP_UP_MISMATCH,
                message="Step-up token does not match the authenticated user",
            )

    try:
        await transition_order_status(db, order, payload.status, note=payload.note)
    except ValueError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message=str(exc),
            details=[{"field": "status", "message": str(exc)}],
        ) from exc

    await db.commit()
    refreshed = await crud_commerce.get_order_by_id(db, order_id)
    return _to_detail(refreshed)
