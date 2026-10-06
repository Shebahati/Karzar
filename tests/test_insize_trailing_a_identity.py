"""Unit tests for INSIZE trailing-A identity rule (Owner-closed)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.insize_trailing_a_identity import (  # noqa: E402
    MATCH_DETAIL,
    match_catalog_sku_to_source_codes,
    match_source_code_to_catalog_skus,
    strip_exactly_one_terminal_A,
)
from catalog_target.supplier_stock import (  # noqa: E402
    CatalogProduct,
    StockRow,
    ValidationReport,
    map_stock_to_catalog,
)


class InsizeTrailingAIdentityTests(unittest.TestCase):
    def test_valid_trailing_a_match_catalog_to_source(self) -> None:
        res = match_catalog_sku_to_source_codes(
            brand="INSIZE",
            catalog_sku="1120-150",
            source_codes={"1120-150A": ["1120-150A"]},
            catalog_insize_skus=frozenset({"1120-150"}),
        )
        self.assertEqual(res.outcome, "EXACT_MATCH")
        self.assertEqual(res.detail, MATCH_DETAIL)
        self.assertEqual(res.source_sku, "1120-150A")

    def test_valid_trailing_a_match_source_to_catalog(self) -> None:
        catalog = {"1120-150": [SimpleNamespace(sku="1120-150")]}
        res = match_source_code_to_catalog_skus(
            brand="INSIZE",
            source_sku="1120-150A",
            catalog_by_sku=catalog,
        )
        self.assertEqual(res.outcome, "EXACT_MATCH")
        self.assertEqual(res.detail, MATCH_DETAIL)
        self.assertEqual(res.catalog_sku, "1120-150")

    def test_exact_sku_precedence(self) -> None:
        res = match_catalog_sku_to_source_codes(
            brand="INSIZE",
            catalog_sku="1106-1002",
            source_codes={"1106-1002": ["1106-1002"], "1106-1002A": ["1106-1002A"]},
            catalog_insize_skus=frozenset({"1106-1002"}),
        )
        self.assertEqual(res.outcome, "EXACT_MATCH")
        self.assertEqual(res.detail, "EXACT_SKU_PRECEDENCE")
        self.assertEqual(res.source_sku, "1106-1002")

    def test_collision_competing_exact_xa(self) -> None:
        res = match_catalog_sku_to_source_codes(
            brand="INSIZE",
            catalog_sku="X",
            source_codes={"XA": ["XA"]},
            catalog_insize_skus=frozenset({"X", "XA"}),
        )
        self.assertEqual(res.outcome, "AMBIGUOUS")
        self.assertEqual(res.detail, "competing_exact_catalog_XA")

    def test_multiple_candidates_multi_row(self) -> None:
        res = match_catalog_sku_to_source_codes(
            brand="INSIZE",
            catalog_sku="1183-150",
            source_codes={"1183-150A": ["1183-150A", "1183-150A"]},
            catalog_insize_skus=frozenset({"1183-150"}),
        )
        self.assertEqual(res.outcome, "AMBIGUOUS")
        self.assertEqual(res.detail, "multi_row_source_XA")

    def test_internal_a_untouched(self) -> None:
        self.assertIsNone(strip_exactly_one_terminal_A("ABCA123"))
        res = match_catalog_sku_to_source_codes(
            brand="INSIZE",
            catalog_sku="ABCA12",
            source_codes={"ABCA123": ["ABCA123"]},
            catalog_insize_skus=frozenset({"ABCA12"}),
        )
        self.assertEqual(res.outcome, "NOT_FOUND")

    def test_multiple_trailing_chars_not_stripped(self) -> None:
        # AA → strips one A → alias A (not empty); catalog looking for ABC123
        # with source ABC123AA does not match (would need ABC123A not ABC123AA)
        self.assertEqual(strip_exactly_one_terminal_A("ABC123AA"), "ABC123A")
        res = match_catalog_sku_to_source_codes(
            brand="INSIZE",
            catalog_sku="ABC123",
            source_codes={"ABC123AA": ["ABC123AA"]},
            catalog_insize_skus=frozenset({"ABC123"}),
        )
        self.assertEqual(res.outcome, "NOT_FOUND")

    def test_wrong_brand(self) -> None:
        res = match_catalog_sku_to_source_codes(
            brand="DASQUA",
            catalog_sku="1120-150",
            source_codes={"1120-150A": ["1120-150A"]},
            catalog_insize_skus=frozenset({"1120-150"}),
        )
        self.assertEqual(res.outcome, "WRONG_BRAND")

        res2 = match_source_code_to_catalog_skus(
            brand="TERMA",
            source_sku="1120-150A",
            catalog_by_sku={"1120-150": [SimpleNamespace(sku="1120-150")]},
        )
        self.assertEqual(res2.outcome, "WRONG_BRAND")

    def test_mapper_wires_insize_trailing_a(self) -> None:
        row = StockRow(
            source_row=2,
            brand="INSIZE",
            supplier=None,
            manufacturer_sku="1120-150A",
            supplier_sku="",
            model="",
            availability_status_raw="موجود",
            quantity_raw="",
            quantity=None,
            quantity_invalid=False,
            warehouse="",
            source_date_raw="",
            source_version="",
            notes="",
            normalized_status="AVAILABLE",
            identity_key="1120-150A",
        )
        report = ValidationReport(
            source_authority_valid=True,
            input_rows=1,
            unique_identifiers=1,
            duplicate_identifiers=0,
            conflicting_identifiers=0,
            available=1,
            unavailable=0,
            unknown=0,
            blank_status=0,
            invalid_quantity=0,
            unknown_status_values=[],
            source_date_present=False,
            source_date_age_days=34,
            freshness="AGING_BUT_USABLE",
            rows=[row],
        )
        catalog = [
            CatalogProduct(
                product_id="1795",
                brand="INSIZE",
                sku="1120-150",
                model="",
                deleted=False,
            )
        ]
        mapped = map_stock_to_catalog(report, catalog, brand="INSIZE")
        self.assertEqual(len(mapped), 1)
        self.assertEqual(mapped[0].match_class, "EXACT_MATCH")
        self.assertEqual(mapped[0].match_detail, MATCH_DETAIL)
        self.assertEqual(mapped[0].product_id, "1795")


if __name__ == "__main__":
    unittest.main()
