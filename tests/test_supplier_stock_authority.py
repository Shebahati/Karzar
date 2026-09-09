"""Tests for supplier stock authority (read-only; no production mutation)."""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.supplier_stock import (  # noqa: E402
    TERMA_PRICE_EXCEPTION_SKUS,
    CatalogProduct,
    FreshnessPolicy,
    activation_candidates_from_mapping,
    dasqua_pack_a_base,
    file_sha256,
    map_stock_to_catalog,
    normalize_availability_status,
    validate_stock_source,
)


def _write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


class SupplierStockAuthorityTests(unittest.TestCase):
    def test_price_only_row_does_not_imply_availability(self) -> None:
        status, _ = normalize_availability_status(
            status_raw="",
            quantity=None,
            quantity_invalid=False,
            quantity_is_sellable_stock=True,
        )
        self.assertEqual(status, "UNKNOWN")
        # Explicit: no price argument exists on the normalizer.
        self.assertNotIn("price", normalize_availability_status.__code__.co_varnames)

    def test_blank_status_unknown(self) -> None:
        status, unk = normalize_availability_status(
            status_raw="  ",
            quantity=None,
            quantity_invalid=False,
            quantity_is_sellable_stock=False,
        )
        self.assertEqual(status, "UNKNOWN")
        self.assertIsNone(unk)

    def test_quantity_positive_available_only_with_sellable_semantics(self) -> None:
        ok, _ = normalize_availability_status(
            status_raw="",
            quantity=3,
            quantity_invalid=False,
            quantity_is_sellable_stock=True,
        )
        blocked, _ = normalize_availability_status(
            status_raw="",
            quantity=3,
            quantity_invalid=False,
            quantity_is_sellable_stock=False,
        )
        self.assertEqual(ok, "AVAILABLE")
        self.assertEqual(blocked, "UNKNOWN")

    def test_quantity_zero_unavailable(self) -> None:
        status, _ = normalize_availability_status(
            status_raw="",
            quantity=0,
            quantity_invalid=False,
            quantity_is_sellable_stock=True,
        )
        self.assertEqual(status, "UNAVAILABLE")

    def test_unknown_textual_status(self) -> None:
        status, token = normalize_availability_status(
            status_raw="CODE-7",
            quantity=None,
            quantity_invalid=False,
            quantity_is_sellable_stock=True,
        )
        self.assertEqual(status, "UNKNOWN")
        self.assertEqual(token, "CODE-7")

    def test_duplicate_conflicting_sku_source_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "stock.csv"
            _write_csv(
                path,
                ["Brand", "SKU", "Availability", "Last Updated"],
                [
                    ["DASQUA", "1120-3113", "موجود", "2026-09-01"],
                    ["DASQUA", "1120-3113", "ناموجود", "2026-09-01"],
                ],
            )
            report = validate_stock_source(
                path,
                brand="DASQUA",
                source_date_override="2026-09-01",
                today=date(2026, 9, 9),
            )
            self.assertFalse(report.source_authority_valid)
            self.assertGreaterEqual(report.conflicting_identifiers, 1)
            catalog = [
                CatalogProduct(product_id="1", brand="DASQUA", sku="1120-3113", is_active=True)
            ]
            # Force-map even if invalid to exercise conflict class
            report.source_authority_valid = True
            mapped = map_stock_to_catalog(report, catalog, brand="DASQUA")
            self.assertTrue(any(m.match_class == "SOURCE_CONFLICT" for m in mapped))

    def test_fuzzy_model_does_not_match(self) -> None:
        report_rows_catalog = [
            CatalogProduct(product_id="1", brand="TERMA", sku="CB210-150", model="CALIPER-150"),
        ]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "stock.csv"
            _write_csv(
                path,
                ["Brand", "SKU", "Model", "Availability", "Last Updated"],
                [["TERMA", "", "CALIPER", "موجود", "2026-09-01"]],
            )
            report = validate_stock_source(
                path, brand="TERMA", source_date_override="2026-09-01", today=date(2026, 9, 9)
            )
            mapped = map_stock_to_catalog(
                report, report_rows_catalog, brand="TERMA", allow_exact_model=True
            )
            self.assertTrue(all(m.match_class == "NOT_FOUND" for m in mapped))

    def test_cross_brand_sku_cannot_match(self) -> None:
        catalog = [
            CatalogProduct(product_id="1", brand="DASQUA", sku="CB210-150", is_active=True),
        ]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "stock.csv"
            _write_csv(
                path,
                ["Brand", "SKU", "Availability", "Last Updated"],
                [["TERMA", "CB210-150", "موجود", "2026-09-01"]],
            )
            report = validate_stock_source(
                path, brand="TERMA", source_date_override="2026-09-01", today=date(2026, 9, 9)
            )
            mapped = map_stock_to_catalog(report, catalog, brand="TERMA")
            self.assertTrue(all(m.match_class == "NOT_FOUND" for m in mapped))

    def test_stale_source_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "stock.csv"
            _write_csv(
                path,
                ["Brand", "SKU", "Availability", "Last Updated"],
                [["DASQUA", "1120-3113", "موجود", "2025-01-01"]],
            )
            report = validate_stock_source(
                path,
                brand="DASQUA",
                freshness=FreshnessPolicy(current_enough_days=14, aging_but_usable_days=45),
                today=date(2026, 9, 9),
            )
            self.assertEqual(report.freshness, "STALE")
            self.assertFalse(report.source_authority_valid)
            self.assertIn("source_stale", report.deny_reasons)

    def test_source_hash_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "stock.csv"
            _write_csv(
                path,
                ["Brand", "SKU", "Availability", "Last Updated"],
                [["DASQUA", "1120-3113", "موجود", "2026-09-01"]],
            )
            a = file_sha256(path)
            b = file_sha256(path)
            self.assertEqual(a, b)
            report = validate_stock_source(
                path, brand="DASQUA", source_date_override="2026-09-01", today=date(2026, 9, 9)
            )
            self.assertEqual(report.manifest.sha256, a)

    def test_dasqua_suffix_normalization_exact(self) -> None:
        self.assertEqual(dasqua_pack_a_base("1120-3113-A"), "1120-3113")
        self.assertIsNone(dasqua_pack_a_base("1120-3113-B"))
        self.assertIsNone(dasqua_pack_a_base("1120-3113-AB"))
        catalog = [
            CatalogProduct(product_id="9", brand="DASQUA", sku="1120-3113", is_active=True),
        ]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "stock.csv"
            _write_csv(
                path,
                ["Brand", "SKU", "Availability", "Last Updated"],
                [["DASQUA", "1120-3113-A", "موجود", "2026-09-01"]],
            )
            report = validate_stock_source(
                path, brand="DASQUA", source_date_override="2026-09-01", today=date(2026, 9, 9)
            )
            mapped = map_stock_to_catalog(report, catalog, brand="DASQUA")
            self.assertEqual(mapped[0].match_class, "EXACT_MATCH")
            self.assertIn("dasqua_trailing_A", mapped[0].match_detail)

    def test_terma_stock_mapper_does_not_repair_price_exceptions(self) -> None:
        self.assertIn("CDA100-300", TERMA_PRICE_EXCEPTION_SKUS)
        catalog = [
            CatalogProduct(product_id="7", brand="TERMA", sku="CDA100-300", is_active=True),
        ]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "stock.csv"
            _write_csv(
                path,
                ["Brand", "SKU", "Quantity", "Last Updated"],
                [["TERMA", "CDA100-300", "5", "2026-09-01"]],
            )
            report = validate_stock_source(
                path, brand="TERMA", source_date_override="2026-09-01", today=date(2026, 9, 9)
            )
            mapped = map_stock_to_catalog(report, catalog, brand="TERMA")
            self.assertEqual(mapped[0].match_class, "EXACT_MATCH")
            self.assertTrue(mapped[0].price_exception_flag)
            cands = activation_candidates_from_mapping(mapped)
            self.assertEqual(cands, [])

    def test_valid_fresh_source_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "stock.csv"
            _write_csv(
                path,
                ["Brand", "SKU", "Availability", "Last Updated"],
                [["DASQUA", "1120-3113", "موجود", "2026-09-01"]],
            )
            report = validate_stock_source(
                path, brand="DASQUA", today=date(2026, 9, 9)
            )
            self.assertTrue(report.source_authority_valid)
            self.assertEqual(report.available, 1)

    def test_owner_brand_source_inventory_adapters_are_scoped(self) -> None:
        from catalog_target.brand_source_inventory_adapters import (
            DASQUA_GOOGLE_DRIVE_INVENTORY_LIST as D,
        )
        from catalog_target.brand_source_inventory_adapters import (
            TERMA_GOOGLE_DRIVE_INVENTORY_LIST as T,
        )
        from catalog_target.brand_source_inventory_adapters import (
            inventory_status_from_positive_price,
        )

        self.assertEqual(
            inventory_status_from_positive_price(
                adapter_id=D.adapter_id,
                source_path=D.source_path,
                sku="1120-3113",
                price=1,
            ),
            "AVAILABLE",
        )
        self.assertEqual(
            inventory_status_from_positive_price(
                adapter_id=D.adapter_id,
                source_path=D.source_path,
                sku="1120-3113",
                price=0,
            ),
            "UNAVAILABLE",
        )
        # Unresolved TERMA exceptions stay unavailable even with a positive price.
        self.assertEqual(
            inventory_status_from_positive_price(
                adapter_id=T.adapter_id,
                source_path=T.source_path,
                sku="CDA100-300",
                price=999,
            ),
            "UNAVAILABLE",
        )
        with self.assertRaises(ValueError):
            inventory_status_from_positive_price(
                adapter_id=D.adapter_id,
                source_path="/not/the/authorized/path.pdf",
                sku="1120-3113",
                price=1,
            )


if __name__ == "__main__":
    unittest.main()
