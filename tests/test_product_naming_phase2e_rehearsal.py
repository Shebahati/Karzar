"""Phase 2E transactional rename rehearsal — gates and SQL safety (no live DB)."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

import pytest

from app.domain.product_naming_phase2e import (
    HOLD_CANARY_MANUFACTURER_CODE,
    PHASE2D_CANDIDATE_SHA256,
    PHASE2D_EXPECTED_READY_ROWS,
    REHEARSAL_REASON,
    build_expected_prestate_rows,
    build_rehearsal_sql,
    load_audit_ready_rows,
    load_freeze_manifest,
    parse_rehearsal_metrics,
    reconcile_live_row,
    rehearsal_logic_file_sha256,
    rehearsal_success_metrics,
    reject_real_apply_flags,
    validate_candidate_file,
    validate_phase2d_freeze_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "audit/product-naming-phase2d/PHASE2D_RENAME_CANDIDATES_PROPOSED.csv"
MANIFEST = ROOT / "audit/product-naming-phase2d/PHASE2D_CANDIDATE_FREEZE_MANIFEST.json"
AUDIT = ROOT / "audit/product-naming-phase2d/PHASE2D_CANONICAL_NAME_AUDIT.csv"


def _sample_prestate(**overrides: str) -> dict[str, str]:
    base = {
        "product_id": "1800",
        "sku": "1122-300",
        "manufacturer_code": "1122-300",
        "brand_id": "3",
        "brand_name": "INSIZE",
        "product_type_id": "12",
        "product_type_code": "HOOK_CALIPER",
        "expected_old_name": "old title",
        "proposed_name": "new title",
        "meta_title_present": "yes",
        "seo_title_impact": "no",
    }
    base.update(overrides)
    return base


def _live_from_prestate(row: dict[str, str]) -> dict[str, str]:
    return {
        "name": row["expected_old_name"],
        "sku": row["sku"],
        "manufacturer_code": row["manufacturer_code"],
        "brand_id": row["brand_id"],
        "product_type_id": row["product_type_id"],
        "deleted_at": "",
        "slug": "slug-1800",
    }


def test_real_apply_flags_rejected():
    with pytest.raises(SystemExit) as ei:
        reject_real_apply_flags(["--apply"])
    assert ei.value.code == 2
    with pytest.raises(SystemExit):
        reject_real_apply_flags(["--commit"])
    with pytest.raises(SystemExit):
        reject_real_apply_flags(["--force-commit"])


def test_phase2d_freeze_manifest_on_main():
    manifest = load_freeze_manifest(MANIFEST)
    validate_phase2d_freeze_manifest(manifest)


def test_candidate_file_freeze_on_main():
    rows, digest = validate_candidate_file(CANDIDATE)
    assert len(rows) == PHASE2D_EXPECTED_READY_ROWS
    assert digest == PHASE2D_CANDIDATE_SHA256


def test_hold_canary_not_in_candidate_cohort(tmp_path: Path):
    rows, _ = validate_candidate_file(CANDIDATE)
    codes = {(r.get("manufacturer_code") or "").strip() for r in rows}
    assert HOLD_CANARY_MANUFACTURER_CODE not in codes
    bad = dict(rows[0])
    bad["manufacturer_code"] = HOLD_CANARY_MANUFACTURER_CODE
    tmp = tmp_path / "bad.csv"
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r if r["product_id"] != bad["product_id"] else bad)
    digest = hashlib.sha256(tmp.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="2223-153"):
        validate_candidate_file(tmp, expected_sha256=digest)


def test_wrong_candidate_sha_blocks(tmp_path: Path):
    shutil_copy = tmp_path / "c.csv"
    shutil_copy.write_bytes(CANDIDATE.read_bytes())
    with pytest.raises(ValueError, match="SHA256"):
        validate_candidate_file(shutil_copy, expected_sha256="0" * 64)


def test_expected_prestate_from_frozen_audit():
    candidates, _ = validate_candidate_file(CANDIDATE)
    audit_ready = load_audit_ready_rows(AUDIT)
    prestate = build_expected_prestate_rows(candidates, audit_ready)
    assert len(prestate) == PHASE2D_EXPECTED_READY_ROWS
    for row in prestate:
        audit = audit_ready[int(row["product_id"])]
        assert row["expected_old_name"] == audit["current_name"].strip()
        assert row["proposed_name"] != row["expected_old_name"]


def test_reconcile_blocks_name_sku_mfg_product_type_drift():
    frozen = _sample_prestate()
    live = _live_from_prestate(frozen)
    assert reconcile_live_row(frozen, live) == []
    live["name"] = "drift"
    assert any("name drift" in e for e in reconcile_live_row(frozen, live))
    live = _live_from_prestate(frozen)
    live["sku"] = "x"
    assert any("sku drift" in e for e in reconcile_live_row(frozen, live))
    live = _live_from_prestate(frozen)
    live["manufacturer_code"] = "x"
    assert any("manufacturer_code drift" in e for e in reconcile_live_row(frozen, live))
    live = _live_from_prestate(frozen)
    live["product_type_id"] = "999"
    assert any("product_type_id drift" in e for e in reconcile_live_row(frozen, live))


def test_rehearsal_sql_serializable_advisory_lock_old_name_guard_rollback():
    sql = build_rehearsal_sql([_sample_prestate()])
    assert "BEGIN ISOLATION LEVEL SERIALIZABLE" in sql
    assert "pg_advisory_xact_lock" in sql
    assert "FOR UPDATE" in sql
    assert f"name = '{_sample_prestate()['expected_old_name']}'" in sql.replace("''", "'")
    assert "ROLLBACK;" in sql
    assert not re.search(r"(^|\n)\s*COMMIT\s*;", sql, re.I)
    assert REHEARSAL_REASON in sql
    assert "INSERT INTO product_change_logs" in sql
    assert "UPDATE products SET name" in sql
    assert "p2e_all_names" in sql


def test_rehearsal_script_source_has_no_commit_path():
    script = (ROOT / "scripts/ops/product_naming_phase2e_rehearsal.py").read_text(encoding="utf-8")
    assert "session.commit" not in script
    assert "connection.commit" not in script
    assert re.search(r'["\']COMMIT["\']', script) is None or "COMMIT forbidden" in script


def test_parse_rehearsal_metrics_and_success_gate():
    stdout = "\n".join(
        [
            "METRIC:drift_in_tx:0",
            "METRIC:updates_exact:47",
            "METRIC:old_names_remaining:0",
            "METRIC:protected_drift:0",
            "METRIC:rehearsal_logs:47",
            "METRIC:exact_name_collisions:0",
            "METRIC:non_target_name_changes:0",
        ]
    )
    m = parse_rehearsal_metrics(stdout)
    assert rehearsal_success_metrics(m, 47) == []


def test_partial_rowcount_fails_metrics():
    m = {
        "drift_in_tx": 0,
        "updates_exact": 46,
        "old_names_remaining": 1,
        "protected_drift": 0,
        "rehearsal_logs": 47,
        "exact_name_collisions": 0,
        "non_target_name_changes": 0,
    }
    errs = rehearsal_success_metrics(m, 47)
    assert "updates_exact" in errs
    assert "old_names_remaining" in errs


def test_rehearsal_logic_file_hashes():
    hashes = rehearsal_logic_file_sha256(ROOT)
    assert "app/domain/product_naming_phase2e.py" in hashes
    assert "scripts/ops/product_naming_phase2e_rehearsal.py" in hashes


def test_failure_injection_sql_fragments_still_rollback_only():
    """Simulated mid-cohort failure: truncated script must not include COMMIT."""
    full = build_rehearsal_sql([_sample_prestate(), _sample_prestate(product_id="1828", sku="1169-150")])
    cut = full.split("UPDATE products")[0] + "ROLLBACK;\n"
    assert "COMMIT" not in cut.upper().replace("ROLLBACK", "")
    assert "ROLLBACK" in cut
