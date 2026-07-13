"""Order endpoints: admin management, customer history, and public tracking."""


from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_active_user,
    get_current_super_admin,
    get_current_super_admin_with_step_up,
)
from app.core.config import settings
from app.core.errors import ErrorCode, api_error
from app.core.request_throttle import enforce_public_throttle
from app.core.security import verify_step_up_token
from app.crud import commerce as crud_commerce
from app.crud import platform as crud_platform
from app.db.database import get_db
from app.db.models.commerce import Order, OrderMode, OrderStatus
from app.db.models.user import User
from app.schemas.common import build_pagination_meta, resolve_pagination
from app.schemas.order import (
    IssueQuoteRequest,
    OrderDetailResponse,
    OrderItemResponse,
    OrderListResponse,
    OrderStatusUpdateRequest,
    OrderSummary,
    OrderTrackingEvent,
    OrderTrackingItemResponse,
    OrderTrackingResponse,
)
from app.services.audit_service import record_audit
from app.services.order_service import (
    allowed_next_statuses,
    build_invoice_response,
    issue_order_quote,
    payment_status_label,
    status_label,
    transition_order_status,
)
from app.utils.storefront_catalog import decimal_to_api_string

router = APIRouter()

_VALID_ORDER_SORTS = frozenset({"newest", "oldest", "total_asc", "total_desc"})
_SENSITIVE_STATUSES = frozenset({OrderStatus.CANCELLED.value})


def _build_timeline(order: Order) -> list[OrderTrackingEvent]:
    events = list(order.status_events or [])
    if not events:
        return [
            OrderTrackingEvent(
                status=order.status,
                status_label=status_label(order.status),
                occurred_at=order.updated_at or order.created_at,
                description=None,
                actor="system",
            )
        ]
    return [
        OrderTrackingEvent(
            status=event.status,
            status_label=status_label(event.status),
            occurred_at=event.created_at,
            description=event.description,
            actor=event.actor,
        )
        for event in events
    ]


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
        admin_note=order.admin_note,
        shipping=order.shipping,
        user_id=order.user_id,
        postal_tracking_code=order.postal_tracking_code,
        delivery_eta=order.delivery_eta,
        invoice=build_invoice_response(order.invoice),
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
        timeline=_build_timeline(order),
    )


@router.get("/me", response_model=OrderListResponse, summary="List the authenticated customer's orders")
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


@router.get("/track/{tracking_code}", response_model=OrderTrackingResponse, summary="Public order tracking by code")
async def track_order(tracking_code: str, request: Request, db: AsyncSession = Depends(get_db)):
    await enforce_public_throttle(
        request,
        scope="tracking",
        max_requests=settings.PUBLIC_THROTTLE_TRACKING_MAX,
        window_seconds=settings.PUBLIC_THROTTLE_TRACKING_WINDOW,
    )
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
        created_at=order.created_at,
        items=[
            OrderTrackingItemResponse(
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=decimal_to_api_string(item.unit_price),
            )
            for item in order.items
        ],
        timeline=_build_timeline(order),
    )


@router.get("", response_model=OrderListResponse, summary="List orders (admin)")
async def list_orders(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    mode: str | None = Query(None),
    payment_status: str | None = Query(None),
    phone: str | None = Query(None),
    customer_phone: str | None = Query(None),
    search: str | None = Query(None),
    sort: str = Query("newest"),
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
            ) from None

    mode_enum: OrderMode | None = None
    if mode is not None:
        try:
            mode_enum = OrderMode(mode)
        except ValueError:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="Invalid mode filter",
                details=[{"field": "mode", "message": "must be 'purchase' or 'inquiry'"}],
            ) from None

    orders, total = await crud_commerce.list_orders(
        db,
        skip=resolved_skip,
        limit=resolved_limit,
        status=status_filter,
        mode=mode_enum,
        payment_status=payment_status,
        phone=phone,
        customer_phone=customer_phone,
        search=search,
        sort=sort,
    )
    return {
        "data": [_to_summary(order) for order in orders],
        "meta": build_pagination_meta(total_count=total, skip=resolved_skip, limit=resolved_limit),
    }


@router.get("/{order_id}", response_model=OrderDetailResponse, summary="Get order detail (admin)")
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


@router.patch("/{order_id}/status", response_model=OrderDetailResponse, summary="Update order status (admin)")
async def update_order_status(
    order_id: int,
    payload: OrderStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
    x_step_up_token: str | None = Header(None, alias="X-Step-Up-Token"),
):
    order = await crud_commerce.get_order_by_id(db, order_id)
    if not order:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Order '{order_id}' not found",
        )

    if payload.status in _SENSITIVE_STATUSES:
        if not x_step_up_token:
            raise api_error(
                status.HTTP_403_FORBIDDEN,
                error_code=ErrorCode.STEP_UP_REQUIRED,
                message="Step-up authentication required to cancel an order",
            )
        step_up_payload = verify_step_up_token(x_step_up_token)
        if step_up_payload.get("sub") != current_user.phone_number:
            raise api_error(
                status.HTTP_403_FORBIDDEN,
                error_code=ErrorCode.STEP_UP_MISMATCH,
                message="Step-up token does not match the authenticated user",
            )
        consumed = await crud_platform.consume_step_up_jti(
            db,
            jti=step_up_payload["jti"],
            expires_at=datetime.fromtimestamp(step_up_payload["exp"], tz=UTC),
        )
        if not consumed:
            raise api_error(
                status.HTTP_403_FORBIDDEN,
                error_code=ErrorCode.STEP_UP_INVALID,
                message="Step-up token has already been used",
            )

    try:
        await transition_order_status(
            db,
            order,
            payload.status,
            note=payload.note,
            postal_tracking_code=payload.postal_tracking_code,
            delivery_eta=payload.delivery_eta,
            actor="admin",
        )
    except ValueError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message=str(exc),
            details=[{"field": "status", "message": str(exc)}],
        ) from exc

    await db.commit()
    if payload.status in _SENSITIVE_STATUSES:
        await record_audit(
            db,
            actor_user_id=current_user.id,
            action="status_change",
            entity_type="order",
            entity_id=order.id,
            details={"to": payload.status},
        )
        await db.commit()
    refreshed = await crud_commerce.get_order_by_id(db, order_id)
    return _to_detail(refreshed)


@router.post("/{order_id}/quote", response_model=OrderDetailResponse, summary="Issue inquiry quote (admin)")
async def issue_quote(
    order_id: int,
    payload: IssueQuoteRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_super_admin),
):
    order = await crud_commerce.get_order_by_id(db, order_id)
    if not order:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Order '{order_id}' not found",
        )
    try:
        await issue_order_quote(db, order, payload)
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.VALIDATION_FAILED,
            message=str(exc),
            details=[{"field": "items", "message": str(exc)}],
        ) from exc

    await db.commit()
    await record_audit(
        db,
        actor_user_id=admin_user.id,
        action="issue_quote",
        entity_type="order",
        entity_id=order.id,
        details={"mode": "line_items"},
    )
    await db.commit()
    refreshed = await crud_commerce.get_order_by_id(db, order_id)
    return _to_detail(refreshed)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Archive order (soft delete, admin)")
async def archive_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_super_admin_with_step_up),
):
    from datetime import datetime

    order = await crud_commerce.get_order_by_id(db, order_id)
    if not order:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Order '{order_id}' not found",
        )
    order.deleted_at = datetime.now(UTC)
    await record_audit(
        db,
        actor_user_id=admin_user.id,
        action="soft_delete",
        entity_type="order",
        entity_id=order.id,
        details={"tracking_code": order.tracking_code},
    )
    await db.commit()
