"""CRUD helpers for Product Type Definitions + Attribute Memberships (PT-W2)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.product_type import (
    ProductTypeAttributeMembership,
    ProductTypeDefinition,
    ProductTypeDefinitionStatus,
)


async def get_definition(
    db: AsyncSession,
    definition_id: int,
    *,
    with_memberships: bool = False,
    for_update: bool = False,
) -> ProductTypeDefinition | None:
    stmt = select(ProductTypeDefinition).where(ProductTypeDefinition.id == definition_id)
    if with_memberships:
        stmt = stmt.options(selectinload(ProductTypeDefinition.memberships))
    if for_update:
        stmt = stmt.with_for_update()
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_definitions_for_product_type(
    db: AsyncSession,
    product_type_id: int,
) -> list[ProductTypeDefinition]:
    stmt = (
        select(ProductTypeDefinition)
        .where(ProductTypeDefinition.product_type_id == product_type_id)
        .options(selectinload(ProductTypeDefinition.memberships))
        .order_by(ProductTypeDefinition.version.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def max_version_for_product_type(
    db: AsyncSession,
    product_type_id: int,
) -> int | None:
    return (
        await db.execute(
            select(func.max(ProductTypeDefinition.version)).where(
                ProductTypeDefinition.product_type_id == product_type_id
            )
        )
    ).scalar_one()


async def get_active_definition_for_product_type(
    db: AsyncSession,
    product_type_id: int,
    *,
    for_update: bool = False,
) -> ProductTypeDefinition | None:
    stmt = select(ProductTypeDefinition).where(
        ProductTypeDefinition.product_type_id == product_type_id,
        ProductTypeDefinition.status == ProductTypeDefinitionStatus.ACTIVE.value,
    )
    if for_update:
        stmt = stmt.with_for_update()
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_membership(
    db: AsyncSession,
    membership_id: int,
    *,
    for_update: bool = False,
) -> ProductTypeAttributeMembership | None:
    stmt = select(ProductTypeAttributeMembership).where(
        ProductTypeAttributeMembership.id == membership_id
    )
    if for_update:
        stmt = stmt.with_for_update()
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_memberships(
    db: AsyncSession,
    definition_id: int,
) -> list[ProductTypeAttributeMembership]:
    stmt = (
        select(ProductTypeAttributeMembership)
        .where(
            ProductTypeAttributeMembership.product_type_definition_id == definition_id
        )
        .order_by(
            ProductTypeAttributeMembership.display_order.nulls_last(),
            ProductTypeAttributeMembership.id,
        )
    )
    return list((await db.execute(stmt)).scalars().all())
