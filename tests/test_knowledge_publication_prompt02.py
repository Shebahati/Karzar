"""Prompt 02: publication lifecycle, rejected freeze, scoped reconciliation."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from app.db.models.knowledge import KnowledgeEdge
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.conftest import TestingSessionLocal

pytestmark = pytest.mark.usefixtures("override_database")

client = TestClient(app)


def _run(coro):
    return asyncio.run(coro)


def _create_product(super_admin_headers, valid_product_data, sku: str = "P02-SKU", **overrides):
    payload = {**valid_product_data, "sku": sku, "name": f"Product {sku}", **overrides}
    response = client.post(
        "/api/v1/products/",
        json=payload,
        headers=super_admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_article(
    super_admin_headers,
    product_ids: list[int],
    *,
    slug: str = "p02-guide",
    is_published: bool = True,
    published_at: datetime | None = None,
):
    response = client.post(
        "/api/v1/cms/articles",
        json={
            "slug": slug,
            "title": "Publication lifecycle guide",
            "excerpt": "Guide excerpt",
            "published_at": (published_at or datetime.now(UTC)).isoformat(),
            "related_product_ids": product_ids,
            "blocks": [],
            "tags": ["metrology"],
            "is_published": is_published,
        },
        headers=super_admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _sync(super_admin_headers, *, product_ids=None, article_ids=None):
    body: dict = {}
    if product_ids is not None:
        body["product_ids"] = product_ids
    if article_ids is not None:
        body["article_ids"] = article_ids
    response = client.post(
        "/api/v1/knowledge/projections/sync",
        json=body,
        headers=super_admin_headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _list_edges(super_admin_headers, **params):
    response = client.get(
        "/api/v1/knowledge/edges",
        params=params,
        headers=super_admin_headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["items"]


async def _set_edge_status(
    *,
    edge_type: str,
    from_type: str,
    from_id: int,
    to_type: str,
    to_id: int,
    status: str,
) -> None:
    async with TestingSessionLocal() as session:
        edge = (
            await session.execute(
                select(KnowledgeEdge).where(
                    KnowledgeEdge.edge_type == edge_type,
                    KnowledgeEdge.from_node_type == from_type,
                    KnowledgeEdge.from_node_id == from_id,
                    KnowledgeEdge.to_node_type == to_type,
                    KnowledgeEdge.to_node_id == to_id,
                )
            )
        ).scalar_one()
        edge.status = status
        await session.commit()


async def _edge_status(
    *,
    edge_type: str,
    from_type: str,
    from_id: int,
    to_type: str,
    to_id: int,
) -> str | None:
    async with TestingSessionLocal() as session:
        edge = (
            await session.execute(
                select(KnowledgeEdge).where(
                    KnowledgeEdge.edge_type == edge_type,
                    KnowledgeEdge.from_node_type == from_type,
                    KnowledgeEdge.from_node_id == from_id,
                    KnowledgeEdge.to_node_type == to_type,
                    KnowledgeEdge.to_node_id == to_id,
                )
            )
        ).scalar_one_or_none()
        return None if edge is None else edge.status


def test_prompt01_security_not_regressed():
    assert client.get("/api/v1/knowledge/edges").status_code == 401
    assert client.get("/api/v1/knowledge/products/1/neighborhood").status_code == 401


def test_review_route_absent():
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert not any("/knowledge/edges/" in p and p.endswith("/review") for p in paths)
    response = client.post("/api/v1/knowledge/edges/1/review", json={"action": "publish"})
    assert response.status_code in (404, 405)


def test_category_brand_public_and_demotion(super_admin_headers, valid_product_data):
    product = _create_product(super_admin_headers, valid_product_data, sku="P02-PUB")
    _sync(super_admin_headers, product_ids=[product["id"]], article_ids=[])

    edges = _list_edges(super_admin_headers, from_type="product", from_id=product["id"])
    by_type = {e["edge_type"]: e for e in edges}
    assert by_type["PRODUCT_BELONGS_TO_CATEGORY"]["status"] == "published"
    assert by_type["PRODUCT_BRANDED_AS"]["status"] == "published"

    patch = client.put(
        f"/api/v1/products/{product['id']}",
        json={"is_active": False},
        headers=super_admin_headers,
    )
    assert patch.status_code == 200, patch.text
    _sync(super_admin_headers, product_ids=[product["id"]], article_ids=[])

    edges = _list_edges(
        super_admin_headers,
        from_type="product",
        from_id=product["id"],
        status="asserted",
    )
    statuses = {e["edge_type"]: e["status"] for e in edges}
    assert statuses["PRODUCT_BELONGS_TO_CATEGORY"] == "asserted"
    assert statuses["PRODUCT_BRANDED_AS"] == "asserted"
    assert (
        _list_edges(
            super_admin_headers,
            from_type="product",
            from_id=product["id"],
            status="deprecated",
        )
        == []
    )

    patch = client.put(
        f"/api/v1/products/{product['id']}",
        json={"is_active": True},
        headers=super_admin_headers,
    )
    assert patch.status_code == 200
    _sync(super_admin_headers, product_ids=[product["id"]], article_ids=[])
    edges = _list_edges(super_admin_headers, from_type="product", from_id=product["id"])
    by_type = {e["edge_type"]: e for e in edges if e["status"] == "published"}
    assert "PRODUCT_BELONGS_TO_CATEGORY" in by_type
    assert "PRODUCT_BRANDED_AS" in by_type


def test_brand_cleared_deprecates_prior(super_admin_headers, valid_product_data):
    product = _create_product(super_admin_headers, valid_product_data, sku="P02-NOBR")
    _sync(super_admin_headers, product_ids=[product["id"]], article_ids=[])
    brand_id = product["brand_id"]

    patch = client.put(
        f"/api/v1/products/{product['id']}",
        json={"brand_id": None},
        headers=super_admin_headers,
    )
    assert patch.status_code == 200, patch.text
    _sync(super_admin_headers, product_ids=[product["id"]], article_ids=[])

    assert (
        _run(
            _edge_status(
                edge_type="PRODUCT_BRANDED_AS",
                from_type="product",
                from_id=product["id"],
                to_type="brand",
                to_id=brand_id,
            )
        )
        == "deprecated"
    )


def test_rejected_freeze_category_and_article(super_admin_headers, valid_product_data):
    product = _create_product(super_admin_headers, valid_product_data, sku="P02-REJ")
    article = _create_article(super_admin_headers, [product["id"]], slug="p02-rej-art")
    _sync(
        super_admin_headers,
        product_ids=[product["id"]],
        article_ids=[article["id"]],
    )

    _run(
        _set_edge_status(
            edge_type="PRODUCT_BELONGS_TO_CATEGORY",
            from_type="product",
            from_id=product["id"],
            to_type="category",
            to_id=product["category_id"],
            status="rejected",
        )
    )
    _run(
        _set_edge_status(
            edge_type="ARTICLE_EXPLAINS_PRODUCT",
            from_type="article",
            from_id=article["id"],
            to_type="product",
            to_id=product["id"],
            status="rejected",
        )
    )

    _sync(
        super_admin_headers,
        product_ids=[product["id"]],
        article_ids=[article["id"]],
    )

    assert (
        _run(
            _edge_status(
                edge_type="PRODUCT_BELONGS_TO_CATEGORY",
                from_type="product",
                from_id=product["id"],
                to_type="category",
                to_id=product["category_id"],
            )
        )
        == "rejected"
    )
    assert (
        _run(
            _edge_status(
                edge_type="ARTICLE_EXPLAINS_PRODUCT",
                from_type="article",
                from_id=article["id"],
                to_type="product",
                to_id=product["id"],
            )
        )
        == "rejected"
    )


def test_article_never_auto_publishes_and_preserves_valid_published(
    super_admin_headers, valid_product_data
):
    product = _create_product(super_admin_headers, valid_product_data, sku="P02-ART")
    article = _create_article(super_admin_headers, [product["id"]], slug="p02-art-new")
    _sync(
        super_admin_headers,
        product_ids=[product["id"]],
        article_ids=[article["id"]],
    )
    assert (
        _run(
            _edge_status(
                edge_type="ARTICLE_EXPLAINS_PRODUCT",
                from_type="article",
                from_id=article["id"],
                to_type="product",
                to_id=product["id"],
            )
        )
        == "asserted"
    )

    _run(
        _set_edge_status(
            edge_type="ARTICLE_EXPLAINS_PRODUCT",
            from_type="article",
            from_id=article["id"],
            to_type="product",
            to_id=product["id"],
            status="published",
        )
    )
    _sync(
        super_admin_headers,
        product_ids=[product["id"]],
        article_ids=[article["id"]],
    )
    assert (
        _run(
            _edge_status(
                edge_type="ARTICLE_EXPLAINS_PRODUCT",
                from_type="article",
                from_id=article["id"],
                to_type="product",
                to_id=product["id"],
            )
        )
        == "published"
    )


def test_article_demotions_and_deprecation(super_admin_headers, valid_product_data):
    p1 = _create_product(super_admin_headers, valid_product_data, sku="P02-D1")
    p2 = _create_product(super_admin_headers, valid_product_data, sku="P02-D2")
    article = _create_article(
        super_admin_headers, [p1["id"], p2["id"]], slug="p02-demote"
    )
    _sync(
        super_admin_headers,
        product_ids=[p1["id"], p2["id"]],
        article_ids=[article["id"]],
    )
    for pid in (p1["id"], p2["id"]):
        _run(
            _set_edge_status(
                edge_type="ARTICLE_EXPLAINS_PRODUCT",
                from_type="article",
                from_id=article["id"],
                to_type="product",
                to_id=pid,
                status="published",
            )
        )

    upd = client.put(
        f"/api/v1/cms/articles/{article['id']}",
        json={"is_published": False},
        headers=super_admin_headers,
    )
    assert upd.status_code == 200, upd.text
    _sync(super_admin_headers, article_ids=[article["id"]], product_ids=[])
    assert (
        _run(
            _edge_status(
                edge_type="ARTICLE_EXPLAINS_PRODUCT",
                from_type="article",
                from_id=article["id"],
                to_type="product",
                to_id=p1["id"],
            )
        )
        == "asserted"
    )

    upd = client.put(
        f"/api/v1/cms/articles/{article['id']}",
        json={
            "is_published": True,
            "published_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        },
        headers=super_admin_headers,
    )
    assert upd.status_code == 200, upd.text
    _run(
        _set_edge_status(
            edge_type="ARTICLE_EXPLAINS_PRODUCT",
            from_type="article",
            from_id=article["id"],
            to_type="product",
            to_id=p1["id"],
            status="published",
        )
    )
    _sync(super_admin_headers, article_ids=[article["id"]], product_ids=[])
    assert (
        _run(
            _edge_status(
                edge_type="ARTICLE_EXPLAINS_PRODUCT",
                from_type="article",
                from_id=article["id"],
                to_type="product",
                to_id=p1["id"],
            )
        )
        == "asserted"
    )

    upd = client.put(
        f"/api/v1/cms/articles/{article['id']}",
        json={
            "is_published": True,
            "published_at": datetime.now(UTC).isoformat(),
            "related_product_ids": [p1["id"], p2["id"]],
        },
        headers=super_admin_headers,
    )
    assert upd.status_code == 200
    _run(
        _set_edge_status(
            edge_type="ARTICLE_EXPLAINS_PRODUCT",
            from_type="article",
            from_id=article["id"],
            to_type="product",
            to_id=p1["id"],
            status="published",
        )
    )
    client.put(
        f"/api/v1/products/{p1['id']}",
        json={"is_active": False},
        headers=super_admin_headers,
    )
    _sync(
        super_admin_headers,
        product_ids=[p1["id"]],
        article_ids=[article["id"]],
    )
    assert (
        _run(
            _edge_status(
                edge_type="ARTICLE_EXPLAINS_PRODUCT",
                from_type="article",
                from_id=article["id"],
                to_type="product",
                to_id=p1["id"],
            )
        )
        == "asserted"
    )

    client.put(
        f"/api/v1/products/{p1['id']}",
        json={"is_active": True},
        headers=super_admin_headers,
    )
    upd = client.put(
        f"/api/v1/cms/articles/{article['id']}",
        json={"related_product_ids": [p2["id"]]},
        headers=super_admin_headers,
    )
    assert upd.status_code == 200
    _sync(super_admin_headers, article_ids=[article["id"]], product_ids=[])
    assert (
        _run(
            _edge_status(
                edge_type="ARTICLE_EXPLAINS_PRODUCT",
                from_type="article",
                from_id=article["id"],
                to_type="product",
                to_id=p1["id"],
            )
        )
        == "deprecated"
    )


def test_article_deprecated_revival_asserted_not_published(
    super_admin_headers, valid_product_data
):
    product = _create_product(super_admin_headers, valid_product_data, sku="P02-REV")
    article = _create_article(super_admin_headers, [product["id"]], slug="p02-rev")
    _sync(
        super_admin_headers,
        product_ids=[product["id"]],
        article_ids=[article["id"]],
    )
    _run(
        _set_edge_status(
            edge_type="ARTICLE_EXPLAINS_PRODUCT",
            from_type="article",
            from_id=article["id"],
            to_type="product",
            to_id=product["id"],
            status="deprecated",
        )
    )
    _sync(super_admin_headers, article_ids=[article["id"]], product_ids=[])
    assert (
        _run(
            _edge_status(
                edge_type="ARTICLE_EXPLAINS_PRODUCT",
                from_type="article",
                from_id=article["id"],
                to_type="product",
                to_id=product["id"],
            )
        )
        == "asserted"
    )


def test_article_missing_target_no_active_orphan(
    super_admin_headers, valid_product_data
):
    product = _create_product(super_admin_headers, valid_product_data, sku="P02-MISS")
    article = _create_article(
        super_admin_headers,
        [product["id"], 999_999_001],
        slug="p02-miss-tgt",
    )
    _sync(
        super_admin_headers,
        product_ids=[product["id"]],
        article_ids=[article["id"]],
    )
    for status in ("asserted", "published"):
        items = _list_edges(
            super_admin_headers,
            edge_type="ARTICLE_EXPLAINS_PRODUCT",
            from_type="article",
            from_id=article["id"],
            status=status,
        )
        assert all(e["to_node_id"] != 999_999_001 for e in items)


def test_scoped_missing_article_and_product_sources(
    super_admin_headers, valid_product_data
):
    product = _create_product(super_admin_headers, valid_product_data, sku="P02-SRC")
    article = _create_article(super_admin_headers, [product["id"]], slug="p02-src-art")
    _sync(
        super_admin_headers,
        product_ids=[product["id"]],
        article_ids=[article["id"]],
    )

    async def _delete_article():
        async with TestingSessionLocal() as session:
            from app.db.models.content import Article

            row = await session.get(Article, article["id"])
            assert row is not None
            await session.delete(row)
            await session.commit()

    _run(_delete_article())
    _sync(super_admin_headers, article_ids=[article["id"]], product_ids=[])
    assert (
        _run(
            _edge_status(
                edge_type="ARTICLE_EXPLAINS_PRODUCT",
                from_type="article",
                from_id=article["id"],
                to_type="product",
                to_id=product["id"],
            )
        )
        == "deprecated"
    )

    p2 = _create_product(super_admin_headers, valid_product_data, sku="P02-SRC2")
    _sync(super_admin_headers, product_ids=[p2["id"]], article_ids=[])
    pid = p2["id"]
    cat_id = p2["category_id"]

    async def _delete_p2():
        async with TestingSessionLocal() as session:
            from app.db.models.product import Product

            row = await session.get(Product, pid)
            assert row is not None
            await session.delete(row)
            await session.commit()

    _run(_delete_p2())
    _sync(super_admin_headers, product_ids=[pid], article_ids=[])
    assert (
        _run(
            _edge_status(
                edge_type="PRODUCT_BELONGS_TO_CATEGORY",
                from_type="product",
                from_id=pid,
                to_type="category",
                to_id=cat_id,
            )
        )
        == "deprecated"
    )


def test_projection_idempotent_no_status_flipflop(
    super_admin_headers, valid_product_data
):
    product = _create_product(super_admin_headers, valid_product_data, sku="P02-IDEM")
    article = _create_article(super_admin_headers, [product["id"]], slug="p02-idem")
    payload = {"product_ids": [product["id"]], "article_ids": [article["id"]]}
    _sync(super_admin_headers, **payload)

    def snapshot():
        return {
            "cat": _run(
                _edge_status(
                    edge_type="PRODUCT_BELONGS_TO_CATEGORY",
                    from_type="product",
                    from_id=product["id"],
                    to_type="category",
                    to_id=product["category_id"],
                )
            ),
            "brand": _run(
                _edge_status(
                    edge_type="PRODUCT_BRANDED_AS",
                    from_type="product",
                    from_id=product["id"],
                    to_type="brand",
                    to_id=product["brand_id"],
                )
            ),
            "art": _run(
                _edge_status(
                    edge_type="ARTICLE_EXPLAINS_PRODUCT",
                    from_type="article",
                    from_id=article["id"],
                    to_type="product",
                    to_id=product["id"],
                )
            ),
        }

    first = snapshot()
    _sync(super_admin_headers, **payload)
    assert snapshot() == first
    assert first["cat"] == "published"
    assert first["art"] == "asserted"


def test_malformed_related_product_ids_do_not_crash(
    super_admin_headers, valid_product_data
):
    product = _create_product(super_admin_headers, valid_product_data, sku="P02-BAD")
    article = _create_article(super_admin_headers, [product["id"]], slug="p02-bad")

    async def _poison():
        async with TestingSessionLocal() as session:
            from app.db.models.content import Article

            row = await session.get(Article, article["id"])
            assert row is not None
            row.related_product_ids = [product["id"], "not-an-id", None, True, product["id"]]
            await session.commit()

    _run(_poison())
    stats = _sync(super_admin_headers, article_ids=[article["id"]], product_ids=[])
    assert stats["articles_scanned"] == 1
    edges = _list_edges(
        super_admin_headers,
        edge_type="ARTICLE_EXPLAINS_PRODUCT",
        from_type="article",
        from_id=article["id"],
    )
    assert len(edges) == 1
    assert edges[0]["to_node_id"] == product["id"]


def test_admin_can_filter_rejected_status(super_admin_headers, valid_product_data):
    product = _create_product(super_admin_headers, valid_product_data, sku="P02-ADM")
    _sync(super_admin_headers, product_ids=[product["id"]], article_ids=[])
    _run(
        _set_edge_status(
            edge_type="PRODUCT_BELONGS_TO_CATEGORY",
            from_type="product",
            from_id=product["id"],
            to_type="category",
            to_id=product["category_id"],
            status="rejected",
        )
    )
    items = _list_edges(
        super_admin_headers,
        from_type="product",
        from_id=product["id"],
        status="rejected",
    )
    assert len(items) == 1
    assert items[0]["status"] == "rejected"


def test_shared_eligibility_matches_pdp_predicate():
    from app.db.models.product import Product
    from app.utils.public_catalog import is_product_storefront_public

    active = Product(is_active=True, deleted_at=None, images=[])
    assert is_product_storefront_public(active) is True

    inactive = Product(is_active=False, deleted_at=None, images=[])
    assert is_product_storefront_public(inactive) is False

    deleted = Product(is_active=True, deleted_at=datetime.now(UTC), images=[])
    assert is_product_storefront_public(deleted) is False
