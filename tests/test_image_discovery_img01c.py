"""IMG-01C targeted correction tests — local/mocked only."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from typing import Any
from urllib.request import Request

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from image_discovery import contracts as C  # noqa: E402
from image_discovery.atomic import atomic_write_text  # noqa: E402
from image_discovery.consolidation import consolidate_batches  # noqa: E402
from image_discovery.core import run_discovery  # noqa: E402
from image_discovery.output import _write_contact_sheet, safe_href  # noqa: E402
from image_discovery.paths import resolve_manifest_asset_path  # noqa: E402
from image_discovery.sources.insize_tosag import InsizeTosagAdapter  # noqa: E402
from image_discovery.transport import HostThrottledFetcher  # noqa: E402


def _jpeg(color: tuple[int, int, int] = (10, 20, 30)) -> bytes:
    img = Image.new("RGB", (300, 300), color)
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

    def __call__(self, req: Request, timeout: float):
        url = req.full_url
        self.calls.append(url)
        item = self.routes[url]

        class Resp:
            def __init__(self):
                self.status = 200
                self._body = item["body"]
                self.headers = {"Content-Type": item.get("ctype", "text/html")}
                self._final = item.get("final", url)

            def read(self, n: int = -1):
                if n is None or n < 0:
                    data, self._body = self._body, b""
                    return data
                data, self._body = self._body[:n], self._body[n:]
                return data

            def getcode(self):
                return 200

            def geturl(self):
                return self._final

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return Resp()


def _base_row(
    *,
    sku: str,
    sha: str,
    path: str,
    name: str = "A",
    brand: str = "INSIZE",
    source_candidate_key: str | None = None,
    image_role: str = "primary",
    cid: str | None = None,
) -> dict:
    """Build a contract-valid Manifest row. ``cid`` is ignored; identity is recomputed."""
    sck = source_candidate_key or hashlib.sha256(f"{sku}|{path}".encode()).hexdigest()
    _, product_key, basis = C.build_product_identity(brand=brand, sku=sku)
    computed = C.make_candidate_id(
        source_adapter="insize_tosag",
        product_key=product_key,
        source_candidate_key=sck,
        image_role=image_role,
    )
    return {
        "candidate_id": computed,
        "product_id": "",
        "product_key": product_key,
        "identity_basis": basis,
        "source_candidate_key": sck,
        "sku": sku,
        "product_name": name,
        "brand": brand,
        "source_adapter": "insize_tosag",
        "source_class": "x",
        "image_role": image_role,
        "source_rank": 1,
        "display_order_candidate": 1,
        "source_image_index": 0,
        "source_detail_url": "https://www.tosag.ch/d",
        "source_image_url": "https://www.tosag.ch/i.jpg",
        "final_image_url": "https://www.tosag.ch/i.jpg",
        "local_asset_path": path,
        "sha256": sha,
        "mime_type": "image/jpeg",
        "extension": "jpg",
        "byte_size": 100,
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


def test_consolidation_rejects_relative_path_escape(tmp_path: Path) -> None:
    root = tmp_path / "batches"
    b = root / "b1"
    (b / "manifests").mkdir(parents=True)
    (b / "assets").mkdir(parents=True)
    secret = tmp_path / "secret.jpg"
    secret.write_bytes(_jpeg())
    jpeg = _jpeg(color=(1, 2, 3))
    sha = hashlib.sha256(jpeg).hexdigest()
    (b / "assets" / "ok.jpg").write_bytes(jpeg)
    row = _base_row(cid="cid:1", sku="A-1", sha=sha, path="assets/../../secret.jpg")
    (b / "manifests" / "manifest.json").write_text(json.dumps([row]), encoding="utf-8")
    out = tmp_path / "cons"
    with pytest.raises(SystemExit, match="integrity"):
        consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)
    # secret must not appear under consolidated assets
    assert not any(p.name == "secret.jpg" for p in (out / "assets").glob("*"))


def test_consolidation_rejects_absolute_asset_path(tmp_path: Path) -> None:
    root = tmp_path / "batches"
    b = root / "b1"
    (b / "manifests").mkdir(parents=True)
    (b / "assets").mkdir(parents=True)
    jpeg = _jpeg()
    sha = hashlib.sha256(jpeg).hexdigest()
    abs_path = str((tmp_path / "outside.jpg").resolve())
    (tmp_path / "outside.jpg").write_bytes(jpeg)
    row = _base_row(cid="cid:1", sku="A-1", sha=sha, path=abs_path)
    (b / "manifests" / "manifest.json").write_text(json.dumps([row]), encoding="utf-8")
    out = tmp_path / "cons"
    with pytest.raises(SystemExit, match="integrity"):
        consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)
    rej = list(csv.DictReader((out / "manifests" / "rejected.csv").open(encoding="utf-8")))
    assert any(r["reason_code"] == "asset_path_absolute" for r in rej)


def test_consolidation_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "batches"
    b = root / "b1"
    (b / "manifests").mkdir(parents=True)
    (b / "assets").mkdir(parents=True)
    outside = tmp_path / "outside.jpg"
    outside.write_bytes(_jpeg(color=(9, 9, 9)))
    link = b / "assets" / "linked.jpg"
    link.symlink_to(outside)
    sha = hashlib.sha256(outside.read_bytes()).hexdigest()
    row = _base_row(cid="cid:1", sku="A-1", sha=sha, path="assets/linked.jpg")
    (b / "manifests" / "manifest.json").write_text(json.dumps([row]), encoding="utf-8")
    out = tmp_path / "cons"
    with pytest.raises(SystemExit, match="integrity"):
        consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)
    rej = list(csv.DictReader((out / "manifests" / "rejected.csv").open(encoding="utf-8")))
    assert any(r["reason_code"] in {"asset_symlink_escape", "asset_path_escape", "unexpected_asset_symlink"} for r in rej)


def test_resume_rejects_asset_path_escape(external_out: Path, tmp_path: Path) -> None:
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
    man = json.loads((external_out / "manifests" / "manifest.json").read_text())
    man[0]["local_asset_path"] = "assets/../secret.jpg"
    (external_out / "manifests" / "manifest.json").write_text(json.dumps(man), encoding="utf-8")
    summary = run_discovery(
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
    # escape causes resume path to fail closed into reject (or re-fetch if network); must not read outside
    assert summary["accepted_rows"] + summary["rejected_rows"] == 1
    if summary["rejected_rows"]:
        rej = list(csv.DictReader((external_out / "manifests" / "rejected.csv").open(encoding="utf-8")))
        assert rej[0]["reason_code"] in {
            "asset_path_escape",
            "missing_source_asset",
            "detail_fetch_failed",
            "unexpected_error",
        }


def test_exact_duplicate_across_batches_deduplicates(tmp_path: Path) -> None:
    root = tmp_path / "batches"
    jpeg = _jpeg()
    sha = hashlib.sha256(jpeg).hexdigest()
    for name in ("b1", "b2"):
        b = root / name
        (b / "manifests").mkdir(parents=True)
        (b / "assets").mkdir(parents=True)
        (b / "assets" / "x.jpg").write_bytes(jpeg)
        row = _base_row(cid="cid:same", sku="A-1", sha=sha, path="assets/x.jpg", name="Same")
        (b / "manifests" / "manifest.json").write_text(json.dumps([row]), encoding="utf-8")
    out = tmp_path / "cons"
    summary = consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)
    assert summary["accepted_rows"] == 1
    assert summary.get("status") == "ok"
    prov = json.loads((out / "manifests" / "candidate-provenance.json").read_text())
    assert len(prov) == 2
    assert {p["provenance_batch"] for p in prov} == {"b1", "b2"}


def test_duplicate_candidate_preserves_all_provenance(tmp_path: Path) -> None:
    test_exact_duplicate_across_batches_deduplicates(tmp_path)


def test_duplicate_occurrence_asset_integrity_checked(tmp_path: Path) -> None:
    root = tmp_path / "batches"
    jpeg = _jpeg()
    sha = hashlib.sha256(jpeg).hexdigest()
    # good batch
    b1 = root / "b1"
    (b1 / "manifests").mkdir(parents=True)
    (b1 / "assets").mkdir(parents=True)
    (b1 / "assets" / "x.jpg").write_bytes(jpeg)
    row = _base_row(cid="cid:same", sku="A-1", sha=sha, path="assets/x.jpg")
    (b1 / "manifests" / "manifest.json").write_text(json.dumps([row]), encoding="utf-8")
    # bad duplicate batch — missing asset
    b2 = root / "b2"
    (b2 / "manifests").mkdir(parents=True)
    (b2 / "assets").mkdir(parents=True)
    (b2 / "manifests" / "manifest.json").write_text(json.dumps([row]), encoding="utf-8")
    out = tmp_path / "cons"
    with pytest.raises(SystemExit, match="integrity"):
        consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)
    summary = json.loads((out / "summary.json").read_text())
    assert summary["status"] == "integrity_failure"
    assert summary["integrity_failure_count"] >= 1


def test_nonempty_output_rejected_without_allow_replace(tmp_path: Path) -> None:
    root = tmp_path / "batches"
    root.mkdir()
    out = tmp_path / "cons"
    out.mkdir()
    (out / "unrelated.txt").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit, match="non-empty"):
        consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)

    out2 = tmp_path / "cons2"
    out2.mkdir()
    (out2 / "assets").mkdir()
    with pytest.raises(SystemExit, match="non-empty"):
        consolidate_batches(input_dir=root, output_dir=out2, repo_root=REPO_ROOT)

    out3 = tmp_path / "cons3"
    out3.mkdir()
    (out3 / "manifests").mkdir()
    (out3 / "manifests" / "run-state.json").write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit, match="non-empty"):
        consolidate_batches(input_dir=root, output_dir=out3, repo_root=REPO_ROOT)


def test_integrity_rejections_exit_nonzero(tmp_path: Path) -> None:
    root = tmp_path / "batches"
    b = root / "b1"
    (b / "manifests").mkdir(parents=True)
    (b / "assets").mkdir(parents=True)
    jpeg = _jpeg()
    (b / "assets" / "x.jpg").write_bytes(jpeg)
    row = _base_row(cid="cid:1", sku="A-1", sha="0" * 64, path="assets/x.jpg")
    (b / "manifests" / "manifest.json").write_text(json.dumps([row]), encoding="utf-8")
    out = tmp_path / "cons"
    with pytest.raises(SystemExit, match="integrity"):
        consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)
    s = json.loads((out / "summary.json").read_text())
    assert s["status"] == "integrity_failure"
    assert s["integrity_failure_count"] >= 1


def test_duplicate_csv_candidates_deduplicated_before_roles(tmp_path: Path) -> None:
    cand = tmp_path / "c.csv"
    rows = [
        {"sku": "X-1", "product_name": "X", "image_url": "https://www.tosag.ch/a.jpg", "detail_url": "https://www.tosag.ch/d", "confidence": "x"},
        {"sku": "X-1", "product_name": "X", "image_url": "https://www.tosag.ch/a.jpg", "detail_url": "https://www.tosag.ch/d", "confidence": "x"},
        {"sku": "X-1", "product_name": "X", "image_url": "https://www.tosag.ch/b.jpg", "detail_url": "https://www.tosag.ch/d", "confidence": "x"},
    ]
    _write_candidates(cand, rows)
    adapter = InsizeTosagAdapter()
    one = adapter.load_candidates(
        products_csv=None, candidates_csv=cand, sku_filters=None, limit=None, offset=0, max_images_per_product=1
    )
    assert len(one) == 1
    assert one[0].image_role == "primary"
    two = adapter.load_candidates(
        products_csv=None, candidates_csv=cand, sku_filters=None, limit=None, offset=0, max_images_per_product=2
    )
    assert len(two) == 2
    assert two[0].image_role == "primary"
    assert two[1].image_role == "alternate"
    assert two[0].image_url != two[1].image_url
    # identity stable: adding duplicates does not change first candidate_id
    only = adapter.load_candidates(
        products_csv=None,
        candidates_csv=cand,
        sku_filters=None,
        limit=None,
        offset=0,
        max_images_per_product=2,
    )
    assert only[0].candidate_id == two[0].candidate_id


def test_empty_rejected_provenance_is_filled(tmp_path: Path) -> None:
    root = tmp_path / "batches"
    b = root / "b1"
    (b / "manifests").mkdir(parents=True)
    (b / "assets").mkdir(parents=True)
    with (b / "manifests" / "rejected.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=C.REJECT_FIELDS)
        w.writeheader()
        w.writerow(
            {
                "candidate_id": "cid:r",
                "product_id": "",
                "product_key": "",
                "sku": "Z-1",
                "product_name": "Z",
                "brand": "INSIZE",
                "stage": "detail",
                "reason_code": "x",
                "reason_detail": "y",
                "detail_url": "",
                "image_url": "",
                "http_status": "",
                "provenance_batch": "",
                "provenance_manifest": "",
                "provenance_source_adapter": "",
            }
        )
    (b / "manifests" / "manifest.json").write_text("[]", encoding="utf-8")
    out = tmp_path / "cons"
    summary = consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)
    assert summary["rejected_rows"] == 1
    rej = list(csv.DictReader((out / "manifests" / "rejected.csv").open(encoding="utf-8")))
    assert rej[0]["provenance_batch"] == "b1"
    assert rej[0]["provenance_manifest"] == "manifests/rejected.csv"


def test_conflict_summary_uses_atomic_writer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "batches"
    jpeg = _jpeg()
    sha = hashlib.sha256(jpeg).hexdigest()
    for name, pname in [("b1", "Left"), ("b2", "Right")]:
        b = root / name
        (b / "manifests").mkdir(parents=True)
        (b / "assets").mkdir(parents=True)
        (b / "assets" / "x.jpg").write_bytes(jpeg)
        row = _base_row(cid="cid:same", sku="A-1", sha=sha, path="assets/x.jpg", name=pname)
        (b / "manifests" / "manifest.json").write_text(json.dumps([row]), encoding="utf-8")
    out = tmp_path / "cons"
    calls: list[Path] = []
    real = atomic_write_text

    def wrapped(path: Path, text: str, *, encoding: str = "utf-8") -> None:
        calls.append(path)
        return real(path, text, encoding=encoding)

    monkeypatch.setattr("image_discovery.consolidation.atomic_write_text", wrapped)
    with pytest.raises(SystemExit, match="conflict"):
        consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)
    assert any(p.name == "summary.json" for p in calls)


def test_contact_sheet_blocks_unsafe_url_schemes(tmp_path: Path) -> None:
    assert safe_href("javascript:alert(1)") is None
    assert safe_href("data:text/html,hi") is None
    assert safe_href("file:///etc/passwd") is None
    assert safe_href("https://www.tosag.ch/valid") == "https://www.tosag.ch/valid"
    out = tmp_path / "sheet"
    (out / "assets").mkdir(parents=True)
    rows = [
        {
            "sku": "A-1",
            "candidate_id": "c1",
            "shared_asset_group": "g1",
            "local_asset_path": "assets/x.jpg",
            "source_detail_url": "javascript:alert(1)",
            "source_image_url": "https://www.tosag.ch/i.jpg",
            "product_name": "A",
            "brand": "INSIZE",
            "product_key": "k",
            "image_role": "primary",
            "source_rank": 1,
            "image_specificity": "singleton_unverified",
            "variant_specific": "unknown",
            "foreground_occupancy_status": "ok",
            "review_status": "pending_human_review",
            "rights_status": "review_required",
            "provenance_batch": "b",
            "provenance_manifest": "m",
            "manufacturer_evidence": "",
            "sku_evidence": "",
            "sha256": "a" * 64,
            "width": 1,
            "height": 1,
        }
    ]
    (out / "assets" / "x.jpg").write_bytes(b"x")
    _write_contact_sheet(out, rows)
    html = (out / "review" / "contact-sheet.html").read_text(encoding="utf-8")
    assert "javascript:alert(1)" in html
    assert "href='javascript:" not in html
    assert "href=\"javascript:" not in html
    assert "href='https://www.tosag.ch/i.jpg'" in html


def test_high_reuse_asset_report(tmp_path: Path) -> None:
    from image_discovery.output import high_reuse_asset_rows, write_outputs

    jpeg = _jpeg()
    sha = hashlib.sha256(jpeg).hexdigest()
    out = tmp_path / "out"
    (out / "assets").mkdir(parents=True)
    (out / "assets" / "x.jpg").write_bytes(jpeg)
    rows = []
    for i in range(10):
        sku = f"SKU-{i}"
        rows.append(
            _base_row(
                sku=sku,
                sha=sha,
                path="assets/x.jpg",
                source_candidate_key=hashlib.sha256(f"k{i}".encode()).hexdigest(),
            )
        )
    high = high_reuse_asset_rows(rows, threshold=8)
    assert len(high) == 1
    assert high[0]["sku_count"] == 10
    write_outputs(out, rows, [], high_reuse=high)
    assert (out / "manifests" / "high-reuse-assets.csv").exists()


def test_resolve_rejects_directory_and_missing(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "subdir").mkdir()
    with pytest.raises(C.DiscoveryError) as e:
        resolve_manifest_asset_path(assets_root=assets, local_asset_path="assets/subdir")
    assert e.value.reason_code == "asset_path_not_file"
    with pytest.raises(C.DiscoveryError) as e2:
        resolve_manifest_asset_path(assets_root=assets, local_asset_path="assets/missing.jpg")
    assert e2.value.reason_code == "missing_source_asset"
