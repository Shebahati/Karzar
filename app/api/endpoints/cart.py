"""Server-side cart endpoints for purchase and inquiry lanes."""


from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_optional_current_user
from app.core.errors import ErrorCode, api_error
from app.db.database import get_db
from app.db.models.platform import CartLane
from app.db.models.user import User
from app.schemas.cart import CartItemUpsertRequest, CartMergeRequest, CartResponse
from app.services.cart_service import (
    clear_lane,
    get_cart_response,
    merge_guest_into_user,
    remove_item,
    upsert_item,
)

router = APIRouter()


def _resolve_lane(value: str) -> CartLane:
    try:
        return CartLane(value)
    except ValueError as exc:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Invalid cart lane",
            details=[{"field": "lane", "message": "must be purchase or inquiry"}],
        ) from exc


def _require_cart_identity(
    current_user: User | None,
    x_cart_token: str | None,
) -> tuple[User | None, str | None]:
    if current_user is not None:
        return current_user, None
    if x_cart_token and x_cart_token.strip():
        token = x_cart_token.strip()
        if len(token) < 32:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="Invalid X-Cart-Token header",
                details=[{"field": "X-Cart-Token", "message": "must be at least 32 characters"}],
            )
        return None, token
    raise api_error(
        status.HTTP_401_UNAUTHORIZED,
        error_code=ErrorCode.UNAUTHORIZED,
        message="Authentication or X-Cart-Token header is required",
    )


@router.get("", response_model=CartResponse, tags=["Cart"])
async def get_cart(
    lane: str = Query("purchase", pattern="^(purchase|inquiry)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
    x_cart_token: str | None = Header(None, alias="X-Cart-Token"),
):
    user, guest_token = _require_cart_identity(current_user, x_cart_token)
    return await get_cart_response(
        db,
        lane=_resolve_lane(lane),
        user=user,
        guest_token=guest_token,
    )


@router.put("/items", response_model=CartResponse, tags=["Cart"])
async def upsert_cart_item(
    payload: CartItemUpsertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
    x_cart_token: str | None = Header(None, alias="X-Cart-Token"),
):
    user, guest_token = _require_cart_identity(current_user, x_cart_token)
    try:
        return await upsert_item(
            db,
            lane=_resolve_lane(payload.lane),
            product_id=payload.product_id,
            quantity=payload.quantity,
            user=user,
            guest_token=guest_token,
        )
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.VALIDATION_FAILED,
            message=str(exc),
        ) from exc


@router.delete("/items/{product_id}", response_model=CartResponse, tags=["Cart"])
async def delete_cart_item(
    product_id: int,
    lane: str = Query("purchase", pattern="^(purchase|inquiry)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
    x_cart_token: str | None = Header(None, alias="X-Cart-Token"),
):
    user, guest_token = _require_cart_identity(current_user, x_cart_token)
    return await remove_item(
        db,
        lane=_resolve_lane(lane),
        product_id=product_id,
        user=user,
        guest_token=guest_token,
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, tags=["Cart"])
async def clear_cart(
    lane: str = Query("purchase", pattern="^(purchase|inquiry)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
    x_cart_token: str | None = Header(None, alias="X-Cart-Token"),
):
    user, guest_token = _require_cart_identity(current_user, x_cart_token)
    await clear_lane(db, lane=_resolve_lane(lane), user=user, guest_token=guest_token)


@router.post("/merge", response_model=list[CartResponse], tags=["Cart"])
async def merge_cart(
    payload: CartMergeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    lane = _resolve_lane(payload.lane) if payload.lane else None
    return await merge_guest_into_user(
        db,
        guest_token=payload.guest_token,
        user=current_user,
        lane=lane,
    )
