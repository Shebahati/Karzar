"""Phase 2C real APPLY — safety gates (no live DB mutation)."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pytest
from app.domain.phase2c_apply import (
    OWNER_FROZEN_ROWS,
    OWNER_FROZEN_SHA256,
    change_log_reason_includes_full_sha,
    reconcile_targets,
    validate_freeze_manifest,
    validate_frozen_artifact,
)
from app.domain.phase2c_real_apply import (
    assert_confirmation_sha,
    build_real_apply_sql,
    build_recovery_target_rows,
    parse_real_apply_metrics,
    real_apply_change_log_reason,
    real_apply_logic_file_sha256,
    second_apply_blocked_reason,
)
from scripts.ops.phase2c_manufacturer_identity_apply_once import (
    FORBIDDEN_FLAGS,
    _reject_forbidden,
)
from scripts.ops.phase2c_manufacturer_identity_apply_once import (
    main as real_apply_main,
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


def test_forbidden_flags_rejected():
    for flag in FORBIDDEN_FLAGS:
        with pytest.raises(SystemExit) as ei:
            _reject_forbidden([flag])
        assert ei.value.code == 2


def test_plain_invocation_does_not_require_confirm_but_apply_does(tmp_path: Path, monkeypatch):
    # --apply without confirm must fail closed before any DB work.
    monkeypatch.setattr(
        "scripts.ops.phase2c_manufacturer_identity_apply_once.collect_runtime_identity",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("should not reach DB")),
    )
    rc = real_apply_main(["--apply"])
    assert rc == 2


def test_wrong_confirmation_sha_fails():
    with pytest.raises(ValueError, match="confirm-cohort-sha mismatch"):
        assert_confirmation_sha("deadbeef")


def test_missing_confirmation_sha_fails():
    with pytest.raises(ValueError, match="missing --confirm-cohort-sha"):
        assert_confirmation_sha(None)


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


def test_reconcile_blocks_missing_deleted_sku_brand_name_existing():
    frozen = [_sample_frozen_row()]
    assert reconcile_targets(frozen, {})[0].reason == "missing_target_product"
    assert (
        reconcile_targets(
            frozen,
            {
                "100": {
                    "sku": "1108-150",
                    "brand_id": "3",
                    "manufacturer_code": "",
                    "name": "n",
                    "slug": "s",
                    "deleted_at": "2026-01-01",
                }
            },
        )[0].reason
        == "deleted_target"
    )
    assert (
        reconcile_targets(
            frozen,
            {
                "100": {
                    "sku": "OTHER",
                    "brand_id": "3",
                    "manufacturer_code": "",
                    "name": "n",
                    "slug": "s",
                    "deleted_at": "",
                }
            },
        )[0].reason
        == "sku_mismatch"
    )
    assert (
        reconcile_targets(
            frozen,
            {
                "100": {
                    "sku": "1108-150",
                    "brand_id": "9",
                    "manufacturer_code": "",
                    "name": "n",
                    "slug": "s",
                    "deleted_at": "",
                }
            },
        )[0].reason
        == "brand_mismatch"
    )
    assert (
        reconcile_targets(
            frozen,
            {
                "100": {
                    "sku": "1108-150",
                    "brand_id": "3",
                    "manufacturer_code": "",
                    "name": "other",
                    "slug": "s",
                    "deleted_at": "",
                }
            },
        )[0].reason
        == "name_mismatch"
    )
    assert (
        reconcile_targets(
            frozen,
            {
                "100": {
                    "sku": "1108-150",
                    "brand_id": "3",
                    "manufacturer_code": "ALREADY",
                    "name": "n",
                    "slug": "s",
                    "deleted_at": "",
                }
            },
        )[0].reason
        == "manufacturer_code_already_populated"
    )


def test_global_prior_manufacturer_code_blocks_second_apply():
    reason = second_apply_blocked_reason(target_existing_code_count=1350)
    assert reason is not None
    assert "already populated" in reason
    assert second_apply_blocked_reason(target_existing_code_count=0) is None


def test_real_apply_reason_includes_full_sha_and_fits():
    reason = real_apply_change_log_reason(OWNER_FROZEN_SHA256)
    assert change_log_reason_includes_full_sha(reason, OWNER_FROZEN_SHA256)
    assert "owner-authorized" in reason
    assert len(reason) <= 255


def test_build_real_apply_sql_has_commit_and_assertions():
    rows = [_sample_frozen_row(product_id=str(i), candidate_manufacturer_code=f"C{i}") for i in range(3)]
    sql = build_real_apply_sql(rows, cohort_sha256=OWNER_FROZEN_SHA256, expected_rows=3)
    assert "BEGIN ISOLATION LEVEL SERIALIZABLE" in sql
    assert "pg_advisory_xact_lock" in sql
    assert "FOR UPDATE" in sql
    assert "RAISE EXCEPTION" in sql
    assert "COMMIT;" in sql
    assert "METRIC:committed:1" in sql
    # success path ends with COMMIT; no standalone ROLLBACK statement
    assert not any(line.strip().upper() == "ROLLBACK;" for line in sql.splitlines())
    assert OWNER_FROZEN_SHA256 in sql


def test_parse_real_apply_metrics_requires_committed():
    out = "\n".join(
        [
            "METRIC:collision_groups:0",
            "METRIC:change_logs:1350",
            "METRIC:exact_matches:1350",
            "METRIC:locked_rows:1350",
            "METRIC:nontarget_changes:0",
            "METRIC:protected_drift:0",
            "METRIC:updated_rows:1350",
            "METRIC:committed:1",
        ]
    )
    m = parse_real_apply_metrics(out)
    assert m["committed"] == 1
    assert m["updated_rows"] == 1350


def test_recovery_artifacts_generated():
    rows = [_sample_frozen_row()]
    recovery = build_recovery_target_rows(rows)
    assert recovery[0]["pre_apply_manufacturer_code"] == ""
    assert recovery[0]["applied_manufacturer_code"] == "1108-150"


def test_owner_frozen_artifact_and_manifest():
    root = Path(__file__).resolve().parents[1]
    art = root / "audit/product-naming-phase2c-discovery/BACKFILL_EXACT_FROZEN.csv"
    man = root / "audit/product-naming-phase2c-discovery/BACKFILL_EXACT_FREEZE_MANIFEST.json"
    rows, meta = validate_frozen_artifact(art)
    assert len(rows) == OWNER_FROZEN_ROWS
    assert meta["sha256"] == OWNER_FROZEN_SHA256
    validate_freeze_manifest(
        __import__("json").loads(man.read_text(encoding="utf-8")),
        meta["sha256"],
    )


def test_real_apply_logic_file_hashes_present():
    root = Path(__file__).resolve().parents[1]
    hashes = real_apply_logic_file_sha256(root)
    assert "app/domain/phase2c_real_apply.py" in hashes
    assert "scripts/ops/phase2c_manufacturer_identity_apply_once.py" in hashes
    assert all(len(v) == 64 for v in hashes.values())


def test_wrong_row_count_fails_sql_builder():
    with pytest.raises(ValueError, match="frozen_rows"):
        build_real_apply_sql([_sample_frozen_row()], cohort_sha256=OWNER_FROZEN_SHA256)


def test_immutable_evidence_cannot_be_silently_overwritten(tmp_path: Path):
    from scripts.ops.phase2c_manufacturer_identity_apply_once import (
        EvidenceImmutabilityError,
        write_json,
    )

    path = tmp_path / "PRE_APPLY_DB_BASELINE.json"
    path.write_text('{"ok": true}\n', encoding="utf-8")
    with pytest.raises(EvidenceImmutabilityError, match="immutable"):
        write_json(path, {"ok": False})
    assert path.read_text(encoding="utf-8") == '{"ok": true}\n'


def test_second_run_redirects_to_probe_dir_when_apply_verified(tmp_path: Path):
    from scripts.ops.phase2c_manufacturer_identity_apply_once import (
        resolve_writable_out_dir,
        write_json,
    )

    first = tmp_path / "real-apply"
    first.mkdir()
    write_json(first / "REAL_APPLY_MANIFEST.json", {"status": "APPLIED_VERIFIED"})
    # Seed an immutable first-run artifact.
    (first / "PRE_APPLY_DB_BASELINE.json").write_text('{"first": true}\n', encoding="utf-8")
    probe = resolve_writable_out_dir(first, default_root=first)
    assert probe != first
    assert probe.parent.name == "probes"
    # Writing into probe dir must not touch first-run file.
    write_json(probe / "PRE_APPLY_DB_BASELINE.json", {"probe": True})
    assert (first / "PRE_APPLY_DB_BASELINE.json").read_text(encoding="utf-8") == '{"first": true}\n'


def test_recovery_manifest_payload_hash_semantics(tmp_path: Path):
    import hashlib
    import json

    from scripts.ops.phase2c_manufacturer_identity_apply_once import (
        canonical_json_bytes,
        write_recovery_package,
    )

    rows = [_sample_frozen_row(product_id=str(i), candidate_manufacturer_code=f"C{i}") for i in range(3)]
    # Expand frozen rows for recovery package helper which only needs candidate fields.
    package = write_recovery_package(tmp_path, rows, cohort_sha256=OWNER_FROZEN_SHA256)
    assert "manifest_payload_sha256" in package
    assert "manifest_sha256" not in package
    on_disk = json.loads((tmp_path / "RECOVERY_MANIFEST.json").read_text(encoding="utf-8"))
    embedded = on_disk["manifest_payload_sha256"]
    without = {k: v for k, v in on_disk.items() if k != "manifest_payload_sha256"}
    recomputed = hashlib.sha256(canonical_json_bytes(without)).hexdigest()
    assert embedded == recomputed
    final_file = hashlib.sha256((tmp_path / "RECOVERY_MANIFEST.json").read_bytes()).hexdigest()
    assert final_file != embedded


def test_committed_recovery_manifest_and_reconstruction_metadata():
    import json

    root = Path(__file__).resolve().parents[1]
    evidence = root / "audit/product-naming-phase2c-real-apply"
    manifest = json.loads((evidence / "RECOVERY_MANIFEST.json").read_text(encoding="utf-8"))
    assert "manifest_payload_sha256" in manifest
    assert "manifest_sha256" not in manifest
    assert manifest["rows"] == OWNER_FROZEN_ROWS
    assert manifest["cohort_sha256"] == OWNER_FROZEN_SHA256
    recon = json.loads((evidence / "PRE_APPLY_BASELINE_RECONSTRUCTION.json").read_text(encoding="utf-8"))
    assert recon["evidence_type"] == "RECONSTRUCTED_FROM_AUTHORITATIVE_PRE_APPLY_BACKUP"
    assert recon["staging_live_db_mutation_during_reconstruction"] == "NO"
    integrity = json.loads((evidence / "APPLY_EVIDENCE_INTEGRITY_REPORT.json").read_text(encoding="utf-8"))
    assert integrity["overall_evidence_integrity"] == "PASS"
    assert integrity["recovery_package"]["self_hash_ambiguity_removed"] is True
    assert (
        integrity["recovery_package"]["final_manifest_file_sha256"]
        != integrity["recovery_package"]["manifest_payload_sha256"]
    )
