"""Admin brand bulk base_price adjustment endpoints (Feature D)."""

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin, get_verified_step_up
from app.core.errors import ErrorCode, api_error
from app.crud import platform as crud_platform
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.brand_bulk_pricing import (
    BrandBulkPricingApplyResponse,
    BrandBulkPricingConfirmRequest,
    BrandBulkPricingOperationDetail,
    BrandBulkPricingOperationListResponse,
    BrandBulkPricingPreviewResponse,
    BrandBulkPricingAdjustRequest,
)
from app.services.brand_bulk_pricing_service import (
    IDEMPOTENCY_SCOPE_PREFIX,
    BrandBulkPricingService,
)

router = APIRouter()


@router.post(
    "/preview",
    response_model=BrandBulkPricingPreviewResponse,
    summary="Preview brand bulk base_price changes",
)
async def preview_brand_bulk_pricing(
    payload: BrandBulkPricingAdjustRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    return await BrandBulkPricingService.preview(db, payload)


@router.post(
    "/confirm",
    response_model=BrandBulkPricingOperationDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Confirm and persist a bulk pricing operation",
)
async def confirm_brand_bulk_pricing(
    payload: BrandBulkPricingConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    return await BrandBulkPricingService.confirm(db, payload, actor=current_user)


@router.post(
    "/operations/{operation_id}/apply",
    response_model=BrandBulkPricingApplyResponse,
    summary="Apply a confirmed bulk pricing operation (step-up required)",
)
async def apply_brand_bulk_pricing(
    operation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    x_step_up_token: str | None = Header(None, alias="X-Step-Up-Token"),
):
    scope = f"{IDEMPOTENCY_SCOPE_PREFIX}:{operation_id}"
    if idempotency_key:
        existing = await crud_platform.get_idempotency_record(
            db, scope=scope, key=idempotency_key
        )
        if existing and existing.status_code and existing.response_body:
            return BrandBulkPricingApplyResponse(**existing.response_body)

    step_up_payload = await get_verified_step_up(x_step_up_token=x_step_up_token, db=db)
    if step_up_payload.get("sub") != current_user.phone_number:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.STEP_UP_MISMATCH,
            message="Step-up token does not match the authenticated user",
        )

    return await BrandBulkPricingService.apply_operation(
        db,
        operation_id,
        actor=current_user,
        idempotency_key=idempotency_key,
    )


@router.get(
    "/operations",
    response_model=BrandBulkPricingOperationListResponse,
    summary="List bulk pricing operation history",
)
async def list_brand_bulk_pricing_operations(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    brand_id: int | None = Query(None, ge=1),
):
    return await BrandBulkPricingService.list_operations(
        db, skip=skip, limit=limit, brand_id=brand_id
    )


@router.get(
    "/operations/{operation_id}",
    response_model=BrandBulkPricingOperationDetail,
    summary="Get bulk pricing operation detail",
)
async def get_brand_bulk_pricing_operation(
    operation_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    return await BrandBulkPricingService.get_operation(db, operation_id)
