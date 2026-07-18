"""CRUD for refresh tokens."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.platform import RefreshToken


async def store_refresh_token(
    db: AsyncSession,
    *,
    user_id: int,
    token_hash: str,
    expires_at: datetime,
) -> RefreshToken:
    row = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(row)
    await db.flush()
    return row


async def get_valid_refresh_token(db: AsyncSession, token_hash: str) -> RefreshToken | None:
    now = datetime.now(UTC)
    stmt = select(RefreshToken).where(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked_at.is_(None),
        RefreshToken.expires_at > now,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def revoke_refresh_token(db: AsyncSession, row: RefreshToken) -> None:
    row.revoked_at = datetime.now(UTC)
    await db.flush()


async def revoke_all_refresh_tokens_for_user(db: AsyncSession, user_id: int) -> None:
    now = datetime.now(UTC)
    stmt = select(RefreshToken).where(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    )
    rows = (await db.execute(stmt)).scalars().all()
    for row in rows:
        row.revoked_at = now
    await db.flush()
