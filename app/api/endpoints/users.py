"""Admin-only user management endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin, get_current_super_admin_with_step_up
from app.core.errors import ErrorCode, api_error
from app.db.database import get_db
from app.db.models.commerce import Order
from app.db.models.user import User, UserRole
from app.schemas.common import build_pagination_meta, resolve_pagination
from app.schemas.user_admin import AdminUserListResponse, AdminUserResponse, AdminUserUpdateRequest
from app.services.audit_service import record_audit

router = APIRouter()

_VALID_USER_SORTS = frozenset(
    {"id_desc", "id_asc", "phone_asc", "name_asc", "created_at_desc", "created_at_asc"}
)


async def _order_counts_by_user(db: AsyncSession, user_ids: list[int]) -> dict[int, int]:
    if not user_ids:
        return {}
    stmt = (
        select(Order.user_id, func.count(Order.id))
        .where(Order.user_id.in_(user_ids), Order.deleted_at.is_(None))
        .group_by(Order.user_id)
    )
    rows = await db.execute(stmt)
    return {int(user_id): int(count) for user_id, count in rows.all() if user_id is not None}


def _to_admin_user(user: User, order_count: int = 0) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        phone_number=user.phone_number,
        full_name=user.full_name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        is_active=user.is_active,
        email=user.email,
        order_count=order_count,
        created_at=user.created_at,
        note=user.note,
        category=user.category,
        tags=list(user.tags or []),
    )


@router.get("", response_model=AdminUserListResponse, summary="List users (admin)")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    search: str | None = Query(None),
    sort: str = Query("id_desc"),
):
    if sort not in _VALID_USER_SORTS:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Invalid sort key",
            details=[{"field": "sort", "message": f"must be one of: {', '.join(sorted(_VALID_USER_SORTS))}"}],
        )

    resolved_skip, resolved_limit = resolve_pagination(
        page=page, page_size=page_size, skip=skip, limit=limit
    )

    filters = [User.deleted_at.is_(None)]
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(or_(User.phone_number.ilike(pattern), User.full_name.ilike(pattern)))

    count_stmt = select(func.count()).select_from(User).where(*filters)
    total = (await db.execute(count_stmt)).scalar_one()

    order_by = [User.id.desc()]
    if sort == "id_asc":
        order_by = [User.id.asc()]
    elif sort == "phone_asc":
        order_by = [User.phone_number.asc(), User.id.asc()]
    elif sort == "name_asc":
        order_by = [User.full_name.asc().nulls_last(), User.id.asc()]
    elif sort == "created_at_desc":
        order_by = [User.created_at.desc(), User.id.desc()]
    elif sort == "created_at_asc":
        order_by = [User.created_at.asc(), User.id.asc()]

    stmt = select(User).where(*filters).order_by(*order_by).offset(resolved_skip).limit(resolved_limit)
    users = (await db.execute(stmt)).scalars().all()
    counts = await _order_counts_by_user(db, [user.id for user in users])

    return {
        "data": [_to_admin_user(user, counts.get(user.id, 0)) for user in users],
        "meta": build_pagination_meta(total_count=total, skip=resolved_skip, limit=resolved_limit),
    }


@router.get("/audit-logs/list", summary="List admin audit logs")
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
):
    from app.crud import platform as crud_platform

    rows, total = await crud_platform.list_audit_logs(
        db,
        skip=skip,
        limit=limit,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    return {
        "data": [
            {
                "id": row.id,
                "actor_user_id": row.actor_user_id,
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "details": row.details,
                "created_at": row.created_at,
            }
            for row in rows
        ],
        "meta": build_pagination_meta(total_count=total, skip=skip, limit=limit),
    }


@router.get("/{user_id}", response_model=AdminUserResponse, summary="Get user by id (admin)")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    user = (
        await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    ).scalars().first()
    if not user:
        raise api_error(status.HTTP_404_NOT_FOUND, error_code=ErrorCode.NOT_FOUND, message="User not found")
    counts = await _order_counts_by_user(db, [user.id])
    return _to_admin_user(user, counts.get(user.id, 0))


@router.patch("/{user_id}", response_model=AdminUserResponse, summary="Update user (admin)")
async def update_user(
    user_id: int,
    payload: AdminUserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_super_admin_with_step_up),
):
    user = (
        await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    ).scalars().first()
    if not user:
        raise api_error(status.HTTP_404_NOT_FOUND, error_code=ErrorCode.NOT_FOUND, message="User not found")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.email is not None:
        user.email = payload.email
    if payload.note is not None:
        user.note = payload.note
    if payload.category is not None:
        user.category = payload.category
    if payload.tags is not None:
        user.tags = payload.tags
    if payload.role is not None:
        old_role = user.role.value if hasattr(user.role, "value") else str(user.role)
        if old_role != payload.role:
            if payload.role == UserRole.SUPER_ADMIN.value:
                raise api_error(
                    status.HTTP_403_FORBIDDEN,
                    error_code=ErrorCode.FORBIDDEN,
                    message="Cannot promote users to super_admin via API",
                    details=[{"field": "role", "message": "super_admin promotion is blocked"}],
                )
            try:
                user.role = UserRole(payload.role)
            except ValueError as exc:
                raise api_error(
                    status.HTTP_422_UNPROCESSABLE_CONTENT,
                    error_code=ErrorCode.VALIDATION_FAILED,
                    message="Invalid role",
                    details=[{"field": "role", "message": "unknown role"}],
                ) from exc
            await record_audit(
                db,
                actor_user_id=admin_user.id,
                action="role_change",
                entity_type="user",
                entity_id=user.id,
                details={"from": old_role, "to": payload.role},
            )

    await db.commit()
    await db.refresh(user)
    counts = await _order_counts_by_user(db, [user.id])
    return _to_admin_user(user, counts.get(user.id, 0))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Soft delete user (admin)")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_super_admin_with_step_up),
):
    user = (
        await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    ).scalars().first()
    if not user:
        raise api_error(status.HTTP_404_NOT_FOUND, error_code=ErrorCode.NOT_FOUND, message="User not found")
    if user.role == UserRole.SUPER_ADMIN:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.BAD_REQUEST,
            message="Super admin accounts cannot be deleted",
        )

    user.deleted_at = datetime.now(UTC)
    user.is_active = False
    user.token_version += 1
    await record_audit(
        db,
        actor_user_id=admin_user.id,
        action="soft_delete",
        entity_type="user",
        entity_id=user.id,
    )
    await db.commit()
