"""CRUD helpers for knowledge_edges overlay (KB-001)."""

from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge import KB001_EDGE_TYPES, KnowledgeEdge


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
