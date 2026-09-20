"""Fixture-based tests for READ-ONLY zcc.ir Phase 1 discovery. No live network."""

from __future__ import annotations

import io
import json
import re
import sys
from decimal import Decimal
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = ROOT / "tests" / "fixtures" / "zcc_ir"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.core import CurrentProduct, index_current_products, normalize_sku  # noqa: E402
from zcc_ir_catalog.categories import map_source_category  # noqa: E402
from zcc_ir_catalog.crawl import ReadOnlyFetcher  # noqa: E402
from zcc_ir_catalog.discover import merge_product_universe  # noqa: E402
from zcc_ir_catalog.karzar_snapshot import (  # noqa: E402
    WRITE_METHODS,
    KarzarApiBaseError,
    _assert_get_only,
    _get_json,
    load_karzar_snapshot,
    normalize_karzar_api_origin,
    products_from_public_json,
    resolve_karzar_public_origin,
)
from zcc_ir_catalog.models import DiscoveryUrl  # noqa: E402
from zcc_ir_catalog.normalize import (  # noqa: E402
    canonicalize_brand,
    encode_http_url,
    extract_model_from_name,
    manufacturer_identity_key,
    normalize_source_url,
)
from zcc_ir_catalog.parse import (  # noqa: E402
    extract_product_urls_from_html,
    listing_page_numbers,
    parse_product_html,
    parse_robots,
    parse_sitemap_index,
    parse_urlset,
    robots_allows,
)
from zcc_ir_catalog.pipeline import crawl_products, run_phase1  # noqa: E402
from zcc_ir_catalog.quality import quality_report  # noqa: E402
from zcc_ir_catalog.reconcile import (  # noqa: E402
    classify_match,
    match_source_to_karzar,
    reconcile_products,
)
from zcc_ir_catalog_discover import FORBIDDEN  # noqa: E402
from zcc_ir_catalog_discover import main as cli_main  # noqa: E402


def _html(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _current(**kwargs: object) -> CurrentProduct:
    sku = str(kwargs.get("sku") or "")
    brand = str(kwargs.get("brand") or "ZCC.CT | زد سی‌سی")
    return CurrentProduct(
        id=str(kwargs.get("id") or "1"),
        sku=sku,
        normalized_sku=normalize_sku(sku),
        slug=str(kwargs.get("slug") or sku.lower()),
        name=str(kwargs.get("name") or sku),
        brand_id=str(kwargs.get("brand_id") or "8"),
        brand=brand,
        brand_key=canonicalize_brand(brand),
        category_id=str(kwargs.get("category_id") or "33"),
        base_price=kwargs.get("base_price") if isinstance(kwargs.get("base_price"), Decimal) else Decimal("1178000"),
        is_active=True,
        is_available=bool(kwargs.get("is_available", True)),
        deleted_at=None,
        primary_image_url=str(kwargs.get("primary_image_url") or "https://example/img.jpg"),
        image_count=1,
        source="test",
    )


def test_sku_and_url_normalization() -> None:
    assert manufacturer_identity_key("DCMT11T312-XM YBC203") == "DCMT11T312-XM-YBC203"
    assert manufacturer_identity_key("DCMT11T312-XM YBC203") != manufacturer_identity_key(
        "DCMT11T312-XM YBC252"
    )
    assert canonicalize_brand("ZCC") == "ZCC.CT"
    assert canonicalize_brand("SANOU") == "SAN OU"
    assert canonicalize_brand("STC") == "STC"
    assert extract_model_from_name("هلدر رو تراش ZCC مدل PWLNR2525M06 برای الماس") == "PWLNR2525M06"
    assert normalize_source_url("https://www.zcc.ir/product/dcmt11t312/") == "https://zcc.ir/product/dcmt11t312/"
    encoded = encode_http_url("https://zcc.ir/product-category/turning/الماس/")
    assert all(ord(ch) < 128 for ch in encoded)
    assert "%D8%" in encoded.upper() or "%d8%" in encoded


def test_listing_and_sitemap_parse() -> None:
    index = parse_sitemap_index((FIXTURES / "sitemap_index.xml").read_text(encoding="utf-8"))
    assert "https://zcc.ir/product-sitemap.xml" in index
    products = parse_urlset(
        (FIXTURES / "product-sitemap.xml").read_text(encoding="utf-8"), kind="product"
    )
    urls = [p.url for p in products]
    assert "https://zcc.ir/shop/" in urls
    assert any("/product/dcmt11t312/" in u for u in urls)
    html = _html("listing_page1.html")
    found = extract_product_urls_from_html(html)
    assert "https://zcc.ir/product/dcmt11t312/" in found
    assert listing_page_numbers(html) == [2, 3]


def test_product_parse_zcc_insert() -> None:
    product = parse_product_html(
        _html("product_dcmt.html"),
        source_url="https://zcc.ir/product/dcmt11t312/",
    )
    assert product.brand_normalized == "ZCC.CT"
    assert product.manufacturer_code == "DCMT11T312-XM YBC203"
    assert product.part_number == "DCMT11T312-XM-YBC203"
    assert product.source_internal_sku == "11396"
    assert product.source_product_id == "7696"
    assert product.price_currency == "IRR"
    assert product.price_normalized == "1178000"
    assert product.availability_normalized == "available"
    assert product.main_image_url.endswith("DCMT11T312-XM-YBC203.jpg")
    assert "turning" in (product.source_category_url or "")
    assert "sku_is_internal_numeric" in product.parse_flags


def test_product_parse_stc_does_not_inherit_jsonld_zcc_brand() -> None:
    product = parse_product_html(_html("product_stc.html"), source_url="https://zcc.ir/product/stc-snhq/")
    assert product.brand_normalized == "STC"
    assert product.jsonld_brand == "ZCC"
    assert "jsonld_brand_conflicts_name" in product.parse_flags
    assert product.manufacturer_code == "SNHQ150704S NC5340"


def test_product_parse_sanou() -> None:
    product = parse_product_html(
        _html("product_sanou.html"), source_url="https://zcc.ir/product/sanou-k11-315/"
    )
    assert product.brand_normalized == "SAN OU"
    assert product.manufacturer_code == "K11-315MM"
    assert product.source_internal_sku == "13494"


def test_malformed_missing_price_missing_image() -> None:
    bad = parse_product_html(
        _html("product_malformed.html"), source_url="https://zcc.ir/product/broken/"
    )
    assert "missing_jsonld_product" in bad.parse_flags
    assert "missing_brand" in bad.parse_flags
    assert "missing_manufacturer_code" in bad.parse_flags
    priced = parse_product_html(
        _html("product_missing_price.html"), source_url="https://zcc.ir/product/pwlnr/"
    )
    assert "missing_price" in priced.parse_flags
    assert priced.price_normalized is None
    imaged = parse_product_html(
        _html("product_missing_image.html"), source_url="https://zcc.ir/product/pwlnl/"
    )
    assert "missing_image" in imaged.parse_flags
    assert imaged.availability_normalized == "unavailable"


def test_variant_identity_preserved() -> None:
    a = parse_product_html(_html("product_variant_a.html"), source_url="https://zcc.ir/product/dcmt-a/")
    b = parse_product_html(_html("product_variant_b.html"), source_url="https://zcc.ir/product/dcmt-b/")
    assert a.part_number != b.part_number
    issues = quality_report([a, b])
    kinds = {i.kind for i in issues}
    assert "sku_normalization_collision" not in kinds


def test_duplicate_detection_flags_conflicts() -> None:
    a = parse_product_html(_html("product_variant_a.html"), source_url="https://zcc.ir/product/dcmt-a/")
    clone = parse_product_html(_html("product_variant_a.html"), source_url="https://zcc.ir/product/dcmt-a-dup/")
    issues = quality_report([a, clone])
    assert any(i.kind == "sku_normalization_collision" for i in issues)
    assert any(i.kind == "duplicate_source_id" for i in issues)


def test_robots_blocks_wp_json_and_query_strings() -> None:
    rules = parse_robots((FIXTURES / "robots.txt").read_text(encoding="utf-8"))
    assert robots_allows("https://zcc.ir/product/dcmt11t312/", rules)
    assert robots_allows("https://zcc.ir/sitemap_index.xml", rules)
    assert not robots_allows("https://zcc.ir/wp-json/wc/store/v1/products", rules)
    assert not robots_allows("https://zcc.ir/shop/?page=2", rules)
    assert robots_allows("https://zcc.ir/shop/page/2/", rules)
    assert not robots_allows("https://zcc.ir/cart/", rules)


def test_reconciliation_exact_and_price_delta() -> None:
    source = parse_product_html(
        _html("product_dcmt.html"), source_url="https://zcc.ir/product/dcmt11t312/"
    )
    exact = _current(
        sku="ZCC-DCMT11T312-XM-YBC203",
        name=source.name_fa,
        base_price=Decimal("1178000"),
    )
    status, method, current, _cands, _reason = match_source_to_karzar(
        source, index_current_products([exact])
    )
    assert status == "MATCHED"
    assert method == "proven_prefix_alias"
    assert current is not None
    assert classify_match(source, exact) == "EXISTING_EXACT"

    priced = _current(
        sku="ZCC-DCMT11T312-XM-YBC203",
        name=source.name_fa,
        base_price=Decimal("999"),
    )
    assert classify_match(source, priced) == "EXISTING_DIFFERENT_PRICE"


def test_reconciliation_ambiguous_and_no_fuzzy() -> None:
    source = parse_product_html(
        _html("product_dcmt.html"), source_url="https://zcc.ir/product/dcmt11t312/"
    )
    dup_a = _current(id="1", sku="ZCC-DCMT11T312-XM-YBC203")
    dup_b = _current(id="2", sku="ZCC-DCMT11T312-XM-YBC203")
    status, _method, current, cands, _reason = match_source_to_karzar(
        source, index_current_products([dup_a, dup_b])
    )
    assert status == "AMBIGUOUS"
    assert current is None
    assert len(cands) == 2

    near = _current(sku="ZCC-DCMT11T312-XM-YBC252", name="different grade")
    status2, _m, cur2, _c, _r = match_source_to_karzar(source, index_current_products([near]))
    assert status2 == "CREATE_CANDIDATE"
    assert cur2 is None


def test_reconcile_karzar_only() -> None:
    source = parse_product_html(
        _html("product_dcmt.html"), source_url="https://zcc.ir/product/dcmt11t312/"
    )
    extra = _current(id="99", sku="ZCC-PWLNR2525M06", name="holder")
    rows, only = reconcile_products([source], [extra])
    assert rows[0].status == "CREATE_CANDIDATE"
    assert len(only) == 1
    assert only[0].sku == "ZCC-PWLNR2525M06"


def test_category_mapping_safety() -> None:
    index = {
        "اینسرتتراشcnc": ("166", "اینسرت › اینسرت تراش CNC"),
        "روتراش": ("27", "رو تراش"),
    }
    status, _conf, reason, kid, _path = map_source_category(
        path_names=["ابزار تراشکاری", "الماس تراشکاری"],
        category_url="https://zcc.ir/product-category/turning/turning-insert/",
        karzar_by_folded_name=index,
    )
    assert status == "SAFE_RULE"
    assert kid == "166"

    grooving, *_rest = map_source_category(
        path_names=["برش"],
        category_url="https://zcc.ir/product-category/turning/turning-tool-holder/cutting-and-grooving-holder/",
        karzar_by_folded_name=index,
    )
    assert grooving == "REVIEW"
    assert "machining distinction" in reason or grooving == "REVIEW"

    unknown, *_ = map_source_category(
        path_names=["something-new"],
        category_url="https://zcc.ir/product-category/unknown-root/leaf/",
        karzar_by_folded_name=index,
    )
    assert unknown == "UNMAPPED"


def test_public_json_snapshot_and_cli_apply_rejected(tmp_path: Path) -> None:
    rows = [
        {
            "id": 1,
            "sku": "ZCC-DCMT11T312-XM-YBC203",
            "name": "الماس",
            "base_price": "1178000",
            "availability": True,
            "thumbnail": "https://x/a.jpg",
            "brand": {"id": 8, "name": "ZCC.CT | زد سی‌سی"},
            "category": {"id": 33, "name": "اینسرت تراش CNC"},
        }
    ]
    products = products_from_public_json(rows, source="test")
    assert products[0].brand_key == "ZCC.CT"
    assert cli_main(["--apply"]) == 2
    for flag in FORBIDDEN:
        assert cli_main([flag]) == 2


class _FakeResp:
    def __init__(self, body: bytes, status: int = 200, headers: dict[str, str] | None = None) -> None:
        self._body = io.BytesIO(body)
        self.status = status
        self.headers = headers or {"Content-Type": "text/html; charset=utf-8"}

    def read(self, n: int = -1) -> bytes:
        return self._body.read() if n < 0 else self._body.read(n)

    def getcode(self) -> int:
        return self.status

    def __enter__(self) -> _FakeResp:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class ScriptedOpener:
    def __init__(self, routes: dict[str, object], failures: dict[str, int] | None = None) -> None:
        self.routes = routes
        self.failures = failures or {}
        self.calls: list[str] = []
        self.methods: list[str] = []

    def __call__(self, req: Request, timeout: float) -> _FakeResp:
        url = req.full_url
        self.calls.append(url)
        self.methods.append(req.get_method())
        remaining = self.failures.get(url, 0)
        if remaining:
            self.failures[url] = remaining - 1
            raise URLError("temporary")
        item = self.routes.get(url)
        if item is None:
            raise URLError(f"missing {url}")
        if isinstance(item, bytes):
            return _FakeResp(item)
        assert isinstance(item, str)
        return _FakeResp(item.encode("utf-8"))


def test_retry_and_checkpoint(tmp_path: Path) -> None:
    url = "https://zcc.ir/product/dcmt11t312/"
    opener = ScriptedOpener(
        {url: _html("product_dcmt.html")},
        failures={url: 2},
    )
    fetcher = ReadOnlyFetcher(
        cache_dir=tmp_path / "cache",
        robots_rules={"disallow": [], "allow": [], "sitemaps": []},
        timeout_s=5,
        retries=4,
        sleep_s=0,
        opener=opener,
        sleeper=lambda _s: None,
    )
    seeds = [DiscoveryUrl(url=url, kind="product")]
    products, failures = crawl_products(fetcher, seeds, output_dir=tmp_path, progress=lambda _m: None)
    assert not failures
    assert len(products) == 1
    assert fetcher.stats["retries"] >= 2
    checkpoint = json.loads((tmp_path / "checkpoint_urls.json").read_text(encoding="utf-8"))
    assert url in checkpoint["completed_urls"]
    # Second run uses cache; opener should not need to succeed again.
    opener.routes = {}
    products2, failures2 = crawl_products(fetcher, seeds, output_dir=tmp_path, progress=lambda _m: None)
    assert not failures2
    assert products2[0].manufacturer_code == products[0].manufacturer_code


def test_merge_universe_does_not_drop_listing_only_urls() -> None:
    sitemap = [
        DiscoveryUrl(url="https://zcc.ir/shop/", kind="product"),
        DiscoveryUrl(url="https://zcc.ir/product/dcmt11t312/", kind="product"),
    ]
    merged = merge_product_universe(
        sitemap, ["https://zcc.ir/product/stc-snhq/"], extra_method="listing_html"
    )
    urls = {row.url for row in merged}
    assert "https://zcc.ir/product/dcmt11t312/" in urls
    assert "https://zcc.ir/product/stc-snhq/" in urls
    assert not any("/shop/" in u for u in urls)


def test_fetcher_refuses_robots_disallowed(tmp_path: Path) -> None:
    rules = parse_robots((FIXTURES / "robots.txt").read_text(encoding="utf-8"))
    opener = ScriptedOpener({"https://zcc.ir/wp-json/": "{}"})
    fetcher = ReadOnlyFetcher(
        cache_dir=tmp_path / "cache",
        robots_rules=rules,
        sleep_s=0,
        opener=opener,
        sleeper=lambda _s: None,
    )
    result = fetcher.fetch("https://zcc.ir/wp-json/")
    assert not result.ok
    assert result.error == "robots_disallowed"
    assert opener.calls == []


def _sample_public_product_row() -> dict[str, object]:
    return {
        "id": 1,
        "sku": "ZCC-DCMT11T312-XM-YBC203",
        "name": "الماس",
        "base_price": "1178000",
        "availability": True,
        "thumbnail": "https://x/a.jpg",
        "brand": {"id": 8, "name": "ZCC.CT | زد سی‌سی"},
        "category": {"id": 33, "name": "اینسرت تراش CNC"},
    }


def _public_catalog_opener(origin: str) -> ScriptedOpener:
    empty = json.dumps({"data": [], "meta": {"has_next": False}})
    brands = json.dumps(
        {
            "data": [
                {"id": 8, "name": "ZCC.CT | زد سی‌سی", "product_count": 1},
                {"id": 9, "name": "SAN OU", "product_count": 0},
                {"id": 10, "name": "STC", "product_count": 0},
            ]
        }
    )
    products = json.dumps({"data": [_sample_public_product_row()], "meta": {"has_next": False}})
    categories = json.dumps({"data": [{"id": 33, "name": "اینسرت تراش CNC"}]})
    return ScriptedOpener(
        {
            f"{origin}/api/v1/brands/": brands,
            f"{origin}/api/v1/brands/?storefront_product_counts=true": brands,
            f"{origin}/api/v1/products/?brand_id=8&limit=100&skip=0": products,
            f"{origin}/api/v1/products/?brand_id=9&limit=100&skip=0": empty,
            f"{origin}/api/v1/products/?brand_id=10&limit=100&skip=0": empty,
            f"{origin}/api/v1/categories/": categories,
        }
    )


def test_no_hardcoded_public_api_origin() -> None:
    snapshot = (SCRIPTS / "zcc_ir_catalog" / "karzar_snapshot.py").read_text(encoding="utf-8")
    discover = (SCRIPTS / "zcc_ir_catalog_discover.py").read_text(encoding="utf-8")
    pipeline = (SCRIPTS / "zcc_ir_catalog" / "pipeline.py").read_text(encoding="utf-8")
    combined = snapshot + "\n" + discover + "\n" + pipeline
    assert "PUBLIC_API_ORIGIN" not in combined
    assert not re.search(
        r"""(?:getenv|environ\.get)\(\s*["'][A-Z0-9_]+["']\s*,\s*["']https?://[^"']*karzartools\.com""",
        combined,
    )
    assert not re.search(r"""\bdefault\s*=\s*["']https?://[^"']*karzartools\.com""", combined)
    assert not re.search(
        r"""^\s*[A-Za-z_][A-Za-z0-9_]*\s*=\s*["']https?://[^"']*karzartools\.com""",
        combined,
        re.M,
    )


def test_file_snapshot_works_without_api_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KARZAR_API_BASE", raising=False)

    def boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("live network must not be used")

    monkeypatch.setattr("zcc_ir_catalog.karzar_snapshot.urlopen", boom)
    path = tmp_path / "products.json"
    path.write_text(json.dumps([_sample_public_product_row()]), encoding="utf-8")
    products, meta = load_karzar_snapshot(products_json=str(path), fetch_public=True)
    assert meta["scope"] == "file_public_json"
    assert products[0].sku == "ZCC-DCMT11T312-XM-YBC203"
    assert products[0].brand_key == "ZCC.CT"


def test_public_fetch_fails_when_api_base_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KARZAR_API_BASE", raising=False)
    with pytest.raises(KarzarApiBaseError, match="KARZAR_API_BASE"):
        resolve_karzar_public_origin()
    with pytest.raises(KarzarApiBaseError, match="KARZAR_API_BASE"):
        load_karzar_snapshot(fetch_public=True)


def test_cli_public_fetch_requires_api_base(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("KARZAR_API_BASE", raising=False)
    assert cli_main(["--output-dir", str(tmp_path / "unused")]) == 2
    err = capsys.readouterr().err
    assert "KARZAR_API_BASE" in err
    assert "FATAL" in err


def test_configured_api_base_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KARZAR_API_BASE", raising=False)

    def boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("live network must not be used")

    monkeypatch.setattr("zcc_ir_catalog.karzar_snapshot.urlopen", boom)
    origin = "http://karzar.test"
    opener = _public_catalog_opener(origin)
    products, meta = load_karzar_snapshot(
        fetch_public=True,
        karzar_api_base=origin,
        opener=opener,
    )
    assert meta["origin"] == origin
    assert origin in str(meta["provenance"])
    assert "api.karzartools.com" not in str(meta["provenance"])
    assert products[0].sku == "ZCC-DCMT11T312-XM-YBC203"
    assert all(url.startswith(f"{origin}/api/v1/") for url in opener.calls)
    assert getattr(opener, "methods", [])
    assert set(opener.methods) == {"GET"}


def test_env_api_base_and_trailing_slash_and_api_v1_suffix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KARZAR_API_BASE", raising=False)
    monkeypatch.setattr(
        "zcc_ir_catalog.karzar_snapshot.urlopen",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("live network must not be used")),
    )
    origin = "http://karzar.test"
    opener = _public_catalog_opener(origin)
    monkeypatch.setenv("KARZAR_API_BASE", f"{origin}/api/v1/")
    products, meta = load_karzar_snapshot(fetch_public=True, opener=opener)
    assert products
    assert meta["origin"] == origin
    assert f"{origin}/api/v1/brands/" in opener.calls

    assert normalize_karzar_api_origin(f"{origin}/") == origin
    assert normalize_karzar_api_origin(f"{origin}/api/v1") == origin
    assert normalize_karzar_api_origin(f"{origin}/api/v1/") == origin


def test_invalid_api_base_rejected() -> None:
    with pytest.raises(KarzarApiBaseError, match="http or https"):
        normalize_karzar_api_origin("ftp://karzar.test")
    with pytest.raises(KarzarApiBaseError, match="credentials"):
        normalize_karzar_api_origin("https://user:pass@karzar.test")
    with pytest.raises(KarzarApiBaseError, match="path"):
        normalize_karzar_api_origin("http://karzar.test/other")
    with pytest.raises(KarzarApiBaseError, match="query"):
        normalize_karzar_api_origin("http://karzar.test/?x=1")
    with pytest.raises(RuntimeError, match="unsupported_url"):
        _get_json("ftp://karzar.test/api/v1/brands/")
    with pytest.raises(RuntimeError, match="credentials_not_allowed"):
        _get_json("https://user:pass@karzar.test/api/v1/brands/")


def test_get_only_enforcement() -> None:
    get_req = Request("http://karzar.test/api/v1/brands/", method="GET")
    _assert_get_only(get_req)
    for method in sorted(WRITE_METHODS):
        req = Request("http://karzar.test/api/v1/brands/", method=method)
        with pytest.raises(RuntimeError, match="write_method_forbidden"):
            _assert_get_only(req)


def test_pipeline_public_fetch_fails_closed_without_api_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("KARZAR_API_BASE", raising=False)
    with pytest.raises(KarzarApiBaseError, match="KARZAR_API_BASE"):
        run_phase1(
            output_dir=tmp_path / "out",
            cache_dir=tmp_path / "cache",
            fetch_karzar_public=True,
        )
    assert not (tmp_path / "out").exists()


def test_write_attempts_still_fail() -> None:
    assert cli_main(["--apply"]) == 2
    assert cli_main(["--write"]) == 2
    assert cli_main(["--mutate"]) == 2
    for flag in FORBIDDEN:
        assert cli_main([flag]) == 2
