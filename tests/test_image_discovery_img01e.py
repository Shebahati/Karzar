"""IMG-01E — structured evidence isolation, atomic JSON-LD, symlink roots, run output policy."""

from __future__ import annotations

import csv
import hashlib
import io
import json
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
from image_discovery.consolidation import (  # noqa: E402
    consolidate_batches,
    recognize_prior_discovery_output,
)
from image_discovery.core import enforce_run_output_policy, run_discovery  # noqa: E402
from image_discovery.output import compare_runs, file_sha256  # noqa: E402
from image_discovery.paths import (  # noqa: E402
    assert_batch_roots_nofollow,
    assert_run_output_roots_nofollow,
    inventory_assets_by_sha,
)
from image_discovery.sources.insize_tosag import InsizeTosagAdapter  # noqa: E402
from image_discovery.transport import HostThrottledFetcher  # noqa: E402

SKU = "1103-150"
ADAPTER = InsizeTosagAdapter()


def _jpeg(color: tuple[int, int, int] = (10, 20, 30)) -> bytes:
    img = Image.new("RGB", (300, 300), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _json_ld(products: list[dict[str, Any]], *, wrapper_attrs: str = "") -> str:
    scripts = []
    for p in products:
        scripts.append(
            f'<script type="application/ld+json">{json.dumps({"@type": "Product", **p})}</script>'
        )
    inner = "\n".join(scripts)
    if wrapper_attrs:
        return f"<div {wrapper_attrs}>{inner}</div>"
    return inner


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

    def __call__(self, req: Request, timeout: float):
        url = req.full_url
        item = self.routes.get(url)
        if item is None:
            raise C.DiscoveryError("fetch", "detail_fetch_failed", f"missing {url}")
        if item.get("redirect"):
            raise HTTPError(url, item.get("code", 302), "redirect", {"Location": item["redirect"]}, io.BytesIO())

        class Resp:
            def __init__(self, body: bytes, ctype: str, final: str):
                self._body = body
                self.headers = {"Content-Type": ctype}
                self.status = 200
                self.url = final

            def read(self, n: int = -1) -> bytes:
                if n < 0:
                    out, self._body = self._body, b""
                    return out
                out, self._body = self._body[:n], self._body[n:]
                return out

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return Resp(item["body"], item.get("ctype", "text/html"), item.get("final", url))


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


def _row(*, sku: str, sha: str, path: str) -> dict[str, Any]:
    cid = "cid:" + hashlib.sha256(f"{sku}:{sha}".encode()).hexdigest()
    return {
        "candidate_id": cid,
        "sku": sku,
        "product_name": sku,
        "brand": "INSIZE",
        "product_id": "",
        "product_key": f"brand_sku:insize:{sku.lower()}",
        "identity_basis": "brand_sku",
        "source_adapter": "insize_tosag",
        "source_candidate_key": hashlib.sha256(path.encode()).hexdigest(),
        "image_role": "primary",
        "source_rank": 1,
        "display_order_candidate": 1,
        "source_image_index": 0,
        "sha256": sha,
        "local_asset_path": path,
        "extension": "jpg",
        "mime_type": "image/jpeg",
        "byte_size": 100,
        "width": 300,
        "height": 300,
        "source_detail_url": "https://www.tosag.ch/x",
        "source_image_url": "https://www.tosag.ch/x.jpg",
        "final_image_url": "https://www.tosag.ch/x.jpg",
        "manufacturer_confirmed": True,
        "sku_confirmed": True,
        "download_status": "downloaded_new",
        "rights_status": "review_required",
        "review_status": "pending_human_review",
        "image_specificity": "singleton_unverified",
        "variant_specific": "unknown",
        "shared_asset_group": "",
        "provenance_batch": "b1",
        "provenance_manifest": "manifests/manifest.json",
        "provenance_source_adapter": "insize_tosag",
    }


def _coherent_prior(out: Path, *, jpeg: bytes | None = None) -> dict[str, Any]:
    jpeg = jpeg or _jpeg()
    sha = hashlib.sha256(jpeg).hexdigest()
    (out / "assets").mkdir(parents=True, exist_ok=True)
    (out / "manifests").mkdir(parents=True, exist_ok=True)
    name = f"insize__a__{sha[:12]}.jpg"
    (out / "assets" / name).write_bytes(jpeg)
    row = _row(sku=SKU, sha=sha, path=f"assets/{name}")
    (out / "manifests" / "manifest.json").write_text(json.dumps([row]), encoding="utf-8")
    (out / "summary.json").write_text(
        json.dumps(
            {
                "pilot_id": "IMG-01E",
                "source_adapter": "insize_tosag",
                "status": "ok",
            }
        ),
        encoding="utf-8",
    )
    return row


# --- §1 region-isolated structured evidence ---


def test_related_meta_sku_does_not_confirm_sku() -> None:
    html = f"""<html><h1>INSIZE Main</h1>
      <div class="related"><meta property="product:retailer_item_id" content="{SKU}"></div>
    </html>"""
    ev = ADAPTER.validate_page(sku=SKU, page_html=html, detail_url="https://www.tosag.ch/x")
    assert ev.sku_confirmed is False


def test_related_meta_brand_and_sku_does_not_confirm_product() -> None:
    html = f"""<html><h1>Other title</h1>
      <section class="related">
        <meta property="product:brand" content="INSIZE">
        <meta property="product:retailer_item_id" content="{SKU}">
      </section></html>"""
    ev = ADAPTER.validate_page(sku=SKU, page_html=html, detail_url="https://www.tosag.ch/x")
    assert ev.manufacturer_confirmed is False or ev.sku_confirmed is False
    assert not (ev.manufacturer_confirmed and ev.sku_confirmed)


def test_related_product_json_ld_does_not_confirm() -> None:
    html = (
        "<html><h1>Other</h1>"
        + _json_ld([{"brand": {"@type": "Brand", "name": "INSIZE"}, "sku": SKU}], wrapper_attrs='class="related"')
        + "</html>"
    )
    ev = ADAPTER.validate_page(sku=SKU, page_html=html, detail_url="https://www.tosag.ch/x")
    assert not (ev.manufacturer_confirmed and ev.sku_confirmed)


def test_nested_cross_sell_json_ld_does_not_confirm() -> None:
    html = f"""<html><h1>Other</h1>
      <div class="cross-sell"><div>
        {_json_ld([{"brand": {"name": "INSIZE"}, "sku": SKU}])}
      </div></div></html>"""
    ev = ADAPTER.validate_page(sku=SKU, page_html=html, detail_url="https://www.tosag.ch/x")
    assert not (ev.manufacturer_confirmed and ev.sku_confirmed)


def test_subject_plus_related_product_uses_only_subject() -> None:
    html = f"""<html><h1>INSIZE {SKU}</h1><p>Art.Nr: {SKU}</p>
      {_json_ld([{"brand": {"name": "INSIZE"}, "sku": SKU}])}
      <section class="related">
        {_json_ld([{"brand": {"name": "INSIZE"}, "sku": "9999-001"}])}
      </section></html>"""
    ev = ADAPTER.validate_page(sku=SKU, page_html=html, detail_url="https://www.tosag.ch/x")
    assert ev.manufacturer_confirmed is True
    assert ev.sku_confirmed is True


# --- §2 atomic Product JSON-LD ---


def test_brand_only_plus_sku_only_json_ld_rejects() -> None:
    html = (
        "<html><h1>INSIZE catalog</h1>"
        + _json_ld([{"brand": {"name": "INSIZE"}}, {"sku": SKU}])
        + "</html>"
    )
    ev = ADAPTER.validate_page(sku=SKU, page_html=html, detail_url="https://www.tosag.ch/x")
    assert ev.sku_confirmed is False
    assert "cross_object" in (ev.sku_evidence or "") or ev.reason_code == "exact_sku_not_confirmed"


def test_other_main_plus_related_requested_json_ld_rejects() -> None:
    html = (
        "<html><h1>Main</h1>"
        + _json_ld([{"brand": {"name": "Mitutoyo"}, "sku": "OTHER-1"}])
        + _json_ld(
            [{"brand": {"name": "INSIZE"}, "sku": SKU}],
            wrapper_attrs='class="related"',
        )
        + "</html>"
    )
    ev = ADAPTER.validate_page(sku=SKU, page_html=html, detail_url="https://www.tosag.ch/x")
    assert not (ev.manufacturer_confirmed and ev.sku_confirmed)


def test_insize_other_sku_plus_requested_sku_json_ld_rejects() -> None:
    html = (
        "<html><h1>INSIZE</h1>"
        + _json_ld(
            [
                {"brand": {"name": "INSIZE"}, "sku": "1103-200"},
                {"brand": {"name": "INSIZE"}, "sku": SKU},
            ]
        )
        + "</html>"
    )
    ev = ADAPTER.validate_page(sku=SKU, page_html=html, detail_url="https://www.tosag.ch/x")
    assert ev.sku_confirmed is False


def test_one_consistent_insize_requested_sku_json_ld_accepts() -> None:
    html = (
        "<html><body>"
        + _json_ld([{"brand": {"name": "INSIZE"}, "sku": SKU, "name": "Caliper"}])
        + "</body></html>"
    )
    ev = ADAPTER.validate_page(sku=SKU, page_html=html, detail_url="https://www.tosag.ch/x")
    assert ev.manufacturer_confirmed is True
    assert ev.sku_confirmed is True


def test_identical_duplicate_consistent_json_ld_accepts() -> None:
    prod = {"brand": {"name": "INSIZE"}, "sku": SKU}
    html = "<html><body>" + _json_ld([prod, dict(prod)]) + "</body></html>"
    ev = ADAPTER.validate_page(sku=SKU, page_html=html, detail_url="https://www.tosag.ch/x")
    assert ev.manufacturer_confirmed is True
    assert ev.sku_confirmed is True


def test_ambiguous_multiple_product_nodes_reject() -> None:
    html = (
        "<html><h1>INSIZE</h1>"
        + _json_ld(
            [
                {"brand": {"name": "INSIZE"}, "sku": SKU, "mpn": "A"},
                {"brand": {"name": "INSIZE"}, "sku": SKU, "mpn": "B"},
            ]
        )
        + "</html>"
    )
    ev = ADAPTER.validate_page(sku=SKU, page_html=html, detail_url="https://www.tosag.ch/x")
    assert ev.sku_confirmed is False


# --- §3 symlink governed roots never opened/hashed ---


def test_symlinked_output_root_rejected(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link_out"
    link.symlink_to(real)
    with pytest.raises(C.DiscoveryError) as e:
        assert_run_output_roots_nofollow(link, require_existing_root=True)
    assert e.value.reason_code == "unexpected_governed_symlink"


def test_symlinked_assets_root_never_hashed(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    target = tmp_path / "ext_assets"
    target.mkdir()
    (target / "secret.bin").write_bytes(b"SECRET-EXTERNAL-TARGET")
    (out / "assets").symlink_to(target)
    hashed: list[Path] = []

    def guarded(path: Path) -> str:
        hashed.append(path)
        if "secret" in path.name:
            raise AssertionError(f"hashed external target: {path}")
        return file_sha256(path)

    with pytest.raises(C.DiscoveryError) as e:
        inventory_assets_by_sha(out / "assets", file_sha256=guarded, fail_closed=True)
    assert e.value.reason_code == "unexpected_governed_symlink"
    assert hashed == []


def test_symlinked_manifest_json_rejected(tmp_path: Path) -> None:
    out = tmp_path / "out"
    (out / "manifests").mkdir(parents=True)
    (out / "assets").mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("[]", encoding="utf-8")
    (out / "manifests" / "manifest.json").symlink_to(outside)
    (out / "summary.json").write_text(
        json.dumps({"pilot_id": "IMG-01E", "source_adapter": "insize_tosag"}), encoding="utf-8"
    )
    ok, reason, _ = recognize_prior_discovery_output(out)
    assert ok is False
    assert "symlink" in reason


def test_symlinked_batch_root_rejected_on_consolidate(tmp_path: Path) -> None:
    root = tmp_path / "batches"
    root.mkdir()
    real = tmp_path / "real_batch"
    (real / "manifests").mkdir(parents=True)
    (real / "assets").mkdir()
    (real / "manifests" / "manifest.json").write_text("[]", encoding="utf-8")
    link = root / "b1"
    link.symlink_to(real)
    out = tmp_path / "out"
    with pytest.raises(C.DiscoveryError) as e:
        consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)
    assert e.value.reason_code == "unexpected_governed_symlink"


def test_symlinked_batch_assets_never_read(tmp_path: Path) -> None:
    root = tmp_path / "batches"
    b = root / "b1"
    (b / "manifests").mkdir(parents=True)
    secret = tmp_path / "secret.jpg"
    secret.write_bytes(_jpeg())
    (b / "assets").symlink_to(secret.parent)
    jpeg = _jpeg(color=(9, 9, 9))
    sha = hashlib.sha256(jpeg).hexdigest()
    # Place file only under the symlink target
    (secret.parent / "x.jpg").write_bytes(jpeg)
    row = _row(sku="A-1", sha=sha, path="assets/x.jpg")
    (b / "manifests" / "manifest.json").write_text(json.dumps([row]), encoding="utf-8")
    out = tmp_path / "out"
    with pytest.raises(C.DiscoveryError) as e:
        assert_batch_roots_nofollow(b)
    assert e.value.reason_code == "unexpected_governed_symlink"
    with pytest.raises(C.DiscoveryError):
        consolidate_batches(input_dir=root, output_dir=out, repo_root=REPO_ROOT)


def test_compare_runs_rejects_symlinked_assets_dir(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    target = tmp_path / "t"
    target.mkdir()
    assets.symlink_to(target)
    with pytest.raises(C.DiscoveryError) as e:
        compare_runs(
            previous_state={},
            previous_manifest=[],
            current_manifest=[],
            current_semantic="0" * 64,
            asset_dir=assets,
        )
    assert e.value.reason_code == "unexpected_governed_symlink"


# --- §4 governed run output policy ---


def test_new_run_rejects_notes_txt(external_out: Path) -> None:
    (external_out / "notes.txt").write_text("hi", encoding="utf-8")
    with pytest.raises(SystemExit, match="non-empty"):
        enforce_run_output_policy(
            external_out, adapter_name="insize_tosag", resume=False, force_refetch=False
        )


def test_new_run_rejects_unrelated_summary(external_out: Path) -> None:
    (external_out / "summary.json").write_text('{"hello":1}', encoding="utf-8")
    with pytest.raises(SystemExit, match="non-empty"):
        enforce_run_output_policy(
            external_out, adapter_name="insize_tosag", resume=False, force_refetch=False
        )


def test_new_run_rejects_assets_only(external_out: Path) -> None:
    (external_out / "assets").mkdir()
    (external_out / "assets" / "x.bin").write_bytes(b"x")
    with pytest.raises(SystemExit, match="non-empty"):
        enforce_run_output_policy(
            external_out, adapter_name="insize_tosag", resume=False, force_refetch=False
        )


def test_new_run_rejects_partial_pipeline(external_out: Path) -> None:
    (external_out / "manifests").mkdir()
    (external_out / "manifests" / "manifest.json").write_text("[]", encoding="utf-8")
    with pytest.raises(SystemExit, match="non-empty"):
        enforce_run_output_policy(
            external_out, adapter_name="insize_tosag", resume=False, force_refetch=False
        )


def test_new_run_rejects_unknown_files_in_old_output(external_out: Path) -> None:
    _coherent_prior(external_out)
    (external_out / "stray.txt").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit, match="non-empty"):
        enforce_run_output_policy(
            external_out, adapter_name="insize_tosag", resume=False, force_refetch=False
        )


def test_resume_requires_coherent_prior(external_out: Path) -> None:
    (external_out / "notes.txt").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit, match="coherent|refused"):
        enforce_run_output_policy(
            external_out, adapter_name="insize_tosag", resume=True, force_refetch=False
        )


def test_resume_rejects_adapter_mismatch(external_out: Path) -> None:
    _coherent_prior(external_out)
    summary = json.loads((external_out / "summary.json").read_text(encoding="utf-8"))
    summary["source_adapter"] = "other_adapter"
    (external_out / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(SystemExit, match="adapter mismatch"):
        enforce_run_output_policy(
            external_out, adapter_name="insize_tosag", resume=True, force_refetch=False
        )


def test_resume_accepts_coherent_same_adapter(external_out: Path) -> None:
    _coherent_prior(external_out)
    enforce_run_output_policy(
        external_out, adapter_name="insize_tosag", resume=True, force_refetch=False
    )


def test_force_refetch_rejects_unrelated_shell(external_out: Path) -> None:
    (external_out / "notes.txt").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit, match="coherent|refused"):
        enforce_run_output_policy(
            external_out, adapter_name="insize_tosag", resume=False, force_refetch=True
        )


def test_force_refetch_accepts_coherent_prior(external_out: Path) -> None:
    _coherent_prior(external_out)
    enforce_run_output_policy(
        external_out, adapter_name="insize_tosag", resume=False, force_refetch=True
    )


def test_new_run_accepts_empty_dir(external_out: Path, tmp_path: Path) -> None:
    detail = "https://www.tosag.ch/s"
    image = "https://www.tosag.ch/s.jpg"
    cand = tmp_path / "c.csv"
    _write_candidates(
        cand,
        [{"sku": SKU, "product_name": "A", "image_url": image, "detail_url": detail, "confidence": "x"}],
    )
    page = f"<html><h1>INSIZE {SKU}</h1><p>Art.Nr: {SKU}</p></html>".encode()
    jpeg = _jpeg()
    opener = RecordingUrlOpen({detail: {"body": page}, image: {"body": jpeg, "ctype": "image/jpeg", "final": image}})
    summary = run_discovery(
        adapter=ADAPTER,
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
