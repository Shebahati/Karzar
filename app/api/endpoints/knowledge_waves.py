"""Knowledge Wave Registry PR1/PR2 — Draft/Review/Seal APIs (super-admin only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.knowledge import (
    KnowledgeWaveCreateRequest,
    KnowledgeWaveExecuteRequest,
    KnowledgeWaveExecuteResponse,
    KnowledgeWaveListResponse,
    KnowledgeWaveResponse,
    KnowledgeWaveReviewRequest,
    KnowledgeWaveSealRequest,
    KnowledgeWaveUpdateRequest,
    KnowledgeWaveValidateResponse,
)
from app.services import knowledge_wave_execute_service as execute_service
from app.services import knowledge_wave_service as wave_service

router = APIRouter()


@router.post(
    "/waves",
    response_model=KnowledgeWaveResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Draft knowledge wave (super-admin)",
)
async def create_wave(
    body: KnowledgeWaveCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> KnowledgeWaveResponse:
    products = [p.model_dump() for p in body.products]
    wave = await wave_service.create_draft_wave(
        db,
        wave_id=body.wave_id,
        brand=body.brand,
        product_type_id=body.product_type_id,
        definition_id=body.definition_id,
        policy_json=body.policy_json,
        products=products,
        actor=current_user,
    )
    await db.commit()
    return KnowledgeWaveResponse.model_validate(wave)


@router.get(
    "/waves",
    response_model=KnowledgeWaveListResponse,
    summary="List knowledge waves (super-admin)",
)
async def list_waves(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> KnowledgeWaveListResponse:
    items = await wave_service.list_waves(db)
    return KnowledgeWaveListResponse(
        items=[KnowledgeWaveResponse.model_validate(i) for i in items],
        total=len(items),
    )


@router.get(
    "/waves/{wave_pk}",
    response_model=KnowledgeWaveResponse,
    summary="Get knowledge wave by id (super-admin)",
)
async def get_wave(
    wave_pk: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> KnowledgeWaveResponse:
    wave = await wave_service.get_wave(db, wave_pk)
    return KnowledgeWaveResponse.model_validate(wave)


@router.patch(
    "/waves/{wave_pk}",
    response_model=KnowledgeWaveResponse,
    summary="Patch Draft wave fields (super-admin; Sealed immutable)",
)
async def patch_draft_wave(
    wave_pk: int,
    body: KnowledgeWaveUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> KnowledgeWaveResponse:
    patch = body.model_dump(exclude_unset=True)
    wave = await wave_service.update_draft_wave(
        db,
        wave_pk=wave_pk,
        patch=patch,
        actor=current_user,
    )
    await db.commit()
    return KnowledgeWaveResponse.model_validate(wave)


@router.post(
    "/waves/{wave_pk}/review",
    response_model=KnowledgeWaveResponse,
    summary="Transition Draft↔Reviewed (super-admin)",
)
async def review_wave(
    wave_pk: int,
    body: KnowledgeWaveReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> KnowledgeWaveResponse:
    wave = await wave_service.review_wave(
        db,
        wave_pk=wave_pk,
        to_status=body.to_status,
        change_reason=body.change_reason,
        actor=current_user,
    )
    await db.commit()
    return KnowledgeWaveResponse.model_validate(wave)


@router.post(
    "/waves/{wave_pk}/seal",
    response_model=KnowledgeWaveResponse,
    summary="Seal Reviewed wave (super-admin; stores manifest_sha256)",
)
async def seal_wave(
    wave_pk: int,
    body: KnowledgeWaveSealRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> KnowledgeWaveResponse:
    wave = await wave_service.seal_wave(
        db,
        wave_pk=wave_pk,
        change_reason=body.change_reason,
        actor=current_user,
    )
    await db.commit()
    return KnowledgeWaveResponse.model_validate(wave)


@router.post(
    "/waves/{wave_pk}/validate",
    response_model=KnowledgeWaveValidateResponse,
    summary="Validate wave by status tier (super-admin; no execution)",
)
async def validate_wave(
    wave_pk: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> KnowledgeWaveValidateResponse:
    result = await wave_service.validate_wave(
        db,
        wave_pk=wave_pk,
        actor=current_user,
    )
    await db.commit()
    return KnowledgeWaveValidateResponse.model_validate(result)


@router.post(
    "/waves/{wave_id}/execute",
    response_model=KnowledgeWaveExecuteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute Sealed wave assert (super-admin; sync SKU loop)",
)
async def execute_wave(
    wave_id: str,
    body: KnowledgeWaveExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> KnowledgeWaveExecuteResponse:
    result = await execute_service.execute_wave(
        db,
        wave_id=wave_id,
        sku_units=[u.model_dump() for u in body.sku_units],
        change_reason=body.change_reason,
        actor=current_user,
        stop_on_first_failure=body.stop_on_first_failure,
    )
    # execute_wave commits internally per SKU
    return KnowledgeWaveExecuteResponse.model_validate(result)
