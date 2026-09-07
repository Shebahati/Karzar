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

from catalog_target.apply_contract import StaleSnapshotGuard  # noqa: E402
from catalog_target.core import (  # noqa: E402
    STATES,
    CurrentProduct,
    canonicalize_brand,
    commerce_ready,
    convert_price,
    cross_brand_sku_collisions,
    detect_markup_percent,
    fold_token,
    index_current_products,
    match_brand_sku,
    normalize_sku,
    public_sell_ready,
    suffix_near_miss,
)
from catalog_target.pdf import (  # noqa: E402
    extract_generic_sku_price_rows,
    extract_insize_product_rows,
    extract_pdf_text,
)
from catalog_target.reconcile import (  # noqa: E402
    ManifestRow,
    counts,
    reconcile,
    run_reconciliation,
)
from catalog_target.sales_wave import row_in_insize_sales_wave_1  # noqa: E402
from catalog_target.snapshot import (  # noqa: E402
    PRODUCTS_SNAPSHOT_SELECT_SQL,
    describe_snapshot_phase,
    load_current_catalog,
    load_snapshot_csv,
    select_primary_image_url,
    validate_snapshot_csv,
)
from catalog_target.sources import SourceDiscovery, resolve_source_root  # noqa: E402
from catalog_target.xlsx import iter_xlsx_rows  # noqa: E402

INSIZE_DIR = Path("اندازه گیری") / "اینسایز"
TERMA_DIR = Path("اندازه گیری") / "ترما"
DASQUA_DIR = Path("اندازه گیری") / "داسکوا"
GUANGLU_DIR = Path("اندازه گیری") / "گوانگلو(GL)"
MITUTOYO_DIR = Path("اندازه گیری") / "میتوتویو"
DCOIL_DIR = Path("هلی کویل") / "DCOIL"
SHAMS_DIR = Path("هلی کویل") / "شمس"
AST_POWER = Path("آذرصنعت") / "AST Power"
DUP_TREE = Path("آذرصنعت") / "اد محصول 15 شهریور"


def _insize_list_pdf(root: Path, lines: list[str]) -> Path:
    path = root / INSIZE_DIR / "لیست محصولات.pdf"
    write_text_pdf(path, lines)
    return path


def _insize_distributor(root: Path, rows: list[list[object]]) -> Path:
    path = root / INSIZE_DIR / "موجودی توزیع کننده 11 شهریور - Sheet1 باز.xlsx"
    _write_xlsx(path, ["CODE", "TOMAN", "وضعیت"], rows)
    return path


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


def write_text_pdf(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ops = ["BT /F1 12 Tf 50 720 Td"]
    for i, line in enumerate(lines):
        esc = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if i:
            ops.append("0 -16 Td")
        ops.append(f"({esc}) Tj")
    ops.append("ET")
    stream = "\n".join(ops).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    chunks = [b"%PDF-1.1\n"]
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(sum(len(c) for c in chunks))
        chunks.append(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref_at = sum(len(c) for c in chunks)
    xref = [b"xref\n0 6\n0000000000 65535 f \n"]
    for off in offsets:
        xref.append(f"{off:010d} 00000 n \n".encode())
    chunks.extend(xref)
    chunks.append(
        b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n"
        + str(xref_at).encode()
        + b"\n%%EOF\n"
    )
    path.write_bytes(b"".join(chunks))


def write_image_pdf(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"%PDF-1.1\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] "
        b"/Resources << /XObject << /Im1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
        b"4 0 obj << /Type /XObject /Subtype /Image /Width 1 /Height 1 "
        b"/ColorSpace /DeviceGray /BitsPerComponent 8 /Length 1 >> stream\n"
        b"X\nendstream\nendobj\n"
        b"5 0 obj << /Length 0 >> stream\nendstream\nendobj\n"
        b"trailer << /Root 1 0 R >>\n%%EOF\n"
    )


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

    def test_fold_token_whitespace_and_zwnj(self):
        self.assertEqual(fold_token("قلاویز زن"), fold_token("قلاویززن"))
        self.assertEqual(fold_token("ابزار تیزکن"), fold_token("ابزارتیزکن"))
        self.assertNotEqual(fold_token("مته برگی"), fold_token("مته کف تراش"))


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

    def test_persian_markup_filename_tokens(self):
        self.assertEqual(detect_markup_percent("لیست قیمت داسکوا +10 درصد.pdf"), Decimal("10"))
        self.assertEqual(detect_markup_percent("لیست قیمت ترما +25درصد.pdf"), Decimal("25"))
        self.assertEqual(detect_markup_percent("لیست قیمت DCOIL +10%.pdf"), Decimal("10"))

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
        self.assertTrue(any(u["source"] == "insize.product_list" for u in discovery.unavailable))
        self.assertEqual(discovery.load_product_scope_targets(), [])

    def test_source_root_outside_git_via_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _insize_list_pdf(root, ["1103-150"])
            resolved = resolve_source_root(None, env={"KARZAR_TARGET_SOURCE_DIR": str(root)})
            self.assertEqual(resolved, root.resolve())
            discovery = SourceDiscovery(source_root=resolved)
            discovery.discover()
            skus = {t.sku for t in discovery.load_product_scope_targets()}
            self.assertEqual(skus, {"1103-150"})

    def test_persian_insize_parent_folder_product_list_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = _insize_list_pdf(root, ["1103-150", "1114-150", "9722-250"])
            self.assertEqual(path.name, "لیست محصولات.pdf")
            self.assertEqual(path.parent.name, "اینسایز")
            extracted = extract_pdf_text(path)
            self.assertTrue(extracted.ok)
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            files = [f for f in discovery.files if f.source_id == "insize.product_list"]
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].roles, ["product_scope"])
            targets = discovery.load_product_scope_targets()
            self.assertEqual({t.sku for t in targets}, {"1103-150", "1114-150", "9722-250"})

    def test_insize_universe_does_not_expand_from_distributor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _insize_list_pdf(root, ["1103-150", "1114-150", "9722-250"])
            extra = [[f"880{i}-01", 1000, "موجود"] for i in range(30)]
            _insize_distributor(
                root,
                [
                    ["1103-150", 50000, "موجود"],
                    ["1114-150A", 60000, "موجود"],
                    ["9722-250", 0, "ناموجود"],
                    ["1103-151", 10, "موجود"],
                    ["9722-251", 8000, "ناموجود"],
                    *extra,
                ],
            )
            snapshot = root / "current.csv"
            _write_csv(
                snapshot,
                [
                    "id",
                    "sku",
                    "brand_id",
                    "brand",
                    "category_id",
                    "slug",
                    "name",
                    "base_price",
                    "is_active",
                    "is_available",
                    "deleted_at",
                    "primary_image_url",
                    "image_count",
                ],
                [
                    ["1", "1103-150", "3", "INSIZE", "57", "1103-150", "caliper", "40000", "true", "true", "", "https://x/a.jpg", "1"],
                    ["2", "OLD-1", "3", "INSIZE", "57", "old-1", "legacy", "10", "true", "true", "", "", "0"],
                    ["3", "1103-150", "3", "INSIZE", "57", "dup", "dup", "1", "true", "true", "", "https://x/a.jpg", "1"],
                ],
            )
            result = run_reconciliation(
                source_root=root,
                output_dir=root / "out",
                baseline_sha="testsha",
                snapshot_path=snapshot,
                expected_snapshot_rows=3,
            )
            self.assertEqual(result.insize.target_sku_count, 3)
            self.assertEqual(result.insize.unique_sku_count, 3)
            self.assertGreater(result.insize.distributor_row_count, 3)
            self.assertFalse(result.insize.universe_expanded_from_distributor)
            self.assertNotIn("8800-01", {t.sku for t in result.target_skus})
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
            self.assertEqual(result.insize.available_positive_price, ["1103-150"])
            self.assertEqual(result.insize.available_missing_zero_price, [])
            self.assertEqual(result.insize.unavailable_positive_price, [])

    def test_generic_price_file_cannot_become_membership(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text_pdf(
                root / INSIZE_DIR / "لیست قیمت اینسایز +10 درصد.pdf",
                ["1103-150 50000"],
            )
            _write_csv(
                root / "misc" / "price_list+10%.csv",
                ["sku", "brand", "price", "currency"],
                [["1012-0010", "DASQUA", "1100", "toman"]],
            )
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            targets = discovery.load_product_scope_targets()
            self.assertEqual(targets, [])

    def test_explicit_dual_role_product_scope_and_price(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text_pdf(
                root / DASQUA_DIR / "لیست قیمت داسکوا +10 درصد.pdf",
                ["1012-0010 11000 rial"],
            )
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            dasqua = [f for f in discovery.files if f.source_id == "dasqua.price_list"]
            self.assertEqual(len(dasqua), 1)
            self.assertEqual(set(dasqua[0].roles), {"product_scope", "price"})
            result = reconcile(
                discovery=discovery,
                current_products=[],
                evidence_kind="test",
                evidence_note="test",
                baseline_sha="x",
            )
            self.assertEqual({t.sku for t in result.target_skus}, {"1012-0010"})
            row = next(r for r in result.rows if r.sku == "1012-0010")
            self.assertEqual(row.base_price_toman, "1100")
            self.assertFalse(row.commerce_ready)

    def test_markup_already_applied_plus_10_and_plus_25(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text_pdf(
                root / DASQUA_DIR / "لیست قیمت داسکوا +10 درصد.pdf",
                ["1012-0010 11000 rial"],
            )
            write_text_pdf(
                root / TERMA_DIR / "لیست قیمت ترما +25درصد.pdf",
                ["TR-100 250000 rial"],
            )
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            result = reconcile(
                discovery=discovery,
                current_products=[],
                evidence_kind="test",
                evidence_note="test",
                baseline_sha="x",
            )
            by_sku = {r.sku: r for r in result.rows if r.target_member}
            self.assertEqual(by_sku["1012-0010"].base_price_toman, "1100")
            self.assertNotEqual(by_sku["1012-0010"].base_price_toman, "1210")
            self.assertEqual(by_sku["TR-100"].base_price_toman, "25000")
            self.assertNotEqual(by_sku["TR-100"].base_price_toman, "31250")

    def test_terma_ignores_jaw_and_letter_only_tokens(self):
        from catalog_target.pdf import extract_terma_rows

        parsed = extract_terma_rows(
            "\n".join(
                [
                    "62.000.000 کولیس 15سانت ساعتی CB210-150 jaw90 1",
                    "WTG hardness",
                    "SHORE A 1",
                ]
            ),
            default_currency="rial",
        )
        skus = [row["sku"] for row in parsed.rows]
        self.assertEqual(skus, ["CB210-150"])

    def test_cross_brand_price_is_not_joined(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _insize_list_pdf(root, ["7111-1000"])
            write_text_pdf(
                root / DASQUA_DIR / "لیست قیمت داسکوا +10 درصد.pdf",
                ["76,250,000 0-150mm 7111-1000 1"],
            )
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            result = reconcile(
                discovery=discovery,
                current_products=[],
                evidence_kind="test",
                evidence_note="test",
                baseline_sha="x",
            )
            insize = next(r for r in result.rows if r.brand == "INSIZE" and r.sku == "7111-1000")
            self.assertEqual(insize.source_price, "")
            self.assertNotIn("داسکوا", insize.source_price)

    def test_dcoil_keeps_full_identity_after_coil(self):
        from catalog_target.pdf import extract_dcoil_rows

        parsed = extract_dcoil_rows(
            "\n".join(
                [
                    "1 کيت هلی کوئل d.coil M2-0.40 ﷼ 29,900,000",
                    "2 فنر d.coilM2-0.40-1.5D ﷼ 4,500,000",
                    "3 d.coil M10 UNC ﷼ 12,000,000",
                ]
            ),
            default_currency="rial",
        )
        skus = [row["sku"] for row in parsed.rows]
        self.assertEqual(skus, ["M2-0.40", "M2-0.40-1.5D", "M10 UNC"])

    def test_dcoil_zero_price_not_commerce_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text_pdf(
                root / DCOIL_DIR / "لیست قیمت DCOIL +10%.pdf",
                ["DC-100 0 rial", "DC-200 10000 rial"],
            )
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            result = reconcile(
                discovery=discovery,
                current_products=[],
                evidence_kind="test",
                evidence_note="test",
                baseline_sha="x",
            )
            by_sku = {r.sku: r for r in result.rows if r.target_member}
            self.assertIn("DC-100", by_sku)
            self.assertFalse(by_sku["DC-100"].commerce_ready)
            self.assertFalse(by_sku["DC-200"].commerce_ready)

    def test_duplicate_target_sku_is_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _insize_list_pdf(root, ["1103-150", "1103-150"])
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            result = reconcile(
                discovery=discovery,
                current_products=[],
                evidence_kind="unavailable",
                evidence_note="test",
                baseline_sha="x",
            )
            members = [r for r in result.rows if r.target_member]
            self.assertEqual(len(members), 1)
            self.assertEqual(members[0].reconciliation_state, "REVIEW")
            self.assertEqual(result.insize.unique_sku_count, 1)
            self.assertIn("1103-150", result.duplicate_scope_skus)

    def test_keep_update_create_deactivate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _insize_list_pdf(root, ["1108-25", "1114-150", "1234-56"])
            _insize_distributor(
                root,
                [
                    ["1108-25", 1000, "موجود"],
                    ["1114-150", 2000, "موجود"],
                    ["1234-56", 3000, "موجود"],
                ],
            )
            current = [
                _current("1108-25", "INSIZE", id="1", base_price=Decimal("1000"), is_available=True),
                _current("1114-150", "INSIZE", id="2", base_price=Decimal("1500"), is_available=True),
                _current("9999-99", "INSIZE", id="3"),
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
            self.assertEqual(by_sku["1108-25"].reconciliation_state, "KEEP")
            self.assertEqual(by_sku["1114-150"].reconciliation_state, "UPDATE")
            self.assertEqual(by_sku["1234-56"].reconciliation_state, "CREATE")
            self.assertEqual(by_sku["9999-99"].reconciliation_state, "DEACTIVATE")
            self.assertTrue(by_sku["1108-25"].commerce_ready)
            self.assertTrue(by_sku["1108-25"].target_member)
            self.assertFalse(by_sku["9999-99"].target_member)

    def test_inactive_non_target_is_noop_not_deactivate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _insize_list_pdf(root, ["1108-25"])
            _insize_distributor(root, [["1108-25", 1000, "موجود"]])
            current = [
                _current("1108-25", "INSIZE", id="1", base_price=Decimal("1000"), is_available=True),
                _current("ACTIVE-OUT", "INSIZE", id="2", is_active=True),
                _current("INACTIVE-OUT", "INSIZE", id="3", is_active=False),
                _current("DELETED-OUT", "INSIZE", id="4", is_active=True, deleted_at="2026-01-01"),
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
            self.assertEqual(by_sku["ACTIVE-OUT"].reconciliation_state, "DEACTIVATE")
            self.assertEqual(by_sku["INACTIVE-OUT"].reconciliation_state, "NOOP_INACTIVE_NON_TARGET")
            self.assertNotIn("DELETED-OUT", by_sku)
            self.assertEqual(counts(result)["DEACTIVATE"], 1)
            self.assertEqual(counts(result)["NOOP_INACTIVE_NON_TARGET"], 1)

    def test_primary_image_prefers_is_primary_then_display_order(self):
        self.assertIn("is_primary DESC", PRODUCTS_SNAPSHOT_SELECT_SQL)
        self.assertIn("display_order ASC", PRODUCTS_SNAPSHOT_SELECT_SQL)
        images = [
            {"id": 1, "is_primary": False, "display_order": 0, "image_url": "first-by-id.jpg"},
            {"id": 5, "is_primary": True, "display_order": 9, "image_url": "primary.jpg"},
            {"id": 2, "is_primary": False, "display_order": 1, "image_url": "second.jpg"},
        ]
        self.assertEqual(select_primary_image_url(images), "primary.jpg")
        no_primary = [
            {"id": 10, "is_primary": False, "display_order": 2, "image_url": "later.jpg"},
            {"id": 11, "is_primary": False, "display_order": 0, "image_url": "earlier-order.jpg"},
            {"id": 9, "is_primary": False, "display_order": 0, "image_url": "same-order-lower-id.jpg"},
        ]
        self.assertEqual(select_primary_image_url(no_primary), "same-order-lower-id.jpg")
        self.assertEqual(select_primary_image_url([]), None)

    def test_snapshot_validation_requires_columns_and_row_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snap.csv"
            headers = list(
                [
                    "id",
                    "sku",
                    "brand_id",
                    "brand",
                    "category_id",
                    "slug",
                    "name",
                    "base_price",
                    "is_active",
                    "is_available",
                    "deleted_at",
                    "primary_image_url",
                    "image_count",
                ]
            )
            _write_csv(
                path,
                headers,
                [
                    ["1", "A-1", "3", "INSIZE", "57", "a-1", "A", "1000", "true", "true", "", "https://x/a.jpg", "1"],
                    ["2", "B-1", "3", "INSIZE", "57", "b-1", "B", "0", "false", "false", "", "", "0"],
                ],
            )
            ok = validate_snapshot_csv(path, expected_row_count=2)
            self.assertTrue(ok.valid)
            bad = validate_snapshot_csv(path, expected_row_count=99)
            self.assertFalse(bad.valid)
            self.assertTrue(bad.truncation_suspected)

    def test_inactive_target_proposes_active_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _insize_list_pdf(root, ["1108-25"])
            _insize_distributor(root, [["1108-25", 1000, "موجود"]])
            current = [
                _current(
                    "1108-25",
                    "INSIZE",
                    id="1",
                    base_price=Decimal("1000"),
                    is_available=True,
                    is_active=False,
                )
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
            row = next(r for r in result.rows if r.sku == "1108-25")
            self.assertEqual(row.reconciliation_state, "UPDATE")
            self.assertIs(row.current_is_active, False)
            self.assertIs(row.proposed_is_active, True)
            self.assertEqual(row.is_active_change, "true")

    def test_deleted_target_match_is_review_not_resurrected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _insize_list_pdf(root, ["1108-25"])
            _insize_distributor(root, [["1108-25", 1000, "موجود"]])
            current = [
                _current(
                    "1108-25",
                    "INSIZE",
                    id="1",
                    base_price=Decimal("1000"),
                    is_available=True,
                    is_active=False,
                    deleted_at="2026-01-01",
                )
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
            row = next(r for r in result.rows if r.sku == "1108-25")
            self.assertEqual(row.reconciliation_state, "REVIEW")
            self.assertIn("deleted_current_match", row.review_reason)
            self.assertIsNone(row.proposed_is_active)
            ok, reasons = row_in_insize_sales_wave_1(row)
            self.assertFalse(ok)
            self.assertTrue(any("review" in r or "deleted" in r for r in reasons))

    def test_public_sell_ready_requires_media(self):
        self.assertTrue(
            public_sell_ready(target_member=True, commerce_ready_flag=True, media_ready_flag=True)
        )
        self.assertFalse(
            public_sell_ready(target_member=True, commerce_ready_flag=True, media_ready_flag=False)
        )
        self.assertFalse(
            public_sell_ready(target_member=True, commerce_ready_flag=False, media_ready_flag=True)
        )

    def test_commerce_ready_no_media_excluded_from_insize_sales_wave(self):
        row = ManifestRow(
            brand="INSIZE",
            sku="1108-25",
            normalized_sku="1108-25",
            product_family="measurement",
            target_member=True,
            source_scope="product_scope",
            source_product="x",
            inventory_status="موجود",
            commerce_ready=True,
            media_ready=False,
            public_sell_ready=False,
            reconciliation_state="UPDATE",
            current_id="1",
            proposed_base_price="1000",
            proposed_is_available=True,
            proposed_is_active=True,
            exact_distributor_match=True,
        )
        ok, reasons = row_in_insize_sales_wave_1(row)
        self.assertFalse(ok)
        self.assertIn("not_media_ready", reasons)

    def test_review_excluded_from_insize_sales_wave(self):
        row = ManifestRow(
            brand="INSIZE",
            sku="1108-25",
            normalized_sku="1108-25",
            product_family="measurement",
            target_member=True,
            source_scope="product_scope",
            source_product="x",
            inventory_status="موجود",
            commerce_ready=False,
            media_ready=True,
            public_sell_ready=False,
            reconciliation_state="REVIEW",
            review_reason="suffix_mismatch",
            current_id="1",
            proposed_base_price="1000",
            proposed_is_available=True,
            proposed_is_active=True,
            exact_distributor_match=True,
        )
        ok, reasons = row_in_insize_sales_wave_1(row)
        self.assertFalse(ok)
        self.assertIn("review_blocked", reasons)

    def test_create_not_in_insize_sales_wave(self):
        row = ManifestRow(
            brand="INSIZE",
            sku="NEW-1",
            normalized_sku="NEW-1",
            product_family="measurement",
            target_member=True,
            source_scope="product_scope",
            source_product="x",
            inventory_status="موجود",
            commerce_ready=True,
            media_ready=False,
            public_sell_ready=False,
            reconciliation_state="CREATE",
            proposed_base_price="1000",
            proposed_is_available=True,
            proposed_is_active=True,
            exact_distributor_match=True,
        )
        ok, reasons = row_in_insize_sales_wave_1(row)
        self.assertFalse(ok)
        self.assertIn("create_excluded_from_sales_wave_1", reasons)

    def test_stale_snapshot_guard_contract(self):
        guard = StaleSnapshotGuard()
        payload = guard.as_dict()
        self.assertEqual(payload["on_mismatch"], "ABORT_BEFORE_MUTATION")
        self.assertFalse(payload["partial_apply_allowed"])
        self.assertFalse(payload["writer_implemented"])
        self.assertIn("id", payload["required_live_fields"])
        self.assertIn("base_price", payload["required_live_fields"])

    def test_xlsx_distributor_join_exact_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _insize_list_pdf(root, ["1103-150"])
            dist = _insize_distributor(
                root,
                [["1103-150", 5000, "موجود"], ["1103-150A", 8000, "موجود"], ["9999-01", 1, "موجود"]],
            )
            rows = iter_xlsx_rows(dist)
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
            self.assertEqual({t.sku for t in result.target_skus}, {"1103-150"})

    def test_ast_approved_enumerator_confers_membership(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text_pdf(
                root / AST_POWER / "مته برگی" / "لیست قیمت.pdf",
                ["MB-100 5000 rial"],
            )
            write_text_pdf(
                root / AST_POWER / "قلاویززن بادی" / "لیست قیمت.pdf",
                ["QT-100 8000 rial"],
            )
            write_text_pdf(
                root / DUP_TREE / "مته برگی" / "لیست قیمت.pdf",
                ["MB-100 5000 rial"],
            )
            write_text_pdf(
                root / AST_POWER / "مته کف تراش" / "لیست قیمت.pdf",
                ["KT-100 9000 rial"],
            )
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            targets = discovery.load_product_scope_targets()
            skus = {t.sku for t in targets}
            self.assertIn("MB-100", skus)
            self.assertIn("QT-100", skus)
            self.assertNotIn("KT-100", skus)
            self.assertEqual(sum(1 for t in targets if t.sku == "MB-100"), 1)
            self.assertTrue(any("اد محصول 15 شهریور" in p for p in discovery.skipped_duplicates))
            families = {t.sku: t.product_family for t in targets}
            self.assertEqual(families["MB-100"], "spade_drills")
            self.assertEqual(families["QT-100"], "pneumatic_tapping")

    def test_ast_arbitrary_pdf_cannot_confer_membership(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text_pdf(root / AST_POWER / "مته برگی" / "notes.pdf", ["MB-100 5000 rial"])
            write_text_pdf(root / AST_POWER / "مته برگی" / "کاتالوگ.pdf", ["MB-200 8000 rial"])
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            skus = {t.sku for t in discovery.load_product_scope_targets()}
            self.assertEqual(skus, set())
            self.assertFalse(
                any(u["reason"] == "AUTHORITY_GAP" for u in discovery.unavailable)
            )
            report = next(r for r in discovery.ast_reports if r.get("family") == "spade_drills")
            self.assertEqual(report.get("membership_result"), "not_membership_in_current_source")
            self.assertEqual(report.get("membership_authority"), "not_membership")
            unclassified = [f for f in discovery.files if "unclassified" in (f.roles or [])]
            catalog = [f for f in discovery.files if f.roles == ["catalog"]]
            self.assertTrue(unclassified)
            self.assertTrue(catalog)

    def test_ast_hamkari_enumerator_and_catalog_non_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text_pdf(
                root / AST_POWER / "مته برگی" / "همکاری مته برگی.pdf",
                ["MB-100 5000 rial"],
            )
            write_text_pdf(
                root / AST_POWER / "قلاویز ET" / "ET همکاری.pdf",
                ["ET-200 8000 rial"],
            )
            write_text_pdf(
                root / AST_POWER / "روغن آب صابون" / "کاتالوگ همکاری.pdf",
                ["CF-300 9000 rial"],
            )
            write_text_pdf(
                root / AST_POWER / "قلاویززن برقی" / "همکاری قلاویززن برقی.pdf",
                ["This brochure has no manufacturer codes."],
            )
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            skus = {t.sku: t.product_family for t in discovery.load_product_scope_targets()}
            self.assertEqual(skus.get("MB-100"), "spade_drills")
            self.assertNotIn("ET-200", skus)
            self.assertNotIn("CF-300", skus)
            et = next(r for r in discovery.ast_reports if r.get("family") == "et_taps")
            self.assertEqual(et.get("membership_result"), "catalog_datasheet_no_stable_product_identity")
            self.assertEqual(et.get("membership_authority"), "not_membership")
            self.assertTrue(
                any(
                    r.get("family") == "electric_tapping"
                    and r.get("membership_result") == "enumerator_candidate_unparsed"
                    for r in discovery.ast_reports
                )
            )

    def test_ast_enumerator_filename_splits_combined_folder_and_ignores_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            combined = root / AST_POWER / "دریل مگنت و کرگیری"
            write_text_pdf(combined / "همکاری دریل مگنت.pdf", ["MD-100 5000 rial"])
            write_text_pdf(combined / "همکاری کرگیری.pdf", ["CD-100 8000 rial"])
            jpg = combined / "کاتالوگ همکاری" / "همکاری TRM.jpg"
            jpg.parent.mkdir(parents=True, exist_ok=True)
            jpg.write_bytes(b"\xff\xd8\xff")
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            skus = {t.sku: t.product_family for t in discovery.load_product_scope_targets()}
            self.assertNotIn("MD-100", skus)
            self.assertNotIn("CD-100", skus)
            magnetic = next(r for r in discovery.ast_reports if r.get("family") == "magnetic_drill")
            core = next(r for r in discovery.ast_reports if r.get("family") == "core_drill")
            self.assertEqual(magnetic.get("membership_result"), "catalog_datasheet_no_stable_product_identity")
            self.assertEqual(core.get("membership_result"), "catalog_datasheet_no_stable_product_identity")
            self.assertEqual(magnetic.get("membership_authority"), "not_membership")
            self.assertTrue(any(Path(p).name == "همکاری دریل مگنت.pdf" for p in magnetic["enumerator_candidates"]))
            self.assertTrue(any(Path(p).name == "همکاری کرگیری.pdf" for p in core["enumerator_candidates"]))
            self.assertFalse(any(p.lower().endswith(".jpg") for p in magnetic["enumerator_candidates"]))
            self.assertFalse(any(p.lower().endswith(".jpg") for p in core["enumerator_candidates"]))

    def test_ast_image_code_table_promotes_verified_skus_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_image_pdf(root / AST_POWER / "قلاویززن اتومات" / "همکاری قلاویززن اتومات.pdf")
            write_image_pdf(root / AST_POWER / "قلاویززن برقی" / "کاتالوگ.pdf")
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            skus = {t.sku: t.product_family for t in discovery.load_product_scope_targets()}
            self.assertEqual(skus.get("AST-GAT7"), "automatic_tapping")
            self.assertEqual(skus.get("AST-GAT20"), "automatic_tapping")
            self.assertNotIn("AST-TRM10", skus)
            report = next(r for r in discovery.ast_reports if r.get("family") == "automatic_tapping")
            self.assertEqual(report.get("membership_result"), "product_scope_conferred")
            self.assertTrue(
                any(
                    rec.get("decision") == "promote_target_member_review" and rec.get("raw_sku") == "AST-GAT7"
                    for rec in discovery.ast_review_rows
                )
            )

    def test_ast_duplicate_tree_only_enumerator_is_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text_pdf(
                root / DUP_TREE / "مته برگی" / "همکاری مته برگی.pdf",
                ["MB-400 5000 rial"],
            )
            (root / AST_POWER / "مته برگی").mkdir(parents=True, exist_ok=True)
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            targets = discovery.load_product_scope_targets()
            self.assertEqual({t.sku for t in targets}, {"MB-400"})
            report = next(r for r in discovery.ast_reports if r.get("family") == "spade_drills")
            self.assertEqual(report.get("duplicate_original_relationship"), "duplicate_tree_only")

    def test_wave1_ready_when_guanglu_deferred_and_insize_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _insize_list_pdf(root, ["1108-150"])
            write_text_pdf(
                root / GUANGLU_DIR / "لیست قیمت گوانگلو(GL).pdf",
                ["GL 60 37,000,000", "! # $ 30 88,000,000"],
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
            self.assertTrue(result.source_tree_valid)
            self.assertTrue(result.partial_target_manifest_valid)
            self.assertTrue(result.target_manifest_ready)
            self.assertEqual(result.target_manifest_scope, "WAVE_1_RESOLVED_AUTHORITIES")
            self.assertEqual(result.deferred_authorities, ["guanglu.price_list"])
            self.assertFalse(any(b.get("source") == "guanglu.price_list" for b in result.unresolved_blockers))
            self.assertFalse(result.apply_ready)
            self.assertFalse(result.current_site_reconciliation_ready)

    def test_full_manifest_ready_false_when_required_brand_unresolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_image_pdf(root / INSIZE_DIR / "لیست محصولات.pdf")
            write_text_pdf(
                root / GUANGLU_DIR / "لیست قیمت گوانگلو(GL).pdf",
                ["GL 60 37,000,000"],
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
            self.assertTrue(result.source_tree_valid)
            self.assertFalse(result.target_manifest_ready)
            self.assertTrue(
                any(b.get("source") == "insize.product_list" for b in result.unresolved_blockers)
            )
            self.assertFalse(any(b.get("source") == "guanglu.price_list" for b in result.unresolved_blockers))

    def test_scanned_pdf_is_unparsed_not_zero_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / INSIZE_DIR / "لیست محصولات.pdf"
            write_image_pdf(path)
            extracted = extract_pdf_text(path)
            self.assertFalse(extracted.ok)
            self.assertIn(extracted.status, {"unparsed_image", "unparsed_empty"})
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            targets = discovery.load_product_scope_targets()
            self.assertEqual(targets, [])
            self.assertTrue(discovery.unparsed)
            self.assertTrue(discovery.parse_failures)
            result = reconcile(
                discovery=discovery,
                current_products=[],
                evidence_kind="unavailable",
                evidence_note="test",
                baseline_sha="x",
            )
            self.assertTrue(result.unparsed)
            self.assertTrue(result.parse_failures)

    def test_pdf_parse_failure_is_surfaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / INSIZE_DIR / "لیست محصولات.pdf"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"this is not a pdf")
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            self.assertEqual(discovery.load_product_scope_targets(), [])
            self.assertTrue(discovery.unparsed or discovery.parse_failures)
            statuses = {f.parse_status for f in discovery.files if f.source_id == "insize.product_list"}
            self.assertTrue(statuses)
            self.assertNotIn("ok", statuses)

    def test_text_pdf_with_no_skus_is_unparsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text_pdf(root / INSIZE_DIR / "لیست محصولات.pdf", ["Price list header only"])
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            discovery.load_product_scope_targets()
            self.assertTrue(discovery.unparsed)
            self.assertTrue(discovery.parse_failures)

    def test_shams_scanned_does_not_create_products(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_image_pdf(root / SHAMS_DIR / "کاتالوگ شمس.pdf")
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            skus = {t.sku for t in discovery.load_product_scope_targets()}
            self.assertEqual(skus, set())
            self.assertTrue(
                any(d.get("source") == "shams.catalog" and d.get("class") == "A" for d in discovery.authority_decisions)
            )
            self.assertTrue(discovery.unparsed)

    def test_mitutoyo_catalog_only_unresolved_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text_pdf(root / MITUTOYO_DIR / "کاتالوگ میتوتویو.pdf", ["103-137 5000"])
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            self.assertEqual(discovery.load_product_scope_targets(), [])
            self.assertTrue(
                any(d.get("source") == "mitutoyo.catalog" and d.get("class") == "A" for d in discovery.authority_decisions)
            )

    def test_guanglu_has_no_manufacturer_sku_column(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text_pdf(
                root / GUANGLU_DIR / "لیست قیمت گوانگلو(GL).pdf",
                ["GL 60 37,000,000", "TG 1-10 21,160,000", "150 stainless GL 50,000,000"],
            )
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            targets = discovery.load_product_scope_targets()
            self.assertEqual({t.sku for t in targets if t.brand_key == "GUANGLU"}, set())
            self.assertTrue(discovery.guanglu_evidence)
            result = reconcile(
                discovery=discovery,
                current_products=[],
                evidence_kind="test",
                evidence_note="test",
                baseline_sha="x",
            )
            self.assertFalse(any(r.brand == "GUANGLU" and r.target_member for r in result.rows))
            self.assertFalse(any(b.get("source") == "guanglu.price_list" for b in result.unresolved_blockers))
            self.assertEqual(result.deferred_authorities, ["guanglu.price_list"])
            self.assertTrue(
                any(d.get("source") == "guanglu.price_list" and d.get("class") == "C" for d in discovery.authority_decisions)
            )

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
            phase = describe_snapshot_phase()
            self.assertEqual(phase["status"], "prepared_not_run")
            self.assertTrue(phase["read_only"])
            self.assertFalse(phase["CURRENT_SITE_RECONCILIATION_READY"])
            self.assertFalse(phase["APPLY_READY"])
            for field in (
                "id",
                "sku",
                "brand_id",
                "brand",
                "category_id",
                "slug",
                "name",
                "base_price",
                "is_active",
                "is_available",
                "deleted_at",
            ):
                self.assertIn(field, phase["required_fields"])

    def test_cli_forbids_apply(self):
        import subprocess

        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "reconcile_target_catalog.py"), "--apply"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("READ-ONLY", proc.stderr)


class InsizeRowStructureTests(unittest.TestCase):
    def test_non_numeric_hyphen_and_bare_codes(self):
        parsed = extract_insize_product_rows(
            "\n".join(
                [
                    "CODE DESCRIPTION RANGE",
                    "1108-150 Digital Caliper 0-150mm",
                    "ISH-R150 Radius gauge",
                    "58698 Accessory block",
                    "7323",
                    "1114-150A Dial caliper",
                    "0/01 mm 2,250,000 Digital caliper 15cm 1108-200 222",
                    "0/01 mm 13,150,000 1110-150A diamond jaws 235",
                    "0/01 mm 4,200,000 1110-150Aکولیس 236",
                    "0/02 mm 1,800,000 1180-6 12",
                    "ISH-PHB hardness tester 40",
                    "ISH-TDV-1000 41",
                    "0/01 mm 1,000,000 - 934",
                ]
            )
        )
        skus = {row["sku"] for row in parsed.rows}
        self.assertEqual(
            skus,
            {
                "1108-150",
                "ISH-R150",
                "58698",
                "7323",
                "1114-150A",
                "1108-200",
                "1110-150A",
                "1180-6",
                "ISH-PHB",
                "ISH-TDV-1000",
            },
        )

    def test_dimensions_and_page_numbers_are_not_skus(self):
        parsed = extract_insize_product_rows(
            "\n".join(
                [
                    "Page 12",
                    "12",
                    "0-150mm",
                    "0-200",
                    "150mm",
                    "2024",
                    "1108-150 Digital Caliper 0-150mm Page 3",
                ]
            )
        )
        skus = [row["sku"] for row in parsed.rows]
        self.assertEqual(skus, ["1108-150"])
        self.assertNotIn("12", skus)
        self.assertNotIn("0-150mm", skus)
        self.assertNotIn("0-200", skus)
        self.assertNotIn("150mm", skus)
        self.assertNotIn("2024", skus)

    def test_real_table_rows_and_false_bare_1000(self):
        parsed = extract_insize_product_rows(
            "\n".join(
                [
                    "Page 50 of 50",
                    "0/01 mm 27,130,000 3222-1000میکرومتر داخل لوله ای 50 - 1000 102",
                    "0/005 mm 105,660,000 3227-1004میکرومتر داخل سه فک 50 - 100 129",
                    "0/01 mm 7,040,000 3230-25BAمیکرومتر سوزنی 0 - 25 170",
                    "0/01 mm 3,970,000 3260-25SAمیکرومتر لوله 0 - 25 173",
                    "0/01 mm ,000 ضخامت سنج پایه دار دیجیتال 2673-10 459",
                    "0/02 mm ,000 تراز صنعتی دیجیتال تخت 20سانت 4953-200 556",
                    "- 7114-3460سیرکومتر قطر لوله 700 - 1100کولیس دیجیتال",
                    "2,220,000 690",
                ]
            )
        )
        by_sku = {row["sku"]: row for row in parsed.rows}
        for sku in [
            "3222-1000",
            "3227-1004",
            "3230-25BA",
            "3260-25SA",
            "2673-10",
            "4953-200",
            "7114-3460",
        ]:
            self.assertIn(sku, by_sku)
        self.assertNotIn("1000", by_sku)
        self.assertEqual(by_sku["2673-10"]["price"], "")
        self.assertEqual(by_sku["4953-200"]["price"], "")
        self.assertEqual(by_sku["3222-1000"]["price"], "27,130,000")
        self.assertEqual(by_sku["7114-3460"]["price"], "2,220,000")

    def test_generic_price_uses_money_cell_not_dimension(self):
        parsed = extract_generic_sku_price_rows(
            "DC-100 description 0-150mm 10000 rial\nPage 9\n1500mm only"
        )
        self.assertEqual(len(parsed.rows), 1)
        self.assertEqual(parsed.rows[0]["sku"], "DC-100")
        self.assertEqual(parsed.rows[0]["price"], "10000")
        self.assertEqual(parsed.rows[0]["currency"], "rial")


class DuplicateHashTests(unittest.TestCase):
    def test_same_name_same_hash_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text_pdf(
                root / AST_POWER / "مته برگی" / "لیست قیمت.pdf",
                ["MB-100 5000 rial"],
            )
            write_text_pdf(
                root / DUP_TREE / "مته برگی" / "لیست قیمت.pdf",
                ["MB-100 5000 rial"],
            )
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            self.assertTrue(discovery.skipped_duplicates)
            self.assertFalse(discovery.hash_conflicts)
            self.assertEqual({t.sku for t in discovery.load_product_scope_targets()}, {"MB-100"})

    def test_same_name_different_hash_is_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text_pdf(
                root / AST_POWER / "مته برگی" / "لیست قیمت.pdf",
                ["MB-100 5000 rial"],
            )
            write_text_pdf(
                root / DUP_TREE / "مته برگی" / "لیست قیمت.pdf",
                ["MB-999 9000 rial"],
            )
            discovery = SourceDiscovery(source_root=root)
            discovery.discover()
            self.assertTrue(discovery.hash_conflicts)
            self.assertEqual(discovery.hash_conflicts[0]["reason"], "same_name_different_hash")
            skus = {t.sku for t in discovery.load_product_scope_targets()}
            self.assertEqual(skus, {"MB-100"})
            self.assertNotIn("MB-999", skus)


class CliBlockedSourceTests(unittest.TestCase):
    def test_cli_blocked_source_does_not_write_manifest(self):
        import os
        import subprocess

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "catalog-target"
            env = {k: v for k, v in os.environ.items() if k != "KARZAR_TARGET_SOURCE_DIR"}
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "reconcile_target_catalog.py"), "--output-dir", str(out)],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(proc.returncode, 3)
            self.assertIn("BLOCKED_SOURCE_NOT_MOUNTED", proc.stdout)
            self.assertIn("Did not regenerate a zero-row manifest", proc.stdout)
            self.assertFalse(out.exists())


class CountInvariantTests(unittest.TestCase):
    def test_exactly_one_state_per_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _insize_list_pdf(root, ["1103-150"])
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
                self.assertIn(row.reconciliation_state, set(STATES))
                self.assertNotEqual(row.reconciliation_state, "DELETE")


if __name__ == "__main__":
    unittest.main()
