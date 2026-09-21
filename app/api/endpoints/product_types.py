"""PT-W3A Product Type stewardship + manual assignment admin API.

All routes require get_current_super_admin. No public mutation surface.
Ambiguous products remain unassigned (product_type_id NULL).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.knowledge import (
    ProductTypeActivateRequest,
    ProductTypeAssignmentRequest,
    ProductTypeAssignmentResponse,
    ProductTypeCreateRequest,
    ProductTypeListResponse,
    ProductTypeResponse,
    ProductTypeUpdateRequest,
)
from app.services import product_type_assignment_service as assignment_service
from app.services import product_type_service as pt_service

router = APIRouter()


@router.post(
    "/product-types",
    response_model=ProductTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create draft Product Type (super-admin)",
)
async def create_product_type(
    body: ProductTypeCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> ProductTypeResponse:
    pt = await pt_service.create_product_type(
        db,
        code=body.code,
        slug=body.slug,
        name_fa=body.name_fa,
        name_en=body.name_en,
        description=body.description,
        actor=current_user,
    )
    await db.commit()
    await db.refresh(pt)
    return ProductTypeResponse.model_validate(pt)


@router.get(
    "/product-types",
    response_model=ProductTypeListResponse,
    summary="List Product Types (super-admin)",
)
async def list_product_types(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> ProductTypeListResponse:
    items = await pt_service.list_product_types(db)
    return ProductTypeListResponse(
        items=[ProductTypeResponse.model_validate(i) for i in items],
        total=len(items),
    )


@router.get(
    "/product-types/{product_type_id}",
    response_model=ProductTypeResponse,
    summary="Get Product Type (super-admin)",
)
async def get_product_type(
    product_type_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> ProductTypeResponse:
    pt = await pt_service.get_product_type(db, product_type_id)
    return ProductTypeResponse.model_validate(pt)


@router.patch(
    "/product-types/{product_type_id}",
    response_model=ProductTypeResponse,
    summary="Update draft Product Type metadata (super-admin)",
)
async def update_product_type(
    product_type_id: int,
    body: ProductTypeUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> ProductTypeResponse:
    patch = body.model_dump(exclude_unset=True)
    pt = await pt_service.update_draft_product_type(
        db,
        product_type_id=product_type_id,
        patch=patch,
        actor=current_user,
    )
    await db.commit()
    await db.refresh(pt)
    return ProductTypeResponse.model_validate(pt)


@router.post(
    "/product-types/{product_type_id}/activate",
    response_model=ProductTypeResponse,
    summary="Activate draft Product Type (super-admin; requires active Definition)",
)
async def activate_product_type(
    product_type_id: int,
    body: ProductTypeActivateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> ProductTypeResponse:
    pt = await pt_service.activate_product_type(
        db,
        product_type_id=product_type_id,
        change_reason=body.change_reason,
        actor=current_user,
    )
    await db.commit()
    await db.refresh(pt)
    return ProductTypeResponse.model_validate(pt)


@router.get(
    "/products/{product_id}/product-type-assignment",
    response_model=ProductTypeAssignmentResponse,
    summary="Get Product Type assignment (super-admin)",
)
async def get_product_type_assignment(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> ProductTypeAssignmentResponse:
    payload = await assignment_service.get_assignment(db, product_id)
    return ProductTypeAssignmentResponse.model_validate(payload)


@router.post(
    "/products/{product_id}/product-type-assignment",
    response_model=ProductTypeAssignmentResponse,
    summary="Manually assign/reassign/clear Product Type (super-admin)",
)
async def set_product_type_assignment(
    product_id: int,
    body: ProductTypeAssignmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> ProductTypeAssignmentResponse:
    payload = await assignment_service.assign_product_type(
        db,
        product_id=product_id,
        product_type_id=body.product_type_id,
        change_reason=body.change_reason,
        actor=current_user,
    )
    await db.commit()
    return ProductTypeAssignmentResponse.model_validate(payload)
