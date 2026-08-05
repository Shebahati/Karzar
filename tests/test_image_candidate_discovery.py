"""Focused fixture tests for IMG-02B candidate discovery (no live network)."""

from __future__ import annotations

import csv
import hashlib
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from image_candidate_discovery import CandidateDiscoveryError  # noqa: E402
from image_candidate_discovery.consolidate import (  # noqa: E402
    MANUAL_FIELDS,
    consolidate_lane_outputs,
)
from image_candidate_discovery.core import run_lane_candidate_discovery  # noqa: E402
from image_candidate_discovery.output import assert_external_output  # noqa: E402
from image_candidate_discovery.providers.dasqua_official import (  # noqa: E402
    allow_dasqua_image_url,
    discover_dasqua_candidates,
    extract_exact_item_code,
    extract_image,
    extract_primary_code,
    family_code,
    governed_sku,
    normalize_dasqua_code,
)
from image_candidate_discovery.providers.insize_tosag import (  # noqa: E402
    extract_primary_image,
    extract_search_product_links,
    sku_search_variants,
    sku_token_present,
)
from image_candidate_discovery.providers.sanou_official import (  # noqa: E402
    _resolve_one,
    extract_model_tokens,
)
from image_candidate_discovery.reconcile_insize import (  # noqa: E402
    apply_insize_reconciliation,
    reconcile_insize_candidate_runs,
)
from image_candidate_discovery.sanou_calibrate import (  # noqa: E402
    calibrate_sanou_site_shape,
)
from image_candidate_discovery.transport import HostThrottledFetcher  # noqa: E402
from image_discovery.sources import get_adapter  # noqa: E402
from image_discovery.sources.dasqua_official import DasquaOfficialAdapter  # noqa: E402
from image_discovery.sources.sanou_official import SanouOfficialAdapter  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class RecordingUrlOpen:
    def __init__(self, mapping: dict[str, dict]) -> None:
        self.mapping = mapping
        self.calls: list[str] = []

    def __call__(self, req, timeout):  # noqa: ANN001
        url = req.full_url if hasattr(req, "full_url") else req.get_full_url()
        self.calls.append(url)
        # match by prefix / exact
        entry = None
        for key, val in self.mapping.items():
            if url == key or url.startswith(key):
                entry = val
                break
        if entry is None:
            raise OSError(f"unexpected URL {url}")

        class Resp:
            def __init__(self, body: bytes, status: int, ctype: str, final: str) -> None:
                self._body = body
                self.status = status
                self.headers = {"Content-Type": ctype, "Content-Length": str(len(body))}
                self._final = final

            def read(self, n: int = -1) -> bytes:
                if n < 0:
                    out, self._body = self._body, b""
                    return out
                out, self._body = self._body[:n], self._body[n:]
                return out

            def getcode(self) -> int:
                return self.status

            def geturl(self) -> str:
                return self._final

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        return Resp(
            entry.get("body", b""),
            entry.get("status", 200),
            entry.get("ctype", "text/html"),
            entry.get("final", url),
        )


def test_host_allowlist_and_redirect_rejection():
    opener = RecordingUrlOpen(
        {
            "https://www.dasquatools.com/ok": {
                "body": b"ok",
                "ctype": "text/html",
                "final": "https://evil.example/steal",
            }
        }
    )
    fetcher = HostThrottledFetcher(
        allowed_hosts=frozenset({"www.dasquatools.com"}),
        delay=0,
        urlopen=opener,
    )
    from image_discovery.contracts import DiscoveryError

    with pytest.raises(DiscoveryError, match="allowlisted|cross_host"):
        fetcher.get("https://www.dasquatools.com/ok", fail_code="x")


def test_dasqua_code_and_image_extraction():
    assert governed_sku("4111-8105A") == "4111-8105A"
    assert family_code("4111-8105A") == "4111-8105"
    assert normalize_dasqua_code("1804-1405A") == "1804-1405"
    html = (
        "<title>Dasqua 1804-1405 Digital Caliper</title>"
        '<meta property="og:image" content="https://www.dasquatools.com/image_product/x.jpg">'
    )
    assert extract_primary_code("Dasqua 1804-1405 Digital Caliper", "https://www.dasquatools.com/p", html) == "1804-1405"
    parent = "https://www.dasquatools.com/p/1804-1405"
    assert extract_image(html, parent_detail_url=parent) == "https://www.dasquatools.com/image_product/x.jpg"
    cdn_html = (
        "<title>DASQUA 2115-2305 Caliper</title>"
        '<meta property="og:image" content="https://ecdn6.globalso.com/upload/p/565/image_product/2024-04/x.jpg">'
    )
    assert (
        extract_image(cdn_html, parent_detail_url=parent)
        == "https://ecdn6.globalso.com/upload/p/565/image_product/2024-04/x.jpg"
    )


def test_dasqua_exact_suffixed_sku_preservation():
    assert governed_sku("4111-8105") == "4111-8105"
    assert governed_sku("4111-8105A") == "4111-8105A"
    assert governed_sku("4111-8105") != governed_sku("4111-8105A")
    html = (
        "<title>Dasqua 4111-8105A Dial Indicator</title>"
        "<body>Item Number: 4111-8105A Dasqua</body>"
    )
    exact = extract_exact_item_code(
        "Dasqua 4111-8105A Dial Indicator",
        "https://www.dasquatools.com/dasqua-4111-8105a-indicator",
        html,
    )
    assert exact == "4111-8105A"
    assert family_code(exact) == "4111-8105"


def test_dasqua_cdn_child_without_parent_rejected():
    cdn = "https://ecdn6.globalso.com/upload/p/565/image_product/2024-04/x.jpg"
    assert not allow_dasqua_image_url(cdn, parent_detail_url="https://evil.example/p")
    assert not allow_dasqua_image_url(
        cdn, parent_detail_url="https://cdn.globalso.com/index"
    )
    assert allow_dasqua_image_url(
        cdn, parent_detail_url="https://www.dasquatools.com/product/x"
    )
    # Unobserved ecdnN host is not pre-authorized.
    assert not allow_dasqua_image_url(
        "https://ecdn3.globalso.com/upload/p/x.jpg",
        parent_detail_url="https://www.dasquatools.com/product/x",
    )


def test_insize_helpers():
    assert sku_token_present("SKU 1120-500 on page", "1120-500")
    assert not sku_token_present("1120-5000 wrong", "1120-500")
    assert "1120-500" in sku_search_variants("1120-500")
    html = (
        '<div class="productbox-title"><a href="https://www.tosag.ch/insize-caliper">'
        "x</a></div>"
    )
    assert extract_search_product_links(html) == ["https://www.tosag.ch/insize-caliper"]
    img_html = 'https://www.tosag.ch/media/image/product/1/lg/abc.jpg'
    assert extract_primary_image(img_html) == "https://www.tosag.ch/media/image/product/1/lg/abc.jpg"


def test_sanou_model_tokens():
    tokens = extract_model_tokens("فک رو K12-160 EXTERNAL -JAWS سانو (SAN OU)")
    assert "K12-160" in tokens


def test_adapters_registered():
    assert get_adapter("dasqua_official").name == "dasqua_official"
    assert get_adapter("insize_tosag").name == "insize_tosag"
    assert get_adapter("sanou_official").name == "sanou_official"


def test_sanou_validate_page():
    adapter = SanouOfficialAdapter()
    adapter._sku_models["SO-336"] = ["K12-160"]
    html = (
        "<html><title>K12-160 Chuck SAN OU</title>"
        "<body>Manufacturer: SAN OU model K12-160</body></html>"
    )
    ev = adapter.validate_page(
        sku="SO-336",
        page_html=html,
        detail_url="https://en.sanouchuck.com/p/k12-160",
    )
    assert ev.manufacturer_confirmed and ev.sku_confirmed


def test_dasqua_validate_page_accept_and_reject_family():
    adapter = DasquaOfficialAdapter()
    good = (
        "<html><head><title>Dasqua 1804-1405 Caliper</title></head>"
        "<body>Item Number: 1804-1405 Dasqua official</body></html>"
    )
    ev = adapter.validate_page(
        sku="1804-1405",
        page_html=good,
        detail_url="https://www.dasquatools.com/p/1804-1405",
    )
    assert ev.sku_confirmed and ev.manufacturer_confirmed

    family = (
        "<html><head><title>Dasqua Family Kit</title></head>"
        "<body>Item Number: 1804-1405 Item Number: 1804-1505 Dasqua</body></html>"
    )
    ev2 = adapter.validate_page(
        sku="1804-1405",
        page_html=family,
        detail_url="https://www.dasquatools.com/family",
    )
    assert not ev2.sku_confirmed
    assert ev2.reason_code == "family_page_ambiguous"

def test_candidate_id_determinism():
    from image_candidate_discovery.output import stable_candidate_id

    a = stable_candidate_id(["IMG-02B-02", "1", "sku", "u1", "i1"])
    b = stable_candidate_id(["IMG-02B-02", "1", "sku", "u1", "i1"])
    assert a == b and len(a) == 64


def test_output_root_must_be_external(tmp_path: Path):
    with pytest.raises(CandidateDiscoveryError, match="outside repository"):
        assert_external_output(REPO / "should-fail", REPO)


def test_insize_lane_mocked_discovery(tmp_path: Path):
    # Minimal worklist root with checksums
    root = tmp_path / "wl"
    root.mkdir()
    # Build tiny brand worklist + all required checksum members as stubs
    fields = [
        "schema_version",
        "task_id",
        "work_item_id",
        "product_key",
        "product_id",
        "sku",
        "product_name",
        "brand_key",
        "brand_name",
        "category_name",
        "work_type",
        "work_reasons",
        "priority",
        "active",
        "available",
        "current_image_id",
        "current_asset_id",
        "source_assignment_id",
        "review_batch_id",
        "review_decision",
        "suitability_status",
        "has_third_party_watermark",
        "rights_status",
        "source_adapter_candidate",
        "source_class",
        "eligible_for_automatic_discovery",
        "status",
        "notes",
    ]
    row = {
        "schema_version": "1",
        "task_id": "IMG-02B",
        "work_item_id": "a" * 64,
        "product_key": "product_id:9",
        "product_id": "9",
        "sku": "1120-500",
        "product_name": "INSIZE caliper",
        "brand_key": "insize",
        "brand_name": "INSIZE",
        "category_name": "c",
        "work_type": "missing_image",
        "work_reasons": "missing_image",
        "priority": "P0",
        "active": "true",
        "available": "true",
        "current_image_id": "",
        "current_asset_id": "",
        "source_assignment_id": "",
        "review_batch_id": "",
        "review_decision": "",
        "suitability_status": "",
        "has_third_party_watermark": "false",
        "rights_status": "review_required",
        "source_adapter_candidate": "insize_tosag",
        "source_class": "authorized_distributor_candidate",
        "eligible_for_automatic_discovery": "true",
        "status": "queued",
        "notes": "",
    }
    for name in (
        "worklist-all.csv",
        "worklist-dasqua.csv",
        "worklist-insize.csv",
        "worklist-san-ou.csv",
        "manual-review-hold.csv",
    ):
        with (root / name).open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            if name in {"worklist-all.csv", "worklist-insize.csv"}:
                w.writerow(row)
    (root / "source-path-contract.json").write_text("{}\n", encoding="utf-8")
    (root / "input-evidence.json").write_text("{}\n", encoding="utf-8")
    (root / "summary.json").write_text("{}\n", encoding="utf-8")
    (root / "README.md").write_text("x\n", encoding="utf-8")
    lines = []
    for name in [
        "worklist-all.csv",
        "worklist-dasqua.csv",
        "worklist-insize.csv",
        "worklist-san-ou.csv",
        "manual-review-hold.csv",
        "source-path-contract.json",
        "input-evidence.json",
        "summary.json",
        "README.md",
    ]:
        lines.append(f"{_sha((root / name).read_bytes())}  {name}")
    (root / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")

    search_html = (
        b'<div class="productbox-title"><a href="https://www.tosag.ch/insize-1120-500">'
        b"INSIZE</a></div>"
    )
    detail_html = (
        b"<html><body>Manufacturers: Insize "
        b'data-sku-0="1120-500" '
        b"https://www.tosag.ch/media/image/product/1/lg/x.jpg"
        b"</body></html>"
    )
    opener = RecordingUrlOpen(
        {
            "https://www.tosag.ch/?suche=": {
                "body": search_html,
                "ctype": "text/html",
                "final": "https://www.tosag.ch/?suche=1120-500&lang=eng",
            },
            "https://www.tosag.ch/insize-1120-500": {
                "body": detail_html,
                "ctype": "text/html",
                "final": "https://www.tosag.ch/insize-1120-500?lang=eng",
            },
        }
    )
    fetcher = HostThrottledFetcher(
        allowed_hosts=frozenset({"www.tosag.ch", "tosag.ch"}),
        delay=0,
        urlopen=opener,
    )
    out = tmp_path / "out-insize"
    result = run_lane_candidate_discovery(
        lane="insize",
        worklist_root=root,
        output_dir=out,
        repo_root=REPO,
        concurrency=1,
        delay=0,
        fetcher=fetcher,
    )
    assert result["candidate_count"] == 1
    rows = list(csv.DictReader((out / "candidate-input.csv").open(encoding="utf-8")))
    assert rows[0]["rights_status"] == "review_required"
    assert rows[0]["apply_status"] == "not_started"
    assert rows[0]["source_image_url"].endswith(".jpg")


def test_no_db_imports_in_candidate_discovery_package():
    root = REPO / "scripts" / "image_candidate_discovery"
    banned = ("from sqlalchemy", "import sqlalchemy", "from app.db", "import app.db", "ProductImage")
    for path in root.rglob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for needle in banned:
                if stripped.startswith(needle) or (
                    needle == "ProductImage" and "import" in stripped and "ProductImage" in stripped
                ):
                    raise AssertionError(f"{path}: {stripped}")


def test_dasqua_majority_vote_removed_and_family_collision():
    sitemap = (
        b'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        b"<url><loc>https://www.dasquatools.com/p-a</loc></url>"
        b"<url><loc>https://www.dasquatools.com/p-b</loc></url>"
        b"</urlset>"
    )
    page_a = (
        b"<html><head><title>Dasqua 1804-1405 Caliper</title>"
        b'<meta property="og:image" content="https://www.dasquatools.com/image_product/a.jpg">'
        b"</head><body>Item Number: 1804-1405 Dasqua</body></html>"
    )
    page_b = (
        b"<html><head><title>Dasqua 1804-1405 Caliper Alt</title>"
        b'<meta property="og:image" content="https://www.dasquatools.com/image_product/b.jpg">'
        b"</head><body>Item Number: 1804-1405 Dasqua</body></html>"
    )
    opener = RecordingUrlOpen(
        {
            "https://www.dasquatools.com/product_sitemap.xml": {
                "body": sitemap,
                "ctype": "application/xml",
            },
            "https://www.dasquatools.com/product_2_sitemap.xml": {
                "body": b'<?xml version="1.0"?><urlset></urlset>',
                "ctype": "application/xml",
            },
            "https://www.dasquatools.com/product_3_sitemap.xml": {
                "body": b'<?xml version="1.0"?><urlset></urlset>',
                "ctype": "application/xml",
            },
            "https://www.dasquatools.com/p-a": {"body": page_a, "ctype": "text/html"},
            "https://www.dasquatools.com/p-b": {"body": page_b, "ctype": "text/html"},
        }
    )
    fetcher = HostThrottledFetcher(
        allowed_hosts=frozenset({"www.dasquatools.com", "dasquatools.com"}),
        delay=0,
        urlopen=opener,
    )
    result = discover_dasqua_candidates(
        [
            {
                "product_id": "1",
                "sku": "1804-1405",
                "product_name": "caliper",
                "product_key": "product_id:1",
                "work_type": "replace_required",
                "work_reasons": "replace_required:IMG-02A-02-BATCH-002",
                "priority": "P0",
            }
        ],
        fetcher=fetcher,
        concurrency=1,
    )
    assert result["candidates"] == []
    assert any(m["reason_code"] == "ambiguous_official_product" for m in result["manual"])
    man = next(m for m in result["manual"] if m["reason_code"] == "ambiguous_official_product")
    assert man["discovery_status"] == "manual_review"
    assert man["eligible_for_automatic_discovery"] == "false"
    assert man["product_key"] == "product_id:1"
    assert man["work_type"] == "replace_required"
    assert man["work_reasons"] == "replace_required:IMG-02A-02-BATCH-002"
    assert man["priority"] == "P0"


def test_dasqua_adapter_consistency_rejects_family_html():
    family_html = (
        "<html><head><title>Dasqua 1804-1405 Family Kit</title></head>"
        "<body>Item Number: 1804-1405 Item Number: 1804-1505 Dasqua</body></html>"
    )
    sitemap = (
        b'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        b"<url><loc>https://www.dasquatools.com/family</loc></url>"
        b"</urlset>"
    )
    page = (
        family_html.encode()
        + b'<meta property="og:image" content="https://www.dasquatools.com/image_product/x.jpg">'
    )
    opener = RecordingUrlOpen(
        {
            "https://www.dasquatools.com/product_sitemap.xml": {
                "body": sitemap,
                "ctype": "application/xml",
            },
            "https://www.dasquatools.com/product_2_sitemap.xml": {
                "body": b'<?xml version="1.0"?><urlset></urlset>',
                "ctype": "application/xml",
            },
            "https://www.dasquatools.com/product_3_sitemap.xml": {
                "body": b'<?xml version="1.0"?><urlset></urlset>',
                "ctype": "application/xml",
            },
            "https://www.dasquatools.com/family": {"body": page, "ctype": "text/html"},
        }
    )
    fetcher = HostThrottledFetcher(
        allowed_hosts=frozenset({"www.dasquatools.com", "dasquatools.com"}),
        delay=0,
        urlopen=opener,
    )
    result = discover_dasqua_candidates(
        [{"product_id": "1", "sku": "1804-1405", "product_name": "x", "product_key": "p:1"}],
        fetcher=fetcher,
        concurrency=1,
    )
    assert result["candidates"] == []
    # Family-ambiguous extract → manual, or adapter reject if somehow unambiguous.
    assert result["manual"] or any(
        r["reason_code"] == "family_page_ambiguous" for r in result["rejected"]
    )


def test_dasqua_base_family_does_not_auto_match_suffix_sibling():
    """4111-8105A page must not auto-accept governed 4111-8105."""
    sitemap = (
        b'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        b"<url><loc>https://www.dasquatools.com/dasqua-4111-8105a</loc></url>"
        b"</urlset>"
    )
    page = (
        b"<html><head><title>Dasqua 4111-8105A Indicator</title>"
        b'<meta property="og:image" content="https://www.dasquatools.com/image_product/a.jpg">'
        b"</head><body>Item Number: 4111-8105A Dasqua</body></html>"
    )
    opener = RecordingUrlOpen(
        {
            "https://www.dasquatools.com/product_sitemap.xml": {
                "body": sitemap,
                "ctype": "application/xml",
            },
            "https://www.dasquatools.com/product_2_sitemap.xml": {
                "body": b'<?xml version="1.0"?><urlset></urlset>',
                "ctype": "application/xml",
            },
            "https://www.dasquatools.com/product_3_sitemap.xml": {
                "body": b'<?xml version="1.0"?><urlset></urlset>',
                "ctype": "application/xml",
            },
            "https://www.dasquatools.com/dasqua-4111-8105a": {
                "body": page,
                "ctype": "text/html",
            },
        }
    )
    fetcher = HostThrottledFetcher(
        allowed_hosts=frozenset({"www.dasquatools.com", "dasquatools.com"}),
        delay=0,
        urlopen=opener,
    )
    result = discover_dasqua_candidates(
        [
            {
                "product_id": "1",
                "sku": "4111-8105",
                "product_name": "base",
                "product_key": "p:1",
            },
            {
                "product_id": "2",
                "sku": "4111-8105A",
                "product_name": "suffix",
                "product_key": "p:2",
            },
        ],
        fetcher=fetcher,
        concurrency=1,
    )
    skus = {c["sku"] for c in result["candidates"]}
    assert "4111-8105A" in skus
    assert "4111-8105" not in skus
    assert result["stats"]["exact_suffix_collisions"] >= 2


def test_sanou_model_token_not_found_is_manual():
    fetcher = HostThrottledFetcher(
        allowed_hosts=frozenset({"en.sanouchuck.com"}),
        delay=0,
        urlopen=RecordingUrlOpen({}),
    )
    cand, rej, man = _resolve_one(
        {
            "product_id": "9",
            "sku": "SO-1",
            "product_name": "فک جانبی بدون مدل",
            "product_key": "product_id:9",
            "work_type": "missing_image",
            "work_reasons": "missing_image",
            "priority": "P0",
        },
        fetcher=fetcher,
    )
    assert cand is None and rej is None and man is not None
    assert man["reason_code"] == "model_token_not_found"
    assert man["discovery_status"] == "manual_review"
    assert man["eligible_for_automatic_discovery"] == "false"
    assert man["work_type"] == "missing_image"
    assert man["priority"] == "P0"


def test_sanou_parser_drift_vs_official_page_not_found():
    opener = RecordingUrlOpen(
        {
            "https://en.sanouchuck.com/product.aspx?keyword=K12-160": {
                "body": b"<html><title>Search</title><body>K12-160 SAN OU listing shell</body></html>",
                "ctype": "text/html",
            },
            "https://en.sanouchuck.com/search.aspx?key=K12-160": {
                "body": b"<html><title>Search</title><body>K12-160 SAN OU listing shell</body></html>",
                "ctype": "text/html",
            },
        }
    )
    fetcher = HostThrottledFetcher(
        allowed_hosts=frozenset(
            {"www.sanouchuck.com", "sanouchuck.com", "en.sanouchuck.com"}
        ),
        delay=0,
        urlopen=opener,
    )
    cand, rej, man = _resolve_one(
        {
            "product_id": "1",
            "sku": "SO-336",
            "product_name": "فک رو K12-160 EXTERNAL سانو (SAN OU)",
            "product_key": "p:1",
        },
        fetcher=fetcher,
    )
    assert cand is None and man is None and rej is not None
    assert rej["reason_code"] == "parser_drift"
    assert rej["reason_code"] != "official_page_not_found"


def test_sanou_bounded_site_shape_calibration():
    opener = RecordingUrlOpen(
        {
            "https://en.sanouchuck.com/robots.txt": {
                "body": b"User-agent: *\nDisallow:\n",
                "ctype": "text/plain",
            },
            "https://www.sanouchuck.com/robots.txt": {
                "body": b"User-agent: *\nDisallow:\n",
                "ctype": "text/plain",
            },
            "https://en.sanouchuck.com/sitemap.xml": {
                "body": b"<urlset></urlset>",
                "ctype": "application/xml",
            },
            "https://www.sanouchuck.com/sitemap.xml": {
                "body": b"<urlset></urlset>",
                "ctype": "application/xml",
            },
            "https://en.sanouchuck.com/": {
                "body": b"<html><title>SAN OU</title><a href='/download.aspx'>d</a></html>",
                "ctype": "text/html",
            },
            "https://www.sanouchuck.com/": {
                "body": b"<html><title>SAN OU CN</title></html>",
                "ctype": "text/html",
            },
            "https://en.sanouchuck.com/download.aspx": {
                "body": b"<html><title>Download</title><body>catalog pdf</body></html>",
                "ctype": "text/html",
            },
            "https://www.sanouchuck.com/download.aspx": {
                "body": b"<html><title>Download</title></html>",
                "ctype": "text/html",
            },
            "https://en.sanouchuck.com/product.aspx": {
                "body": b"<html><title>Products</title></html>",
                "ctype": "text/html",
            },
            "https://en.sanouchuck.com/product-n.aspx": {
                "body": b"<html><title>Products N</title></html>",
                "ctype": "text/html",
            },
        }
    )
    fetcher = HostThrottledFetcher(
        allowed_hosts=frozenset(
            {"www.sanouchuck.com", "sanouchuck.com", "en.sanouchuck.com"}
        ),
        delay=0,
        urlopen=opener,
    )
    report = calibrate_sanou_site_shape(
        fetcher=fetcher,
        model_samples=[{"product_id": "1", "sku": "SO-1", "model": "K12-160"}],
        max_model_samples=25,
    )
    assert report["governed_outcome"] in {
        "official_catalog_only",
        "source_unavailable",
        "official_detail_candidate",
    }
    assert report["proven_product_detail_shape"] is False
    assert len(report["calibration_rows"]) >= len(
        [
            "robots",
            "sitemap",
            "homepage",
            "download",
        ]
    )


def test_sanou_catalog_only_manual_path():
    search = (
        b"<html><body>K12-160 SAN OU "
        b'<a href="https://en.sanouchuck.com/productshow.aspx?id=1">detail</a>'
        b"</body></html>"
    )
    detail = (
        b"<html><body>SAN OU manufacturer K12-160 "
        b'<img src="/images/banner/pl1.jpg">'
        b"</body></html>"
    )
    opener = RecordingUrlOpen(
        {
            "https://en.sanouchuck.com/product.aspx?keyword=K12-160": {
                "body": search,
                "ctype": "text/html",
            },
            "https://en.sanouchuck.com/productshow.aspx?id=1": {
                "body": detail,
                "ctype": "text/html",
            },
        }
    )
    fetcher = HostThrottledFetcher(
        allowed_hosts=frozenset(
            {"www.sanouchuck.com", "sanouchuck.com", "en.sanouchuck.com"}
        ),
        delay=0,
        urlopen=opener,
    )
    cand, rej, man = _resolve_one(
        {
            "product_id": "1",
            "sku": "SO-336",
            "product_name": "K12-160 EXTERNAL SAN OU",
            "product_key": "p:1",
        },
        fetcher=fetcher,
    )
    assert cand is None and rej is None and man is not None
    assert man["reason_code"] == "official_catalog_only"


def test_insize_drift_and_materialization_reconcile(tmp_path: Path):
    fields = [
        "product_id",
        "sku",
        "source_detail_url",
        "source_image_url",
    ]

    def write_cands(path: Path, rows: list[dict[str, str]]) -> None:
        path.mkdir(parents=True)
        with (path / "candidate-input.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in rows:
                w.writerow(r)

    first = [
        {
            "product_id": "1",
            "sku": "1120-500",
            "source_detail_url": "https://www.tosag.ch/a",
            "source_image_url": "https://www.tosag.ch/i1.jpg",
        },
        {
            "product_id": "2",
            "sku": "1112-150",
            "source_detail_url": "https://www.tosag.ch/b",
            "source_image_url": "https://www.tosag.ch/i2.jpg",
        },
    ]
    second = [
        {
            "product_id": "1",
            "sku": "1120-500",
            "source_detail_url": "https://www.tosag.ch/a-new",
            "source_image_url": "https://www.tosag.ch/i1b.jpg",
        },
        {
            "product_id": "3",
            "sku": "1205-150",
            "source_detail_url": "https://www.tosag.ch/c",
            "source_image_url": "https://www.tosag.ch/i3.jpg",
        },
    ]
    write_cands(tmp_path / "r1", first)
    write_cands(tmp_path / "r2", second)
    mat = tmp_path / "mat" / "manifests"
    mat.mkdir(parents=True)
    with (mat / "manifest.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sku", "sha256"])
        w.writeheader()
        w.writerow({"sku": "1120-500", "sha256": "aa" * 32})
        w.writerow({"sku": "1112-150", "sha256": "aa" * 32})  # family/dup
        w.writerow({"sku": "1205-150", "sha256": "bb" * 32})
    with (mat / "rejected.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sku", "reason_code"])
        w.writeheader()
        w.writerow({"sku": "x", "reason_code": "exact_sku_not_confirmed"})

    report = reconcile_insize_candidate_runs(
        first_run_dir=tmp_path / "r1",
        second_run_dir=tmp_path / "r2",
        materialization_dir=tmp_path / "mat",
        requested=263,
    )
    assert report["first_run_candidates"] == 2
    assert report["second_run_candidates"] == 2
    assert report["removed_candidates"] == ["2"]
    assert report["added_candidates"] == ["3"]
    assert report["source_drift_count"] >= 1
    assert report["sku_1120_500"]["first"]["detail"].endswith("/a")
    assert report["sku_1120_500"]["second"]["detail"].endswith("/a-new")
    assert report["materialization"]["materialized_rows"] == 3
    assert report["materialization"]["unique_assets"] == 2
    assert report["materialization"]["family_group_count"] == 1
    assert "candidate_discovery_coverage_pct" in report["coverage"]
    assert "validated_materialization_coverage_pct" in report["coverage"]


def test_started_at_finished_at_clock_injection(tmp_path: Path):
    fields = [
        "schema_version",
        "task_id",
        "work_item_id",
        "product_key",
        "product_id",
        "sku",
        "product_name",
        "brand_key",
        "brand_name",
        "category_name",
        "work_type",
        "work_reasons",
        "priority",
        "active",
        "available",
        "current_image_id",
        "current_asset_id",
        "source_assignment_id",
        "review_batch_id",
        "review_decision",
        "suitability_status",
        "has_third_party_watermark",
        "rights_status",
        "source_adapter_candidate",
        "source_class",
        "eligible_for_automatic_discovery",
        "status",
        "notes",
    ]
    root = tmp_path / "wl"
    root.mkdir()
    row = {k: "" for k in fields}
    row.update(
        {
            "schema_version": "1",
            "task_id": "IMG-02B",
            "work_item_id": "b" * 64,
            "product_key": "product_id:1",
            "product_id": "1",
            "sku": "SO-1",
            "product_name": "بدون مدل",
            "brand_key": "san_ou",
            "brand_name": "SAN OU",
            "work_type": "missing_image",
            "work_reasons": "missing_image",
            "priority": "P0",
            "active": "true",
            "available": "true",
            "has_third_party_watermark": "false",
            "rights_status": "review_required",
            "source_adapter_candidate": "sanou_official",
            "source_class": "official_manufacturer",
            "eligible_for_automatic_discovery": "false",
            "status": "queued",
        }
    )
    for name in (
        "worklist-all.csv",
        "worklist-dasqua.csv",
        "worklist-insize.csv",
        "worklist-san-ou.csv",
        "manual-review-hold.csv",
    ):
        with (root / name).open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            if name in {"worklist-all.csv", "worklist-san-ou.csv"}:
                w.writerow(row)
    for name in (
        "source-path-contract.json",
        "input-evidence.json",
        "summary.json",
        "README.md",
    ):
        (root / name).write_text("{}\n", encoding="utf-8")
    lines = []
    for name in [
        "worklist-all.csv",
        "worklist-dasqua.csv",
        "worklist-insize.csv",
        "worklist-san-ou.csv",
        "manual-review-hold.csv",
        "source-path-contract.json",
        "input-evidence.json",
        "summary.json",
        "README.md",
    ]:
        lines.append(f"{_sha((root / name).read_bytes())}  {name}")
    (root / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")

    ticks = [
        datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC),
        datetime(2026, 8, 5, 12, 0, 5, tzinfo=UTC),
    ]

    def clock() -> datetime:
        return ticks.pop(0)

    fetcher = HostThrottledFetcher(
        allowed_hosts=frozenset(
            {"www.sanouchuck.com", "sanouchuck.com", "en.sanouchuck.com"}
        ),
        delay=0,
        urlopen=RecordingUrlOpen({}),
    )
    out = tmp_path / "out-sanou"
    result = run_lane_candidate_discovery(
        lane="san_ou",
        worklist_root=root,
        output_dir=out,
        repo_root=REPO,
        concurrency=1,
        delay=0,
        fetcher=fetcher,
        clock=clock,
    )
    summary = result["summary"]
    assert summary["started_at"] <= summary["finished_at"]
    assert summary["elapsed_seconds"] == 5.0
    assert summary["discovered_candidates"] == 0
    assert "validated_candidate_rows" in summary
    assert result["manual_count"] == 1
    man = list(csv.DictReader((out / "manual-review.csv").open(encoding="utf-8")))
    assert man[0]["reason_code"] == "model_token_not_found"


def _write_mini_insize_partition(tmp_path: Path) -> dict[str, Path]:
    """Build a deterministic 49=42+7 / 30=28+2 / 19=14+5 fixture family."""
    import json

    cand_fields = [
        "schema_version",
        "task_id",
        "lane_id",
        "product_id",
        "product_key",
        "sku",
        "product_name",
        "brand_key",
        "work_type",
        "work_reasons",
        "priority",
        "source_adapter",
        "source_class",
        "source_detail_url",
        "source_image_url",
        "source_image_index",
        "candidate_discovery_method",
        "candidate_match_basis",
        "manufacturer_evidence",
        "sku_evidence",
        "confidence",
        "rights_status",
        "apply_status",
        "discovery_status",
        "notes",
    ]

    def cand(pid: int, sku: str, detail: str, image: str) -> dict[str, str]:
        return {
            "schema_version": "1",
            "task_id": "IMG-02B",
            "lane_id": "IMG-02B-03",
            "product_id": str(pid),
            "product_key": f"product_id:{pid}",
            "sku": sku,
            "product_name": f"name-{sku}",
            "brand_key": "insize",
            "work_type": "missing_image",
            "work_reasons": "missing_image",
            "priority": "P0",
            "source_adapter": "insize_tosag",
            "source_class": "authorized_distributor_candidate",
            "source_detail_url": detail,
            "source_image_url": image,
            "source_image_index": "0",
            "candidate_discovery_method": "tosag_search",
            "candidate_match_basis": "exact_sku",
            "manufacturer_evidence": "insize",
            "sku_evidence": sku,
            "confidence": "very_high",
            "rights_status": "review_required",
            "apply_status": "not_started",
            "discovery_status": "candidate_ready",
            "notes": "",
        }

    first = [
        cand(i, f"S-{i}", f"https://www.tosag.ch/d{i}", f"https://www.tosag.ch/i{i}.jpg")
        for i in range(1, 50)
    ]
    second = [
        cand(i, f"S-{i}", f"https://www.tosag.ch/d{i}", f"https://www.tosag.ch/i{i}.jpg")
        for i in range(1, 43)
    ] + [
        cand(
            49,
            "S-49",
            "https://www.tosag.ch/d49-new",
            "https://www.tosag.ch/i49-new.jpg",
        )
    ]
    man_fields = [
        "candidate_id",
        "product_id",
        "product_key",
        "sku",
        "product_name",
        "brand",
        "sha256",
        "local_asset_path",
        "rights_status",
        "review_status",
        "notes",
    ]
    rej_fields = [
        "candidate_id",
        "product_id",
        "product_key",
        "sku",
        "product_name",
        "brand",
        "reason_code",
        "reason_detail",
    ]
    accepted = []
    for i in list(range(1, 29)) + [43, 49]:
        accepted.append(
            {
                "candidate_id": f"c{i}",
                "product_id": str(i),
                "product_key": f"product_id:{i}",
                "sku": f"S-{i}",
                "product_name": f"name-S-{i}",
                "brand": "INSIZE",
                "sha256": f"{i:064x}"[:64],
                "local_asset_path": f"assets/S-{i}.jpg",
                "rights_status": "review_required",
                "review_status": "queued",
                "notes": "",
            }
        )
    rejected = []
    for i in list(range(29, 43)) + [44, 45, 46, 47, 48]:
        rejected.append(
            {
                "candidate_id": f"c{i}",
                "product_id": str(i),
                "product_key": f"product_id:{i}",
                "sku": f"S-{i}",
                "product_name": f"name-S-{i}",
                "brand": "INSIZE",
                "reason_code": "exact_sku_not_confirmed",
                "reason_detail": "x",
            }
        )

    r1 = tmp_path / "first"
    r2 = tmp_path / "second"
    mat = tmp_path / "mat"
    r1.mkdir()
    r2.mkdir()
    (mat / "manifests").mkdir(parents=True)
    for path, rows in ((r1 / "candidate-input.csv", first), (r2 / "candidate-input.csv", second)):
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cand_fields)
            w.writeheader()
            for row in rows:
                w.writerow(row)
    with (mat / "manifests" / "manifest.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=man_fields)
        w.writeheader()
        for row in accepted:
            w.writerow(row)
    with (mat / "manifests" / "rejected.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rej_fields)
        w.writeheader()
        for row in rejected:
            w.writerow(row)
    (r1 / "summary.json").write_text(
        json.dumps(
            {
                "started_at": "2026-08-04T00:00:00+00:00",
                "finished_at": "2026-08-04T00:00:00.000192+00:00",
                "elapsed_seconds": 0.000192,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return {"first": r1, "second": r2, "mat": mat}


def test_apply_insize_reconciliation_partitions_and_quarantines(tmp_path: Path):
    import json

    paths = _write_mini_insize_partition(tmp_path)
    out = tmp_path / "effective"
    result = apply_insize_reconciliation(
        first_run_dir=paths["first"],
        second_run_dir=paths["second"],
        materialization_dir=paths["mat"],
        output_dir=out,
        repo_root=REPO,
        requested=263,
    )
    assert result["stable_candidates"] == 42
    assert result["source_drift_rows"] == 7
    assert result["stable_materialized_rows"] == 28
    assert result["materialized_source_drift_rows"] == 2

    stable = list(csv.DictReader((out / "stable-candidates.csv").open(encoding="utf-8")))
    drift = list(csv.DictReader((out / "source-drift-review.csv").open(encoding="utf-8")))
    stab_mat = list(
        csv.DictReader((out / "stable-materialized-manifest.csv").open(encoding="utf-8"))
    )
    stab_rej = list(
        csv.DictReader((out / "stable-materialization-rejected.csv").open(encoding="utf-8"))
    )
    assert len(stable) == 42
    assert len(drift) == 7
    assert len(stab_mat) == 28
    assert len(stab_rej) == 14
    assert {r["product_id"] for r in stable}.isdisjoint({r["product_id"] for r in drift})
    assert all(r["discovery_status"] == "source_drift_review" for r in drift)
    assert all(r["eligible_for_automatic_discovery"] == "false" for r in drift)
    assert all(r["review_status"] == "source_drift_review" for r in drift)
    assert {r["product_id"] for r in stab_mat}.isdisjoint({r["product_id"] for r in drift})
    assert sum(1 for r in drift if r["materialized"] == "true") == 2
    assert all(r["asset_sha256"] for r in drift if r["materialized"] == "true")

    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["coverage"]["stable_candidate_discovery_coverage_pct"] == round(
        100.0 * 42 / 263, 2
    )
    assert summary["coverage"]["stable_validated_materialization_coverage_pct"] == round(
        100.0 * 28 / 263, 2
    )
    assert summary["coverage"]["raw_pre_quarantine_materialization_coverage_pct"] == round(
        100.0 * 30 / 263, 2
    )
    assert summary["timing"]["timing_status"] == "legacy_unreliable"
    assert summary["timing"]["timing_used_for_governance"] is False
    assert (out / "checksums.sha256").is_file()
    out2 = tmp_path / "effective2"
    apply_insize_reconciliation(
        first_run_dir=paths["first"],
        second_run_dir=paths["second"],
        materialization_dir=paths["mat"],
        output_dir=out2,
        repo_root=REPO,
        requested=263,
    )
    assert (out / "checksums.sha256").read_text() == (out2 / "checksums.sha256").read_text()


def test_consolidate_full_manual_schema_and_governed_review_count(tmp_path: Path):
    import json

    def lane(brand: str, lane_id: str, manuals: list[dict[str, str]], cands: int = 0) -> Path:
        d = tmp_path / f"lane-{brand}"
        d.mkdir()
        (d / "summary.json").write_text(
            json.dumps({"requested": 10, "lane_id": lane_id, "brand_key": brand}) + "\n",
            encoding="utf-8",
        )
        fields = [
            "schema_version",
            "task_id",
            "lane_id",
            "product_id",
            "product_key",
            "sku",
            "product_name",
            "brand_key",
            "work_type",
            "work_reasons",
            "priority",
            "source_adapter",
            "source_class",
            "source_detail_url",
            "source_image_url",
            "source_image_index",
            "candidate_discovery_method",
            "candidate_match_basis",
            "manufacturer_evidence",
            "sku_evidence",
            "confidence",
            "rights_status",
            "apply_status",
            "discovery_status",
            "notes",
        ]
        with (d / "candidate-input.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for i in range(cands):
                w.writerow(
                    {
                        "schema_version": "1",
                        "task_id": "IMG-02B",
                        "lane_id": lane_id,
                        "product_id": str(1000 + i),
                        "product_key": f"product_id:{1000 + i}",
                        "sku": f"{brand}-{i}",
                        "product_name": "x",
                        "brand_key": brand,
                        "work_type": "missing_image",
                        "work_reasons": "missing_image",
                        "priority": "P0",
                        "source_adapter": "x",
                        "source_class": "x",
                        "source_detail_url": "https://example.com/d",
                        "source_image_url": "https://example.com/i.jpg",
                        "source_image_index": "0",
                        "candidate_discovery_method": "x",
                        "candidate_match_basis": "x",
                        "manufacturer_evidence": "x",
                        "sku_evidence": "x",
                        "confidence": "high",
                        "rights_status": "review_required",
                        "apply_status": "not_started",
                        "discovery_status": "candidate_ready",
                        "notes": "",
                    }
                )
        with (d / "rejected-candidates.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "lane_id",
                    "product_id",
                    "sku",
                    "product_name",
                    "reason_code",
                    "reason_detail",
                    "notes",
                ],
            )
            w.writeheader()
        with (d / "manual-review.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=MANUAL_FIELDS)
            w.writeheader()
            for row in manuals:
                w.writerow({k: row.get(k, "") for k in MANUAL_FIELDS})
        return d

    dasqua = lane(
        "dasqua",
        "IMG-02B-02",
        [
            {
                "lane_id": "IMG-02B-02",
                "product_id": "1176",
                "product_key": "product_id:1176",
                "sku": "1804-1405",
                "product_name": "gauge",
                "work_type": "replace_required",
                "work_reasons": "replace_required:IMG-02A-02-BATCH-002",
                "priority": "P0",
                "reason_code": "ambiguous_official_product",
                "reason_detail": "family",
                "source_detail_url": "",
                "discovery_status": "manual_review",
                "eligible_for_automatic_discovery": "false",
                "notes": "",
            }
        ],
    )
    sanou_manuals = [
        {
            "lane_id": "IMG-02B-04",
            "product_id": str(2000 + i),
            "product_key": f"product_id:{2000 + i}",
            "sku": f"SO-{i}",
            "product_name": "tokenless",
            "work_type": "missing_image",
            "work_reasons": "missing_image",
            "priority": "P0",
            "reason_code": "model_token_not_found",
            "reason_detail": "no token",
            "source_detail_url": "",
            "discovery_status": "manual_review",
            "eligible_for_automatic_discovery": "false",
            "notes": "",
        }
        for i in range(38)
    ]
    sanou = lane("san_ou", "IMG-02B-04", sanou_manuals)
    insize = lane("insize", "IMG-02B-03", [], cands=0)

    stab = tmp_path / "stable-manifest.csv"
    with stab.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["product_id", "sku", "sha256", "brand"])
        w.writeheader()
        for i in range(1, 29):
            w.writerow(
                {
                    "product_id": str(i),
                    "sku": f"S-{i}",
                    "sha256": f"{i:064x}"[:64],
                    "brand": "INSIZE",
                }
            )
    drift = tmp_path / "source-drift-review.csv"
    with drift.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "product_id",
                "product_key",
                "sku",
                "product_name",
                "work_type",
                "work_reasons",
                "priority",
                "lane_id",
                "drift_type",
                "first_detail_url",
                "second_detail_url",
                "first_image_url",
                "second_image_url",
                "materialized",
                "local_asset_path",
                "asset_sha256",
                "review_status",
                "discovery_status",
                "eligible_for_automatic_discovery",
                "rights_status",
                "apply_status",
                "reason_code",
                "reason_detail",
                "notes",
            ],
        )
        w.writeheader()
        for i in range(43, 50):
            w.writerow(
                {
                    "product_id": str(i),
                    "product_key": f"product_id:{i}",
                    "sku": f"S-{i}",
                    "product_name": f"n-{i}",
                    "work_type": "missing_image",
                    "work_reasons": "missing_image",
                    "priority": "P0",
                    "lane_id": "IMG-02B-03",
                    "drift_type": "removed_in_second_run",
                    "first_detail_url": "https://www.tosag.ch/d",
                    "second_detail_url": "",
                    "first_image_url": "https://www.tosag.ch/i.jpg",
                    "second_image_url": "",
                    "materialized": "false",
                    "local_asset_path": "",
                    "asset_sha256": "",
                    "review_status": "source_drift_review",
                    "discovery_status": "source_drift_review",
                    "eligible_for_automatic_discovery": "false",
                    "rights_status": "review_required",
                    "apply_status": "not_started",
                    "reason_code": "source_drift_review",
                    "reason_detail": "drift",
                    "notes": "",
                }
            )

    out = tmp_path / "cons"
    result = consolidate_lane_outputs(
        lane_dirs={"dasqua": dasqua, "insize": insize, "san_ou": sanou},
        download_dirs=None,
        output_dir=out,
        repo_root=REPO,
        accepted_manifest_by_brand={"insize": stab},
        drift_review_csvs=[drift],
    )
    accepted = list(csv.DictReader((out / "all-accepted-manifest.csv").open(encoding="utf-8")))
    manual = list(csv.DictReader((out / "all-manual-review.csv").open(encoding="utf-8")))
    assert len(accepted) == 28
    assert len(manual) == 46
    assert list(manual[0].keys()) == MANUAL_FIELDS
    assert all(r["eligible_for_automatic_discovery"] == "false" for r in manual)
    das = next(r for r in manual if r["product_id"] == "1176")
    assert das["product_key"] == "product_id:1176"
    assert das["work_type"] == "replace_required"
    assert das["work_reasons"] == "replace_required:IMG-02A-02-BATCH-002"
    assert das["priority"] == "P0"
    assert das["reason_code"] == "ambiguous_official_product"
    assert (out / "all-source-drift-review.csv").is_file()
    summary = result["summary"]
    assert summary["totals"]["stable_accepted_or_materialized"] == 28
    assert summary["totals"]["ordinary_manual_review"] == 39
    assert summary["totals"]["source_drift_review"] == 7
    assert summary["totals"]["combined_governed_review"] == 46
