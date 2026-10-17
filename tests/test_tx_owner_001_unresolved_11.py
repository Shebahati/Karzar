"""Tests for TX-OWNER-001 remaining 11 NEEDS_MORE evidence package."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from catalog_target.tx_owner_001_unresolved_11_research import (  # noqa: E402
    EXACT_MANUFACTURER_IDENTITY_STATUS,
    UNRESOLVED_11_PRODUCT_IDS,
)

PKG = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-unresolved-11-2026-10-17"
OWNER_PKG = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-owner-decision-package"
EXPECTED_IDS = {3090, 3091, 3093, 3095, 3096, 3097, 3098, 3099, 3101, 5146, 5147}


class TxOwner001Unresolved11Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not (PKG / "01-UNRESOLVED-11-EVIDENCE-MATRIX.csv").is_file():
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "audit_tx_owner_001_unresolved_11.py")],
                cwd=ROOT,
                check=True,
            )

    def test_matrix_exactly_eleven_ids(self):
        with (PKG / "01-UNRESOLVED-11-EVIDENCE-MATRIX.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 11)
        self.assertEqual({int(r["product_id"]) for r in rows}, EXPECTED_IDS)

    def test_all_exact_oem_identity_unresolved(self):
        with (PKG / "01-UNRESOLVED-11-EVIDENCE-MATRIX.csv").open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                self.assertEqual(
                    row["exact_manufacturer_identity_status"],
                    EXACT_MANUFACTURER_IDENTITY_STATUS,
                )
                self.assertEqual(row["karzar_product_oem_identity_verification"], EXACT_MANUFACTURER_IDENTITY_STATUS)
                self.assertEqual(row["exact_manufacturer_article"], "")

    def test_all_needs_more_agent_proposal(self):
        with (PKG / "01-UNRESOLVED-11-EVIDENCE-MATRIX.csv").open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                self.assertEqual(row["historical_pr499_proposal"], "NEEDS_MORE_EVIDENCE")
                self.assertEqual(row["agent_proposal_not_owner_approved"], "NEEDS_MORE_EVIDENCE")
                self.assertEqual(row["owner_decision"], "")
                self.assertEqual(row["authorization_status"], "PENDING")

    def test_m7_no_exact_q_suffix_claim(self):
        with (PKG / "01-UNRESOLVED-11-EVIDENCE-MATRIX.csv").open(encoding="utf-8", newline="") as handle:
            by_id = {r["product_id"]: r for r in csv.DictReader(handle)}
        for pid, sku in (("5146", "NC4277"), ("5147", "NC4299")):
            row = by_id[pid]
            self.assertEqual(row["karzar_catalog_sku"], sku)
            self.assertIn("NEAR_MODEL", row["confidence_basis"])
            self.assertIn("Q", row["competing_interpretations"])

    def test_grooving_finishing_low_confidence_application_only(self):
        grooving_ids = {"3090", "3091", "3093", "3095", "3096", "3097", "3098", "3099", "3101"}
        with (PKG / "01-UNRESOLVED-11-EVIDENCE-MATRIX.csv").open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row["product_id"] not in grooving_ids:
                    continue
                self.assertEqual(row["confidence_level"], "LOW")
                self.assertIn("WOODWORKING", row["proposed_application_class"])

    def test_evidence_gap_register(self):
        with (PKG / "03-EVIDENCE-GAP-REGISTER.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertGreaterEqual(len(rows), 11)
        pids = {r["product_id"] for r in rows}
        self.assertTrue(EXPECTED_IDS <= {int(x) for x in pids})

    def test_owner_batches_untouched(self):
        for batch in (
            OWNER_PKG / "OWNER-AUTHORIZATION-BATCH-001-2026-10-17.csv",
            OWNER_PKG / "OWNER-AUTHORIZATION-BATCH-002-2026-10-17.csv",
            OWNER_PKG / "OWNER-AUTHORIZATION-BATCH-003-2026-10-17.csv",
        ):
            with batch.open(encoding="utf-8", newline="") as handle:
                pids = {r.get("product_id") for r in csv.DictReader(handle)}
            for eid in EXPECTED_IDS:
                self.assertNotIn(str(eid), pids)

    def test_frozen_input_shas_in_identity(self):
        identity = json.loads((PKG / "00-PACKAGE-IDENTITY.json").read_text(encoding="utf-8"))
        self.assertEqual(identity["safety"]["OWNER_BATCH_JOURNALS_TOUCHED"], "NO")
        self.assertFalse(identity["owner_batches_mutated"])
        self.assertEqual(identity["product_ids"], list(UNRESOLVED_11_PRODUCT_IDS))


if __name__ == "__main__":
    unittest.main()
