"""Tests for INSIZE sales activation workbook parse / match / guarded pilot apply."""

from __future__ import annotations

import io
import zipfile
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from xml.etree.ElementTree import Element, SubElement, tostring

import pytest

from scripts.insize_sales_activation_lib import (
    CONTROL_RIAL,
    CONTROL_SKU,
    CONTROL_TOMAN,
    CONTROL_USD,
    PilotGateError,
    PilotSkuPlan,
    WorkbookRow,
    apply_pilot_plans,
    assert_expected_rate,
    assert_expected_workbook_sha,
    content_ready,
    final_toman_from_usd,
    image_ready,
    load_workbook_catalog,
    match_exact,
    normalize_sku,
    normalize_status,
    revalidate_plan_against_live,
    rial_from_usd,
    supplier_available,
    toman_from_rial,
    valid_workbook_price,
    verify_control_sku,
    verify_pilot_state,
    workbook_sha256,
)


def _xlsx_bytes(
    *,
    headers: list[str],
    rows: list[list[object]],
    rate: int = 2_500_000,
    rate_cell: str = "K6",
) -> bytes:
    strings: list[str] = []
    string_index: dict[str, int] = {}

    def sid(text: str) -> int:
        if text not in string_index:
            string_index[text] = len(strings)
            strings.append(text)
        return string_index[text]

    def col_name(idx: int) -> str:
        n = idx + 1
        s = ""
        while n:
            n, r = divmod(n - 1, 26)
            s = chr(65 + r) + s
        return s

    sheet_data = Element("sheetData")
    row1 = SubElement(sheet_data, "row", r="1")
    for i, h in enumerate(headers):
        c = SubElement(row1, "c", r=f"{col_name(i)}1", t="s")
        SubElement(c, "v").text = str(sid(h))
    for r_i, values in enumerate(rows, start=2):
        row = SubElement(sheet_data, "row", r=str(r_i))
        for i, val in enumerate(values):
            ref = f"{col_name(i)}{r_i}"
            if isinstance(val, str):
                c = SubElement(row, "c", r=ref, t="s")
                SubElement(c, "v").text = str(sid(val))
            else:
                c = SubElement(row, "c", r=ref)
                SubElement(c, "v").text = str(val)
    row6 = sheet_data.find("./row[@r='6']")
    if row6 is None:
        row6 = SubElement(sheet_data, "row", r="6")
    c_rate = SubElement(row6, "c", r=rate_cell)
    SubElement(c_rate, "v").text = str(rate)

    worksheet = Element(
        "worksheet",
        xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    )
    worksheet.append(sheet_data)
    sst = Element(
        "sst",
        xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        count=str(len(strings)),
        uniqueCount=str(len(strings)),
    )
    for s in strings:
        si = SubElement(sst, "si")
        SubElement(si, "t").text = s
    workbook = Element(
        "workbook",
        xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    )
    sheets = SubElement(workbook, "sheets")
    SubElement(
        sheets,
        "sheet",
        name="Sheet1",
        sheetId="1",
        **{
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id": "rId1"
        },
    )
    rels = Element(
        "Relationships",
        xmlns="http://schemas.openxmlformats.org/package/2006/relationships",
    )
    SubElement(
        rels,
        "Relationship",
        Id="rId1",
        Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
        Target="worksheets/sheet1.xml",
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
        )
        z.writestr("xl/workbook.xml", tostring(workbook, encoding="unicode"))
        z.writestr("xl/_rels/workbook.xml.rels", tostring(rels, encoding="unicode"))
        z.writestr("xl/sharedStrings.xml", tostring(sst, encoding="unicode"))
        z.writestr("xl/worksheets/sheet1.xml", tostring(worksheet, encoding="unicode"))
    return buf.getvalue()


HEADERS = [
    "CODE",
    "DESCRIPTION",
    "موجودی قدس",
    "موجودی تهران",
    "شوروم قدس",
    "شوروم تهران",
    "موجودی کل",
    "وضعیت",
    "قیمت دلاری",
]


@pytest.fixture()
def sample_xlsx(tmp_path: Path) -> Path:
    rows = [
        ["1114-150A", "DIGITAL CALIPER", 10, 0, 0, 0, 10, "موجود", 28.5],
        ["9722-250", "TAPE", 8, 0, 0, 0, 8, "موجود", 1.92],
        ["9999-1", "OTHER", 0, 0, 0, 0, 0, "نا موجود", 12],
    ]
    path = tmp_path / "sample.xlsx"
    path.write_bytes(_xlsx_bytes(headers=HEADERS, rows=rows))
    return path


def _plan(**overrides) -> PilotSkuPlan:
    base = dict(
        product_id=1,
        sku="9722-250",
        title="متر",
        category_id=77,
        category_name="متر",
        slug="9722-250",
        public_path="/product/9722-250",
        workbook_code="9722-250",
        workbook_row=3,
        workbook_description="TAPE",
        usd_price=Decimal("1.92"),
        rate=Decimal("2500000"),
        rial_price=Decimal("4800000"),
        toman_price=Decimal("480000"),
        current_base_price=Decimal("399000"),
        new_base_price=Decimal("480000"),
        absolute_delta=Decimal("81000"),
        percentage_delta=20.3,
        current_is_available=False,
        target_is_available=True,
        is_active=True,
        image_ready=True,
        content_ready=True,
        eligibility_reason="test",
        expected_updated_at="2026-01-01T00:00:00+00:00",
        review_flags=[],
    )
    base.update(overrides)
    return PilotSkuPlan(**base)


def test_normalize_sku_hyphen_and_case():
    assert normalize_sku(" 1114‑150a ") == "1114-150A"
    assert normalize_sku("1114_150A") == "1114-150A"


def test_status_and_availability():
    assert supplier_available("موجود")
    assert not supplier_available("نا موجود")
    assert normalize_status("  موجود  ") == "موجود"


def test_rial_to_toman_conversion():
    rial = rial_from_usd(CONTROL_USD, Decimal("2500000"))
    toman = toman_from_rial(rial)
    assert rial == CONTROL_RIAL
    assert toman == CONTROL_TOMAN
    assert final_toman_from_usd(CONTROL_USD, Decimal("2500000")) == CONTROL_TOMAN


def test_workbook_rate_mismatch(sample_xlsx: Path):
    cat = load_workbook_catalog(sample_xlsx)
    with pytest.raises(PilotGateError, match="workbook-rate mismatch"):
        assert_expected_rate(cat, Decimal("999"))


def test_workbook_hash_mismatch(sample_xlsx: Path):
    with pytest.raises(PilotGateError, match="workbook-hash mismatch"):
        assert_expected_workbook_sha(sample_xlsx, "0" * 64)
    sha = workbook_sha256(sample_xlsx)
    assert assert_expected_workbook_sha(sample_xlsx, sha) == sha


def test_exact_sku_enforcement_and_suffix_rejection():
    wb = {
        "1114-150A": WorkbookRow(
            code="1114-150A",
            description="x",
            total_inventory=Decimal("10"),
            status="موجود",
            usd_price=CONTROL_USD,
            source_row=2,
        )
    }
    assert match_exact("1114-150A", wb).method == "exact"
    assert match_exact("1114-150", wb).method == "unmatched"


def test_header_parser_and_control_checksum(sample_xlsx: Path):
    cat = load_workbook_catalog(sample_xlsx)
    assert cat.rate == Decimal("2500000")
    check = verify_control_sku(cat)
    assert check["ok"] is True


def test_fail_closed_missing_header(tmp_path: Path):
    headers = HEADERS[:-1]
    path = tmp_path / "bad.xlsx"
    path.write_bytes(
        _xlsx_bytes(headers=headers, rows=[["1114-150A", "x", 0, 0, 0, 0, 0, "موجود"]])
    )
    with pytest.raises(ValueError, match="FAIL CLOSED"):
        load_workbook_catalog(path)


def test_invalid_price_rejection():
    cls, _, _ = valid_workbook_price(None, Decimal("2500000"))
    assert cls == "INVALID_WORKBOOK_PRICE"
    cls2, _, _ = valid_workbook_price(Decimal("0"), Decimal("2500000"))
    assert cls2 == "INVALID_WORKBOOK_PRICE"


def test_image_and_content_readiness():
    assert image_ready(1, "/media/products/x.webp")
    assert not image_ready(0, "/media/products/x.webp")
    assert content_ready(
        name="کولیس",
        short_description="کولیس دیجیتال اینسایز با بازه اندازه‌گیری مشخص و بدنه فلزی.",
        description=None,
        specifications=None,
    )


def _live_ok(sku="9722-250", **over):
    base = {
        "id": 1,
        "sku": sku,
        "name": "متر",
        "base_price": "399000",
        "is_available": "f",
        "is_active": "t",
        "category_id": "77",
        "slug": sku,
        "short_description": "متر فلزی صنعتی اینسایز با طول مفید مشخص برای کارگاه.",
        "description": "توضیح بلندتر از چهل کاراکتر برای رد کردن stub classifier در تست.",
        "specifications": '{"technical_specs":{"range":"0-250mm"}}',
        "image_count": "1",
        "primary_image_url": "/media/x.webp",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    base.update(over)
    return base


def test_inactive_product_rejection(sample_xlsx: Path):
    cat = load_workbook_catalog(sample_xlsx)
    plan = _plan()
    live = _live_ok(is_active="f")
    wb = cat.by_code["9722-250"]
    with pytest.raises(PilotGateError, match="inactive"):
        revalidate_plan_against_live(plan, product=live, workbook_row=wb, catalog=cat)


def test_image_content_readiness_rejection(sample_xlsx: Path):
    cat = load_workbook_catalog(sample_xlsx)
    plan = _plan()
    live = _live_ok(image_count="0", primary_image_url="")
    wb = cat.by_code["9722-250"]
    with pytest.raises(PilotGateError, match="image"):
        revalidate_plan_against_live(plan, product=live, workbook_row=wb, catalog=cat)


def test_stale_concurrent_rejection(sample_xlsx: Path):
    cat = load_workbook_catalog(sample_xlsx)
    plan = _plan(expected_updated_at="2026-01-01T00:00:00+00:00")
    live = _live_ok(updated_at="2026-09-01T00:00:00+00:00")
    wb = cat.by_code["9722-250"]
    with pytest.raises(PilotGateError, match="stale/concurrent"):
        revalidate_plan_against_live(plan, product=live, workbook_row=wb, catalog=cat)


def test_apply_only_allowlisted_fields_and_idempotent(sample_xlsx: Path):
    cat = load_workbook_catalog(sample_xlsx)
    plan = _plan()
    product = SimpleNamespace(
        id=1,
        sku="9722-250",
        name="متر",
        base_price=Decimal("399000"),
        is_available=False,
        is_active=True,
        brand_id=3,
        category_id=77,
        short_description="x",
        description="y",
        specifications={},
        stock_quantity=Decimal("0"),
        slug="9722-250",
        original_price=None,
        meta_title=None,
        meta_description=None,
    )
    live = _live_ok()
    result = apply_pilot_plans(
        products_by_id={1: product},
        plans=[plan],
        workbook_by_code=cat.by_code,
        catalog=cat,
        live_product_rows={"9722-250": live},
    )
    assert product.base_price == Decimal("480000")
    assert product.is_available is True
    assert product.name == "متر"
    assert product.sku == "9722-250"
    assert product.brand_id == 3
    assert len(result.updated) == 1

    # Second run idempotent
    result2 = apply_pilot_plans(
        products_by_id={1: product},
        plans=[plan],
        workbook_by_code=cat.by_code,
        catalog=cat,
        live_product_rows={"9722-250": live},
    )
    assert result2.updated == []
    assert len(result2.skipped_idempotent) == 1


def test_verify_forbidden_field_preservation():
    plan = _plan()
    product = SimpleNamespace(
        id=1,
        base_price=Decimal("480000"),
        is_available=True,
        name="CHANGED",
        sku="9722-250",
    )
    before = {"name": "متر", "sku": "9722-250"}
    with pytest.raises(PilotGateError, match="forbidden field"):
        verify_pilot_state(
            plans=[plan],
            products_by_id={1: product},
            snapshots_before={1: before},
        )


def test_explicit_count_mismatch_via_empty_plans():
    with pytest.raises(PilotGateError, match="empty pilot plan"):
        apply_pilot_plans(
            products_by_id={},
            plans=[],
            workbook_by_code={},
            catalog=SimpleNamespace(rate=Decimal("2500000"), by_code={}),  # type: ignore[arg-type]
            live_product_rows={},
        )


def test_transaction_rollback_semantics(sample_xlsx: Path):
    """If a later plan fails gate, caller must not keep earlier mutations.

    We simulate by validating all-or-nothing preflight: a bad second plan raises
    before any mutation.
    """
    cat = load_workbook_catalog(sample_xlsx)
    good = _plan()
    bad = _plan(product_id=2, sku="NO-SUCH", workbook_code="NO-SUCH", new_base_price=Decimal("1"), toman_price=Decimal("1"), rial_price=Decimal("10"), usd_price=Decimal("0.004"))
    p1 = SimpleNamespace(id=1, base_price=Decimal("399000"), is_available=False, name="متر", sku="9722-250", brand_id=3, category_id=77, short_description="x", description="y", specifications={}, stock_quantity=Decimal("0"), slug="9722-250", original_price=None, meta_title=None, meta_description=None, is_active=True)
    with pytest.raises(PilotGateError):
        apply_pilot_plans(
            products_by_id={1: p1},
            plans=[good, bad],
            workbook_by_code=cat.by_code,
            catalog=cat,
            live_product_rows={"9722-250": _live_ok()},
        )
    # First product untouched because preflight failed before mutations
    assert p1.base_price == Decimal("399000")
    assert p1.is_available is False


def test_only_allowlisted_skus_in_apply_set(sample_xlsx: Path):
    cat = load_workbook_catalog(sample_xlsx)
    plan = _plan()
    p1 = SimpleNamespace(id=1, base_price=Decimal("399000"), is_available=False, name="متر", sku="9722-250", brand_id=3, category_id=77, short_description="x", description="y", specifications={}, stock_quantity=Decimal("0"), slug="9722-250", original_price=None, meta_title=None, meta_description=None, is_active=True)
    p2 = SimpleNamespace(id=2, base_price=Decimal("100"), is_available=False, name="other", sku="OTHER", brand_id=3, category_id=77)
    apply_pilot_plans(
        products_by_id={1: p1, 2: p2},
        plans=[plan],
        workbook_by_code=cat.by_code,
        catalog=cat,
        live_product_rows={"9722-250": _live_ok()},
    )
    assert p2.base_price == Decimal("100")
    assert p2.is_available is False
