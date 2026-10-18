"""Tests for TX-OWNER-001 111-row evidence recovery package."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PKG = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-evidence-111-recovery-2026-10-18"
REGISTER = (
    ROOT
    / "audit"
    / "taxonomy-phase1b-tx-owner-001-evidence-111-action-2026-10-18"
    / "01-EXACT-111-OPEN-EVIDENCE-ACTION-REGISTER.csv"
)


class TxOwner001Evidence111RecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        script = ROOT / "scripts" / "audit_tx_owner_001_evidence_111_recovery.py"
        subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True, timeout=600)

    def test_matrix_exactly_111_unique_ids(self):
        with (PKG / "01-EVIDENCE-RECOVERY-MATRIX-111.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 111)
        reg_ids = {r["product_id"] for r in csv.DictReader(REGISTER.open(encoding="utf-8"))}
        self.assertEqual({r["product_id"] for r in rows}, reg_ids)

    def test_owner_decision_unchanged_and_no_apply(self):
        with (PKG / "01-EVIDENCE-RECOVERY-MATRIX-111.csv").open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                self.assertEqual(row["owner_decision_unchanged"], "REQUEST_MORE_EVIDENCE")
                self.assertEqual(row["apply_authorization"], "NO")
                self.assertEqual(row["new_owner_disposition"], "")

    def test_wave_and_workstream_reconciliation(self):
        recon = json.loads((PKG / "06-RECONCILIATION.json").read_text(encoding="utf-8"))
        self.assertEqual(recon["status"], "PASS")
        self.assertEqual(recon["open_evidence_request_count"], 111)
        self.assertTrue(recon["documentary_exit_count_matches_expected"])
        self.assertEqual(recon["apply_authorization_rows"], 0)
        self.assertEqual(
            recon["wave_counts"],
            {"W1_BLADEKAT_34": 34, "W2_P1_31": 31, "W3_P2_19": 19, "W4_SPECIAL_27": 27},
        )

    def test_physical_manifest_covers_all_physical_required(self):
        with (PKG / "01-EVIDENCE-RECOVERY-MATRIX-111.csv").open(encoding="utf-8", newline="") as handle:
            need = {r["product_id"] for r in csv.DictReader(handle) if r["physical_stock_evidence_required"] == "YES"}
        with (PKG / "03-PHYSICAL-EVIDENCE-COLLECTION-MANIFEST.csv").open(encoding="utf-8", newline="") as handle:
            manifest = {r["product_id"] for r in csv.DictReader(handle)}
        self.assertEqual(need, manifest)

    def test_source_register_has_access_dates(self):
        with (PKG / "02-SOURCE-REGISTER.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertGreater(len(rows), 20)
        for row in rows:
            self.assertTrue(row["access_date_utc"])
            self.assertIn(row["retrieval_status"], ("HTTP_OK", "HTTP_ERROR", "HTTP_TIMEOUT", "HTTP_UNAVAILABLE", "HTTP_PROBE_ERROR", "SKIPPED_NON_HTTP"))

    def test_register_sha_pinned_in_identity(self):
        identity = json.loads((PKG / "00-PACKAGE-IDENTITY.json").read_text(encoding="utf-8"))
        digest = hashlib.sha256(REGISTER.read_bytes()).hexdigest()
        self.assertEqual(identity["canonical_action_register_sha256"], digest)

    def test_semantic_safety_5146_near_model_not_exact(self):
        with (PKG / "01-EVIDENCE-RECOVERY-MATRIX-111.csv").open(encoding="utf-8", newline="") as handle:
            row = next(r for r in csv.DictReader(handle) if r["product_id"] == "5146")
        self.assertEqual(row["exact_oem_documentary_recovered"], "NO")
        self.assertEqual(row["conflicting_evidence_flag"], "YES")


if __name__ == "__main__":
    unittest.main()
