"""FastAPI dependency injection for authentication and authorization."""


from datetime import UTC, datetime

from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, api_error
from app.core.security import decode_token, verify_step_up_token
from app.crud import platform as crud_platform
from app.db.database import get_db
from app.db.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a valid JWT bearer token."""
    payload = decode_token(token)
    if payload.get("type") not in (None, "access"):
        raise api_error(
            401,
            error_code=ErrorCode.UNAUTHORIZED,
            message="Invalid access token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    phone_number: str | None = payload.get("sub")
    if phone_number is None:
        raise api_error(
            401,
            error_code=ErrorCode.UNAUTHORIZED,
            message="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(
        select(User).where(
            User.phone_number == phone_number,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalars().first()
    if user is None:
        raise api_error(
            401,
            error_code=ErrorCode.UNAUTHORIZED,
            message="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_version = payload.get("ver", 0)
    if user.token_version != token_version:
        raise api_error(
            401,
            error_code=ErrorCode.UNAUTHORIZED,
            message="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Reject deactivated accounts."""
    if not current_user.is_active:
        raise api_error(
            403,
            error_code=ErrorCode.FORBIDDEN,
            message="Inactive user",
        )
    return current_user


async def get_current_super_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Restrict endpoint to users with the super_admin role."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise api_error(
            403,
            error_code=ErrorCode.FORBIDDEN,
            message="The user doesn't have enough privileges",
        )
    return current_user


async def get_verified_step_up(
    x_step_up_token: str | None = Header(None, alias="X-Step-Up-Token"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Validate the step-up JWT supplied in the X-Step-Up-Token header."""
    if not x_step_up_token:
        raise api_error(
            403,
            error_code=ErrorCode.STEP_UP_REQUIRED,
            message="Step-up authentication required for this action",
            details=[{"field": "X-Step-Up-Token", "message": "Missing step-up token"}],
        )
    payload = verify_step_up_token(x_step_up_token)
    expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)
    consumed = await crud_platform.consume_step_up_jti(
        db,
        jti=payload["jti"],
        expires_at=expires_at,
    )
    if not consumed:
        raise api_error(
            403,
            error_code=ErrorCode.STEP_UP_INVALID,
            message="Step-up token has already been used",
        )
    return payload


async def get_current_super_admin_with_step_up(
    current_user: User = Depends(get_current_super_admin),
    step_up_payload: dict = Depends(get_verified_step_up),
) -> User:
    """Require both super_admin role and a step-up token bound to the same user."""
    if step_up_payload.get("sub") != current_user.phone_number:
        raise api_error(
            403,
            error_code=ErrorCode.STEP_UP_MISMATCH,
            message="Step-up token does not match the authenticated user",
        )
    return current_user


async def get_optional_current_user(
    token: str | None = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Resolve an authenticated user when a bearer token is supplied."""
    if not token:
        return None

    payload = decode_token(token)
    if payload.get("type") not in (None, "access"):
        return None

    phone_number: str | None = payload.get("sub")
    if phone_number is None:
        return None

    result = await db.execute(
        select(User).where(
            User.phone_number == phone_number,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalars().first()
    if user is None or not user.is_active:
        return None

    token_version = payload.get("ver", 0)
    if user.token_version != token_version:
        return None
    return user


def is_super_admin(user: User | None) -> bool:
    return user is not None and user.role == UserRole.SUPER_ADMIN
