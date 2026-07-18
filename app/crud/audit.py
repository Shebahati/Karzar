"""CRUD for admin audit logs and product change logs."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.platform import AdminAuditLog, ProductChangeLog


async def record_audit_log(
    db: AsyncSession,
    *,
    actor_user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> AdminAuditLog:
    row = AdminAuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    db.add(row)
    await db.flush()
    return row


async def list_audit_logs(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> tuple[list[AdminAuditLog], int]:
    filters = []
    if entity_type:
        filters.append(AdminAuditLog.entity_type == entity_type)
    if entity_id:
        filters.append(AdminAuditLog.entity_id == entity_id)

    count_stmt = select(func.count()).select_from(AdminAuditLog)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(AdminAuditLog)
        .order_by(AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc())
        .offset(skip)
        .limit(limit)
    )
    if filters:
        stmt = stmt.where(*filters)
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows), total


async def record_product_change(
    db: AsyncSession,
    *,
    product_id: int,
    field_name: str,
    old_value: str | None,
    new_value: str | None,
    reason: str | None = None,
    actor_user_id: int | None = None,
) -> ProductChangeLog:
    row = ProductChangeLog(
        product_id=product_id,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
        actor_user_id=actor_user_id,
    )
    db.add(row)
    await db.flush()
    return row


async def list_product_change_logs(
    db: AsyncSession,
    product_id: int,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[ProductChangeLog], int]:
    count_stmt = (
        select(func.count())
        .select_from(ProductChangeLog)
        .where(ProductChangeLog.product_id == product_id)
    )
    total = (await db.execute(count_stmt)).scalar_one()
    stmt = (
        select(ProductChangeLog)
        .where(ProductChangeLog.product_id == product_id)
        .order_by(ProductChangeLog.created_at.desc(), ProductChangeLog.id.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows), total
