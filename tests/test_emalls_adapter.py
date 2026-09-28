"""Emalls read-only product extraction adapter tests.

Never contacts live emalls.ir — all validator HTTP calls are mocked.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from app.core.config import settings
from app.db.models.product import Product, ProductImage
from app.main import app
from app.services.emalls.client import EmallsClient
from app.services.emalls.exceptions import (
    EmallsTokenInvalidError,
    EmallsValidationUnavailableError,
)
from app.services.emalls.presenter import build_emalls_spec, present_emalls_product
from app.services.emalls.token_cache import (
    InMemoryEmallsTokenCache,
    reset_emalls_token_cache_for_tests,
    token_cache_key,
)
from fastapi.testclient import TestClient
from scripts.emalls_preflight import analyze_products
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TestingSessionLocal

pytestmark = pytest.mark.usefixtures("override_database")

client = TestClient(app)
ENDPOINT = "/api/v1/integrations/emalls/products"
VALID_TOKEN = "emalls-test-token-not-a-secret"


@pytest.fixture(autouse=True)
def _emalls_test_defaults(monkeypatch):
    reset_emalls_token_cache_for_tests()
    monkeypatch.setattr(settings, "STOREFRONT_HIDE_IMAGELESS_PRODUCTS", True)
    monkeypatch.setattr(settings, "STOREFRONT_REQUIRE_MATERIALIZED_IMAGES", False)
    monkeypatch.setattr(settings, "PUBLIC_ASSET_BASE", "https://cdn.karzartools.com")
    monkeypatch.setattr(settings, "EMALLS_PUBLIC_SITE_ORIGIN", "https://www.karzartools.com")
    monkeypatch.setattr(settings, "EMALLS_SHOP_DOMAIN", "karzartools.com")
    monkeypatch.setattr(settings, "EMALLS_COMPAT_VERSION", "1.3.0")
    monkeypatch.setattr(settings, "PUBLIC_THROTTLE_EMALLS_MAX", 5000)
    yield
    reset_emalls_token_cache_for_tests()


def _valid_image(
    product_id: int,
    *,
    url: str = "/static/uploads/products/1/photo.webp",
    is_primary: bool = True,
    display_order: int = 0,
) -> ProductImage:
    return ProductImage(
        product_id=product_id,
        image_url=url,
        is_primary=is_primary,
        display_order=display_order,
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
    warranty_text: str | None = "گارانتی اصالت",
    short_description: str | None = "خلاصه",
    specifications: dict | None = None,
    slug: str | None = None,
) -> Product:
    return Product(
        sku=sku,
        slug=slug or sku.lower().replace(" ", "-"),
        name=name or sku,
        category_id=3,
        brand_id=1,
        is_active=is_active,
        is_available=is_available,
        deleted_at=deleted_at,
        base_price=base_price,
        original_price=original_price,
        warranty_text=warranty_text,
        short_description=short_description,
        specifications=specifications
        or {
            "technical_specs": {"range": "0-150mm"},
            "dimensions": {},
            "features": {},
            "optional_accessories": [],
        },
    )


async def _seed_product(session: AsyncSession, product: Product, *images: ProductImage) -> Product:
    session.add(product)
    await session.flush()
    for image in images:
        image.product_id = product.id
        session.add(image)
    await session.flush()
    await session.refresh(product)
    return product


def _mock_valid_client() -> EmallsClient:
    client_mock = EmallsClient()
    client_mock.validate_token = AsyncMock(return_value=None)  # type: ignore[method-assign]
    return client_mock


def _post_json(body: dict, *, emalls_client: EmallsClient | None = None, cache=None):
    mock_client = emalls_client or _mock_valid_client()
    from contextlib import ExitStack

    with ExitStack() as stack:
        stack.enter_context(
            patch("app.services.emalls.service.get_emalls_client", return_value=mock_client)
        )
        if cache is not None:
            stack.enter_context(
                patch("app.services.emalls.service.get_emalls_token_cache", return_value=cache)
            )
        return client.post(ENDPOINT, json=body)


def _post_form(data: dict, *, emalls_client: EmallsClient | None = None, cache=None):
    mock_client = emalls_client or _mock_valid_client()
    from contextlib import ExitStack

    with ExitStack() as stack:
        stack.enter_context(
            patch("app.services.emalls.service.get_emalls_client", return_value=mock_client)
        )
        if cache is not None:
            stack.enter_context(
                patch("app.services.emalls.service.get_emalls_token_cache", return_value=cache)
            )
        return client.post(ENDPOINT, data=data)


class TestEmallsAuthAndNeedSession:
    def test_valid_token_cache_miss_need_session_true(self):
        async def seed():
            async with TestingSessionLocal() as session:
                product = await _seed_product(session, _product(sku="AUTH-OK"), _valid_image(0))
                await session.commit()
                return product.id

        product_id = asyncio.run(seed())
        response = _post_json({"token": VALID_TOKEN, "page": 1, "limit": 10})
        assert response.status_code == 200
        body = response.json()
        assert body["NeedSession"] is True
        assert body["Version"] == "1.3.0"
        assert "TokenSendByEmalls" not in body
        assert any(row["page_unique"] == product_id for row in body["products"])

    def test_cached_valid_token_need_session_false_skips_outbound(self):
        cache = InMemoryEmallsTokenCache()
        key = token_cache_key(VALID_TOKEN, settings.EMALLS_SHOP_DOMAIN)
        asyncio.run(cache.set_valid(key, 3600))

        mock_client = EmallsClient()
        mock_client.validate_token = AsyncMock(  # type: ignore[method-assign]
            side_effect=AssertionError("should not call validator on cache hit")
        )
        response = _post_json(
            {"token": VALID_TOKEN, "page": 1, "limit": 5},
            emalls_client=mock_client,
            cache=cache,
        )
        assert response.status_code == 200
        assert response.json()["NeedSession"] is False
        mock_client.validate_token.assert_not_awaited()

    def test_second_call_within_ttl_uses_cache(self):
        cache = InMemoryEmallsTokenCache()
        mock_client = EmallsClient()
        mock_client.validate_token = AsyncMock(return_value=None)  # type: ignore[method-assign]

        first = _post_json(
            {"token": VALID_TOKEN, "page": 1, "limit": 5},
            emalls_client=mock_client,
            cache=cache,
        )
        second = _post_json(
            {"token": VALID_TOKEN, "page": 1, "limit": 5},
            emalls_client=mock_client,
            cache=cache,
        )
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["NeedSession"] is True
        assert second.json()["NeedSession"] is False
        assert mock_client.validate_token.await_count == 1

    def test_invalid_token_401_not_cached(self):
        cache = InMemoryEmallsTokenCache()
        bad = EmallsClient()
        bad.validate_token = AsyncMock(side_effect=EmallsTokenInvalidError("bad"))  # type: ignore[method-assign]
        response = _post_json(
            {"token": "bad-token", "page": 1, "limit": 10},
            emalls_client=bad,
            cache=cache,
        )
        assert response.status_code == 401
        key = token_cache_key("bad-token", settings.EMALLS_SHOP_DOMAIN)
        assert asyncio.run(cache.get_valid(key)) is False

    def test_validator_unavailable_fail_closed_503(self):
        down = EmallsClient()
        down.validate_token = AsyncMock(  # type: ignore[method-assign]
            side_effect=EmallsValidationUnavailableError("timeout")
        )
        response = _post_json({"token": VALID_TOKEN, "page": 1, "limit": 5}, emalls_client=down)
        assert response.status_code == 503

    def test_raw_token_not_logged(self, caplog):
        secret = "super-secret-emalls-token-xyz"
        with caplog.at_level(logging.INFO):
            response = _post_json({"token": secret, "page": 1, "limit": 5})
        assert response.status_code == 200
        joined = " ".join(record.getMessage() for record in caplog.records)
        assert secret not in joined


class TestEmallsFormAndJsonParity:
    def test_json_and_form_same_products(self):
        async def seed():
            async with TestingSessionLocal() as session:
                await _seed_product(session, _product(sku="PARITY-1"), _valid_image(0))
                await session.commit()

        asyncio.run(seed())
        cache_a = InMemoryEmallsTokenCache()
        cache_b = InMemoryEmallsTokenCache()
        json_body = _post_json(
            {"token": VALID_TOKEN, "page": 1, "limit": 10, "variation": False},
            cache=cache_a,
        ).json()
        form_body = _post_form(
            {
                "token": VALID_TOKEN,
                "page": "1",
                "limit": "10",
                "variation": "false",
            },
            cache=cache_b,
        ).json()
        assert json_body["count"] == form_body["count"]
        assert [p["page_unique"] for p in json_body["products"]] == [
            p["page_unique"] for p in form_body["products"]
        ]
        assert [p["current_price"] for p in json_body["products"]] == [
            p["current_price"] for p in form_body["products"]
        ]

    def test_form_valid_200(self):
        response = _post_form({"token": VALID_TOKEN, "page": "1", "limit": "5"})
        assert response.status_code == 200

    def test_form_invalid_page_422(self):
        response = client.post(ENDPOINT, data={"token": VALID_TOKEN, "page": "0", "limit": "5"})
        assert response.status_code == 422
        assert response.json()["error_code"] == "VALIDATION_FAILED"

    def test_form_limit_over_100_422(self):
        response = client.post(ENDPOINT, data={"token": VALID_TOKEN, "page": "1", "limit": "101"})
        assert response.status_code == 422

    def test_form_missing_token_422(self):
        response = client.post(ENDPOINT, data={"page": "1", "limit": "5"})
        assert response.status_code == 422

    def test_form_whitespace_token_422(self):
        response = client.post(ENDPOINT, data={"token": "   ", "page": "1", "limit": "5"})
        assert response.status_code == 422


class TestEmallsPagination:
    def _seed_n(self, n: int) -> list[int]:
        async def run():
            ids: list[int] = []
            async with TestingSessionLocal() as session:
                for index in range(n):
                    product = await _seed_product(
                        session,
                        _product(sku=f"PAGE-{index:03d}"),
                        _valid_image(0),
                    )
                    ids.append(product.id)
                await session.commit()
            return ids

        return asyncio.run(run())

    def test_count_max_pages_and_ordering(self):
        ids = self._seed_n(5)
        response = _post_json({"token": VALID_TOKEN, "page": 1, "limit": 2})
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 5
        assert body["max_pages"] == 3
        page_ids = [row["page_unique"] for row in body["products"]]
        assert page_ids == sorted(page_ids, reverse=True)
        assert set(page_ids).issubset(set(ids))

    def test_last_page_and_beyond(self):
        self._seed_n(3)
        last = _post_json({"token": VALID_TOKEN, "page": 3, "limit": 1})
        assert last.status_code == 200
        assert len(last.json()["products"]) == 1
        beyond = _post_json({"token": VALID_TOKEN, "page": 99, "limit": 1})
        assert beyond.status_code == 200
        assert beyond.json()["products"] == []
        assert beyond.json()["count"] == 3

    def test_limit_cap_and_invalid(self):
        self._seed_n(1)
        ok = _post_json({"token": VALID_TOKEN, "page": 1, "limit": 100})
        assert ok.status_code == 200
        bad_limit = client.post(ENDPOINT, json={"token": VALID_TOKEN, "page": 1, "limit": 101})
        assert bad_limit.status_code == 422
        bad_page = client.post(ENDPOINT, json={"token": VALID_TOKEN, "page": 0, "limit": 10})
        assert bad_page.status_code == 422

    def test_no_duplicates_across_pages(self):
        self._seed_n(7)
        seen: set[int] = set()
        for page in (1, 2, 3, 4):
            body = _post_json({"token": VALID_TOKEN, "page": page, "limit": 2}).json()
            for row in body["products"]:
                assert row["page_unique"] not in seen
                seen.add(row["page_unique"])
        assert len(seen) == 7


class TestEmallsEligibilityAndAvailability:
    def test_eligibility_matrix(self):
        async def seed():
            async with TestingSessionLocal() as session:
                active = await _seed_product(
                    session,
                    _product(sku="ELIG-ACTIVE", is_available=True),
                    _valid_image(0),
                )
                unavailable = await _seed_product(
                    session,
                    _product(sku="ELIG-OUT", is_available=False),
                    _valid_image(0),
                )
                inactive = await _seed_product(
                    session,
                    _product(sku="ELIG-INACTIVE", is_active=False),
                    _valid_image(0),
                )
                deleted = await _seed_product(
                    session,
                    _product(sku="ELIG-DEL", deleted_at=datetime.now(UTC)),
                    _valid_image(0),
                )
                placeholder_only = await _seed_product(
                    session,
                    _product(sku="ELIG-PH"),
                    ProductImage(
                        product_id=0,
                        image_url="/images/placeholders/karzar-editorial.svg",
                        is_primary=True,
                        display_order=0,
                    ),
                )
                imageless = await _seed_product(session, _product(sku="ELIG-NOIMG"))
                await session.commit()
                return {
                    "active": active.id,
                    "unavailable": unavailable.id,
                    "inactive": inactive.id,
                    "deleted": deleted.id,
                    "placeholder": placeholder_only.id,
                    "imageless": imageless.id,
                }

        ids = asyncio.run(seed())
        body = _post_json({"token": VALID_TOKEN, "page": 1, "limit": 50}).json()
        exported = {row["page_unique"]: row for row in body["products"]}
        assert ids["active"] in exported
        assert exported[ids["active"]]["availability"] == "instock"
        assert ids["unavailable"] in exported
        assert exported[ids["unavailable"]]["availability"] == "outofstock"
        assert ids["inactive"] not in exported
        assert ids["deleted"] not in exported
        assert ids["placeholder"] not in exported
        assert ids["imageless"] not in exported
        for row in body["products"]:
            assert "stock_quantity" not in row


class TestEmallsPriceAndFields:
    def test_price_pass_through_toman_no_x10(self):
        async def seed():
            async with TestingSessionLocal() as session:
                product = await _seed_product(
                    session,
                    _product(
                        sku="PRICE-2500K",
                        base_price=Decimal("2500000"),
                        original_price=Decimal("3000000"),
                    ),
                    _valid_image(0),
                )
                null_price = await _seed_product(
                    session,
                    _product(sku="PRICE-NULL", base_price=None, original_price=None),
                    _valid_image(0),
                )
                await session.commit()
                return product.id, null_price.id

        priced_id, null_id = asyncio.run(seed())
        body = _post_json({"token": VALID_TOKEN, "page": 1, "limit": 50}).json()
        by_id = {row["page_unique"]: row for row in body["products"]}
        assert by_id[priced_id]["current_price"] == "2500000"
        assert by_id[priced_id]["old_price"] == "3000000"
        assert by_id[priced_id]["current_price"] != "25000000"
        assert by_id[priced_id]["current_price"] != "250000"
        assert by_id[null_id]["current_price"] == ""
        assert by_id[null_id]["old_price"] == ""

    def test_urls_images_warranty_timestamps_specs_features(self):
        async def seed():
            async with TestingSessionLocal() as session:
                product = await _seed_product(
                    session,
                    _product(
                        sku="1108-150",
                        name="کولیس دیجیتال",
                        slug="digital-caliper-1108-150",
                        warranty_text="18 ماه",
                        specifications={
                            "technical_specs": {"range": "0-150mm", "شناسه کالا": "legacy"},
                            "dimensions": {"L_mm": "236"},
                            "features": {"waterproof": True},
                            "optional_accessories": [{"name": "case"}],
                            "internal_evidence_id": "SHOULD-NOT-LEAK",
                        },
                    ),
                    _valid_image(
                        0,
                        url="/static/uploads/products/1/secondary.webp",
                        is_primary=False,
                        display_order=1,
                    ),
                    _valid_image(
                        0,
                        url="/static/uploads/products/1/primary.webp",
                        is_primary=True,
                        display_order=0,
                    ),
                    ProductImage(
                        product_id=0,
                        image_url="/images/placeholders/karzar-editorial.svg",
                        is_primary=False,
                        display_order=2,
                    ),
                )
                await session.commit()
                return product.id

        product_id = asyncio.run(seed())
        row = next(
            r
            for r in _post_json({"token": VALID_TOKEN, "page": 1, "limit": 50}).json()["products"]
            if r["page_unique"] == product_id
        )
        assert row["page_url"] == (
            "https://www.karzartools.com/product/digital-caliper-1108-150"
        )
        assert row["image_link"].startswith("https://cdn.karzartools.com/")
        assert "primary.webp" in row["image_link"]
        assert row["image_links"][0] == row["image_link"]
        assert all("placeholder" not in url for url in row["image_links"])
        assert len(row["image_links"]) == 2
        assert row["guarantee"] == "18 ماه"
        assert row["product_type"] == "simple"
        assert row["registry"] == ""
        assert row["category_name"] == "0-150mm Range"
        assert isinstance(row["spec"], list)
        assert len(row["spec"]) == 1
        spec = row["spec"][0]
        assert spec["شناسه کالا"] == "legacy"
        assert "range" in spec
        assert spec["waterproof"] == "true"
        assert "SHOULD-NOT-LEAK" not in str(spec)
        assert "internal_evidence_id" not in spec
        assert "optional_accessories" not in spec
        assert "case" not in str(spec)


class TestEmallsPresenterUnit:
    def test_sku_inserted_when_missing(self):
        product = _product(sku="ABC-1", specifications={"technical_specs": {"range": "1"}})
        product.id = 42
        product.category = None
        product.images = []
        product.created_at = datetime(2026, 1, 2, tzinfo=UTC)
        product.updated_at = datetime(2026, 1, 3, tzinfo=UTC)
        spec = build_emalls_spec(product)
        assert spec == [{"range": "1", "شناسه کالا": "ABC-1"}]

    def test_sku_only_when_no_other_specs(self):
        product = _product(
            sku="ONLY-SKU",
            specifications={
                "technical_specs": {},
                "dimensions": {},
                "features": {},
                "optional_accessories": [],
            },
        )
        assert build_emalls_spec(product) == [{"شناسه کالا": "ONLY-SKU"}]

    def test_features_included_unknown_excluded(self):
        product = _product(
            sku="FEAT-1",
            specifications={
                "technical_specs": {"range": "x"},
                "dimensions": {},
                "features": {"digital": True, "brand_secret": "nope"},
                "optional_accessories": [],
                "kb_evidence_id": "EV-9",
            },
        )
        flat = build_emalls_spec(product)[0]
        assert flat["digital"] == "true"
        assert flat["brand_secret"] == "nope"
        assert "kb_evidence_id" not in flat
        assert "EV-9" not in flat.values()

    def test_missing_warranty_empty(self):
        product = _product(sku="W-EMPTY", warranty_text=None)
        product.id = 7
        product.category = None
        product.images = [
            ProductImage(
                id=1,
                product_id=7,
                image_url="https://cdn.example/p.webp",
                is_primary=True,
                display_order=0,
            )
        ]
        product.created_at = datetime(2026, 1, 2, tzinfo=UTC)
        product.updated_at = datetime(2026, 1, 3, tzinfo=UTC)
        presented = present_emalls_product(product)
        assert presented.guarantee == ""


class TestEmallsClientStrictValidation:
    def _patch_response(self, monkeypatch, payload: dict, status_code: int = 200):
        class _Resp:
            def __init__(self):
                self.status_code = status_code

            def json(self):
                return payload

        class _Client:
            def __init__(self, *args, **kwargs):
                self.last_data = None

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def post(self, url, data=None, **kwargs):
                self.last_data = data
                _Client.last_posted = data  # type: ignore[attr-defined]
                return _Resp()

        monkeypatch.setattr(httpx, "AsyncClient", _Client)
        return _Client

    def test_exact_valid_message_accepted(self, monkeypatch):
        self._patch_response(
            monkeypatch, {"success": True, "message": "the token is valid"}
        )
        asyncio.run(EmallsClient().validate_token("tok"))

    def test_token_invalid_substring_rejected(self, monkeypatch):
        self._patch_response(
            monkeypatch, {"success": True, "message": "token invalid"}
        )
        with pytest.raises(EmallsTokenInvalidError):
            asyncio.run(EmallsClient().validate_token("tok"))

    def test_empty_message_rejected(self, monkeypatch):
        self._patch_response(monkeypatch, {"success": True, "message": ""})
        with pytest.raises(EmallsTokenInvalidError):
            asyncio.run(EmallsClient().validate_token("tok"))

    def test_success_false_rejected(self, monkeypatch):
        self._patch_response(
            monkeypatch, {"success": False, "message": "the token is valid"}
        )
        with pytest.raises(EmallsTokenInvalidError):
            asyncio.run(EmallsClient().validate_token("tok"))

    def test_validator_receives_compat_version_1_3_0(self, monkeypatch):
        client_cls = self._patch_response(
            monkeypatch, {"success": True, "message": "the token is valid"}
        )
        asyncio.run(EmallsClient().validate_token("tok"))
        posted = client_cls.last_posted  # type: ignore[attr-defined]
        assert posted["version"] == "1.3.0"
        assert posted["shop_domain"] == "karzartools.com"


class TestEmallsPreflightHelpers:
    def test_sku_mismatch_and_form_format_flags(self):
        products = [
            {
                "page_unique": 1,
                "title": "A",
                "current_price": "1000",
                "availability": "instock",
                "page_url": "https://www.karzartools.com/product/a",
                "image_link": "https://cdn.karzartools.com/a.webp",
                "spec": [{"شناسه کالا": "WRONG"}],
            },
            {
                "page_unique": 2,
                "title": "B",
                "current_price": "2000",
                "availability": "outofstock",
                "page_url": "https://www.karzartools.com/product/b",
                "image_link": "/relative.webp",
                "spec": [{}],
            },
        ]
        report = analyze_products(
            products,
            expected_skus={1: "RIGHT", 2: "B-SKU"},
            expected_page_origin="https://www.karzartools.com",
        )
        assert report["sku_spec_mismatch"] == 1
        assert report["sku_spec_missing"] == 1
        assert report["non_absolute_image"] == 1
