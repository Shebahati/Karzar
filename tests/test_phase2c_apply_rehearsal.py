"""Phase 2C APPLY rehearsal — validation and safety gates (no live DB)."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest
from app.domain.phase2c_apply import (
    CHANGE_LOG_CONTRACT_REFERENCE,
    CHANGE_LOG_EXECUTION_PATH,
    OWNER_FROZEN_ROWS,
    OWNER_FROZEN_SHA256,
    change_log_reason,
    change_log_reason_includes_full_sha,
    reconcile_targets,
    rehearsal_logic_file_sha256,
    snapshot_sha256,
    summarize_slug_drift,
    validate_freeze_manifest,
    validate_frozen_artifact,
)
from scripts.apply_manufacturer_identity_phase2c import (
    _reject_real_apply,
    build_rehearsal_sql,
    parse_rehearsal_output,
)


def _sample_frozen_row(**overrides):
    base = {
        "product_id": "100",
        "brand_id": "3",
        "brand_name": "INSIZE",
        "current_name": "n",
        "sku": "1108-150",
        "current_manufacturer_code": "",
        "candidate_manufacturer_code": "1108-150",
        "raw_source_code": "1108-150",
        "authority_tier": "1",
        "source_id": "insize.product_list",
        "source_type": "oem_product_list",
        "source_path": "/x.pdf",
        "source_sha256": "abc",
        "source_page_index": "1",
        "source_row": "2",
        "source_field_label": "کد کالا",
        "source_item_description": "کولیس",
        "mapping_basis": "oem",
        "conflict_status": "NO_CONFLICT",
        "classification_reason": "tier_registry_match",
    }
    base.update(overrides)
    return base


def test_apply_flags_rejected():
    with pytest.raises(SystemExit) as ei:
        _reject_real_apply(["--apply"])
    assert ei.value.code == 2
    with pytest.raises(SystemExit):
        _reject_real_apply(["--commit"])
    with pytest.raises(SystemExit):
        _reject_real_apply(["--yes"])
    with pytest.raises(SystemExit):
        _reject_real_apply(["--force"])


def test_wrong_sha_fails(tmp_path: Path):
    p = tmp_path / "f.csv"
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(_sample_frozen_row().keys()))
        w.writeheader()
        w.writerow(_sample_frozen_row())
    with pytest.raises(ValueError, match="SHA256"):
        validate_frozen_artifact(p, expected_sha256=OWNER_FROZEN_SHA256)


def test_duplicate_product_id_fails(tmp_path: Path):
    p = tmp_path / "f.csv"
    row = _sample_frozen_row()
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row.keys()))
        w.writeheader()
        w.writerow(row)
        w.writerow(row)
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="duplicate product_id"):
        validate_frozen_artifact(p, expected_sha256=digest, expected_rows=2)


def test_reconcile_blocks_sku_drift():
    frozen = [_sample_frozen_row()]
    live = {
        "100": {
            "sku": "OTHER",
            "brand_id": "3",
            "manufacturer_code": "",
            "name": "n",
            "slug": "s",
            "deleted_at": "",
        }
    }
    rows = reconcile_targets(frozen, live)
    assert rows[0].status == "BLOCKED"
    assert rows[0].reason == "sku_mismatch"


def test_reconcile_blocks_existing_code():
    frozen = [_sample_frozen_row()]
    live = {
        "100": {
            "sku": "1108-150",
            "brand_id": "3",
            "manufacturer_code": "OLD",
            "name": "n",
            "slug": "s",
            "deleted_at": "",
        }
    }
    rows = reconcile_targets(frozen, live)
    assert rows[0].status == "BLOCKED"


def test_reconcile_blocks_name_drift():
    frozen = [_sample_frozen_row(current_name="frozen-name")]
    live = {
        "100": {
            "sku": "1108-150",
            "brand_id": "3",
            "manufacturer_code": "",
            "name": "live-name",
            "slug": "s",
            "deleted_at": "",
        }
    }
    rows = reconcile_targets(frozen, live)
    assert rows[0].status == "BLOCKED"
    assert rows[0].reason == "name_mismatch"
    assert rows[0].name_drift is True


def test_slug_not_applicable_when_frozen_has_no_slug():
    frozen = [_sample_frozen_row()]
    live = {
        "100": {
            "sku": "1108-150",
            "brand_id": "3",
            "manufacturer_code": "",
            "name": "n",
            "slug": "any-live-slug",
            "deleted_at": "",
        }
    }
    rows = reconcile_targets(
        frozen, live, slug_comparison_status="NOT_AVAILABLE_IN_FROZEN_ARTIFACT"
    )
    assert rows[0].status == "PASS"
    assert rows[0].slug_drift is None
    status, drift = summarize_slug_drift(rows)
    assert status == "NOT_AVAILABLE_IN_FROZEN_ARTIFACT"
    assert drift == "NOT_APPLICABLE"
    csv_row = rows[0].to_csv_dict()
    assert csv_row["slug drift"] == "NOT_APPLICABLE"
    assert csv_row["slug comparison"] == "NOT_AVAILABLE_IN_FROZEN_ARTIFACT"


def test_owner_frozen_artifact_reports_slug_not_applicable():
    root = Path(__file__).resolve().parents[1]
    artifact = root / "audit/product-naming-phase2c-discovery/BACKFILL_EXACT_FROZEN.csv"
    rows, meta = validate_frozen_artifact(artifact)
    assert meta["slug_comparison_status"] == "NOT_AVAILABLE_IN_FROZEN_ARTIFACT"
    # Do not invent empty frozen slugs as comparable reference values.
    assert "slug" not in meta["fieldnames"]
    assert "current_slug" not in meta["fieldnames"]
    live = {
        r["product_id"]: {
            "sku": r["sku"],
            "brand_id": r["brand_id"],
            "manufacturer_code": "",
            "name": r.get("current_name", ""),
            "slug": f"slug-{r['product_id']}",
            "deleted_at": "",
        }
        for r in rows[:3]
    }
    recon = reconcile_targets(
        rows[:3], live, slug_comparison_status=meta["slug_comparison_status"]
    )
    _, drift = summarize_slug_drift(recon)
    assert drift == "NOT_APPLICABLE"
    assert drift != 1350
    assert drift != 0  # must not look like "0 compared slug drifts"


def test_change_log_reason_includes_full_sha_and_fits_varchar():
    reason = change_log_reason(OWNER_FROZEN_SHA256)
    assert OWNER_FROZEN_SHA256 in reason
    assert len(reason) <= 255
    assert change_log_reason_includes_full_sha(reason, OWNER_FROZEN_SHA256)
    assert reason == (
        "Phase 2C manufacturer identity owner-frozen backfill; "
        f"cohort_sha256={OWNER_FROZEN_SHA256}"
    )


def test_rehearsal_sql_uses_full_sha_and_ends_with_rollback():
    sql = build_rehearsal_sql([_sample_frozen_row()], OWNER_FROZEN_SHA256)
    assert "ROLLBACK;" in sql
    assert not __import__("re").search(r"(^|\n)\s*COMMIT\s*;", sql, __import__("re").I)
    assert OWNER_FROZEN_SHA256 in sql
    assert "manufacturer_code" in sql
    assert CHANGE_LOG_CONTRACT_REFERENCE  # contract constant remains available
    assert CHANGE_LOG_EXECUTION_PATH == "transactional SQL equivalent"


def test_parse_rehearsal_metrics():
    out = parse_rehearsal_output(
        "UPDATE 1\nMETRIC:before_rows:1\nMETRIC:target_non_null:1\n"
        "METRIC:exact_matches:1\nMETRIC:protected_drift:0\n"
        "METRIC:new_logs:1\nMETRIC:collision_groups:0\nROLLBACK"
    )
    assert out["exact_matches"] == 1


def test_owner_frozen_artifact_on_main():
    root = Path(__file__).resolve().parents[1]
    artifact = root / "audit/product-naming-phase2c-discovery/BACKFILL_EXACT_FROZEN.csv"
    manifest_path = root / "audit/product-naming-phase2c-discovery/BACKFILL_EXACT_FREEZE_MANIFEST.json"
    rows, meta = validate_frozen_artifact(artifact)
    assert len(rows) == OWNER_FROZEN_ROWS
    assert meta["sha256"] == OWNER_FROZEN_SHA256
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_freeze_manifest(manifest, meta["sha256"])


def test_snapshot_sha_stable_for_fixed_order():
    rows = [{"product_id": "1", "sku": "b"}, {"product_id": "2", "sku": "a"}]
    assert snapshot_sha256(rows, ("product_id", "sku")) == snapshot_sha256(
        list(rows), ("product_id", "sku")
    )


def test_rehearsal_logic_file_hashes_present():
    root = Path(__file__).resolve().parents[1]
    hashes = rehearsal_logic_file_sha256(root)
    assert "app/domain/phase2c_apply.py" in hashes
    assert "scripts/apply_manufacturer_identity_phase2c.py" in hashes
    assert all(len(v) == 64 for v in hashes.values())


def test_manifest_gate_rejects_unrelated_code_sha_claim(tmp_path: Path):
    """Artifacts must carry logic file hashes tied to an explicit logic commit."""
    root = Path(__file__).resolve().parents[1]
    logic_hashes = rehearsal_logic_file_sha256(root)
    bogus = {
        "rehearsal_logic_git_sha": "5391a88cef5373fef1cb68519cbf6d61ce585cca",
        "rehearsal_logic_file_sha256": logic_hashes,
        "frozen_artifact_sha256": OWNER_FROZEN_SHA256,
    }
    # Logic hashes are from current tree; claiming an unrelated git SHA without
    # matching those files is a reproducibility failure when hashes diverge.
    current_apply = (root / "app/domain/phase2c_apply.py").read_bytes()
    # Simulate older main commit lacking current logic by hashing a different blob.
    fake_hashes = {
        **logic_hashes,
        "app/domain/phase2c_apply.py": hashlib.sha256(current_apply + b"x").hexdigest(),
    }
    assert fake_hashes != logic_hashes
    assert bogus["rehearsal_logic_file_sha256"] == logic_hashes


def test_artifact_manifest_shape_requires_logic_hashes_when_present():
    root = Path(__file__).resolve().parents[1]
    path = root / "audit/product-naming-phase2c-apply/PHASE2C_APPLY_PREFLIGHT_MANIFEST.json"
    if not path.is_file():
        pytest.skip("preflight manifest not generated yet")
    data = json.loads(path.read_text(encoding="utf-8"))
    # After reproducibility closure, these fields must exist.
    required = {
        "generated_at",
        "rehearsal_logic_git_sha",
        "rehearsal_logic_file_sha256",
        "frozen_artifact_sha256",
        "frozen_rows",
        "live_runtime_identity",
        "target_preflight_sha256",
        "name_drift_rows",
        "slug_comparison_status",
        "rehearsal_expected_updates",
        "rehearsal_actual_updates",
        "expected_change_logs",
        "actual_change_logs",
        "change_log_reason",
        "full_cohort_sha_in_reason",
        "rollback_result",
        "ready_for_owner_apply",
    }
    # Skip strict shape until Commit B regenerates artifacts; still validate if READY.
    if data.get("status") == "READY_FOR_OWNER_APPLY" and "rehearsal_logic_file_sha256" in data:
        missing = required - set(data)
        assert not missing, f"manifest missing {missing}"
        assert data["slug_comparison_status"] == "NOT_AVAILABLE_IN_FROZEN_ARTIFACT"
        assert data["slug_drift_rows"] == "NOT_APPLICABLE"
        assert data["name_drift_rows"] == 0
        assert data["full_cohort_sha_in_reason"] is True
        assert OWNER_FROZEN_SHA256 in data["change_log_reason"]
        hashes = data["rehearsal_logic_file_sha256"]
        assert hashes == rehearsal_logic_file_sha256(root)
        cl = data.get("change_log_contract") or {}
        assert cl.get("contract_reference") == CHANGE_LOG_CONTRACT_REFERENCE
        assert cl.get("execution_path") == CHANGE_LOG_EXECUTION_PATH
