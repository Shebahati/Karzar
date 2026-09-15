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
from zcc_ir_import_plan import FORBIDDEN, main as cli_main  # noqa: E402
from zcc_ir_phase2.manifest import (  # noqa: E402
    ALLOWED_OPERATIONS,
    FORBIDDEN_OPERATIONS,
    manifest_sha256,
)
from zcc_ir_phase2.pipeline import run_phase2_plan  # noqa: E402
from zcc_ir_phase2.snapshot_stats import brand_catalog_stats  # noqa: E402
from zcc_ir_phase2.validate import validate_manifest  # noqa: E402


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
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["IMPORT_MANIFEST_SHA256"]
    assert validate_manifest(manifest_path) == []
    run_phase2_plan(
        phase1_dir=FIXTURES / "phase1_mini",
        output_dir=tmp_path / "phase2b",
        karzar_snapshot=str(FIXTURES / "karzar_full_snapshot.csv"),
    )
    manifest2 = json.loads((tmp_path / "phase2b" / "import_manifest.json").read_text(encoding="utf-8"))
    assert manifest["IMPORT_MANIFEST_SHA256"] == manifest2["IMPORT_MANIFEST_SHA256"]
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
    body = {"entries": [entry]}
    body["IMPORT_MANIFEST_SHA256"] = manifest_sha256(body)
    path = tmp_path / "zero.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    errors = validate_manifest(path)
    assert any("price=0" in e for e in errors)


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


def test_aods_ingestion_boundary_still_passes() -> None:
    result = subprocess.run(
        ["python3", "aods/tools/aods_validate.py", "--gate", "ingestion-boundary"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "ingestion-boundary" in result.stdout and "PASS" in result.stdout
