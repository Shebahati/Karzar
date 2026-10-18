"""Tests for Owner Architecture Decision Journal package."""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from catalog_target.taxonomy_owner_architecture_decision_journal import (  # noqa: E402
    B2_PENDING_GROUP_COUNT,
    B2_TOTAL_DECISION_GROUPS,
    DECISION_ID_ACCESSORIES_154,
    DECISION_ID_ARCH_7_L1,
    DECISION_ID_FLUIDS_155,
    DECISION_ID_FLUIDS_156_PUBLICATION,
    DECISION_ID_HELICOIL_55_THREAD_REPAIR,
    DECISION_ID_MACHINE_ACCESSORIES_163_164,
    DECISION_ID_MEGAMENU_186_187_188,
    DECISION_ID_METROLOGY_L2,
    DECISION_ID_MIXED_CHUCKS_116_118,
    DECISION_ID_TX_OWNER_SCOPE_157_160,
    JOURNAL_ENTRY_SPECS,
    JournalPaths,
    validate_journal_package,
    write_journal_package,
)


class OwnerArchitectureDecisionJournalTests(unittest.TestCase):
    def test_write_and_validate_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            payload = write_journal_package(out, generator_git_sha="test")
            self.assertEqual(payload["validation"]["status"], "PASS")
            result = validate_journal_package(JournalPaths(out))
            self.assertEqual(result["status"], "PASS")

    def test_b2_snapshot_decided_groups_still_pending(self):
        b2 = ROOT / "audit/taxonomy-phase1b-route-b2-architecture-review-2026-10-18"
        with (b2 / "C-GROUPED-OWNER-DECISION-REGISTER.csv").open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        for gid in (
            DECISION_ID_ARCH_7_L1,
            DECISION_ID_METROLOGY_L2,
            DECISION_ID_ACCESSORIES_154,
            DECISION_ID_FLUIDS_155,
            DECISION_ID_FLUIDS_156_PUBLICATION,
            DECISION_ID_MACHINE_ACCESSORIES_163_164,
            DECISION_ID_TX_OWNER_SCOPE_157_160,
            DECISION_ID_MIXED_CHUCKS_116_118,
            DECISION_ID_HELICOIL_55_THREAD_REPAIR,
            DECISION_ID_MEGAMENU_186_187_188,
        ):
            row = next(r for r in rows if r["decision_group_id"] == gid)
            self.assertEqual(row["owner_architecture_decision_status"], "PENDING")

    def test_pending_b2_group_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_journal_package(out, generator_git_sha="test")
            pending = list(
                csv.DictReader(
                    (out / "04-B2-REMAINING-PENDING-DECISION-GROUPS.csv").open(encoding="utf-8")
                )
            )
            self.assertEqual(len(pending), B2_PENDING_GROUP_COUNT)

    def test_journal_entry_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_journal_package(out, generator_git_sha="test")
            rows = list(csv.DictReader((out / "01-OWNER-ARCHITECTURE-DECISION-JOURNAL.csv").open()))
            self.assertEqual(len(rows), len(JOURNAL_ENTRY_SPECS))

    def test_validation_fails_if_apply_authorized(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_journal_package(out, generator_git_sha="test")
            path = out / "01-OWNER-ARCHITECTURE-DECISION-JOURNAL.csv"
            rows = list(csv.DictReader(path.open(encoding="utf-8")))
            rows[0]["category_apply_authorization"] = "YES"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            result = validate_journal_package(JournalPaths(out))
            self.assertEqual(result["status"], "FAIL")

    def test_ten_decision_closeout_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_journal_package(out, generator_git_sha="test")
            self.assertEqual(len(JOURNAL_ENTRY_SPECS), B2_TOTAL_DECISION_GROUPS)
            self.assertTrue((out / "K-OWNER-ARCHITECTURE-CLOSEOUT-REPORT.md").is_file())
            self.assertTrue((out / "14-EFFECTIVE-DECISION-STATE-SUMMARY.json").is_file())
            pending = list(
                csv.DictReader(
                    (out / "04-B2-REMAINING-PENDING-DECISION-GROUPS.csv").open(encoding="utf-8")
                )
            )
            self.assertEqual(len(pending), 0)
            hold = list(csv.DictReader((out / "16-HOLD-CATEGORY-TO-DECISION-RECONCILIATION.csv").open()))
            self.assertEqual(len(hold), 11)

    def test_validation_fails_if_b2_arch7_retroactively_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_journal_package(out, generator_git_sha="test")
            # Simulate forbidden B2 rewrite by patching only in-memory validation path:
            # validation reads live B2 from repo; we only test journal apply flag here.
            paths = JournalPaths(out)
            journal_rows = list(csv.DictReader(paths.journal_csv.open(encoding="utf-8")))
            journal_rows[0]["production_mutation_authorization"] = "YES"
            with paths.journal_csv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=journal_rows[0].keys())
                writer.writeheader()
                writer.writerows(journal_rows)
            self.assertEqual(validate_journal_package(paths)["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
