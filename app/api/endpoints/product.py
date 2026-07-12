"""Product CRUD, search, stock management, and statistics endpoints."""

from decimal import Decimal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_super_admin,
    get_current_super_admin_with_step_up,
    get_optional_current_user,
    is_super_admin,
)
from app.core.config import settings
from app.core.errors import ErrorCode, api_error
from app.core.logging import get_logger
from app.core.request_throttle import enforce_public_throttle
from app.crud import category as crud_category
from app.crud import content as crud_content
from app.crud import product as crud_product
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.common import build_pagination_meta
from app.schemas.product import (
    BulkStockAdjustRequest,
    BulkStockAdjustResponse,
    ProductChangeLogEntry,
    ProductChangeLogListResponse,
    ProductCreate,
    ProductDetailResponse,
    ProductImageCreate,
    ProductImageReorderRequest,
    ProductImageUploadResponse,
    ProductListResponse,
    ProductStatisticsResponse,
    ProductUpdate,
    StockStatusResponse,
)
from app.schemas.storefront import (
    ProductCommentCreateRequest,
    ProductCommentListResponse,
    ProductCommentResponse,
    RelatedProductsResponse,
)
from app.services.product_service import ProductService
from app.utils.category_depth import build_category_metadata
from app.utils.file_storage import save_product_image_upload
from app.utils.image_validation import ensure_image_count_within_limit, validate_product_image_url
from app.utils.jsonb_filters import merge_spec_filters
from app.utils.product_presenter import to_product_detail, to_product_summary
from app.utils.storefront_catalog import VALID_SORT_KEYS, parse_in_stock_filter

logger = get_logger(__name__)

router = APIRouter()


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


@router.post(
    "/",
    response_model=ProductDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
)
async def create_new_product(
    product_in: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    try:
        product = await ProductService.create_product_with_validation(db=db, product_data=product_in)
        return await _product_detail_after_write(db, product.id)
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Business validation error: {str(e)}")
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message=str(e),
            details=[{"field": "sku", "message": str(e)}],
        ) from e
    except Exception as e:
        logger.error(f"Error creating product: {str(e)}")
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error creating product",
        ) from e


@router.get(
    "/",
    response_model=ProductListResponse,
    summary="List all products",
)
async def read_products(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return"),
    category_id: int | None = Query(None, description="Filter by category ID"),
    brand_id: int | None = Query(None, description="Filter by brand ID"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    is_deleted: bool | None = Query(
        None,
        description="Filter soft-deleted products (admin only when true)",
    ),
    search: str | None = Query(None, description="Search in name, SKU, and brand"),
    min_price: Decimal | None = Query(None, description="Minimum price filter"),
    max_price: Decimal | None = Query(None, description="Maximum price filter"),
    country: str | None = Query(None, description="Filter by brand country"),
    in_stock: str | None = Query(None, description="Only in-stock active products (true/false/1/0)"),
    sort: str | None = Query(
        None,
        description="Sort key: newest, price_asc, price_desc, name_asc, name_desc",
    ),
    ids: str | None = Query(None, description="Comma-separated product IDs"),
    filters: str | None = Query(
        None,
        description='JSON object for specification filters, e.g. {"technical_specs.range":"0-150mm"}',
    ),
):
    try:
        if not is_super_admin(current_user):
            has_plp_search = bool(
                search
                or filters
                or any(
                    key.startswith("spec_")
                    for key in request.query_params.keys()
                )
            )
            if has_plp_search:
                await enforce_public_throttle(
                    request,
                    scope="plp_search",
                    max_requests=settings.PUBLIC_THROTTLE_PLP_MAX,
                    window_seconds=settings.PUBLIC_THROTTLE_PLP_WINDOW,
                )

        if is_deleted is True and not is_super_admin(current_user):
            raise api_error(
                status.HTTP_403_FORBIDDEN,
                error_code=ErrorCode.FORBIDDEN,
                message="Only administrators can list deleted products",
            )

        if is_active is None and not is_super_admin(current_user):
            is_active = True

        if sort is not None and sort not in VALID_SORT_KEYS:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="Invalid sort key",
                details=[
                    {"field": "sort", "message": f"must be one of: {', '.join(sorted(VALID_SORT_KEYS))}"}
                ],
            )

        product_ids: list[int] | None = None
        if ids:
            try:
                product_ids = [int(value.strip()) for value in ids.split(",") if value.strip()]
            except ValueError:
                raise api_error(
                    status.HTTP_422_UNPROCESSABLE_CONTENT,
                    error_code=ErrorCode.VALIDATION_FAILED,
                    message="ids must be a comma-separated list of integers",
                    details=[{"field": "ids", "message": "invalid integer in list"}],
                ) from None

        spec_filters = merge_spec_filters(filters_json=filters, request=request)
        parsed_in_stock = parse_in_stock_filter(in_stock)
        products, total = await ProductService.search_products(
            db=db,
            skip=skip,
            limit=limit,
            category_id=category_id,
            brand_id=brand_id,
            is_active=is_active,
            search=search,
            min_price=min_price,
            max_price=max_price,
            spec_filters=spec_filters or None,
            country=country,
            in_stock=parsed_in_stock,
            sort=sort,
            product_ids=product_ids,
            is_deleted=is_deleted,
        )

        metadata = await _category_metadata(db)
        audience = _audience_for_user(current_user)

        return {
            "data": [
                to_product_summary(product, metadata, audience=audience) for product in products
            ],
            "meta": build_pagination_meta(total_count=total, skip=skip, limit=limit),
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.VALIDATION_FAILED,
            message=str(e),
            details=[{"field": "filters", "message": str(e)}],
        ) from e
    except Exception as e:
        logger.error(f"Error retrieving products: {str(e)}")
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error retrieving products",
        ) from e


@router.get(
    "/statistics",
    response_model=ProductStatisticsResponse,
    summary="Aggregate product statistics (admin)",
    tags=["Products"],
)
async def read_product_statistics(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    stats = await ProductService.get_product_statistics(db)
    return ProductStatisticsResponse(
        total_products=stats["total_products"],
        active_products=stats["active_products"],
        total_stock_value=str(stats["total_stock_value"]),
        total_stock_quantity=str(stats["total_stock_quantity"]),
        categories=stats["categories"],
        brands=stats["brands"],
    )


@router.get(
    "/sku/{sku}",
    response_model=ProductDetailResponse,
    summary="Get product by SKU",
)
async def read_product_by_sku(
    sku: str = Path(..., min_length=1, max_length=50, description="Product SKU"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    from app.crud import product as crud_product

    try:
        product = await crud_product.get_product_by_sku(db=db, sku=sku.strip().upper())
        if not product:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Product with SKU '{sku}' not found",
            )
        _guard_inactive_product(product, current_user, sku)
        audience = _audience_for_user(current_user)
        return to_product_detail(product, await _category_metadata(db), audience=audience)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving product by SKU: {str(e)}")
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error retrieving product",
        ) from e


@router.get(
    "/{product_id}",
    response_model=ProductDetailResponse,
    summary="Get product by ID",
)
async def read_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        details = await ProductService.get_product_details(db=db, product_id=product_id)
        if not details:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Product with ID '{product_id}' not found",
            )
        _guard_inactive_product(details["product"], current_user, str(product_id))
        audience = _audience_for_user(current_user)
        return to_product_detail(details["product"], await _category_metadata(db), audience=audience)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving product: {str(e)}")
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error retrieving product",
        ) from e


@router.get(
    "/{product_id}/related",
    response_model=RelatedProductsResponse,
    summary="Related products for PDP carousel",
)
async def read_related_products(product_id: int, db: AsyncSession = Depends(get_db)):
    products = await crud_product.get_related_products(db, product_id)
    metadata = await _category_metadata(db)
    return {
        "data": [to_product_summary(product, metadata, audience="storefront") for product in products]
    }


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
    comments = await crud_content.list_product_comments(db, product_id)
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
):
    product = await crud_product.get_product_by_id(db, product_id)
    if not product:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Product with ID '{product_id}' not found",
        )
    comment = await crud_content.create_product_comment(
        db,
        product_id=product_id,
        author_name=payload.author_name,
        rating=payload.rating,
        body=payload.body,
        is_verified_buyer=payload.is_verified_buyer,
    )
    await db.commit()
    return ProductCommentResponse.model_validate(comment, from_attributes=True)


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


@router.put(
    "/{product_id}",
    response_model=ProductDetailResponse,
    summary="Update product",
)
async def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    try:
        product = await ProductService.update_product_with_validation(
            db=db, product_id=product_id, update_data=product_in
        )
        if not product:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Product with ID '{product_id}' not found",
            )
        return await _product_detail_after_write(db, product_id)
    except HTTPException:
        raise
    except ValueError as e:
        message = str(e)
        if "SKU" in message and "already exists" in message:
            raise api_error(
                status.HTTP_409_CONFLICT,
                error_code=ErrorCode.CONFLICT,
                message=message,
                details=[{"field": "sku", "message": message}],
            ) from e
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.BAD_REQUEST,
            message=message,
        ) from e
    except Exception as e:
        logger.error(f"Error updating product: {str(e)}")
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error updating product",
        ) from e


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete product (soft delete)",
)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_with_step_up),
):
    try:
        deleted = await ProductService.delete_product(
            db=db,
            product_id=product_id,
            actor_user_id=current_user.id,
        )
        if not deleted:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Product with ID '{product_id}' not found",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting product: {str(e)}")
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error deleting product",
        ) from e


@router.post(
    "/{product_id}/restore",
    response_model=ProductDetailResponse,
    summary="Restore deleted product",
)
async def restore_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_with_step_up),
):
    try:
        product = await ProductService.restore_product(db=db, product_id=product_id)
        if not product:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Product with ID '{product_id}' not found or is not deleted",
            )
        return await _product_detail_after_write(db, product_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring product: {str(e)}")
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error restoring product",
        ) from e


@router.get(
    "/{product_id}/stock",
    response_model=StockStatusResponse,
    summary="Get product stock status",
    tags=["Stock Management"],
)
async def get_stock(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    from app.crud import product as crud_product

    try:
        stock_status = await crud_product.get_stock_status(db=db, product_id=product_id)
        if not stock_status:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Product with ID '{product_id}' not found",
            )
        return stock_status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving stock status: {str(e)}")
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error retrieving stock status",
        ) from e


@router.post(
    "/{product_id}/stock/adjust",
    response_model=ProductDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Adjust product stock",
    tags=["Stock Management"],
)
async def adjust_stock(
    product_id: int,
    quantity_delta: Decimal = Query(..., description="Quantity to add or subtract"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    try:
        product = await ProductService.adjust_stock_with_validation(
            db=db,
            product_id=product_id,
            quantity_delta=quantity_delta,
            reason="API Adjustment",
            actor_user_id=current_user.id,
        )
        if not product:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                error_code=ErrorCode.NOT_FOUND,
                message=f"Product with ID '{product_id}' not found",
            )
        return await _product_detail_after_write(db, product_id)
    except HTTPException:
        raise
    except ValueError as e:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.BAD_REQUEST,
            message=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error adjusting stock: {str(e)}")
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Error adjusting stock",
        ) from e


@router.post(
    "/bulk/stock-adjust",
    response_model=BulkStockAdjustResponse,
    summary="Bulk stock adjustment (admin)",
    tags=["Stock Management"],
)
async def bulk_adjust_stock(
    payload: BulkStockAdjustRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    items = [
        {
            "product_id": item.product_id,
            "quantity_delta": item.quantity_delta,
            "reason": item.reason,
        }
        for item in payload.items
    ]
    updated_ids = await ProductService.bulk_adjust_stock(
        db, items, actor_user_id=current_user.id
    )
    return BulkStockAdjustResponse(updated_product_ids=updated_ids)


@router.get(
    "/{product_id}/change-log",
    response_model=ProductChangeLogListResponse,
    summary="Product price/stock change history (admin)",
)
async def list_product_change_log(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    from app.crud import platform as crud_platform

    product = await crud_product.get_product_by_id(db, product_id)
    if not product:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Product with ID '{product_id}' not found",
        )
    rows, total = await crud_platform.list_product_change_logs(
        db, product_id, skip=skip, limit=limit
    )
    return {
        "data": [ProductChangeLogEntry.model_validate(row, from_attributes=True) for row in rows],
        "meta": build_pagination_meta(total_count=total, skip=skip, limit=limit),
    }
