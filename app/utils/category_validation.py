"""Validate product category assignments against catalog rules."""


from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, api_error
from app.crud import brand as crud_brand
from app.crud import category as crud_category
from app.utils.category_depth import build_category_metadata, is_selectable_product_category


async def ensure_selectable_product_category(
    db: AsyncSession,
    category_id: int | None,
    *,
    required: bool = False,
) -> None:
    """Reject missing, unknown, or non-assignable categories for products."""
    if category_id is None:
        if required:
            raise api_error(
                400,
                error_code=ErrorCode.BAD_REQUEST,
                message="Category is required",
                details=[{"field": "category_id", "message": "انتخاب دسته‌بندی الزامی است."}],
            )
        return

    category = await crud_category.get_category_by_id(db, category_id)
    if category is None:
        raise api_error(
            400,
            error_code=ErrorCode.BAD_REQUEST,
            message="Category not found",
            details=[{"field": "category_id", "message": "دسته‌بندی یافت نشد."}],
        )

    categories = await crud_category.get_all_categories(db)
    metadata = build_category_metadata(categories)[category_id]
    if not is_selectable_product_category(metadata):
        raise api_error(
            400,
            error_code=ErrorCode.BAD_REQUEST,
            message="Category must be a depth-3 leaf",
            details=[
                {
                    "field": "category_id",
                    "message": "محصول فقط می‌تواند به یک زیردستهٔ برگ با عمق ۳ اختصاص یابد.",
                }
            ],
        )


async def ensure_brand_exists(db: AsyncSession, brand_id: int | None) -> None:
    """Reject unknown brand references on product writes."""
    if brand_id is None:
        return

    brand = await crud_brand.get_brand_by_id(db, brand_id)
    if brand is None:
        raise api_error(
            400,
            error_code=ErrorCode.BAD_REQUEST,
            message="Brand not found",
            details=[{"field": "brand_id", "message": "برند یافت نشد."}],
        )
