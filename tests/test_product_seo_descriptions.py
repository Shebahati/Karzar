"""Tests for product SEO description fields and metadata priority helpers."""

from app.main import app
from app.utils.seo_descriptions import (
    is_stub_description,
    render_short_description_template,
    resolve_jsonld_description,
    resolve_meta_description,
    resolve_meta_title,
)
from fastapi.testclient import TestClient

client = TestClient(app)


class TestSeoHelpers:
    def test_meta_title_prefers_override(self):
        assert resolve_meta_title(meta_title="عنوان سئو", name="نام محصول") == "عنوان سئو"
        assert resolve_meta_title(meta_title=None, name="نام محصول") == "نام محصول"

    def test_meta_description_priority(self):
        assert (
            resolve_meta_description(
                meta_description="متای اختصاصی محصول برای موتور جستجو",
                short_description="توضیح کوتاه واقعی درباره کولیس دیجیتال",
                description="بدنه بلند",
                name="کولیس",
            )
            == "متای اختصاصی محصول برای موتور جستجو"
        )
        assert (
            resolve_meta_description(
                meta_description=None,
                short_description="توضیح کوتاه واقعی درباره کولیس دیجیتال اینسایز",
                description="بدنه بلند نباید استفاده شود",
                name="کولیس",
            )
            == "توضیح کوتاه واقعی درباره کولیس دیجیتال اینسایز"
        )
        assert "کارزار" in resolve_meta_description(
            meta_description=None,
            short_description=None,
            description=None,
            name="کولیس دیجیتال",
        )

    def test_stub_classifier(self):
        assert is_stub_description(None) is True
        assert is_stub_description("کوتاه", product_name="کولیس") is True
        assert is_stub_description("کولیس دیجیتال میتوتویو", product_name="کولیس دیجیتال میتوتویو") is True
        assert (
            is_stub_description(
                "کولیس دیجیتال میتوتویو با بدنه استیل ضدزنگ برای اندازه‌گیری دقیق در کارگاه",
                product_name="کولیس دیجیتال میتوتویو",
            )
            is False
        )

    def test_jsonld_uses_short(self):
        text = resolve_jsonld_description(
            short_description="توضیح کوتاه قابل‌نمایش روی صفحه محصول بدون ادعای دقت عددی",
            description="بدنه بلند با جزئیات بیشتر",
            name="محصول",
        )
        assert text.startswith("توضیح کوتاه")

    def test_template_uses_only_sot(self):
        assert render_short_description_template(name="X") is None
        out = render_short_description_template(
            name="کولیس دیجیتال",
            brand_name="INSIZE",
            category_name="کولیس دیجیتال",
            sku="1108-150",
            technical_specs={"range": "0-150mm"},
        )
        assert out is not None
        assert "INSIZE" in out
        assert "0-150mm" in out
        assert "1108-150" in out


class TestProductSeoApi:
    def test_create_and_public_detail_expose_seo_fields(
        self, valid_product_data, super_admin_headers
    ):
        payload = {
            **valid_product_data,
            "sku": "SEO-P0-001",
            "short_description": "توضیح کوتاه محصول برای کارت و متا بدون ادعای ساختگی",
            "description": "توضیحات بلند محصول برای بخش پایین صفحه.",
            "meta_title": "عنوان سئو تست",
            "meta_description": "توضیح متای تست برای موتور جستجو با طول کافی",
        }
        create = client.post("/api/v1/products/", json=payload, headers=super_admin_headers)
        assert create.status_code == 201
        created = create.json()
        for field in ("slug", "short_description", "meta_title", "meta_description"):
            assert field in created
        assert created["short_description"].startswith("توضیح کوتاه")
        assert created["meta_title"] == "عنوان سئو تست"
        assert created["description"].startswith("توضیحات بلند")

        product_id = created["id"]
        public = client.get(f"/api/v1/products/{product_id}")
        assert public.status_code == 200
        body = public.json()
        assert body["slug"]
        assert body["short_description"] == payload["short_description"]
        assert body["meta_title"] == "عنوان سئو تست"
        assert body["meta_description"] == payload["meta_description"]
        assert body["description"] == payload["description"]

        listing = client.get("/api/v1/products/?search=SEO-P0-001")
        assert listing.status_code == 200
        row = next(r for r in listing.json()["data"] if r["sku"] == "SEO-P0-001")
        assert row["slug"] == body["slug"]
        assert row["short_description"] == payload["short_description"]

    def test_update_short_and_meta_fields(self, valid_product_data, super_admin_headers):
        create = client.post(
            "/api/v1/products/",
            json={**valid_product_data, "sku": "SEO-P0-002"},
            headers=super_admin_headers,
        )
        product_id = create.json()["id"]
        updated = client.put(
            f"/api/v1/products/{product_id}",
            json={
                "short_description": "بدنه کوتاه به‌روزشده برای نمایش در صفحه محصول کارزار",
                "meta_description": "متای به‌روز برای ایندکس با متن غیرتکراری و کافی",
            },
            headers=super_admin_headers,
        )
        assert updated.status_code == 200
        assert updated.json()["short_description"].startswith("بدنه کوتاه")
        assert "متای به‌روز" in updated.json()["meta_description"]
