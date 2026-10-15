"""INSIZE #258 hardened apply — extended deterministic coverage."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.insize_commercial_reconcile_258 import (  # noqa: E402
    EXPECTED_ELIGIBLE_ROWS,
    EXPECTED_PRODUCTION_DATABASE,
    FORBIDDEN_MUTATION_COLUMNS,
    LOCKED_PLAN_SHA256,
    LOCKED_ROLLBACK_MANIFEST_SHA256,
    OWNER_SOURCE_SHA256,
    PlanRow,
    StaleGuardResult,
    apply_plan_rows,
    assert_expected_production_database_identity,
    build_mutation_sql,
    compute_expected_post_hash,
    load_apply_journal,
    load_plan_rows,
    production_preflight,
    rollback_plan_rows,
    rollback_post_apply_drift_guard,
    state_hash,
    validate_apply_journal_for_rollback,
    validate_production_source_xlsx,
    verify_post_apply_hashes,
    verify_post_rollback_hashes,
    write_journal_atomic,
)
from catalog_target.sales_wave_apply import ApplyAbort  # noqa: E402

from tests.test_insize_commercial_reconcile_258_apply import (  # noqa: E402
    ApplyTransactionTests,
    FakeConn,
)

EVIDENCE = ROOT / "audit" / "insize-commercial-reconcile-258-2026-10-13"
PLAN = EVIDENCE / "INSIZE_COMMERCIAL_RECONCILE_PLAN.csv"

CANONICAL_IDENTITY = {
    "current_database": "karzar_staging",
    "current_user": "karzar_staging",
    "pg_system_identifier": EXPECTED_PRODUCTION_DATABASE["pg_system_identifier"],
    "postgres_container": "lathe_postgres",
    "expected_live_host": "srv5944957438",
    "live_host_proof": "srv5944957438",
}


def _valid_apply_journal(**overrides: object) -> dict:
    base = {
        "mode": "APPLY",
        "batch_id": "batch-1",
        "COMMITTED": "YES",
        "committed": True,
        "ROWS_WRITTEN": 1,
        "source_sha256": OWNER_SOURCE_SHA256,
        "plan_sha256": LOCKED_PLAN_SHA256,
        "rollback_manifest_sha256": LOCKED_ROLLBACK_MANIFEST_SHA256,
        "database_identity": dict(CANONICAL_IDENTITY),
        "POST_COMMIT_VERIFICATION": "PASS",
        "rows": [
            {
                "product_id": 5,
                "sku": "S5",
                "before_is_available": False,
                "before_base_price": "100",
                "expected_post_hash": "post",
                "expected_current_hash": "pre",
            }
        ],
    }
    base.update(overrides)
    return base


class ProductionPreflightTests(unittest.TestCase):
    def _ok_guard(self, plan_rows):
        return StaleGuardResult(ok=True, expected_count=len(plan_rows), match_count=len(plan_rows), mismatches=[])


    def test_wrong_xlsx_sha_blocked(self):
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp.write(b"not-the-real-workbook")
            path = Path(tmp.name)
        try:
            with self.assertRaises(ApplyAbort) as ctx:
                validate_production_source_xlsx(path)
            self.assertIn("BLOCKED_SOURCE_SHA_MISMATCH", str(ctx.exception))
        finally:
            path.unlink(missing_ok=True)

    @mock.patch("catalog_target.insize_commercial_reconcile_258.fetch_hash_rows_ssh")
    @mock.patch("catalog_target.insize_commercial_reconcile_258.fetch_production_identity_ssh_reference")
    @mock.patch("catalog_target.insize_commercial_reconcile_258.validate_production_source_xlsx")
    @mock.patch("catalog_target.insize_commercial_reconcile_258.stale_hash_guard")
    @mock.patch("catalog_target.insize_commercial_reconcile_258.sha256_file")
    def test_wrong_plan_sha_status(self, sha_mock, guard_mock, _src, id_mock, live_mock):
        plan_rows = load_plan_rows(PLAN)
        guard_mock.return_value = self._ok_guard(plan_rows)
        sha_mock.side_effect = lambda p: "wrong-plan" if "PLAN" in str(p) else LOCKED_ROLLBACK_MANIFEST_SHA256
        id_mock.return_value = CANONICAL_IDENTITY
        live_mock.return_value = {r.product_id: _live_for_plan(r) for r in plan_rows}
        report = production_preflight(
            evidence_dir=EVIDENCE,
            plan_rows=plan_rows,
            source_xlsx=Path("/tmp/x"),
            ssh_host="karzar-vps",
        )
        self.assertEqual(report["STATUS"], "BLOCKED_PLAN_ARTIFACT_MISMATCH")

    @mock.patch("catalog_target.insize_commercial_reconcile_258.fetch_hash_rows_ssh")
    @mock.patch("catalog_target.insize_commercial_reconcile_258.fetch_production_identity_ssh_reference")
    @mock.patch("catalog_target.insize_commercial_reconcile_258.validate_production_source_xlsx")
    @mock.patch("catalog_target.insize_commercial_reconcile_258.stale_hash_guard")
    @mock.patch("catalog_target.insize_commercial_reconcile_258.sha256_file")
    def test_db_identity_mismatch_status(self, sha_mock, guard_mock, _src, id_mock, live_mock):
        plan_rows = load_plan_rows(PLAN)
        guard_mock.return_value = self._ok_guard(plan_rows)
        sha_mock.side_effect = lambda p: LOCKED_PLAN_SHA256 if "PLAN" in str(p) else LOCKED_ROLLBACK_MANIFEST_SHA256
        id_mock.return_value = {**CANONICAL_IDENTITY, "pg_system_identifier": "wrong"}
        live_mock.return_value = {r.product_id: _live_for_plan(r) for r in plan_rows}
        report = production_preflight(
            evidence_dir=EVIDENCE,
            plan_rows=plan_rows,
            source_xlsx=Path("/tmp/x"),
            ssh_host="karzar-vps",
        )
        self.assertEqual(report["STATUS"], "BLOCKED_DATABASE_IDENTITY")
        self.assertEqual(report["DATABASE_IDENTITY_MATCH"], "NO")

    @mock.patch("catalog_target.insize_commercial_reconcile_258.fetch_hash_rows_ssh")
    @mock.patch("catalog_target.insize_commercial_reconcile_258.fetch_production_identity_ssh_reference")
    @mock.patch("catalog_target.insize_commercial_reconcile_258.validate_production_source_xlsx")
    @mock.patch("catalog_target.insize_commercial_reconcile_258.stale_hash_guard")
    @mock.patch("catalog_target.insize_commercial_reconcile_258.sha256_file")
    def test_stale_plan_status(self, sha_mock, guard_mock, _src, id_mock, live_mock):
        plan_rows = load_plan_rows(PLAN)
        sha_mock.side_effect = lambda p: LOCKED_PLAN_SHA256 if "PLAN" in str(p) else LOCKED_ROLLBACK_MANIFEST_SHA256
        id_mock.return_value = CANONICAL_IDENTITY
        live_mock.return_value = {}
        guard_mock.return_value = StaleGuardResult(ok=False, expected_count=len(plan_rows), match_count=0, mismatches=[{"reason": "hash_mismatch"}])
        report = production_preflight(
            evidence_dir=EVIDENCE,
            plan_rows=plan_rows,
            source_xlsx=Path("/tmp/x"),
            ssh_host="karzar-vps",
        )
        self.assertEqual(report["STATUS"], "BLOCKED_STALE_PLAN")

    @mock.patch("catalog_target.insize_commercial_reconcile_258.fetch_hash_rows_ssh")
    @mock.patch("catalog_target.insize_commercial_reconcile_258.fetch_production_identity_ssh_reference")
    @mock.patch("catalog_target.insize_commercial_reconcile_258.validate_production_source_xlsx")
    @mock.patch("catalog_target.insize_commercial_reconcile_258.stale_hash_guard")
    @mock.patch("catalog_target.insize_commercial_reconcile_258.sha256_file")
    def test_ready_status(self, sha_mock, guard_mock, _src, id_mock, live_mock):
        plan_rows = load_plan_rows(PLAN)
        guard_mock.return_value = self._ok_guard(plan_rows)
        sha_mock.side_effect = lambda p: LOCKED_PLAN_SHA256 if "PLAN" in str(p) else LOCKED_ROLLBACK_MANIFEST_SHA256
        id_mock.return_value = CANONICAL_IDENTITY
        live_mock.return_value = {r.product_id: _live_for_plan(r) for r in plan_rows}
        report = production_preflight(
            evidence_dir=EVIDENCE,
            plan_rows=plan_rows,
            source_xlsx=Path("/tmp/x"),
            ssh_host="karzar-vps",
        )
        self.assertEqual(report["STATUS"], "READY")
        self.assertEqual(report.get("SOURCE_FILE_PRESENT", "YES"), "YES")


def _live_for_plan(plan: PlanRow, *, drift: bool = False) -> dict[str, str]:
    row = {
        "product_id": str(plan.product_id),
        "sku": plan.sku,
        "brand_id": "1",
        "is_active": "true",
        "is_available": str(plan.current_is_available).lower(),
        "base_price": str(plan.current_base_price or ""),
        "deleted_at": "",
        "image_present": "true",
    }
    if drift:
        row["base_price"] = "999999"
    return row


class DatabaseFingerprintTests(unittest.TestCase):
    def test_wrong_fingerprint_blocked(self):
        with self.assertRaises(ApplyAbort):
            assert_expected_production_database_identity(
                {**CANONICAL_IDENTITY, "pg_system_identifier": "1"}
            )

    def test_correct_fingerprint_passes(self):
        assert_expected_production_database_identity(CANONICAL_IDENTITY)

    def test_url_must_match_ssh_reference(self):
        url_id = {**CANONICAL_IDENTITY, "pg_system_identifier": "other"}
        ssh_ref = CANONICAL_IDENTITY
        with self.assertRaises(ApplyAbort):
            assert_expected_production_database_identity(url_id, ssh_reference=ssh_ref)


class ApplyJournalBindingTests(unittest.TestCase):
    def test_missing_journal_file(self):
        with self.assertRaises(ApplyAbort):
            load_apply_journal(Path(tempfile.mkdtemp()), "missing")

    def _validate(self, journal: dict, **kwargs: object) -> None:
        validate_apply_journal_for_rollback(
            journal,
            batch_id=str(kwargs.get("batch_id", journal.get("batch_id"))),
            source_sha256=OWNER_SOURCE_SHA256,
            plan_sha256=LOCKED_PLAN_SHA256,
            rollback_manifest_sha256=LOCKED_ROLLBACK_MANIFEST_SHA256,
            database_identity=CANONICAL_IDENTITY,
            expected_rows=int(kwargs.get("expected_rows", 1)),
        )

    def test_valid_journal_accepted(self):
        self._validate(_valid_apply_journal())

    def test_wrong_batch_blocked(self):
        with self.assertRaises(ApplyAbort):
            self._validate(_valid_apply_journal(), batch_id="other")

    def test_committed_no_blocked(self):
        with self.assertRaises(ApplyAbort):
            self._validate(_valid_apply_journal(COMMITTED="NO", committed=False))

    def test_post_verify_fail_blocked(self):
        with self.assertRaises(ApplyAbort):
            self._validate(_valid_apply_journal(POST_COMMIT_VERIFICATION="FAIL"))


class PostCommitVerificationTests(unittest.TestCase):
    def test_pass_all_hashes(self):
        plan = ApplyTransactionTests()._mini_plan()[0]
        live = _live_for_plan(plan)
        post = compute_expected_post_hash(live, plan)
        live_after = dict(live)
        live_after["base_price"] = ""
        report = verify_post_apply_hashes(
            {plan.product_id: live_after},
            [{"product_id": plan.product_id, "expected_post_hash": post}],
        )
        self.assertEqual(report["POST_COMMIT_VERIFICATION"], "PASS")

    def test_one_mismatch_fails(self):
        report = verify_post_apply_hashes(
            {1: _live_for_plan(ApplyTransactionTests()._mini_plan()[0])},
            [{"product_id": 1, "expected_post_hash": "dead"}],
        )
        self.assertEqual(report["POST_COMMIT_VERIFICATION"], "FAIL")


class RollbackDriftTests(unittest.TestCase):
    def _row(self, live: dict[str, str], expected_post: str) -> dict:
        return {"product_id": int(live["product_id"]), "expected_post_hash": expected_post}

    def test_exact_post_hash_allowed(self):
        live = _live_for_plan(ApplyTransactionTests()._mini_plan()[0])
        h = state_hash(live)
        guard = rollback_post_apply_drift_guard([self._row(live, h)], {int(live["product_id"]): live})
        self.assertTrue(guard.ok)

    def test_brand_drift_blocked(self):
        live = _live_for_plan(ApplyTransactionTests()._mini_plan()[0])
        h = state_hash(live)
        drifted = dict(live)
        drifted["brand_id"] = "999"
        guard = rollback_post_apply_drift_guard([self._row(live, h)], {int(live["product_id"]): drifted})
        self.assertFalse(guard.ok)


class ForbiddenColumnTests(unittest.TestCase):
    def test_apply_sql_never_sets_forbidden_columns(self):
        plan = PlanRow(
            product_id=1,
            sku="A",
            combined_action="SET_AVAILABLE_AND_PRICE",
            availability_action="SET_AVAILABLE",
            price_action="SET_PRICE",
            expected_current_hash="x",
            proposed_is_available=True,
            proposed_base_price=Decimal("10"),
            current_is_available=False,
            current_base_price=Decimal("5"),
        )
        sql, _ = build_mutation_sql(
            plan,
            prop_avail=True,
            prop_price=Decimal("10"),
            before_avail=False,
            before_price=Decimal("5"),
        )
        set_clause = sql.lower().split(" set ", 1)[1].split(" where ", 1)[0]
        for col in FORBIDDEN_MUTATION_COLUMNS:
            self.assertNotIn(f"{col} =", set_clause)


class JournalDurabilityTests(unittest.TestCase):
    def test_write_journal_atomic_creates_file(self):
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "j.json"
        write_journal_atomic(path, {"COMMITTED": "NO", "journal_phase": "PRE_COMMIT"})
        self.assertTrue(path.is_file())
        payload = json.loads(path.read_text())
        self.assertEqual(payload["journal_phase"], "PRE_COMMIT")


class PostRollbackVerificationTests(unittest.TestCase):
    def test_restored_pre_hash_pass(self):
        live = _live_for_plan(ApplyTransactionTests()._mini_plan()[0])
        pre = state_hash(live)
        report = verify_post_rollback_hashes(
            {int(live["product_id"]): live},
            [{"product_id": int(live["product_id"]), "expected_current_hash": pre}],
        )
        self.assertEqual(report["POST_ROLLBACK_VERIFICATION"], "PASS")




class ApplyJournalMetadataTests(unittest.TestCase):
    def test_journal_rows_include_post_hash_and_shas(self):
        plan = ApplyTransactionTests()._mini_plan()
        live_row = {
            "product_id": "10",
            "sku": "S10",
            "brand_id": "1",
            "is_active": "true",
            "is_available": "true",
            "base_price": "5000",
            "deleted_at": "",
            "image_present": "true",
        }
        conn = FakeConn({10: dict(live_row)})
        meta = {
            "started_at": "t",
            "source_sha256": OWNER_SOURCE_SHA256,
            "plan_sha256": LOCKED_PLAN_SHA256,
            "rollback_manifest_sha256": LOCKED_ROLLBACK_MANIFEST_SHA256,
            "database_identity": CANONICAL_IDENTITY,
        }
        result = apply_plan_rows(
            conn,
            plan,
            dry_run=False,
            batch_id="meta-test",
            metadata=meta,
            journal_dir=Path(tempfile.mkdtemp()),
        )
        row = result.journal["rows"][0]
        self.assertTrue(row["expected_post_hash"])
        self.assertEqual(result.journal["source_sha256"], OWNER_SOURCE_SHA256)
        self.assertEqual(result.journal["database_identity"]["pg_system_identifier"], CANONICAL_IDENTITY["pg_system_identifier"])


class RollbackAcceptanceTests(unittest.TestCase):
    def test_valid_post_hash_allows_rollback(self):
        plan = ApplyTransactionTests()._mini_plan()[0]
        live = _live_for_plan(plan)
        post = compute_expected_post_hash(live, plan)
        live_post = dict(live)
        live_post["base_price"] = ""
        journal = _valid_apply_journal(
            rows=[
                {
                    "product_id": plan.product_id,
                    "sku": plan.sku,
                    "before_is_available": True,
                    "before_base_price": "5000",
                    "expected_post_hash": post,
                    "expected_current_hash": state_hash(live),
                }
            ]
        )
        conn = FakeConn({plan.product_id: live_post})
        result = rollback_plan_rows(
            conn,
            apply_journal=journal,
            batch_id="batch-1",
            metadata={"started_at": "t"},
            journal_dir=Path(tempfile.mkdtemp()),
        )
        self.assertTrue(result.committed)


class ApplyJournalBindingExtraTests(unittest.TestCase):
    def test_wrong_rows_written_blocked(self):
        with self.assertRaises(ApplyAbort):
            validate_apply_journal_for_rollback(
                _valid_apply_journal(ROWS_WRITTEN=EXPECTED_ELIGIBLE_ROWS),
                batch_id="batch-1",
                source_sha256=OWNER_SOURCE_SHA256,
                plan_sha256=LOCKED_PLAN_SHA256,
                rollback_manifest_sha256=LOCKED_ROLLBACK_MANIFEST_SHA256,
                database_identity=CANONICAL_IDENTITY,
                expected_rows=1,
            )

if __name__ == "__main__":
    unittest.main()
