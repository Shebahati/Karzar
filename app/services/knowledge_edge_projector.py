"""Project commerce soft-links into typed knowledge_edges (KB-001 freeze).

Prompt 02: publication lifecycle, rejected freeze, shared PDP eligibility,
scoped reconciliation (demotion/deprecation). No Review API / events / jobs.

Sources (Accepted SPEC-knowledge-graph-model § migration map):
- products.category_id → PRODUCT_BELONGS_TO_CATEGORY
- products.brand_id → PRODUCT_BRANDED_AS
- articles.related_product_ids → ARTICLE_EXPLAINS_PRODUCT

ADR-012: Category A local sync only — this service never chooses a remote API base.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud import knowledge as knowledge_crud
from app.db.models.content import Article
from app.db.models.knowledge import KnowledgeEdge
from app.db.models.product import Brand, Category, Product
from app.utils.public_catalog import is_product_storefront_public

RECORDER = "kb001-projector"
SOURCE_KIND = "projection"
_ACTIVE = ("asserted", "published")


def _now() -> datetime:
    return datetime.now(UTC)


def _commerce_edge_status(product: Product) -> str:
    """Category/brand: published iff product is storefront-public (shared PDP predicate)."""
    if is_product_storefront_public(product):
        return "published"
    return "asserted"


def _parse_related_product_ids(raw: Any) -> list[int]:
    """Dedupe coercible int IDs; skip malformed tokens without raising."""
    if not raw:
        return []
    if not isinstance(raw, list):
        return []
    seen: set[int] = set()
    out: list[int] = []
    for token in raw:
        if token is None or isinstance(token, bool):
            continue
        try:
            pid = int(token)
        except (TypeError, ValueError):
            continue
        if pid in seen:
            continue
        seen.add(pid)
        out.append(pid)
    return out


def _article_public_gates_hold(article: Article, product: Product) -> bool:
    """Gates that allow preserving an already-published ARTICLE_EXPLAINS_PRODUCT edge."""
    if not article.is_published:
        return False
    published_at = article.published_at
    if published_at is not None:
        ts = published_at if published_at.tzinfo is not None else published_at.replace(tzinfo=UTC)
        if ts > _now():
            return False
    return is_product_storefront_public(product)


async def _target_exists(
    db: AsyncSession,
    *,
    node_type: str,
    node_id: int,
) -> bool:
    if node_type == "category":
        row = await db.get(Category, node_id)
        return row is not None
    if node_type == "brand":
        row = await db.get(Brand, node_id)
        return row is not None
    if node_type == "product":
        row = await db.get(Product, node_id)
        return row is not None
    if node_type == "article":
        row = await db.get(Article, node_id)
        return row is not None
    return False


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
) -> tuple[KnowledgeEdge | None, bool]:
    """Upsert with rejected freeze. Returns (edge_or_none, created_or_status_changed)."""
    existing = await knowledge_crud.get_edge_by_identity(
        db,
        edge_type=edge_type,
        from_node_type=from_node_type,
        from_node_id=from_node_id,
        to_node_type=to_node_type,
        to_node_id=to_node_id,
    )
    if existing is not None and existing.status == "rejected":
        # Prompt 02: projector MUST NOT mutate rejected steward decisions.
        return existing, False

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

    if existing.status == status:
        return existing, False

    existing.status = status
    existing.source_kind = SOURCE_KIND
    existing.source_ref = source_ref
    existing.recorded_at = recorded_at
    existing.recorder = RECORDER
    await db.flush()
    return existing, True


async def _set_status_if_active(
    db: AsyncSession,
    edge: KnowledgeEdge,
    *,
    status: str,
) -> bool:
    """Mutate active (non-rejected) edge status. Rejected freeze applies."""
    if edge.status == "rejected":
        return False
    if edge.status == status:
        return False
    edge.status = status
    edge.recorded_at = _now()
    edge.recorder = RECORDER
    edge.source_kind = SOURCE_KIND
    await db.flush()
    return True


async def _deprecate_stale(
    db: AsyncSession,
    *,
    edge_type: str,
    from_node_type: str,
    from_node_id: int,
    keep_to: set[tuple[str, int]],
) -> int:
    """Deprecate active edges whose target is no longer in keep_to. Skip rejected."""
    rows = (
        await db.execute(
            select(KnowledgeEdge).where(
                KnowledgeEdge.edge_type == edge_type,
                KnowledgeEdge.from_node_type == from_node_type,
                KnowledgeEdge.from_node_id == from_node_id,
                KnowledgeEdge.status.in_(_ACTIVE),
            )
        )
    ).scalars().all()
    deprecated = 0
    for edge in rows:
        key = (edge.to_node_type, edge.to_node_id)
        if key not in keep_to:
            if await _set_status_if_active(db, edge, status="deprecated"):
                deprecated += 1
    return deprecated


async def _deprecate_edges_for_missing_product(db: AsyncSession, product_id: int) -> int:
    """Scoped: requested product id missing → deprecate active KB-001 edges involving it."""
    rows = (
        await db.execute(
            select(KnowledgeEdge).where(
                KnowledgeEdge.status.in_(_ACTIVE),
                or_(
                    and_(
                        KnowledgeEdge.from_node_type == "product",
                        KnowledgeEdge.from_node_id == product_id,
                    ),
                    and_(
                        KnowledgeEdge.to_node_type == "product",
                        KnowledgeEdge.to_node_id == product_id,
                    ),
                ),
            )
        )
    ).scalars().all()
    count = 0
    for edge in rows:
        if await _set_status_if_active(db, edge, status="deprecated"):
            count += 1
    return count


async def _deprecate_edges_for_missing_article(db: AsyncSession, article_id: int) -> int:
    """Scoped: requested article id missing → deprecate its ARTICLE_EXPLAINS_PRODUCT edges."""
    rows = (
        await db.execute(
            select(KnowledgeEdge).where(
                KnowledgeEdge.edge_type == "ARTICLE_EXPLAINS_PRODUCT",
                KnowledgeEdge.from_node_type == "article",
                KnowledgeEdge.from_node_id == article_id,
                KnowledgeEdge.status.in_(_ACTIVE),
            )
        )
    ).scalars().all()
    count = 0
    for edge in rows:
        if await _set_status_if_active(db, edge, status="deprecated"):
            count += 1
    return count


async def project_product(db: AsyncSession, product: Product) -> tuple[int, int]:
    upserted = 0
    deprecated = 0
    status = _commerce_edge_status(product)

    keep: set[tuple[str, int]] = set()
    if product.category_id is not None:
        if await _target_exists(db, node_type="category", node_id=product.category_id):
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
        else:
            existing = await knowledge_crud.get_edge_by_identity(
                db,
                edge_type="PRODUCT_BELONGS_TO_CATEGORY",
                from_node_type="product",
                from_node_id=product.id,
                to_node_type="category",
                to_node_id=product.category_id,
            )
            if existing is not None and await _set_status_if_active(
                db, existing, status="deprecated"
            ):
                deprecated += 1
    deprecated += await _deprecate_stale(
        db,
        edge_type="PRODUCT_BELONGS_TO_CATEGORY",
        from_node_type="product",
        from_node_id=product.id,
        keep_to=keep,
    )

    brand_keep: set[tuple[str, int]] = set()
    if product.brand_id is not None:
        if await _target_exists(db, node_type="brand", node_id=product.brand_id):
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
        else:
            existing = await knowledge_crud.get_edge_by_identity(
                db,
                edge_type="PRODUCT_BRANDED_AS",
                from_node_type="product",
                from_node_id=product.id,
                to_node_type="brand",
                to_node_id=product.brand_id,
            )
            if existing is not None and await _set_status_if_active(
                db, existing, status="deprecated"
            ):
                deprecated += 1
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
    deprecated = 0
    product_ids = _parse_related_product_ids(article.related_product_ids)
    keep: set[tuple[str, int]] = set()

    for pid in product_ids:
        product = (
            await db.execute(
                select(Product)
                .where(Product.id == pid)
                .options(selectinload(Product.images))
            )
        ).scalar_one_or_none()

        if product is None:
            existing = await knowledge_crud.get_edge_by_identity(
                db,
                edge_type="ARTICLE_EXPLAINS_PRODUCT",
                from_node_type="article",
                from_node_id=article.id,
                to_node_type="product",
                to_node_id=pid,
            )
            if existing is not None and await _set_status_if_active(
                db, existing, status="deprecated"
            ):
                deprecated += 1
            continue

        existing = await knowledge_crud.get_edge_by_identity(
            db,
            edge_type="ARTICLE_EXPLAINS_PRODUCT",
            from_node_type="article",
            from_node_id=article.id,
            to_node_type="product",
            to_node_id=pid,
        )
        if existing is not None and existing.status == "rejected":
            keep.add(("product", pid))
            continue

        # Never auto-publish. Preserve valid published; else asserted (incl. deprecated revival).
        if (
            existing is not None
            and existing.status == "published"
            and _article_public_gates_hold(article, product)
        ):
            desired = "published"
        else:
            desired = "asserted"

        _, changed = await _upsert_edge(
            db,
            edge_type="ARTICLE_EXPLAINS_PRODUCT",
            from_node_type="article",
            from_node_id=article.id,
            to_node_type="product",
            to_node_id=pid,
            status=desired,
            source_ref="articles.related_product_ids",
        )
        upserted += int(changed)
        keep.add(("product", pid))

    deprecated += await _deprecate_stale(
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
    product_q = select(Product).options(selectinload(Product.images))
    if product_ids is not None:
        product_q = product_q.where(Product.id.in_(product_ids))
    products = list((await db.execute(product_q)).scalars().unique().all())

    article_q = select(Article)
    if article_ids is not None:
        article_q = article_q.where(Article.id.in_(article_ids))
    articles = list((await db.execute(article_q)).scalars().all())

    upserted = 0
    deprecated = 0

    if product_ids is not None:
        found = {p.id for p in products}
        for missing_id in product_ids:
            if missing_id not in found:
                deprecated += await _deprecate_edges_for_missing_product(db, missing_id)

    if article_ids is not None:
        found_articles = {a.id for a in articles}
        for missing_id in article_ids:
            if missing_id not in found_articles:
                deprecated += await _deprecate_edges_for_missing_article(db, missing_id)

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
