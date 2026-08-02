"""CRUD helpers for knowledge_edges overlay (KB-001) + Property Dictionary (11A)."""

from __future__ import annotations

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge import (
    KB001_EDGE_TYPES,
    KnowledgeEdge,
    KnowledgePropertyAlias,
    KnowledgePropertyDefinition,
    KnowledgeUnit,
)


def _visible_statuses() -> tuple[str, ...]:
    return ("asserted", "published")


async def list_edges(
    db: AsyncSession,
    *,
    edge_type: str | None = None,
    from_node_type: str | None = None,
    from_node_id: int | None = None,
    to_node_type: str | None = None,
    to_node_id: int | None = None,
    status: str | None = None,
    include_inactive: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[KnowledgeEdge], int]:
    if edge_type is not None and edge_type not in KB001_EDGE_TYPES:
        return [], 0

    stmt: Select[tuple[KnowledgeEdge]] = select(KnowledgeEdge)
    count_stmt = select(func.count()).select_from(KnowledgeEdge)

    def apply_filters(q):
        if edge_type is not None:
            q = q.where(KnowledgeEdge.edge_type == edge_type)
        if from_node_type is not None:
            q = q.where(KnowledgeEdge.from_node_type == from_node_type)
        if from_node_id is not None:
            q = q.where(KnowledgeEdge.from_node_id == from_node_id)
        if to_node_type is not None:
            q = q.where(KnowledgeEdge.to_node_type == to_node_type)
        if to_node_id is not None:
            q = q.where(KnowledgeEdge.to_node_id == to_node_id)
        if status is not None:
            q = q.where(KnowledgeEdge.status == status)
        elif not include_inactive:
            q = q.where(KnowledgeEdge.status.in_(_visible_statuses()))
        return q

    stmt = apply_filters(stmt).order_by(KnowledgeEdge.id).offset(skip).limit(limit)
    count_stmt = apply_filters(count_stmt)

    rows = (await db.execute(stmt)).scalars().all()
    total = int((await db.execute(count_stmt)).scalar_one())
    return list(rows), total


async def get_product_neighborhood(
    db: AsyncSession,
    product_id: int,
) -> dict[str, KnowledgeEdge | list[KnowledgeEdge] | None]:
    """Depth-1 neighborhood for a commerce product (ADR-014 join key)."""
    visible = _visible_statuses()

    outbound = (
        await db.execute(
            select(KnowledgeEdge).where(
                KnowledgeEdge.from_node_type == "product",
                KnowledgeEdge.from_node_id == product_id,
                KnowledgeEdge.edge_type.in_(
                    ("PRODUCT_BELONGS_TO_CATEGORY", "PRODUCT_BRANDED_AS")
                ),
                KnowledgeEdge.status.in_(visible),
            )
        )
    ).scalars().all()

    belongs = next(
        (e for e in outbound if e.edge_type == "PRODUCT_BELONGS_TO_CATEGORY"),
        None,
    )
    branded = next(
        (e for e in outbound if e.edge_type == "PRODUCT_BRANDED_AS"),
        None,
    )

    inbound_articles = (
        await db.execute(
            select(KnowledgeEdge).where(
                KnowledgeEdge.edge_type == "ARTICLE_EXPLAINS_PRODUCT",
                KnowledgeEdge.to_node_type == "product",
                KnowledgeEdge.to_node_id == product_id,
                KnowledgeEdge.status.in_(visible),
            ).order_by(KnowledgeEdge.id)
        )
    ).scalars().all()

    return {
        "belongs_to_category": belongs,
        "branded_as": branded,
        "explained_by_articles": list(inbound_articles),
    }


async def get_edge_by_identity(
    db: AsyncSession,
    *,
    edge_type: str,
    from_node_type: str,
    from_node_id: int,
    to_node_type: str,
    to_node_id: int,
) -> KnowledgeEdge | None:
    result = await db.execute(
        select(KnowledgeEdge).where(
            KnowledgeEdge.edge_type == edge_type,
            KnowledgeEdge.from_node_type == from_node_type,
            KnowledgeEdge.from_node_id == from_node_id,
            KnowledgeEdge.to_node_type == to_node_type,
            KnowledgeEdge.to_node_id == to_node_id,
        )
    )
    return result.scalars().first()


async def list_units(
    db: AsyncSession,
    *,
    dimension: str | None = None,
    status: str | None = None,
    q: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[KnowledgeUnit], int]:
    stmt: Select[tuple[KnowledgeUnit]] = select(KnowledgeUnit)
    count_stmt = select(func.count()).select_from(KnowledgeUnit)

    def apply_filters(query):
        if dimension is not None:
            query = query.where(KnowledgeUnit.dimension == dimension)
        if status is not None:
            query = query.where(KnowledgeUnit.status == status)
        if q:
            like = f"%{q}%"
            query = query.where(
                or_(
                    KnowledgeUnit.canonical_code.ilike(like),
                    KnowledgeUnit.label_en.ilike(like),
                    KnowledgeUnit.label_fa.ilike(like),
                )
            )
        return query

    stmt = apply_filters(stmt).order_by(KnowledgeUnit.id).offset(skip).limit(limit)
    count_stmt = apply_filters(count_stmt)
    rows = (await db.execute(stmt)).scalars().all()
    total = int((await db.execute(count_stmt)).scalar_one())
    return list(rows), total


async def get_unit_by_id(db: AsyncSession, unit_id: int) -> KnowledgeUnit | None:
    return (
        await db.execute(select(KnowledgeUnit).where(KnowledgeUnit.id == unit_id))
    ).scalar_one_or_none()


async def list_property_definitions(
    db: AsyncSession,
    *,
    status: str | None = None,
    data_type: str | None = None,
    unit_dimension: str | None = None,
    q: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[KnowledgePropertyDefinition], int]:
    stmt: Select[tuple[KnowledgePropertyDefinition]] = select(
        KnowledgePropertyDefinition
    )
    count_stmt = select(func.count()).select_from(KnowledgePropertyDefinition)

    def apply_filters(query):
        if status is not None:
            query = query.where(KnowledgePropertyDefinition.status == status)
        if data_type is not None:
            query = query.where(KnowledgePropertyDefinition.data_type == data_type)
        if unit_dimension is not None:
            query = query.where(
                KnowledgePropertyDefinition.unit_dimension == unit_dimension
            )
        if q:
            like = f"%{q}%"
            query = query.where(
                or_(
                    KnowledgePropertyDefinition.key.ilike(like),
                    KnowledgePropertyDefinition.definition_id.ilike(like),
                    KnowledgePropertyDefinition.label_en.ilike(like),
                    KnowledgePropertyDefinition.label_fa.ilike(like),
                )
            )
        return query

    stmt = (
        apply_filters(stmt)
        .order_by(KnowledgePropertyDefinition.id)
        .offset(skip)
        .limit(limit)
    )
    count_stmt = apply_filters(count_stmt)
    rows = (await db.execute(stmt)).scalars().all()
    total = int((await db.execute(count_stmt)).scalar_one())
    return list(rows), total


async def get_property_definition_by_id(
    db: AsyncSession, definition_pk: int
) -> KnowledgePropertyDefinition | None:
    return (
        await db.execute(
            select(KnowledgePropertyDefinition).where(
                KnowledgePropertyDefinition.id == definition_pk
            )
        )
    ).scalar_one_or_none()


async def get_property_definition_by_definition_id(
    db: AsyncSession, definition_id: str
) -> KnowledgePropertyDefinition | None:
    return (
        await db.execute(
            select(KnowledgePropertyDefinition).where(
                KnowledgePropertyDefinition.definition_id == definition_id
            )
        )
    ).scalar_one_or_none()


async def list_aliases_for_definition(
    db: AsyncSession, definition_id: str
) -> list[KnowledgePropertyAlias]:
    rows = (
        await db.execute(
            select(KnowledgePropertyAlias)
            .where(KnowledgePropertyAlias.definition_id == definition_id)
            .order_by(KnowledgePropertyAlias.id)
        )
    ).scalars().all()
    return list(rows)


async def list_property_aliases(
    db: AsyncSession,
    *,
    definition_id: str | None = None,
    status: str | None = None,
    q: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[KnowledgePropertyAlias], int]:
    stmt: Select[tuple[KnowledgePropertyAlias]] = select(KnowledgePropertyAlias)
    count_stmt = select(func.count()).select_from(KnowledgePropertyAlias)

    def apply_filters(query):
        if definition_id is not None:
            query = query.where(KnowledgePropertyAlias.definition_id == definition_id)
        if status is not None:
            query = query.where(KnowledgePropertyAlias.status == status)
        if q:
            like = f"%{q}%"
            query = query.where(
                or_(
                    KnowledgePropertyAlias.alias.ilike(like),
                    KnowledgePropertyAlias.alias_normalized.ilike(like),
                )
            )
        return query

    stmt = (
        apply_filters(stmt).order_by(KnowledgePropertyAlias.id).offset(skip).limit(limit)
    )
    count_stmt = apply_filters(count_stmt)
    rows = (await db.execute(stmt)).scalars().all()
    total = int((await db.execute(count_stmt)).scalar_one())
    return list(rows), total
