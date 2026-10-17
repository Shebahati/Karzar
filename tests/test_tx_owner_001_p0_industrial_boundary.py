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
OEM_REG = PKG / "02-OEM-SOURCE-REGISTER.csv"
GAP_REG = PKG / "03-EVIDENCE-GAP-REGISTER.csv"
EXPECTED_IDS = set(P0_PRODUCT_IDS)


class TxOwner001P0BoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        script = ROOT / "scripts" / "audit_tx_owner_001_p0_industrial_boundary.py"
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

    def test_post_research_proposal_counts(self):
        recon = json.loads((PKG / "05-RECONCILIATION.json").read_text(encoding="utf-8"))
        self.assertEqual(recon["status"], "PASS")
        self.assertEqual(
            recon["post_research_proposal_counts"],
            {
                "CATALOG_EXIT_CANDIDATE": 16,
                "INDUSTRIAL_EXCEPTION_CANDIDATE": 1,
                "NEEDS_MORE_EVIDENCE": 2,
            },
        )

    def test_p0_subset_of_risk_register(self):
        with RISK.open(encoding="utf-8", newline="") as handle:
            risk_p0 = {
                int(r["product_id"])
                for r in csv.DictReader(handle)
                if r.get("priority") == "P0_BOUNDARY_CHECK"
            }
        self.assertEqual(risk_p0, EXPECTED_IDS)
        recon = json.loads((PKG / "05-RECONCILIATION.json").read_text(encoding="utf-8"))
        self.assertEqual(recon["risk_register_row_count"], 176)
        self.assertEqual(recon["overlap_owner_batches_001_004"], 0)
        self.assertEqual(recon["identity_checks_pass"], 19)

    def test_semantic_safety_3008(self):
        with (PKG / "01-P0-19-TECHNICAL-EVIDENCE-MATRIX.csv").open(encoding="utf-8", newline="") as handle:
            row = next(r for r in csv.DictReader(handle) if r["product_id"] == "3008")
        self.assertEqual(row["post_research_agent_proposal_not_owner_approved"], "NEEDS_MORE_EVIDENCE")
        self.assertEqual(row["approved_domain_fit_assessment"], "UNPROVEN")
        self.assertEqual(row["recommended_owner_review_option"], "REQUEST_MORE_EVIDENCE")
        with OEM_REG.open(encoding="utf-8", newline="") as handle:
            spruce = next(r for r in csv.DictReader(handle) if r["source_id"] == "MARKET-PARALLEL-CLAMP-WOOD")
        self.assertEqual(spruce["evidence_match_type"], "APPLICATION_CLASS_REFERENCE")

    def test_semantic_safety_3009_distributor_not_oem(self):
        with (PKG / "01-P0-19-TECHNICAL-EVIDENCE-MATRIX.csv").open(encoding="utf-8", newline="") as handle:
            row = next(r for r in csv.DictReader(handle) if r["product_id"] == "3009")
        self.assertEqual(row["oem_match_classification"], "DISTRIBUTOR_MARKET_FAMILY_REFERENCE")
        self.assertIn("UNRESOLVED", row["karzar_product_oem_identity_verification"])
        self.assertEqual(row["post_research_agent_proposal_not_owner_approved"], "INDUSTRIAL_EXCEPTION_CANDIDATE")
        with OEM_REG.open(encoding="utf-8", newline="") as handle:
            types = {r["evidence_match_type"] for r in csv.DictReader(handle) if r["related_karzar_product_ids"] == "3009"}
        self.assertTrue(types <= {"DISTRIBUTOR_MARKET_FAMILY_REFERENCE"})

    def test_semantic_safety_5227_physical_stock_unverified(self):
        with (PKG / "01-P0-19-TECHNICAL-EVIDENCE-MATRIX.csv").open(encoding="utf-8", newline="") as handle:
            row = next(r for r in csv.DictReader(handle) if r["product_id"] == "5227")
        self.assertEqual(row["exact_manufacturer_identity_status"], "UNRESOLVED")
        self.assertEqual(row["exact_manufacturer_article"], "")
        self.assertEqual(row["oem_match_classification"], "NEAR_MODEL_REFERENCE")
        self.assertEqual(
            row["karzar_product_oem_identity_verification"],
            "REFERENCE_MODEL_NEAR_QE-98L_PHYSICAL_STOCK_UNVERIFIED",
        )
        self.assertNotIn("EXACT_SKU", row["karzar_product_oem_identity_verification"])

    def test_semantic_safety_5301_title_mismatch_blocks(self):
        with (PKG / "01-P0-19-TECHNICAL-EVIDENCE-MATRIX.csv").open(encoding="utf-8", newline="") as handle:
            row = next(r for r in csv.DictReader(handle) if r["product_id"] == "5301")
        self.assertEqual(row["post_research_agent_proposal_not_owner_approved"], "NEEDS_MORE_EVIDENCE")
        self.assertIn("TITLE_MISMATCH", row["karzar_product_oem_identity_verification"])
        with GAP_REG.open(encoding="utf-8", newline="") as handle:
            gaps = [r for r in csv.DictReader(handle) if r["product_id"] == "5301"]
        title_gap = next(r for r in gaps if r["gap_id"] == "GAP-5301-TITLE-OEM-MISMATCH")
        self.assertEqual(title_gap["blocks_disposition"], "YES")
        self.assertIn("SY-2002M", title_gap["gap_description"])

    def test_m7_tyre_inflators_exact_oem(self):
        with (PKG / "01-P0-19-TECHNICAL-EVIDENCE-MATRIX.csv").open(encoding="utf-8", newline="") as handle:
            by_id = {r["product_id"]: r for r in csv.DictReader(handle)}
        for pid in ("5259", "5260", "5261"):
            self.assertEqual(by_id[pid]["oem_match_classification"], "EXACT_OEM_ARTICLE_MATCH")
            self.assertEqual(by_id[pid]["approved_domain_fit_assessment"], "DOES_NOT_FIT")

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
