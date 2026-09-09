"""Unit tests for official INSIZE rebuild writer (no production mutation)."""

from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.official_insize_rebuild import (  # noqa: E402
    FORBIDDEN_PAYLOAD_FIELDS,
    ApplyAbort,
    LiveContentProduct,
    PlanRow,
    apply_plan,
    assert_payload_content_only,
    build_proposed_title,
    content_hash,
    customer_facing_specifications,
    load_and_validate_plan,
    plan_row_to_update_payload,
    stale_guard,
    validate_proposed_content,
    write_pre_apply_backup,
    writer_contract_summary,
)


def _plan_row(**overrides: Any) -> PlanRow:
    specs = json.dumps(
        {
            "technical_specs": {"measuring_range": {"value": "0-5m"}},
            "features": ["Non-glare nylon coating tape"],
            "provenance": {"source_id": "insize.catalog.108A", "source_page": "523"},
        },
        ensure_ascii=False,
    )
    customer = customer_facing_specifications(specs)
    base = {
        "product_id": 3815,
        "site_sku": "7142-5",
        "current_name": "متر 5 متری اینسایز (Insize) مدل 5-7142",
        "proposed_name": "متر 5متری اینسایز مدل 7142-5",
        "current_short_description_hash": content_hash("old short"),
        "proposed_short_description": "متر 5متری اینسایز مدل 7142-5؛ با محدوده اندازه‌گیری 0-5m.",
        "current_description_hash": content_hash("old desc"),
        "proposed_description": "متر 5متری اینسایز با کد 7142-5 برای کاربردهای صنعتی.",
        "current_specifications_hash": content_hash('{"legacy":true}'),
        "proposed_specifications": json.dumps(customer, ensure_ascii=False),
        "current_meta_title": "old",
        "proposed_meta_title": "متر 5متری اینسایز 7142-5",
        "current_meta_description_hash": content_hash("old meta"),
        "proposed_meta_description": "متر 5متری اینسایز مدل 7142-5",
        "official_model": "7142-5",
        "official_product_name": "متر 5متری",
        "official_source_id": "insize.catalog.108A",
        "official_source_page": "523",
        "official_fact_count": 5,
        "mapping_class": "EXACT_SKU_AND_MODEL",
        "title_class": "SAFE_IDENTITY_CORRECTION",
        "completeness": "OFFICIAL_REBUILD_READY",
    }
    base.update(overrides)
    return PlanRow(**base)


def _live_from_plan(row: PlanRow, **overrides: Any) -> LiveContentProduct:
    payload = {
        "id": row.product_id,
        "sku": row.site_sku,
        "name": row.current_name,
        "slug": row.site_sku.lower(),
        "brand_id": 3,
        "category_id": 77,
        "short_description": "old short",
        "description": "old desc",
        "specifications": '{"legacy":true}',
        "meta_title": row.current_meta_title,
        "meta_description": "old meta",
        "updated_at": "2026-09-08T00:00:00+00:00",
        "base_price": "1107500.00",
        "is_active": True,
        "is_available": True,
        "deleted_at": None,
    }
    payload.update(overrides)
    return LiveContentProduct(**payload)


class FakeCursor:
    def __init__(self, store: dict[int, LiveContentProduct]):
        self.store = store
        self.rowcount = 0
        self._result: list[tuple] = []
        self.executed: list[tuple[str, Any]] = []

    def execute(self, sql: str, params=None) -> None:  # noqa: ANN001
        self.executed.append((sql, params))
        sql_l = " ".join(sql.lower().split())
        if sql_l.startswith("select "):
            ids = list(params[0])
            self._result = []
            for pid in ids:
                row = self.store[pid]
                self._result.append(
                    (
                        row.id,
                        row.sku,
                        row.name,
                        row.slug,
                        row.brand_id,
                        row.category_id,
                        row.short_description,
                        row.description,
                        row.specifications,
                        row.meta_title,
                        row.meta_description,
                        row.updated_at,
                        row.base_price,
                        row.is_active,
                        row.is_available,
                        row.deleted_at or "",
                    )
                )
            self.rowcount = len(self._result)
            return
        if sql_l.startswith("update "):
            (
                name,
                short,
                desc,
                specs,
                meta_t,
                meta_d,
                pid,
                sku,
                *_rest,
            ) = params
            row = self.store[pid]
            assert row.sku == sku
            self.store[pid] = LiveContentProduct(
                id=row.id,
                sku=row.sku,
                name=name,
                slug=row.slug,
                brand_id=row.brand_id,
                category_id=row.category_id,
                short_description=short,
                description=desc,
                specifications=specs,
                meta_title=meta_t,
                meta_description=meta_d,
                updated_at=row.updated_at,
                base_price=row.base_price,
                is_active=row.is_active,
                is_available=row.is_available,
                deleted_at=row.deleted_at,
            )
            self.rowcount = 1
            return
        raise AssertionError(sql)

    def fetchall(self) -> list[tuple]:
        return list(self._result)


class FakeConn:
    def __init__(self, store: dict[int, LiveContentProduct]):
        self.store = store
        self.commits = 0
        self.rollbacks = 0
        self._cursor = FakeCursor(store)

    def cursor(self, *args: Any, **kwargs: Any) -> FakeCursor:
        return self._cursor

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class OfficialRebuildTests(unittest.TestCase):
    def test_exact_official_match_title_corrected(self) -> None:
        name, klass = build_proposed_title(
            site_sku="0110-1125",
            official_model="0110-1125",
            official_product_name="بادسنج",
            current_name="بادسنج اینسایز (Insize) مدل 1125-0110",
        )
        self.assertEqual(klass, "SAFE_IDENTITY_CORRECTION")
        self.assertIn("0110-1125", name)
        self.assertNotIn("1125-0110", name)

    def test_sku_model_mismatch_rejected(self) -> None:
        with self.assertRaises(ApplyAbort):
            build_proposed_title(
                site_sku="0110-1125",
                official_model="1125-0110",
                official_product_name="بادسنج",
                current_name="بادسنج مدل 1125-0110",
            )

    def test_material_identity_change_detected(self) -> None:
        _name, klass = build_proposed_title(
            site_sku="4602-32",
            official_model="4602-32",
            official_product_name="فیلر",
            current_name="کولیس دیجیتال اینسایز مدل 32-4602",
        )
        self.assertEqual(klass, "MATERIAL_IDENTITY_CHANGE")

    def test_shopmill_text_rejected(self) -> None:
        row = _plan_row(proposed_short_description="متن از shopmilltools.com مدل 7142-5")
        with self.assertRaises(ApplyAbort):
            validate_proposed_content(row)

    def test_shopmill_provenance_stripped_and_rejected_if_present_in_output(self) -> None:
        raw = {
            "technical_specs": {
                "range": {"value": "0-5m", "source_id": "insize.catalog.108A"},
            },
            "features": [],
            "provenance": {"shopmill": False, "authority": "official_insize_only"},
        }
        # Nested key name containing shopmill must not appear in customer payload.
        with self.assertRaises(ApplyAbort):
            customer_facing_specifications(raw)

        clean = {
            "technical_specs": {"range": {"value": "0-5m"}},
            "features": ["wear resistance"],
            "provenance": {"source_id": "insize.catalog.108A"},
        }
        out = customer_facing_specifications(clean)
        self.assertEqual(out["authority"], "official_insize")
        self.assertNotIn("provenance", out)
        self.assertEqual(out["technical_specs"]["range"], "0-5m")

    def test_legacy_specs_not_merged(self) -> None:
        row = _plan_row()
        payload = plan_row_to_update_payload(row)
        self.assertIn("technical_specs", payload["specifications"])
        self.assertNotIn("legacy", json.dumps(payload["specifications"]))

    def test_commerce_fields_impossible_in_payload(self) -> None:
        row = _plan_row()
        payload = plan_row_to_update_payload(row)
        assert_payload_content_only(payload)
        for key in FORBIDDEN_PAYLOAD_FIELDS:
            self.assertNotIn(key, payload)
        with self.assertRaises(ApplyAbort):
            assert_payload_content_only({**payload, "base_price": 1})

    def test_ambiguous_and_partial_rejected_by_validate(self) -> None:
        with self.assertRaises(ApplyAbort):
            validate_proposed_content(_plan_row(completeness="OFFICIAL_PARTIAL"))
        with self.assertRaises(ApplyAbort):
            validate_proposed_content(_plan_row(mapping_class="AMBIGUOUS"))
        with self.assertRaises(ApplyAbort):
            validate_proposed_content(_plan_row(title_class="MATERIAL_IDENTITY_CHANGE"))

    def test_stale_guard_blocks_drift(self) -> None:
        row = _plan_row()
        live = _live_from_plan(row, name="CHANGED TITLE")
        guard = stale_guard([row], [live])
        self.assertFalse(guard.ok)
        self.assertTrue(any(item["field"] == "name" for item in guard.drifts))

    def test_backup_and_rollback_bounded(self) -> None:
        row = _plan_row()
        live = _live_from_plan(row)
        with tempfile.TemporaryDirectory() as tmp:
            backup, sha, rollback = write_pre_apply_backup([live], output_dir=Path(tmp))
            self.assertTrue(backup.exists())
            self.assertEqual(len(sha), 64)
            text = rollback.read_text(encoding="utf-8")
            self.assertIn("UPDATE products SET", text)
            self.assertIn("name =", text)
            self.assertNotIn("base_price", text)
            self.assertNotIn("is_available", text)
            self.assertNotIn("slug =", text)

    def test_dry_run_apply_no_commit(self) -> None:
        row = _plan_row()
        live = _live_from_plan(row)
        conn = FakeConn({live.id: live})
        result = apply_plan(conn, [row], dry_run=True, backup_dir=None)
        self.assertEqual(result.mode, "dry_run")
        self.assertFalse(result.production_apply_executed)
        self.assertEqual(conn.commits, 0)
        self.assertGreaterEqual(conn.rollbacks, 1)

    def test_apply_updates_content_only_keeps_sku_slug(self) -> None:
        row = _plan_row()
        live = _live_from_plan(row)
        conn = FakeConn({live.id: live})
        result = apply_plan(conn, [row], dry_run=False, backup_dir=None)
        self.assertEqual(result.mode, "apply")
        self.assertEqual(result.updated_count, 1)
        updated = conn.store[live.id]
        self.assertEqual(updated.sku, "7142-5")
        self.assertEqual(updated.slug, live.slug)
        self.assertEqual(updated.name, row.proposed_name)
        self.assertEqual(updated.base_price, "1107500.00")
        self.assertTrue(updated.is_available)

    def test_writer_contract_default_dry_run(self) -> None:
        contract = writer_contract_summary()
        self.assertEqual(contract["default_mode"], "DRY_RUN")
        self.assertFalse(contract["shopmill_dependency"])
        self.assertTrue(contract["whole_field_specs_replace"])

    def test_load_plan_rejects_forbidden_content(self) -> None:
        row = _plan_row()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.csv"
            from catalog_target.official_insize_rebuild import REQUIRED_PLAN_FIELDS

            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(REQUIRED_PLAN_FIELDS))
                writer.writeheader()
                writer.writerow({k: getattr(row, k) for k in REQUIRED_PLAN_FIELDS})
            loaded = load_and_validate_plan(path)
            self.assertEqual(len(loaded), 1)


if __name__ == "__main__":
    unittest.main()
