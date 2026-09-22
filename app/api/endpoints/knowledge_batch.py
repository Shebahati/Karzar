"""Prompt 41 — governed SKU-unit KB batch assert endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.knowledge import (
    KnowledgeBatchAssertRequest,
    KnowledgeBatchAssertResponse,
)
from app.services import knowledge_batch_assert_service as batch_service

router = APIRouter()


@router.post(
    "/products/{product_id}/kb-batch-assert",
    response_model=KnowledgeBatchAssertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Atomic SKU KB unit: assign GEN_CALIPER + assert 3 Facts + 3 Evidence links",
)
async def kb_batch_assert(
    product_id: int,
    body: KnowledgeBatchAssertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> KnowledgeBatchAssertResponse:
    """Single commit for one Product KB assertion unit (Prompt 41).

    Never publishes Facts. Never creates Evidence Artifacts. Never mutates JSONB.
    """
    payload = await batch_service.execute_kb_batch_assert(
        db,
        product_id=product_id,
        manifest_sha256=body.manifest_sha256,
        sku=body.sku,
        product_type_id=body.product_type_id,
        definition_id=body.definition_id,
        facts=[f.model_dump() for f in body.facts],
        evidence_links=[e.model_dump() for e in body.evidence_links],
        change_reason=body.change_reason,
        actor=current_user,
    )
    await db.commit()
    return KnowledgeBatchAssertResponse.model_validate(payload)
