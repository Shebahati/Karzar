"""Prompt 12 Fact admin API — super-admin only. No public Fact surface."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.knowledge import (
    KnowledgeFactCreateRequest,
    KnowledgeFactLifecycleRequest,
    KnowledgeFactListResponse,
    KnowledgeFactResponse,
    KnowledgeFactRevisionListResponse,
    KnowledgeFactRevisionResponse,
    KnowledgeFactUpdateRequest,
)
from app.services import knowledge_fact_service as fact_service

router = APIRouter()


@router.post(
    "/products/{product_id}/facts",
    response_model=KnowledgeFactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create asserted Fact (super-admin)",
)
async def create_product_fact(
    product_id: int,
    body: KnowledgeFactCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> KnowledgeFactResponse:
    fact = await fact_service.create_fact(
        db,
        product_id=product_id,
        definition_id=body.definition_id,
        value=body.value,
        unit=body.unit,
        qualifier=body.qualifier,
        source_id=body.source_id,
        confidence=body.confidence,
        actor=current_user,
    )
    await db.commit()
    await db.refresh(fact)
    return KnowledgeFactResponse.model_validate(fact)


@router.get(
    "/products/{product_id}/facts",
    response_model=KnowledgeFactListResponse,
    summary="List Facts for a product (super-admin; all statuses)",
)
async def list_product_facts(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> KnowledgeFactListResponse:
    items = await fact_service.list_facts_for_product(
        db, product_id, public_only=False
    )
    return KnowledgeFactListResponse(
        items=[KnowledgeFactResponse.model_validate(i) for i in items],
        total=len(items),
    )


@router.get(
    "/facts/{fact_id}",
    response_model=KnowledgeFactResponse,
    summary="Get Fact by id (super-admin)",
)
async def get_fact(
    fact_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> KnowledgeFactResponse:
    fact = await fact_service.get_fact(db, fact_id)
    return KnowledgeFactResponse.model_validate(fact)


@router.put(
    "/facts/{fact_id}",
    response_model=KnowledgeFactResponse,
    summary="Update Fact value fields (super-admin; not status)",
)
async def update_fact(
    fact_id: int,
    body: KnowledgeFactUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> KnowledgeFactResponse:
    patch = body.model_dump(exclude_unset=True)
    change_reason = patch.pop("change_reason", None)
    fact = await fact_service.update_fact(
        db,
        fact_id=fact_id,
        patch=patch,
        actor=current_user,
        change_reason=change_reason,
    )
    await db.commit()
    await db.refresh(fact)
    return KnowledgeFactResponse.model_validate(fact)


@router.get(
    "/facts/{fact_id}/revisions",
    response_model=KnowledgeFactRevisionListResponse,
    summary="List append-only Fact revisions (super-admin)",
)
async def list_fact_revisions(
    fact_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> KnowledgeFactRevisionListResponse:
    items = await fact_service.list_revisions(db, fact_id)
    return KnowledgeFactRevisionListResponse(
        items=[KnowledgeFactRevisionResponse.model_validate(i) for i in items],
        total=len(items),
    )


@router.post(
    "/facts/{fact_id}/publish",
    response_model=KnowledgeFactResponse,
    summary="Publish asserted Fact (super-admin)",
)
async def publish_fact(
    fact_id: int,
    body: KnowledgeFactLifecycleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> KnowledgeFactResponse:
    fact = await fact_service.publish_fact(
        db,
        fact_id=fact_id,
        actor=current_user,
        change_reason=body.change_reason,
    )
    await db.commit()
    await db.refresh(fact)
    return KnowledgeFactResponse.model_validate(fact)


@router.post(
    "/facts/{fact_id}/dispute",
    response_model=KnowledgeFactResponse,
    summary="Mark published Fact disputed (super-admin)",
)
async def dispute_fact(
    fact_id: int,
    body: KnowledgeFactLifecycleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> KnowledgeFactResponse:
    fact = await fact_service.dispute_fact(
        db,
        fact_id=fact_id,
        actor=current_user,
        change_reason=body.change_reason,
    )
    await db.commit()
    await db.refresh(fact)
    return KnowledgeFactResponse.model_validate(fact)


@router.post(
    "/facts/{fact_id}/deprecate",
    response_model=KnowledgeFactResponse,
    summary="Deprecate Fact (super-admin)",
)
async def deprecate_fact(
    fact_id: int,
    body: KnowledgeFactLifecycleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> KnowledgeFactResponse:
    fact = await fact_service.deprecate_fact(
        db,
        fact_id=fact_id,
        actor=current_user,
        change_reason=body.change_reason,
    )
    await db.commit()
    await db.refresh(fact)
    return KnowledgeFactResponse.model_validate(fact)
