"""Shared helpers for product endpoint modules."""

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import is_super_admin
from app.core.errors import ErrorCode, api_error
from app.crud import category as crud_category
from app.db.models.user import User
from app.schemas.product import ProductDetailResponse
from app.services.product_service import ProductService
from app.utils.category_depth import build_category_metadata
from app.utils.product_presenter import to_product_detail


def _audience_for_user(user: User | None) -> str:
    return "admin" if is_super_admin(user) else "storefront"


def _guard_inactive_product(product, user: User | None, identifier: str) -> None:
    """Hide inactive products from non-admin callers on direct read paths."""
    if not product.is_active and not is_super_admin(user):
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Product '{identifier}' not found",
        )


async def _category_metadata(db: AsyncSession):
    categories = await crud_category.get_all_categories(db)
    return build_category_metadata(categories)


async def _product_detail_after_write(db: AsyncSession, product_id: int) -> ProductDetailResponse:
    """Re-fetch a product with relationships after a write operation."""
    details = await ProductService.get_product_details(db=db, product_id=product_id)
    if not details:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Product with ID '{product_id}' not found",
        )
    metadata = await _category_metadata(db)
    return to_product_detail(details["product"], metadata, audience="admin")
