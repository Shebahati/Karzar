"""Hero Studio CMS + Storefront read APIs (PR1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin, verify_and_consume_step_up
from app.core.errors import ErrorCode, api_error
from app.db.database import get_db
from app.db.models.hero_design import HeroDesignRevision
from app.db.models.user import User
from app.schemas.hero_design import (
    HeroDesignedPackResponse,
    HeroDraftReadResponse,
    HeroPublishRequest,
    HeroPublishResult,
    HeroRevisionListResponse,
    HeroRevisionSummary,
    HeroRollbackRequest,
    HeroValidateRequest,
    HeroValidateResponse,
)
from app.services import hero_design_service as hero_service

storefront_router = APIRouter()
cms_router = APIRouter()


def _pack_response(pointer, revision: HeroDesignRevision) -> HeroDesignedPackResponse:
    return HeroDesignedPackResponse(
        revision_id=revision.id,
        etag=pointer.etag,
        profile=revision.profile,
        schema_version=revision.schema_version,
        published_at=pointer.published_at,
        pack=revision.pack_json,
        published_by=pointer.published_by,
        pack_sha256=revision.pack_sha256,
    )


@storefront_router.get("/storefront/hero-design", response_model=HeroDesignedPackResponse)
async def get_storefront_hero_design(
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    pointer = await hero_service.get_published_pointer(db)
    if pointer is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="No published hero design",
        )
    revision = await db.get(HeroDesignRevision, pointer.revision_id)
    if revision is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Published revision missing",
        )
    response.headers["Cache-Control"] = "public, max-age=60"
    response.headers["ETag"] = f'"{pointer.etag}"'
    return _pack_response(pointer, revision)


@cms_router.get("/hero-design/published", response_model=HeroDesignedPackResponse)
async def get_cms_published(
    _: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    pointer = await hero_service.get_published_pointer(db)
    if pointer is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="No published hero design",
        )
    revision = await db.get(HeroDesignRevision, pointer.revision_id)
    if revision is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Published revision missing",
        )
    return _pack_response(pointer, revision)


@cms_router.get("/hero-design/revisions", response_model=HeroRevisionListResponse)
async def list_revisions(
    limit: int = 20,
    offset: int = 0,
    _: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    limit = min(max(limit, 1), 100)
    rows, total = await hero_service.list_revisions(db, limit=limit, offset=offset)
    items = [
        HeroRevisionSummary(
            id=r.id,
            status=r.status,
            pack_sha256=r.pack_sha256,
            created_at=r.created_at,
            created_by=r.created_by,
            publish_comment=r.publish_comment,
        )
        for r in rows
    ]
    return HeroRevisionListResponse(items=items, total=total)


@cms_router.get("/hero-design/revisions/{revision_id}", response_model=HeroDesignedPackResponse)
async def get_revision(
    revision_id: str,
    _: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    revision = await db.get(HeroDesignRevision, revision_id)
    if revision is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND, error_code=ErrorCode.NOT_FOUND, message="Revision not found"
        )
    pointer = await hero_service.get_published_pointer(db)
    published_at = (
        pointer.published_at
        if pointer and pointer.revision_id == revision_id
        else revision.created_at
    )
    return HeroDesignedPackResponse(
        revision_id=revision.id,
        etag=revision.pack_sha256,
        profile=revision.profile,
        schema_version=revision.schema_version,
        published_at=published_at,
        pack=revision.pack_json,
        published_by=revision.created_by,
        pack_sha256=revision.pack_sha256,
    )


@cms_router.get("/hero-design/draft", response_model=HeroDraftReadResponse)
async def get_draft(
    _: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    draft = await hero_service.get_draft_row(db)
    if draft is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND, error_code=ErrorCode.NOT_FOUND, message="No draft"
        )
    return HeroDraftReadResponse(
        base_revision_id=draft.base_revision_id,
        draft_json=draft.draft_json,
        lock_version=draft.lock_version,
        updated_at=draft.updated_at,
    )


@cms_router.put("/hero-design/draft")
async def put_draft_deferred():
    raise api_error(
        status.HTTP_501_NOT_IMPLEMENTED,
        error_code=ErrorCode.BAD_REQUEST,
        message="Draft PUT deferred to PR2",
    )


@cms_router.post("/hero-design/validate", response_model=HeroValidateResponse)
async def validate_pack(
    body: HeroValidateRequest,
    _: User = Depends(get_current_super_admin),
):
    errors = hero_service.validate_pack(body.pack_json)
    return HeroValidateResponse(valid=not errors, errors=errors)


@cms_router.post("/hero-design/publish", response_model=HeroPublishResult)
async def publish_hero(
    body: HeroPublishRequest,
    x_step_up_token: str | None = Header(None, alias="X-Step-Up-Token"),
    actor: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    step_up_payload = await verify_and_consume_step_up(db, x_step_up_token)
    if step_up_payload.get("sub") != actor.phone_number:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.STEP_UP_MISMATCH,
            message="Step-up token does not match the authenticated user",
        )
    pointer = await hero_service.publish_from_server_draft(
        db,
        actor=actor,
        expected_parent_revision_id=body.expected_parent_revision_id,
        publish_comment=body.publish_comment,
    )
    await db.commit()
    return HeroPublishResult(
        revision_id=pointer.revision_id,
        etag=pointer.etag,
        published_at=pointer.published_at,
    )


@cms_router.post("/hero-design/rollback", response_model=HeroPublishResult)
async def rollback_hero(
    body: HeroRollbackRequest,
    x_step_up_token: str | None = Header(None, alias="X-Step-Up-Token"),
    actor: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    step_up_payload = await verify_and_consume_step_up(db, x_step_up_token)
    if step_up_payload.get("sub") != actor.phone_number:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.STEP_UP_MISMATCH,
            message="Step-up token does not match the authenticated user",
        )
    pointer = await hero_service.rollback_to_revision(
        db,
        actor=actor,
        revision_id=body.revision_id,
        expected_current_revision_id=body.expected_current_revision_id,
    )
    await db.commit()
    return HeroPublishResult(
        revision_id=pointer.revision_id,
        etag=pointer.etag,
        published_at=pointer.published_at,
    )
