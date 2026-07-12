"""Refresh token issuance, rotation, and revocation."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, hash_token
from app.crud import platform as crud_platform
from app.db.models.user import User


def _refresh_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


async def issue_auth_tokens(db: AsyncSession, user: User) -> dict[str, str | int]:
    access_token = create_access_token(
        subject=user.phone_number,
        token_version=user.token_version,
    )
    refresh_plain = create_refresh_token()
    await crud_platform.store_refresh_token(
        db,
        user_id=user.id,
        token_hash=hash_token(refresh_plain),
        expires_at=_refresh_expires_at(),
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_plain,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def rotate_refresh_token(
    db: AsyncSession,
    user: User,
    refresh_plain: str,
) -> dict[str, str | int]:
    row = await crud_platform.get_valid_refresh_token(db, hash_token(refresh_plain))
    if row is None or row.user_id != user.id:
        raise ValueError("Invalid or expired refresh token")

    await crud_platform.revoke_refresh_token(db, row)
    return await issue_auth_tokens(db, user)


async def logout_user(db: AsyncSession, user: User) -> None:
    user.token_version += 1
    await crud_platform.revoke_all_refresh_tokens_for_user(db, user.id)
    await db.flush()
