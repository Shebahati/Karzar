"""IMG-01B blocker coverage — local/mocked only (no network, no DB)."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "tosag"
sys.path.insert(0, str(SCRIPTS))

from discover_product_images import main as cli_main  # noqa: E402
from image_discovery import contracts as C  # noqa: E402
from image_discovery.atomic import atomic_write_text  # noqa: E402
from image_discovery.consolidation import consolidate_batches  # noqa: E402
from image_discovery.core import run_discovery  # noqa: E402
from image_discovery.output import (  # noqa: E402
    load_previous_manifest,
    load_run_state,
    rename_and_classify,
    write_outputs,
)
from image_discovery.paths import (  # noqa: E402
    assert_under_assets,
    governed_asset_filename,
    safe_path_segment,
)
from image_discovery.sources.insize_tosag import InsizeTosagAdapter  # noqa: E402
from image_discovery.transport import HostThrottledFetcher  # noqa: E402


def _jpeg(color: tuple[int, int, int] = (10, 20, 30), width: int = 300, height: int = 300) -> bytes:
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _write_candidates(path: Path, rows: list[dict[str, str]]) -> None:
    fields = ["sku", "product_name", "image_url", "detail_url", "confidence", "brand", "product_id"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


class RecordingUrlOpen:
    def __init__(self, routes: dict[str, Any]) -> None:
        self.routes = routes
        self.calls: list[str] = []
        self.lock = threading.Lock()
        self.active = 0
        self.max_active = 0

    def __call__(self, req: Request, timeout: float):
        url = req.full_url
        with self.lock:
            self.calls.append(url)
        item = self.routes.get(url)
        if item is None:
            raise C.DiscoveryError("fetch", "detail_fetch_failed", f"missing {url}")
        if item.get("redirect"):
            raise HTTPError(url, item.get("code", 302), "redirect", {"Location": item["redirect"]}, io.BytesIO())

        class Resp:
            def __init__(self, status: int, body: bytes, headers: dict[str, str], final: str):
                self.status = status
                self._body = body
                self.headers = headers
                self._final = final

            def read(self, n: int = -1):
                if n is None or n < 0:
                    data, self._body = self._body, b""
                    return data
                data, self._body = self._body[:n], self._body[n:]
                return data

            def getcode(self):
                return self.status

            def geturl(self):
                return self._final

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        headers = {"Content-Type": item.get("ctype", "text/html")}
        if "content_length" in item:
            headers["Content-Length"] = str(item["content_length"])
        delay = float(item.get("delay") or 0)
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            if delay:
                time.sleep(delay)
            return Resp(item.get("status", 200), item["body"], headers, item.get("final", url))
        finally:
            with self.lock:
                self.active -= 1


@pytest.fixture()
def external_out(tmp_path: Path) -> Path:
    out = tmp_path / "out"
    out.mkdir()
    try:
        out.resolve().relative_to(REPO_ROOT)
        pytest.skip("tmp inside repo")
    except ValueError:
        pass
    return out



def _valid_identity(sku: str, brand: str = "INSIZE", sck: str | None = None, role: str = "primary"):
    sck = sck or ("a" * 64)
    _, product_key, basis = C.build_product_identity(brand=brand, sku=sku)
    cid = C.make_candidate_id(
        source_adapter="insize_tosag",
        product_key=product_key,
        source_candidate_key=sck,
        image_role=role,
    )
    return cid, product_key, basis, sck


def test_global_candidate_identity_brands_and_adapters() -> None:
    a = C.ImageCandidate(
        sku="1103-150",
        product_name="A",
        brand="INSIZE",
        detail_url="https://www.tosag.ch/d",
        image_url="https://www.tosag.ch/i.jpg",
        source_adapter="insize_tosag",
    )
    b = C.ImageCandidate(
        sku="1103-150",
        product_name="A",
        brand="OtherBrand",
        detail_url="https://www.tosag.ch/d",
        image_url="https://www.tosag.ch/i.jpg",
        source_adapter="insize_tosag",
    )
    c = C.ImageCandidate(
        sku="1103-150",
        product_name="A",
        brand="INSIZE",
        detail_url="https://www.tosag.ch/d",
        image_url="https://www.tosag.ch/i.jpg",
        source_adapter="other_adapter",
    )
    a.ensure_identity()
    b.ensure_identity()
    c.ensure_identity()
    assert a.product_key != b.product_key
    assert a.candidate_id != b.candidate_id
    assert a.candidate_id != c.candidate_id
    assert a.identity_basis == "brand_sku"
    assert a.sku != a.product_key


def test_same_product_two_candidates_and_deterministic_id() -> None:
    base = dict(
        sku="X-1",
        product_name="X",
        brand="INSIZE",
        detail_url="https://www.tosag.ch/d",
        image_url="https://www.tosag.ch/a.jpg",
        source_adapter="insize_tosag",
        product_id="42",
    )
    c1 = C.ImageCandidate(**base, image_role="primary", source_image_index=0)
    c2 = C.ImageCandidate(
        **{**base, "image_url": "https://www.tosag.ch/b.jpg"},
        image_role="alternate",
        source_image_index=1,
    )
    c1.ensure_identity()
    c2.ensure_identity()
    assert c1.product_key == "product_id:42"
    assert c1.identity_basis == "product_id"
    assert c1.candidate_id != c2.candidate_id
    again = C.ImageCandidate(**base, image_role="primary", source_image_index=0)
    again.ensure_identity()
    assert again.candidate_id == c1.candidate_id
    # source URL change alters source_candidate_key / candidate_id
    changed = C.ImageCandidate(**{**base, "image_url": "https://www.tosag.ch/c.jpg"}, image_role="primary", source_image_index=0)
    changed.ensure_identity()
    assert changed.candidate_id != c1.candidate_id


def test_safe_path_hostile_values(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    hostile = [
        "../../../outside",
        "A/B",
        "A\\B",
        "..",
        ".",
        "CON",
        "NUL",
        "  leading trailing  ",
        "e\u0301",  # combining form
        "SKU-" + ("X" * 300),
    ]
    for raw in hostile:
        seg = safe_path_segment(raw)
        assert "/" not in seg and "\\" not in seg
        assert ".." not in seg
        assert "\x00" not in seg
        name = governed_asset_filename(brand=raw, label=raw, sha256="a" * 64, extension="jpg")
        dest = assert_under_assets(assets, assets / name)
        assert dest.is_relative_to(assets.resolve()) or str(assets.resolve()) in str(dest)
        # never write outside assets
        dest.write_bytes(b"x")
        assert dest.exists()
        assert assets in dest.parents or dest.parent == assets


def test_provenance_survives_write_read_consolidate(external_out: Path, tmp_path: Path) -> None:
    root = tmp_path / "batches"
    detail = "https://www.tosag.ch/p"
    image = "https://www.tosag.ch/p.jpg"
    cand = tmp_path / "c.csv"
    _write_candidates(
        cand,
        [{"sku": "1103-150", "product_name": "A", "image_url": image, "detail_url": detail, "confidence": "x"}],
    )
    page = (FIXTURES / "product_heading_article.html").read_bytes()
    jpeg = _jpeg()
    opener = RecordingUrlOpen({detail: {"body": page}, image: {"body": jpeg, "ctype": "image/jpeg", "final": image}})
    batch = root / "batch-a"
    run_discovery(
        adapter=InsizeTosagAdapter(),
        products_csv=None,
        candidates_csv=cand,
        output_dir=batch,
        repo_root=REPO_ROOT,
        concurrency=1,
        delay=0,
        fetcher=HostThrottledFetcher(allowed_hosts=frozenset({"www.tosag.ch"}), delay=0, urlopen=opener),
        min_bytes=100,
        min_dim=50,
        provenance_batch="batch-a",
    )
    man = json.loads((batch / "manifests" / "manifest.json").read_text())
    assert man[0]["provenance_batch"] == "batch-a"
    assert man[0]["provenance_source_adapter"] == "insize_tosag"
    out = tmp_path / "cons"
    summary = consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)
    assert summary["accepted_rows"] == 1
    cman = json.loads((out / "manifests" / "manifest.json").read_text())
    assert cman[0]["provenance_batch"] == "batch-a"
    assert "provenance_manifest" in cman[0]


def test_manifest_and_destination_sha_mismatch_and_missing(tmp_path: Path) -> None:
    root = tmp_path / "batches"
    b1 = root / "b1"
    (b1 / "manifests").mkdir(parents=True)
    (b1 / "assets").mkdir(parents=True)
    jpeg = _jpeg()
    sha = hashlib.sha256(jpeg).hexdigest()
    (b1 / "assets" / "x.jpg").write_bytes(jpeg)
    cid, product_key, basis, sck = _valid_identity("A-1", sck="b" * 64)
    row = {
        "candidate_id": cid,
        "product_id": "",
        "product_key": product_key,
        "identity_basis": basis,
        "source_candidate_key": sck,
        "sku": "A-1",
        "product_name": "A",
        "brand": "INSIZE",
        "source_adapter": "insize_tosag",
        "source_class": "x",
        "image_role": "primary",
        "source_rank": 1,
        "display_order_candidate": 1,
        "source_image_index": 0,
        "source_detail_url": "https://www.tosag.ch/d",
        "source_image_url": "https://www.tosag.ch/i.jpg",
        "final_image_url": "https://www.tosag.ch/i.jpg",
        "local_asset_path": "assets/x.jpg",
        "sha256": "0" * 64,  # mismatch
        "mime_type": "image/jpeg",
        "extension": "jpg",
        "byte_size": len(jpeg),
        "width": 300,
        "height": 300,
        "foreground_occupancy_status": "ok",
        "presentation_note": "",
        "match_confidence": "x",
        "sku_confirmed": True,
        "manufacturer_confirmed": True,
        "manufacturer_evidence": "h",
        "sku_evidence": "s",
        "page_subject_evidence": "h",
        "image_specificity": "singleton_unverified",
        "variant_specific": "unknown",
        "shared_asset_group": "g",
        "download_status": "downloaded_new",
        "review_status": "pending_human_review",
        "rights_status": "review_required",
        "provenance_batch": "b1",
        "provenance_manifest": "manifests/manifest.json",
        "provenance_source_adapter": "insize_tosag",
        "notes": "",
    }
    (b1 / "manifests" / "manifest.json").write_text(json.dumps([row]), encoding="utf-8")
    out = tmp_path / "cons"
    with pytest.raises(SystemExit, match="integrity"):
        consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)
    summary = json.loads((out / "summary.json").read_text())
    assert summary["accepted_rows"] == 0
    assert summary["status"] == "integrity_failure"
    rej = list(csv.DictReader((out / "manifests" / "rejected.csv").open(encoding="utf-8")))
    assert any(r["reason_code"] == "manifest_sha_mismatch" for r in rej)

    # missing asset
    row2 = dict(row)
    cid2, pk2, basis2, sck2 = _valid_identity("A-2", sck="c" * 64)
    row2["candidate_id"] = cid2
    row2["product_key"] = pk2
    row2["identity_basis"] = basis2
    row2["source_candidate_key"] = sck2
    row2["sku"] = "A-2"
    row2["sha256"] = sha
    row2["local_asset_path"] = "assets/missing.jpg"
    b2 = root / "b2"
    (b2 / "manifests").mkdir(parents=True)
    (b2 / "assets").mkdir(parents=True)
    (b2 / "manifests" / "manifest.json").write_text(json.dumps([row2]), encoding="utf-8")
    out2 = tmp_path / "cons2"
    with pytest.raises(SystemExit, match="integrity"):
        consolidate_batches(input_dir=root, output_dir=out2, repo_root=REPO_ROOT)
    # b1 still mismatch reject; b2 missing
    rej2 = list(csv.DictReader((out2 / "manifests" / "rejected.csv").open(encoding="utf-8")))
    codes = {r["reason_code"] for r in rej2}
    assert "missing_source_asset" in codes


def test_duplicate_candidate_conflict_exits(tmp_path: Path) -> None:
    root = tmp_path / "batches"
    jpeg = _jpeg()
    sha = hashlib.sha256(jpeg).hexdigest()
    cid, product_key, basis, sck = _valid_identity("A-1", sck="d" * 64)
    base_row = {
        "candidate_id": cid,
        "product_id": "",
        "product_key": product_key,
        "identity_basis": basis,
        "source_candidate_key": sck,
        "sku": "A-1",
        "product_name": "A",
        "brand": "INSIZE",
        "source_adapter": "insize_tosag",
        "source_class": "x",
        "image_role": "primary",
        "source_rank": 1,
        "display_order_candidate": 1,
        "source_image_index": 0,
        "source_detail_url": "https://www.tosag.ch/d",
        "source_image_url": "https://www.tosag.ch/i.jpg",
        "final_image_url": "https://www.tosag.ch/i.jpg",
        "local_asset_path": "assets/x.jpg",
        "sha256": sha,
        "mime_type": "image/jpeg",
        "extension": "jpg",
        "byte_size": len(jpeg),
        "width": 300,
        "height": 300,
        "foreground_occupancy_status": "ok",
        "presentation_note": "",
        "match_confidence": "x",
        "sku_confirmed": True,
        "manufacturer_confirmed": True,
        "manufacturer_evidence": "h",
        "sku_evidence": "s",
        "page_subject_evidence": "h",
        "image_specificity": "singleton_unverified",
        "variant_specific": "unknown",
        "shared_asset_group": "g",
        "download_status": "downloaded_new",
        "review_status": "pending_human_review",
        "rights_status": "review_required",
        "provenance_batch": "",
        "provenance_manifest": "",
        "provenance_source_adapter": "insize_tosag",
        "notes": "",
    }
    for name, note in [("b1", "left"), ("b2", "right-different")]:
        b = root / name
        (b / "manifests").mkdir(parents=True)
        (b / "assets").mkdir(parents=True)
        (b / "assets" / "x.jpg").write_bytes(jpeg)
        row = dict(base_row)
        row["notes"] = note  # semantic fields don't include notes — change sha256 field via product_name
        row["product_name"] = note
        (b / "manifests" / "manifest.json").write_text(json.dumps([row]), encoding="utf-8")
    out = tmp_path / "cons"
    with pytest.raises(SystemExit, match="conflict"):
        consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)
    assert (out / "manifests" / "candidate-conflicts.json").exists()
    assert (out / "manifests" / "candidate-conflicts.csv").exists()


def test_cross_brand_duplicate_classification(tmp_path: Path) -> None:
    out = tmp_path / "out"
    (out / "assets").mkdir(parents=True)
    jpeg = _jpeg()
    sha = hashlib.sha256(jpeg).hexdigest()
    path = out / "assets" / f"pending__{sha[:12]}.jpg"
    path.write_bytes(jpeg)
    rows = []
    for brand, sku in [("INSIZE", "A-1"), ("Mitutoyo", "A-1")]:
        rows.append(
            {
                "sku": sku,
                "brand": brand,
                "product_key": f"brand_sku:{brand.lower()}:{sku.lower()}",
                "sha256": sha,
                "extension": "jpg",
                "local_asset_path": f"assets/{path.name}",
                "candidate_id": f"cid:{brand}",
                "source_image_url": "https://www.tosag.ch/i.jpg",
                "byte_size": len(jpeg),
                "width": 300,
                "height": 300,
                "shared_asset_group": "",
                "image_specificity": "",
            }
        )
    cross = rename_and_classify(rows, out)
    assert rows[0]["image_specificity"] == "cross_brand_duplicate"
    assert cross and cross[0]["review_status"] == "pending_human_review"
    write_outputs(out, rows, [], cross_brand=cross, conflicts=[])
    assert (out / "manifests" / "cross-brand-duplicates.csv").exists()


def test_run_state_referenced_assets_not_leftovers(external_out: Path, tmp_path: Path) -> None:
    detail = "https://www.tosag.ch/s"
    image = "https://www.tosag.ch/s.jpg"
    cand = tmp_path / "c.csv"
    _write_candidates(
        cand,
        [
            {"sku": "1103-150", "product_name": "A", "image_url": image, "detail_url": detail, "confidence": "x"},
            {"sku": "1103-200", "product_name": "B", "image_url": image, "detail_url": detail, "confidence": "x"},
        ],
    )
    page = (FIXTURES / "family_variation_table.html").read_bytes()
    jpeg = _jpeg()
    opener = RecordingUrlOpen({detail: {"body": page}, image: {"body": jpeg, "ctype": "image/jpeg", "final": image}})
    fetcher = HostThrottledFetcher(allowed_hosts=frozenset({"www.tosag.ch"}), delay=0, urlopen=opener)
    s1 = run_discovery(
        adapter=InsizeTosagAdapter(),
        products_csv=None,
        candidates_csv=cand,
        output_dir=external_out,
        repo_root=REPO_ROOT,
        concurrency=1,
        delay=0,
        fetcher=fetcher,
        min_bytes=100,
        min_dim=50,
    )
    # leftover stale file
    stale = external_out / "assets" / "stale-leftover.jpg"
    stale.write_bytes(_jpeg(color=(1, 2, 3)))
    # remove one SKU
    cand2 = tmp_path / "c2.csv"
    _write_candidates(
        cand2,
        [{"sku": "1103-150", "product_name": "A", "image_url": image, "detail_url": detail, "confidence": "x"}],
    )
    s2 = run_discovery(
        adapter=InsizeTosagAdapter(),
        products_csv=None,
        candidates_csv=cand2,
        output_dir=external_out,
        repo_root=REPO_ROOT,
        concurrency=1,
        delay=0,
        resume=True,
        fetcher=fetcher,
        min_bytes=100,
        min_dim=50,
    )
    assert s2["stale_unreferenced_files"] >= 1
    assert s2["missing_referenced_files"] == 0
    # asset_set_stable compares referenced sets — leftover must not break stability alone if refs unchanged
    s3 = run_discovery(
        adapter=InsizeTosagAdapter(),
        products_csv=None,
        candidates_csv=cand2,
        output_dir=external_out,
        repo_root=REPO_ROOT,
        concurrency=1,
        delay=0,
        resume=True,
        fetcher=fetcher,
        min_bytes=100,
        min_dim=50,
    )
    assert s3["semantic_manifest_stable"] is True
    assert s3["asset_set_stable"] is True
    assert s1["accepted_rows"] == 2


def test_corrupt_manifest_and_run_state(external_out: Path) -> None:
    (external_out / "manifests").mkdir(parents=True, exist_ok=True)
    (external_out / "manifests" / "manifest.json").write_text("{not-json", encoding="utf-8")
    with pytest.raises(C.DiscoveryError) as e:
        load_previous_manifest(external_out, resume=True)
    assert e.value.reason_code == "corrupt_previous_manifest"
    (external_out / "manifests" / "run-state.json").write_text("{bad", encoding="utf-8")
    with pytest.raises(C.DiscoveryError) as e2:
        load_run_state(external_out, resume=True)
    assert e2.value.reason_code == "corrupt_run_state"


def test_atomic_output_replacement(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    atomic_write_text(path, '{"ok":1}\n')
    assert json.loads(path.read_text())["ok"] == 1
    atomic_write_text(path, '{"ok":2}\n')
    assert json.loads(path.read_text())["ok"] == 2
    assert not list(tmp_path.glob(".manifest.json.*"))


def test_bounded_http_and_scheme_port() -> None:
    url = "https://www.tosag.ch/big"
    opener = RecordingUrlOpen(
        {url: {"body": b"x" * 1000, "content_length": 1000, "ctype": "text/html"}}
    )
    fetcher = HostThrottledFetcher(
        allowed_hosts=frozenset({"www.tosag.ch"}),
        delay=0,
        urlopen=opener,
        max_detail_page_bytes=100,
    )
    with pytest.raises(C.DiscoveryError) as e:
        fetcher.get(url, fail_code="detail_fetch_failed")
    assert e.value.reason_code == "response_too_large"

    with pytest.raises(C.DiscoveryError) as e2:
        HostThrottledFetcher(allowed_hosts=frozenset({"www.tosag.ch"}), delay=0, urlopen=opener).get(
            "http://www.tosag.ch/x", fail_code="detail_fetch_failed"
        )
    assert e2.value.reason_code == "unsupported_scheme"

    with pytest.raises(C.DiscoveryError) as e3:
        HostThrottledFetcher(allowed_hosts=frozenset({"www.tosag.ch"}), delay=0, urlopen=opener).get(
            "https://www.tosag.ch:8443/x", fail_code="detail_fetch_failed"
        )
    assert e3.value.reason_code == "unexpected_port"


def test_concurrency_unrelated_overlap() -> None:
    u1 = "https://www.tosag.ch/a"
    u2 = "https://www.tosag.ch/b"
    body = b"<html>ok</html>"
    opener = RecordingUrlOpen(
        {
            u1: {"body": body, "delay": 0.2},
            u2: {"body": body, "delay": 0.2},
        }
    )
    fetcher = HostThrottledFetcher(allowed_hosts=frozenset({"www.tosag.ch"}), delay=0, urlopen=opener)

    def one(u: str) -> None:
        fetcher.get(u, fail_code="detail_fetch_failed")

    with ThreadPoolExecutor(max_workers=2) as ex:
        list(ex.map(one, [u1, u2]))
    assert opener.max_active >= 2
    assert opener.calls.count(u1) == 1
    assert opener.calls.count(u2) == 1


def test_concurrency_page_single_flight(external_out: Path, tmp_path: Path) -> None:
    detail = "https://www.tosag.ch/shared"
    img1 = "https://www.tosag.ch/i1.jpg"
    img2 = "https://www.tosag.ch/i2.jpg"
    page = (FIXTURES / "family_variation_table.html").read_bytes()
    jpeg = _jpeg()
    opener = RecordingUrlOpen(
        {
            detail: {"body": page, "delay": 0.2},
            img1: {"body": jpeg, "ctype": "image/jpeg", "final": img1},
            img2: {"body": jpeg, "ctype": "image/jpeg", "final": img2},
        }
    )
    cand = tmp_path / "c.csv"
    _write_candidates(
        cand,
        [
            {"sku": "1103-150", "product_name": "A", "image_url": img1, "detail_url": detail, "confidence": "x"},
            {"sku": "1103-200", "product_name": "B", "image_url": img2, "detail_url": detail, "confidence": "x"},
        ],
    )
    run_discovery(
        adapter=InsizeTosagAdapter(),
        products_csv=None,
        candidates_csv=cand,
        output_dir=external_out,
        repo_root=REPO_ROOT,
        concurrency=2,
        delay=0,
        fetcher=HostThrottledFetcher(allowed_hosts=frozenset({"www.tosag.ch"}), delay=0, urlopen=opener),
        min_bytes=100,
        min_dim=50,
    )
    assert opener.calls.count(detail) == 1


def test_cli_invalid_numeric_values() -> None:
    with pytest.raises(SystemExit, match="max-images-per-product"):
        cli_main(
            [
                "run",
                "--source",
                "insize_tosag",
                "--candidates-csv",
                "/tmp/x.csv",
                "--output-dir",
                "/tmp/out-img01b",
                "--max-images-per-product",
                "0",
            ]
        )
    with pytest.raises(SystemExit, match="concurrency"):
        cli_main(
            [
                "run",
                "--source",
                "insize_tosag",
                "--candidates-csv",
                "/tmp/x.csv",
                "--output-dir",
                "/tmp/out-img01b",
                "--concurrency",
                "-1",
            ]
        )


def test_consolidate_path_nesting_rejected(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    child = parent / "child"
    parent.mkdir()
    child.mkdir()
    with pytest.raises(SystemExit, match="nested"):
        consolidate_batches(input_dir=parent, output_dir=child, repo_root=REPO_ROOT)
    with pytest.raises(SystemExit, match="nested"):
        consolidate_batches(input_dir=child, output_dir=parent, repo_root=REPO_ROOT)
    with pytest.raises(SystemExit, match="differ"):
        consolidate_batches(input_dir=parent, output_dir=parent, repo_root=REPO_ROOT)


def test_tosag_fixtures_subject_rules() -> None:
    adapter = InsizeTosagAdapter()
    ok = adapter.validate_page(
        sku="1103-150",
        page_html=(FIXTURES / "product_heading_article.html").read_text(encoding="utf-8"),
        detail_url="https://www.tosag.ch/x",
    )
    assert ok.manufacturer_confirmed and ok.sku_confirmed

    fam = adapter.validate_page(
        sku="1103-150",
        page_html=(FIXTURES / "family_variation_table.html").read_text(encoding="utf-8"),
        detail_url="https://www.tosag.ch/x",
    )
    assert fam.sku_confirmed

    weak_mfg = adapter.validate_page(
        sku="1103-150",
        page_html=(FIXTURES / "body_marketing_insize_only.html").read_text(encoding="utf-8"),
        detail_url="https://www.tosag.ch/x",
    )
    assert not weak_mfg.manufacturer_confirmed
    assert weak_mfg.weak_review_only or weak_mfg.reason_code == "manufacturer_not_confirmed"

    weak_sku = adapter.validate_page(
        sku="1103-150",
        page_html=(FIXTURES / "body_paragraph_sku_only.html").read_text(encoding="utf-8"),
        detail_url="https://www.tosag.ch/x",
    )
    assert not weak_sku.sku_confirmed

    related = adapter.validate_page(
        sku="1103-150",
        page_html=(FIXTURES / "related_section_not_div.html").read_text(encoding="utf-8"),
        detail_url="https://www.tosag.ch/x",
    )
    assert not related.sku_confirmed

    crumb = adapter.validate_page(
        sku="1103-150",
        page_html=(FIXTURES / "breadcrumb_only.html").read_text(encoding="utf-8"),
        detail_url="https://www.tosag.ch/x",
    )
    assert not crumb.manufacturer_confirmed or not crumb.sku_confirmed

    other = adapter.validate_page(
        sku="1103-150",
        page_html=(FIXTURES / "jsonld_other_brand.html").read_text(encoding="utf-8"),
        detail_url="https://www.tosag.ch/x",
    )
    assert not other.manufacturer_confirmed


def test_no_getdata_deprecation_warning() -> None:
    import warnings

    from image_discovery.quality import estimate_foreground_occupancy

    jpeg = _jpeg()
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        estimate_foreground_occupancy(data=jpeg, width=300, height=300, byte_size=len(jpeg))
    dep = [w for w in record if "getdata" in str(w.message).lower()]
    assert dep == []
