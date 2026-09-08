"""Guarded INSIZE strict public-sale Safety S1 APPLY tests (no production mutation)."""

from __future__ import annotations

import csv
import json
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

from apply_insize_strict_public_sale_s1 import main as apply_main  # noqa: E402
from catalog_target.public_sale_safety_apply import (  # noqa: E402
    REVIEWED_ALLOWLIST_COUNT,
    REVIEWED_PLAN_CSV_SHA256,
    ApplyAbort,
    LiveProduct,
    StrictPlanRow,
    apply_allowlist,
    assert_isolation_queries_match_schema,
    assert_production_apply_authorized,
    isolation_proof_queries,
    load_and_validate_plan,
    sha256_file,
    stale_guard,
    write_pre_apply_backup,
    writer_contract_summary,
)

PLAN_CSV = ROOT / "data" / "catalog-target" / "insize_strict_public_sale_s1_plan.csv"


def _sample_plan_rows(n: int = 3) -> list[StrictPlanRow]:
    rows = load_and_validate_plan(PLAN_CSV)
    return rows[:n]


def _live_from_plan_row(row: StrictPlanRow, **overrides: Any) -> LiveProduct:
    payload = {
        "id": row.product_id,
        "sku": row.sku,
        "base_price": row.expected_base_price,
        "is_active": row.expected_is_active,
        "is_available": row.expected_is_available,
        "deleted_at": None,
        "brand_id": "3",
        "category_id": "57",
        "name": f"name-{row.sku}",
        "slug": row.sku.lower(),
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
            # Availability-only mutation — identity/price/active/media untouched.
            self.store[int(product_id)] = LiveProduct(
                id=row.id,
                sku=row.sku,
                base_price=row.base_price,
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
        self.assertTrue(all(r.expected_is_available for r in rows))
        self.assertTrue(all(not r.proposed_is_available for r in rows))
        self.assertTrue(all(r.price_mutation == "none" for r in rows))
        self.assertTrue(any(r.sku == "2313-1" for r in rows))  # non-target quarantine
        self.assertTrue(any(r.sku == "5042" for r in rows))
        self.assertTrue(any(r.sku == "ISM-PM200SA" for r in rows))

    def test_plan_checksum_mismatch_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "plan.csv"
            bad.write_bytes(PLAN_CSV.read_bytes() + b"\n")
            with self.assertRaises(ApplyAbort) as ctx:
                load_and_validate_plan(bad)
            self.assertIn("plan_checksum_mismatch", str(ctx.exception))

    def test_row_count_mismatch_aborts(self):
        rows = load_and_validate_plan(PLAN_CSV)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "short.csv"
            with PLAN_CSV.open(encoding="utf-8-sig", newline="") as src, path.open(
                "w", encoding="utf-8", newline=""
            ) as dst:
                reader = csv.DictReader(src)
                writer = csv.DictWriter(dst, fieldnames=reader.fieldnames)
                writer.writeheader()
                writer.writerows(list(reader)[:10])
            with self.assertRaises(ApplyAbort) as ctx:
                load_and_validate_plan(path, require_checksum=False)
            self.assertIn("plan_count_mismatch", str(ctx.exception))
        self.assertEqual(len(rows), REVIEWED_ALLOWLIST_COUNT)


class StaleGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = _sample_plan_rows(5)

    def test_stale_price_aborts(self):
        live = [_live_from_plan_row(r) for r in self.plan]
        live[0] = replace(live[0], base_price=(live[0].base_price or Decimal("0")) + Decimal("1"))
        guard = stale_guard(self.plan, live)
        self.assertFalse(guard.ok)
        self.assertTrue(any(d.reason == "stale_price" for d in guard.drifts))

    def test_stale_availability_aborts(self):
        live = [_live_from_plan_row(r) for r in self.plan]
        live[0] = replace(live[0], is_available=False)
        guard = stale_guard(self.plan, live)
        self.assertFalse(guard.ok)
        self.assertTrue(any(d.reason == "stale_availability" for d in guard.drifts))

    def test_sku_mismatch_aborts(self):
        live = [_live_from_plan_row(r) for r in self.plan]
        live[0] = replace(live[0], sku="WRONG-SKU")
        guard = stale_guard(self.plan, live)
        self.assertFalse(guard.ok)
        self.assertTrue(any(d.reason == "sku_mismatch" for d in guard.drifts))


class ApplyBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.plan = _sample_plan_rows(4)
        self.store = {r.product_id: _live_from_plan_row(r) for r in self.plan}

    def test_dry_run_zero_mutation(self):
        before = {pid: replace(row) for pid, row in self.store.items()}
        conn = FakeConn(self.store)
        result = apply_allowlist(
            conn, self.plan, dry_run=True, expected_count=len(self.plan)
        )
        self.assertEqual(result.mode, "dry_run")
        self.assertFalse(result.production_apply_executed)
        self.assertFalse(result.aborted)
        self.assertEqual(result.updated_count, 0)
        self.assertTrue(conn.rolled_back)
        self.assertFalse(conn.committed)
        for pid, row in before.items():
            self.assertEqual(self.store[pid].is_available, row.is_available)
            self.assertEqual(self.store[pid].base_price, row.base_price)
            self.assertEqual(self.store[pid].is_active, row.is_active)
            self.assertEqual(self.store[pid].sku, row.sku)
            self.assertEqual(self.store[pid].name, row.name)

    def test_apply_only_allowlisted_availability(self):
        outsider = LiveProduct(
            id=999999,
            sku="OUTSIDER",
            base_price=Decimal("1"),
            is_active=True,
            is_available=True,
            deleted_at=None,
            brand_id="3",
            category_id="57",
            name="out",
            slug="out",
        )
        self.store[outsider.id] = outsider
        before_out = replace(outsider)
        conn = FakeConn(self.store)
        result = apply_allowlist(
            conn, self.plan, dry_run=False, expected_count=len(self.plan)
        )
        self.assertEqual(result.mode, "apply_committed")
        self.assertTrue(result.production_apply_executed)
        self.assertEqual(result.updated_count, len(self.plan))
        for row in self.plan:
            live = self.store[row.product_id]
            self.assertFalse(live.is_available)
            self.assertEqual(live.base_price, row.expected_base_price)
            self.assertEqual(live.is_active, row.expected_is_active)
            self.assertEqual(live.sku, row.sku)
            self.assertEqual(live.name, f"name-{row.sku}")
        self.assertEqual(self.store[outsider.id].is_available, before_out.is_available)
        self.assertEqual(self.store[outsider.id].base_price, before_out.base_price)

    def test_stale_row_aborts_entire_transaction(self):
        self.store[self.plan[0].product_id] = replace(
            self.store[self.plan[0].product_id],
            base_price=Decimal("123456"),
        )
        conn = FakeConn(self.store)
        result = apply_allowlist(
            conn, self.plan, dry_run=False, expected_count=len(self.plan)
        )
        self.assertTrue(result.aborted)
        self.assertEqual(result.abort_reason, "stale_snapshot_guard_failed")
        self.assertFalse(result.production_apply_executed)
        self.assertTrue(conn.rolled_back)
        # No availability flips when aborted before writes.
        self.assertTrue(self.store[self.plan[1].product_id].is_available)

    def test_rowcount_mismatch_aborts_and_rolls_back(self):
        conn = FakeConn(self.store, fail_after=1)
        with self.assertRaises(ApplyAbort) as ctx:
            apply_allowlist(
                conn, self.plan, dry_run=False, expected_count=len(self.plan)
            )
        self.assertIn("affected_row_mismatch", str(ctx.exception))
        self.assertTrue(conn.rolled_back)
        # FakeConn rollback restores snapshot taken at first cursor().
        self.assertTrue(all(self.store[r.product_id].is_available for r in self.plan))

    def test_backup_and_rollback_sql_sufficient(self):
        conn = FakeConn(self.store)
        with tempfile.TemporaryDirectory() as tmp:
            result = apply_allowlist(
                conn,
                self.plan,
                dry_run=True,
                backup_dir=Path(tmp),
                expected_count=len(self.plan),
            )
            self.assertTrue(result.backup_path)
            self.assertTrue(Path(result.backup_path).is_file())
            self.assertTrue(Path(result.rollback_sql_path).is_file())
            sql = Path(result.rollback_sql_path).read_text(encoding="utf-8")
            self.assertIn("UPDATE products SET is_available", sql)
            self.assertNotIn("base_price =", sql.split("SET", 1)[1].split("WHERE", 1)[0])
            self.assertIn("BEGIN;", sql)
            self.assertIn("COMMIT;", sql)

    def test_apply_cannot_run_accidentally_default(self):
        with mock.patch.dict("os.environ", {}, clear=False):
            for key in ("KARZAR_ALLOW_PRODUCTION_WRITE", "KARZAR_INGESTION_CATEGORY"):
                # Ensure missing auth aborts when --apply requested.
                pass
            with self.assertRaises(ApplyAbort):
                assert_production_apply_authorized(
                    apply=True,
                    confirm_production_write=False,
                    confirm_plan_sha256=REVIEWED_PLAN_CSV_SHA256,
                    plan_csv_sha256=REVIEWED_PLAN_CSV_SHA256,
                    db_host="api.karzartools.com",
                    database_url="postgresql://u:p@api.karzartools.com/db",
                )

    def test_cli_defaults_to_dry_run_plan_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.json"
            rc = apply_main(
                [
                    "--plan-csv",
                    str(PLAN_CSV),
                    "--report-json",
                    str(report),
                ]
            )
            self.assertEqual(rc, 0)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["mode"], "dry_run_plan_only")
            self.assertFalse(payload["production_apply_executed"])
            self.assertEqual(payload["PRODUCTION_MUTATION"], "ZERO")
            self.assertEqual(payload["allowlist_count"], REVIEWED_ALLOWLIST_COUNT)

    def test_isolation_queries_and_contract(self):
        assert_isolation_queries_match_schema()
        queries = isolation_proof_queries([1, 2, 3])
        self.assertIn("non_allowlist_fingerprint", queries)
        self.assertIn("product_images_fingerprint", queries)
        contract = writer_contract_summary()
        self.assertEqual(contract["default_mode"], "DRY_RUN")
        self.assertEqual(contract["mutable_columns"], ["is_available"])
        self.assertIn("base_price", contract["forbidden_columns"])


if __name__ == "__main__":
    unittest.main()
