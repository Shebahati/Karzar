"""Tests for TX-OWNER-001 P0 industrial boundary evidence package."""

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
sys.path.insert(0, str(SCRIPTS))

from catalog_target.tx_owner_001_p0_industrial_boundary_research import (  # noqa: E402
    P0_PRODUCT_IDS,
)

PKG = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-p0-industrial-boundary-2026-10-17"
OWNER_PKG = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-owner-decision-package"
RISK = (
    ROOT
    / "audit"
    / "taxonomy-phase1b-tx-owner-001-low-confidence-risk-triage-2026-10-17"
    / "01-PRIORITIZED-RISK-REGISTER-176.csv"
)
EXPECTED_IDS = set(P0_PRODUCT_IDS)


class TxOwner001P0BoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        script = ROOT / "scripts" / "audit_tx_owner_001_p0_industrial_boundary.py"
        if not (PKG / "01-P0-19-TECHNICAL-EVIDENCE-MATRIX.csv").is_file():
            subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True)

    def test_matrix_exactly_nineteen_p0_ids(self):
        with (PKG / "01-P0-19-TECHNICAL-EVIDENCE-MATRIX.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 19)
        self.assertEqual({int(r["product_id"]) for r in rows}, EXPECTED_IDS)

    def test_all_owner_decisions_pending(self):
        with (PKG / "01-P0-19-TECHNICAL-EVIDENCE-MATRIX.csv").open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                self.assertEqual(row["owner_decision"], "")
                self.assertEqual(row["authorization_status"], "PENDING")
                self.assertEqual(row["historical_pr499_proposal"], "CATALOG_EXIT_CANDIDATE")

    def test_p0_subset_of_risk_register(self):
        with RISK.open(encoding="utf-8", newline="") as handle:
            risk_p0 = {
                int(r["product_id"])
                for r in csv.DictReader(handle)
                if r.get("priority") == "P0_BOUNDARY_CHECK"
            }
        self.assertEqual(risk_p0, EXPECTED_IDS)

    def test_sy2001m_needs_more_evidence(self):
        with (PKG / "01-P0-19-TECHNICAL-EVIDENCE-MATRIX.csv").open(encoding="utf-8", newline="") as handle:
            row = next(r for r in csv.DictReader(handle) if r["product_id"] == "5301")
        self.assertEqual(row["post_research_agent_proposal_not_owner_approved"], "NEEDS_MORE_EVIDENCE")
        self.assertIn("TITLE_MISMATCH", row["karzar_product_oem_identity_verification"])

    def test_groz_arbor_toolholding_hypothesis(self):
        with (PKG / "01-P0-19-TECHNICAL-EVIDENCE-MATRIX.csv").open(encoding="utf-8", newline="") as handle:
            row = next(r for r in csv.DictReader(handle) if r["product_id"] == "3009")
        self.assertEqual(row["industrial_domain_hypothesis"], "KZ.DOM.TOOLHOLDING")
        self.assertEqual(row["post_research_agent_proposal_not_owner_approved"], "INDUSTRIAL_EXCEPTION_CANDIDATE")
        self.assertIn("UNRESOLVED", row["karzar_product_oem_identity_verification"])

    def test_m7_tyre_inflators_exact_oem(self):
        with (PKG / "01-P0-19-TECHNICAL-EVIDENCE-MATRIX.csv").open(encoding="utf-8", newline="") as handle:
            by_id = {r["product_id"]: r for r in csv.DictReader(handle)}
        for pid in ("5259", "5260", "5261"):
            self.assertEqual(by_id[pid]["oem_match_classification"], "EXACT_OEM_ARTICLE_MATCH")
            self.assertEqual(by_id[pid]["approved_domain_fit_assessment"], "DOES_NOT_FIT")

    def test_industrial_boundary_nineteen_rows(self):
        with (PKG / "04-INDUSTRIAL-BOUNDARY-ANALYSIS.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 19)

    def test_owner_batches_001_004_untouched_hashes(self):
        identity = json.loads((PKG / "00-PACKAGE-IDENTITY.json").read_text(encoding="utf-8"))
        for i in range(1, 5):
            batch = OWNER_PKG / f"OWNER-AUTHORIZATION-BATCH-00{i}-2026-10-17.csv"
            digest = hashlib.sha256(batch.read_bytes()).hexdigest()
            self.assertEqual(identity[f"owner_batch_00{i}_sha256"], digest)
        for batch in OWNER_PKG.glob("OWNER-AUTHORIZATION-BATCH-00*-2026-10-17.csv"):
            with batch.open(encoding="utf-8", newline="") as handle:
                pids = {r.get("product_id") for r in csv.DictReader(handle)}
            for eid in EXPECTED_IDS:
                self.assertNotIn(str(eid), pids)


if __name__ == "__main__":
    unittest.main()
