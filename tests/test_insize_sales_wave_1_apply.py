"""Guarded INSIZE Sales Wave 1 APPLY tests (no production mutation)."""

from __future__ import annotations

import csv
import os
import shutil
import sys
import tempfile
import unittest
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from apply_insize_sales_wave_1 import main as apply_main  # noqa: E402
from catalog_target.sales_wave_apply import (  # noqa: E402
    REVIEWED_ALLOWLIST_COUNT,
    REVIEWED_PLAN_CSV_SHA256,
    ApplyAbort,
    LiveProduct,
    PlanRow,
    apply_allowlist,
    assert_production_apply_authorized,
    load_and_validate_plan,
    sha256_file,
    stale_guard,
    write_pre_apply_backup,
    writer_contract_summary,
)

PLAN_CSV = ROOT / "data" / "catalog-target" / "insize_sales_wave_1_plan.csv"


def _live_from_plan_row(row: PlanRow, **overrides: Any) -> LiveProduct:
    payload = {
        "id": row.product_id,
        "sku": row.sku,
        "base_price": row.expected_base_price,
        "is_active": row.expected_is_active,
        "is_available": row.expected_is_available,
        "deleted_at": None,
    }
    payload.update(overrides)
    return LiveProduct(**payload)


class FakeCursor:
    def __init__(self, store: dict[int, LiveProduct], *, fail_after: int | None = None):
        self.store = store
        self.fail_after = fail_after
        self.updates = 0
        self.rowcount = 0
        self._result: list[tuple] = []
        self.executed: list[tuple[str, Any]] = []

    def execute(self, sql: str, params=None) -> None:  # noqa: ANN001
        self.executed.append((sql, params))
        sql_l = " ".join(sql.lower().split())
        if sql_l.startswith("select "):
            ids = list(params[0])
            self._result = []
            for pid in sorted(ids):
                row = self.store.get(pid)
                if row is None:
                    continue
                self._result.append(
                    (
                        row.id,
                        row.sku,
                        row.base_price,
                        row.is_active,
                        row.is_available,
                        row.deleted_at,
                        row.brand_id,
                        row.category_id,
                        row.name,
                        row.slug,
                    )
                )
            self.rowcount = len(self._result)
            return
        if sql_l.startswith("update "):
            (
                new_price,
                new_avail,
                product_id,
                sku,
                expected_price,
                expected_avail,
                expected_active,
            ) = params
            if self.fail_after is not None and self.updates >= self.fail_after:
                self.rowcount = 0
                return
            row = self.store.get(int(product_id))

            def _price_matches(live_price: Decimal | None, expected: Any) -> bool:
                if expected is None or expected == "":
                    return live_price is None
                if live_price is None:
                    return False
                return Decimal(str(live_price)) == Decimal(str(expected))

            if (
                row is None
                or row.sku != sku
                or row.deleted_at
                or not _price_matches(row.base_price, expected_price)
                or row.is_available is not expected_avail
                or row.is_active is not expected_active
            ):
                self.rowcount = 0
                return
            self.store[int(product_id)] = LiveProduct(
                id=row.id,
                sku=row.sku,
                base_price=Decimal(str(new_price)),
                is_active=row.is_active,
                is_available=bool(new_avail),
                deleted_at=row.deleted_at,
                brand_id=row.brand_id,
                category_id=row.category_id,
                name=row.name,
                slug=row.slug,
            )
            self.updates += 1
            self.rowcount = 1
            return
        raise AssertionError(f"unexpected SQL: {sql}")

    def fetchall(self):
        return list(self._result)


class FakeConn:
    def __init__(self, store: dict[int, LiveProduct], *, fail_after: int | None = None):
        self.store = store
        self.fail_after = fail_after
        self.committed = False
        self.rolled_back = False
        self._snapshot: dict[int, LiveProduct] | None = None
        self.cursor_obj = FakeCursor(store, fail_after=fail_after)

    def cursor(self, *args, **kwargs):  # noqa: ANN002, ANN003
        if self._snapshot is None:
            self._snapshot = {pid: replace(row) for pid, row in self.store.items()}
        return self.cursor_obj

    def commit(self) -> None:
        self.committed = True
        self._snapshot = {pid: replace(row) for pid, row in self.store.items()}

    def rollback(self) -> None:
        self.rolled_back = True
        if self._snapshot is not None:
            self.store.clear()
            self.store.update({pid: replace(row) for pid, row in self._snapshot.items()})


class PlanContractTests(unittest.TestCase):
    def test_load_reviewed_plan(self):
        rows = load_and_validate_plan(PLAN_CSV)
        self.assertEqual(len(rows), REVIEWED_ALLOWLIST_COUNT)
        self.assertEqual(sha256_file(PLAN_CSV), REVIEWED_PLAN_CSV_SHA256)
        self.assertTrue(all(r.proposed_is_available for r in rows))
        self.assertTrue(all(r.inventory_status == "موجود" for r in rows))
        self.assertTrue(any(r.sku == "4602-32" for r in rows))

    def test_plan_checksum_mismatch_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "plan.csv"
            shutil.copy(PLAN_CSV, bad)
            with bad.open("a", encoding="utf-8") as handle:
                handle.write("\n")
            with self.assertRaises(ApplyAbort) as ctx:
                load_and_validate_plan(bad)
            self.assertIn("plan_checksum_mismatch", str(ctx.exception))

    def test_duplicate_product_id_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dup.csv"
            with PLAN_CSV.open(encoding="utf-8-sig", newline="") as src, path.open(
                "w", encoding="utf-8", newline=""
            ) as dst:
                reader = csv.DictReader(src)
                writer = csv.DictWriter(dst, fieldnames=reader.fieldnames)
                writer.writeheader()
                all_rows = list(reader)
                all_rows[1]["id"] = all_rows[0]["id"]
                writer.writerows(all_rows)
            with self.assertRaises(ApplyAbort) as ctx:
                load_and_validate_plan(path, require_checksum=False)
            self.assertIn("duplicate_product_id", str(ctx.exception))

    def test_wrong_brand_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "brand.csv"
            with PLAN_CSV.open(encoding="utf-8-sig", newline="") as src, path.open(
                "w", encoding="utf-8", newline=""
            ) as dst:
                reader = csv.DictReader(src)
                writer = csv.DictWriter(dst, fieldnames=reader.fieldnames)
                writer.writeheader()
                all_rows = list(reader)
                all_rows[0]["current_brand"] = "TERMA"
                writer.writerows(all_rows)
            with self.assertRaises(ApplyAbort) as ctx:
                load_and_validate_plan(path, require_checksum=False)
            self.assertIn("wrong_brand", str(ctx.exception))

    def test_review_row_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review.csv"
            with PLAN_CSV.open(encoding="utf-8-sig", newline="") as src, path.open(
                "w", encoding="utf-8", newline=""
            ) as dst:
                reader = csv.DictReader(src)
                writer = csv.DictWriter(dst, fieldnames=reader.fieldnames)
                writer.writeheader()
                all_rows = list(reader)
                all_rows[0]["reconciliation_state"] = "REVIEW"
                writer.writerows(all_rows)
            with self.assertRaises(ApplyAbort) as ctx:
                load_and_validate_plan(path, require_checksum=False)
            self.assertIn("review_row_forbidden", str(ctx.exception))


class StaleGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = load_and_validate_plan(PLAN_CSV)

    def test_stale_price_aborts(self):
        live = [_live_from_plan_row(r) for r in self.plan]
        live[0] = replace(live[0], base_price=live[0].base_price + Decimal("1"))
        guard = stale_guard(self.plan, live)
        self.assertFalse(guard.ok)
        self.assertTrue(any(d.reason == "stale_price" for d in guard.drifts))

    def test_stale_availability_aborts(self):
        live = [_live_from_plan_row(r) for r in self.plan]
        live[0] = replace(live[0], is_available=not live[0].is_available)
        guard = stale_guard(self.plan, live)
        self.assertFalse(guard.ok)
        self.assertTrue(any(d.reason == "stale_availability" for d in guard.drifts))

    def test_missing_row_aborts(self):
        live = [_live_from_plan_row(r) for r in self.plan][1:]
        guard = stale_guard(self.plan, live)
        self.assertFalse(guard.ok)
        self.assertEqual(len(guard.missing_ids), 1)

    def test_deleted_row_aborts(self):
        live = [_live_from_plan_row(r) for r in self.plan]
        live[0] = replace(live[0], deleted_at="2026-01-01T00:00:00Z")
        guard = stale_guard(self.plan, live)
        self.assertFalse(guard.ok)
        self.assertTrue(any(d.reason == "deleted_current" for d in guard.drifts))


class ApplyTransactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = load_and_validate_plan(PLAN_CSV)

    def _store(self) -> dict[int, LiveProduct]:
        return {r.product_id: _live_from_plan_row(r) for r in self.plan}

    def test_dry_run_default_zero_writes(self):
        store = self._store()
        before = {pid: replace(row) for pid, row in store.items()}
        conn = FakeConn(store)
        with tempfile.TemporaryDirectory() as tmp:
            result = apply_allowlist(conn, self.plan, dry_run=True, backup_dir=Path(tmp))
        self.assertEqual(result.mode, "dry_run")
        self.assertFalse(result.production_apply_executed)
        self.assertEqual(result.updated_count, 0)
        self.assertFalse(conn.committed)
        self.assertTrue(conn.rolled_back)
        self.assertEqual(conn.cursor_obj.updates, 0)
        for pid, row in before.items():
            self.assertEqual(store[pid].base_price, row.base_price)
            self.assertEqual(store[pid].is_available, row.is_available)

    def test_stale_guard_aborts_before_first_write(self):
        store = self._store()
        first_id = self.plan[0].product_id
        store[first_id] = replace(store[first_id], base_price=Decimal("1"))
        conn = FakeConn(store)
        result = apply_allowlist(conn, self.plan, dry_run=False)
        self.assertTrue(result.aborted)
        self.assertEqual(result.abort_reason, "stale_snapshot_guard_failed")
        self.assertFalse(conn.committed)
        self.assertEqual(conn.cursor_obj.updates, 0)

    def test_transaction_success_path(self):
        store = self._store()
        conn = FakeConn(store)
        with tempfile.TemporaryDirectory() as tmp:
            result = apply_allowlist(conn, self.plan, dry_run=False, backup_dir=Path(tmp))
            self.assertTrue(Path(result.backup_path).is_file())
            self.assertTrue(Path(result.rollback_sql_path).is_file())
            self.assertTrue(result.backup_sha256)
        self.assertEqual(result.mode, "apply_committed")
        self.assertTrue(result.production_apply_executed)
        self.assertEqual(result.updated_count, REVIEWED_ALLOWLIST_COUNT)
        self.assertTrue(conn.committed)
        for plan in self.plan:
            live = store[plan.product_id]
            self.assertEqual(live.base_price, plan.proposed_base_price)
            self.assertEqual(live.is_available, plan.proposed_is_available)
            self.assertEqual(live.is_active, plan.expected_is_active)

    def test_partial_failure_complete_rollback(self):
        store = self._store()
        before = {pid: replace(row) for pid, row in store.items()}
        conn = FakeConn(store, fail_after=10)
        with self.assertRaises(ApplyAbort) as ctx:
            apply_allowlist(conn, self.plan, dry_run=False)
        self.assertIn("affected_row_mismatch", str(ctx.exception))
        self.assertTrue(conn.rolled_back)
        self.assertFalse(conn.committed)
        self.assertLess(conn.cursor_obj.updates, REVIEWED_ALLOWLIST_COUNT)
        for pid, row in before.items():
            self.assertEqual(store[pid].base_price, row.base_price)
            self.assertEqual(store[pid].is_available, row.is_available)
            self.assertEqual(store[pid].is_active, row.is_active)

    def test_non_allowlisted_row_cannot_mutate(self):
        store = self._store()
        outsider = LiveProduct(
            id=999999001,
            sku="OUTSIDER-1",
            base_price=Decimal("100"),
            is_active=True,
            is_available=False,
            deleted_at=None,
        )
        store[outsider.id] = outsider
        conn = FakeConn(store)
        apply_allowlist(conn, self.plan, dry_run=False)
        self.assertEqual(store[outsider.id].base_price, Decimal("100"))
        self.assertFalse(store[outsider.id].is_available)

    def test_only_base_price_and_is_available_mutable(self):
        store = self._store()
        conn = FakeConn(store)
        apply_allowlist(conn, self.plan, dry_run=False)
        for sql, _params in conn.cursor_obj.executed:
            if sql.strip().lower().startswith("update"):
                set_clause = sql.lower().split("where", 1)[0]
                self.assertIn("base_price", set_clause)
                self.assertIn("is_available", set_clause)
                self.assertNotIn("is_active", set_clause)
                self.assertNotIn("brand_id", set_clause)
                self.assertNotIn("category_id", set_clause)
                self.assertNotIn("deleted_at", set_clause)

    def test_rollback_artifact_generation(self):
        live = [_live_from_plan_row(r) for r in self.plan[:3]]
        with tempfile.TemporaryDirectory() as tmp:
            backup, digest, rollback = write_pre_apply_backup(live, output_dir=Path(tmp), stamp="T")
            self.assertTrue(backup.is_file())
            self.assertEqual(digest, sha256_file(backup))
            text = rollback.read_text(encoding="utf-8")
            self.assertIn("BEGIN;", text)
            self.assertIn("COMMIT;", text)
            self.assertIn(f"WHERE id = {live[0].id}", text)


class AuthorizationTests(unittest.TestCase):
    def test_apply_requires_explicit_gate(self):
        with self.assertRaises(ApplyAbort):
            assert_production_apply_authorized(
                apply=True,
                confirm_production_write=False,
                confirm_plan_sha256=REVIEWED_PLAN_CSV_SHA256,
                plan_csv_sha256=REVIEWED_PLAN_CSV_SHA256,
                db_host="db.karzartools.com",
            )

    def test_plan_sha_confirm_mismatch(self):
        env = {
            "KARZAR_ALLOW_PRODUCTION_WRITE": "1",
            "KARZAR_INGESTION_CATEGORY": "B",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            with self.assertRaises(ApplyAbort) as ctx:
                assert_production_apply_authorized(
                    apply=True,
                    confirm_production_write=True,
                    confirm_plan_sha256="deadbeef",
                    plan_csv_sha256=REVIEWED_PLAN_CSV_SHA256,
                    db_host="localhost",
                )
            self.assertIn("confirm_plan_sha256_mismatch", str(ctx.exception))

    def test_cli_dry_run_default_no_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.json"
            code = apply_main(["--report-json", str(report)])
            self.assertEqual(code, 0)
            payload = report.read_text(encoding="utf-8")
            self.assertIn('"PRODUCTION_APPLY_EXECUTED": false', payload)
            self.assertIn('"PRODUCTION_DB_MUTATION": "ZERO"', payload)

    def test_writer_contract_marks_implementation(self):
        contract = writer_contract_summary()
        self.assertTrue(contract["stale_snapshot_guard"]["writer_implemented"])
        self.assertEqual(contract["default_mode"], "DRY_RUN")
        self.assertEqual(contract["mutable_columns"], ["base_price", "is_available"])


class CliLiveCsvDryRunTests(unittest.TestCase):
    def test_live_csv_stale_ok_dry_run(self):
        plan = load_and_validate_plan(PLAN_CSV)
        with tempfile.TemporaryDirectory() as tmp:
            live_path = Path(tmp) / "live.csv"
            with live_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "id",
                        "sku",
                        "base_price",
                        "is_active",
                        "is_available",
                        "deleted_at",
                    ],
                )
                writer.writeheader()
                for row in plan:
                    writer.writerow(
                        {
                            "id": row.product_id,
                            "sku": row.sku,
                            "base_price": ""
                            if row.expected_base_price is None
                            else str(row.expected_base_price),
                            # Match PostgreSQL COPY bool literals.
                            "is_active": "t" if row.expected_is_active else "f",
                            "is_available": "t" if row.expected_is_available else "f",
                            "deleted_at": "",
                        }
                    )
            report = Path(tmp) / "report.json"
            code = apply_main(
                [
                    "--live-csv",
                    str(live_path),
                    "--report-json",
                    str(report),
                ]
            )
            self.assertEqual(code, 0)
            text = report.read_text(encoding="utf-8")
            self.assertIn('"ok": true', text)
            self.assertIn('"PRODUCTION_APPLY_EXECUTED": false', text)


if __name__ == "__main__":
    unittest.main()
