"""Minimal Product Type stewardship (PT-W3A).

Create starts as draft. Activation requires one active Product Type Definition.
No seeds, no automatic assignment, no retirement required for the pilot.
"""

from __future__ import annotations

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, api_error
from app.crud import product_type_definition as ptd_crud
from app.db.models.product_type import ProductType, ProductTypeStatus
from app.db.models.user import User
from app.services.audit_service import record_audit


def _require_change_reason(change_reason: str) -> str:
    reason = (change_reason or "").strip()
    if not reason:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="change_reason is required",
            details=[{"field": "change_reason", "message": "required"}],
        )
    return reason


def _normalize_required_text(value: str, *, field: str, max_len: int) -> str:
    text = (value or "").strip()
    if not text:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message=f"{field} is required",
            details=[{"field": field, "message": "required"}],
        )
    if len(text) > max_len:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message=f"{field} exceeds max length {max_len}",
            details=[{"field": field, "message": f"max_length={max_len}"}],
        )
    return text


async def get_product_type(db: AsyncSession, product_type_id: int) -> ProductType:
    pt = await db.get(ProductType, product_type_id)
    if pt is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Product Type not found",
            details=[{"field": "product_type_id", "message": "not found"}],
        )
    return pt


async def list_product_types(db: AsyncSession) -> list[ProductType]:
    stmt = select(ProductType).order_by(ProductType.id.asc())
    return list((await db.execute(stmt)).scalars().all())


async def create_product_type(
    db: AsyncSession,
    *,
    code: str,
    slug: str,
    name_fa: str,
    name_en: str | None,
    description: str | None,
    actor: User,
) -> ProductType:
    """Create always starts as draft. No active/retired create path."""
    normalized_code = _normalize_required_text(code, field="code", max_len=64)
    normalized_slug = _normalize_required_text(slug, field="slug", max_len=200)
    normalized_name_fa = _normalize_required_text(name_fa, field="name_fa", max_len=255)
    name_en_norm = name_en.strip() if isinstance(name_en, str) and name_en.strip() else None
    if name_en_norm is not None and len(name_en_norm) > 255:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="name_en exceeds max length 255",
            details=[{"field": "name_en", "message": "max_length=255"}],
        )
    description_norm = (
        description.strip() if isinstance(description, str) and description.strip() else None
    )

    pt = ProductType(
        code=normalized_code,
        slug=normalized_slug,
        name_fa=normalized_name_fa,
        name_en=name_en_norm,
        description=description_norm,
        status=ProductTypeStatus.DRAFT.value,
    )
    db.add(pt)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Product Type code or slug already exists",
            details=[
                {"field": "code", "message": normalized_code},
                {"field": "slug", "message": normalized_slug},
            ],
        ) from exc

    await record_audit(
        db,
        actor_user_id=actor.id,
        action="product_type.create",
        entity_type="product_type",
        entity_id=pt.id,
        details={
            "code": pt.code,
            "slug": pt.slug,
            "status": pt.status,
        },
    )
    await db.refresh(pt)
    return pt


async def update_draft_product_type(
    db: AsyncSession,
    *,
    product_type_id: int,
    patch: dict,
    actor: User,
) -> ProductType:
    """Only draft Product Types may edit presentation metadata. code/status immutable here."""
    pt = await get_product_type(db, product_type_id)
    if pt.status != ProductTypeStatus.DRAFT.value:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Only draft Product Types may edit presentation metadata",
            details=[{"field": "status", "message": f"current status is '{pt.status}'"}],
        )

    if "code" in patch:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Product Type code is immutable after creation",
            details=[{"field": "code", "message": "immutable"}],
        )
    if "status" in patch:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Product Type status cannot be mutated via generic update; use activate",
            details=[{"field": "status", "message": "use activate endpoint"}],
        )

    allowed = {"slug", "name_fa", "name_en", "description"}
    unknown = set(patch) - allowed
    if unknown:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Unsupported Product Type draft fields",
            details=[{"field": sorted(unknown)[0], "message": "not editable"}],
        )

    if "slug" in patch:
        pt.slug = _normalize_required_text(patch["slug"], field="slug", max_len=200)
    if "name_fa" in patch:
        pt.name_fa = _normalize_required_text(
            patch["name_fa"], field="name_fa", max_len=255
        )
    if "name_en" in patch:
        value = patch["name_en"]
        if value is None:
            pt.name_en = None
        else:
            text = str(value).strip()
            pt.name_en = text or None
            if pt.name_en is not None and len(pt.name_en) > 255:
                raise api_error(
                    status.HTTP_422_UNPROCESSABLE_CONTENT,
                    error_code=ErrorCode.VALIDATION_FAILED,
                    message="name_en exceeds max length 255",
                    details=[{"field": "name_en", "message": "max_length=255"}],
                )
    if "description" in patch:
        value = patch["description"]
        if value is None:
            pt.description = None
        else:
            text = str(value).strip()
            pt.description = text or None

    try:
        await db.flush()
    except IntegrityError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Product Type slug already exists",
            details=[{"field": "slug", "message": pt.slug}],
        ) from exc

    await record_audit(
        db,
        actor_user_id=actor.id,
        action="product_type.update_draft",
        entity_type="product_type",
        entity_id=pt.id,
        details={"fields": sorted(patch.keys())},
    )
    await db.refresh(pt)
    return pt


async def activate_product_type(
    db: AsyncSession,
    *,
    product_type_id: int,
    change_reason: str,
    actor: User,
) -> ProductType:
    """Activate draft Product Type when exactly one active Definition exists."""
    reason = _require_change_reason(change_reason)
    pt = await get_product_type(db, product_type_id)

    if pt.status != ProductTypeStatus.DRAFT.value:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="Only a draft Product Type may be activated",
            details=[{"field": "status", "message": f"current status is '{pt.status}'"}],
        )

    active_definition = await ptd_crud.get_active_definition_for_product_type(
        db, product_type_id
    )
    if active_definition is None:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message=(
                "Product Type activation requires exactly one active "
                "Product Type Definition"
            ),
            details=[
                {
                    "field": "product_type_id",
                    "message": "no active Product Type Definition",
                }
            ],
        )

    pt.status = ProductTypeStatus.ACTIVE.value
    await db.flush()

    await record_audit(
        db,
        actor_user_id=actor.id,
        action="product_type.activate",
        entity_type="product_type",
        entity_id=pt.id,
        details={
            "change_reason": reason,
            "active_definition_id": active_definition.id,
            "code": pt.code,
        },
    )
    await db.refresh(pt)
    return pt
