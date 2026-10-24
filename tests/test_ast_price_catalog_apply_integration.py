"""AST catalog apply — integration-style tests (no production DB)."""

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

from catalog_target.ast_price_catalog_apply import (  # noqa: E402
    ApplyAbort,
    CreatePlanRow,
    UpdatePlanRow,
    apply_creates_sql,
    apply_updates_sql,
    execute_ast_catalog_apply,
    load_create_plan,
    load_update_plan,
    rollback_from_journal,
)
from catalog_target.ast_price_catalog_category_map import classify_create_category  # noqa: E402
from catalog_target.ast_price_catalog_constants import (  # noqa: E402
    PRICING_POLICY_ID,
    SOURCE_ARCHIVE_SHA256,
)
from catalog_target.ast_price_catalog_reconcile import CREATE_APPROVAL_OWNER  # noqa: E402


class FakeCursor:
    def __init__(self, store: dict[int, dict[str, str]], sku_index: dict[str, int]):
        self.store = store
        self.sku_index = sku_index
        self.rowcount = 0
        self._rows: list[tuple] = []
        self._next_id = max(store.keys(), default=0) + 1

    def execute(self, sql: str, params=None) -> None:  # noqa: ANN001
        sql_l = " ".join(sql.lower().split())
        if sql_l.startswith("select "):
            if "any" in sql_l:
                ids = list(params[0])
                self._rows = []
                for pid in ids:
                    row = self.store.get(int(pid))
                    if row:
                        self._rows.append(
                            (int(row["product_id"]), row["sku"], row.get("base_price") or "")
                        )
                self.rowcount = len(self._rows)
            return
        if sql_l.startswith("update "):
            if "deleted_at = now()" in sql_l:
                pid, sku = int(params[0]), params[1]
                live = self.store.get(pid)
                if live and live["sku"] == sku and not live.get("deleted_at"):
                    live = dict(live)
                    live["deleted_at"] = "now"
                    live["is_active"] = "false"
                    self.store[pid] = live
                    self.rowcount = 1
                else:
                    self.rowcount = 0
                return
            new_price = params[0]
            pid = int(params[1])
            sku = params[2]
            expect = params[3] if len(params) > 3 else None
            live = self.store.get(pid)
            if live is None or live["sku"] != sku:
                self.rowcount = 0
                return
            if expect is not None:
                cur_p = live.get("base_price") or ""
                if Decimal(cur_p or "0") != Decimal(str(expect or "0")) and (
                    cur_p != str(expect)
                ):
                    if str(cur_p) != str(expect):
                        self.rowcount = 0
                        return
            live = dict(live)
            live["base_price"] = "" if new_price is None else str(new_price)
            self.store[pid] = live
            self.rowcount = 1
            return
        if sql_l.startswith("insert into products"):
            sku, name, brand_id, category_id, base_price, is_active, slug = params[:7]
            if sku in self.sku_index:
                self.rowcount = 0
                return
            pid = self._next_id
            self._next_id += 1
            self.store[pid] = {
                "product_id": str(pid),
                "sku": sku,
                "base_price": str(base_price or ""),
                "brand_id": str(brand_id),
                "is_active": "true" if is_active else "false",
            }
            self.sku_index[sku] = pid
            self._rows = [(pid,)]
            self.rowcount = 1
            return
        raise AssertionError(sql_l)

    def fetchall(self):
        return list(self._rows)

    def fetchone(self):
        return self._rows[0] if self._rows else None


class FakeConn:
    def __init__(self, store: dict[int, dict[str, str]]):
        self.store = store
        self.sku_index = {v["sku"]: int(k) for k, v in store.items()}
        self.committed = False
        self.rolled_back = False

    def cursor(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return FakeCursor(self.store, self.sku_index)

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


class AstApplyIntegrationTests(unittest.TestCase):
    def test_update_rowcount_mismatch_rolls_back(self):
        store = {1: {"product_id": "1", "sku": "A", "base_price": "100"}}
        conn = FakeConn(store)
        rows = [
            UpdatePlanRow(
                product_id=1, sku="A", expected_current_price=Decimal("999"), proposed_price=Decimal("200")
            )
        ]
        with self.assertRaises(ApplyAbort):
            apply_updates_sql(conn, rows, dry_run=False)
        self.assertTrue(conn.rolled_back)

    def test_execute_apply_updates_and_creates(self):
        store = {10: {"product_id": "10", "sku": "U1", "base_price": "1000"}}
        conn = FakeConn(store)
        updates = [
            UpdatePlanRow(
                product_id=10,
                sku="U1",
                expected_current_price=Decimal("1000"),
                proposed_price=Decimal("1100"),
            )
        ]
        creates = [
            CreatePlanRow(
                sku="N1",
                brand_id=13,
                category_id=49,
                name="tap ET N1",
                base_price=Decimal("500"),
            )
        ]
        with tempfile.TemporaryDirectory() as td:
            result = execute_ast_catalog_apply(
                conn,
                updates,
                creates,
                dry_run=False,
                batch_id="test-batch",
                journal_dir=Path(td),
                metadata={},
                live_by_id={10: {"sku": "U1", "base_price": "1000"}},
                create_executor=lambda c, rows: apply_creates_sql(c, rows, dry_run=False),
            )
        self.assertTrue(result.production_apply_executed)
        self.assertEqual(result.updates_written, 1)
        self.assertEqual(result.creates_written, 1)
        self.assertEqual(store[10]["base_price"], "1100")

    def test_rollback_from_journal_restores_price(self):
        store = {10: {"product_id": "10", "sku": "U1", "base_price": "1100"}}
        conn = FakeConn(store)
        journal = {
            "committed": True,
            "execution_state": "VERIFIED",
            "updates": [
                {
                    "product_id": 10,
                    "sku": "U1",
                    "before_base_price": "1000",
                    "after_base_price": "1100",
                }
            ],
            "creates": [],
        }
        rollback_from_journal(conn, journal, dry_run=False)
        self.assertEqual(store[10]["base_price"], "1000")

    def test_load_create_plan_requires_owner_approval(self):
        path = Path(tempfile.mkstemp(suffix=".csv")[1])
        path.write_text(
            "sku,brand_id,category_id,name,base_price,is_available,is_active,apply_eligible,"
            "approval_status,pricing_policy_id,archive_checksum\n"
            f"C1,13,49,name C1,100,false,true,YES,PROPOSED,{PRICING_POLICY_ID},{SOURCE_ARCHIVE_SHA256}\n",
            encoding="utf-8",
        )
        self.assertEqual(len(load_create_plan(path, require_owner_approval=True)), 0)
        path.write_text(
            "sku,brand_id,category_id,name,base_price,is_available,is_active,apply_eligible,"
            "approval_status,pricing_policy_id,archive_checksum\n"
            f"C1,13,49,name C1,100,false,true,YES,{CREATE_APPROVAL_OWNER},{PRICING_POLICY_ID},"
            f"{SOURCE_ARCHIVE_SHA256}\n",
            encoding="utf-8",
        )
        self.assertEqual(len(load_create_plan(path, require_owner_approval=True)), 1)

    def test_category_dasqua_not_machine_tap(self):
        meta = {57: {"selectable": True}, 49: {"selectable": True}}
        decision = classify_create_category(
            source_file="لیست قیمت داسکوا 14050721.pdf",
            brand_hint="DASQUA",
            code="1234",
            code_nearby="کولیس دیجیتال",
            cat_meta=meta,
        )
        self.assertEqual(decision.category_id, 57)

    def test_category_endmill_not_carbide_drill(self):
        meta = {35: {"selectable": True}, 41: {"selectable": True}}
        decision = classify_create_category(
            source_file="لیست قیمت  فرز انگشتی 14050707.pdf",
            brand_hint="ASTPOWER_OR_SOURCE_BRAND_REVIEW",
            code="EM10",
            code_nearby="",
            cat_meta=meta,
        )
        self.assertEqual(decision.category_id, 35)

    def test_category_hssco_endmill_not_carbide(self):
        meta = {38: {"selectable": True}, 35: {"selectable": True}}
        decision = classify_create_category(
            source_file="لیست قیمت  فرز انگشتی 14050707.pdf",
            brand_hint="ASTPOWER_OR_SOURCE_BRAND_REVIEW",
            code="HSSCO10",
            code_nearby="HSS CO 10mm",
            cat_meta=meta,
        )
        self.assertEqual(decision.category_id, 38)

    def test_cli_apply_not_noop(self):
        ops = SCRIPTS / "ops"
        sys.path.insert(0, str(ops))
        import ast_price_catalog_apply_once as cli  # noqa: E402

        audit = ROOT / "audit/ast-price-and-catalog-20261024"
        if not (audit / "UPDATE_PRODUCTS.csv").is_file():
            self.skipTest("audit manifests missing")
        with mock.patch.object(cli, "connect_runtime_db") as mock_db:
            mock_db.side_effect = RuntimeError("should not connect on dry run")
            with mock.patch(
                "sys.argv",
                ["prog", "--audit-dir", str(audit)],
            ):
                rc = cli.main()
        self.assertEqual(rc, 0)

    def test_malformed_create_price_rejected(self):
        path = Path(tempfile.mkstemp(suffix=".csv")[1])
        path.write_text(
            "sku,brand_id,category_id,name,base_price,is_available,is_active,apply_eligible,"
            "approval_status,pricing_policy_id,archive_checksum\n"
            f"C1,13,49,name C1,not-a-price,false,true,YES,{CREATE_APPROVAL_OWNER},"
            f"{PRICING_POLICY_ID},{SOURCE_ARCHIVE_SHA256}\n",
            encoding="utf-8",
        )
        with self.assertRaises(ApplyAbort):
            load_create_plan(path, require_owner_approval=True)

    def test_create_batch_avoids_product_service(self):
        import inspect

        from catalog_target.ast_price_catalog_apply import create_products_ast_batch

        src = inspect.getsource(create_products_ast_batch)
        self.assertNotIn("ProductService", src)

    def test_partial_create_failure_aborts(self):
        store = {}
        conn = FakeConn(store)
        creates = [
            CreatePlanRow(sku="A", brand_id=13, category_id=49, name="A x", base_price=Decimal("1")),
            CreatePlanRow(sku="A", brand_id=13, category_id=49, name="A x", base_price=Decimal("1")),
        ]
        with self.assertRaises(ApplyAbort):
            from catalog_target.ast_price_catalog_apply import apply_creates_sql

            apply_creates_sql(conn, creates, dry_run=False)

    def test_manifest_sha_mismatch(self):
        path = Path(tempfile.mkstemp(suffix=".csv")[1])
        path.write_text("sku\nx\n", encoding="utf-8")
        with self.assertRaises(ApplyAbort):
            load_create_plan(path, expected_manifest_sha256="deadbeef", require_owner_approval=False)

    def test_duplicate_update_product_id_rejected(self):
        path = Path(tempfile.mkstemp(suffix=".csv")[1])
        path.write_text(
            "product_id,sku,expected_current_price,proposed_price,validation_result\n"
            "1,A,100,200,OK\n"
            "1,A,100,201,OK\n",
            encoding="utf-8",
        )
        with self.assertRaises(ApplyAbort):
            load_update_plan(path)


if __name__ == "__main__":
    unittest.main()
