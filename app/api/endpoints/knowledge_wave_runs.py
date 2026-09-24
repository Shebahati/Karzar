"""Knowledge Wave run ledger APIs (PR3-A) — super-admin only."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.knowledge import (
    KnowledgeWaveExecuteResponse,
    KnowledgeWaveResumeRequest,
    KnowledgeWaveRunResponse,
)
from app.services import knowledge_wave_execute_service as execute_service

router = APIRouter()


@router.get(
    "/wave-runs/{run_id}",
    response_model=KnowledgeWaveRunResponse,
    summary="Get wave run ledger (super-admin)",
)
async def get_wave_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> KnowledgeWaveRunResponse:
    result = await execute_service.get_wave_run(db, run_id)
    return KnowledgeWaveRunResponse.model_validate(result)


@router.post(
    "/wave-runs/{run_id}/resume",
    response_model=KnowledgeWaveExecuteResponse,
    status_code=201,
    summary="Resume failed or interrupted wave assert run (super-admin)",
)
async def resume_wave_run(
    run_id: int,
    body: KnowledgeWaveResumeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> KnowledgeWaveExecuteResponse:
    sku_units = None
    if body.sku_units is not None:
        sku_units = [u.model_dump() for u in body.sku_units]
    result = await execute_service.resume_wave_run(
        db,
        run_id=run_id,
        change_reason=body.change_reason,
        actor=current_user,
        sku_units=sku_units,
        stop_on_first_failure=body.stop_on_first_failure,
    )
    return KnowledgeWaveExecuteResponse.model_validate(result)
