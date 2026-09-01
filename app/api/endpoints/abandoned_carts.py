"""Admin abandoned-cart API."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.common import PaginationMeta, build_pagination_meta, resolve_pagination
from app.services.abandoned_cart_service import list_abandoned_carts
from app.utils.storefront_catalog import decimal_to_api_string

router = APIRouter()


class AbandonedCartItemResponse(BaseModel):
    product_id: int
    quantity: int
    product_name: str | None = None
    product_sku: str | None = None


class AbandonedCartSummary(BaseModel):
    cart_id: int
    user_id: int | None
    customer_name: str
    customer_phone: str | None
    item_count: int
    cart_value: str
    last_activity_at: datetime
    items: list[AbandonedCartItemResponse] = Field(default_factory=list)


class AbandonedCartListResponse(BaseModel):
    data: list[AbandonedCartSummary]
    meta: PaginationMeta


@router.get("", response_model=AbandonedCartListResponse, summary="List abandoned carts (admin)")
async def list_abandoned_carts_endpoint(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    inactive_hours: int = Query(24, ge=1, le=24 * 30),
):
    resolved_skip, resolved_limit = resolve_pagination(
        page=page, page_size=page_size, skip=skip, limit=limit
    )
    rows, total = await list_abandoned_carts(
        db, skip=resolved_skip, limit=resolved_limit, inactive_hours=inactive_hours
    )
    return {
        "data": [
            AbandonedCartSummary(
                cart_id=row["cart_id"],
                user_id=row["user_id"],
                customer_name=row["customer_name"],
                customer_phone=row["customer_phone"],
                item_count=row["item_count"],
                cart_value=decimal_to_api_string(row["cart_value"]) or "0",
                last_activity_at=row["last_activity_at"],
                items=[AbandonedCartItemResponse(**item) for item in row["items"]],
            )
            for row in rows
        ],
        "meta": build_pagination_meta(total_count=total, skip=resolved_skip, limit=resolved_limit),
    }
