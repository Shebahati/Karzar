"""Admin-only user management endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin, get_current_super_admin_with_step_up
from app.core.errors import ErrorCode, api_error
from app.db.database import get_db
from app.db.models.user import User, UserRole
from app.schemas.common import build_pagination_meta, resolve_pagination
from app.schemas.user_admin import AdminUserListResponse, AdminUserResponse, AdminUserUpdateRequest

router = APIRouter()

_VALID_USER_SORTS = frozenset({"id_desc", "id_asc", "phone_asc", "name_asc"})


@router.get("", response_model=AdminUserListResponse, summary="List users (admin)")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    page: Optional[int] = Query(None, ge=1, description="1-based page number (alternative to skip)"),
    page_size: Optional[int] = Query(None, ge=1, le=200, description="Page size (alternative to limit)"),
    search: Optional[str] = Query(None, description="Search by phone number or full name"),
    sort: str = Query("id_desc", description="Sort key: id_desc, id_asc, phone_asc, name_asc"),
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

    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(or_(User.phone_number.ilike(pattern), User.full_name.ilike(pattern)))

    count_stmt = select(func.count()).select_from(User)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = (await db.execute(count_stmt)).scalar_one()

    order_by = [User.id.desc()]
    if sort == "id_asc":
        order_by = [User.id.asc()]
    elif sort == "phone_asc":
        order_by = [User.phone_number.asc(), User.id.asc()]
    elif sort == "name_asc":
        order_by = [User.full_name.asc().nulls_last(), User.id.asc()]

    stmt = select(User).order_by(*order_by).offset(resolved_skip).limit(resolved_limit)
    if filters:
        stmt = stmt.where(*filters)
    users = (await db.execute(stmt)).scalars().all()

    return {
        "data": [
            AdminUserResponse(
                id=user.id,
                phone_number=user.phone_number,
                full_name=user.full_name,
                role=user.role.value if hasattr(user.role, "value") else str(user.role),
                is_active=user.is_active,
            )
            for user in users
        ],
        "meta": build_pagination_meta(total_count=total, skip=resolved_skip, limit=resolved_limit),
    }


@router.patch("/{user_id}", response_model=AdminUserResponse, summary="Update user (admin)")
async def update_user(
    user_id: int,
    payload: AdminUserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin_with_step_up),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalars().first()
    if not user:
        raise api_error(status.HTTP_404_NOT_FOUND, error_code=ErrorCode.NOT_FOUND, message="User not found")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.role is not None:
        try:
            user.role = UserRole(payload.role)
        except ValueError as exc:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="Invalid role",
                details=[{"field": "role", "message": "unknown role"}],
            ) from exc

    await db.commit()
    await db.refresh(user)
    return AdminUserResponse(
        id=user.id,
        phone_number=user.phone_number,
        full_name=user.full_name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        is_active=user.is_active,
    )
