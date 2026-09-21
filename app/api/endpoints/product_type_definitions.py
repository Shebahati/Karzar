"""PT-W2 Product Type Definition + Attribute Membership admin API.

All routes require get_current_super_admin. No public mutation surface.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.knowledge import (
    ProductTypeAttributeMembershipCreateRequest,
    ProductTypeAttributeMembershipResponse,
    ProductTypeAttributeMembershipUpdateRequest,
    ProductTypeDefinitionActivateRequest,
    ProductTypeDefinitionCreateRequest,
    ProductTypeDefinitionListResponse,
    ProductTypeDefinitionResponse,
)
from app.services import product_type_definition_service as ptd_service

router = APIRouter()


@router.post(
    "/product-types/{product_type_id}/definitions",
    response_model=ProductTypeDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create draft Product Type Definition (super-admin)",
)
async def create_product_type_definition(
    product_type_id: int,
    body: ProductTypeDefinitionCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> ProductTypeDefinitionResponse:
    definition = await ptd_service.create_draft_definition(
        db,
        product_type_id=product_type_id,
        notes=body.notes,
        version=body.version,
    )
    await db.commit()
    loaded = await ptd_service.get_definition(db, definition.id)
    return ProductTypeDefinitionResponse.model_validate(loaded)


@router.get(
    "/product-types/{product_type_id}/definitions",
    response_model=ProductTypeDefinitionListResponse,
    summary="List Product Type Definitions (super-admin)",
)
async def list_product_type_definitions(
    product_type_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> ProductTypeDefinitionListResponse:
    items = await ptd_service.list_definitions(db, product_type_id)
    return ProductTypeDefinitionListResponse(
        items=[ProductTypeDefinitionResponse.model_validate(i) for i in items],
        total=len(items),
    )


@router.get(
    "/product-type-definitions/{definition_id}",
    response_model=ProductTypeDefinitionResponse,
    summary="Get Product Type Definition with memberships (super-admin)",
)
async def get_product_type_definition(
    definition_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> ProductTypeDefinitionResponse:
    definition = await ptd_service.get_definition(db, definition_id)
    return ProductTypeDefinitionResponse.model_validate(definition)


@router.post(
    "/product-type-definitions/{definition_id}/memberships",
    response_model=ProductTypeAttributeMembershipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add attribute membership to a draft Definition (super-admin)",
)
async def add_definition_membership(
    definition_id: int,
    body: ProductTypeAttributeMembershipCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> ProductTypeAttributeMembershipResponse:
    membership = await ptd_service.add_membership(
        db,
        definition_id=definition_id,
        property_definition_id=body.property_definition_id,
        requiredness=body.requiredness,
        applicability_condition=body.applicability_condition,
        validation_overrides=body.validation_overrides,
        public_visibility_default=body.public_visibility_default,
        filterable=body.filterable,
        comparable=body.comparable,
        display_group=body.display_group,
        display_order=body.display_order,
        evidence_requirement_override=body.evidence_requirement_override,
    )
    await db.commit()
    await db.refresh(membership)
    return ProductTypeAttributeMembershipResponse.model_validate(membership)


@router.put(
    "/product-type-definitions/{definition_id}/memberships/{membership_id}",
    response_model=ProductTypeAttributeMembershipResponse,
    summary="Update attribute membership on a draft Definition (super-admin)",
)
async def update_definition_membership(
    definition_id: int,
    membership_id: int,
    body: ProductTypeAttributeMembershipUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> ProductTypeAttributeMembershipResponse:
    patch = body.model_dump(exclude_unset=True)
    membership = await ptd_service.update_membership(
        db,
        definition_id=definition_id,
        membership_id=membership_id,
        patch=patch,
    )
    await db.commit()
    await db.refresh(membership)
    return ProductTypeAttributeMembershipResponse.model_validate(membership)


@router.delete(
    "/product-type-definitions/{definition_id}/memberships/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove attribute membership from a draft Definition (super-admin)",
)
async def delete_definition_membership(
    definition_id: int,
    membership_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> None:
    await ptd_service.remove_membership(
        db,
        definition_id=definition_id,
        membership_id=membership_id,
    )
    await db.commit()


@router.post(
    "/product-type-definitions/{definition_id}/activate",
    response_model=ProductTypeDefinitionResponse,
    summary="Activate draft Definition (super-admin; retires prior active)",
)
async def activate_product_type_definition(
    definition_id: int,
    body: ProductTypeDefinitionActivateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> ProductTypeDefinitionResponse:
    definition = await ptd_service.activate_definition(
        db,
        definition_id=definition_id,
        reviewer=current_user,
        change_reason=body.change_reason,
    )
    await db.commit()
    loaded = await ptd_service.get_definition(db, definition.id)
    return ProductTypeDefinitionResponse.model_validate(loaded)
