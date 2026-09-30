"""Contract tests for public GET /products/?on_sale=… discount facet."""

from __future__ import annotations

import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _create_product(headers, valid_product_data, **overrides):
    payload = {**valid_product_data, **overrides}
    resp = client.post("/api/v1/products/", json=payload, headers=headers)
    assert resp.status_code in (200, 201), resp.text
    body = resp.json()
    return body["id"] if "id" in body else body["data"]["id"]


def _skus(resp) -> set[str]:
    return {row["sku"] for row in resp.json()["data"]}


@pytest.mark.usefixtures("override_database")
class TestOnSaleFacet:
    def test_discounted_included(
        self, valid_product_data, super_admin_headers
    ):
        _create_product(
            super_admin_headers,
            valid_product_data,
            sku="SALE-A",
            name="Discounted A",
            base_price="900.00",
            original_price="1000.00",
        )
        resp = client.get("/api/v1/products/?on_sale=true")
        assert resp.status_code == 200, resp.text
        assert "SALE-A" in _skus(resp)
        row = next(r for r in resp.json()["data"] if r["sku"] == "SALE-A")
        assert row["discount_percent"] == 10
        assert float(row["original_price"]) > float(row["base_price"])

    def test_no_original_excluded(
        self, valid_product_data, super_admin_headers
    ):
        _create_product(
            super_admin_headers,
            valid_product_data,
            sku="SALE-NO-ORIG",
            base_price="900.00",
            original_price=None,
        )
        resp = client.get("/api/v1/products/?on_sale=true")
        assert resp.status_code == 200
        assert "SALE-NO-ORIG" not in _skus(resp)

    def test_original_equals_base_excluded(
        self, valid_product_data, super_admin_headers
    ):
        _create_product(
            super_admin_headers,
            valid_product_data,
            sku="SALE-EQ",
            base_price="1000.00",
            original_price="1000.00",
        )
        resp = client.get("/api/v1/products/?on_sale=true")
        assert resp.status_code == 200
        assert "SALE-EQ" not in _skus(resp)

    def test_original_below_base_excluded(
        self, valid_product_data, super_admin_headers
    ):
        _create_product(
            super_admin_headers,
            valid_product_data,
            sku="SALE-LT",
            base_price="1000.00",
            original_price="900.00",
        )
        resp = client.get("/api/v1/products/?on_sale=true")
        assert resp.status_code == 200
        assert "SALE-LT" not in _skus(resp)

    def test_unavailable_included_unless_in_stock(
        self, valid_product_data, super_admin_headers
    ):
        _create_product(
            super_admin_headers,
            valid_product_data,
            sku="SALE-UNAVAIL",
            base_price="900.00",
            original_price="1000.00",
            is_available=False,
            is_active=True,
        )
        all_sale = client.get("/api/v1/products/?on_sale=true")
        assert all_sale.status_code == 200
        assert "SALE-UNAVAIL" in _skus(all_sale)

        in_stock_sale = client.get("/api/v1/products/?on_sale=true&in_stock=true")
        assert in_stock_sale.status_code == 200
        assert "SALE-UNAVAIL" not in _skus(in_stock_sale)

    def test_brand_intersection(
        self, valid_product_data, super_admin_headers
    ):
        brand = client.post(
            "/api/v1/brands/",
            json={"name": "Sale Brand X", "country": "ژاپن"},
            headers=super_admin_headers,
        )
        assert brand.status_code in (200, 201), brand.text
        brand_id = brand.json().get("id") or brand.json()["data"]["id"]
        _create_product(
            super_admin_headers,
            valid_product_data,
            sku="SALE-BRAND-HIT",
            brand_id=brand_id,
            base_price="800.00",
            original_price="1000.00",
        )
        _create_product(
            super_admin_headers,
            valid_product_data,
            sku="SALE-BRAND-MISS",
            base_price="800.00",
            original_price="1000.00",
        )
        resp = client.get(
            f"/api/v1/products/?on_sale=true&brand_id={brand_id}"
        )
        assert resp.status_code == 200
        skus = _skus(resp)
        assert "SALE-BRAND-HIT" in skus
        assert "SALE-BRAND-MISS" not in skus

    def test_category_intersection(
        self, valid_product_data, super_admin_headers
    ):
        # Seed tree leaf category_id=3 is selectable; create sale SKU there and
        # prove category_id filter intersects with on_sale.
        cat_id = valid_product_data["category_id"]
        _create_product(
            super_admin_headers,
            valid_product_data,
            sku="SALE-CAT-HIT",
            category_id=cat_id,
            base_price="700.00",
            original_price="1000.00",
        )
        brand = client.post(
            "/api/v1/brands/",
            json={"name": "Sale Cat Other Brand", "country": "آلمان"},
            headers=super_admin_headers,
        )
        assert brand.status_code in (200, 201), brand.text
        other_brand = brand.json().get("id") or brand.json()["data"]["id"]
        _create_product(
            super_admin_headers,
            valid_product_data,
            sku="SALE-CAT-OTHER-BRAND",
            category_id=cat_id,
            brand_id=other_brand,
            base_price="700.00",
            original_price="1000.00",
        )
        by_cat = client.get(f"/api/v1/products/?on_sale=true&category_id={cat_id}")
        assert by_cat.status_code == 200
        skus = _skus(by_cat)
        assert "SALE-CAT-HIT" in skus
        assert "SALE-CAT-OTHER-BRAND" in skus

        by_cat_brand = client.get(
            f"/api/v1/products/?on_sale=true&category_id={cat_id}&brand_id={other_brand}"
        )
        assert by_cat_brand.status_code == 200
        skus2 = _skus(by_cat_brand)
        assert "SALE-CAT-OTHER-BRAND" in skus2
        assert "SALE-CAT-HIT" not in skus2

    def test_pagination_total_and_page2(
        self, valid_product_data, super_admin_headers
    ):
        created_skus = []
        for i in range(5):
            sku = f"SALE-PAGE-{i}"
            created_skus.append(sku)
            _create_product(
                super_admin_headers,
                valid_product_data,
                sku=sku,
                name=f"Sale page {i}",
                base_price=f"{800 - i * 10}.00",
                original_price="1000.00",
            )
        # Admin list bypasses storefront image-visibility gates so pagination
        # asserts the on_sale SQL facet itself (public visibility covered elsewhere).
        page1 = client.get(
            "/api/v1/products/?on_sale=true&search=Sale%20page&limit=2&skip=0",
            headers=super_admin_headers,
        )
        assert page1.status_code == 200
        body1 = page1.json()
        assert body1["meta"]["total_count"] == 5
        assert len(body1["data"]) == 2
        assert body1["meta"]["has_next"] is True

        page2 = client.get(
            "/api/v1/products/?on_sale=true&search=Sale%20page&limit=2&skip=2",
            headers=super_admin_headers,
        )
        assert page2.status_code == 200
        body2 = page2.json()
        assert body2["meta"]["total_count"] == 5
        assert len(body2["data"]) == 2
        ids1 = {r["id"] for r in body1["data"]}
        ids2 = {r["id"] for r in body2["data"]}
        assert ids1.isdisjoint(ids2)
        page3 = client.get(
            "/api/v1/products/?on_sale=true&search=Sale%20page&limit=2&skip=4",
            headers=super_admin_headers,
        )
        assert page3.status_code == 200
        assert len(page3.json()["data"]) == 1
        assert {r["sku"] for r in body1["data"] + body2["data"] + page3.json()["data"]} == set(
            created_skus
        )

    def test_discount_desc_default_and_order(
        self, valid_product_data, super_admin_headers
    ):
        _create_product(
            super_admin_headers,
            valid_product_data,
            sku="SALE-DEEP",
            base_price="500.00",
            original_price="1000.00",  # 50%
        )
        _create_product(
            super_admin_headers,
            valid_product_data,
            sku="SALE-SHALLOW",
            base_price="900.00",
            original_price="1000.00",  # 10%
        )
        # Default sort when on_sale=true with no sort → discount_desc
        resp = client.get("/api/v1/products/?on_sale=true&limit=50")
        assert resp.status_code == 200
        rows = [r for r in resp.json()["data"] if r["sku"] in {"SALE-DEEP", "SALE-SHALLOW"}]
        assert len(rows) == 2
        assert rows[0]["sku"] == "SALE-DEEP"
        assert rows[1]["sku"] == "SALE-SHALLOW"

        explicit = client.get(
            "/api/v1/products/?on_sale=true&sort=discount_desc&limit=50"
        )
        assert explicit.status_code == 200
        rows2 = [
            r
            for r in explicit.json()["data"]
            if r["sku"] in {"SALE-DEEP", "SALE-SHALLOW"}
        ]
        assert rows2[0]["sku"] == "SALE-DEEP"

    def test_inactive_excluded_from_public(
        self, valid_product_data, super_admin_headers
    ):
        _create_product(
            super_admin_headers,
            valid_product_data,
            sku="SALE-INACTIVE",
            base_price="900.00",
            original_price="1000.00",
            is_active=False,
        )
        public = client.get("/api/v1/products/?on_sale=true")
        assert public.status_code == 200
        assert "SALE-INACTIVE" not in _skus(public)

    def test_discount_desc_sort_accepted(self):
        resp = client.get("/api/v1/products/?sort=discount_desc")
        assert resp.status_code == 200, resp.text

    def test_stock_first_sort_accepted(self):
        resp = client.get("/api/v1/products/?sort=stock_first")
        assert resp.status_code == 200, resp.text
