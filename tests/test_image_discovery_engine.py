"""IMG-01A tests — mocked HTTP / local fixtures only (no network, no DB)."""

from __future__ import annotations

import csv
import io
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from image_discovery import contracts as C  # noqa: E402
from image_discovery.consolidation import consolidate_batches  # noqa: E402
from image_discovery.core import (  # noqa: E402
    assert_no_forbidden_imports_in_tree,
    run_discovery,
    validate_output_dir,
)
from image_discovery.output import semantic_manifest_sha256  # noqa: E402
from image_discovery.quality import validate_image_bytes  # noqa: E402
from image_discovery.sources.insize_tosag import InsizeTosagAdapter  # noqa: E402
from image_discovery.transport import HostThrottledFetcher  # noqa: E402

# Deterministic RGB fixtures — never use Python hash()
RGB_A = (10, 20, 30)
RGB_B = (40, 50, 60)
RGB_C = (70, 80, 90)
RGB_D = (100, 110, 120)
RGB_E = (130, 140, 150)
RGB_F = (160, 170, 180)
RGB_G = (190, 200, 210)


def _jpeg(width: int = 300, height: int = 300, color: tuple[int, int, int] = RGB_A) -> bytes:
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _png(width: int = 300, height: int = 300, color: tuple[int, int, int] = RGB_B) -> bytes:
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _write_candidates(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["sku", "product_name", "image_url", "detail_url", "confidence"])
        w.writeheader()
        for r in rows:
            w.writerow(r)


class RecordingUrlOpen:
    """Drive real HostThrottledFetcher redirect logic without network."""

    def __init__(self, routes: dict[str, Any]) -> None:
        self.routes = routes
        self.calls: list[str] = []

    def __call__(self, req: Request, timeout: float):
        url = req.full_url
        self.calls.append(url)
        item = self.routes.get(url)
        if item is None:
            raise C.DiscoveryError("fetch", "detail_fetch_failed", f"missing {url}")
        if item.get("redirect"):
            raise HTTPError(url, item.get("code", 302), "redirect", {"Location": item["redirect"]}, io.BytesIO())
        class Resp:
            def __init__(self, status: int, body: bytes, ctype: str, final: str):
                self.status = status
                self._body = body
                self.headers = {"Content-Type": ctype}
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
        resp = Resp(item.get("status", 200), item["body"], item.get("ctype", "text/html"), item.get("final", url))
        resp.headers = headers
        if item.get("delay"):
            import time

            time.sleep(float(item["delay"]))
        return resp


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


def test_forbidden_db_deps_absent() -> None:
    assert_no_forbidden_imports_in_tree(SCRIPTS / "image_discovery")
    text = (SCRIPTS / "discover_product_images.py").read_text(encoding="utf-8") + (
        SCRIPTS / "discover_insize_product_images.py"
    ).read_text(encoding="utf-8")
    assert "import sqlalchemy" not in text
    assert "DATABASE_URL" not in text
    assert "POSTGRES_" not in text
    assert "from app.db" not in text


def test_no_credential_env_access(monkeypatch: pytest.MonkeyPatch, external_out: Path, tmp_path: Path) -> None:
    probed: list[str] = []

    class Guard(dict):
        def __getitem__(self, key):  # type: ignore[no-untyped-def]
            probed.append(str(key))
            return super().__getitem__(key)

        def get(self, key, default=None):  # type: ignore[no-untyped-def]
            probed.append(str(key))
            return super().get(key, default)

        def __contains__(self, key):  # type: ignore[no-untyped-def]
            probed.append(str(key))
            return super().__contains__(key)

    # Ensure discovery does not touch os.environ for credentials
    real = os.environ
    monkeypatch.setattr(os, "environ", Guard(real))
    detail = "https://www.tosag.ch/d"
    image = "https://www.tosag.ch/i.jpg"
    cand = tmp_path / "c.csv"
    _write_candidates(
        cand,
        [{"sku": "1103-150", "product_name": "A", "image_url": image, "detail_url": detail, "confidence": "x"}],
    )
    page = b"<html><h1>INSIZE 1103-150</h1><p>manufacturer: INSIZE</p></html>"
    jpeg = _jpeg()
    opener = RecordingUrlOpen(
        {
            detail: {"body": page, "ctype": "text/html"},
            image: {"body": jpeg, "ctype": "image/jpeg", "final": image},
        }
    )
    fetcher = HostThrottledFetcher(allowed_hosts=frozenset({"www.tosag.ch"}), delay=0, urlopen=opener)
    run_discovery(
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
    sensitive = [k for k in probed if k.startswith(("DATABASE", "POSTGRES", "AWS", "S3")) or "TOKEN" in k or "SECRET" in k]
    assert sensitive == []


def test_output_dir_rejected_inside_repo() -> None:
    with pytest.raises(SystemExit, match="outside"):
        validate_output_dir(REPO_ROOT / "data" / "uploads" / "x", REPO_ROOT)


def test_exact_page_subject_acceptance(external_out: Path, tmp_path: Path) -> None:
    detail = "https://www.tosag.ch/ok"
    image = "https://www.tosag.ch/ok.jpg"
    cand = tmp_path / "c.csv"
    _write_candidates(
        cand,
        [{"sku": "1103-150", "product_name": "A", "image_url": image, "detail_url": detail, "confidence": "x"}],
    )
    page = b"<html><body><h1>Digital caliper INSIZE</h1><p>Art.Nr: 1103-150</p></body></html>"
    opener = RecordingUrlOpen(
        {detail: {"body": page}, image: {"body": _jpeg(), "ctype": "image/jpeg", "final": image}}
    )
    summary = run_discovery(
        adapter=InsizeTosagAdapter(),
        products_csv=None,
        candidates_csv=cand,
        output_dir=external_out,
        repo_root=REPO_ROOT,
        concurrency=1,
        delay=0,
        fetcher=HostThrottledFetcher(allowed_hosts=frozenset({"www.tosag.ch"}), delay=0, urlopen=opener),
        min_bytes=100,
        min_dim=50,
    )
    assert summary["accepted_rows"] == 1
    man = json.loads((external_out / "manifests" / "manifest.json").read_text())
    assert man[0]["rights_status"] == "review_required"
    assert man[0]["manufacturer_evidence"]
    assert man[0]["sku_evidence"]
    assert man[0]["image_role"] == "primary"


def test_footer_only_insize_rejection(external_out: Path, tmp_path: Path) -> None:
    detail = "https://www.tosag.ch/f"
    image = "https://www.tosag.ch/f.jpg"
    cand = tmp_path / "c.csv"
    _write_candidates(
        cand,
        [{"sku": "1103-150", "product_name": "A", "image_url": image, "detail_url": detail, "confidence": "x"}],
    )
    page = b"<html><body><h1>Generic tool</h1><p>Art 9999-000</p><footer>Powered by INSIZE partners</footer></body></html>"
    opener = RecordingUrlOpen(
        {detail: {"body": page}, image: {"body": _jpeg(), "ctype": "image/jpeg", "final": image}}
    )
    summary = run_discovery(
        adapter=InsizeTosagAdapter(),
        products_csv=None,
        candidates_csv=cand,
        output_dir=external_out,
        repo_root=REPO_ROOT,
        concurrency=1,
        delay=0,
        fetcher=HostThrottledFetcher(allowed_hosts=frozenset({"www.tosag.ch"}), delay=0, urlopen=opener),
        min_bytes=100,
        min_dim=50,
    )
    assert summary["rejected_rows"] == 1
    rej = list(csv.DictReader((external_out / "manifests" / "rejected.csv").open(encoding="utf-8")))
    assert rej[0]["reason_code"] == "manufacturer_not_confirmed"


def test_related_product_only_sku_rejection(external_out: Path, tmp_path: Path) -> None:
    detail = "https://www.tosag.ch/r"
    image = "https://www.tosag.ch/r.jpg"
    cand = tmp_path / "c.csv"
    _write_candidates(
        cand,
        [{"sku": "1103-150", "product_name": "A", "image_url": image, "detail_url": detail, "confidence": "x"}],
    )
    page = (
        b"<html><body><h1>INSIZE other model</h1><p>Art.Nr: 9999-111</p>"
        b"<div class='related-products'>Also see 1103-150</div></body></html>"
    )
    opener = RecordingUrlOpen(
        {detail: {"body": page}, image: {"body": _jpeg(), "ctype": "image/jpeg", "final": image}}
    )
    summary = run_discovery(
        adapter=InsizeTosagAdapter(),
        products_csv=None,
        candidates_csv=cand,
        output_dir=external_out,
        repo_root=REPO_ROOT,
        concurrency=1,
        delay=0,
        fetcher=HostThrottledFetcher(allowed_hosts=frozenset({"www.tosag.ch"}), delay=0, urlopen=opener),
        min_bytes=100,
        min_dim=50,
    )
    assert summary["rejected_rows"] == 1
    rej = list(csv.DictReader((external_out / "manifests" / "rejected.csv").open(encoding="utf-8")))
    assert rej[0]["reason_code"] == "exact_sku_not_confirmed"


def test_wrong_manufacturer_rejection(external_out: Path, tmp_path: Path) -> None:
    detail = "https://www.tosag.ch/w"
    image = "https://www.tosag.ch/w.jpg"
    cand = tmp_path / "c.csv"
    _write_candidates(
        cand,
        [{"sku": "1103-150", "product_name": "A", "image_url": image, "detail_url": detail, "confidence": "x"}],
    )
    page = b"<html><h1>Mitutoyo</h1><p>Art.Nr: 1103-150</p><p>Brand: Mitutoyo</p></html>"
    opener = RecordingUrlOpen(
        {detail: {"body": page}, image: {"body": _jpeg(), "ctype": "image/jpeg", "final": image}}
    )
    summary = run_discovery(
        adapter=InsizeTosagAdapter(),
        products_csv=None,
        candidates_csv=cand,
        output_dir=external_out,
        repo_root=REPO_ROOT,
        concurrency=1,
        delay=0,
        fetcher=HostThrottledFetcher(allowed_hosts=frozenset({"www.tosag.ch"}), delay=0, urlopen=opener),
        min_bytes=100,
        min_dim=50,
    )
    assert summary["rejected_rows"] == 1


def test_partial_sku_prefix_rejection(external_out: Path, tmp_path: Path) -> None:
    detail = "https://www.tosag.ch/p"
    image = "https://www.tosag.ch/p.jpg"
    cand = tmp_path / "c.csv"
    _write_candidates(
        cand,
        [{"sku": "1103-150", "product_name": "A", "image_url": image, "detail_url": detail, "confidence": "x"}],
    )
    page = b"<html><h1>INSIZE</h1><p>Art.Nr: 1103-1500</p></html>"
    opener = RecordingUrlOpen(
        {detail: {"body": page}, image: {"body": _jpeg(), "ctype": "image/jpeg", "final": image}}
    )
    summary = run_discovery(
        adapter=InsizeTosagAdapter(),
        products_csv=None,
        candidates_csv=cand,
        output_dir=external_out,
        repo_root=REPO_ROOT,
        concurrency=1,
        delay=0,
        fetcher=HostThrottledFetcher(allowed_hosts=frozenset({"www.tosag.ch"}), delay=0, urlopen=opener),
        min_bytes=100,
        min_dim=50,
    )
    assert summary["rejected_rows"] == 1


def test_same_host_absolute_and_relative_redirect(external_out: Path, tmp_path: Path) -> None:
    start = "https://www.tosag.ch/start"
    mid = "https://www.tosag.ch/mid"
    final_page = "https://www.tosag.ch/final"
    image = "https://www.tosag.ch/img.jpg"
    rel_start = "https://www.tosag.ch/rel"
    cand = tmp_path / "c.csv"
    _write_candidates(
        cand,
        [
            {"sku": "1103-150", "product_name": "A", "image_url": image, "detail_url": start, "confidence": "x"},
            {"sku": "1103-200", "product_name": "B", "image_url": image, "detail_url": rel_start, "confidence": "x"},
        ],
    )
    page = b"<html><h1>INSIZE</h1><p>Art 1103-150 1103-200</p></html>"
    opener = RecordingUrlOpen(
        {
            start: {"redirect": mid, "code": 302},
            mid: {"redirect": final_page, "code": 301},
            final_page: {"body": page},
            rel_start: {"redirect": "/final", "code": 302},
            image: {"body": _jpeg(), "ctype": "image/jpeg", "final": image},
        }
    )
    summary = run_discovery(
        adapter=InsizeTosagAdapter(),
        products_csv=None,
        candidates_csv=cand,
        output_dir=external_out,
        repo_root=REPO_ROOT,
        concurrency=1,
        delay=0,
        fetcher=HostThrottledFetcher(allowed_hosts=frozenset({"www.tosag.ch"}), delay=0, urlopen=opener),
        min_bytes=100,
        min_dim=50,
    )
    assert summary["accepted_rows"] == 2


def test_cross_host_redirect_rejected(external_out: Path, tmp_path: Path) -> None:
    detail = "https://www.tosag.ch/x"
    image = "https://www.tosag.ch/x.jpg"
    cand = tmp_path / "c.csv"
    _write_candidates(
        cand,
        [{"sku": "1103-150", "product_name": "A", "image_url": image, "detail_url": detail, "confidence": "x"}],
    )
    opener = RecordingUrlOpen(
        {
            detail: {"redirect": "https://evil.example/x", "code": 302},
            image: {"body": _jpeg(), "ctype": "image/jpeg", "final": image},
        }
    )
    run_discovery(
        adapter=InsizeTosagAdapter(),
        products_csv=None,
        candidates_csv=cand,
        output_dir=external_out,
        repo_root=REPO_ROOT,
        concurrency=1,
        delay=0,
        fetcher=HostThrottledFetcher(allowed_hosts=frozenset({"www.tosag.ch"}), delay=0, urlopen=opener),
        min_bytes=100,
        min_dim=50,
    )
    rej = list(csv.DictReader((external_out / "manifests" / "rejected.csv").open(encoding="utf-8")))
    assert rej[0]["reason_code"] == "cross_host_redirect"


def test_redirect_loop_and_limit() -> None:
    a = "https://www.tosag.ch/a"
    b = "https://www.tosag.ch/b"
    opener = RecordingUrlOpen({a: {"redirect": b}, b: {"redirect": a}})
    fetcher = HostThrottledFetcher(allowed_hosts=frozenset({"www.tosag.ch"}), delay=0, urlopen=opener)
    with pytest.raises(C.DiscoveryError) as ei:
        fetcher.get(a, fail_code="detail_fetch_failed")
    assert ei.value.reason_code in {"redirect_loop", "redirect_limit"}

    # limit
    chain = {f"https://www.tosag.ch/n{i}": {"redirect": f"https://www.tosag.ch/n{i+1}"} for i in range(0, 12)}
    opener2 = RecordingUrlOpen(chain)
    fetcher2 = HostThrottledFetcher(
        allowed_hosts=frozenset({"www.tosag.ch"}), delay=0, max_redirects=3, urlopen=opener2
    )
    with pytest.raises(C.DiscoveryError) as e2:
        fetcher2.get("https://www.tosag.ch/n0", fail_code="detail_fetch_failed")
    assert e2.value.reason_code == "redirect_limit"


def test_unsupported_host_before_request() -> None:
    opener = RecordingUrlOpen({})
    fetcher = HostThrottledFetcher(allowed_hosts=frozenset({"www.tosag.ch"}), delay=0, urlopen=opener)
    with pytest.raises(C.DiscoveryError) as ei:
        fetcher.get("https://other.example/x", fail_code="detail_fetch_failed")
    assert ei.value.reason_code == "unsupported_host"
    assert opener.calls == []


def test_html_as_image_and_corrupt_jpeg_png(external_out: Path, tmp_path: Path) -> None:
    with pytest.raises(C.DiscoveryError):
        validate_image_bytes(b"<!DOCTYPE html><html></html>", content_type="text/html", final_url="https://www.tosag.ch/a.jpg", min_bytes=10, min_dim=10)
    with pytest.raises(C.DiscoveryError):
        validate_image_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 200, content_type="image/jpeg", final_url="https://www.tosag.ch/a.jpg", min_bytes=10, min_dim=10)
    bad_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
    with pytest.raises(C.DiscoveryError):
        validate_image_bytes(bad_png, content_type="image/png", final_url="https://www.tosag.ch/a.png", min_bytes=10, min_dim=10)


def test_family_and_counters_20_7(external_out: Path, tmp_path: Path) -> None:
    groups = [("1103", 3, RGB_A), ("1106", 10, RGB_B), ("1108", 3, RGB_C), ("1120", 1, RGB_D), ("1122", 1, RGB_E), ("1135", 1, RGB_F), ("1136", 1, RGB_G)]
    rows = []
    routes: dict[str, Any] = {}
    for prefix, count, color in groups:
        detail = f"https://www.tosag.ch/d-{prefix}"
        image = f"https://www.tosag.ch/i-{prefix}.jpg"
        skus = [f"{prefix}-{i}" for i in range(count)]
        page = (
            "<html><h1>INSIZE</h1><p>Brand: INSIZE</p><table>"
            + "".join(f"<tr><td>{sku}</td></tr>" for sku in skus)
            + "</table></html>"
        ).encode()
        routes[detail] = {"body": page}
        routes[image] = {"body": _jpeg(color=color), "ctype": "image/jpeg", "final": image}
        for sku in skus:
            rows.append({"sku": sku, "product_name": sku, "image_url": image, "detail_url": detail, "confidence": "x"})
    cand = tmp_path / "c.csv"
    _write_candidates(cand, rows)
    opener = RecordingUrlOpen(routes)
    summary = run_discovery(
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
    assert summary["requested_rows"] == 20
    assert summary["accepted_rows"] == 20
    assert summary["unique_assets"] == 7
    assert summary["downloaded_unique_assets"] == 7
    assert summary["reused_within_run_rows"] == 13
    assert summary["family_rows"] == 16
    assert summary["singleton_unverified_rows"] == 4


def test_duplicate_bytes_across_urls(external_out: Path, tmp_path: Path) -> None:
    jpeg = _jpeg(color=RGB_A)
    rows = [
        {"sku": "A-1", "product_name": "A", "image_url": "https://www.tosag.ch/u1.jpg", "detail_url": "https://www.tosag.ch/d1", "confidence": "x"},
        {"sku": "A-2", "product_name": "B", "image_url": "https://www.tosag.ch/u2.jpg", "detail_url": "https://www.tosag.ch/d2", "confidence": "x"},
    ]
    cand = tmp_path / "c.csv"
    _write_candidates(cand, rows)
    opener = RecordingUrlOpen(
        {
            "https://www.tosag.ch/d1": {"body": b"<html><h1>INSIZE</h1><p>Art A-1</p></html>"},
            "https://www.tosag.ch/d2": {"body": b"<html><h1>INSIZE</h1><p>Art A-2</p></html>"},
            "https://www.tosag.ch/u1.jpg": {"body": jpeg, "ctype": "image/jpeg", "final": "https://www.tosag.ch/u1.jpg"},
            "https://www.tosag.ch/u2.jpg": {"body": jpeg, "ctype": "image/jpeg", "final": "https://www.tosag.ch/u2.jpg"},
        }
    )
    summary = run_discovery(
        adapter=InsizeTosagAdapter(),
        products_csv=None,
        candidates_csv=cand,
        output_dir=external_out,
        repo_root=REPO_ROOT,
        concurrency=1,
        delay=0,
        fetcher=HostThrottledFetcher(allowed_hosts=frozenset({"www.tosag.ch"}), delay=0, urlopen=opener),
        min_bytes=100,
        min_dim=50,
    )
    assert summary["unique_assets"] == 1
    assert summary["family_rows"] == 2


def test_semantic_hash_stability_sensitivity() -> None:
    base = {k: None for k in C.SEMANTIC_FIELDS}
    base.update(
        {
            "candidate_id": "cid:abc",
            "product_id": "",
            "product_key": "brand_sku:insize:1103-150",
            "identity_basis": "brand_sku",
            "source_candidate_key": "deadbeef",
            "sku": "1103-150",
            "product_name": "A",
            "brand": "INSIZE",
            "source_adapter": "insize_tosag",
            "source_class": "authorized_distributor_candidate",
            "image_role": "primary",
            "source_rank": 1,
            "display_order_candidate": 1,
            "source_image_index": 0,
            "source_detail_url": "https://www.tosag.ch/d",
            "source_image_url": "https://www.tosag.ch/i.jpg",
            "final_image_url": "https://www.tosag.ch/i.jpg",
            "local_asset_path": "assets/x.jpg",
            "sha256": "abc",
            "mime_type": "image/jpeg",
            "extension": "jpg",
            "byte_size": 10,
            "width": 100,
            "height": 100,
            "foreground_occupancy_status": "ok",
            "presentation_note": "",
            "match_confidence": "very_high",
            "sku_confirmed": True,
            "manufacturer_confirmed": True,
            "manufacturer_evidence": "heading",
            "sku_evidence": "art",
            "page_subject_evidence": "h1",
            "image_specificity": "singleton_unverified",
            "variant_specific": "unknown",
            "shared_asset_group": "g1",
            "review_status": "pending_human_review",
            "rights_status": "review_required",
            "provenance_batch": "batch-a",
            "provenance_manifest": "manifests/manifest.json",
            "provenance_source_adapter": "insize_tosag",
        }
    )
    other = dict(base)
    # download_status / notes not in semantic fields
    assert semantic_manifest_sha256([base]) == semantic_manifest_sha256([other])
    changed = dict(base)
    changed["sha256"] = "zzz"
    assert semantic_manifest_sha256([base]) != semantic_manifest_sha256([changed])


def test_second_run_comparison_generated(external_out: Path, tmp_path: Path) -> None:
    detail = "https://www.tosag.ch/s"
    image = "https://www.tosag.ch/s.jpg"
    cand = tmp_path / "c.csv"
    _write_candidates(
        cand,
        [{"sku": "1103-150", "product_name": "A", "image_url": image, "detail_url": detail, "confidence": "x"}],
    )
    page = b"<html><h1>INSIZE</h1><p>Art.Nr: 1103-150</p></html>"
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
    s2 = run_discovery(
        adapter=InsizeTosagAdapter(),
        products_csv=None,
        candidates_csv=cand,
        output_dir=external_out,
        repo_root=REPO_ROOT,
        concurrency=1,
        delay=0,
        resume=True,
        fetcher=fetcher,
        min_bytes=100,
        min_dim=50,
    )
    assert s1["manifest_semantic_sha256"] == s2["manifest_semantic_sha256"]
    assert s2["semantic_manifest_stable"] is True
    assert s2["asset_set_stable"] is True
    assert s2["downloaded_unique_assets"] == 0
    assert (external_out / "manifests" / "run-state.json").exists()


def test_max_images_per_product_and_roles(tmp_path: Path) -> None:
    # Two candidate rows same SKU in CSV — max 1 keeps primary only
    cand = tmp_path / "c.csv"
    rows = [
        {"sku": "X-1", "product_name": "X", "image_url": "https://www.tosag.ch/a.jpg", "detail_url": "https://www.tosag.ch/d", "confidence": "x"},
        {"sku": "X-1", "product_name": "X", "image_url": "https://www.tosag.ch/b.jpg", "detail_url": "https://www.tosag.ch/d", "confidence": "x"},
    ]
    _write_candidates(cand, rows)
    adapter = InsizeTosagAdapter()
    one = adapter.load_candidates(
        products_csv=None,
        candidates_csv=cand,
        sku_filters=None,
        limit=None,
        offset=0,
        max_images_per_product=1,
    )
    assert len(one) == 1
    assert one[0].image_role == "primary"
    two = adapter.load_candidates(
        products_csv=None,
        candidates_csv=cand,
        sku_filters=None,
        limit=None,
        offset=0,
        max_images_per_product=2,
    )
    assert len(two) == 2
    assert two[0].image_role == "primary"
    assert two[1].image_role == "alternate"
    assert two[0].display_order_candidate == 1
    assert two[1].display_order_candidate == 2


def test_consolidation_across_batches(tmp_path: Path) -> None:
    root = tmp_path / "batches"
    out = tmp_path / "consolidated"
    # Build two mini batch outputs via discovery
    for name, color, sku in [("b1", RGB_A, "B1-1"), ("b2", RGB_A, "B2-1")]:
        batch = root / name
        # same bytes → global family after consolidate
        detail = f"https://www.tosag.ch/{name}"
        image = f"https://www.tosag.ch/{name}.jpg"
        cand = tmp_path / f"{name}.csv"
        _write_candidates(
            cand,
            [{"sku": sku, "product_name": sku, "image_url": image, "detail_url": detail, "confidence": "x"}],
        )
        page = f"<html><h1>INSIZE</h1><p>Art {sku}</p></html>".encode()
        jpeg = _jpeg(color=color)
        opener = RecordingUrlOpen({detail: {"body": page}, image: {"body": jpeg, "ctype": "image/jpeg", "final": image}})
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
        )
    summary = consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)
    assert summary["accepted_rows"] == 2
    assert summary["unique_assets"] == 1
    assert summary["family_rows"] == 2
    assert summary["singleton_unverified_rows"] == 0


def test_deterministic_ordering(external_out: Path, tmp_path: Path) -> None:
    rows = [
        {"sku": "Z-9", "product_name": "Z", "image_url": "https://www.tosag.ch/z.jpg", "detail_url": "https://www.tosag.ch/zd", "confidence": "x"},
        {"sku": "A-1", "product_name": "A", "image_url": "https://www.tosag.ch/a.jpg", "detail_url": "https://www.tosag.ch/ad", "confidence": "x"},
    ]
    cand = tmp_path / "c.csv"
    _write_candidates(cand, rows)
    jpeg = _jpeg()
    opener = RecordingUrlOpen(
        {
            "https://www.tosag.ch/zd": {"body": b"<html><h1>INSIZE</h1><p>Art Z-9</p></html>"},
            "https://www.tosag.ch/ad": {"body": b"<html><h1>INSIZE</h1><p>Art A-1</p></html>"},
            "https://www.tosag.ch/z.jpg": {"body": jpeg, "ctype": "image/jpeg", "final": "https://www.tosag.ch/z.jpg"},
            "https://www.tosag.ch/a.jpg": {"body": jpeg, "ctype": "image/jpeg", "final": "https://www.tosag.ch/a.jpg"},
        }
    )
    run_discovery(
        adapter=InsizeTosagAdapter(),
        products_csv=None,
        candidates_csv=cand,
        output_dir=external_out,
        repo_root=REPO_ROOT,
        concurrency=1,
        delay=0,
        fetcher=HostThrottledFetcher(allowed_hosts=frozenset({"www.tosag.ch"}), delay=0, urlopen=opener),
        min_bytes=100,
        min_dim=50,
    )
    man = json.loads((external_out / "manifests" / "manifest.json").read_text())
    assert [m["sku"] for m in man] == ["A-1", "Z-9"]
