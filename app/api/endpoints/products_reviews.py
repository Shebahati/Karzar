"""Product comment/review endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.api.endpoints.product_common import _guard_inactive_product
from app.core.errors import ErrorCode, api_error
from app.crud import product as crud_product
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.storefront import (
    ProductCommentCreateRequest,
    ProductCommentListResponse,
    ProductCommentResponse,
)
from app.services import product_review_service

router = APIRouter()


@router.get(
    "/{product_id}/comments",
    response_model=ProductCommentListResponse,
    summary="Product reviews",
)
async def read_product_comments(product_id: int, db: AsyncSession = Depends(get_db)):
    product = await crud_product.get_product_by_id(db, product_id)
    if not product:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Product with ID '{product_id}' not found",
        )
    _guard_inactive_product(product, None, str(product_id))
    comments = await product_review_service.list_comments(db, product_id)
    return {
        "data": [
            ProductCommentResponse.model_validate(comment, from_attributes=True)
            for comment in comments
        ]
    }


@router.post(
    "/{product_id}/comments",
    response_model=ProductCommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product review",
)
async def create_product_comment(
    product_id: int,
    payload: ProductCommentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    product = await crud_product.get_product_by_id(db, product_id)
    if not product:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Product with ID '{product_id}' not found",
        )
    _guard_inactive_product(product, current_user, str(product_id))
    comment = await product_review_service.create_comment(
        db,
        product_id=product_id,
        user_id=current_user.id,
        author_name=payload.author_name,
        rating=payload.rating,
        body=payload.body,
    )
    await db.commit()
    return ProductCommentResponse.model_validate(comment, from_attributes=True)
