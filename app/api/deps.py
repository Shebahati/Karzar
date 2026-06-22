# app/api/deps.py
from typing import Optional

from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, api_error
from app.core.security import decode_token, verify_step_up_token
from app.db.database import get_db
from app.db.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(token)
    if payload.get("type") not in (None, "access"):
        raise api_error(
            401,
            error_code=ErrorCode.UNAUTHORIZED,
            message="Invalid access token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    phone_number: Optional[str] = payload.get("sub")
    if phone_number is None:
        raise api_error(
            401,
            error_code=ErrorCode.UNAUTHORIZED,
            message="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.phone_number == phone_number))
    user = result.scalars().first()
    if user is None:
        raise api_error(
            401,
            error_code=ErrorCode.UNAUTHORIZED,
            message="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise api_error(
            403,
            error_code=ErrorCode.FORBIDDEN,
            message="Inactive user",
        )
    return current_user


async def get_current_super_admin(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role != UserRole.SUPER_ADMIN:
        raise api_error(
            403,
            error_code=ErrorCode.FORBIDDEN,
            message="The user doesn't have enough privileges",
        )
    return current_user


async def get_verified_step_up(
    x_step_up_token: Optional[str] = Header(None, alias="X-Step-Up-Token"),
) -> dict:
    if not x_step_up_token:
        raise api_error(
            403,
            error_code=ErrorCode.STEP_UP_REQUIRED,
            message="Step-up authentication required for this action",
            details=[{"field": "X-Step-Up-Token", "message": "Missing step-up token"}],
        )
    return verify_step_up_token(x_step_up_token)


async def get_current_super_admin_with_step_up(
    current_user: User = Depends(get_current_super_admin),
    step_up_payload: dict = Depends(get_verified_step_up),
) -> User:
    if step_up_payload.get("sub") != current_user.phone_number:
        raise api_error(
            403,
            error_code=ErrorCode.STEP_UP_MISMATCH,
            message="Step-up token does not match the authenticated user",
        )
    return current_user
