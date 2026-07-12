"""Immutable admin audit trail for destructive and sensitive operations."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import platform as crud_platform


async def record_audit(
    db: AsyncSession,
    *,
    actor_user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: str | int | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    entity_id_str = str(entity_id) if entity_id is not None else None
    await crud_platform.record_audit_log(
        db,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id_str,
        details=details,
    )
