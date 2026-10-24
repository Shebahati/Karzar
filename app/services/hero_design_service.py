"""Hero Studio pack validation, seeding, publish, and rollback."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ErrorCode, api_error
from app.db.models.hero_design import (
    HERO_PROFILE_REBORN_5_V1,
    HeroDesignDraft,
    HeroDesignPublished,
    HeroDesignRevision,
)
from app.db.models.user import User
from app.schemas.hero_design import (
    EXPECTED_R0_SHA256,
    REBORN_FIVE_ASSET_PREFIX,
    REBORN_FIVE_DOCK_KEYS,
    REBORN_FIVE_SLIDE_IDS,
    HeroValidationErrorItem,
)
from app.services.audit_service import record_audit

REPO_ROOT = Path(__file__).resolve().parents[2]
STOREFRONT_PACK_PATH = REPO_ROOT / "frontend" / "Storefront" / "public" / "hero-design.json"
FIXTURE_PACK_PATH = REPO_ROOT / "tests" / "fixtures" / "hero_design_r0.json"


def api_publish_enabled() -> bool:
    return bool(settings.HERO_STUDIO_API_PUBLISH)


def pack_file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pack_canonical_sha256(pack: dict[str, Any]) -> str:
    payload = json.dumps(pack, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_pack_from_path(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_pack(pack: dict[str, Any]) -> list[HeroValidationErrorItem]:
    errors: list[HeroValidationErrorItem] = []
    if pack.get("version") != 1:
        errors.append(HeroValidationErrorItem(field="version", message="must be 1"))
    slides = pack.get("slides")
    if not isinstance(slides, list):
        errors.append(HeroValidationErrorItem(field="slides", message="must be array"))
        return errors
    active = [s for s in slides if isinstance(s, dict) and s.get("isActive")]
    if len(active) != 5:
        errors.append(
            HeroValidationErrorItem(field="slides", message="requires exactly 5 active slides")
        )
    keys: list[str] = []
    for slide in active:
        cfg = slide.get("config") if isinstance(slide.get("config"), dict) else {}
        key = cfg.get("linkedOrbKey")
        if isinstance(key, str):
            keys.append(key)
    active_sorted = sorted(
        active,
        key=lambda s: int(s.get("sortOrder") or 0) if isinstance(s.get("sortOrder"), int | float) else 0,
    )
    slide_ids = [s.get("id") for s in active_sorted if isinstance(s.get("id"), str)]
    if slide_ids != list(REBORN_FIVE_SLIDE_IDS):
        errors.append(
            HeroValidationErrorItem(
                field="slides.id",
                message=f"expected active slide ids {list(REBORN_FIVE_SLIDE_IDS)}",
            )
        )
    for idx, slide in enumerate(active_sorted):
        cfg = slide.get("config") if isinstance(slide.get("config"), dict) else {}
        bg = cfg.get("background") if isinstance(cfg.get("background"), dict) else {}
        for field in ("imageUrl", "mobileImageUrl"):
            url = bg.get(field)
            if not isinstance(url, str) or not url.startswith(REBORN_FIVE_ASSET_PREFIX):
                errors.append(
                    HeroValidationErrorItem(
                        field=f"slides[{idx}].config.background.{field}",
                        message=f"must start with {REBORN_FIVE_ASSET_PREFIX}",
                    )
                )

    if keys != list(REBORN_FIVE_DOCK_KEYS):
        errors.append(
            HeroValidationErrorItem(
                field="slides.config.linkedOrbKey",
                message=f"expected order {list(REBORN_FIVE_DOCK_KEYS)}",
            )
        )
    dock = pack.get("categoryDock")
    if not isinstance(dock, dict):
        errors.append(HeroValidationErrorItem(field="categoryDock", message="required"))
    else:
        cats = dock.get("categories")
        if not isinstance(cats, list):
            errors.append(HeroValidationErrorItem(field="categoryDock.categories", message="array"))
        else:
            featured = sorted(
                [
                    c
                    for c in cats
                    if isinstance(c, dict) and c.get("featuredOrder") is not None
                ],
                key=lambda c: int(c.get("featuredOrder") or 0),
            )
            featured_keys = [c.get("key") for c in featured]
            if featured_keys != list(REBORN_FIVE_DOCK_KEYS):
                errors.append(
                    HeroValidationErrorItem(
                        field="categoryDock.categories.featuredOrder",
                        message="featured dock keys mismatch",
                    )
                )
    return errors


def _publish_disabled() -> None:
    raise api_error(
        status.HTTP_403_FORBIDDEN,
        error_code=ErrorCode.FORBIDDEN,
        message="Hero Studio API publish is disabled",
        details=[{"field": "HERO_STUDIO_API_PUBLISH", "message": "hero_publish_disabled"}],
    )


async def _lock_published_pointer(db: AsyncSession) -> HeroDesignPublished | None:
    result = await db.execute(
        select(HeroDesignPublished).where(HeroDesignPublished.id == 1).with_for_update()
    )
    return result.scalar_one_or_none()


async def get_published_pointer(db: AsyncSession) -> HeroDesignPublished | None:
    return await db.get(HeroDesignPublished, 1)


async def get_published_revision(db: AsyncSession) -> HeroDesignRevision | None:
    pointer = await get_published_pointer(db)
    if pointer is None:
        return None
    return await db.get(HeroDesignRevision, pointer.revision_id)


async def seed_r0_if_absent(db: AsyncSession, *, actor_id: int | None = None) -> str | None:
    """Idempotent R0 seed from Storefront JSON. Returns revision id if created."""
    existing = await get_published_pointer(db)
    if existing is not None:
        return None
    path = STOREFRONT_PACK_PATH if STOREFRONT_PACK_PATH.is_file() else FIXTURE_PACK_PATH
    sha = pack_file_sha256(path)
    if sha != EXPECTED_R0_SHA256:
        raise ValueError(f"R0 pack SHA mismatch: {sha}")
    pack = load_pack_from_path(path)
    errors = validate_pack(pack)
    if errors:
        raise ValueError("R0 pack failed validation")
    revision = HeroDesignRevision(
        schema_version=int(pack.get("version") or 1),
        profile=HERO_PROFILE_REBORN_5_V1,
        pack_json=pack,
        pack_sha256=sha,
        parent_revision_id=None,
        status="published",
        created_by=actor_id,
    )
    db.add(revision)
    await db.flush()
    db.add(
        HeroDesignPublished(
            id=1,
            revision_id=revision.id,
            etag=sha,
            published_by=actor_id,
        )
    )
    db.add(
        HeroDesignDraft(
            id=1,
            base_revision_id=revision.id,
            draft_json=pack,
            lock_version=1,
            updated_by=actor_id,
        )
    )
    await db.flush()
    return revision.id


async def list_revisions(
    db: AsyncSession, *, limit: int = 20, offset: int = 0
) -> tuple[list[HeroDesignRevision], int]:
    total = (
        await db.execute(select(HeroDesignRevision))
    ).scalars().all()
    rows = (
        await db.execute(
            select(HeroDesignRevision)
            .order_by(HeroDesignRevision.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return list(rows), len(total)


async def get_draft_row(db: AsyncSession) -> HeroDesignDraft | None:
    return await db.get(HeroDesignDraft, 1)


async def publish_from_server_draft(
    db: AsyncSession,
    *,
    actor: User,
    expected_parent_revision_id: str | None,
    publish_comment: str | None,
) -> HeroDesignPublished:
    if not api_publish_enabled():
        _publish_disabled()
    draft = await get_draft_row(db)
    if draft is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="No server draft",
        )
    pack = draft.draft_json
    errors = validate_pack(pack)
    if errors:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Pack validation failed",
            details=[e.model_dump() for e in errors],
        )
    pointer = await _lock_published_pointer(db)
    current_parent = pointer.revision_id if pointer else None
    if expected_parent_revision_id != current_parent:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Parent revision mismatch",
            details=[
                {
                    "field": "expected_parent_revision_id",
                    "message": f"expected {expected_parent_revision_id!r} current {current_parent!r}",
                }
            ],
        )
    if pointer:
        current_rev = await db.get(HeroDesignRevision, pointer.revision_id)
        if current_rev and current_rev.status == "published":
            current_rev.status = "superseded"
    sha = pack_canonical_sha256(pack)
    revision = HeroDesignRevision(
        schema_version=int(pack.get("version") or 1),
        profile=HERO_PROFILE_REBORN_5_V1,
        pack_json=pack,
        pack_sha256=sha,
        parent_revision_id=current_parent,
        status="published",
        created_by=actor.id,
        publish_comment=publish_comment,
    )
    db.add(revision)
    await db.flush()
    now = datetime.now(UTC)
    if pointer is None:
        pointer = HeroDesignPublished(id=1, revision_id=revision.id, etag=sha, published_by=actor.id)
        db.add(pointer)
    else:
        pointer.revision_id = revision.id
        pointer.etag = sha
        pointer.published_at = now
        pointer.published_by = actor.id
    draft.base_revision_id = revision.id
    draft.draft_json = pack
    draft.lock_version += 1
    draft.updated_by = actor.id
    draft.updated_at = now
    await record_audit(
        db,
        actor_user_id=actor.id,
        action="hero_design.publish",
        entity_type="hero_design",
        entity_id=revision.id,
        details={"pack_sha256": sha, "parent_revision_id": current_parent},
    )
    await db.flush()
    return pointer


async def rollback_to_revision(
    db: AsyncSession,
    *,
    actor: User,
    revision_id: str,
) -> HeroDesignPublished:
    if not api_publish_enabled():
        _publish_disabled()
    target = await db.get(HeroDesignRevision, revision_id)
    if target is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Revision not found",
        )
    pointer = await _lock_published_pointer(db)
    if pointer is None:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="No published pointer",
        )
    if pointer.revision_id == revision_id:
        return pointer
    current = await db.get(HeroDesignRevision, pointer.revision_id)
    if current and current.status == "published":
        current.status = "superseded"
    target.status = "published"
    pointer.revision_id = revision_id
    pointer.etag = target.pack_sha256
    pointer.published_at = datetime.now(UTC)
    pointer.published_by = actor.id
    draft = await get_draft_row(db)
    if draft:
        draft.base_revision_id = revision_id
        draft.draft_json = target.pack_json
        draft.lock_version += 1
        draft.updated_by = actor.id
        draft.updated_at = datetime.now(UTC)
    await record_audit(
        db,
        actor_user_id=actor.id,
        action="hero_design.rollback",
        entity_type="hero_design",
        entity_id=revision_id,
        details={"pack_sha256": target.pack_sha256},
    )
    await db.flush()
    return pointer
