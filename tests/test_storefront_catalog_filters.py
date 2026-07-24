"""Unit/integration tests for storefront catalog filter helpers and contracts."""

from app.main import app
from app.utils.storefront_catalog import (
    escape_ilike_pattern,
    parse_in_stock_filter,
    parse_int_id_list,
    parse_string_list,
    product_sort_clause,
)
from fastapi.testclient import TestClient

client = TestClient(app)


def _brand_id(resp) -> int:
    body = resp.json()
    return body["id"] if "id" in body else body["data"]["id"]


class TestParseInStockFilter:
    def test_true_values(self):
        for value in ("1", "true", "TRUE", "yes"):
            assert parse_in_stock_filter(value) is True

    def test_false_values(self):
        for value in ("0", "false", "FALSE", "no"):
            assert parse_in_stock_filter(value) is False

    def test_none_and_blank(self):
        assert parse_in_stock_filter(None) is None
        assert parse_in_stock_filter("") is None
        assert parse_in_stock_filter("  ") is None

    def test_invalid_raises(self):
        try:
            parse_in_stock_filter("maybe")
            raise AssertionError("expected ValueError")
        except ValueError as exc:
            assert "in_stock" in str(exc)


class TestParseIntIdList:
    def test_none_and_empty(self):
        assert parse_int_id_list(None) is None
        assert parse_int_id_list([]) is None
        assert parse_int_id_list([""]) is None

    def test_single_int_and_string(self):
        assert parse_int_id_list(3) == [3]
        assert parse_int_id_list("7") == [7]

    def test_repeated_and_comma(self):
        assert parse_int_id_list(["1", "2", "1"]) == [1, 2]
        assert parse_int_id_list(["1,2", "3"]) == [1, 2, 3]
        assert parse_int_id_list("4,5,4") == [4, 5]

    def test_invalid_raises(self):
        try:
            parse_int_id_list(["abc"])
            raise AssertionError("expected ValueError")
        except ValueError as exc:
            assert "invalid integer" in str(exc)


class TestParseStringList:
    def test_none_and_empty(self):
        assert parse_string_list(None) is None
        assert parse_string_list([]) is None
        assert parse_string_list([""]) is None

    def test_single_and_multi(self):
        assert parse_string_list("ژاپن") == ["ژاپن"]
        assert parse_string_list(["آلمان", "ژاپن", "آلمان"]) == ["آلمان", "ژاپن"]
        assert parse_string_list("آلمان,ژاپن") == ["آلمان", "ژاپن"]


class TestEscapeIlike:
    def test_escapes_wildcards_and_backslash(self):
        assert escape_ilike_pattern("a%b_c\\d") == r"a\%b\_c\\d"


class TestNameSortPortable:
    def test_name_sort_returns_plain_name_order(self):
        asc_clause = product_sort_clause("name_asc")
        desc_clause = product_sort_clause("name_desc")
        assert "fa_IR" not in str(asc_clause[0])
        assert "fa_IR" not in str(desc_clause[0])


class TestCatalogFilterContract:
    def test_invalid_in_stock_returns_422(self):
        response = client.get("/api/v1/products/?in_stock=maybe")
        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "VALIDATION_FAILED"

    def test_negative_min_price_rejected(self):
        response = client.get("/api/v1/products/?min_price=-1")
        assert response.status_code == 422

    def test_invalid_brand_id_returns_422(self):
        response = client.get("/api/v1/products/?brand_id=not-a-number")
        assert response.status_code == 422
        assert response.json()["error_code"] == "VALIDATION_FAILED"

    def test_name_sort_does_not_500(self, valid_product_data, super_admin_headers):
        client.post(
            "/api/v1/products/",
            json={**valid_product_data, "sku": "SORT-NAME-1", "name": "آچار"},
            headers=super_admin_headers,
        )
        for sort in ("name_asc", "name_desc"):
            response = client.get(f"/api/v1/products/?sort={sort}")
            assert response.status_code == 200, response.text

    def test_in_stock_false_filters_out_of_stock(
        self, valid_product_data, super_admin_headers
    ):
        client.post(
            "/api/v1/products/",
            json={
                **valid_product_data,
                "sku": "STOCK-OUT-1",
                "stock_quantity": "0",
                "name": "ناموجود تست",
            },
            headers=super_admin_headers,
        )
        client.post(
            "/api/v1/products/",
            json={
                **valid_product_data,
                "sku": "STOCK-IN-1",
                "stock_quantity": "5",
                "name": "موجود تست",
            },
            headers=super_admin_headers,
        )
        out = client.get("/api/v1/products/?in_stock=false")
        assert out.status_code == 200
        skus = {row["sku"] for row in out.json()["data"]}
        assert "STOCK-OUT-1" in skus
        assert "STOCK-IN-1" not in skus

    def test_search_treats_percent_as_literal(
        self, valid_product_data, super_admin_headers
    ):
        client.post(
            "/api/v1/products/",
            json={**valid_product_data, "sku": "PCT-1", "name": "آچار 10% کروم"},
            headers=super_admin_headers,
        )
        response = client.get("/api/v1/products/?search=%25")
        assert response.status_code == 200
        names = [row["name"] for row in response.json()["data"]]
        assert any("%" in name for name in names)

    def test_multi_brand_id_repeated_and_comma(
        self, valid_product_data, super_admin_headers
    ):
        brand_a = client.post(
            "/api/v1/brands/",
            json={"name": "Brand Multi A", "country": "آلمان"},
            headers=super_admin_headers,
        )
        brand_b = client.post(
            "/api/v1/brands/",
            json={"name": "Brand Multi B", "country": "ژاپن"},
            headers=super_admin_headers,
        )
        assert brand_a.status_code in (200, 201), brand_a.text
        assert brand_b.status_code in (200, 201), brand_b.text
        id_a = _brand_id(brand_a)
        id_b = _brand_id(brand_b)

        client.post(
            "/api/v1/products/",
            json={
                **valid_product_data,
                "sku": "MULTI-BRAND-A",
                "name": "محصول برند آ",
                "brand_id": id_a,
            },
            headers=super_admin_headers,
        )
        client.post(
            "/api/v1/products/",
            json={
                **valid_product_data,
                "sku": "MULTI-BRAND-B",
                "name": "محصول برند ب",
                "brand_id": id_b,
            },
            headers=super_admin_headers,
        )
        client.post(
            "/api/v1/products/",
            json={
                **valid_product_data,
                "sku": "MULTI-BRAND-OTHER",
                "name": "محصول دیگر",
            },
            headers=super_admin_headers,
        )

        repeated = client.get(f"/api/v1/products/?brand_id={id_a}&brand_id={id_b}")
        assert repeated.status_code == 200, repeated.text
        skus_repeated = {row["sku"] for row in repeated.json()["data"]}
        assert "MULTI-BRAND-A" in skus_repeated
        assert "MULTI-BRAND-B" in skus_repeated

        comma = client.get(f"/api/v1/products/?brand_id={id_a},{id_b}")
        assert comma.status_code == 200, comma.text
        skus_comma = {row["sku"] for row in comma.json()["data"]}
        assert "MULTI-BRAND-A" in skus_comma
        assert "MULTI-BRAND-B" in skus_comma

        single = client.get(f"/api/v1/products/?brand_id={id_a}")
        assert single.status_code == 200
        skus_single = {row["sku"] for row in single.json()["data"]}
        assert "MULTI-BRAND-A" in skus_single
        assert "MULTI-BRAND-B" not in skus_single

    def test_multi_country_filter(self, valid_product_data, super_admin_headers):
        brand_de = client.post(
            "/api/v1/brands/",
            json={"name": "Country Filter DE", "country": "آلمان"},
            headers=super_admin_headers,
        )
        brand_jp = client.post(
            "/api/v1/brands/",
            json={"name": "Country Filter JP", "country": "ژاپن"},
            headers=super_admin_headers,
        )
        brand_ir = client.post(
            "/api/v1/brands/",
            json={"name": "Country Filter IR", "country": "ایران"},
            headers=super_admin_headers,
        )
        assert brand_de.status_code in (200, 201), brand_de.text
        assert brand_jp.status_code in (200, 201), brand_jp.text
        assert brand_ir.status_code in (200, 201), brand_ir.text

        id_de, id_jp, id_ir = _brand_id(brand_de), _brand_id(brand_jp), _brand_id(brand_ir)

        client.post(
            "/api/v1/products/",
            json={
                **valid_product_data,
                "sku": "COUNTRY-DE-1",
                "brand_id": id_de,
                "name": "آلمانی",
            },
            headers=super_admin_headers,
        )
        client.post(
            "/api/v1/products/",
            json={
                **valid_product_data,
                "sku": "COUNTRY-JP-1",
                "brand_id": id_jp,
                "name": "ژاپنی",
            },
            headers=super_admin_headers,
        )
        client.post(
            "/api/v1/products/",
            json={
                **valid_product_data,
                "sku": "COUNTRY-IR-1",
                "brand_id": id_ir,
                "name": "ایرانی",
            },
            headers=super_admin_headers,
        )

        response = client.get(
            "/api/v1/products/",
            params=[("country", "آلمان"), ("country", "ژاپن")],
        )
        assert response.status_code == 200, response.text
        skus = {row["sku"] for row in response.json()["data"]}
        assert "COUNTRY-DE-1" in skus
        assert "COUNTRY-JP-1" in skus
        assert "COUNTRY-IR-1" not in skus
