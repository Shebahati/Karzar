"""Prompt 13 Evidence stewardship — artifacts and links.

Evidence linkage never auto-publishes Facts and never appends FactRevisions.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, api_error
from app.crud.audit import record_audit_log
from app.db.models.knowledge import (
    EVIDENCE_ARTIFACT_KINDS,
    KnowledgeEdge,
    KnowledgeEvidenceArtifact,
    KnowledgeEvidenceLink,
    KnowledgeFact,
)
from app.db.models.user import User

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _actor_label(actor: User) -> str:
    return actor.phone_number or f"user:{actor.id}"


def locator_fingerprint(locator: dict[str, Any] | None) -> str:
    payload = locator or {}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_sha256(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    normalized = value.strip().lower()
    if not _SHA256_RE.fullmatch(normalized):
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="checksum_sha256 must be a 64-character lowercase hex digest",
            details=[{"field": "checksum_sha256", "message": "malformed"}],
        )
    return normalized


def _require_provenance(
    *,
    source_url: str | None,
    source_ref: str | None,
    checksum_sha256: str | None,
) -> None:
    if not (source_url or source_ref or checksum_sha256):
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Evidence Artifact requires at least one of source_url, source_ref, checksum_sha256",
            details=[{"field": "provenance", "message": "required"}],
        )


async def create_artifact(
    db: AsyncSession,
    *,
    artifact_id: str,
    kind: str,
    title: str | None,
    source_url: str | None,
    source_ref: str | None,
    checksum_sha256: str | None,
    publisher: str | None,
    document_version: str | None,
    notes: str | None,
    actor: User,
) -> KnowledgeEvidenceArtifact:
    if kind not in EVIDENCE_ARTIFACT_KINDS:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="invalid Evidence Artifact kind",
            details=[{"field": "kind", "message": "unsupported"}],
        )
    aid = (artifact_id or "").strip()
    if not aid:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="artifact_id is required",
            details=[{"field": "artifact_id", "message": "required"}],
        )
    digest = _validate_sha256(checksum_sha256)
    _require_provenance(
        source_url=source_url,
        source_ref=source_ref,
        checksum_sha256=digest,
    )

    existing = await db.scalar(
        select(KnowledgeEvidenceArtifact).where(
            KnowledgeEvidenceArtifact.artifact_id == aid
        )
    )
    if existing is not None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Evidence Artifact artifact_id already exists",
            details=[{"field": "artifact_id", "message": "duplicate"}],
        )

    row = KnowledgeEvidenceArtifact(
        artifact_id=aid,
        kind=kind,
        title=title,
        source_url=source_url,
        source_ref=source_ref,
        checksum_sha256=digest,
        publisher=publisher,
        document_version=document_version,
        recorded_at=datetime.now(UTC),
        recorder=_actor_label(actor),
        notes=notes,
    )
    db.add(row)
    await db.flush()
    await record_audit_log(
        db,
        actor_user_id=actor.id,
        action="knowledge_evidence_artifact.create",
        entity_type="knowledge_evidence_artifact",
        entity_id=str(row.id),
        details={"artifact_id": aid, "kind": kind},
    )
    return row


async def get_artifact(db: AsyncSession, artifact_pk: int) -> KnowledgeEvidenceArtifact:
    row = await db.get(KnowledgeEvidenceArtifact, artifact_pk)
    if row is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Evidence Artifact not found",
        )
    return row


async def list_artifacts(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[KnowledgeEvidenceArtifact]:
    stmt = (
        select(KnowledgeEvidenceArtifact)
        .order_by(KnowledgeEvidenceArtifact.id.asc())
        .offset(skip)
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


async def link_artifact_to_fact(
    db: AsyncSession,
    *,
    artifact_pk: int,
    fact_id: int,
    locator: dict[str, Any] | None,
    notes: str | None,
    actor: User,
) -> KnowledgeEvidenceLink:
    artifact = await get_artifact(db, artifact_pk)
    fact = await db.get(KnowledgeFact, fact_id)
    if fact is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Fact not found",
        )
    loc = locator or {}
    if not isinstance(loc, dict):
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="locator must be an object",
            details=[{"field": "locator", "message": "invalid"}],
        )
    fp = locator_fingerprint(loc)
    existing = await db.scalar(
        select(KnowledgeEvidenceLink.id).where(
            KnowledgeEvidenceLink.artifact_id == artifact.id,
            KnowledgeEvidenceLink.target_type == "fact",
            KnowledgeEvidenceLink.fact_id == fact.id,
            KnowledgeEvidenceLink.relation_type == "FACT_SUPPORTED_BY",
            KnowledgeEvidenceLink.locator_fingerprint == fp,
        )
    )
    if existing is not None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="duplicate Evidence link for this Fact/artifact/locator",
            details=[{"field": "evidence_link", "message": "duplicate"}],
        )
    link = KnowledgeEvidenceLink(
        artifact_id=artifact.id,
        target_type="fact",
        fact_id=fact.id,
        edge_id=None,
        relation_type="FACT_SUPPORTED_BY",
        locator=loc,
        locator_fingerprint=fp,
        recorded_at=datetime.now(UTC),
        recorder=_actor_label(actor),
        notes=notes,
    )
    db.add(link)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="duplicate Evidence link for this Fact/artifact/locator",
            details=[{"field": "evidence_link", "message": "duplicate"}],
        ) from exc
    await record_audit_log(
        db,
        actor_user_id=actor.id,
        action="knowledge_evidence_link.create",
        entity_type="knowledge_evidence_link",
        entity_id=str(link.id),
        details={
            "artifact_id": artifact.id,
            "target_type": "fact",
            "fact_id": fact.id,
            "relation_type": "FACT_SUPPORTED_BY",
        },
    )
    return link


async def link_artifact_to_edge(
    db: AsyncSession,
    *,
    artifact_pk: int,
    edge_id: int,
    locator: dict[str, Any] | None,
    notes: str | None,
    actor: User,
) -> KnowledgeEvidenceLink:
    artifact = await get_artifact(db, artifact_pk)
    edge = await db.get(KnowledgeEdge, edge_id)
    if edge is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Knowledge Edge not found",
        )
    loc = locator or {}
    if not isinstance(loc, dict):
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="locator must be an object",
            details=[{"field": "locator", "message": "invalid"}],
        )
    fp = locator_fingerprint(loc)
    existing = await db.scalar(
        select(KnowledgeEvidenceLink.id).where(
            KnowledgeEvidenceLink.artifact_id == artifact.id,
            KnowledgeEvidenceLink.target_type == "edge",
            KnowledgeEvidenceLink.edge_id == edge.id,
            KnowledgeEvidenceLink.relation_type == "EDGE_SUPPORTED_BY",
            KnowledgeEvidenceLink.locator_fingerprint == fp,
        )
    )
    if existing is not None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="duplicate Evidence link for this Edge/artifact/locator",
            details=[{"field": "evidence_link", "message": "duplicate"}],
        )
    link = KnowledgeEvidenceLink(
        artifact_id=artifact.id,
        target_type="edge",
        fact_id=None,
        edge_id=edge.id,
        relation_type="EDGE_SUPPORTED_BY",
        locator=loc,
        locator_fingerprint=fp,
        recorded_at=datetime.now(UTC),
        recorder=_actor_label(actor),
        notes=notes,
    )
    db.add(link)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="duplicate Evidence link for this Edge/artifact/locator",
            details=[{"field": "evidence_link", "message": "duplicate"}],
        ) from exc
    await record_audit_log(
        db,
        actor_user_id=actor.id,
        action="knowledge_evidence_link.create",
        entity_type="knowledge_evidence_link",
        entity_id=str(link.id),
        details={
            "artifact_id": artifact.id,
            "target_type": "edge",
            "edge_id": edge.id,
            "relation_type": "EDGE_SUPPORTED_BY",
        },
    )
    return link


async def list_links_for_fact(
    db: AsyncSession, fact_id: int
) -> list[KnowledgeEvidenceLink]:
    stmt = (
        select(KnowledgeEvidenceLink)
        .where(
            KnowledgeEvidenceLink.target_type == "fact",
            KnowledgeEvidenceLink.fact_id == fact_id,
            KnowledgeEvidenceLink.relation_type == "FACT_SUPPORTED_BY",
        )
        .order_by(KnowledgeEvidenceLink.id.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def list_links_for_edge(
    db: AsyncSession, edge_id: int
) -> list[KnowledgeEvidenceLink]:
    stmt = (
        select(KnowledgeEvidenceLink)
        .where(
            KnowledgeEvidenceLink.target_type == "edge",
            KnowledgeEvidenceLink.edge_id == edge_id,
            KnowledgeEvidenceLink.relation_type == "EDGE_SUPPORTED_BY",
        )
        .order_by(KnowledgeEvidenceLink.id.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def fact_has_supporting_evidence(db: AsyncSession, fact_id: int) -> bool:
    """True when at least one FACT_SUPPORTED_BY link to an existing Artifact exists."""
    stmt = (
        select(KnowledgeEvidenceLink.id)
        .join(
            KnowledgeEvidenceArtifact,
            KnowledgeEvidenceArtifact.id == KnowledgeEvidenceLink.artifact_id,
        )
        .where(
            KnowledgeEvidenceLink.target_type == "fact",
            KnowledgeEvidenceLink.fact_id == fact_id,
            KnowledgeEvidenceLink.relation_type == "FACT_SUPPORTED_BY",
        )
        .limit(1)
    )
    return (await db.scalar(stmt)) is not None
