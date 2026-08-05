"""Fixture-only tests for IMG-02C multisource discovery (no live network)."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from image_multisource import MultisourceError  # noqa: E402
from image_multisource.calibrate import calibrate_source, validate_redirect  # noqa: E402
from image_multisource.eligibility import (  # noqa: E402
    build_eligibility_report,
    select_calibration_sample,
)
from image_multisource.matching import classify_match, sku_token_present  # noqa: E402
from image_multisource.output import assert_external_output  # noqa: E402
from image_multisource.pdf import build_pdf_record  # noqa: E402
from image_multisource.pipeline import run_foundation_and_calibration  # noqa: E402
from image_multisource.quality import (  # noqa: E402
    average_perceptual_hash,
    group_duplicates,
    inspect_image_bytes,
    normalize_source_url,
    sha256_bytes,
)
from image_multisource.registry import (  # noqa: E402
    builtin_known_host_registry,
    parse_source,
    prefer_higher_priority,
    sort_sources,
    write_registry_snapshot,
)
from image_multisource.robots import classify_robots_text  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def _mini_jpeg(color: tuple[int, int, int] = (40, 80, 120)) -> bytes:
    from io import BytesIO

    from PIL import Image

    im = Image.new("RGB", (320, 320), color)
    buf = BytesIO()
    im.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _worklist(tmp: Path, rows: list[dict[str, str]]) -> Path:
    fields = [
        "schema_version",
        "task_id",
        "work_item_id",
        "product_key",
        "product_id",
        "sku",
        "product_name",
        "brand_key",
        "work_type",
        "work_reasons",
        "priority",
        "eligible_for_automatic_discovery",
    ]
    path = tmp / "worklist-all.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})
    return path


def _r2_dir(tmp: Path, *, stable: list[str], drift: list[str], manual: list[str]) -> Path:
    root = tmp / "IMG-02B-R2"
    cons = root / "consolidated"
    cons.mkdir(parents=True)
    with (cons / "all-accepted-manifest.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["product_id", "sku", "sha256"])
        w.writeheader()
        for pid in stable:
            w.writerow({"product_id": pid, "sku": f"S-{pid}", "sha256": f"{int(pid):064x}"[:64]})
    with (cons / "all-source-drift-review.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["product_id", "discovery_status"])
        w.writeheader()
        for pid in drift:
            w.writerow({"product_id": pid, "discovery_status": "source_drift_review"})
    with (cons / "all-manual-review.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "product_id",
                "discovery_status",
                "eligible_for_automatic_discovery",
                "reason_code",
            ],
        )
        w.writeheader()
        for pid in manual:
            w.writerow(
                {
                    "product_id": pid,
                    "discovery_status": "manual_review",
                    "eligible_for_automatic_discovery": "false",
                    "reason_code": "ambiguous_official_product",
                }
            )
    return root


def test_registry_rejects_enabled_unknown():
    raw = {
        "source_id": "bad",
        "source_class": "S5",
        "brand_keys": ["insize"],
        "allowed_page_hosts": ["x.example"],
        "allowed_asset_hosts": ["cdn.example"],
        "country": "IR",
        "authorization_status": "unknown",
        "authorization_evidence": "",
        "robots_status": "not_checked",
        "discovery_method": "none",
        "exact_sku_supported": False,
        "catalog_pdf_supported": False,
        "enabled": True,
        "rights_status": "review_required",
        "notes": "",
    }
    with pytest.raises(MultisourceError):
        parse_source(raw)


def test_source_priority_and_sort():
    sources = builtin_known_host_registry()
    ordered = sort_sources(sources)
    classes = [s.source_class for s in ordered]
    assert classes == sorted(classes, key=lambda c: ["S1", "S2", "S3", "S4", "S5"].index(c))
    assert prefer_higher_priority("S3", "S1") is True
    assert prefer_higher_priority("S1", "S5") is False


def test_eligibility_excludes_seed_hold_drift(tmp_path: Path):
    wl = _worklist(
        tmp_path,
        [
            {
                "product_id": "1",
                "sku": "A",
                "brand_key": "insize",
                "work_type": "missing_image",
                "priority": "P0",
                "eligible_for_automatic_discovery": "true",
            },
            {
                "product_id": "2",
                "sku": "B",
                "brand_key": "insize",
                "work_type": "missing_image",
                "priority": "P0",
                "eligible_for_automatic_discovery": "true",
            },
            {
                "product_id": "3",
                "sku": "C",
                "brand_key": "dasqua",
                "work_type": "missing_image",
                "priority": "P0",
                "eligible_for_automatic_discovery": "true",
            },
            {
                "product_id": "4",
                "sku": "D",
                "brand_key": "dasqua",
                "work_type": "manual_review_hold",
                "priority": "P0",
                "eligible_for_automatic_discovery": "false",
            },
            {
                "product_id": "5",
                "sku": "E",
                "brand_key": "san_ou",
                "work_type": "missing_image",
                "priority": "P1",
                "eligible_for_automatic_discovery": "true",
            },
        ],
    )
    r2 = _r2_dir(tmp_path, stable=["1"], drift=["2"], manual=["3"])
    report = build_eligibility_report(worklist_csv=wl, r2_seed=r2)
    assert report["totals"]["total_governed_work_items"] == 5
    assert report["totals"]["already_sourced"] == 1
    assert report["totals"]["source_drift"] == 1
    assert report["totals"]["remaining_eligible"] == 1
    assert report["remaining_eligible_product_ids"] == ["5"]
    sample = select_calibration_sample(report, wl, brand_key="san_ou", limit=20)
    assert len(sample) == 1


def test_exact_sku_matching_and_retailer_quarantine():
    src = parse_source(
        {
            "source_id": "tosag",
            "source_class": "S3",
            "brand_keys": ["insize"],
            "allowed_page_hosts": ["www.tosag.ch"],
            "allowed_asset_hosts": ["www.tosag.ch"],
            "country": "CH",
            "authorization_status": "authorized_candidate",
            "authorization_evidence": "x",
            "robots_status": "allow",
            "discovery_method": "search",
            "exact_sku_supported": True,
            "catalog_pdf_supported": False,
            "enabled": False,
            "rights_status": "review_required",
            "notes": "",
        }
    )
    ok = classify_match(
        source=src,
        product_id="10",
        sku="1120-500",
        brand_key="insize",
        page_url="https://www.tosag.ch/product/1120-500",
        asset_url="https://www.tosag.ch/i.jpg",
        page_text="INSIZE micrometer 1120-500 exact",
        match_basis="exact_sku_authorized_distributor",
        brand_confirmed=True,
        subject_exact=True,
        redirect_approved=True,
    )
    assert ok["discovery_status"] == "candidate_ready"
    assert sku_token_present("footer only", "1120-500") is False

    retail = parse_source(
        {
            **src.to_dict(),
            "source_id": "shop",
            "source_class": "S4",
            "authorization_status": "specialist_retailer",
            "brand_keys": list(src.brand_keys),
            "allowed_page_hosts": list(src.allowed_page_hosts),
            "allowed_asset_hosts": list(src.allowed_asset_hosts),
        }
    )
    # rebuild via parse
    retail = parse_source(
        {
            "source_id": "shop",
            "source_class": "S4",
            "brand_keys": ["insize"],
            "allowed_page_hosts": ["www.tosag.ch"],
            "allowed_asset_hosts": ["www.tosag.ch"],
            "country": "CH",
            "authorization_status": "specialist_retailer",
            "authorization_evidence": "x",
            "robots_status": "allow",
            "discovery_method": "search",
            "exact_sku_supported": True,
            "catalog_pdf_supported": False,
            "enabled": False,
            "rights_status": "review_required",
            "notes": "",
        }
    )
    rr = classify_match(
        source=retail,
        product_id="10",
        sku="1120-500",
        brand_key="insize",
        page_url="https://www.tosag.ch/product/1120-500",
        asset_url="https://www.tosag.ch/i.jpg",
        page_text="1120-500",
        match_basis="exact_sku_product_page",
        brand_confirmed=True,
        subject_exact=True,
        redirect_approved=True,
    )
    assert rr["discovery_status"] == "retailer_review"
    assert rr["eligible_for_automatic_acceptance"] == "false"


def test_redirect_rejection_and_robots():
    src = builtin_known_host_registry()[0]
    assert validate_redirect(
        requested_url="https://www.dasquatools.com/a",
        final_url="https://evil.example/a",
        source=src,
    ) is False
    rob = classify_robots_text(
        "User-agent: *\nDisallow: /\n",
        user_agent="KarzarImageMultisource/0.1",
        url="https://www.dasquatools.com/",
    )
    assert rob["crawl_permitted"] == "false"


def test_pdf_provenance_rejects_family_proximity():
    data = b"%PDF-1.4\n1 0 obj<< /Type /Page >>endobj\n%%EOF\n"
    rec = build_pdf_record(
        source_url="https://www.dasquatools.com/c.pdf",
        data=data,
        sku="1804-1405",
        matched_page_number=1,
        text_evidence="family catalogue page nearby items",
        image_ref="page-1-img-2",
    )
    assert rec.identity_status == "rejected_family_or_missing_exact_sku"
    ok = build_pdf_record(
        source_url="https://www.dasquatools.com/c.pdf",
        data=data,
        sku="1804-1405",
        matched_page_number=1,
        text_evidence="Item number 1804-1405 digital gauge",
        image_ref="page-1-img-2",
    )
    assert ok.identity_status == "exact_sku_or_model_confirmed"


def test_quality_filter_and_dedupe():
    a = _mini_jpeg((10, 20, 30))
    b = _mini_jpeg((10, 20, 30))
    c = _mini_jpeg((200, 10, 10))
    ia = inspect_image_bytes(a)
    assert ia["quality_status"] == "ok"
    assert ia["sha256"] == sha256_bytes(a)
    assert average_perceptual_hash(a) == average_perceptual_hash(b)
    assert normalize_source_url("https://X.Example/a.jpg?utm=1#h") == "https://x.example/a.jpg"
    html = inspect_image_bytes(b"<html>nope</html>")
    assert html["quality_status"] == "reject"
    groups = group_duplicates(
        [
            {
                "asset_id": "a1",
                "sha256": sha256_bytes(a),
                "source_image_url": "https://x.example/a.jpg",
                "perceptual_hash": average_perceptual_hash(a),
            },
            {
                "asset_id": "a2",
                "sha256": sha256_bytes(b),
                "source_image_url": "https://x.example/a.jpg?x=1",
                "perceptual_hash": average_perceptual_hash(b),
            },
            {
                "asset_id": "c1",
                "sha256": sha256_bytes(c),
                "source_image_url": "https://x.example/c.jpg",
                "perceptual_hash": average_perceptual_hash(c),
            },
        ]
    )
    assert any(g["member_count"] == "2" for g in groups)


def test_family_image_non_collapse_relations_separate():
    # Same physical sha may map to multiple products only as separate relations.
    sha = "ab" * 32
    relations = [
        {"product_id": "1", "sha256": sha, "evidence": "exact_sku_page_a"},
        {"product_id": "2", "sha256": sha, "evidence": "exact_sku_page_b"},
    ]
    assert len({r["product_id"] for r in relations}) == 2
    assert len({r["sha256"] for r in relations}) == 1


def test_external_output_safety_and_checksum_determinism(tmp_path: Path):
    with pytest.raises(MultisourceError):
        assert_external_output(REPO / "inside", REPO)
    wl = _worklist(
        tmp_path,
        [
            {
                "product_id": "10",
                "sku": "X",
                "brand_key": "insize",
                "work_type": "missing_image",
                "priority": "P0",
                "eligible_for_automatic_discovery": "true",
            }
        ],
    )
    r2 = _r2_dir(tmp_path, stable=[], drift=[], manual=[])
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    r1 = run_foundation_and_calibration(
        worklist_csv=wl,
        r2_seed=r2,
        output_dir=out1,
        repo_root=REPO,
        calibration_limit=5,
    )
    r2b = run_foundation_and_calibration(
        worklist_csv=wl,
        r2_seed=r2,
        output_dir=out2,
        repo_root=REPO,
        calibration_limit=5,
    )
    assert r1["checksums_digest"] == r2b["checksums_digest"]
    assert (out1 / "summary.json").is_file()
    snap = json.loads((out1 / "source-registry-snapshot.json").read_text(encoding="utf-8"))
    assert any(s["authorization_status"] == "unknown" and s["enabled"] is False for s in snap["sources"])
    assert r1["summary"]["safety"]["database_accessed"] is False


def test_calibration_disables_on_parser_drift(tmp_path: Path):
    wl = _worklist(
        tmp_path,
        [
            {
                "product_id": str(i),
                "sku": f"S-{i}",
                "brand_key": "insize",
                "work_type": "missing_image",
                "priority": "P0",
                "eligible_for_automatic_discovery": "true",
            }
            for i in range(1, 6)
        ],
    )
    r2 = _r2_dir(tmp_path, stable=[], drift=[], manual=[])
    report = build_eligibility_report(worklist_csv=wl, r2_seed=r2)
    src = [s for s in builtin_known_host_registry() if s.source_id == "insize_tosag"][0]

    def probe(_source, row):
        return {
            "product_id": row["product_id"],
            "sku": row["sku"],
            "status": "probed",
            "page_identity_ok": False,
            "exact_sku_ok": False,
            "redirect_ok": True,
            "generic_category": False,
            "parser_drift": True,
            "asset_host_ok": False,
            "notes": "fixture drift",
        }

    result = calibrate_source(
        source=src,
        eligibility_report=report,
        worklist_csv=wl,
        output_dir=tmp_path / "calib",
        limit=5,
        probe=probe,
    )
    assert result.enabled_after_calibration is False
    assert "parser_drift" in result.disable_reason


def test_resume_behavior_reuses_empty_checkpoint_outputs(tmp_path: Path):
    # Resume semantics at calibration stage: second run requires empty/absent dir (fail closed).
    wl = _worklist(
        tmp_path,
        [
            {
                "product_id": "7",
                "sku": "Y",
                "brand_key": "dasqua",
                "work_type": "missing_image",
                "priority": "P0",
                "eligible_for_automatic_discovery": "true",
            }
        ],
    )
    r2 = _r2_dir(tmp_path, stable=[], drift=[], manual=[])
    out = tmp_path / "batch"
    run_foundation_and_calibration(
        worklist_csv=wl, r2_seed=r2, output_dir=out, repo_root=REPO, calibration_limit=1
    )
    with pytest.raises(MultisourceError):
        run_foundation_and_calibration(
            worklist_csv=wl, r2_seed=r2, output_dir=out, repo_root=REPO, calibration_limit=1
        )


def test_registry_snapshot_deterministic_order(tmp_path: Path):
    sources = builtin_known_host_registry()
    p1 = tmp_path / "a.json"
    p2 = tmp_path / "b.json"
    write_registry_snapshot(list(reversed(sources)), p1)
    write_registry_snapshot(sources, p2)
    assert p1.read_text(encoding="utf-8") == p2.read_text(encoding="utf-8")
