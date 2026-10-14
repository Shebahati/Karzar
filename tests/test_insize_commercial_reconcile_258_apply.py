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
    OWNER_AUTH_APPLY,
    OWNER_SOURCE_SHA256,
    PlanRow,
    RollbackRow,
    apply_plan_rows,
    assert_apply_authorization_gates,
    classify_owner_freshness,
    load_plan_rows,
    proposed_values_for_row,
    rollback_plan_rows,
    state_hash,
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
            if len(params) == 6:
                new_price, new_avail, pid, sku, _exp_price, _exp_avail = params
            else:
                new_price, new_avail, pid, sku = params
            if self.fail_on_pid == int(pid):
                self.rowcount = 0
                return
            live = self.store.get(int(pid))
            if live is None or live["sku"] != sku:
                self.rowcount = 0
                return
            live = dict(live)
            live["is_available"] = "true" if new_avail else "false"
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
                confirm_plan_sha256="x",
                confirm_mutation_count=711,
                owner_authorization="WRONG",
                plan_sha256="x",
                eligible_count=711,
            )

    def test_cli_apply_without_confirmations_aborts(self):
        with self.assertRaises(ApplyAbort):
            apply_main(["--apply"])


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
        row = RollbackRow(
            product_id=5,
            sku="S5",
            pre_is_available=False,
            pre_base_price=Decimal("100"),
            proposed_is_available=True,
            proposed_base_price=Decimal("200"),
            expected_current_hash="x",
        )
        live = {
            5: {
                "product_id": "5",
                "sku": "S5",
                "brand_id": "1",
                "is_active": "true",
                "is_available": "true",
                "base_price": "999",
                "deleted_at": "",
                "image_present": "false",
            }
        }
        conn = FakeConn(live)
        result = rollback_plan_rows(
            conn,
            [row],
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


if __name__ == "__main__":
    unittest.main()
