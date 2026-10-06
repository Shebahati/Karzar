"""Phase 2E transactional rename rehearsal — gates and SQL safety (no live DB)."""

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

import pytest
from app.domain.product_naming import normalize_persian_text
from app.domain.product_naming_phase2e import (
    HOLD_CANARY_MANUFACTURER_CODE,
    PHASE2D_CANDIDATE_SHA256,
    PHASE2D_EXPECTED_READY_ROWS,
    REHEARSAL_REASON,
    audit_rehearsal_logs,
    build_expected_prestate_rows,
    build_rehearsal_sql,
    collision_precheck_python,
    load_audit_ready_rows,
    load_freeze_manifest,
    normalize_name_for_collision,
    parse_rehearsal_stdout,
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
        "proposed_name_norm": "new title",
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


def test_phase2d_freeze_manifest_on_main():
    validate_phase2d_freeze_manifest(load_freeze_manifest(MANIFEST))


def test_candidate_file_freeze_on_main():
    rows, digest = validate_candidate_file(CANDIDATE)
    assert len(rows) == PHASE2D_EXPECTED_READY_ROWS
    assert digest == PHASE2D_CANDIDATE_SHA256


def test_hold_canary_not_in_candidate_cohort(tmp_path: Path):
    rows, _ = validate_candidate_file(CANDIDATE)
    assert HOLD_CANARY_MANUFACTURER_CODE not in {
        (r.get("manufacturer_code") or "").strip() for r in rows
    }
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


def test_normalized_collision_detects_arabic_ye_variant():
    a = "کولیس"
    b = a.replace("ی", "\u064a")
    assert a != b
    assert normalize_name_for_collision(a) == normalize_name_for_collision(b)
    prestate = [
        _sample_prestate(proposed_name=a, proposed_name_norm=normalize_name_for_collision(a)),
        _sample_prestate(
            product_id="1801",
            proposed_name=b,
            proposed_name_norm=normalize_name_for_collision(b),
        ),
    ]
    hits = collision_precheck_python(prestate, [])
    assert hits["cohort_normalized_dup"] == 1


def test_expected_prestate_from_frozen_audit():
    candidates, _ = validate_candidate_file(CANDIDATE)
    prestate = build_expected_prestate_rows(candidates, load_audit_ready_rows(AUDIT))
    assert len(prestate) == PHASE2D_EXPECTED_READY_ROWS
    for row in prestate:
        audit = load_audit_ready_rows(AUDIT)[int(row["product_id"])]
        assert row["expected_old_name"] == audit["current_name"].strip()
        assert row["proposed_name_norm"] == normalize_persian_text(row["proposed_name"])


def test_rehearsal_sql_identity_gate_coupled_update_rollback():
    sql = build_rehearsal_sql([_sample_prestate()], catalog_norm_rows=[(1, "x")])
    assert "p2e_frozen_identity" in sql
    assert "METRIC:in_tx_identity_drift:" in sql
    assert "RETURNING p.id" in sql
    assert "INSERT INTO product_change_logs" in sql
    assert "ROLLBACK;" in sql
    assert not re.search(r"(^|\n)\s*COMMIT\s*;", sql, re.I)


def test_parse_metrics_requires_full_contract():
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
            "rehearsal_logs_exact": 47,
            "exact_name_collisions": 0,
            "normalized_name_collisions": 0,
            "catalog_exact_collisions": 0,
            "catalog_normalized_collisions": 0,
            "non_target_name_changes": 0,
            "non_target_protected_changes": 0,
        }.items()
    )
    metrics, _ = parse_rehearsal_stdout(stdout)
    metrics["actual_log_row_mismatches"] = 0
    assert rehearsal_success_metrics(metrics, 47) == []


def test_audit_rehearsal_logs_detects_wrong_old_value():
    prestate = [_sample_prestate()]
    logs = [
        {
            "id": 1,
            "product_id": 1800,
            "field_name": "name",
            "old_value": "wrong",
            "new_value": "new title",
            "reason": REHEARSAL_REASON,
            "actor_user_id": None,
        }
    ]
    summary, _ = audit_rehearsal_logs(prestate, logs)
    assert summary["wrong_old_value"] == 1
    assert summary["actual_log_row_mismatches"] > 0


def test_rehearsal_logic_file_hashes():
    hashes = rehearsal_logic_file_sha256(ROOT)
    assert "app/domain/product_naming_phase2e.py" in hashes
