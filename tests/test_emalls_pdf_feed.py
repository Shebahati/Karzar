"""Direct Emalls PDF feed adapter tests (query-param contract).

Isolated from the WordPress-compatible ``/products`` adapter.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from app.core.config import settings
from app.db.models.product import Category, Product, ProductImage
from app.main import app
from app.services.emalls.client import EmallsClient
from app.services.emalls.pdf_feed import (
    EmallsPdfFeedIntegrityError,
    decimal_to_exact_toman_int,
)
from app.services.emalls.token_cache import reset_emalls_token_cache_for_tests
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TestingSessionLocal

pytestmark = pytest.mark.usefixtures("override_database")

client = TestClient(app)
FEED = "/api/v1/integrations/emalls/feed"
WP_PRODUCTS = "/api/v1/integrations/emalls/products"

# Sentinel: omit category_id → default seeded leaf (id=3).
# Pass category_id=None explicitly when a null FK is intended (DB may reject).
_DEFAULT_CATEGORY = object()


@pytest.fixture(autouse=True)
def _pdf_feed_defaults(monkeypatch):
    reset_emalls_token_cache_for_tests()
    monkeypatch.setattr(settings, "STOREFRONT_HIDE_IMAGELESS_PRODUCTS", True)
    monkeypatch.setattr(settings, "STOREFRONT_REQUIRE_MATERIALIZED_IMAGES", False)
    monkeypatch.setattr(settings, "PUBLIC_ASSET_BASE", "https://cdn.karzartools.com")
    monkeypatch.setattr(settings, "EMALLS_PUBLIC_SITE_ORIGIN", "https://www.karzartools.com")
    monkeypatch.setattr(settings, "PUBLIC_THROTTLE_EMALLS_MAX", 5000)
    yield
    reset_emalls_token_cache_for_tests()


def _valid_image(product_id: int = 0, *, url: str = "/static/uploads/p.webp") -> ProductImage:
    return ProductImage(
        product_id=product_id,
        image_url=url,
        is_primary=True,
        display_order=0,
    )


def _product(
    *,
    sku: str,
    name: str | None = None,
    is_active: bool = True,
    is_available: bool = True,
    deleted_at: datetime | None = None,
    base_price: Decimal | None = Decimal("2500000"),
    original_price: Decimal | None = None,
    warranty_text: str | None = "گارانتی",
    slug: str | None = None,
    category_id: Any = _DEFAULT_CATEGORY,
) -> Product:
    resolved_category: int | None
    if category_id is _DEFAULT_CATEGORY:
        resolved_category = 3
    else:
        resolved_category = category_id  # may be None when explicitly requested
    return Product(
        sku=sku,
        slug=slug if slug is not None else sku.lower().replace(" ", "-"),
        name=name if name is not None else sku,
        category_id=resolved_category,  # type: ignore[arg-type]
        brand_id=1,
        is_active=is_active,
        is_available=is_available,
        deleted_at=deleted_at,
        base_price=base_price,
        original_price=original_price,
        warranty_text=warranty_text,
        specifications={
            "technical_specs": {},
            "dimensions": {},
            "features": {},
            "optional_accessories": [],
        },
    )


async def _seed(session: AsyncSession, product: Product, *images: ProductImage) -> Product:
    session.add(product)
    await session.flush()
    for image in images:
        image.product_id = product.id
        session.add(image)
    await session.flush()
    await session.refresh(product)
    return product


class TestEmallsPdfFeedRequest:
    def test_get_valid_200(self):
        async def seed():
            async with TestingSessionLocal() as session:
                await _seed(session, _product(sku="PDF-1"), _valid_image())
                await session.commit()

        asyncio.run(seed())
        response = client.get(FEED, params={"page": 1, "item_per_page": 50})
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")

    def test_post_empty_body_query_200(self):
        response = client.post(f"{FEED}?page=1&item_per_page=50")
        assert response.status_code == 200

    def test_get_post_parity(self):
        async def seed():
            async with TestingSessionLocal() as session:
                await _seed(session, _product(sku="PDF-PARITY"), _valid_image())
                await session.commit()

        asyncio.run(seed())
        get_body = client.get(FEED, params={"page": 1, "item_per_page": 10}).json()
        post_body = client.post(f"{FEED}?page=1&item_per_page=10").json()
        assert get_body == post_body

    def test_defaults(self):
        body = client.get(FEED).json()
        assert body["page_num"] == 1
        assert body["item_per_page"] == 50

    def test_page_zero_422(self):
        assert client.get(FEED, params={"page": 0}).status_code == 422

    def test_item_per_page_zero_422(self):
        assert client.get(FEED, params={"item_per_page": 0}).status_code == 422

    def test_over_safety_cap_422(self):
        assert client.get(FEED, params={"item_per_page": 101}).status_code == 422


class TestEmallsPdfFeedRootAndProduct:
    def test_root_and_product_contract(self):
        async def seed():
            async with TestingSessionLocal() as session:
                discounted = await _seed(
                    session,
                    _product(
                        sku="PDF-DISC",
                        name="کولیس",
                        slug="caliper-disc",
                        base_price=Decimal("2500000"),
                        original_price=Decimal("3000000"),
                        is_available=True,
                        warranty_text="12 ماه",
                    ),
                    _valid_image(url="/static/uploads/primary.webp"),
                )
                no_disc = await _seed(
                    session,
                    _product(
                        sku="PDF-NODISC",
                        name="میکرومتر",
                        slug="micrometer",
                        base_price=Decimal("2500000"),
                        original_price=None,
                        is_available=False,
                    ),
                    _valid_image(),
                )
                await session.commit()
                return discounted.id, no_disc.id

        disc_id, nodisc_id = asyncio.run(seed())
        body = client.get(FEED, params={"page": 1, "item_per_page": 50}).json()
        assert set(body.keys()) == {
            "success",
            "products",
            "total_items",
            "pages_count",
            "item_per_page",
            "page_num",
        }
        assert body["success"] is True
        assert isinstance(body["products"], list)
        assert body["total_items"] == 2
        assert body["pages_count"] == 1
        assert body["item_per_page"] == 50
        assert body["page_num"] == 1
        # Forbidden WP-adapter fields
        for forbidden in ("count", "max_pages", "Version", "NeedSession", "TokenSendByEmalls"):
            assert forbidden not in body

        by_id = {row["id"]: row for row in body["products"]}
        disc = by_id[str(disc_id)]
        assert isinstance(disc["id"], str)
        assert disc["price"] == 2500000
        assert isinstance(disc["price"], int)
        assert disc["price"] != "2500000"
        assert disc["old_price"] == 3000000
        assert disc["title"] == "کولیس"
        assert disc["category"] == "0-150mm Range"
        assert disc["image"].startswith("https://cdn.karzartools.com/")
        assert disc["guarantee"] == "12 ماه"
        assert disc["color"] == ""
        assert disc["is_available"] is True
        assert isinstance(disc["is_available"], bool)
        assert disc["url"] == "https://www.karzartools.com/product/caliper-disc"
        assert set(disc.keys()) == {
            "title",
            "id",
            "price",
            "old_price",
            "category",
            "image",
            "color",
            "guarantee",
            "is_available",
            "url",
        }
        assert "stock_quantity" not in disc

        nodisc = by_id[str(nodisc_id)]
        assert nodisc["old_price"] is None
        assert nodisc["is_available"] is False
        assert nodisc["price"] == 2500000


class TestEmallsPdfFeedEligibility:
    def test_eligibility_matrix(self):
        async def seed():
            async with TestingSessionLocal() as session:
                ok_out = await _seed(
                    session,
                    _product(sku="ELIG-OUT", is_available=False),
                    _valid_image(),
                )
                inactive = await _seed(
                    session,
                    _product(sku="ELIG-INACT", is_active=False),
                    _valid_image(),
                )
                deleted = await _seed(
                    session,
                    _product(sku="ELIG-DEL", deleted_at=datetime.now(UTC)),
                    _valid_image(),
                )
                unpriced = await _seed(
                    session,
                    _product(sku="ELIG-NOPRICE", base_price=None),
                    _valid_image(),
                )
                imageless = await _seed(session, _product(sku="ELIG-NOIMG"))
                placeholder = await _seed(
                    session,
                    _product(sku="ELIG-PH"),
                    ProductImage(
                        product_id=0,
                        image_url="/images/placeholders/karzar-editorial.svg",
                        is_primary=True,
                        display_order=0,
                    ),
                )
                empty_name = await _seed(
                    session,
                    _product(sku="ELIG-ENAME", name=" "),
                    _valid_image(),
                )
                empty_slug = await _seed(
                    session,
                    _product(sku="ELIG-ESLUG", slug=" "),
                    _valid_image(),
                )
                await session.commit()
                return {
                    "ok_out": ok_out.id,
                    "inactive": inactive.id,
                    "deleted": deleted.id,
                    "unpriced": unpriced.id,
                    "imageless": imageless.id,
                    "placeholder": placeholder.id,
                    "empty_name": empty_name.id,
                    "empty_slug": empty_slug.id,
                }

        ids = asyncio.run(seed())
        exported = {
            row["id"] for row in client.get(FEED, params={"item_per_page": 100}).json()["products"]
        }
        assert str(ids["ok_out"]) in exported
        for key in (
            "inactive",
            "deleted",
            "unpriced",
            "imageless",
            "placeholder",
            "empty_name",
            "empty_slug",
        ):
            assert str(ids[key]) not in exported


class TestEmallsPdfFeedPagination:
    def test_ordering_pages_and_beyond(self):
        async def seed():
            async with TestingSessionLocal() as session:
                ids = []
                for i in range(5):
                    p = await _seed(session, _product(sku=f"PAGE-{i}"), _valid_image())
                    ids.append(p.id)
                await session.commit()
                return ids

        ids = asyncio.run(seed())
        page1 = client.get(FEED, params={"page": 1, "item_per_page": 2}).json()
        assert page1["total_items"] == 5
        assert page1["pages_count"] == 3
        page_ids = [int(row["id"]) for row in page1["products"]]
        assert page_ids == sorted(page_ids, reverse=True)
        assert set(page_ids).issubset(set(ids))

        seen: set[str] = set()
        for page in (1, 2, 3):
            body = client.get(FEED, params={"page": page, "item_per_page": 2}).json()
            for row in body["products"]:
                assert row["id"] not in seen
                seen.add(row["id"])
        assert len(seen) == 5

        beyond = client.get(FEED, params={"page": 99, "item_per_page": 2}).json()
        assert beyond["products"] == []
        assert beyond["total_items"] == 5
        assert beyond["pages_count"] == 3
        assert beyond["page_num"] == 99

    def test_zero_eligible(self):
        body = client.get(FEED).json()
        assert body["total_items"] == 0
        assert body["pages_count"] == 0
        assert body["products"] == []


class TestEmallsPdfPriceIntegrity:
    def test_exact_int_and_fractional_rejected(self):
        assert decimal_to_exact_toman_int(Decimal("2500000")) == 2500000
        with pytest.raises(EmallsPdfFeedIntegrityError):
            decimal_to_exact_toman_int(Decimal("2500000.5"))

    def test_fractional_base_price_excluded(self):
        async def seed():
            async with TestingSessionLocal() as session:
                await _seed(
                    session,
                    _product(sku="FRAC", base_price=Decimal("2500000.5")),
                    _valid_image(),
                )
                await session.commit()

        asyncio.run(seed())
        body = client.get(FEED).json()
        assert body["total_items"] == 0


class TestEmallsContractsIsolated:
    def test_wp_products_endpoint_unchanged_shape(self):
        mock = EmallsClient()
        mock.validate_token = AsyncMock(return_value=None)  # type: ignore[method-assign]
        with patch("app.services.emalls.service.get_emalls_client", return_value=mock):
            response = client.post(
                WP_PRODUCTS,
                json={"token": "tok", "page": 1, "limit": 5},
            )
        assert response.status_code == 200
        body = response.json()
        assert "count" in body
        assert "max_pages" in body
        assert "Version" in body
        assert "NeedSession" in body
        assert "products" in body
        assert "total_items" not in body
        assert "pages_count" not in body


class TestEmallsPdfPaginationIntegrity:
    def test_sql_ok_but_http_image_does_not_inflate_totals(self):
        """Would fail on HEAD that paginated before final HTTPS eligibility."""

        async def seed():
            async with TestingSessionLocal() as session:
                # Higher id → appears first in DESC order. SQL-coarse eligible
                # (non-placeholder image exists) but final PDF rule rejects HTTP.
                bad = await _seed(
                    session,
                    _product(sku="PAG-BAD-HTTP"),
                    ProductImage(
                        product_id=0,
                        image_url="http://example.com/bad.webp",
                        is_primary=True,
                        display_order=0,
                    ),
                )
                good = await _seed(
                    session,
                    _product(sku="PAG-GOOD"),
                    _valid_image(url="/static/uploads/good.webp"),
                )
                await session.commit()
                return bad.id, good.id

        bad_id, good_id = asyncio.run(seed())
        page1 = client.get(FEED, params={"page": 1, "item_per_page": 1}).json()
        assert page1["total_items"] == 1
        assert page1["pages_count"] == 1
        assert len(page1["products"]) == 1
        assert page1["products"][0]["id"] == str(good_id)

        page2 = client.get(FEED, params={"page": 2, "item_per_page": 1}).json()
        assert page2["products"] == []
        assert page2["total_items"] == 1
        assert page2["pages_count"] == 1
        assert str(bad_id) not in {
            row["id"]
            for body in (page1, page2)
            for row in body["products"]
        }

    def test_blank_category_name_excluded(self):
        async def seed():
            async with TestingSessionLocal() as session:
                blank = Category(
                    name=" ",
                    slug="blank-cat-pdf",
                    parent_id=2,
                )
                session.add(blank)
                await session.flush()
                excluded = await _seed(
                    session,
                    _product(sku="BLANK-CAT", category_id=blank.id),
                    _valid_image(),
                )
                included = await _seed(
                    session,
                    _product(sku="OK-CAT"),
                    _valid_image(),
                )
                await session.commit()
                return excluded.id, included.id

        excluded_id, included_id = asyncio.run(seed())
        body = client.get(FEED, params={"item_per_page": 100}).json()
        exported = {row["id"] for row in body["products"]}
        assert str(excluded_id) not in exported
        assert str(included_id) in exported

    def test_invalid_first_image_falls_through_to_valid(self):
        async def seed():
            async with TestingSessionLocal() as session:
                product = await _seed(
                    session,
                    _product(sku="IMG-FALLTHROUGH"),
                    ProductImage(
                        product_id=0,
                        image_url="http://example.com/first-bad.webp",
                        is_primary=True,
                        display_order=0,
                    ),
                    ProductImage(
                        product_id=0,
                        image_url="/static/uploads/second-good.webp",
                        is_primary=False,
                        display_order=1,
                    ),
                )
                await session.commit()
                return product.id

        pid = asyncio.run(seed())
        body = client.get(FEED, params={"item_per_page": 100}).json()
        by_id = {row["id"]: row for row in body["products"]}
        assert str(pid) in by_id
        assert by_id[str(pid)]["image"].startswith("https://cdn.karzartools.com/")
        assert "second-good.webp" in by_id[str(pid)]["image"]

    def test_full_scan_cardinality_with_interleaved_ineligible(self):
        async def seed():
            async with TestingSessionLocal() as session:
                # Interleave: good, http-bad, good, placeholder, good (DESC order)
                ids_good = []
                for i in range(3):
                    p = await _seed(
                        session,
                        _product(sku=f"SCAN-G-{i}"),
                        _valid_image(url=f"/static/uploads/scan-g-{i}.webp"),
                    )
                    ids_good.append(p.id)
                    if i < 2:
                        await _seed(
                            session,
                            _product(sku=f"SCAN-B-{i}"),
                            ProductImage(
                                product_id=0,
                                image_url=(
                                    "http://example.com/bad.webp"
                                    if i == 0
                                    else "/images/placeholders/karzar-editorial.svg"
                                ),
                                is_primary=True,
                                display_order=0,
                            ),
                        )
                await session.commit()
                return ids_good

        good_ids = asyncio.run(seed())
        item_per_page = 2
        first = client.get(FEED, params={"page": 1, "item_per_page": item_per_page}).json()
        total = first["total_items"]
        pages_count = first["pages_count"]
        assert total == 3
        assert pages_count == 2

        fetched = 0
        seen: set[str] = set()
        for page in range(1, pages_count + 1):
            body = client.get(
                FEED, params={"page": page, "item_per_page": item_per_page}
            ).json()
            assert body["total_items"] == total
            assert body["pages_count"] == pages_count
            assert body["page_num"] == page
            assert body["item_per_page"] == item_per_page
            if page < pages_count:
                assert len(body["products"]) == item_per_page
            for row in body["products"]:
                assert row["id"] not in seen
                seen.add(row["id"])
            fetched += len(body["products"])

        assert fetched == total
        assert seen == {str(i) for i in good_ids}
