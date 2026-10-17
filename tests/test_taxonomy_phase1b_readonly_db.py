"""Regression tests for Phase 1B read-only PostgreSQL helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from catalog_target.taxonomy_phase1b_readonly_db import (  # noqa: E402
    parse_pipe_rows,
    read_only_transaction_proof,
    run_readonly_scalar,
    run_readonly_sql,
    verify_production_database_identity,
)


def _mock_psql(stdout: str, returncode: int = 0):
    return mock.Mock(returncode=returncode, stdout=stdout, stderr="")


class TaxonomyPhase1bReadonlyDbTests(unittest.TestCase):
    def test_scalar_select_ignores_rollback_noise(self):
        with mock.patch(
            "catalog_target.taxonomy_phase1b_readonly_db._docker_psql_exec",
        ) as exec_mock:
            exec_mock.return_value = _mock_psql("karzar_staging\nROLLBACK\n")
            value = run_readonly_scalar("vps", "SELECT current_database()")
        self.assertEqual(value, "karzar_staging")

    def test_scalar_rejects_multiple_data_lines(self):
        with mock.patch(
            "catalog_target.taxonomy_phase1b_readonly_db._docker_psql_exec",
        ) as exec_mock:
            exec_mock.return_value = _mock_psql("one\ntwo\n")
            with self.assertRaises(RuntimeError):
                run_readonly_scalar("vps", "SELECT 1")

    def test_category_export_pipe_parsing(self):
        raw = "1|L1|slug||f|f||\n2|Child|child-slug|1|f|f||\n"
        rows = parse_pipe_rows(raw, min_fields=8)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], "1")

    def test_megamenu_export_pipe_parsing(self):
        raw = "10|helicoil|Helicoil|1|t|f|{186,187,188}\n"
        rows = parse_pipe_rows(raw, min_fields=7)
        self.assertEqual(rows[0][1], "helicoil")

    def test_transaction_proof_accepts_on_only(self):
        with mock.patch(
            "catalog_target.taxonomy_phase1b_readonly_db.run_readonly_scalar",
            return_value="on",
        ):
            proof = read_only_transaction_proof("vps")
        self.assertEqual(proof["transaction_read_only"], "on")

    def test_transaction_proof_rejects_off(self):
        with mock.patch(
            "catalog_target.taxonomy_phase1b_readonly_db.run_readonly_scalar",
            return_value="off",
        ):
            with self.assertRaises(RuntimeError):
                read_only_transaction_proof("vps")

    def test_transaction_proof_rejects_malformed(self):
        with mock.patch(
            "catalog_target.taxonomy_phase1b_readonly_db.run_readonly_scalar",
            return_value="on extra",
        ):
            with self.assertRaises(RuntimeError):
                read_only_transaction_proof("vps")

    def test_begin_bypass_rejected(self):
        with self.assertRaises(RuntimeError):
            run_readonly_sql("vps", "BEGIN; SELECT 1")

    def test_readonly_sql_wraps_transaction_and_pset(self):
        with mock.patch(
            "catalog_target.taxonomy_phase1b_readonly_db._docker_psql_exec",
        ) as exec_mock:
            exec_mock.return_value = _mock_psql("ok\n")
            run_readonly_sql("vps", "SELECT 1")
            heredoc = exec_mock.call_args[0][1]
            self.assertIn("SET TRANSACTION READ ONLY", heredoc)
            self.assertIn("ROLLBACK", heredoc)
            self.assertIn("\\pset tuples_only on", heredoc)
            self.assertIn("\\pset fieldsep '|'", heredoc)

    def test_verify_production_identity_exact_values(self):
        scalars = iter(
            [
                "karzar_staging",
                "karzar_staging",
                "7664189378775347234",
                "on",
            ]
        )

        def fake_scalar(_host, _sql):
            return next(scalars)

        with mock.patch(
            "catalog_target.taxonomy_phase1b_readonly_db.run_readonly_scalar",
            side_effect=fake_scalar,
        ):
            identity = verify_production_database_identity("vps")
        self.assertEqual(identity["pg_system_identifier"], "7664189378775347234")
        self.assertEqual(identity["transaction_read_only"], "on")


if __name__ == "__main__":
    unittest.main()
