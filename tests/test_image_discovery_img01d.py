"""IMG-01D final blocker tests — local/mocked only."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from image_discovery import contracts as C  # noqa: E402
from image_discovery.consolidation import consolidate_batches  # noqa: E402
from image_discovery.output import compare_runs, file_sha256, rename_and_classify  # noqa: E402
from image_discovery.paths import iter_local_asset_files  # noqa: E402
from image_discovery.sources.insize_tosag import InsizeTosagAdapter  # noqa: E402


def _jpeg(color: tuple[int, int, int] = (10, 20, 30)) -> bytes:
    img = Image.new("RGB", (300, 300), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _row(*, sku: str, sha: str, path: str, name: str = "A", brand: str = "INSIZE", sck: str | None = None) -> dict:
    sck = sck or hashlib.sha256(f"{sku}|{path}".encode()).hexdigest()
    _, product_key, basis = C.build_product_identity(brand=brand, sku=sku)
    cid = C.make_candidate_id(
        source_adapter="insize_tosag",
        product_key=product_key,
        source_candidate_key=sck,
        image_role="primary",
    )
    return {
        "candidate_id": cid,
        "product_id": "",
        "product_key": product_key,
        "identity_basis": basis,
        "source_candidate_key": sck,
        "sku": sku,
        "product_name": name,
        "brand": brand,
        "source_adapter": "insize_tosag",
        "source_class": "x",
        "image_role": "primary",
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


def _batch(root: Path, name: str, rows: list[dict], assets: dict[str, bytes] | None = None) -> Path:
    b = root / name
    (b / "manifests").mkdir(parents=True)
    (b / "assets").mkdir(parents=True)
    for fname, data in (assets or {}).items():
        (b / "assets" / fname).write_bytes(data)
    (b / "manifests" / "manifest.json").write_text(json.dumps(rows), encoding="utf-8")
    return b


# --- §1 structural parser ---


def test_nested_related_block_does_not_leak_labeled_sku() -> None:
    html = """<html>
      <h1>INSIZE Other Product</h1>
      <section class="related">
        <section><p>intro</p></section>
        <p>SKU: 1103-150</p>
      </section>
    </html>"""
    ev = InsizeTosagAdapter().validate_page(sku="1103-150", page_html=html, detail_url="https://www.tosag.ch/x")
    assert ev.manufacturer_confirmed is True
    assert ev.sku_confirmed is False
    assert ev.reason_code == "exact_sku_not_confirmed"


def test_nested_related_heading_does_not_confirm_sku() -> None:
    html = """<html><h1>INSIZE Main</h1>
      <div class="related"><div><h2>1103-150</h2></div></div></html>"""
    ev = InsizeTosagAdapter().validate_page(sku="1103-150", page_html=html, detail_url="https://www.tosag.ch/x")
    assert ev.sku_confirmed is False


def test_nested_related_variation_table_does_not_confirm_sku() -> None:
    html = """<html><h1>INSIZE Main</h1>
      <section class="related"><table><tr><td>1103-150</td></tr></table></section></html>"""
    ev = InsizeTosagAdapter().validate_page(sku="1103-150", page_html=html, detail_url="https://www.tosag.ch/x")
    assert ev.sku_confirmed is False


def test_nested_cross_sell_article_rejects() -> None:
    html = """<html><h1>INSIZE Main</h1>
      <article class="cross-sell"><p>Art.Nr: 1103-150</p></article></html>"""
    ev = InsizeTosagAdapter().validate_page(sku="1103-150", page_html=html, detail_url="https://www.tosag.ch/x")
    assert ev.sku_confirmed is False


def test_nested_breadcrumb_wrapper_rejects() -> None:
    html = """<html><h1>INSIZE Main</h1>
      <nav class="breadcrumb"><span>SKU 1103-150</span></nav></html>"""
    ev = InsizeTosagAdapter().validate_page(sku="1103-150", page_html=html, detail_url="https://www.tosag.ch/x")
    assert ev.sku_confirmed is False


def test_malformed_recoverable_nested_html() -> None:
    html = """<html><h1>INSIZE Main</h1>
      <section class="related"><section><p>x</section>
      <p>SKU: 1103-150</p></section></html>"""
    ev = InsizeTosagAdapter().validate_page(sku="1103-150", page_html=html, detail_url="https://www.tosag.ch/x")
    assert ev.sku_confirmed is False


def test_main_subject_sku_plus_unrelated_other_sku() -> None:
    html = """<html><h1>INSIZE 1103-150</h1><p>Art.Nr: 1103-150</p>
      <section class="related"><p>SKU: 9999-001</p></section></html>"""
    ev = InsizeTosagAdapter().validate_page(sku="1103-150", page_html=html, detail_url="https://www.tosag.ch/x")
    assert ev.sku_confirmed is True
    assert ev.manufacturer_confirmed is True


def test_main_subject_other_sku_plus_unrelated_requested_sku() -> None:
    html = """<html><h1>INSIZE Other</h1><p>Art.Nr: 1103-200</p>
      <section class="related"><p>SKU: 1103-150</p></section></html>"""
    ev = InsizeTosagAdapter().validate_page(sku="1103-150", page_html=html, detail_url="https://www.tosag.ch/x")
    assert ev.sku_confirmed is False


# --- §2 allow-replace recognition ---


def test_allow_replace_rejects_assets_only_directory(tmp_path: Path) -> None:
    root = tmp_path / "batches"
    root.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    (out / "assets").mkdir()
    (out / "assets" / "unrelated.txt").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit, match="allow-replace|coherent|recogn"):
        consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT, allow_replace=True)


def test_allow_replace_rejects_partial_output_signature(tmp_path: Path) -> None:
    root = tmp_path / "batches"
    root.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    (out / "manifests").mkdir()
    (out / "manifests" / "manifest.json").write_text("[]", encoding="utf-8")
    # missing summary + assets
    with pytest.raises(SystemExit, match="allow-replace|coherent|recogn"):
        consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT, allow_replace=True)

    out2 = tmp_path / "out2"
    out2.mkdir()
    (out2 / "summary.json").write_text('{"pilot_id":"IMG-01D"}', encoding="utf-8")
    with pytest.raises(SystemExit, match="allow-replace|coherent|recogn"):
        consolidate_batches(input_dir=root, output_dir=out2, repo_root=REPO_ROOT, allow_replace=True)


def test_allow_replace_rejects_unknown_files(tmp_path: Path) -> None:
    jpeg = _jpeg()
    sha = hashlib.sha256(jpeg).hexdigest()
    root = tmp_path / "batches"
    _batch(root, "b1", [], {})
    out = tmp_path / "out"
    out.mkdir()
    (out / "assets").mkdir()
    (out / "manifests").mkdir()
    (out / "assets" / "a.jpg").write_bytes(jpeg)
    row = _row(sku="A-1", sha=sha, path="assets/a.jpg")
    (out / "manifests" / "manifest.json").write_text(json.dumps([row]), encoding="utf-8")
    (out / "summary.json").write_text(
        json.dumps({"pilot_id": "IMG-01D-CONSOLIDATE", "status": "ok"}), encoding="utf-8"
    )
    (out / "stray.txt").write_text("nope", encoding="utf-8")
    with pytest.raises(SystemExit, match="allow-replace|unknown|coherent"):
        consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT, allow_replace=True)


def test_allow_replace_reports_stale_governed_assets(tmp_path: Path) -> None:
    jpeg = _jpeg()
    sha = hashlib.sha256(jpeg).hexdigest()
    stale = _jpeg(color=(1, 2, 3))
    root = tmp_path / "batches"
    root.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    (out / "assets").mkdir()
    (out / "manifests").mkdir()
    (out / "assets" / "a.jpg").write_bytes(jpeg)
    (out / "assets" / "stale.jpg").write_bytes(stale)
    row = _row(sku="A-1", sha=sha, path="assets/a.jpg")
    (out / "manifests" / "manifest.json").write_text(json.dumps([row]), encoding="utf-8")
    (out / "summary.json").write_text(
        json.dumps({"pilot_id": "IMG-01D-CONSOLIDATE", "status": "ok"}), encoding="utf-8"
    )
    with pytest.raises(SystemExit, match="stale"):
        consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT, allow_replace=True)
    stale_csv = out / "manifests" / "preexisting-stale-files.csv"
    assert stale_csv.exists()
    rows = list(csv.DictReader(stale_csv.open(encoding="utf-8")))
    assert any("stale.jpg" in r["relative_path"] for r in rows)
    assert (out / "assets" / "stale.jpg").exists()  # not deleted


def test_allow_replace_accepts_recognized_clean_prior(tmp_path: Path) -> None:
    jpeg = _jpeg()
    sha = hashlib.sha256(jpeg).hexdigest()
    root = tmp_path / "batches"
    _batch(root, "b1", [_row(sku="A-1", sha=sha, path="assets/x.jpg")], {"x.jpg": jpeg})
    out = tmp_path / "out"
    # first consolidate into empty
    consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)
    # second with allow-replace on clean prior
    summary = consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT, allow_replace=True)
    assert summary["status"] == "ok"


# --- §3/§5 manifest contract ---


def test_consolidation_rejects_missing_manifest_sha(tmp_path: Path) -> None:
    jpeg = _jpeg()
    root = tmp_path / "batches"
    row = _row(sku="A-1", sha=hashlib.sha256(jpeg).hexdigest(), path="assets/x.jpg")
    row["sha256"] = ""
    _batch(root, "b1", [row], {"x.jpg": jpeg})
    out = tmp_path / "out"
    with pytest.raises(SystemExit, match="integrity"):
        consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)
    assert json.loads((out / "summary.json").read_text())["status"] == "integrity_failure"
    rej = list(csv.DictReader((out / "manifests" / "rejected.csv").open(encoding="utf-8")))
    assert any(r["reason_code"] == "missing_manifest_sha256" for r in rej)


def test_consolidation_rejects_invalid_manifest_sha(tmp_path: Path) -> None:
    jpeg = _jpeg()
    root = tmp_path / "batches"
    row = _row(sku="A-1", sha=hashlib.sha256(jpeg).hexdigest(), path="assets/x.jpg")
    row["sha256"] = "ZZZZ"
    _batch(root, "b1", [row], {"x.jpg": jpeg})
    out = tmp_path / "out"
    with pytest.raises(SystemExit, match="integrity"):
        consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)
    rej = list(csv.DictReader((out / "manifests" / "rejected.csv").open(encoding="utf-8")))
    assert any(r["reason_code"] == "invalid_manifest_sha256" for r in rej)


def test_consolidation_rejects_missing_candidate_id(tmp_path: Path) -> None:
    jpeg = _jpeg()
    root = tmp_path / "batches"
    row = _row(sku="A-1", sha=hashlib.sha256(jpeg).hexdigest(), path="assets/x.jpg")
    row["candidate_id"] = ""
    _batch(root, "b1", [row], {"x.jpg": jpeg})
    out = tmp_path / "out"
    with pytest.raises(SystemExit, match="integrity"):
        consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)
    summary = json.loads((out / "summary.json").read_text())
    assert summary["status"] == "integrity_failure"
    assert summary["integrity_failure_count"] >= 1
    rej = list(csv.DictReader((out / "manifests" / "rejected.csv").open(encoding="utf-8")))
    assert any(r["reason_code"] == "missing_candidate_id" for r in rej)


def test_consolidation_rejects_invalid_candidate_id(tmp_path: Path) -> None:
    jpeg = _jpeg()
    root = tmp_path / "batches"
    row = _row(sku="A-1", sha=hashlib.sha256(jpeg).hexdigest(), path="assets/x.jpg")
    row["candidate_id"] = "cid:not-hex"
    _batch(root, "b1", [row], {"x.jpg": jpeg})
    out = tmp_path / "out"
    with pytest.raises(SystemExit, match="integrity"):
        consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)
    rej = list(csv.DictReader((out / "manifests" / "rejected.csv").open(encoding="utf-8")))
    assert any(r["reason_code"] == "invalid_candidate_id" for r in rej)


def test_consolidation_rejects_candidate_id_mismatch(tmp_path: Path) -> None:
    jpeg = _jpeg()
    root = tmp_path / "batches"
    row = _row(sku="A-1", sha=hashlib.sha256(jpeg).hexdigest(), path="assets/x.jpg")
    row["candidate_id"] = "cid:" + ("f" * 64)
    _batch(root, "b1", [row], {"x.jpg": jpeg})
    out = tmp_path / "out"
    with pytest.raises(SystemExit, match="integrity"):
        consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)
    rej = list(csv.DictReader((out / "manifests" / "rejected.csv").open(encoding="utf-8")))
    assert any(r["reason_code"] == "candidate_id_mismatch" for r in rej)


def test_consolidation_rejects_missing_required_identity_fields(tmp_path: Path) -> None:
    jpeg = _jpeg()
    root = tmp_path / "batches"
    out = tmp_path / "out"
    for field, code in [
        ("product_key", "missing_product_key"),
        ("source_candidate_key", "missing_source_candidate_key"),
        ("source_adapter", "missing_source_adapter"),
    ]:
        row = _row(sku="A-1", sha=hashlib.sha256(jpeg).hexdigest(), path="assets/x.jpg")
        row[field] = ""
        # keep candidate_id as-is so we hit the field check (may also mismatch — clear cid after empty product_key)
        if field != "source_adapter":
            row["candidate_id"] = "cid:" + ("a" * 64)  # valid format but will fail field or mismatch
        batch_root = root / field
        if batch_root.exists():
            import shutil

            shutil.rmtree(batch_root)
        _batch(batch_root, "b1", [row], {"x.jpg": jpeg})
        out_i = out / field
        with pytest.raises(SystemExit, match="integrity"):
            consolidate_batches(input_dir=batch_root, output_dir=out_i, repo_root=REPO_ROOT)
        rej = list(csv.DictReader((out_i / "manifests" / "rejected.csv").open(encoding="utf-8")))
        codes = {r["reason_code"] for r in rej}
        assert code in codes or "candidate_id_mismatch" in codes or "invalid_candidate_id" in codes


# --- §4 no-follow ---


def test_compare_runs_does_not_follow_symlink(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    secret = tmp_path / "secret.bin"
    secret.write_bytes(b"SECRET-EXTERNAL")
    secret.chmod(0o000)
    link = assets / "link.bin"
    link.symlink_to(secret)
    hashed: list[Path] = []

    def guarded_sha(path: Path) -> str:
        hashed.append(path)
        if path.resolve() == secret.resolve() or path == secret:
            raise AssertionError("hashed external secret")
        return file_sha256(path)

    with pytest.raises(C.DiscoveryError) as e:
        compare_runs(
            previous_state={},
            previous_manifest=[],
            current_manifest=[],
            current_semantic="0" * 64,
            asset_dir=assets,
        )
    assert e.value.reason_code == "unexpected_asset_symlink"
    secret.chmod(0o600)


def test_materialize_scan_does_not_follow_symlink(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    secret = tmp_path / "secret.bin"
    secret.write_bytes(b"SECRET")
    (assets / "link.bin").symlink_to(secret)
    with pytest.raises(C.DiscoveryError) as e:
        list(iter_local_asset_files(assets, fail_closed=True))
    assert e.value.reason_code == "unexpected_asset_symlink"


def test_classification_scan_does_not_follow_symlink(tmp_path: Path) -> None:
    out = tmp_path / "out"
    (out / "assets").mkdir(parents=True)
    secret = tmp_path / "secret.jpg"
    secret.write_bytes(_jpeg())
    (out / "assets" / "link.jpg").symlink_to(secret)
    jpeg = _jpeg(color=(9, 9, 9))
    sha = hashlib.sha256(jpeg).hexdigest()
    (out / "assets" / f"pending__{sha[:12]}.jpg").write_bytes(jpeg)
    rows = [
        {
            "sku": "A-1",
            "brand": "INSIZE",
            "product_key": "brand_sku:insize:a-1",
            "sha256": sha,
            "extension": "jpg",
            "local_asset_path": f"assets/pending__{sha[:12]}.jpg",
            "candidate_id": "cid:" + ("1" * 64),
        }
    ]
    with pytest.raises(C.DiscoveryError) as e:
        rename_and_classify(rows, out)
    assert e.value.reason_code == "unexpected_asset_symlink"


def test_pending_cleanup_does_not_follow_symlink(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    secret = tmp_path / "secret.bin"
    secret.write_bytes(b"SECRET")
    (assets / "pending__deadbeef").symlink_to(secret)  # name looks pending but is symlink
    # Force pending-like symlink name
    link = assets / "pending__aabbccddee12.bin"
    if link.exists() or link.is_symlink():
        link.unlink()
    link.symlink_to(secret)
    with pytest.raises(C.DiscoveryError) as e:
        list(iter_local_asset_files(assets, fail_closed=True))
    assert e.value.reason_code == "unexpected_asset_symlink"


def test_duplicate_physical_assets_are_reported(tmp_path: Path) -> None:
    jpeg = _jpeg()
    sha = hashlib.sha256(jpeg).hexdigest()
    root = tmp_path / "batches"
    row = _row(sku="A-1", sha=sha, path="assets/x.jpg")
    _batch(root, "b1", [row], {"x.jpg": jpeg})
    out = tmp_path / "out"
    consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)
    # plant a second physical copy with same bytes
    assets = out / "assets"
    files = list(iter_local_asset_files(assets, fail_closed=True))
    assert files
    dup = assets / "copy_extra.jpg"
    dup.write_bytes(jpeg)
    by_sha, _ = __import__("image_discovery.paths", fromlist=["inventory_assets_by_sha"]).inventory_assets_by_sha(
        assets, file_sha256=file_sha256, fail_closed=True
    )
    assert len(by_sha[sha]) >= 2
    from image_discovery.consolidation import _write_duplicate_physical_report

    groups, nfiles = _write_duplicate_physical_report(out, by_sha)
    assert groups >= 1
    assert nfiles >= 2
    assert (out / "manifests" / "duplicate-physical-assets.csv").exists()
