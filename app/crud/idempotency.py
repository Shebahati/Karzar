"""CRUD for idempotency keys and step-up JTI consumption."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.platform import IdempotencyKey, StepUpTokenUse


async def get_idempotency_record(
    db: AsyncSession,
    *,
    scope: str,
    key: str,
) -> IdempotencyKey | None:
    now = datetime.now(UTC)
    stmt = select(IdempotencyKey).where(
        IdempotencyKey.scope == scope,
        IdempotencyKey.key == key,
        IdempotencyKey.expires_at > now,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def store_idempotency_record(
    db: AsyncSession,
    *,
    scope: str,
    key: str,
    status_code: int,
    response_body: dict[str, Any],
    expires_at: datetime,
) -> IdempotencyKey:
    row = IdempotencyKey(
        scope=scope,
        key=key,
        status_code=status_code,
        response_body=response_body,
        expires_at=expires_at,
    )
    db.add(row)
    await db.flush()
    return row


async def reserve_idempotency_record(
    db: AsyncSession,
    *,
    scope: str,
    key: str,
    expires_at: datetime,
) -> bool:
    try:
        async with db.begin_nested():
            row = IdempotencyKey(
                scope=scope,
                key=key,
                status_code=0,
                response_body={},
                expires_at=expires_at,
            )
            db.add(row)
            await db.flush()
            return True
    except IntegrityError:
        return False


async def finalize_idempotency_record(
    db: AsyncSession,
    *,
    scope: str,
    key: str,
    status_code: int,
    response_body: dict[str, Any],
    expires_at: datetime,
) -> None:
    existing = await get_idempotency_record(db, scope=scope, key=key)
    if existing is None:
        await store_idempotency_record(
            db,
            scope=scope,
            key=key,
            status_code=status_code,
            response_body=response_body,
            expires_at=expires_at,
        )
        return
    existing.status_code = status_code
    existing.response_body = response_body
    existing.expires_at = expires_at
    await db.flush()


async def delete_idempotency_record(
    db: AsyncSession,
    *,
    scope: str,
    key: str,
) -> None:
    existing = await get_idempotency_record(db, scope=scope, key=key)
    if existing is None:
        return
    await db.delete(existing)
    await db.flush()


async def consume_step_up_jti(
    db: AsyncSession,
    *,
    jti: str,
    expires_at: datetime,
) -> bool:
    try:
        async with db.begin_nested():
            row = StepUpTokenUse(jti=jti, expires_at=expires_at)
            db.add(row)
            await db.flush()
            return True
    except IntegrityError:
        return False
