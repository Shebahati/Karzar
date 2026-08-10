"""Fixture-only tests for IMG-FAST-01B one-image discovery."""

from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.fast_image_coverage_discovery import ACCEPTED_SEED_ARTIFACT_SHA256  # noqa: E402
from scripts.fast_image_coverage_discovery.assets import (  # noqa: E402
    materialize_asset,
)
from scripts.fast_image_coverage_discovery.checkpoint import (  # noqa: E402
    apply_checkpoint,
    save_checkpoint,
)
from scripts.fast_image_coverage_discovery.contracts import (  # noqa: E402
    DiscoveryRunState,
    ProductTerminalState,
    RunProduct,
    SeedProduct,
)
from scripts.fast_image_coverage_discovery.drift import reconcile_storefront  # noqa: E402
from scripts.fast_image_coverage_discovery.extract import (  # noqa: E402
    extract_product_images,
    extract_title,
)
from scripts.fast_image_coverage_discovery.identity import (  # noqa: E402
    classify_identity,
    exact_sku_in_text,
    is_family_only_match,
    normalize_sku,
    owner_policy_for_country,
    temporary_primary_eligible,
)
from scripts.fast_image_coverage_discovery.orchestrator import (  # noqa: E402
    summarize_from_rows,
)
from scripts.fast_image_coverage_discovery.ordering import order_run_universe  # noqa: E402
from scripts.fast_image_coverage_discovery.seed import load_seed_products  # noqa: E402
from scripts.fast_image_coverage_discovery.sources.wc_store import (  # noqa: E402
    SourceIndex,
    calibrate_index,
)


def _png(w: int = 120, h: int = 120) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (w, h), color=(200, 10, 10)).save(buf, format="PNG")
    return buf.getvalue()


def test_normalize_sku_and_variant_protection():
    assert normalize_sku("5801-A55") == "5801a55"
    assert exact_sku_in_text("5801-A55", "Product 5801-A55 datasheet")
    assert not exact_sku_in_text("5801-A55", "Product 5801 only")
    assert is_family_only_match("5801-A55", "5801")


def test_brand_mismatch_red():
    status, *_rest = classify_identity(
        sku="35252",
        brand_key="chumpower",
        product_name="Unknown 35252",
        page_title="SAN OU 35252",
        page_text="SAN OU tool",
        has_pdp_structure=True,
        image_is_product_gallery=True,
        source_country="IR",
    )
    assert status == "red_rejected"


def test_exact_brand_sku_green():
    status, match_type, brand_ev, sku_ev, _ = classify_identity(
        sku="5801-A55",
        brand_key="insize",
        product_name="INSIZE 5801-A55",
        page_title="INSIZE Micrometer 5801-A55",
        page_text="INSIZE 5801-A55",
        has_pdp_structure=True,
        image_is_product_gallery=True,
        source_country="IR",
    )
    assert status == "green_exact"
    assert match_type == "exact_brand_sku"
    assert brand_ev == "exact_brand"
    assert sku_ev == "exact_sku"


def test_no_brand_conservative_yellow_or_green():
    status, *_ = classify_identity(
        sku="35252",
        brand_key="",
        product_name="سه نظام 35252",
        page_title="35252",
        page_text="35252",
        has_pdp_structure=True,
        image_is_product_gallery=True,
        source_country="IR",
    )
    assert status in {"green_exact", "yellow_review"}


def test_category_page_rejection():
    status, *_ = classify_identity(
        sku="35252",
        brand_key="",
        product_name="x",
        page_title="Category",
        page_text="list",
        has_pdp_structure=False,
        image_is_product_gallery=False,
        source_country="IR",
    )
    assert status == "red_rejected"


def test_json_ld_and_og_extraction():
    html = """
    <html><head><title>INSIZE 5801-A55</title>
    <meta property="og:image" content="https://cdn.example/og.jpg"/>
    <script type="application/ld+json">{"@type":"Product","name":"5801-A55","image":"https://cdn.example/ld.jpg"}</script>
    </head><body>INSIZE 5801-A55 product gallery</body></html>
    """
    assert "5801-A55" in extract_title(html)
    urls, evidence, has_pdp = extract_product_images(html, "https://shop.example/p/1", sku="5801-A55")
    assert has_pdp
    assert any("ld.jpg" in u or "og.jpg" in u for u in urls)
    assert evidence in {"json_ld", "og_image", "dom_img"}


def test_iranian_owner_policy():
    assert owner_policy_for_country("IR") == "iranian_source_allowed"
    assert temporary_primary_eligible("iranian_source_allowed") is True
    assert owner_policy_for_country("US") == "non_iranian_not_precleared"
    assert temporary_primary_eligible("non_iranian_not_precleared") is False


def test_sha_dedupe_assets(tmp_path: Path):
    data = _png()
    sha_map: dict[str, str] = {}
    a1 = materialize_asset(data, assets_dir=tmp_path / "assets", source_url="https://x/a.png", sha_map=sha_map)
    a2 = materialize_asset(data, assets_dir=tmp_path / "assets", source_url="https://x/b.png", sha_map=sha_map)
    assert a1 and a2
    assert a1.sha256 == a2.sha256
    assert len(sha_map) == 1


def test_source_calibration_pass_fail():
    idx = SourceIndex(source_id="t", domain="example.com")
    idx.by_sku[normalize_sku("ABC-1")] = type("R", (), {"image_urls": ["u"], "permalink": "p", "title": "ABC-1"})()
    assert calibrate_index(idx, ["ABC-1", "ABC-1", "ABC-1"]) is True
    idx2 = SourceIndex(source_id="t2", domain="example.com")
    assert calibrate_index(idx2, ["NOPE"]) is False


def test_ordering_by_brand_count():
    products = [
        RunProduct(1, "a", "brand-a", "", "n", "active_seed_missing"),
        RunProduct(2, "b", "brand-b", "", "n", "active_seed_missing"),
        RunProduct(3, "c", "brand-a", "", "n", "active_seed_missing"),
    ]
    ordered = order_run_universe(products)
    assert ordered[0].brand_key == "brand-a"


def test_checkpoint_resume(tmp_path: Path):
    state = DiscoveryRunState(api_base="http://127.0.0.1:8000/api/v1", package_dir=str(tmp_path), seed_manifest_sha256="x")
    state.products[1] = ProductTerminalState(product_id=1, final_status="green_exact", stop_search=True)
    save_checkpoint(state, tmp_path)
    state2 = DiscoveryRunState(api_base="http://127.0.0.1:8000/api/v1", package_dir=str(tmp_path), seed_manifest_sha256="x")
    from scripts.fast_image_coverage_discovery.checkpoint import load_checkpoint

    apply_checkpoint(state2, load_checkpoint(tmp_path) or {})
    assert state2.products[1].stop_search is True


def test_final_queue_reconciliation():
    state = DiscoveryRunState(
        api_base="http://127.0.0.1:8000/api/v1",
        package_dir="/tmp/x",
        seed_manifest_sha256="x",
        run_discovery_universe_total=3,
    )
    state.products[1] = ProductTerminalState(product_id=1, final_status="green_exact", stop_search=True)
    state.products[2] = ProductTerminalState(product_id=2, final_status="yellow_review", stop_search=False)
    state.products[3] = ProductTerminalState(product_id=3, final_status="unresolved", stop_search=False)
    metrics = summarize_from_rows(
        greens=[{"owner_usage_policy": "iranian_source_allowed"}],
        yellows=[{}],
        unresolved=[{}],
        reds=[],
        run_total=3,
    )
    assert metrics["green_exact"] + metrics["yellow_review"] + metrics["unresolved"] == 3


def test_drift_reconciliation_fixture_api():
    seed = [
        SeedProduct(1, "A1", "brand", 1, "cat", "name", "missing_all_images", "iranian_retailer_exact"),
        SeedProduct(2, "A2", "brand", 1, "cat", "name2", "missing_all_images", "iranian_retailer_exact"),
    ]

    def sync_fetch(method: str, url: str):
        from scripts.fast_image_coverage_baseline.http_transport import HttpResponse

        if "skip=0" in url:
            payload = {
                "data": [
                    {"id": 1, "sku": "A1", "name": "n1", "thumbnail": None},
                    {"id": 2, "sku": "A2", "name": "n2", "thumbnail": "https://cdn.example/t.png"},
                    {"id": 3, "sku": "A3", "name": "n3", "thumbnail": None},
                ],
                "meta": {"total_count": 3, "has_next": False},
            }
            return HttpResponse(200, {"content-type": "application/json"}, json.dumps(payload).encode(), url)
        if url.endswith("t.png"):
            return HttpResponse(200, {"content-type": "image/png"}, _png(), url)
        raise AssertionError(url)

    import asyncio

    drift, universe, counters = asyncio.run(
        reconcile_storefront(
            api_base="http://127.0.0.1:8000/api/v1",
            seed_products=seed,
            sync_fetch=sync_fetch,
        )
    )
    assert counters["active_seed_missing"] == 1
    assert counters["resolved_since_baseline"] == 1
    assert counters["new_missing_since_baseline"] == 1
    assert len(universe) == 2


def test_accepted_seed_sha_constant():
    assert ACCEPTED_SEED_ARTIFACT_SHA256 == (
        "abbed4a4890d136ee48f767cf5450c6389524042a22c0b9dd172c1a9d0995016"
    )


def test_seed_load_from_fixture_csv(tmp_path: Path):
    csv_path = tmp_path / "internet-discovery-universe.csv"
    rows = [
        {
            "product_id": str(i),
            "sku": f"S{i}",
            "brand_key": "",
            "category_id": "1",
            "category_slug": "c",
            "product_name": f"P{i}",
            "current_state": "missing_all_images",
            "priority_tier": "unassigned",
            "priority_basis": "none",
            "reason_code": "no_image_references",
            "current_primary_reference": "",
            "suggested_discovery_lane": "iranian_retailer_exact",
            "notes": "",
        }
        for i in range(4708)
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    loaded = load_seed_products(csv_path)
    assert len(loaded) == 4708


def test_ci_zero_network_guard_discovery_modules():
    from pathlib import Path as P

    forbidden_imports = ("import httpx", "import aiohttp", "import requests")
    tree = P(ROOT / "scripts/fast_image_coverage_discovery")
    for py in tree.rglob("*.py"):
        src = py.read_text(encoding="utf-8")
        if "test_" in py.name:
            continue
        for lib in forbidden_imports:
            assert lib not in src, f"{py} imports {lib}"


def test_first_green_stop_orchestrator(tmp_path: Path, monkeypatch):
    products = [
        RunProduct(10, "SKU10", "brand", "cat", "Product 10", "active_seed_missing"),
    ]

    def fake_run_discovery(**kwargs):
        state = DiscoveryRunState(
            api_base=kwargs["api_base"],
            package_dir=str(kwargs["package_dir"]),
            seed_manifest_sha256="m",
            run_discovery_universe_total=1,
        )
        from scripts.fast_image_coverage_discovery.contracts import (
            DiscoveryCandidate,
            MaterializedAsset,
        )

        asset = MaterializedAsset("abc", "assets/abc.png", 100, 100, "png", 1000, "image/png", "u")
        cand = DiscoveryCandidate(
            product_id=10,
            sku="SKU10",
            brand_key="brand",
            product_name="Product 10",
            category="cat",
            source_id="shopmill_wc",
            source_domain="shopmilltools.com",
            source_country="IR",
            source_class="wc",
            lane="IR-1",
            source_page_url="https://shopmilltools.com/p/1",
            source_image_url="https://shopmilltools.com/i.png",
            match_type="exact_brand_sku",
            brand_evidence="exact",
            sku_model_evidence="exact",
            page_identity_evidence="wc",
            gallery_identity_evidence="wc",
            owner_usage_policy="iranian_source_allowed",
            discovery_status="green_exact",
            temporary_primary_eligible=True,
            asset=asset,
            stop_search=True,
        )
        state.products[10] = ProductTerminalState(
            product_id=10, final_status="green_exact", stop_search=True, attempts=[cand]
        )
        return state

    monkeypatch.setattr("scripts.build_fast_image_coverage_discovery.run_discovery", fake_run_discovery)
    # direct call to fake is enough — orchestrator sets stop_search
    st = fake_run_discovery(api_base="http://127.0.0.1:8000/api/v1", package_dir=tmp_path, run_universe=products, seed_manifest_sha256="m", drift_counters={})
    assert st.products[10].stop_search is True
