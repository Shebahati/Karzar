"""Prompt 13 Evidence admin API — super-admin only."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.knowledge import (
    EvidenceArtifactCreateRequest,
    EvidenceArtifactListResponse,
    EvidenceArtifactResponse,
    EvidenceLinkCreateRequest,
    EvidenceLinkListResponse,
    EvidenceLinkResponse,
)
from app.services import knowledge_evidence_service as evidence_service

router = APIRouter()


@router.post(
    "/evidence/artifacts",
    response_model=EvidenceArtifactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Evidence Artifact (super-admin)",
)
async def create_evidence_artifact(
    body: EvidenceArtifactCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> EvidenceArtifactResponse:
    row = await evidence_service.create_artifact(
        db,
        artifact_id=body.artifact_id,
        kind=body.kind,
        title=body.title,
        source_url=body.source_url,
        source_ref=body.source_ref,
        checksum_sha256=body.checksum_sha256,
        publisher=body.publisher,
        document_version=body.document_version,
        notes=body.notes,
        actor=current_user,
    )
    await db.commit()
    await db.refresh(row)
    return EvidenceArtifactResponse.model_validate(row)


@router.get(
    "/evidence/artifacts",
    response_model=EvidenceArtifactListResponse,
    summary="List Evidence Artifacts (super-admin)",
)
async def list_evidence_artifacts(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> EvidenceArtifactListResponse:
    items = await evidence_service.list_artifacts(db)
    return EvidenceArtifactListResponse(
        items=[EvidenceArtifactResponse.model_validate(i) for i in items],
        total=len(items),
    )


@router.get(
    "/evidence/artifacts/{artifact_id}",
    response_model=EvidenceArtifactResponse,
    summary="Get Evidence Artifact (super-admin)",
)
async def get_evidence_artifact(
    artifact_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> EvidenceArtifactResponse:
    row = await evidence_service.get_artifact(db, artifact_id)
    return EvidenceArtifactResponse.model_validate(row)


@router.post(
    "/facts/{fact_id}/evidence-links",
    response_model=EvidenceLinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Link Evidence Artifact to Fact (super-admin; does not auto-publish)",
)
async def link_evidence_to_fact(
    fact_id: int,
    body: EvidenceLinkCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> EvidenceLinkResponse:
    link = await evidence_service.link_artifact_to_fact(
        db,
        artifact_pk=body.artifact_id,
        fact_id=fact_id,
        locator=body.locator,
        notes=body.notes,
        actor=current_user,
    )
    await db.commit()
    await db.refresh(link)
    return EvidenceLinkResponse.model_validate(link)


@router.get(
    "/facts/{fact_id}/evidence-links",
    response_model=EvidenceLinkListResponse,
    summary="List Evidence links for a Fact (super-admin)",
)
async def list_fact_evidence_links(
    fact_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> EvidenceLinkListResponse:
    items = await evidence_service.list_links_for_fact(db, fact_id)
    return EvidenceLinkListResponse(
        items=[EvidenceLinkResponse.model_validate(i) for i in items],
        total=len(items),
    )


@router.post(
    "/edges/{edge_id}/evidence-links",
    response_model=EvidenceLinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Link Evidence Artifact to Edge (super-admin)",
)
async def link_evidence_to_edge(
    edge_id: int,
    body: EvidenceLinkCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
) -> EvidenceLinkResponse:
    link = await evidence_service.link_artifact_to_edge(
        db,
        artifact_pk=body.artifact_id,
        edge_id=edge_id,
        locator=body.locator,
        notes=body.notes,
        actor=current_user,
    )
    await db.commit()
    await db.refresh(link)
    return EvidenceLinkResponse.model_validate(link)


@router.get(
    "/edges/{edge_id}/evidence-links",
    response_model=EvidenceLinkListResponse,
    summary="List Evidence links for an Edge (super-admin)",
)
async def list_edge_evidence_links(
    edge_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> EvidenceLinkListResponse:
    items = await evidence_service.list_links_for_edge(db, edge_id)
    return EvidenceLinkListResponse(
        items=[EvidenceLinkResponse.model_validate(i) for i in items],
        total=len(items),
    )
