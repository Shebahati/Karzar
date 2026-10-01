"""Phase 2C APPLY rehearsal — validation and safety gates (no live DB)."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from app.domain.phase2c_apply import (
    OWNER_FROZEN_ROWS,
    OWNER_FROZEN_SHA256,
    reconcile_targets,
    snapshot_sha256,
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
    digest = __import__("hashlib").sha256(p.read_bytes()).hexdigest()
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


def test_rehearsal_sql_ends_with_rollback():
    sql = build_rehearsal_sql([_sample_frozen_row()], OWNER_FROZEN_SHA256)
    assert "ROLLBACK;" in sql
    assert "COMMIT" not in sql.upper().replace("ON COMMIT DROP", "")


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
    manifest = __import__("json").loads(manifest_path.read_text(encoding="utf-8"))
    validate_freeze_manifest(manifest, meta["sha256"])


def test_snapshot_sha_stable_for_fixed_order():
    rows = [{"product_id": "1", "sku": "b"}, {"product_id": "2", "sku": "a"}]
    assert snapshot_sha256(rows, ("product_id", "sku")) == snapshot_sha256(
        list(rows), ("product_id", "sku")
    )
