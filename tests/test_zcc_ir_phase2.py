"""Fixture-based tests for READ-ONLY zcc.ir Phase 2 import planning."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = ROOT / "tests" / "fixtures" / "zcc_ir_phase2"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.snapshot import load_snapshot_csv  # noqa: E402
from zcc_ir_import_plan import FORBIDDEN  # noqa: E402
from zcc_ir_import_plan import main as cli_main  # noqa: E402
from zcc_ir_phase2.canonical_hash import (  # noqa: E402
    canonical_import_plan_sha256,
    sha256_file,
)
from zcc_ir_phase2.manifest import (  # noqa: E402
    ALLOWED_OPERATIONS,
    FORBIDDEN_OPERATIONS,
    write_import_manifest,
)
from zcc_ir_phase2.pipeline import run_phase2_plan  # noqa: E402
from zcc_ir_phase2.snapshot_stats import brand_catalog_stats  # noqa: E402
from zcc_ir_phase2.stc_hold import summarize_hold_brand_review  # noqa: E402
from zcc_ir_phase2.validate import validate_manifest, validate_manifest_layers  # noqa: E402

SNAPSHOT_SHA_FIXTURE = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def _manifest_body_with_entry(entry: dict) -> dict:
    return {
        "phase2_version": "test",
        "karzar_snapshot_sha256": SNAPSHOT_SHA_FIXTURE,
        "entries": [entry],
    }


def test_no_hardcoded_production_url_in_phase2_scripts() -> None:
    combined = ""
    for rel in ("zcc_ir_import_plan.py", "zcc_ir_phase2/pipeline.py", "zcc_ir_phase2/load.py"):
        combined += (SCRIPTS / rel).read_text(encoding="utf-8") + "\n"
    assert not re.search(
        r"""^\s*[A-Za-z_][A-Za-z0-9_]*\s*=\s*["']https?://[^"']*karzartools\.com""",
        combined,
        re.M,
    )


def test_apply_path_rejected() -> None:
    assert cli_main(["plan", "--apply"]) == 2
    for flag in FORBIDDEN:
        assert cli_main(["validate", "--manifest", str(FIXTURES / "x.json"), flag]) == 2


def test_inactive_san_ou_detected_in_full_snapshot() -> None:
    products, _kind = load_snapshot_csv(FIXTURES / "karzar_full_snapshot.csv")
    stats = brand_catalog_stats(products, {"SAN OU"})
    san = stats["SAN OU"]
    assert san["total"] == 3
    assert san["inactive"] >= 2
    assert san["storefront_visible_heuristic"] == 1


def test_phase2_plan_and_manifest_determinism(tmp_path: Path) -> None:
    out = tmp_path / "phase2"
    summary = run_phase2_plan(
        phase1_dir=FIXTURES / "phase1_mini",
        output_dir=out,
        karzar_snapshot=str(FIXTURES / "karzar_full_snapshot.csv"),
    )
    manifest_path = out / "import_manifest.json"
    assert manifest_path.is_file()
    sidecar = manifest_path.with_name(manifest_path.name + ".sha256")
    assert sidecar.is_file()
    assert sidecar.read_text(encoding="utf-8").strip() == sha256_file(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["CANONICAL_IMPORT_PLAN_SHA256"]
    assert manifest["IMPORT_MANIFEST_SHA256"]
    assert manifest["IMPORT_MANIFEST_SHA256"] != manifest["CANONICAL_IMPORT_PLAN_SHA256"]
    assert manifest["karzar_snapshot_sha256"] == sha256_file(FIXTURES / "karzar_full_snapshot.csv")
    assert validate_manifest(manifest_path) == []
    run_phase2_plan(
        phase1_dir=FIXTURES / "phase1_mini",
        output_dir=tmp_path / "phase2b",
        karzar_snapshot=str(FIXTURES / "karzar_full_snapshot.csv"),
    )
    manifest2 = json.loads((tmp_path / "phase2b" / "import_manifest.json").read_text(encoding="utf-8"))
    assert manifest["CANONICAL_IMPORT_PLAN_SHA256"] == manifest2["CANONICAL_IMPORT_PLAN_SHA256"]
    assert summary["current_snapshot"]["source_product_count"] == 3
    ops = set(manifest["operation_counts"])
    assert ops.issubset(ALLOWED_OPERATIONS)
    assert not ops.intersection(FORBIDDEN_OPERATIONS)


def test_validator_rejects_forbidden_operation(tmp_path: Path) -> None:
    bad = {
        "entries": [
            {
                "operation": "CREATE",
                "source_url": "https://zcc.ir/product/x/",
                "source_identity": {"brand": "ZCC.CT", "manufacturer_code": "X"},
                "planned_fields": {},
                "primary_state": "CREATE_CANDIDATE",
            }
        ],
        "IMPORT_MANIFEST_SHA256": "deadbeef",
        "karzar_snapshot_sha256": SNAPSHOT_SHA_FIXTURE,
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    errors = validate_manifest(path)
    assert any("forbidden operation" in e for e in errors)


def test_validator_rejects_zero_price_create(tmp_path: Path) -> None:
    entry = {
        "operation": "CREATE_PLAN",
        "source_url": "https://zcc.ir/product/x/",
        "source_identity": {"brand": "ZCC.CT", "manufacturer_code": "ONLYONE"},
        "category_id": "33",
        "planned_fields": {
            "identity": {"sku_proposal": "ZCC-ONLYONE"},
            "commerce_observations": {"observed_price": "0"},
            "images": {"main_image_source_url": "https://example/a.jpg"},
        },
        "primary_state": "CREATE_CANDIDATE",
    }
    body = {
        "entries": [entry],
        "phase2_version": "test",
        "karzar_snapshot_sha256": SNAPSHOT_SHA_FIXTURE,
    }
    body["CANONICAL_IMPORT_PLAN_SHA256"] = canonical_import_plan_sha256(body)
    path = tmp_path / "zero.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    layers = validate_manifest_layers(path)
    assert any("COMMERCE_INVALID" in e for e in layers.commerce_errors)
    assert layers.CONTENT_PLAN_VALID


def test_cli_validate_command(tmp_path: Path) -> None:
    run_phase2_plan(
        phase1_dir=FIXTURES / "phase1_mini",
        output_dir=tmp_path / "out",
        karzar_snapshot=str(FIXTURES / "karzar_full_snapshot.csv"),
    )
    manifest = tmp_path / "out" / "import_manifest.json"
    assert cli_main(["validate", "--manifest", str(manifest)]) == 0


def test_stc_brand_proposal_present(tmp_path: Path) -> None:
    out = tmp_path / "phase2"
    run_phase2_plan(
        phase1_dir=FIXTURES / "phase1_mini",
        output_dir=out,
        karzar_snapshot=str(FIXTURES / "karzar_full_snapshot.csv"),
    )
    stc = json.loads((out / "stc_brand_proposal.json").read_text(encoding="utf-8"))
    assert stc["canonical_name"] == "STC"
    assert stc["product_count"] >= 1
    assert stc["decision_status"] in {"READY_FOR_OWNER_APPROVAL", "REVIEW_REQUIRED"}


def test_validator_duplicate_pair_collision_affected_rows(tmp_path: Path) -> None:
    """Diagnostics attach to later occurrences; both rows count as collision-affected."""
    shared = {
        "operation": "CREATE_PLAN",
        "source_identity": {"brand": "ZCC.CT", "manufacturer_code": "DUP-1"},
        "category_id": "33",
        "planned_fields": {
            "identity": {"sku_proposal": "ZCC-DUP-1"},
            "commerce_observations": {"observed_price": "1000"},
            "images": {"main_image_source_url": "https://example/a.jpg"},
        },
        "primary_state": "CREATE_CANDIDATE",
    }
    first = {**shared, "source_url": "https://zcc.ir/product/first/"}
    second = {**shared, "source_url": "https://zcc.ir/product/second/"}
    body = {
        "entries": [first, second],
        "phase2_version": "test",
        "karzar_snapshot_sha256": SNAPSHOT_SHA_FIXTURE,
    }
    body["CANONICAL_IMPORT_PLAN_SHA256"] = canonical_import_plan_sha256(body)
    path = tmp_path / "dup.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    layers = validate_manifest_layers(path)
    assert layers.DUPLICATE_IDENTITY_DIAGNOSTICS == 1
    assert layers.DUPLICATE_SKU_DIAGNOSTICS == 1
    assert layers.CONTENT_BLOCKING_ERROR_COUNT == 2
    assert layers.CONTENT_DIAGNOSTIC_ROW_COUNT == 1
    assert layers.CONTENT_COLLISION_AFFECTED_ROW_COUNT == 2
    assert layers.LOGICAL_COLLISION_GROUP_COUNT == 1
    cluster = layers.logical_collision_clusters[0]
    assert "DUPLICATE_MANUFACTURER_IDENTITY" in cluster.reasons
    assert "DUPLICATE_TARGET_SKU" in cluster.reasons


def test_stc_hold_brand_review_invariant_from_classification() -> None:
    rows: list[dict] = []
    rows.extend(
        {"primary_state": "HOLD_BRAND_REVIEW", "brand_normalized": "STC"} for _ in range(53)
    )
    rows.extend(
        {"primary_state": "HOLD_BRAND_REVIEW", "brand_normalized": None} for _ in range(12)
    )
    rows.append({"primary_state": "CREATE_CANDIDATE", "brand_normalized": "ZCC.CT"})
    summary = summarize_hold_brand_review(rows)
    assert summary["TRUE_STC_ROWS"] == 53
    assert summary["NON_STC_BRAND_REVIEW_ROWS"] == 12
    assert summary["HOLD_BRAND_REVIEW_TOTAL"] == 65
    assert summary["COUNT_INVARIANT_VALID"] is True


def test_canonical_hash_ignores_volatile_metadata(tmp_path: Path) -> None:
    base_entry = {
        "operation": "NOOP",
        "source_url": "https://zcc.ir/product/a/",
        "source_identity": {"brand": "ZCC.CT", "manufacturer_code": "A1"},
        "target_identity": {"karzar_id": "1", "karzar_sku": "ZCC-A1"},
        "planned_fields": {},
        "primary_state": "NOOP_EXISTING_EXACT",
    }
    m1 = {
        "phase2_version": "zcc_ir_phase2/1.0.0",
        "git_sha": "aaa",
        "karzar_snapshot_timestamp": "t1",
        "karzar_snapshot_sha256": SNAPSHOT_SHA_FIXTURE,
        "entries": [base_entry],
        "operation_counts": {"NOOP": 1},
    }
    m2 = dict(m1)
    m2["git_sha"] = "bbb"
    m2["karzar_snapshot_timestamp"] = "t2"
    m2["generated_at"] = "2026-01-01T00:00:00Z"
    assert canonical_import_plan_sha256(m1) == canonical_import_plan_sha256(m2)

    m_snap = dict(m1)
    m_snap["karzar_snapshot_sha256"] = "b" * 64
    assert canonical_import_plan_sha256(m1) != canonical_import_plan_sha256(m_snap)

    m3 = dict(m1)
    m3["entries"] = [
        {
            **base_entry,
            "planned_fields": {"identity": {"sku_proposal": "ZCC-CHANGED"}},
        }
    ]
    assert canonical_import_plan_sha256(m1) != canonical_import_plan_sha256(m3)

    m4 = dict(m1)
    m4["entries"] = [{**base_entry, "operation": "HOLD", "primary_state": "HOLD_CATEGORY_REVIEW"}]
    assert canonical_import_plan_sha256(m1) != canonical_import_plan_sha256(m4)

    m5 = dict(m1)
    m5["entries"] = [
        {**base_entry, "target_identity": {"karzar_id": "99", "karzar_sku": "ZCC-OTHER"}}
    ]
    assert canonical_import_plan_sha256(m1) != canonical_import_plan_sha256(m5)

    m6 = dict(m1)
    m6["entries"] = [{**base_entry, "category_id": "99"}]
    assert canonical_import_plan_sha256(m1) != canonical_import_plan_sha256(m6)

    m7 = dict(m1)
    m7["entries"] = [
        {
            **base_entry,
            "source_identity": {"brand": "SAN OU", "manufacturer_code": "A1"},
        }
    ]
    assert canonical_import_plan_sha256(m1) != canonical_import_plan_sha256(m7)

    m8 = dict(m1)
    m8["entries"] = [
        {
            **base_entry,
            "planned_fields": {"description_class": "changed"},
        }
    ]
    assert canonical_import_plan_sha256(m1) != canonical_import_plan_sha256(m8)

    m9 = dict(m1)
    m9["entries"] = [{**base_entry, "blocking_flags": ["ambiguous_match"]}]
    assert canonical_import_plan_sha256(m1) != canonical_import_plan_sha256(m9)

    m_ts = dict(m1)
    m_ts["entries"] = [{**base_entry, "source_timestamp": "row-only-ts"}]
    assert canonical_import_plan_sha256(m1) == canonical_import_plan_sha256(m_ts)


def test_manifest_sidecar_matches_on_disk_bytes(tmp_path: Path) -> None:
    body = {
        "phase2_version": "test",
        "karzar_snapshot_sha256": SNAPSHOT_SHA_FIXTURE,
        "entries": [],
    }
    path = tmp_path / "import_manifest.json"
    write_import_manifest(path, body)
    sidecar = path.with_name(path.name + ".sha256")
    assert sidecar.read_text(encoding="utf-8").strip() == sha256_file(path)


def test_aods_ingestion_boundary_still_passes() -> None:
    result = subprocess.run(
        ["python3", "aods/tools/aods_validate.py", "--gate", "ingestion-boundary"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "ingestion-boundary" in result.stdout and "PASS" in result.stdout
