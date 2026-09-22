"""Prompt 13 Taxonomy + classification admin API — super-admin only.

No public SEO routes. No commerce Category mutation. No PRODUCT_CLASSIFIED_AS
edge projection (deferred; assignment table is runtime source).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.knowledge import (
    ClassificationAssignmentCreateRequest,
    ClassificationAssignmentListResponse,
    ClassificationAssignmentResponse,
    TaxonomyNodeCreateRequest,
    TaxonomyNodeResponse,
    TaxonomyNodeStatusRequest,
)
from app.services import knowledge_taxonomy_service as taxonomy_service

router = APIRouter()


@router.post(
    "/taxonomy/nodes",
    response_model=TaxonomyNodeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create taxonomy node as draft (super-admin)",
)
async def create_taxonomy_node(
    body: TaxonomyNodeCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> TaxonomyNodeResponse:
    row = await taxonomy_service.create_taxonomy_node(
        db,
        node_id=body.node_id,
        dimension=body.dimension,
        node_type=body.node_type,
        slug=body.slug,
        name_fa=body.name_fa,
        name_en=body.name_en,
        parent_id=body.parent_id,
        synonyms=body.synonyms,
        seo_meta_title=body.seo_meta_title,
        seo_meta_description=body.seo_meta_description,
        commerce_category_id=body.commerce_category_id,
        product_type_id=body.product_type_id,
        sort_order=body.sort_order,
        steward=body.steward,
        actor=current_user,
    )
    await db.commit()
    await db.refresh(row)
    return TaxonomyNodeResponse.model_validate(row)


@router.get(
    "/taxonomy/nodes/{node_id}",
    response_model=TaxonomyNodeResponse,
    summary="Get taxonomy node (super-admin)",
)
async def get_taxonomy_node(
    node_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> TaxonomyNodeResponse:
    row = await taxonomy_service.get_taxonomy_node(db, node_id)
    return TaxonomyNodeResponse.model_validate(row)


@router.post(
    "/taxonomy/nodes/{node_id}/status",
    response_model=TaxonomyNodeResponse,
    summary="Activate or deprecate taxonomy node (super-admin)",
)
async def set_taxonomy_node_status(
    node_id: int,
    body: TaxonomyNodeStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> TaxonomyNodeResponse:
    row = await taxonomy_service.update_taxonomy_node_status(
        db,
        node_pk=node_id,
        status_value=body.status,
        actor=current_user,
    )
    await db.commit()
    await db.refresh(row)
    return TaxonomyNodeResponse.model_validate(row)


@router.post(
    "/products/{product_id}/classification-assignments",
    response_model=ClassificationAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create secondary classification assignment (super-admin)",
)
async def create_classification_assignment(
    product_id: int,
    body: ClassificationAssignmentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> ClassificationAssignmentResponse:
    row = await taxonomy_service.create_classification_assignment(
        db,
        product_id=product_id,
        taxonomy_node_id=body.taxonomy_node_id,
        assignment_role=body.assignment_role,
        is_primary=body.is_primary,
        source_ref=body.source_ref,
        notes=body.notes,
        actor=current_user,
    )
    await db.commit()
    await db.refresh(row)
    return ClassificationAssignmentResponse.model_validate(row)


@router.get(
    "/products/{product_id}/classification-assignments",
    response_model=ClassificationAssignmentListResponse,
    summary="List classification assignments for a product (super-admin)",
)
async def list_classification_assignments(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> ClassificationAssignmentListResponse:
    items = await taxonomy_service.list_assignments_for_product(db, product_id)
    return ClassificationAssignmentListResponse(
        items=[ClassificationAssignmentResponse.model_validate(i) for i in items],
        total=len(items),
    )
