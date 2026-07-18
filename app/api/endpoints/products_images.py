"""Product image management endpoints."""

from fastapi import (
    APIRouter,
    Depends,
    Request,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin
from app.api.endpoints.product_common import _product_detail_after_write
from app.core.errors import ErrorCode, api_error
from app.crud import product as crud_product
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.product import (
    ProductDetailResponse,
    ProductImageCreate,
    ProductImageReorderRequest,
    ProductImageUploadResponse,
)
from app.utils.file_storage import save_product_image_upload
from app.utils.image_validation import ensure_image_count_within_limit, validate_product_image_url

router = APIRouter()


@router.post(
    "/{product_id}/images",
    status_code=status.HTTP_201_CREATED,
    summary="Add a product image by URL or multipart upload",
    response_model=None,
)
async def add_product_image(
    product_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    product = await crud_product.get_product_by_id(db, product_id)
    if not product:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Product with ID '{product_id}' not found",
        )

    content_type = request.headers.get("content-type", "")
    try:
        image_count = await crud_product.count_product_images(db, product_id)
        ensure_image_count_within_limit(image_count)
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.VALIDATION_FAILED,
            message=str(exc),
        ) from exc

    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("file")
        if upload is None:
            raise api_error(
                status.HTTP_400_BAD_REQUEST,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="file is required for multipart upload",
            )
        try:
            image_url = await save_product_image_upload(product_id, upload)  # type: ignore[arg-type]
        except ValueError as exc:
            raise api_error(
                status.HTTP_400_BAD_REQUEST,
                error_code=ErrorCode.VALIDATION_FAILED,
                message=str(exc),
            ) from exc
        image = await crud_product.add_product_image(
            db,
            product_id,
            image_url,
            is_primary=not product.images,
        )
        await db.commit()
        return ProductImageUploadResponse(
            id=image.id,
            url=image.image_url,
            is_primary=image.is_primary,
        )

    payload = ProductImageCreate(**(await request.json()))
    try:
        validated_url = validate_product_image_url(payload.image_url)
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.VALIDATION_FAILED,
            message=str(exc),
            details=[{"field": "image_url", "message": str(exc)}],
        ) from exc

    await crud_product.add_product_image(
        db,
        product_id,
        validated_url,
        is_primary=payload.is_primary or not product.images,
    )
    await db.commit()
    return await _product_detail_after_write(db, product_id)


@router.delete(
    "/{product_id}/images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product image",
)
async def remove_product_image(
    product_id: int,
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    deleted = await crud_product.delete_product_image(db, product_id, image_id)
    if not deleted:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Image '{image_id}' not found for product '{product_id}'",
        )
    await db.commit()


@router.patch(
    "/{product_id}/images/{image_id}/primary",
    response_model=ProductDetailResponse,
    summary="Set primary product image",
)
async def set_primary_product_image(
    product_id: int,
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    image = await crud_product.set_primary_product_image(db, product_id, image_id)
    if not image:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Image '{image_id}' not found for product '{product_id}'",
        )
    await db.commit()
    return await _product_detail_after_write(db, product_id)


@router.patch(
    "/{product_id}/images/reorder",
    response_model=ProductDetailResponse,
    summary="Reorder product images",
)
async def reorder_product_images(
    product_id: int,
    payload: ProductImageReorderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    product = await crud_product.get_product_by_id(db, product_id)
    if not product:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Product with ID '{product_id}' not found",
        )
    try:
        await crud_product.reorder_product_images(db, product_id, payload.image_ids)
    except ValueError as exc:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.VALIDATION_FAILED,
            message=str(exc),
            details=[{"field": "image_ids", "message": str(exc)}],
        ) from exc
    await db.commit()
    return await _product_detail_after_write(db, product_id)
