"""KB-001 wave-1: project 3 edge types + queryable read path."""

from datetime import UTC, datetime

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _create_product(super_admin_headers, valid_product_data, sku: str = "KB-001"):
    payload = {**valid_product_data, "sku": sku, "name": f"Product {sku}"}
    response = client.post(
        "/api/v1/products/",
        json=payload,
        headers=super_admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_article(super_admin_headers, product_ids: list[int], slug: str = "kb-guide"):
    response = client.post(
        "/api/v1/cms/articles",
        json={
            "slug": slug,
            "title": "How to read a caliper",
            "excerpt": "Guide excerpt",
            "published_at": datetime.now(UTC).isoformat(),
            "related_product_ids": product_ids,
            "blocks": [],
            "tags": ["metrology"],
            "is_published": True,
        },
        headers=super_admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_sync_requires_admin():
    anon = client.post("/api/v1/knowledge/projections/sync", json={})
    assert anon.status_code in (401, 403)


def test_sync_as_admin_projects_edges(super_admin_headers, valid_product_data):
    product = _create_product(super_admin_headers, valid_product_data)
    sync = client.post(
        "/api/v1/knowledge/projections/sync",
        json={"product_ids": [product["id"]]},
        headers=super_admin_headers,
    )
    assert sync.status_code == 200, sync.text
    body = sync.json()
    assert body["products_scanned"] == 1
    assert body["edges_upserted"] >= 1


def test_project_brand_and_category_edges(super_admin_headers, valid_product_data):
    product = _create_product(super_admin_headers, valid_product_data, sku="KB-CAT")
    sync = client.post(
        "/api/v1/knowledge/projections/sync",
        json={"product_ids": [product["id"]], "article_ids": []},
        headers=super_admin_headers,
    )
    assert sync.status_code == 200

    edges = client.get(
        "/api/v1/knowledge/edges",
        params={"from_type": "product", "from_id": product["id"]},
    )
    assert edges.status_code == 200
    items = edges.json()["items"]
    types = {e["edge_type"] for e in items}
    assert "PRODUCT_BELONGS_TO_CATEGORY" in types
    assert "PRODUCT_BRANDED_AS" in types
    cat = next(e for e in items if e["edge_type"] == "PRODUCT_BELONGS_TO_CATEGORY")
    brand = next(e for e in items if e["edge_type"] == "PRODUCT_BRANDED_AS")
    assert cat["to_node_type"] == "category"
    assert cat["to_node_id"] == product["category_id"]
    assert cat["status"] == "published"
    assert cat["source_kind"] == "projection"
    assert brand["to_node_type"] == "brand"
    assert brand["to_node_id"] == product["brand_id"]


def test_project_article_explains_product(super_admin_headers, valid_product_data):
    p1 = _create_product(super_admin_headers, valid_product_data, sku="KB-A1")
    p2 = _create_product(super_admin_headers, valid_product_data, sku="KB-A2")
    article = _create_article(
        super_admin_headers,
        [p1["id"], p2["id"]],
        slug="kb-explains",
    )
    sync = client.post(
        "/api/v1/knowledge/projections/sync",
        json={
            "product_ids": [p1["id"], p2["id"]],
            "article_ids": [article["id"]],
        },
        headers=super_admin_headers,
    )
    assert sync.status_code == 200
    assert sync.json()["articles_scanned"] == 1

    edges = client.get(
        "/api/v1/knowledge/edges",
        params={"edge_type": "ARTICLE_EXPLAINS_PRODUCT", "from_type": "article", "from_id": article["id"]},
    )
    assert edges.status_code == 200
    items = edges.json()["items"]
    assert len(items) == 2
    assert all(e["status"] == "asserted" for e in items)
    assert {e["to_node_id"] for e in items} == {p1["id"], p2["id"]}

    neighborhood = client.get(f"/api/v1/knowledge/products/{p1['id']}/neighborhood")
    assert neighborhood.status_code == 200
    body = neighborhood.json()
    assert body["product_id"] == p1["id"]
    assert body["belongs_to_category"] is not None
    assert body["branded_as"] is not None
    assert len(body["explained_by_articles"]) == 1
    assert body["explained_by_articles"][0]["from_node_id"] == article["id"]


def test_sync_idempotent(super_admin_headers, valid_product_data):
    product = _create_product(super_admin_headers, valid_product_data, sku="KB-IDEM")
    payload = {"product_ids": [product["id"]], "article_ids": []}
    first = client.post(
        "/api/v1/knowledge/projections/sync",
        json=payload,
        headers=super_admin_headers,
    )
    second = client.post(
        "/api/v1/knowledge/projections/sync",
        json=payload,
        headers=super_admin_headers,
    )
    assert first.status_code == 200 and second.status_code == 200
    edges = client.get(
        "/api/v1/knowledge/edges",
        params={"from_type": "product", "from_id": product["id"]},
    )
    # still exactly one of each commerce projection type
    items = edges.json()["items"]
    assert sum(1 for e in items if e["edge_type"] == "PRODUCT_BELONGS_TO_CATEGORY") == 1
    assert sum(1 for e in items if e["edge_type"] == "PRODUCT_BRANDED_AS") == 1


def test_rejects_unknown_edge_type_filter():
    response = client.get(
        "/api/v1/knowledge/edges",
        params={"edge_type": "FREE_STRING_NOT_ALLOWED"},
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "INVALID_EDGE_TYPE"


def test_no_brand_edge_when_brand_null(super_admin_headers, valid_product_data):
    payload = {**valid_product_data, "sku": "KB-NOBRAND", "brand_id": None}
    create = client.post(
        "/api/v1/products/",
        json=payload,
        headers=super_admin_headers,
    )
    assert create.status_code == 201, create.text
    product_id = create.json()["id"]
    sync = client.post(
        "/api/v1/knowledge/projections/sync",
        json={"product_ids": [product_id], "article_ids": []},
        headers=super_admin_headers,
    )
    assert sync.status_code == 200
    edges = client.get(
        "/api/v1/knowledge/edges",
        params={"from_type": "product", "from_id": product_id},
    )
    types = {e["edge_type"] for e in edges.json()["items"]}
    assert "PRODUCT_BELONGS_TO_CATEGORY" in types
    assert "PRODUCT_BRANDED_AS" not in types
