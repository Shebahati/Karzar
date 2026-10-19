"""Published manual homepage bestseller selection; no inferred/automatic ranking."""

from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin
from app.core.errors import ErrorCode, api_error
from app.db.database import get_db
from app.db.models.content import HomeBestsellerSelection
from app.db.models.product import Product
from app.db.models.user import User
from app.services.audit_service import record_audit
from app.utils.public_catalog import storefront_public_product_filters

router = APIRouter()


class BestsellerSelectionResponse(BaseModel):
    product_ids: list[int]
    revision: int
    published_at: datetime | None


class BestsellerPublishRequest(BaseModel):
    product_ids: list[int] = Field(max_length=48)
    expected_revision: int = Field(ge=0)


def _response(row: HomeBestsellerSelection | None) -> BestsellerSelectionResponse:
    if row is None:
        return BestsellerSelectionResponse(product_ids=[], revision=0, published_at=None)
    return BestsellerSelectionResponse(
        product_ids=list(row.product_ids), revision=row.revision, published_at=row.published_at
    )


@router.get("/bestsellers", response_model=BestsellerSelectionResponse)
async def read_bestsellers(db: AsyncSession = Depends(get_db)):
    # Only published IDs are exposed; no sales/account/stock internals.
    row = await db.get(HomeBestsellerSelection, 1)
    return _response(row)


@router.put("/bestsellers", response_model=BestsellerSelectionResponse)
async def publish_bestsellers(
    payload: BestsellerPublishRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_super_admin),
):
    ids = payload.product_ids
    if any(type(i) is not int or i <= 0 for i in ids) or len(set(ids)) != len(ids):
        raise api_error(status.HTTP_422_UNPROCESSABLE_CONTENT,
                        error_code=ErrorCode.VALIDATION_FAILED,
                        message="product_ids must be unique positive integers in display order")
    row = (await db.execute(select(HomeBestsellerSelection)
                            .where(HomeBestsellerSelection.id == 1).with_for_update())).scalar_one_or_none()
    if payload.expected_revision != (row.revision if row else 0):
        raise api_error(status.HTTP_409_CONFLICT, error_code=ErrorCode.CONFLICT,
                        message="Bestseller selection changed; reload before publishing")
    if ids:
        found = set((await db.execute(select(Product.id).where(
            Product.id.in_(ids), Product.deleted_at.is_(None),
            Product.is_active.is_(True), Product.is_available.is_(True),
            *storefront_public_product_filters(),
        ))).scalars().all())
        if found != set(ids):
            raise api_error(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            error_code=ErrorCode.VALIDATION_FAILED,
                            message="Selection contains unavailable, inactive, deleted or non-public products")
    if row is None:
        row = HomeBestsellerSelection(id=1, product_ids=list(ids), revision=1)
        db.add(row)
    else:
        row.product_ids = list(ids)
        row.revision += 1
        from sqlalchemy.sql import func
        row.published_at = func.now()
    await record_audit(db, actor_user_id=admin.id, action="publish",
                       entity_type="home_bestsellers", entity_id="1",
                       details={"product_ids": ids, "revision": row.revision})
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise api_error(status.HTTP_409_CONFLICT, error_code=ErrorCode.CONFLICT,
                        message="Concurrent bestseller publication; reload and retry") from None
    await db.refresh(row)
    return _response(row)
