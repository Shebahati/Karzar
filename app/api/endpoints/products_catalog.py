"""Product catalog read endpoints: list, statistics, detail, related."""

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
    get_optional_current_user,
    is_super_admin,
)
from app.api.endpoints.product_common import (
    _audience_for_user,
    _category_metadata,
    _guard_inactive_product,
)
from app.core.config import settings
from app.core.errors import ErrorCode, api_error
from app.core.logging import get_logger
from app.core.request_throttle import enforce_public_throttle
from app.crud import product as crud_product
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.common import build_pagination_meta
from app.schemas.product import (
    ProductDetailResponse,
    ProductListResponse,
    ProductStatisticsResponse,
)
from app.schemas.storefront import RelatedProductsResponse
from app.services.product_service import ProductService
from app.utils.jsonb_filters import merge_spec_filters
from app.utils.product_presenter import to_product_detail, to_product_summary
from app.utils.storefront_catalog import VALID_SORT_KEYS, parse_in_stock_filter

logger = get_logger(__name__)

router = APIRouter()


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

        if not is_super_admin(current_user):
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
