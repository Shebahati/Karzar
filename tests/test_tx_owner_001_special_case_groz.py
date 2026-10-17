"""Tests for TX-OWNER-001 Groz special-case evidence package."""

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

from catalog_target.tx_owner_001_external_sources import APPROVED_DOMAIN_CODES  # noqa: E402
from catalog_target.tx_owner_001_groz_special_case_research import (  # noqa: E402
    SPECIAL_CASE_PRODUCTS,
)

PKG = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-special-case-groz-2026-10-17"
BATCH_001 = (
    ROOT
    / "audit"
    / "taxonomy-phase1b-tx-owner-001-owner-decision-package"
    / "OWNER-AUTHORIZATION-BATCH-001-2026-10-17.csv"
)
BATCH_002 = (
    ROOT
    / "audit"
    / "taxonomy-phase1b-tx-owner-001-owner-decision-package"
    / "OWNER-AUTHORIZATION-BATCH-002-2026-10-17.csv"
)


class TxOwner001SpecialCaseGrozTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not (PKG / "01-SPECIAL-CASE-EVIDENCE-MATRIX.csv").is_file():
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "audit_tx_owner_001_special_case_groz.py")],
                cwd=ROOT,
                check=True,
            )

    def test_matrix_two_products(self):
        with (PKG / "01-SPECIAL-CASE-EVIDENCE-MATRIX.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 2)
        ids = {int(r["product_id"]) for r in rows}
        self.assertEqual(ids, {2915, 3238})

    def test_owner_fields_pending(self):
        with (PKG / "01-SPECIAL-CASE-EVIDENCE-MATRIX.csv").open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                self.assertEqual(row["owner_decision"], "")
                self.assertEqual(row["authorization_status"], "PENDING")

    def test_pr499_historical_preserved(self):
        with (PKG / "01-SPECIAL-CASE-EVIDENCE-MATRIX.csv").open(encoding="utf-8", newline="") as handle:
            by_id = {r["product_id"]: r for r in csv.DictReader(handle)}
        self.assertEqual(by_id["2915"]["historical_pr499_proposal"], "INDUSTRIAL_EXCEPTION_CANDIDATE")
        self.assertEqual(by_id["3238"]["historical_pr499_proposal"], "OWNER_DECISION_REQUIRED")

    def test_domains_in_approved_set(self):
        for pid, spec in SPECIAL_CASE_PRODUCTS.items():
            domain = spec["proposed_industrial_domain"]
            self.assertIn(domain, APPROVED_DOMAIN_CODES, msg=f"pid={pid}")

    def test_oem_sources_linked_per_product(self):
        with (PKG / "01-SPECIAL-CASE-EVIDENCE-MATRIX.csv").open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                self.assertTrue(row["oem_source_ids"])
                self.assertTrue(row["oem_source_urls"])
                self.assertIn("groz-tools.com", row["oem_source_urls"])

    def test_2915_has_cutting_and_wood_competing_sources(self):
        with (PKG / "02-OEM-SOURCE-REGISTER.csv").open(encoding="utf-8", newline="") as handle:
            ids = {r["source_id"] for r in csv.DictReader(handle) if "2915" in r["related_karzar_product_ids"]}
        self.assertIn("GROZ-OEM-COB-CUTOFF", ids)
        self.assertIn("GROZ-OEM-WW-PLANE", ids)

    def test_3238_machinist_jack_source(self):
        with (PKG / "02-OEM-SOURCE-REGISTER.csv").open(encoding="utf-8", newline="") as handle:
            rows = [r for r in csv.DictReader(handle) if "3238" in r["related_karzar_product_ids"]]
        self.assertTrue(any(r["source_id"] == "GROZ-OEM-MJ-MACHINIST-JACK" for r in rows))

    def test_owner_batches_not_in_matrix(self):
        for batch in (BATCH_001, BATCH_002):
            with batch.open(encoding="utf-8", newline="") as handle:
                pids = {r.get("product_id") for r in csv.DictReader(handle)}
            self.assertNotIn("2915", pids)
            self.assertNotIn("3238", pids)

    def test_identity_safety_flags(self):
        identity = json.loads((PKG / "00-PACKAGE-IDENTITY.json").read_text(encoding="utf-8"))
        self.assertEqual(identity["safety"]["PRODUCTION_MUTATION"], "NO")
        self.assertEqual(identity["safety"]["OWNER_BATCH_JOURNALS_TOUCHED"], "NO")
        self.assertFalse(identity["owner_batches_mutated"])

    def test_sha256sums(self):
        sums = (PKG / "SHA256SUMS").read_text(encoding="utf-8").strip().splitlines()
        self.assertTrue(any(line.endswith("  01-SPECIAL-CASE-EVIDENCE-MATRIX.csv") for line in sums))


if __name__ == "__main__":
    unittest.main()
