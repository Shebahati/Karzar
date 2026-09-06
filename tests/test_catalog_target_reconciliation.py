"""Deterministic tests for READ-ONLY Target Catalog reconciliation."""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
import zipfile
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.core import (  # noqa: E402
    CurrentProduct,
    canonicalize_brand,
    commerce_ready,
    convert_price,
    cross_brand_sku_collisions,
    index_current_products,
    match_brand_sku,
    normalize_sku,
    suffix_near_miss,
)
from catalog_target.reconcile import counts, reconcile, run_reconciliation  # noqa: E402
from catalog_target.snapshot import load_current_catalog, load_snapshot_csv  # noqa: E402
from catalog_target.sources import SourceDiscovery, resolve_source_root  # noqa: E402
from catalog_target.xlsx import iter_xlsx_rows  # noqa: E402


def _write_csv(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def _col(n: int) -> str:
    s = ""
    n += 1
    while n:
        n, rem = divmod(n - 1, 26)
        s = chr(65 + rem) + s
    return s


def _write_xlsx(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    """Minimal shared-string XLSX for tests (no openpyxl)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    strings: list[str] = []
    string_index: dict[str, int] = {}

    def sid(value: str) -> int:
        if value not in string_index:
            string_index[value] = len(strings)
            strings.append(value)
        return string_index[value]

    def cell_xml(r: int, c: int, value: object) -> str:
        ref = f"{_col(c)}{r}"
        if isinstance(value, int | float):
            return f'<c r="{ref}"><v>{value}</v></c>'
        idx = sid(str(value))
        return f'<c r="{ref}" t="s"><v>{idx}</v></c>'

    sheet_cells = []
    for c, header in enumerate(headers):
        sheet_cells.append(cell_xml(1, c, header))
    sheet_rows = [f'<row r="1">{"".join(sheet_cells)}</row>']
    for r, row in enumerate(rows, start=2):
        cells = [cell_xml(r, c, value) for c, value in enumerate(row)]
        sheet_rows.append(f'<row r="{r}">{"".join(cells)}</row>')
    sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData></worksheet>'
    )
    sst_items = "".join(f"<si><t>{s}</t></si>" for s in strings)
    sst = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"{sst_items}</sst>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
        "</Relationships>"
    )
    ctypes = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
        z.writestr("xl/sharedStrings.xml", sst)


def _current(
    sku: str,
    brand: str,
    **kwargs,
) -> CurrentProduct:
    return CurrentProduct(
        id=kwargs.get("id", "1"),
        sku=sku,
        normalized_sku=normalize_sku(sku),
        slug=kwargs.get("slug", sku.lower()),
        name=kwargs.get("name", sku),
        brand_id=kwargs.get("brand_id", "3"),
        brand=brand,
        brand_key=canonicalize_brand(brand),
        category_id=kwargs.get("category_id", "57"),
        base_price=kwargs.get("base_price", Decimal("1000")),
        is_active=kwargs.get("is_active", True),
        is_available=kwargs.get("is_available", True),
        deleted_at=kwargs.get("deleted_at"),
        primary_image_url=kwargs.get("primary_image_url", "https://cdn.example/a.jpg"),
        image_count=kwargs.get("image_count", 1),
        source="test",
    )


class SkuNormalizationTests(unittest.TestCase):
    def test_normalize_strips_space_and_unifies_hyphen(self):
        self.assertEqual(normalize_sku(" 1114-150 "), "1114-150")
        self.assertEqual(normalize_sku("1114–150"), "1114-150")
        self.assertEqual(normalize_sku("abc_1"), "ABC-1")

    def test_distinct_skus_preserved(self):
        self.assertNotEqual(normalize_sku("1114-150"), normalize_sku("1114-150A"))
        self.assertTrue(suffix_near_miss("1114-150", "1114-150A"))
        self.assertFalse(suffix_near_miss("1114-150", "1114-150"))
        self.assertFalse(suffix_near_miss("1103-150", "1114-150"))


class BrandMatchTests(unittest.TestCase):
    def test_exact_brand_sku_match(self):
        products = [_current("1103-150", "INSIZE")]
        index = index_current_products(products)
        hit = match_brand_sku(
            brand_key="INSIZE",
            normalized_sku=normalize_sku("1103-150"),
            index=index,
        )
        self.assertEqual(hit.method, "exact_brand_sku")
        self.assertEqual(hit.current.sku, "1103-150")

    def test_cross_brand_collision_not_auto_matched(self):
        products = [_current("1103-150", "DASQUA", id="9")]
        index = index_current_products(products)
        hit = match_brand_sku(
            brand_key="INSIZE",
            normalized_sku=normalize_sku("1103-150"),
            index=index,
            allow_cross_brand=False,
        )
        self.assertIsNone(hit.current)
        self.assertEqual(hit.method, "none")
        collisions = cross_brand_sku_collisions(
            products + [_current("1103-150", "INSIZE", id="3")]
        )
        self.assertIn("1103-150", collisions)

    def test_ambiguous_alias_stays_review(self):
        products = [
            _current("AAA-1", "INSIZE", id="1"),
            _current("AAA-2", "INSIZE", id="2"),
        ]
        index = index_current_products(products)
        hit = match_brand_sku(
            brand_key="INSIZE",
            normalized_sku=normalize_sku("ALIAS"),
            index=index,
            aliases={("INSIZE", "ALIAS"): "AAA-1"},
        )
        # alias points at AAA-1 uniquely
        self.assertEqual(hit.method, "proven_alias")
        ambiguous = match_brand_sku(
            brand_key="INSIZE",
            normalized_sku=normalize_sku("ALIAS"),
            index=index,
            aliases={("INSIZE", "ALIAS"): "MISSING"},
        )
        self.assertEqual(ambiguous.method, "ambiguous_alias")
        self.assertEqual(ambiguous.review_reason, "ambiguous_alias")


class PriceTests(unittest.TestCase):
    def test_rial_to_toman(self):
        conv = convert_price("100000", currency="rial")
        self.assertEqual(conv.base_price_toman, Decimal("10000"))
        self.assertEqual(conv.conversion, "rial_div_10")
        self.assertIsNone(conv.review_reason)

    def test_never_infer_currency(self):
        conv = convert_price("100000", currency=None)
        self.assertIsNone(conv.base_price_toman)
        self.assertEqual(conv.review_reason, "uncertain_currency")

    def test_zero_and_missing_price_not_commerce_ready(self):
        zero = convert_price("0", currency="toman")
        self.assertEqual(zero.review_reason, "non_positive_price")
        self.assertFalse(
            commerce_ready(
                target_member=True,
                base_price_toman=zero.base_price_toman,
                inventory_available=True,
                review_reason=zero.review_reason,
            )
        )
        missing = convert_price(None, currency="toman")
        self.assertEqual(missing.review_reason, "missing_price")
        self.assertFalse(
            commerce_ready(
                target_member=True,
                base_price_toman=None,
                inventory_available=True,
                review_reason=None,
            )
        )

    def test_prevent_double_markup(self):
        already = convert_price(
            "1100",
            currency="toman",
            markup_already_present=True,
            apply_markup_percent=Decimal("10"),
        )
        self.assertEqual(already.base_price_toman, Decimal("1100"))
        applied = convert_price(
            "1000",
            currency="toman",
            markup_already_present=False,
            apply_markup_percent=Decimal("10"),
        )
        self.assertEqual(applied.base_price_toman, Decimal("1100"))

    def test_membership_not_availability(self):
        self.assertTrue(
            commerce_ready(
                target_member=True,
                base_price_toman=Decimal("10"),
                inventory_available=True,
                review_reason=None,
            )
        )
        self.assertFalse(
            commerce_ready(
                target_member=True,
                base_price_toman=Decimal("10"),
                inventory_available=False,
                review_reason=None,
            )
        )


class SourceAndInsizeTests(unittest.TestCase):
    def test_missing_source_root(self):
        self.assertIsNone(resolve_source_root(None, env={}))
        discovery = SourceDiscovery(source_root=None)
        discovery.discover()
        self.assertTrue(any("INSIZE/product_scope" == u["source"] for u in discovery.unavailable))
        self.assertEqual(discovery.load_product_scope_targets(), [])

    def test_insize_universe_does_not_expand_from_distributor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(
                root / "INSIZE" / "insize_product_list.csv",
                ["CODE", "brand", "product_family"],
                [
                    ["1103-150", "INSIZE", "measurement"],
                    ["1114-150", "INSIZE", "measurement"],
                    ["9722-250", "INSIZE", "measurement"],
                ],
            )
            extra = [[f"X-{i}", "INSIZE", "1000", "toman", "موجود"] for i in range(30)]
            _write_csv(
                root / "INSIZE" / "insize_distributor.csv",
                ["CODE", "brand", "TOMAN", "currency", "وضعیت"],
                [
                    ["1103-150", "INSIZE", "50000", "toman", "موجود"],
                    ["1114-150A", "INSIZE", "60000", "toman", "موجود"],
                    ["9722-250", "INSIZE", "0", "toman", "ناموجود"],
                    *extra,
                ],
            )
            snapshot = root / "current.csv"
            _write_csv(
                snapshot,
                [
                    "id",
                    "sku",
                    "slug",
                    "name",
                    "brand",
                    "category_id",
                    "base_price",
                    "is_active",
                    "is_available",
                    "primary_image_url",
                    "image_count",
                ],
                [
                    ["1", "1103-150", "1103-150", "caliper", "INSIZE", "57", "40000", "true", "true", "https://x/a.jpg", "1"],
                    ["2", "OLD-1", "old-1", "legacy", "INSIZE", "57", "10", "true", "true", "", "0"],
                    ["3", "1103-150", "dup", "dup", "INSIZE", "57", "1", "true", "true", "https://x/a.jpg", "1"],
                ],
            )
            result = run_reconciliation(
                source_root=root,
                output_dir=root / "out",
                baseline_sha="testsha",
                snapshot_path=snapshot,
            )
            self.assertEqual(result.insize.target_sku_count, 3)
            self.assertGreater(result.insize.distributor_row_count, 3)
            self.assertFalse(result.insize.universe_expanded_from_distributor)
            self.assertNotIn("X-0", {t.sku for t in result.target_skus})
            self.assertEqual(result.insize.exact_distributor_matches, 2)  # 1103-150 and 9722-250
            self.assertIn("1114-150", result.insize.unmatched_target_skus)
            self.assertTrue(any(u["sku"] == "1114-150" for u in result.insize.unresolved_identities))
            states = {row.sku: row.reconciliation_state for row in result.rows if row.target_member}
            self.assertEqual(states["1114-150"], "REVIEW")
            self.assertEqual(states["1103-150"], "REVIEW")  # duplicate current SKU
            self.assertEqual(states["9722-250"], "CREATE")
            self.assertFalse(any(r.commerce_ready for r in result.rows if r.sku == "9722-250"))
            deactivate = [r for r in result.rows if r.reconciliation_state == "DEACTIVATE"]
            self.assertTrue(any(r.sku == "OLD-1" for r in deactivate))

    def test_source_precedence_price_does_not_create_membership(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(
                root / "DASQUA" / "dasqua_price+10%.csv",
                ["sku", "brand", "price", "currency"],
                [["1012-0010", "DASQUA", "1100", "toman"]],
            )
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            targets = discovery.load_product_scope_targets()
            self.assertEqual(targets, [])

    def test_duplicate_target_sku_is_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(
                root / "INSIZE" / "insize_product_list.csv",
                ["CODE", "brand"],
                [["1103-150", "INSIZE"], ["1103-150", "INSIZE"]],
            )
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            result = reconcile(
                discovery=discovery,
                current_products=[],
                evidence_kind="unavailable",
                evidence_note="test",
                baseline_sha="x",
            )
            self.assertTrue(all(r.reconciliation_state == "REVIEW" for r in result.rows if r.target_member))

    def test_keep_update_create_deactivate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(
                root / "INSIZE" / "insize_product_list.csv",
                ["CODE", "brand"],
                [["KEEP-1", "INSIZE"], ["UPD-1", "INSIZE"], ["NEW-1", "INSIZE"]],
            )
            _write_csv(
                root / "INSIZE" / "insize_distributor.csv",
                ["CODE", "TOMAN", "وضعیت"],
                [
                    ["KEEP-1", "1000", "موجود"],
                    ["UPD-1", "2000", "موجود"],
                    ["NEW-1", "3000", "موجود"],
                ],
            )
            current = [
                _current("KEEP-1", "INSIZE", id="1", base_price=Decimal("1000"), is_available=True),
                _current("UPD-1", "INSIZE", id="2", base_price=Decimal("1500"), is_available=True),
                _current("GONE-1", "INSIZE", id="3"),
            ]
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            result = reconcile(
                discovery=discovery,
                current_products=current,
                evidence_kind="test",
                evidence_note="test",
                baseline_sha="x",
            )
            by_sku = {r.sku: r for r in result.rows}
            self.assertEqual(by_sku["KEEP-1"].reconciliation_state, "KEEP")
            self.assertEqual(by_sku["UPD-1"].reconciliation_state, "UPDATE")
            self.assertEqual(by_sku["NEW-1"].reconciliation_state, "CREATE")
            self.assertEqual(by_sku["GONE-1"].reconciliation_state, "DEACTIVATE")
            self.assertTrue(by_sku["KEEP-1"].commerce_ready)
            self.assertTrue(by_sku["KEEP-1"].target_member)
            self.assertFalse(by_sku["GONE-1"].target_member)

    def test_xlsx_distributor_join_exact_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(
                root / "INSIZE" / "insize_product_list.csv",
                ["CODE", "brand"],
                [["A-1", "INSIZE"]],
            )
            _write_xlsx(
                root / "INSIZE" / "insize_distributor.xlsx",
                ["CODE", "TOMAN", "وضعیت"],
                [["A-1", 5000, "موجود"], ["A-1B", 8000, "موجود"], ["Z-9", 1, "موجود"]],
            )
            rows = iter_xlsx_rows(root / "INSIZE" / "insize_distributor.xlsx")
            self.assertEqual(len(rows), 3)
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            result = reconcile(
                discovery=discovery,
                current_products=[],
                evidence_kind="unavailable",
                evidence_note="test",
                baseline_sha="x",
            )
            self.assertEqual(result.insize.target_sku_count, 1)
            self.assertEqual(result.insize.exact_distributor_matches, 1)
            self.assertFalse(result.insize.universe_expanded_from_distributor)
            self.assertEqual({t.sku for t in result.target_skus}, {"A-1"})

    def test_snapshot_labeled_non_live(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snap.csv"
            _write_csv(
                path,
                ["id", "sku", "brand", "base_price", "is_active"],
                [["1", "X", "INSIZE", "10", "true"]],
            )
            products, kind = load_snapshot_csv(path)
            self.assertEqual(len(products), 1)
            self.assertEqual(kind, "repository_snapshot_non_live")
            empty, kind2, note = load_current_catalog(read_db=False, env={})
            self.assertEqual(empty, [])
            self.assertEqual(kind2, "unavailable")
            self.assertIn("no_live_db", note)

    def test_cli_forbids_apply(self):
        import subprocess

        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "reconcile_target_catalog.py"), "--apply"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("READ-ONLY", proc.stderr)


class CountInvariantTests(unittest.TestCase):
    def test_exactly_one_state_per_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_csv(
                root / "INSIZE" / "insize_product_list.csv",
                ["CODE", "brand"],
                [["N-1", "INSIZE"]],
            )
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            result = reconcile(
                discovery=discovery,
                current_products=[_current("OTHER", "TERMA")],
                evidence_kind="test",
                evidence_note="test",
                baseline_sha="x",
            )
            states = counts(result)
            self.assertEqual(sum(states.values()), len(result.rows))
            for row in result.rows:
                self.assertIn(row.reconciliation_state, {"KEEP", "UPDATE", "CREATE", "DEACTIVATE", "REVIEW"})


if __name__ == "__main__":
    unittest.main()
