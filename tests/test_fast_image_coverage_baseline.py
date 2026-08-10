"""Fixture-only tests for IMG-FAST-01A (zero live network)."""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
from pathlib import Path

import pytest
from PIL import Image
from scripts.fast_image_coverage_baseline.api_client import (
    fetch_all_products,
    parse_detail_images,
    require_api_base,
)
from scripts.fast_image_coverage_baseline.classify import classify_product, reconcile_states
from scripts.fast_image_coverage_baseline.contracts import (
    AssetValidation,
    DetailImage,
    ProductClassification,
    ProductListItem,
    RunCounters,
    ScanResult,
)
from scripts.fast_image_coverage_baseline.http_transport import (
    HttpResponse,
    RateLimitedTransport,
    decode_image_bytes,
    validate_asset,
)
from scripts.fast_image_coverage_baseline.output import (
    BASELINE_CSV_FIELDS,
    build_summary,
    verify_checksums,
    write_artifact_package,
)
from scripts.fast_image_coverage_baseline.placeholders import mark_placeholder
from scripts.fast_image_coverage_baseline.scan import run_scan
from scripts.fast_image_coverage_baseline.stability import compare_runs


def _png_bytes(color: tuple[int, int, int] = (10, 20, 30), size: tuple[int, int] = (32, 32)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _item(**kwargs) -> ProductListItem:
    base = dict(
        product_id=1,
        sku="SKU1",
        slug="sku-1",
        name="Product",
        brand_key="acme",
        brand_id=1,
        category_id=2,
        category_slug="cat",
        category_name="Cat",
        thumbnail=None,
    )
    base.update(kwargs)
    return ProductListItem(**base)  # type: ignore[arg-type]


def test_placeholder_exact_signature_only():
    assert mark_placeholder(
        "https://cdn.example/images/placeholders/karzar-editorial.svg",
        None,
    )
    assert mark_placeholder(
        "https://x/y.jpg",
        "6beb73e070a87c786ec339cb1d46943c726ba5e96866172690687e065b7b346f",
    )
    # small / plain image must NOT be placeholder by heuristics
    assert not mark_placeholder("https://cdn.example/static/uploads/products/1/a.jpg", None)


def test_decode_unreadable():
    ok, w, h, err = decode_image_bytes(b"not-an-image")
    assert ok is False and err and "decode_failed" in err


def test_six_state_usable_primary():
    thumb = "https://cdn.example/a.png"
    val = AssetValidation(
        url=thumb,
        normalized_url=thumb,
        http_status=200,
        decode_ok=True,
        width=100,
        height=100,
        sha256="abc",
    )
    c = classify_product(
        _item(thumbnail=thumb),
        thumb_validation=val,
        detail_images=None,
        image_validations={thumb: val},
        detail_fetched=False,
    )
    assert c.image_state == "usable_primary"
    assert c.fast_coverage_needed is False


def test_missing_thumbnail_empty_detail():
    c = classify_product(
        _item(thumbnail=None),
        thumb_validation=None,
        detail_images=[],
        image_validations={},
        detail_fetched=True,
    )
    assert c.image_state == "missing_all_images"


def test_broken_thumbnail_promotable_secondary():
    thumb = "https://cdn.example/broken.png"
    good = "https://cdn.example/good.png"
    broken = AssetValidation(
        url=thumb,
        normalized_url=thumb,
        http_status=404,
        decode_ok=False,
        error="http_404",
    )
    ok = AssetValidation(
        url=good,
        normalized_url=good,
        http_status=200,
        decode_ok=True,
        width=40,
        height=40,
        sha256="deadbeef",
    )
    images = [
        DetailImage(image_id=1, url=thumb, is_primary=True, display_order=0),
        DetailImage(image_id=2, url=good, is_primary=False, display_order=1),
    ]
    c = classify_product(
        _item(thumbnail=thumb),
        thumb_validation=broken,
        detail_images=images,
        image_validations={thumb: broken, good: ok},
        detail_fetched=True,
    )
    assert c.image_state == "promotable_existing_image"
    assert c.reusable_image_id == 2
    assert c.reusable_selection_reason


def test_broken_only():
    thumb = "https://cdn.example/broken.png"
    broken = AssetValidation(
        url=thumb,
        normalized_url=thumb,
        http_status=500,
        decode_ok=False,
        error="http_500",
        transient_exhausted=True,
    )
    c = classify_product(
        _item(thumbnail=thumb),
        thumb_validation=broken,
        detail_images=[DetailImage(1, thumb, True, 0)],
        image_validations={thumb: broken},
        detail_fetched=True,
    )
    assert c.image_state == "broken_only"


def test_known_placeholder_only():
    url = "https://cdn.example/images/placeholders/karzar-editorial.svg"
    val = AssetValidation(
        url=url,
        normalized_url=url,
        http_status=200,
        decode_ok=True,
        width=10,
        height=10,
        sha256="6beb73e070a87c786ec339cb1d46943c726ba5e96866172690687e065b7b346f",
        is_known_placeholder=True,
    )
    c = classify_product(
        _item(thumbnail=url),
        thumb_validation=val,
        detail_images=[DetailImage(1, url, True, 0)],
        image_validations={url: val},
        detail_fetched=True,
    )
    assert c.image_state == "known_placeholder_only"


def test_mutual_exclusivity_reconcile():
    rows = []
    for i, state in enumerate(
        [
            "usable_primary",
            "promotable_existing_image",
            "missing_all_images",
            "broken_only",
            "known_placeholder_only",
            "ambiguous_current_state",
        ]
    ):
        rows.append(
            ProductClassification(
                product_id=i + 1,
                sku=f"S{i}",
                slug=None,
                name="n",
                brand_key=None,
                brand_id=None,
                category_id=None,
                category_slug=None,
                category_name=None,
                image_state=state,
                primary_image_present=False,
                primary_image_reference=None,
                primary_decode_ok=None,
                primary_width=None,
                primary_height=None,
                primary_sha256=None,
                primary_http_status=None,
                placeholder_flag=False,
                broken_flag=False,
                fast_coverage_needed=state != "usable_primary",
            )
        )
    counts = reconcile_states(rows)
    assert counts["duplicate_product_ids_across_states"] == 0
    assert sum(counts[s] for s in [
        "usable_primary",
        "promotable_existing_image",
        "missing_all_images",
        "broken_only",
        "known_placeholder_only",
        "ambiguous_current_state",
    ]) == 6


def test_pagination_and_duplicate_protection():
    pages = {
        "https://api.example/api/v1/products/?skip=0&limit=2": {
            "data": [
                {"id": 1, "sku": "A", "slug": "a", "name": "A", "thumbnail": None, "brand": None, "category": None},
                {"id": 2, "sku": "B", "slug": "b", "name": "B", "thumbnail": None, "brand": None, "category": None},
            ],
            "meta": {"total_count": 3, "skip": 0, "limit": 2, "has_next": True},
        },
        "https://api.example/api/v1/products/?skip=2&limit=2": {
            "data": [
                {"id": 3, "sku": "C", "slug": "c", "name": "C", "thumbnail": None, "brand": None, "category": None},
            ],
            "meta": {"total_count": 3, "skip": 2, "limit": 2, "has_next": False},
        },
    }

    def fetch(method: str, url: str) -> HttpResponse:
        assert method == "GET"
        body = json.dumps(pages[url]).encode()
        return HttpResponse(200, {"content-type": "application/json"}, body, url)

    async def _run() -> None:
        transport = RateLimitedTransport(counters=RunCounters(), sync_fetch=fetch)
        items, total = await fetch_all_products(transport, api_base="https://api.example", page_size=2)
        assert total == 3 and [i.product_id for i in items] == [1, 2, 3]
        await transport.aclose()

    asyncio.run(_run())


def test_duplicate_page_raises():
    pages = {
        "https://api.example/api/v1/products/?skip=0&limit=2": {
            "data": [
                {"id": 1, "sku": "A", "slug": "a", "name": "A", "thumbnail": None},
                {"id": 2, "sku": "B", "slug": "b", "name": "B", "thumbnail": None},
            ],
            "meta": {"total_count": 3, "skip": 0, "limit": 2, "has_next": True},
        },
        "https://api.example/api/v1/products/?skip=2&limit=2": {
            "data": [
                {"id": 2, "sku": "B", "slug": "b", "name": "B", "thumbnail": None},
            ],
            "meta": {"total_count": 3, "skip": 2, "limit": 2, "has_next": False},
        },
    }

    def fetch(method: str, url: str) -> HttpResponse:
        body = json.dumps(pages[url]).encode()
        return HttpResponse(200, {}, body, url)

    async def _run() -> None:
        transport = RateLimitedTransport(counters=RunCounters(), sync_fetch=fetch)
        with pytest.raises(Exception) as ei:
            await fetch_all_products(transport, api_base="https://api.example", page_size=2)
        assert "duplicate" in str(ei.value).lower()
        await transport.aclose()

    asyncio.run(_run())


def test_429_backoff_and_retry(monkeypatch):
    calls = {"n": 0}

    def fetch(method: str, url: str) -> HttpResponse:
        calls["n"] += 1
        if calls["n"] == 1:
            return HttpResponse(429, {"retry-after": "0"}, b"", url)
        png = _png_bytes()
        return HttpResponse(200, {"content-type": "image/png"}, png, url)

    async def no_sleep(_):
        return None

    monkeypatch.setattr(
        "scripts.fast_image_coverage_baseline.http_transport.asyncio.sleep",
        no_sleep,
    )

    async def _run() -> None:
        transport = RateLimitedTransport(counters=RunCounters(), sync_fetch=fetch, retries=2)
        cache: dict[str, AssetValidation] = {}
        val = await validate_asset(transport, "https://cdn.example/x.png", cache=cache)
        assert val.decode_ok is True
        assert transport.counters.count_429 == 1
        val2 = await validate_asset(transport, "https://cdn.example/x.png", cache=cache)
        assert val2 is val
        assert transport.counters.asset_validation_requests == 1
        await transport.aclose()

    asyncio.run(_run())


def test_full_scan_fixture_resume_and_package(tmp_path: Path, monkeypatch):
    png = _png_bytes()
    png_sha = hashlib.sha256(png).hexdigest()
    catalog = [
        {"id": 1, "sku": "A", "slug": "a", "name": "A", "thumbnail": "https://cdn.example/ok.png", "brand": {"id": 1, "slug": "acme", "name": "Acme"}, "category": {"id": 9, "slug": "tools", "name": "Tools"}},
        {"id": 2, "sku": "B", "slug": "b", "name": "B", "thumbnail": None, "brand": None, "category": {"id": 9, "slug": "tools", "name": "Tools"}},
        {"id": 3, "sku": "C", "slug": "c", "name": "C", "thumbnail": "https://cdn.example/bad.png", "brand": {"slug": "acme"}, "category": {"id": 9, "slug": "tools", "name": "Tools"}},
    ]
    details = {
        2: {"id": 2, "images": []},
        3: {
            "id": 3,
            "images": [
                {"id": 10, "url": "https://cdn.example/bad.png", "is_primary": True, "display_order": 0},
                {"id": 11, "url": "https://cdn.example/good2.png", "is_primary": False, "display_order": 1},
            ],
        },
    }

    def fetch(method: str, url: str) -> HttpResponse:
        if "/api/v1/products/?" in url and "skip=0" in url:
            body = json.dumps(
                {
                    "data": catalog,
                    "meta": {
                        "total_count": 3,
                        "skip": 0,
                        "limit": 1000,
                        "has_next": False,
                    },
                }
            ).encode()
            return HttpResponse(200, {"content-type": "application/json"}, body, url)
        if url.endswith("/api/v1/products/2"):
            return HttpResponse(200, {}, json.dumps(details[2]).encode(), url)
        if url.endswith("/api/v1/products/3"):
            return HttpResponse(200, {}, json.dumps(details[3]).encode(), url)
        if url.endswith("/ok.png") or url.endswith("/good2.png"):
            return HttpResponse(200, {"content-type": "image/png"}, png, url)
        if url.endswith("/bad.png"):
            return HttpResponse(404, {}, b"missing", url)
        raise AssertionError(url)

    async def no_sleep(_):
        return None

    monkeypatch.setattr(
        "scripts.fast_image_coverage_baseline.http_transport.asyncio.sleep",
        no_sleep,
    )

    async def _run() -> None:
        run_dir = tmp_path / "run1"
        scan = await run_scan(
            output_run_dir=run_dir,
            api_base="https://api.example",
            page_size=1000,
            sync_fetch=fetch,
        )
        states = {c.product_id: c.image_state for c in scan.classifications}
        assert states[1] == "usable_primary"
        assert states[2] == "missing_all_images"
        assert states[3] == "promotable_existing_image"
        assert scan.catalog_total == 3

        scan2 = await run_scan(
            output_run_dir=run_dir,
            api_base="https://api.example",
            page_size=1000,
            sync_fetch=fetch,
            resume=True,
        )
        stable, drift = compare_runs(scan, scan2)
        assert stable is True
        assert drift == []

        summary = build_summary(scan2, semantic_second_run_stable=True, drift_rows=0, run_label="t")
        pkg = tmp_path / "pkg"
        write_artifact_package(pkg, scan2, summary=summary, drift_rows=[])
        checks = verify_checksums(pkg)
        assert checks["checksum_failures"] == 0
        assert checks["checksum_uncovered_files"] == 0
        assert checks["checksum_entries"] == checks["regular_payload_files_excluding_checksums_file"]
        header = (pkg / "catalog-image-baseline.csv").read_text(encoding="utf-8").splitlines()[0]
        for col in BASELINE_CSV_FIELDS:
            assert col in header
        assert png_sha

    asyncio.run(_run())


def test_parse_detail_image_order():
    payload = {
        "images": [
            {"id": 2, "url": "b", "is_primary": False, "display_order": 5},
            {"id": 1, "url": "a", "is_primary": True, "display_order": 9},
            {"id": 3, "url": "c", "is_primary": False, "display_order": 1},
        ]
    }
    imgs = parse_detail_images(payload)
    assert [i.url for i in imgs] == ["a", "c", "b"]


def test_drift_detection():
    def make(pid: int, state: str, thumb: str | None = None) -> ProductClassification:
        return ProductClassification(
            product_id=pid,
            sku="s",
            slug=None,
            name="n",
            brand_key=None,
            brand_id=None,
            category_id=None,
            category_slug=None,
            category_name=None,
            image_state=state,
            primary_image_present=bool(thumb),
            primary_image_reference=thumb,
            primary_decode_ok=True,
            primary_width=1,
            primary_height=1,
            primary_sha256=None,
            primary_http_status=200,
            placeholder_flag=False,
            broken_flag=False,
            fast_coverage_needed=state != "usable_primary",
        )

    r1 = ScanResult(
        classifications=[make(1, "usable_primary", "a"), make(2, "missing_all_images")],
        catalog_total=2,
        unique_product_ids=[1, 2],
    )
    r2 = ScanResult(
        classifications=[make(1, "broken_only", "a"), make(2, "missing_all_images")],
        catalog_total=2,
        unique_product_ids=[1, 2],
    )
    stable, drift = compare_runs(r1, r2)
    assert stable is False
    assert any(d["change_reason"] == "state_changed" for d in drift)


def test_zero_mutation_guards_in_summary(tmp_path: Path):
    c = ProductClassification(
        product_id=1,
        sku="s",
        slug=None,
        name="n",
        brand_key=None,
        brand_id=None,
        category_id=None,
        category_slug=None,
        category_name=None,
        image_state="missing_all_images",
        primary_image_present=False,
        primary_image_reference=None,
        primary_decode_ok=None,
        primary_width=None,
        primary_height=None,
        primary_sha256=None,
        primary_http_status=None,
        placeholder_flag=False,
        broken_flag=False,
        fast_coverage_needed=True,
    )
    scan = ScanResult(
        classifications=[c],
        catalog_total=1,
        unique_product_ids=[1],
        counters=RunCounters(),
        authority_notes={"authority_mode": "live_public_storefront_api"},
    )
    summary = build_summary(scan, semantic_second_run_stable=True, drift_rows=0, run_label="t")
    assert summary["database_accessed"] is False
    assert summary["database_modified"] is False
    assert summary["ProductImage_modified"] is False
    assert summary["API_write_requests"] == 0
    assert summary["external_discovery_requests"] == 0
    pkg = tmp_path / "out"
    write_artifact_package(pkg, scan, summary=summary, drift_rows=[])
    # package outside repo path not required in unit test; ensure no .git write
    assert not any(p.name.endswith(".pyc") for p in pkg.iterdir())


def test_api_client_has_no_production_default():
    import inspect

    import scripts.fast_image_coverage_baseline.api_client as api_client

    assert not hasattr(api_client, "DEFAULT_API_BASE")
    src = Path(api_client.__file__).read_text(encoding="utf-8")
    assert "karzartools.com" not in src
    sig_list = inspect.signature(api_client.fetch_all_products)
    assert sig_list.parameters["api_base"].default is inspect.Parameter.empty
    sig_detail = inspect.signature(api_client.fetch_product_detail)
    assert sig_detail.parameters["api_base"].default is inspect.Parameter.empty


def test_require_api_base_fail_closed():
    from scripts.fast_image_coverage_baseline.contracts import BaselineError

    with pytest.raises(BaselineError):
        require_api_base(None)
    with pytest.raises(BaselineError):
        require_api_base("")
    with pytest.raises(BaselineError):
        require_api_base("   ")
    assert require_api_base("https://api.example/") == "https://api.example"


def test_fetch_requires_explicit_api_base():
    transport = RateLimitedTransport(counters=RunCounters(), sync_fetch=lambda m, u: HttpResponse(200, {}, b"{}", u))

    async def _run() -> None:
        with pytest.raises(TypeError):
            await fetch_all_products(transport, page_size=1)  # type: ignore[call-arg]
        from scripts.fast_image_coverage_baseline.api_client import fetch_product_detail

        with pytest.raises(TypeError):
            await fetch_product_detail(transport, 1)  # type: ignore[call-arg]
        await transport.aclose()

    asyncio.run(_run())


def test_cli_requires_api_base_before_network(monkeypatch):
    """Missing --api-base exits via argparse before any scan/network."""
    from scripts import build_fast_image_coverage_baseline as cli

    network_calls: list[str] = []

    async def fake_run_scan(**kwargs):  # type: ignore[no-untyped-def]
        network_calls.append("run_scan")
        raise AssertionError("run_scan must not be reached without --api-base")

    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    with pytest.raises(SystemExit) as ei:
        cli.main([])
    assert ei.value.code == 2  # argparse error
    assert network_calls == []

    with pytest.raises(SystemExit) as ei2:
        cli._build_parser().parse_args([])
    assert ei2.value.code == 2
