"""Admin-only user management endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin, get_current_super_admin_with_step_up
from app.core.errors import ErrorCode, api_error
from app.db.database import get_db
from app.db.models.user import User, UserRole
from app.schemas.user_admin import AdminUserResponse, AdminUserUpdateRequest

router = APIRouter()


@router.get("", response_model=list[AdminUserResponse], summary="List users (admin)")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
):
    users = (await db.execute(select(User).order_by(User.id.asc()))).scalars().all()
    return [
        AdminUserResponse(
            id=user.id,
            phone_number=user.phone_number,
            full_name=user.full_name,
            role=user.role.value if hasattr(user.role, "value") else str(user.role),
            is_active=user.is_active,
        )
        for user in users
    ]


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
