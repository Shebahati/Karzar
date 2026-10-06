"""Phase 2F real APPLY — safety gates (no live DB mutation)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.domain.product_naming_phase2e import (
    HOLD_CANARY_MANUFACTURER_CODE,
    PHASE2D_CANDIDATE_SHA256,
    PHASE2D_EXPECTED_READY_ROWS,
    reconcile_live_row,
    validate_candidate_file,
)
from app.domain.product_naming_phase2f import (
    FORBIDDEN_APPLY_FLAGS,
    PHASE2E_PRESTATE_SHA256,
    REAL_APPLY_EXPECTED_ROWS,
    apply_change_log_reason,
    apply_success_metrics,
    assert_confirmation_sha,
    audit_apply_logs,
    build_real_apply_sql,
    load_expected_prestate_csv,
    parse_apply_stdout,
    real_apply_logic_file_sha256,
    reject_forbidden_apply_flags,
    second_apply_blocked_reason,
    validate_phase2e_manifest,
)
from scripts.ops.product_naming_phase2f_apply_once import main as apply_main

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "audit/product-naming-phase2d/PHASE2D_RENAME_CANDIDATES_PROPOSED.csv"
PRESTATE = ROOT / "audit/product-naming-phase2e-rehearsal/PHASE2E_EXPECTED_PRESTATE.csv"
MANIFEST = ROOT / "audit/product-naming-phase2e-rehearsal/PHASE2E_REHEARSAL_MANIFEST.json"


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
        "proposed_name_norm": "new title",
        "meta_title_present": "yes",
        "seo_title_impact": "no",
    }
    base.update(overrides)
    return base


def test_forbidden_flags_rejected():
    for flag in FORBIDDEN_APPLY_FLAGS:
        with pytest.raises(SystemExit) as ei:
            reject_forbidden_apply_flags([flag])
        assert ei.value.code == 2


def test_plain_invocation_no_db():
    rc = apply_main([])
    assert rc == 2


def test_apply_without_confirmations_fails():
    rc = apply_main(["--apply"])
    assert rc == 2


def test_wrong_cohort_sha_fails():
    with pytest.raises(ValueError, match="confirm-cohort-sha mismatch"):
        assert_confirmation_sha("deadbeef", PHASE2D_CANDIDATE_SHA256, flag_name="confirm-cohort-sha")


def test_frozen_prestate_on_main():
    rows = load_expected_prestate_csv(PRESTATE)
    assert len(rows) == REAL_APPLY_EXPECTED_ROWS


def test_phase2e_manifest_ready():
    validate_phase2e_manifest(MANIFEST)


def test_hold_canary_not_in_cohort():
    rows, _ = validate_candidate_file(CANDIDATE, expected_sha256=PHASE2D_CANDIDATE_SHA256)
    assert HOLD_CANARY_MANUFACTURER_CODE not in {
        (r.get("manufacturer_code") or "").strip() for r in rows
    }


def test_apply_sql_commits_with_identity_gate():
    prestate = load_expected_prestate_csv(PRESTATE)
    sql = build_real_apply_sql(prestate, catalog_norm_rows=[(1, "x")])
    assert "p2f_frozen_identity" in sql
    assert "p2f_identity_gate" in sql
    assert "COMMIT;" in sql
    assert "ROLLBACK" not in sql.upper().split("COMMIT")[0]


def test_change_log_reason_includes_full_cohort_sha():
    reason = apply_change_log_reason(PHASE2D_CANDIDATE_SHA256)
    assert PHASE2D_CANDIDATE_SHA256 in reason
    assert len(reason) <= 255


def test_parse_apply_stdout_contract():
    stdout = "\n".join(
        f"METRIC:{k}:{v}"
        for k, v in {
            "in_tx_identity_drift": 0,
            "in_tx_name_drift": 0,
            "in_tx_sku_drift": 0,
            "in_tx_manufacturer_code_drift": 0,
            "in_tx_brand_drift": 0,
            "in_tx_product_type_drift": 0,
            "in_tx_deleted_drift": 0,
            "updates_exact": 47,
            "old_names_remaining": 0,
            "target_protected_drift": 0,
            "apply_logs_exact": 47,
            "exact_name_collisions": 0,
            "normalized_name_collisions": 0,
            "catalog_exact_collisions": 0,
            "catalog_normalized_collisions": 0,
            "non_target_name_changes": 0,
            "non_target_protected_changes": 0,
            "txid": 99,
        }.items()
    )
    metrics, _ = parse_apply_stdout(stdout)
    assert apply_success_metrics(metrics, PHASE2D_EXPECTED_READY_ROWS) == []


def test_audit_apply_logs_wrong_reason():
    prestate = [_sample_prestate()]
    reason = apply_change_log_reason()
    logs = [
        {
            "id": 1,
            "product_id": 1800,
            "field_name": "name",
            "old_value": "old title",
            "new_value": "new title",
            "reason": "wrong",
            "actor_user_id": None,
        }
    ]
    summary, _ = audit_apply_logs(prestate, logs)
    assert summary["wrong_reason"] == 1
    assert summary["actual_log_row_mismatches"] > 0


def test_second_apply_blocked_when_all_proposed():
    prestate = [_sample_prestate(), _sample_prestate(product_id="1801")]
    live = {
        "1800": {"name": "new title"},
        "1801": {"name": "new title"},
    }
    assert second_apply_blocked_reason(prestate, live) == "ALREADY_APPLIED_BLOCKED"


def test_reconcile_blocks_name_drift():
    row = _sample_prestate()
    live = {
        "name": "different",
        "sku": row["sku"],
        "manufacturer_code": row["manufacturer_code"],
        "brand_id": row["brand_id"],
        "product_type_id": row["product_type_id"],
        "deleted_at": "",
        "slug": "s",
    }
    assert any("name" in e for e in reconcile_live_row(row, live))


def test_real_apply_logic_files_exist():
    hashes = real_apply_logic_file_sha256(ROOT)
    assert "app/domain/product_naming_phase2f.py" in hashes
    assert "scripts/ops/product_naming_phase2f_apply_once.py" in hashes


def test_wrong_prestate_sha(tmp_path: Path):
    bad = tmp_path / "bad.csv"
    bad.write_text("product_id\n1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="prestate SHA256 mismatch"):
        load_expected_prestate_csv(bad)
