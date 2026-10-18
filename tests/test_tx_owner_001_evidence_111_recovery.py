"""Tests for TX-OWNER-001 111-row evidence recovery package."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from catalog_target.tx_owner_001_evidence_111_recovery import (  # noqa: E402
    ACTION_REGISTER,
    CANONICAL_ACTION_REGISTER_GIT_BLOB_SHA1,
    PriorSlice,
    build_recovery_matrix,
    build_source_catalog,
    classify_recovery,
    classify_tier_semantics,
    fail_closed_reconciliation,
    git_blob_sha1,
    sha256_file,
    verify_action_register_identity,
)

PKG = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-evidence-111-recovery-2026-10-18"
REGISTER = (
    ROOT
    / "audit"
    / "taxonomy-phase1b-tx-owner-001-evidence-111-action-2026-10-18"
    / "01-EXACT-111-OPEN-EVIDENCE-ACTION-REGISTER.csv"
)
BLADEKAT_GROOVING_IDS = ("3090", "3091", "3093", "3095", "3096", "3097", "3098", "3099", "3101")


class TxOwner001Evidence111RecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        script = ROOT / "scripts" / "audit_tx_owner_001_evidence_111_recovery.py"
        subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True, timeout=120)

    def test_git_blob_sha1_differs_from_sha256(self):
        blob = git_blob_sha1(REGISTER)
        digest = sha256_file(REGISTER)
        self.assertEqual(blob, CANONICAL_ACTION_REGISTER_GIT_BLOB_SHA1)
        self.assertEqual(len(blob), 40)
        self.assertEqual(len(digest), 64)
        self.assertNotEqual(blob, digest)

    def test_register_identity_not_target_moved(self):
        identity = verify_action_register_identity()
        self.assertEqual(identity["register_identity_attestation"], "MATCH_CANONICAL_GIT_BLOB")
        pkg_identity = json.loads((PKG / "00-PACKAGE-IDENTITY.json").read_text(encoding="utf-8"))
        self.assertEqual(
            pkg_identity["canonical_action_register_git_blob_sha1"],
            CANONICAL_ACTION_REGISTER_GIT_BLOB_SHA1,
        )
        self.assertNotIn("TARGET_MOVED", pkg_identity.get("register_identity_attestation", ""))

    def test_negative_exact_oem_token_never_positive_semantics(self):
        self.assertEqual(
            classify_tier_semantics("UNRESOLVED_NO_EXACT_OEM_ARTICLE_MATCH"),
            "NEGATIVE_UNRESOLVED",
        )

    def test_matrix_exactly_111_unique_ids(self):
        with (PKG / "01-EVIDENCE-RECOVERY-MATRIX-111.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 111)
        with REGISTER.open(encoding="utf-8", newline="") as handle:
            reg_ids = {r["product_id"] for r in csv.DictReader(handle)}
        self.assertEqual({r["product_id"] for r in rows}, reg_ids)

    def test_bladekat_grooving_never_exact_oem(self):
        with (PKG / "01-EVIDENCE-RECOVERY-MATRIX-111.csv").open(encoding="utf-8", newline="") as handle:
            by_id = {r["product_id"]: r for r in csv.DictReader(handle)}
        for pid in BLADEKAT_GROOVING_IDS:
            self.assertEqual(by_id[pid]["exact_oem_documentary_recovered"], "NO")
            self.assertEqual(by_id[pid]["evidence_tier_semantics"], "NEGATIVE_UNRESOLVED")

    def test_owner_decision_unchanged_and_no_apply(self):
        with (PKG / "01-EVIDENCE-RECOVERY-MATRIX-111.csv").open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                self.assertEqual(row["owner_decision_unchanged"], "REQUEST_MORE_EVIDENCE")
                self.assertEqual(row["apply_authorization"], "NO")

    def test_wave_and_workstream_reconciliation(self):
        recon = json.loads((PKG / "06-RECONCILIATION.json").read_text(encoding="utf-8"))
        self.assertEqual(recon["status"], "PASS")
        self.assertEqual(recon["open_evidence_request_count"], 111)
        self.assertEqual(recon["documentary_exit_count_in_journals"], 151)
        self.assertEqual(recon["pr499_unique_product_ids"], 262)
        self.assertEqual(recon["owner_journal_unique_product_ids"], 262)
        self.assertEqual(recon["apply_authorization_rows"], 0)

    def test_physical_manifest_matches_matrix(self):
        with (PKG / "01-EVIDENCE-RECOVERY-MATRIX-111.csv").open(encoding="utf-8", newline="") as handle:
            need = {r["product_id"] for r in csv.DictReader(handle) if r["physical_stock_evidence_required"] == "YES"}
        with (PKG / "03-PHYSICAL-EVIDENCE-COLLECTION-MANIFEST.csv").open(encoding="utf-8", newline="") as handle:
            manifest = {r["product_id"] for r in csv.DictReader(handle)}
        self.assertEqual(need, manifest)

    def test_source_register_provenance_and_empty_urls(self):
        with (PKG / "02-SOURCE-REGISTER.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertGreater(len(rows), 10)
        for row in rows:
            self.assertTrue(row["provenance_class"])
            self.assertTrue(row["evidence_origin"])
            if not row["source_url"]:
                self.assertEqual(row["http_transport_status"], "PRIOR_REFERENCE_NO_URL")
            else:
                self.assertEqual(
                    row["http_transport_status"],
                    "TRANSPORT_PROBE_SKIPPED_REPRODUCIBLE_BUILD",
                )

    def test_matrix_source_traceability(self):
        with (PKG / "01-EVIDENCE-RECOVERY-MATRIX-111.csv").open(encoding="utf-8", newline="") as handle:
            matrix = list(csv.DictReader(handle))
        with (PKG / "02-SOURCE-REGISTER.csv").open(encoding="utf-8", newline="") as handle:
            source_ids = {r["source_id"] for r in csv.DictReader(handle)}
        for row in matrix:
            if row["traceable_source_ids"]:
                for sid in row["traceable_source_ids"].split("|"):
                    self.assertIn(sid, source_ids)

    def test_semantic_safety_5146_near_model_not_exact(self):
        with (PKG / "01-EVIDENCE-RECOVERY-MATRIX-111.csv").open(encoding="utf-8", newline="") as handle:
            row = next(r for r in csv.DictReader(handle) if r["product_id"] == "5146")
        self.assertEqual(row["exact_oem_documentary_recovered"], "NO")
        self.assertEqual(row["conflicting_evidence_flag"], "YES")

    def test_bounded_boundary_not_all_placeholder(self):
        with (PKG / "05-SEVEN-DOMAIN-TECHNICAL-BOUNDARY-ASSESSMENT.csv").open(encoding="utf-8", newline="") as handle:
            kinds = {r["technical_assessment_kind"] for r in csv.DictReader(handle)}
        self.assertIn("BOUNDED_WOOD_VS_METAL_CUTTING_OPEN", kinds)
        self.assertTrue(any(k.startswith("BOUNDED_") for k in kinds))
        self.assertNotEqual(kinds, {"OWNER_GATE_PLACEHOLDER"})

    def test_fail_closed_rejects_matrix_apply_yes(self):
        from catalog_target.tx_owner_001_evidence_111_recovery import load_action_register

        register_rows = load_action_register()
        matrix = [
            {
                "product_id": r["product_id"],
                "owner_decision_unchanged": "REQUEST_MORE_EVIDENCE",
                "apply_authorization": "YES",
                "physical_stock_evidence_required": "YES",
                "evidence_recovery_status": "REMOTE_RESEARCH_UNRESOLVED",
                "exact_oem_documentary_recovered": "NO",
                "partial_or_family_evidence": "NO",
                "conflicting_evidence_flag": "NO",
                "remote_research_unresolved": "YES",
            }
            for r in register_rows
        ]
        physical = [{"product_id": r["product_id"]} for r in register_rows]
        identity = verify_action_register_identity()
        with self.assertRaises(RuntimeError) as ctx:
            fail_closed_reconciliation(register_rows, matrix, physical, identity)
        self.assertIn("matrix_apply_authorization", str(ctx.exception))

    def test_fail_closed_raises_on_incomplete_journals(self):
        from types import SimpleNamespace

        from catalog_target import tx_owner_001_evidence_111_recovery as mod
        from catalog_target.tx_owner_001_evidence_111_recovery import load_action_register

        register_rows = load_action_register()
        matrix = [
            {
                "product_id": r["product_id"],
                "owner_decision_unchanged": "REQUEST_MORE_EVIDENCE",
                "apply_authorization": "NO",
                "physical_stock_evidence_required": "YES",
                "evidence_recovery_status": "REMOTE_RESEARCH_UNRESOLVED",
                "exact_oem_documentary_recovered": "NO",
                "partial_or_family_evidence": "NO",
                "conflicting_evidence_flag": "NO",
                "remote_research_unresolved": "YES",
            }
            for r in register_rows
        ]
        physical = [{"product_id": r["product_id"]} for r in register_rows]
        identity = verify_action_register_identity()
        one_batch = sorted(mod.OWNER_PKG.glob("OWNER-AUTHORIZATION-BATCH-*-2026-10-1*.csv"))[:1]
        fake_pkg = SimpleNamespace(glob=lambda _pattern: one_batch)

        with mock.patch.object(mod, "OWNER_PKG", fake_pkg):
            with self.assertRaises(RuntimeError) as ctx:
                fail_closed_reconciliation(register_rows, matrix, physical, identity)
            self.assertIn("RECONCILIATION_FAILED", str(ctx.exception))

    def test_classify_recovery_negative_tier_not_exact(self):
        catalog = build_source_catalog(
            [{"product_id": "3090", "sku": "3865", "evidence_workstream": "BLADEKAT_WOOD_METAL_34", "historical_title": "t"}]
        )
        reg = {
            "product_id": "3090",
            "sku": "3865",
            "evidence_workstream": "BLADEKAT_WOOD_METAL_34",
            "historical_title": "شیارزن cnc",
        }
        slices = [
            PriorSlice(
                "unresolved_11",
                {"exact_manufacturer_identity_status": "UNRESOLVED_NO_EXACT_OEM_ARTICLE_MATCH"},
            )
        ]
        out = classify_recovery(reg, slices, catalog)
        self.assertEqual(out["exact_oem_documentary_recovered"], "NO")


if __name__ == "__main__":
    unittest.main()
