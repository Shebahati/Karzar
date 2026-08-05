"""Focused fixture tests for IMG-02B candidate discovery (no live network)."""

from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from image_candidate_discovery import CandidateDiscoveryError  # noqa: E402
from image_candidate_discovery.core import run_lane_candidate_discovery  # noqa: E402
from image_candidate_discovery.output import assert_external_output  # noqa: E402
from image_candidate_discovery.providers.dasqua_official import (  # noqa: E402
    extract_image,
    extract_primary_code,
    normalize_dasqua_code,
)
from image_candidate_discovery.providers.insize_tosag import (  # noqa: E402
    extract_primary_image,
    extract_search_product_links,
    sku_search_variants,
    sku_token_present,
)
from image_candidate_discovery.providers.sanou_official import (  # noqa: E402
    extract_model_tokens,
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
    assert normalize_dasqua_code("1804-1405A") == "1804-1405"
    html = (
        "<title>Dasqua 1804-1405 Digital Caliper</title>"
        '<meta property="og:image" content="https://www.dasquatools.com/image_product/x.jpg">'
    )
    assert extract_primary_code("Dasqua 1804-1405 Digital Caliper", "https://www.dasquatools.com/p", html) == "1804-1405"
    assert extract_image(html) == "https://www.dasquatools.com/image_product/x.jpg"
    cdn_html = (
        "<title>DASQUA 2115-2305 Caliper</title>"
        '<meta property="og:image" content="https://ecdn6.globalso.com/upload/p/565/image_product/2024-04/x.jpg">'
    )
    assert (
        extract_image(cdn_html)
        == "https://ecdn6.globalso.com/upload/p/565/image_product/2024-04/x.jpg"
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
        "<html><head><title>Dasqua Family</title></head>"
        "<body>Dasqua 1804-1405 and Dasqua 1804-1505</body></html>"
    )
    ev2 = adapter.validate_page(
        sku="1804-1405",
        page_html=family,
        detail_url="https://www.dasquatools.com/family",
    )
    assert not ev2.sku_confirmed


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
