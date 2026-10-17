"""Tests for TX-OWNER-001 Owner decision package generator."""

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

from catalog_target.tx_owner_001_external_sources import APPROVED_DOMAIN_CODES  # noqa: E402
from catalog_target.tx_owner_001_owner_post_research import (  # noqa: E402
    M7_POST_RESEARCH_EXIT_IDS,
    POST_RESEARCH_EXPECTED,
    PR499_ANCHOR_DISPOSITIONS,
    enrich_row,
)
from catalog_target.tx_owner_001_semantic_review import load_cohort_products  # noqa: E402

PKG = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-owner-decision-package"
BASELINE = ROOT / "audit" / "taxonomy-phase1b-baseline-2026-10-15"
REVIEW = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-review"

M7_SKUS = {
    5139: "NC4233Q",
    5140: "NC4233QH",
    5174: "PA201",
    5176: "PA211",
    5177: "PA301",
    5178: "PA301V",
}


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class TxOwner001OwnerDecisionPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not (PKG / "06-RECONCILIATION-262.json").is_file():
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "audit_tx_owner_001_owner_decision_package.py")],
                cwd=ROOT,
                check=True,
            )

    def test_package_reconciliation(self):
        recon = json.loads((PKG / "06-RECONCILIATION-262.json").read_text(encoding="utf-8"))
        self.assertEqual(recon["unique_product_ids"], 262)
        self.assertEqual(len(recon["product_ids_accounted"]), 262)
        self.assertFalse(recon["category_154_included"])
        self.assertFalse(recon["category_156_oils_included"])
        for key, expected in PR499_ANCHOR_DISPOSITIONS.items():
            self.assertEqual(
                recon["disposition_counts_historical_pr499_anchor"][key],
                expected,
                key,
            )
        for key, expected in POST_RESEARCH_EXPECTED.items():
            self.assertEqual(
                recon["disposition_counts_post_research_effective"][key],
                expected,
                key,
            )
        self.assertEqual(
            set(recon["m7_post_research_exit_product_ids"]),
            set(M7_POST_RESEARCH_EXIT_IDS),
        )
        self.assertEqual(set(recon["post_research_exit_delta_product_ids"]), set(M7_POST_RESEARCH_EXIT_IDS))

    def test_frozen_pr499_population(self):
        review_ids = sorted(int(r["product_id"]) for r in _load_csv(REVIEW / "01-262-PRODUCT-SEMANTIC-REVIEW.csv"))
        recon = json.loads((PKG / "06-RECONCILIATION-262.json").read_text(encoding="utf-8"))
        self.assertEqual(recon["product_ids_accounted"], review_ids)

    def test_critical_matrix_twenty(self):
        rows = _load_csv(PKG / "01-CRITICAL-20-EVIDENCE-MATRIX.csv")
        self.assertEqual(len(rows), 20)
        ids = {int(r["product_id"]) for r in rows}
        self.assertIn(2915, ids)
        self.assertIn(3238, ids)
        for r in rows:
            self.assertEqual(r["authorization_status"], "PENDING")
            self.assertEqual(r["owner_decision"], "")

    def test_artifacts_agree_on_post_research_proposals(self):
        matrix = {r["product_id"]: r for r in _load_csv(PKG / "01-CRITICAL-20-EVIDENCE-MATRIX.csv")}
        sheet = {r["product_id"]: r for r in _load_csv(PKG / "05-PROPOSED-DECISION-SHEET-262.csv")}
        journal = {r["product_id"]: r for r in _load_csv(PKG / "07-OWNER-APPROVAL-JOURNAL-TEMPLATE.csv")}
        self.assertEqual(len(sheet), 262)
        self.assertEqual(len(journal), 262)
        for pid, row in sheet.items():
            self.assertEqual(row["post_research_proposal"], journal[pid]["post_research_proposal"])
            self.assertEqual(
                row["historical_pr499_proposal"],
                journal[pid]["historical_pr499_proposal"],
            )
            if pid in matrix:
                self.assertEqual(row["post_research_proposal"], matrix[pid]["post_research_proposal"])
                self.assertEqual(
                    row["historical_pr499_proposal"],
                    matrix[pid]["historical_pr499_proposal"],
                )

    def test_six_m7_corrections(self):
        sheet = {r["product_id"]: r for r in _load_csv(PKG / "05-PROPOSED-DECISION-SHEET-262.csv")}
        oem = _load_csv(PKG / "04-OEM-TECHNICAL-SOURCE-REGISTER.csv")
        oem_by_sku = {s["sku_match"]: s for s in oem}
        for pid, sku in M7_SKUS.items():
            row = sheet[str(pid)]
            self.assertEqual(row["historical_pr499_proposal"], "NEEDS_MORE_EVIDENCE")
            self.assertEqual(row["post_research_proposal"], "CATALOG_EXIT_CANDIDATE")
            self.assertIn("OEM-M7", row["oem_source_ids"])
            self.assertIn(sku, oem_by_sku)
            self.assertEqual(oem_by_sku[sku]["verification_status"], "HUMAN_VERIFIED_URL")

    def test_nc4277_nc4299_not_inferred(self):
        sheet = {r["product_id"]: r for r in _load_csv(PKG / "05-PROPOSED-DECISION-SHEET-262.csv")}
        for pid in ("5146", "5147"):
            row = sheet[pid]
            self.assertEqual(row["post_research_proposal"], "NEEDS_MORE_EVIDENCE")
            self.assertEqual(row["post_research_evidence_basis"], "UNRESOLVED")

    def test_low_confidence_register_176(self):
        rows = _load_csv(PKG / "03-LOW-CONFIDENCE-EXIT-RISK-REGISTER.csv")
        self.assertEqual(len(rows), 176)

    def test_owner_journal_no_prefilled_approval(self):
        rows = _load_csv(PKG / "07-OWNER-APPROVAL-JOURNAL-TEMPLATE.csv")
        self.assertEqual(len(rows), 262)
        self.assertTrue(all(r["authorization_status"] == "PENDING" for r in rows))
        self.assertTrue(all(r["owner_decision"] == "" for r in rows))
        industrial = [r for r in rows if r["post_research_proposal"] == "INDUSTRIAL_EXCEPTION_CANDIDATE"]
        self.assertEqual(len(industrial), 1)
        self.assertEqual(industrial[0]["product_id"], "2915")
        self.assertEqual(industrial[0]["authorization_status"], "PENDING")

    def test_family_membership_complete(self):
        rows = _load_csv(PKG / "08-FAMILY-MEMBERSHIP-COMPLETE-262.csv")
        self.assertEqual(len(rows), 262)
        ids = [r["product_id"] for r in rows]
        self.assertEqual(len(ids), len(set(ids)))
        hist_exit = [r for r in rows if r["exit_cohort_tag"] == "PRIORITY_B_HISTORICAL_EXIT"]
        self.assertEqual(len(hist_exit), 242)
        delta = [r for r in rows if r["exit_cohort_tag"] == "POST_RESEARCH_EXIT_DELTA"]
        self.assertEqual(len(delta), 6)
        post_exit = [r for r in rows if r["post_research_proposal"] == "CATALOG_EXIT_CANDIDATE"]
        self.assertEqual(len(post_exit), 248)

    def test_package_identity_distinguishes_heads(self):
        identity = json.loads((PKG / "00-PACKAGE-IDENTITY.json").read_text(encoding="utf-8"))
        self.assertIn("package_generation_git_head_sha", identity)
        self.assertIn("pr_500_branch_head_at_package_generation", identity)
        self.assertIn("frozen_pr499_semantic_review_csv_sha256", identity)
        self.assertEqual(
            identity["package_generation_git_head_sha"],
            identity["pr_500_branch_head_at_package_generation"],
        )
        self.assertIn("disposition_counts_historical_pr499_anchor", identity)
        self.assertIn("disposition_counts_post_research_effective", identity)

    def test_sha256sums_cover_artifacts(self):
        sums = (PKG / "SHA256SUMS").read_text(encoding="utf-8").strip().splitlines()
        names = {line.split()[-1] for line in sums if line.strip()}
        for name in (
            "05-PROPOSED-DECISION-SHEET-262.csv",
            "08-FAMILY-MEMBERSHIP-COMPLETE-262.csv",
            "01-CRITICAL-20-EVIDENCE-MATRIX.csv",
        ):
            self.assertIn(name, names)
            path = PKG / name
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            line = next(l for l in sums if l.endswith(f"  {name}"))
            self.assertTrue(line.startswith(expected))

    def test_cohort_excludes_154_and_156_oils(self):
        cohort = load_cohort_products(
            BASELINE / "02-PRODUCT-CATEGORY-CENSUS.csv",
            category_census_path=BASELINE / "01-CATEGORY-CENSUS.csv",
        )
        cats = {int(r["category_id"]) for r in cohort}
        self.assertTrue(cats <= {158, 160})

    def test_pr499_domains_only_seven(self):
        with (REVIEW / "01-262-PRODUCT-SEMANTIC-REVIEW.csv").open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                code = row.get("proposed_industrial_domain_code") or ""
                if code:
                    self.assertIn(code, APPROVED_DOMAIN_CODES)

    def test_enrich_row_matches_review_proposal_field(self):
        with (REVIEW / "01-262-PRODUCT-SEMANTIC-REVIEW.csv").open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                e = enrich_row(row)
                self.assertEqual(e["historical_pr499_proposal"], row["proposed_disposition"])


if __name__ == "__main__":
    unittest.main()
