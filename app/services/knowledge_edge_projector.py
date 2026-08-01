"""Project commerce soft-links into typed knowledge_edges (KB-001 freeze).

Sources (Accepted SPEC-knowledge-graph-model § migration map):
- products.category_id → PRODUCT_BELONGS_TO_CATEGORY
- products.brand_id → PRODUCT_BRANDED_AS
- articles.related_product_ids → ARTICLE_EXPLAINS_PRODUCT (asserted)

ADR-012: Category A local sync only — this service never chooses a remote API base.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import knowledge as knowledge_crud
from app.db.models.content import Article
from app.db.models.knowledge import KnowledgeEdge
from app.db.models.product import Product

RECORDER = "kb001-projector"
SOURCE_KIND = "projection"


def _now() -> datetime:
    return datetime.now(UTC)


def _commerce_status(product: Product) -> str:
    """Publish with commerce when the SKU is active and not soft-deleted."""
    if product.is_active and product.deleted_at is None:
        return "published"
    return "asserted"


async def _upsert_edge(
    db: AsyncSession,
    *,
    edge_type: str,
    from_node_type: str,
    from_node_id: int,
    to_node_type: str,
    to_node_id: int,
    status: str,
    source_ref: str,
) -> tuple[KnowledgeEdge, bool]:
    """Return (edge, created_or_updated). Always refreshes status/provenance."""
    existing = await knowledge_crud.get_edge_by_identity(
        db,
        edge_type=edge_type,
        from_node_type=from_node_type,
        from_node_id=from_node_id,
        to_node_type=to_node_type,
        to_node_id=to_node_id,
    )
    recorded_at = _now()
    if existing is None:
        edge = KnowledgeEdge(
            edge_type=edge_type,
            from_node_type=from_node_type,
            from_node_id=from_node_id,
            to_node_type=to_node_type,
            to_node_id=to_node_id,
            status=status,
            source_kind=SOURCE_KIND,
            source_ref=source_ref,
            recorded_at=recorded_at,
            recorder=RECORDER,
            attributes={},
        )
        db.add(edge)
        await db.flush()
        return edge, True

    existing.status = status
    existing.source_kind = SOURCE_KIND
    existing.source_ref = source_ref
    existing.recorded_at = recorded_at
    existing.recorder = RECORDER
    await db.flush()
    return existing, True


async def _deprecate_stale(
    db: AsyncSession,
    *,
    edge_type: str,
    from_node_type: str,
    from_node_id: int,
    keep_to: set[tuple[str, int]],
) -> int:
    rows = (
        await db.execute(
            select(KnowledgeEdge).where(
                KnowledgeEdge.edge_type == edge_type,
                KnowledgeEdge.from_node_type == from_node_type,
                KnowledgeEdge.from_node_id == from_node_id,
                KnowledgeEdge.status.in_(("asserted", "published")),
            )
        )
    ).scalars().all()
    deprecated = 0
    for edge in rows:
        key = (edge.to_node_type, edge.to_node_id)
        if key not in keep_to:
            edge.status = "deprecated"
            edge.recorded_at = _now()
            edge.recorder = RECORDER
            deprecated += 1
    if deprecated:
        await db.flush()
    return deprecated


async def project_product(db: AsyncSession, product: Product) -> tuple[int, int]:
    upserted = 0
    deprecated = 0
    status = _commerce_status(product)
    keep: set[tuple[str, int]] = set()

    if product.category_id is not None:
        _, changed = await _upsert_edge(
            db,
            edge_type="PRODUCT_BELONGS_TO_CATEGORY",
            from_node_type="product",
            from_node_id=product.id,
            to_node_type="category",
            to_node_id=product.category_id,
            status=status,
            source_ref="products.category_id",
        )
        upserted += int(changed)
        keep.add(("category", product.category_id))
    deprecated += await _deprecate_stale(
        db,
        edge_type="PRODUCT_BELONGS_TO_CATEGORY",
        from_node_type="product",
        from_node_id=product.id,
        keep_to=keep,
    )

    brand_keep: set[tuple[str, int]] = set()
    if product.brand_id is not None:
        _, changed = await _upsert_edge(
            db,
            edge_type="PRODUCT_BRANDED_AS",
            from_node_type="product",
            from_node_id=product.id,
            to_node_type="brand",
            to_node_id=product.brand_id,
            status=status,
            source_ref="products.brand_id",
        )
        upserted += int(changed)
        brand_keep.add(("brand", product.brand_id))
    deprecated += await _deprecate_stale(
        db,
        edge_type="PRODUCT_BRANDED_AS",
        from_node_type="product",
        from_node_id=product.id,
        keep_to=brand_keep,
    )
    return upserted, deprecated


async def project_article(db: AsyncSession, article: Article) -> tuple[int, int]:
    upserted = 0
    related = article.related_product_ids or []
    # Coerce JSON numbers that may arrive as ints
    product_ids = [int(pid) for pid in related if pid is not None]
    keep: set[tuple[str, int]] = set()
    for pid in product_ids:
        _, changed = await _upsert_edge(
            db,
            edge_type="ARTICLE_EXPLAINS_PRODUCT",
            from_node_type="article",
            from_node_id=article.id,
            to_node_type="product",
            to_node_id=pid,
            status="asserted",
            source_ref="articles.related_product_ids",
        )
        upserted += int(changed)
        keep.add(("product", pid))
    deprecated = await _deprecate_stale(
        db,
        edge_type="ARTICLE_EXPLAINS_PRODUCT",
        from_node_type="article",
        from_node_id=article.id,
        keep_to=keep,
    )
    return upserted, deprecated


async def sync_projections(
    db: AsyncSession,
    *,
    product_ids: list[int] | None = None,
    article_ids: list[int] | None = None,
) -> dict[str, int]:
    product_q = select(Product)
    if product_ids is not None:
        product_q = product_q.where(Product.id.in_(product_ids))
    products = (await db.execute(product_q)).scalars().all()

    article_q = select(Article)
    if article_ids is not None:
        article_q = article_q.where(Article.id.in_(article_ids))
    articles = (await db.execute(article_q)).scalars().all()

    upserted = 0
    deprecated = 0
    for product in products:
        u, d = await project_product(db, product)
        upserted += u
        deprecated += d
    for article in articles:
        u, d = await project_article(db, article)
        upserted += u
        deprecated += d

    return {
        "products_scanned": len(products),
        "articles_scanned": len(articles),
        "edges_upserted": upserted,
        "edges_deprecated": deprecated,
    }
