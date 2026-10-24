"""Owner manifest + backup attestation gate tests."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.ast_price_catalog_backup_attestation import (  # noqa: E402
    assert_production_backup_attestation_gate,
)
from catalog_target.ast_price_catalog_manifest_acceptance import (  # noqa: E402
    MANIFEST_ABSENT,
    OWNER_MANIFEST_ACCEPTED,
    assert_owner_manifest_acceptance_gate,
    build_cohort_owner_bundle,
    build_update_stage_owner_bundle,
    manifest_file_sha256,
    recompute_manifest_bundle_sha256,
)
from catalog_target.sales_wave_apply import ApplyAbort  # noqa: E402


class ManifestGateTests(unittest.TestCase):
    def test_empty_create_manifest_is_absent_not_zero_byte_hash(self) -> None:
        path = Path(tempfile.mkstemp(suffix=".csv")[1])
        path.write_text("", encoding="utf-8")
        self.assertEqual(manifest_file_sha256(path), MANIFEST_ABSENT)
        self.assertNotEqual(manifest_file_sha256(path), "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

    def test_owner_acceptance_required(self) -> None:
        bundle = build_cohort_owner_bundle(
            apply_cohort="update",
            manifest_hashes={
                "UPDATE_PRODUCTS.csv": "abc",
                "CREATE_PRODUCTS.csv": MANIFEST_ABSENT,
                "SOURCE_ROW_LEDGER.csv": "led",
            },
            expected_update_count=1,
            expected_create_count=0,
        )
        path = Path(tempfile.mkstemp(suffix=".json")[1])
        path.write_text(json.dumps(bundle), encoding="utf-8")
        with self.assertRaises(ApplyAbort):
            assert_owner_manifest_acceptance_gate(
                cohort="update",
                bundle_path=path,
                confirm_manifest_bundle_sha256=bundle["manifest_bundle_sha256"],
                confirm_owner_acceptance_id="owner-1",
                live_update_manifest_sha256="abc",
                live_create_manifest_sha256=MANIFEST_ABSENT,
                live_update_count=1,
                live_create_count=0,
            )

    def test_owner_acceptance_passes_when_signed(self) -> None:
        bundle = build_cohort_owner_bundle(
            apply_cohort="update",
            manifest_hashes={
                "UPDATE_PRODUCTS.csv": "abc",
                "CREATE_PRODUCTS.csv": MANIFEST_ABSENT,
                "SOURCE_ROW_LEDGER.csv": "led",
            },
            expected_update_count=1,
            expected_create_count=0,
        )
        bundle["owner_acceptance_status"] = OWNER_MANIFEST_ACCEPTED
        bundle["owner_acceptance_id"] = "owner-accept-001"
        bundle["owner_acceptance_at"] = "2026-10-24T12:00:00Z"
        bundle["owner_acceptance_by"] = "owner@karzar"
        path = Path(tempfile.mkstemp(suffix=".json")[1])
        path.write_text(json.dumps(bundle), encoding="utf-8")
        assert_owner_manifest_acceptance_gate(
            cohort="update",
            bundle_path=path,
            confirm_manifest_bundle_sha256=bundle["manifest_bundle_sha256"],
            confirm_owner_acceptance_id="owner-accept-001",
            live_update_manifest_sha256="abc",
            live_create_manifest_sha256=MANIFEST_ABSENT,
            live_update_count=1,
            live_create_count=0,
        )

    def test_bundle_digest_tamper_rejected(self) -> None:
        bundle = build_cohort_owner_bundle(
            apply_cohort="update",
            manifest_hashes={
                "UPDATE_PRODUCTS.csv": "abc",
                "CREATE_PRODUCTS.csv": MANIFEST_ABSENT,
                "SOURCE_ROW_LEDGER.csv": "led",
            },
            expected_update_count=1,
            expected_create_count=0,
        )
        bundle["owner_acceptance_status"] = OWNER_MANIFEST_ACCEPTED
        bundle["owner_acceptance_id"] = "owner-accept-001"
        bundle["owner_acceptance_at"] = "2026-10-24T12:00:00Z"
        bundle["owner_acceptance_by"] = "owner@karzar"
        bundle["expected_update_count"] = 999
        path = Path(tempfile.mkstemp(suffix=".json")[1])
        path.write_text(json.dumps(bundle), encoding="utf-8")
        with self.assertRaises(ApplyAbort):
            assert_owner_manifest_acceptance_gate(
                cohort="update",
                bundle_path=path,
                confirm_manifest_bundle_sha256=bundle["manifest_bundle_sha256"],
                confirm_owner_acceptance_id="owner-accept-001",
                live_update_manifest_sha256="abc",
                live_create_manifest_sha256=MANIFEST_ABSENT,
                live_update_count=999,
                live_create_count=0,
            )

    def test_stage_bundle_v3_digest_stable_without_commit(self) -> None:
        bundle = build_update_stage_owner_bundle(
            update_stage="stage1",
            master_update_manifest_sha256="master",
            stage_manifest_sha256="stage",
            ledger_manifest_sha256="led",
            expected_update_count=5,
            product_id_allowlist_sha256="allow",
        )
        self.assertEqual(recompute_manifest_bundle_sha256(bundle), bundle["manifest_bundle_sha256"])
        self.assertEqual(bundle.get("bundle_schema_version"), "3")

    def test_backup_placeholder_rejected(self) -> None:
        path = Path(tempfile.mkstemp(suffix=".json")[1])
        path.write_text(
            json.dumps(
                {
                    "backup_completion_status": "COMPLETED",
                    "restore_validation_status": "VERIFIED",
                    "backup_artifact_sha256": "PENDING",
                    "backup_artifact_location": "/tmp/x",
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaises(ApplyAbort):
            assert_production_backup_attestation_gate(
                attestation_path=path,
                confirm_backup_artifact_sha256="PENDING",
            )


if __name__ == "__main__":
    unittest.main()
