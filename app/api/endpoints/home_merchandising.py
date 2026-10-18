"""Live, audited homepage bestseller curation. No static JSON/container cross-write."""
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert
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
MAX_ITEMS = 24

class BestsellerSelectionResponse(BaseModel):
    product_ids: list[int]
    revision: int
    published_at: datetime | None

class BestsellerSelectionWrite(BaseModel):
    product_ids: list[Annotated[int, Field(gt=0)]] = Field(max_length=MAX_ITEMS)
    expected_revision: int = Field(ge=0)

def as_response(row: HomeBestsellerSelection | None) -> BestsellerSelectionResponse:
    if row is None:
        return BestsellerSelectionResponse(product_ids=[], revision=0, published_at=None)
    return BestsellerSelectionResponse(
        product_ids=list(row.product_ids or []),
        revision=row.revision,
        published_at=row.published_at,
    )

@router.get("/bestsellers", response_model=BestsellerSelectionResponse)
async def get_home_bestsellers(db: AsyncSession = Depends(get_db)):
    row = await db.get(HomeBestsellerSelection, 1)
    return as_response(row)

@router.put("/bestsellers", response_model=BestsellerSelectionResponse)
async def publish_home_bestsellers(
    payload: BestsellerSelectionWrite,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_super_admin),
):
    ids = payload.product_ids
    if len(ids) != len(set(ids)):
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Product IDs must be unique and ordered",
        )
    # Fail closed on missing, deleted, inactive or currently unavailable IDs.
    # A later stock change is filtered again by the storefront.
    if ids:
        q = select(Product.id).where(
            and_(
                Product.id.in_(ids),
                *storefront_public_product_filters(),
                Product.is_available.is_(True),
            )
        )
        found = set((await db.execute(q)).scalars().all())
        if found != set(ids):
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="One or more selected products are not publicly available",
            )

    # Insert singleton safely under concurrent first writes; then lock row to
    # serialize owner updates and enforce optimistic revision matching.
    await db.execute(
        insert(HomeBestsellerSelection)
        .values(id=1, product_ids=[], revision=0)
        .on_conflict_do_nothing(index_elements=["id"])
    )
    row = (await db.execute(
        select(HomeBestsellerSelection)
        .where(HomeBestsellerSelection.id == 1)
        .with_for_update()
    )).scalar_one()
    if row.revision != payload.expected_revision:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Bestseller selection changed; reload before publishing",
        )
    old_ids = list(row.product_ids or [])
    row.product_ids = ids[:]
    row.revision += 1
    row.published_at = datetime.now().astimezone()
    row.actor_user_id = user.id
    await record_audit(
        db, actor_user_id=user.id, action="publish",
        entity_type="home_bestsellers", entity_id=1,
        details={"previous_product_ids": old_ids, "product_ids": ids, "revision": row.revision},
    )
    await db.commit()
    return as_response(row)
