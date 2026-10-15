"""Guarded INSIZE #258 commercial APPLY tests (no production mutation)."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from apply_insize_commercial_reconcile_258 import main as apply_main  # noqa: E402, I001
from catalog_target.insize_commercial_reconcile_258 import (  # noqa: E402, I001
    LOCKED_PLAN_SHA256,
    LOCKED_ROLLBACK_MANIFEST_SHA256,
    OWNER_AUTH_APPLY,
    OWNER_AUTH_ROLLBACK,
    OWNER_SOURCE_SHA256,
    PlanRow,
    apply_plan_rows,
    assert_apply_authorization_gates,
    classify_owner_freshness,
    load_plan_rows,
    proposed_values_for_row,
    rollback_plan_rows,
    build_mutation_sql,
    compute_expected_post_hash,
    plan_mutates_price,
    state_hash,
    validate_production_source_xlsx,
    assert_expected_production_database_identity,
    write_journal_atomic,
    stale_hash_guard,
)
from catalog_target.sales_wave_apply import ApplyAbort  # noqa: E402, I001

EVIDENCE = ROOT / "audit" / "insize-commercial-reconcile-258-2026-10-13"
PLAN = EVIDENCE / "INSIZE_COMMERCIAL_RECONCILE_PLAN.csv"


class FakeCursor:
    def __init__(self, store: dict[int, dict[str, str]], *, fail_on_pid: int | None = None):
        self.store = store
        self.fail_on_pid = fail_on_pid
        self.rowcount = 0
        self._rows: list[tuple] = []
        self.executed: list[tuple] = []

    def execute(self, sql: str, params=None) -> None:  # noqa: ANN001
        self.executed.append((sql, params))
        sql_l = " ".join(sql.lower().split())
        if sql_l.startswith("select "):
            ids = list(params[0])
            self._rows = []
            for pid in sorted(ids):
                row = self.store.get(pid)
                if row is None:
                    continue
                self._rows.append(
                    (
                        int(row["product_id"]),
                        row["sku"],
                        row.get("brand_id") or None,
                        row.get("is_active") in {"true", "t", "1"},
                        row.get("is_available") in {"true", "t", "1"},
                        Decimal(row["base_price"]) if row.get("base_price") else None,
                        None,
                        row.get("image_present", "false"),
                    )
                )
            self.rowcount = len(self._rows)
            return
        if sql_l.startswith("update "):
            set_part = sql_l.split(" set ", 1)[1].split(" where ", 1)[0]
            mutates_price = "base_price" in set_part
            mutates_avail = "is_available" in set_part
            idx = 0
            new_price = None
            new_avail = None
            if mutates_price:
                new_price = params[idx]
                idx += 1
            if mutates_avail:
                new_avail = params[idx]
                idx += 1
            pid, sku = params[idx], params[idx + 1]
            if self.fail_on_pid == int(pid):
                self.rowcount = 0
                return
            live = self.store.get(int(pid))
            if live is None or live["sku"] != sku:
                self.rowcount = 0
                return
            live = dict(live)
            if new_avail is not None:
                live["is_available"] = "true" if new_avail else "false"
            if new_price is not None or mutates_price:
                live["base_price"] = "" if new_price is None else str(new_price)
            self.store[int(pid)] = live
            self.rowcount = 1
            return
        raise AssertionError(sql)

    def fetchall(self):
        return list(self._rows)


class FakeConn:
    def __init__(self, store: dict[int, dict[str, str]], *, fail_on_pid: int | None = None):
        self.store = store
        self.fail_on_pid = fail_on_pid
        self.committed = False
        self.rolled_back = False
        self._snap: dict[int, dict[str, str]] | None = None

    def cursor(self, *args, **kwargs):  # noqa: ANN002, ANN003
        if self._snap is None:
            self._snap = {k: dict(v) for k, v in self.store.items()}
        return FakeCursor(self.store, fail_on_pid=self.fail_on_pid)

    def commit(self) -> None:
        self.committed = True
        self._snap = {k: dict(v) for k, v in self.store.items()}

    def rollback(self) -> None:
        self.rolled_back = True
        if self._snap is not None:
            self.store.clear()
            self.store.update({k: dict(v) for k, v in self._snap.items()})


class HashTests(unittest.TestCase):
    def test_state_hash_fixture(self):
        row = {
            "product_id": "1",
            "sku": "ABC",
            "brand_id": "3",
            "is_active": "true",
            "is_available": "false",
            "base_price": "1000",
            "deleted_at": "",
            "image_present": "true",
        }
        h1 = state_hash(row)
        h2 = state_hash(dict(row))
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)


class FreshnessTests(unittest.TestCase):
    def test_freshness_ages_with_time(self):
        manifest = {
            "inspected_at": "2026-10-13T20:46:18Z",
            "freshness_basis": "OWNER_CONFIRMED_RECENCY",
        }
        at = datetime(2026, 10, 13, 20, 46, 18, tzinfo=UTC)
        age_now, cls = classify_owner_freshness(manifest, now=at + timedelta(days=0))
        self.assertEqual(age_now, 7)
        self.assertIn(cls, {"CURRENT_ENOUGH", "AGING_BUT_USABLE"})
        age_stale, cls_stale = classify_owner_freshness(
            manifest, now=at + timedelta(days=60)
        )
        self.assertGreater(age_stale, 45)
        self.assertEqual(cls_stale, "STALE")


class GateTests(unittest.TestCase):
    def test_apply_without_owner_token_aborts(self):
        with self.assertRaises(ApplyAbort):
            assert_apply_authorization_gates(
                apply=True,
                rollback=False,
                confirm_production_write=True,
                confirm_source_sha256=OWNER_SOURCE_SHA256,
                confirm_plan_sha256=LOCKED_PLAN_SHA256,
                confirm_mutation_count=711,
                owner_authorization="WRONG",
                plan_sha256=LOCKED_PLAN_SHA256,
                eligible_count=711,
            )

    def test_cli_apply_without_confirmations_aborts(self):
        with self.assertRaises(ApplyAbort):
            apply_main(["--apply"])




def _locked_sha_side_effect(path: Path) -> str:
    name = path.name.upper()
    if "PLAN" in name:
        return LOCKED_PLAN_SHA256
    if "ROLLBACK" in name:
        return LOCKED_ROLLBACK_MANIFEST_SHA256
    return "00"


def _apply_write_argv(**overrides: str) -> list[str]:
    argv = [
        "--apply",
        "--confirm-production-write",
        f"--confirm-source-sha256={OWNER_SOURCE_SHA256}",
        f"--confirm-plan-sha256={LOCKED_PLAN_SHA256}",
        "--confirm-mutation-count=711",
        f"--owner-authorization={OWNER_AUTH_APPLY}",
        "--database-url=postgresql://karzar_staging:secret@127.0.0.1:5432/karzar_staging",
    ]
    for key, value in overrides.items():
        flag = f"--{key.replace('_', '-')}"
        argv = [a for a in argv if not a.startswith(flag + "=") and a != flag]
        argv.extend([flag, value])
    return argv


def _rollback_write_argv(**overrides: str) -> list[str]:
    argv = [
        "--rollback",
        "--confirm-production-write",
        f"--confirm-rollback-manifest-sha256={LOCKED_ROLLBACK_MANIFEST_SHA256}",
        "--confirm-batch-id=batch-1",
        f"--owner-authorization={OWNER_AUTH_ROLLBACK}",
        "--database-url=postgresql://karzar_staging:secret@127.0.0.1:5432/karzar_staging",
    ]
    for key, value in overrides.items():
        flag = f"--{key.replace('_', '-')}"
        argv = [a for a in argv if not a.startswith(flag + "=") and a != flag]
        argv.extend([flag, value])
    return argv


_PRODUCTION_WRITE_ENV = {
    "KARZAR_ALLOW_PRODUCTION_WRITE": "1",
    "KARZAR_INGESTION_CATEGORY": "B",
}


class LockedArtifactWritePathTests(unittest.TestCase):
    @mock.patch("apply_insize_commercial_reconcile_258.connect_runtime_db")
    @mock.patch("apply_insize_commercial_reconcile_258.resolve_production_database_identity")
    @mock.patch("apply_insize_commercial_reconcile_258.validate_production_source_xlsx")
    @mock.patch("apply_insize_commercial_reconcile_258.sha256_file")
    def test_apply_wrong_plan_sha_blocks_before_db(
        self, sha_mock, _src_mock, resolve_mock, conn_mock
    ):
        def side_effect(path: Path) -> str:
            if "PLAN" in path.name.upper():
                return "deadbeef"
            return LOCKED_ROLLBACK_MANIFEST_SHA256

        sha_mock.side_effect = side_effect
        with mock.patch.dict(os.environ, _PRODUCTION_WRITE_ENV, clear=False):
            with self.assertRaises(ApplyAbort) as ctx:
                apply_main(_apply_write_argv())
        self.assertIn("BLOCKED_LOCKED_PLAN_SHA_MISMATCH", str(ctx.exception))
        resolve_mock.assert_not_called()
        conn_mock.assert_not_called()

    @mock.patch("apply_insize_commercial_reconcile_258.connect_runtime_db")
    @mock.patch("apply_insize_commercial_reconcile_258.resolve_production_database_identity")
    @mock.patch("apply_insize_commercial_reconcile_258.validate_production_source_xlsx")
    @mock.patch("apply_insize_commercial_reconcile_258.sha256_file")
    def test_apply_wrong_rollback_sha_blocks_before_db(
        self, sha_mock, _src_mock, resolve_mock, conn_mock
    ):
        def side_effect(path: Path) -> str:
            if "ROLLBACK" in path.name.upper():
                return "deadbeef"
            return LOCKED_PLAN_SHA256

        sha_mock.side_effect = side_effect
        with mock.patch.dict(os.environ, _PRODUCTION_WRITE_ENV, clear=False):
            with self.assertRaises(ApplyAbort) as ctx:
                apply_main(_apply_write_argv())
        self.assertIn("BLOCKED_LOCKED_ROLLBACK_SHA_MISMATCH", str(ctx.exception))
        resolve_mock.assert_not_called()
        conn_mock.assert_not_called()

    @mock.patch("apply_insize_commercial_reconcile_258.connect_runtime_db")
    @mock.patch("apply_insize_commercial_reconcile_258.resolve_production_database_identity")
    @mock.patch("apply_insize_commercial_reconcile_258.validate_production_source_xlsx")
    @mock.patch("apply_insize_commercial_reconcile_258.load_plan_rows")
    @mock.patch("apply_insize_commercial_reconcile_258.sha256_file")
    @mock.patch("apply_insize_commercial_reconcile_258.assert_plan_matches_evidence")
    def test_apply_wrong_eligible_count_blocks_before_db(
        self, evidence_mock, sha_mock, load_mock, _src_mock, resolve_mock, conn_mock
    ):
        evidence_mock.return_value = {}
        sha_mock.side_effect = _locked_sha_side_effect
        load_mock.return_value = load_plan_rows(PLAN)[:710]
        with mock.patch.dict(os.environ, _PRODUCTION_WRITE_ENV, clear=False):
            with self.assertRaises(ApplyAbort) as ctx:
                apply_main(_apply_write_argv())
        self.assertIn("BLOCKED_LOCKED_ELIGIBLE_COUNT_MISMATCH", str(ctx.exception))
        resolve_mock.assert_not_called()
        conn_mock.assert_not_called()

    @mock.patch("apply_insize_commercial_reconcile_258.connect_runtime_db")
    @mock.patch("apply_insize_commercial_reconcile_258.resolve_production_database_identity")
    @mock.patch("apply_insize_commercial_reconcile_258.validate_production_source_xlsx")
    @mock.patch("apply_insize_commercial_reconcile_258.sha256_file")
    def test_apply_confirm_matching_altered_plan_still_blocked(
        self, sha_mock, _src_mock, resolve_mock, conn_mock
    ):
        altered = "a" * 64

        def side_effect(path: Path) -> str:
            if "PLAN" in path.name.upper():
                return altered
            return LOCKED_ROLLBACK_MANIFEST_SHA256

        sha_mock.side_effect = side_effect
        with mock.patch.dict(os.environ, _PRODUCTION_WRITE_ENV, clear=False):
            with self.assertRaises(ApplyAbort) as ctx:
                apply_main(_apply_write_argv(confirm_plan_sha256=altered))
        self.assertIn("BLOCKED_LOCKED_PLAN_SHA_MISMATCH", str(ctx.exception))
        resolve_mock.assert_not_called()
        conn_mock.assert_not_called()

    @mock.patch("apply_insize_commercial_reconcile_258.apply_plan_rows")
    @mock.patch("apply_insize_commercial_reconcile_258.connect_runtime_db")
    @mock.patch("apply_insize_commercial_reconcile_258.resolve_production_database_identity")
    @mock.patch("apply_insize_commercial_reconcile_258.assert_production_apply_authorized")
    @mock.patch("apply_insize_commercial_reconcile_258.validate_production_source_xlsx")
    @mock.patch("apply_insize_commercial_reconcile_258.sha256_file")
    def test_apply_locked_artifacts_reach_db_layer(
        self,
        sha_mock,
        _src_mock,
        _prod_auth_mock,
        resolve_mock,
        conn_mock,
        apply_rows_mock,
    ):
        sha_mock.side_effect = _locked_sha_side_effect
        resolve_mock.return_value = {"current_database": "karzar_staging", "pg_system_identifier": "1"}
        conn_mock.return_value = mock.Mock()
        apply_rows_mock.return_value = mock.Mock(committed=True, journal={}, aborted_reason=None)
        with mock.patch.dict(os.environ, _PRODUCTION_WRITE_ENV, clear=False):
            rc = apply_main(_apply_write_argv())
        self.assertEqual(rc, 0)
        resolve_mock.assert_called_once()
        conn_mock.assert_called_once()

    @mock.patch("apply_insize_commercial_reconcile_258.connect_runtime_db")
    @mock.patch("apply_insize_commercial_reconcile_258.load_apply_journal")
    @mock.patch("apply_insize_commercial_reconcile_258.resolve_production_database_identity")
    @mock.patch("apply_insize_commercial_reconcile_258.validate_production_source_xlsx")
    @mock.patch("apply_insize_commercial_reconcile_258.sha256_file")
    def test_rollback_altered_plan_blocks_before_db(
        self, sha_mock, _src_mock, resolve_mock, _load_mock, conn_mock
    ):
        def side_effect(path: Path) -> str:
            if "PLAN" in path.name.upper():
                return "deadbeef"
            return LOCKED_ROLLBACK_MANIFEST_SHA256

        sha_mock.side_effect = side_effect
        with mock.patch.dict(os.environ, _PRODUCTION_WRITE_ENV, clear=False):
            with self.assertRaises(ApplyAbort) as ctx:
                apply_main(_rollback_write_argv())
        self.assertIn("BLOCKED_LOCKED_PLAN_SHA_MISMATCH", str(ctx.exception))
        resolve_mock.assert_not_called()
        conn_mock.assert_not_called()

    @mock.patch("apply_insize_commercial_reconcile_258.connect_runtime_db")
    @mock.patch("apply_insize_commercial_reconcile_258.resolve_production_database_identity")
    @mock.patch("apply_insize_commercial_reconcile_258.validate_production_source_xlsx")
    @mock.patch("apply_insize_commercial_reconcile_258.sha256_file")
    def test_rollback_altered_manifest_blocks_before_db(
        self, sha_mock, _src_mock, resolve_mock, conn_mock
    ):
        def side_effect(path: Path) -> str:
            if "ROLLBACK" in path.name.upper():
                return "deadbeef"
            return LOCKED_PLAN_SHA256

        sha_mock.side_effect = side_effect
        with mock.patch.dict(os.environ, _PRODUCTION_WRITE_ENV, clear=False):
            with self.assertRaises(ApplyAbort) as ctx:
                apply_main(_rollback_write_argv())
        self.assertIn("BLOCKED_LOCKED_ROLLBACK_SHA_MISMATCH", str(ctx.exception))
        resolve_mock.assert_not_called()
        conn_mock.assert_not_called()

    @mock.patch("apply_insize_commercial_reconcile_258.connect_runtime_db")
    @mock.patch("apply_insize_commercial_reconcile_258.resolve_production_database_identity")
    @mock.patch("apply_insize_commercial_reconcile_258.validate_production_source_xlsx")
    @mock.patch("apply_insize_commercial_reconcile_258.load_plan_rows")
    @mock.patch("apply_insize_commercial_reconcile_258.sha256_file")
    @mock.patch("apply_insize_commercial_reconcile_258.assert_plan_matches_evidence")
    def test_rollback_wrong_eligible_count_blocks_before_db(
        self, evidence_mock, sha_mock, load_mock, _src_mock, resolve_mock, conn_mock
    ):
        evidence_mock.return_value = {}
        sha_mock.side_effect = _locked_sha_side_effect
        load_mock.return_value = load_plan_rows(PLAN)[:710]
        with mock.patch.dict(os.environ, _PRODUCTION_WRITE_ENV, clear=False):
            with self.assertRaises(ApplyAbort) as ctx:
                apply_main(_rollback_write_argv())
        self.assertIn("BLOCKED_LOCKED_ELIGIBLE_COUNT_MISMATCH", str(ctx.exception))
        resolve_mock.assert_not_called()
        conn_mock.assert_not_called()

    @mock.patch("apply_insize_commercial_reconcile_258.connect_runtime_db")
    @mock.patch("apply_insize_commercial_reconcile_258.resolve_production_database_identity")
    @mock.patch("apply_insize_commercial_reconcile_258.validate_production_source_xlsx")
    @mock.patch("apply_insize_commercial_reconcile_258.sha256_file")
    def test_rollback_confirm_matching_altered_manifest_still_blocked(
        self, sha_mock, _src_mock, resolve_mock, conn_mock
    ):
        altered = "b" * 64

        def side_effect(path: Path) -> str:
            if "ROLLBACK" in path.name.upper():
                return altered
            return LOCKED_PLAN_SHA256

        sha_mock.side_effect = side_effect
        with mock.patch.dict(os.environ, _PRODUCTION_WRITE_ENV, clear=False):
            with self.assertRaises(ApplyAbort) as ctx:
                apply_main(_rollback_write_argv(confirm_rollback_manifest_sha256=altered))
        self.assertIn("BLOCKED_LOCKED_ROLLBACK_SHA_MISMATCH", str(ctx.exception))
        resolve_mock.assert_not_called()
        conn_mock.assert_not_called()

    @mock.patch("apply_insize_commercial_reconcile_258.connect_runtime_db")
    @mock.patch("apply_insize_commercial_reconcile_258.validate_apply_journal_for_rollback")
    @mock.patch("apply_insize_commercial_reconcile_258.load_apply_journal")
    @mock.patch("apply_insize_commercial_reconcile_258.resolve_production_database_identity")
    @mock.patch("apply_insize_commercial_reconcile_258.assert_production_apply_authorized")
    @mock.patch("apply_insize_commercial_reconcile_258.validate_production_source_xlsx")
    @mock.patch("apply_insize_commercial_reconcile_258.sha256_file")
    def test_rollback_locked_artifacts_reach_journal_binding(
        self,
        sha_mock,
        _src_mock,
        _prod_auth_mock,
        resolve_mock,
        load_journal_mock,
        validate_journal_mock,
        conn_mock,
    ):
        sha_mock.side_effect = _locked_sha_side_effect
        resolve_mock.return_value = {"current_database": "karzar_staging", "pg_system_identifier": "1"}
        load_journal_mock.return_value = {"mode": "APPLY"}
        validate_journal_mock.side_effect = ApplyAbort("stop_after_journal_binding")
        with mock.patch.dict(os.environ, _PRODUCTION_WRITE_ENV, clear=False):
            with self.assertRaises(ApplyAbort) as ctx:
                apply_main(_rollback_write_argv())
        self.assertEqual(str(ctx.exception), "stop_after_journal_binding")
        validate_journal_mock.assert_called_once()
        conn_mock.assert_not_called()

class PlanTests(unittest.TestCase):
    def test_plan_load_matches_evidence_counts(self):
        rows = load_plan_rows(PLAN)
        self.assertEqual(len(rows), 711)


class ApplyTransactionTests(unittest.TestCase):
    def _mini_plan(self) -> list[PlanRow]:
        return [
            PlanRow(
                product_id=10,
                sku="S10",
                combined_action="CLEAR_PRICE",
                availability_action="NO_CHANGE",
                price_action="CLEAR_PRICE",
                expected_current_hash=state_hash(
                    {
                        "product_id": "10",
                        "sku": "S10",
                        "brand_id": "1",
                        "is_active": "true",
                        "is_available": "true",
                        "base_price": "5000",
                        "deleted_at": "",
                        "image_present": "true",
                    }
                ),
                proposed_is_available=True,
                proposed_base_price=None,
                current_is_available=True,
                current_base_price=Decimal("5000"),
            )
        ]

    def test_stale_hash_blocks_writes(self):
        plan = self._mini_plan()
        live = {
            10: {
                "product_id": "10",
                "sku": "S10",
                "brand_id": "1",
                "is_active": "true",
                "is_available": "true",
                "base_price": "9999",
                "deleted_at": "",
                "image_present": "true",
            }
        }
        conn = FakeConn(live)
        result = apply_plan_rows(
            conn,
            plan,
            dry_run=False,
            batch_id="test",
            metadata={"started_at": "t"},
            journal_dir=Path(tempfile.mkdtemp()),
        )
        self.assertFalse(result.committed)
        self.assertEqual(result.rows_written, 0)
        self.assertFalse(conn.committed)

    def test_successful_apply_commits(self):
        plan = self._mini_plan()
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
        tmp = Path(tempfile.mkdtemp())
        result = apply_plan_rows(
            conn,
            plan,
            dry_run=False,
            batch_id="testbatch",
            metadata={"started_at": "t"},
            journal_dir=tmp,
        )
        self.assertTrue(result.committed)
        self.assertEqual(result.rows_written, 1)
        self.assertEqual(conn.store[10]["base_price"], "")

    def test_mid_apply_failure_rolls_back(self):
        plan = self._mini_plan() + [
            replace(
                self._mini_plan()[0],
                product_id=11,
                sku="S11",
                expected_current_hash=state_hash(
                    {
                        "product_id": "11",
                        "sku": "S11",
                        "brand_id": "1",
                        "is_active": "true",
                        "is_available": "true",
                        "base_price": "100",
                        "deleted_at": "",
                        "image_present": "false",
                    }
                ),
            )
        ]
        plan[1].product_id = 11
        plan[1].sku = "S11"
        live = {
            10: {
                "product_id": "10",
                "sku": "S10",
                "brand_id": "1",
                "is_active": "true",
                "is_available": "true",
                "base_price": "5000",
                "deleted_at": "",
                "image_present": "true",
            },
            11: {
                "product_id": "11",
                "sku": "S11",
                "brand_id": "1",
                "is_active": "true",
                "is_available": "true",
                "base_price": "100",
                "deleted_at": "",
                "image_present": "false",
            },
        }
        conn = FakeConn(live, fail_on_pid=11)
        result = apply_plan_rows(
            conn,
            plan,
            dry_run=False,
            batch_id="b",
            metadata={"started_at": "t"},
            journal_dir=Path(tempfile.mkdtemp()),
        )
        self.assertFalse(result.committed)
        self.assertEqual(conn.store[10]["base_price"], "5000")



class DryRunTests(unittest.TestCase):
    def test_dry_run_zero_writes(self):
        plan = [
            PlanRow(
                product_id=10,
                sku="S10",
                combined_action="CLEAR_PRICE",
                availability_action="NO_CHANGE",
                price_action="CLEAR_PRICE",
                expected_current_hash=state_hash(
                    {
                        "product_id": "10",
                        "sku": "S10",
                        "brand_id": "1",
                        "is_active": "true",
                        "is_available": "true",
                        "base_price": "5000",
                        "deleted_at": "",
                        "image_present": "true",
                    }
                ),
                proposed_is_available=True,
                proposed_base_price=None,
                current_is_available=True,
                current_base_price=Decimal("5000"),
            )
        ]
        live = {
            10: {
                "product_id": "10",
                "sku": "S10",
                "brand_id": "1",
                "is_active": "true",
                "is_available": "true",
                "base_price": "5000",
                "deleted_at": "",
                "image_present": "true",
            }
        }
        conn = FakeConn(live)
        result = apply_plan_rows(
            conn,
            plan,
            dry_run=True,
            batch_id="dry",
            metadata={"started_at": "t"},
            journal_dir=Path(tempfile.mkdtemp()),
        )
        self.assertFalse(result.committed)
        self.assertEqual(result.rows_written, 0)
        self.assertEqual(conn.store[10]["base_price"], "5000")


class EnvGateTests(unittest.TestCase):
    def test_missing_category_b_env(self):
        with mock.patch.dict(os.environ, {"KARZAR_ALLOW_PRODUCTION_WRITE": "1"}, clear=True):
            with self.assertRaises(ApplyAbort):
                assert_apply_authorization_gates(
                    apply=True,
                    rollback=False,
                    confirm_production_write=True,
                    confirm_source_sha256=OWNER_SOURCE_SHA256,
                    confirm_plan_sha256="abc",
                    confirm_mutation_count=711,
                    owner_authorization=OWNER_AUTH_APPLY,
                    plan_sha256="abc",
                    eligible_count=711,
                )


class StaleGuardHelperTests(unittest.TestCase):
    def test_stale_hash_guard_detects_drift(self):
        plan = PlanRow(
            product_id=1,
            sku="A",
            combined_action="CLEAR_PRICE",
            availability_action="NO_CHANGE",
            price_action="CLEAR_PRICE",
            expected_current_hash="deadbeef",
            proposed_is_available=True,
            proposed_base_price=None,
            current_is_available=True,
            current_base_price=Decimal("1"),
        )
        live = {
            1: {
                "product_id": "1",
                "sku": "A",
                "brand_id": "1",
                "is_active": "true",
                "is_available": "true",
                "base_price": "2",
                "deleted_at": "",
                "image_present": "false",
            }
        }
        guard = stale_hash_guard([plan], live)
        self.assertFalse(guard.ok)


class RollbackSkeletonTests(unittest.TestCase):
    def test_rollback_aborts_on_post_apply_drift(self):
        live_row = {
            "product_id": "5",
            "sku": "S5",
            "brand_id": "1",
            "is_active": "true",
            "is_available": "true",
            "base_price": "999",
            "deleted_at": "",
            "image_present": "false",
        }
        apply_journal = {
            "mode": "APPLY",
            "batch_id": "rb",
            "COMMITTED": "YES",
            "committed": True,
            "ROWS_WRITTEN": 1,
            "source_sha256": OWNER_SOURCE_SHA256,
            "plan_sha256": "plan",
            "rollback_manifest_sha256": "rb",
            "database_identity": {
                "current_database": "karzar_staging",
                "current_user": "karzar_staging",
            },
            "POST_COMMIT_VERIFICATION": "PASS",
            "rows": [
                {
                    "product_id": 5,
                    "sku": "S5",
                    "before_is_available": False,
                    "before_base_price": "100",
                    "expected_post_hash": "expected-post",
                    "expected_current_hash": "pre",
                }
            ],
        }
        conn = FakeConn({5: dict(live_row)})
        result = rollback_plan_rows(
            conn,
            apply_journal=apply_journal,
            batch_id="rb",
            metadata={"started_at": "t"},
            journal_dir=Path(tempfile.mkdtemp()),
        )
        self.assertFalse(result.committed)
        self.assertEqual(result.aborted_reason, "ROLLBACK_DRIFT")


class ActionSemanticsTests(unittest.TestCase):
    def test_clear_price_action_sets_null_target(self):
        row = PlanRow(
            product_id=1,
            sku="A",
            combined_action="CLEAR_PRICE",
            availability_action="NO_CHANGE",
            price_action="CLEAR_PRICE",
            expected_current_hash="x",
            proposed_is_available=True,
            proposed_base_price=None,
            current_is_available=True,
            current_base_price=Decimal("100"),
        )
        avail, price = proposed_values_for_row(row)
        self.assertTrue(avail)
        self.assertIsNone(price)




class ProductionGateTests(unittest.TestCase):
    def test_preflight_missing_xlsx_blocked(self):
        with self.assertRaises(ApplyAbort) as ctx:
            validate_production_source_xlsx(Path("/nonexistent/source.xlsx"))
        self.assertIn("BLOCKED_SOURCE_XLSX_MISSING", str(ctx.exception))

    def test_wrong_db_identity_blocked(self):
        with self.assertRaises(ApplyAbort):
            assert_expected_production_database_identity(
                {"current_database": "wrong", "current_user": "karzar_staging"}
            )


class WriterSemanticsTests(unittest.TestCase):
    def test_availability_only_sql(self):
        plan = PlanRow(
            product_id=1,
            sku="A",
            combined_action="SET_AVAILABLE",
            availability_action="SET_AVAILABLE",
            price_action="NO_CHANGE",
            expected_current_hash="x",
            proposed_is_available=True,
            proposed_base_price=Decimal("100"),
            current_is_available=False,
            current_base_price=Decimal("100"),
        )
        sql, _params = build_mutation_sql(
            plan,
            prop_avail=True,
            prop_price=Decimal("100"),
            before_avail=False,
            before_price=Decimal("100"),
        )
        self.assertIn("is_available", sql)
        self.assertNotIn("base_price =", sql)

    def test_price_only_sql(self):
        plan = PlanRow(
            product_id=1,
            sku="A",
            combined_action="CLEAR_PRICE",
            availability_action="NO_CHANGE",
            price_action="CLEAR_PRICE",
            expected_current_hash="x",
            proposed_is_available=True,
            proposed_base_price=None,
            current_is_available=True,
            current_base_price=Decimal("100"),
        )
        sql, _params = build_mutation_sql(
            plan,
            prop_avail=True,
            prop_price=None,
            before_avail=True,
            before_price=Decimal("100"),
        )
        self.assertIn("base_price", sql)
        self.assertNotIn("is_available =", sql)


class JournalCrashSafetyTests(unittest.TestCase):
    def test_precommit_journal_before_commit(self):
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
        order: list[str] = []

        def tracking_writer(path, payload):  # noqa: ANN001
            order.append(f"journal:{payload.get('journal_phase')}")
            write_journal_atomic(path, payload)

        real_commit = conn.commit

        def commit_track():
            order.append("commit")
            real_commit()

        conn.commit = commit_track  # type: ignore[method-assign]
        tmp = Path(tempfile.mkdtemp())
        apply_plan_rows(
            conn,
            plan,
            dry_run=False,
            batch_id="order-test",
            metadata={"started_at": "t", "source_sha256": OWNER_SOURCE_SHA256},
            journal_dir=tmp,
            journal_writer=tracking_writer,
        )
        self.assertIn("journal:PRE_COMMIT", order)
        self.assertLess(order.index("journal:PRE_COMMIT"), order.index("commit"))

    def test_journal_write_failure_skips_commit(self):
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

        def fail_writer(path, payload):  # noqa: ANN001
            raise OSError("disk full")

        result = apply_plan_rows(
            conn,
            plan,
            dry_run=False,
            batch_id="fail-journal",
            metadata={"started_at": "t"},
            journal_dir=Path(tempfile.mkdtemp()),
            journal_writer=fail_writer,
        )
        self.assertFalse(result.committed)
        self.assertFalse(conn.committed)
        self.assertEqual(result.aborted_reason, "JOURNAL_WRITE_FAILED")


class PostHashTests(unittest.TestCase):
    def test_expected_post_hash_respects_no_change_columns(self):
        live = {
            "product_id": "1",
            "sku": "A",
            "brand_id": "1",
            "is_active": "true",
            "is_available": "false",
            "base_price": "100",
            "deleted_at": "",
            "image_present": "false",
        }
        plan = PlanRow(
            product_id=1,
            sku="A",
            combined_action="SET_AVAILABLE",
            availability_action="SET_AVAILABLE",
            price_action="NO_CHANGE",
            expected_current_hash="x",
            proposed_is_available=True,
            proposed_base_price=Decimal("100"),
            current_is_available=False,
            current_base_price=Decimal("100"),
        )
        post = compute_expected_post_hash(live, plan)
        only_avail = dict(live)
        only_avail["is_available"] = "true"
        self.assertEqual(post, state_hash(only_avail))
        self.assertTrue(plan_mutates_price(plan) is False)

if __name__ == "__main__":
    unittest.main()
