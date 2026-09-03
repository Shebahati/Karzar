"""Tests for INSIZE sales activation workbook parse / match / guarded pilot apply."""

from __future__ import annotations

import io
import json
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from xml.etree.ElementTree import Element, SubElement, tostring

import pytest
from scripts.insize_sales_activation_lib import (
    CONTROL_RIAL,
    CONTROL_TOMAN,
    CONTROL_USD,
    PilotGateError,
    PilotManifest,
    PilotSkuPlan,
    WorkbookRow,
    apply_pilot_plans,
    assert_expected_rate,
    assert_expected_workbook_sha,
    assert_manifest_identity_unique,
    bind_workbook_authorities,
    category_inconsistency_reason,
    content_ready,
    final_toman_from_usd,
    image_ready,
    load_workbook_catalog,
    match_exact,
    normalize_sku,
    normalize_status,
    revalidate_plan_against_db_row,
    revalidate_plan_against_live,
    rial_from_usd,
    rollback_from_recovery_snapshot,
    supplier_available,
    toman_from_rial,
    valid_workbook_price,
    verify_control_sku,
    verify_pilot_state,
    workbook_sha256,
    write_recovery_snapshot,
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
        pilot_group="unavailable_to_available",
        category_review_note="test OK",
    )
    base.update(overrides)
    return PilotSkuPlan(**base)


def _db_product(**over) -> SimpleNamespace:
    base = dict(
        id=1,
        sku="9722-250",
        name="متر",
        base_price=Decimal("399000"),
        is_available=False,
        is_active=True,
        brand_id=3,
        category_id=77,
        short_description="متر فلزی صنعتی اینسایز با طول مفید مشخص برای کارگاه.",
        description="توضیح بلندتر از چهل کاراکتر برای رد کردن stub classifier در تست.",
        specifications={"technical_specs": {"range": "0-250mm"}},
        stock_quantity=Decimal("0"),
        slug="9722-250",
        original_price=None,
        meta_title=None,
        meta_description=None,
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    base.update(over)
    return SimpleNamespace(**base)


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


def test_stale_csv_cannot_authorize_write(sample_xlsx: Path):
    cat = load_workbook_catalog(sample_xlsx)
    with pytest.raises(PilotGateError, match="stale CSV cannot authorize"):
        revalidate_plan_against_live(
            _plan(),
            product={"sku": "9722-250", "updated_at": "anything"},
            workbook_row=cat.by_code["9722-250"],
            catalog=cat,
        )


def test_inactive_product_rejection(sample_xlsx: Path):
    cat = load_workbook_catalog(sample_xlsx)
    product = _db_product(is_active=False)
    with pytest.raises(PilotGateError, match="inactive"):
        revalidate_plan_against_db_row(
            _plan(),
            product=product,
            workbook_row=cat.by_code["9722-250"],
            catalog=cat,
            image_count=1,
            primary_image_url="/media/x.webp",
        )


def test_image_content_readiness_rejection(sample_xlsx: Path):
    cat = load_workbook_catalog(sample_xlsx)
    with pytest.raises(PilotGateError, match="image"):
        revalidate_plan_against_db_row(
            _plan(),
            product=_db_product(),
            workbook_row=cat.by_code["9722-250"],
            catalog=cat,
            image_count=0,
            primary_image_url="",
        )


def test_db_product_id_sku_mismatch_blocks(sample_xlsx: Path):
    cat = load_workbook_catalog(sample_xlsx)
    with pytest.raises(PilotGateError, match="product_id/SKU mismatch"):
        revalidate_plan_against_db_row(
            _plan(),
            product=_db_product(sku="OTHER-SKU"),
            workbook_row=cat.by_code["9722-250"],
            catalog=cat,
            image_count=1,
            primary_image_url="/media/x.webp",
        )


def test_live_db_price_availability_updated_at_drift(sample_xlsx: Path):
    cat = load_workbook_catalog(sample_xlsx)
    wb = cat.by_code["9722-250"]
    with pytest.raises(PilotGateError, match="live DB price drift"):
        revalidate_plan_against_db_row(
            _plan(),
            product=_db_product(base_price=Decimal("1")),
            workbook_row=wb,
            catalog=cat,
            image_count=1,
            primary_image_url="/media/x.webp",
        )
    with pytest.raises(PilotGateError, match="live DB availability drift"):
        revalidate_plan_against_db_row(
            _plan(),
            product=_db_product(is_available=True),
            workbook_row=wb,
            catalog=cat,
            image_count=1,
            primary_image_url="/media/x.webp",
        )
    with pytest.raises(PilotGateError, match="stale/concurrent"):
        revalidate_plan_against_db_row(
            _plan(expected_updated_at="2026-01-01T00:00:00+00:00"),
            product=_db_product(updated_at=datetime(2026, 9, 1, tzinfo=UTC)),
            workbook_row=wb,
            catalog=cat,
            image_count=1,
            primary_image_url="/media/x.webp",
        )


def test_manifest_sha_rate_and_duplicate_identity_blocks(sample_xlsx: Path):
    cat = load_workbook_catalog(sample_xlsx)
    plan = _plan()
    manifest = PilotManifest(
        version=2,
        workbook_sha256="deadbeef",
        expected_rate="2500000",
        expected_sku_count=1,
        selected_skus=[plan.sku],
        checkout_test_sku=plan.sku,
        plans=[plan],
        generated_at_utc="2026-01-01T00:00:00+00:00",
    )
    with pytest.raises(PilotGateError, match="workbook SHA authority mismatch"):
        bind_workbook_authorities(
            xlsx=sample_xlsx,
            catalog=cat,
            manifest=manifest,
            cli_sha256=workbook_sha256(sample_xlsx),
            cli_rate=cat.rate,
        )
    bad_rate = PilotManifest(
        version=2,
        workbook_sha256=workbook_sha256(sample_xlsx),
        expected_rate="1",
        expected_sku_count=1,
        selected_skus=[plan.sku],
        checkout_test_sku=plan.sku,
        plans=[plan],
        generated_at_utc="2026-01-01T00:00:00+00:00",
    )
    with pytest.raises(PilotGateError, match="workbook rate authority mismatch"):
        bind_workbook_authorities(
            xlsx=sample_xlsx,
            catalog=cat,
            manifest=bad_rate,
            cli_sha256=workbook_sha256(sample_xlsx),
            cli_rate=cat.rate,
        )
    dup_sku = PilotManifest(
        version=2,
        workbook_sha256=workbook_sha256(sample_xlsx),
        expected_rate="2500000",
        expected_sku_count=2,
        selected_skus=["9722-250", "9722-250"],
        checkout_test_sku="9722-250",
        plans=[plan, _plan(product_id=2)],
        generated_at_utc="2026-01-01T00:00:00+00:00",
    )
    with pytest.raises(PilotGateError, match="duplicate normalized SKUs"):
        assert_manifest_identity_unique(dup_sku)
    dup_id = PilotManifest(
        version=2,
        workbook_sha256=workbook_sha256(sample_xlsx),
        expected_rate="2500000",
        expected_sku_count=2,
        selected_skus=["9722-250", "1114-150A"],
        checkout_test_sku="9722-250",
        plans=[plan, _plan(product_id=1, sku="1114-150A", workbook_code="1114-150A")],
        generated_at_utc="2026-01-01T00:00:00+00:00",
    )
    with pytest.raises(PilotGateError, match="duplicate product IDs"):
        assert_manifest_identity_unique(dup_id)


def test_unavailable_to_available_transition_and_second_apply_noop(
    sample_xlsx: Path, tmp_path: Path
):
    cat = load_workbook_catalog(sample_xlsx)
    plan = _plan(current_is_available=False)
    product = _db_product(is_available=False)
    snap = tmp_path / "recovery.json"
    result = apply_pilot_plans(
        products_by_id={1: product},
        plans=[plan],
        workbook_by_code=cat.by_code,
        catalog=cat,
        image_state_by_id={1: (1, "/media/x.webp")},
        recovery_snapshot_path=snap,
    )
    assert product.base_price == Decimal("480000")
    assert product.is_available is True
    assert len(result.updated) == 1
    assert snap.is_file()
    assert result.recovery_snapshot_sha256

    # Second apply is a no-op when approved pre-values already match targets.
    plan2 = _plan(
        current_base_price=Decimal("480000"),
        current_is_available=True,
        expected_updated_at=product.updated_at.isoformat(),
    )
    result2 = apply_pilot_plans(
        products_by_id={1: product},
        plans=[plan2],
        workbook_by_code=cat.by_code,
        catalog=cat,
        image_state_by_id={1: (1, "/media/x.webp")},
        recovery_snapshot_path=None,
    )
    assert result2.updated == []
    assert len(result2.skipped_idempotent) == 1


def test_recovery_snapshot_failure_prevents_mutation(
    sample_xlsx: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    cat = load_workbook_catalog(sample_xlsx)
    product = _db_product()
    snap = tmp_path / "recovery.json"

    def fail_write(path, rows):
        raise PilotGateError("recovery snapshot failure prevents mutation")

    monkeypatch.setattr(
        "scripts.insize_sales_activation_lib.write_recovery_snapshot", fail_write
    )
    with pytest.raises(PilotGateError, match="recovery snapshot failure"):
        apply_pilot_plans(
            products_by_id={1: product},
            plans=[_plan()],
            workbook_by_code=cat.by_code,
            catalog=cat,
            image_state_by_id={1: (1, "/media/x.webp")},
            recovery_snapshot_path=snap,
        )
    assert product.base_price == Decimal("399000")
    assert product.is_available is False


def test_write_recovery_snapshot_os_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import scripts.insize_sales_activation_lib as lib

    def boom(*_a, **_k):
        raise OSError("nope")

    monkeypatch.setattr(lib.os, "replace", boom)
    with pytest.raises(PilotGateError, match="recovery snapshot failure"):
        write_recovery_snapshot(
            tmp_path / "r.json",
            [
                {
                    "product_id": 1,
                    "sku": "X",
                    "old_base_price": "1",
                    "old_is_available": False,
                    "updated_at": "t",
                }
            ],
        )


def test_rollback_restores_allowed_fields_only(sample_xlsx: Path, tmp_path: Path):
    cat = load_workbook_catalog(sample_xlsx)
    product = _db_product()
    snap = tmp_path / "recovery.json"
    apply_pilot_plans(
        products_by_id={1: product},
        plans=[_plan()],
        workbook_by_code=cat.by_code,
        catalog=cat,
        image_state_by_id={1: (1, "/media/x.webp")},
        recovery_snapshot_path=snap,
    )
    assert product.is_available is True
    product.name = "SHOULD_STAY"
    raw = json.loads(snap.read_text(encoding="utf-8"))
    restored = rollback_from_recovery_snapshot(
        products_by_id={1: product},
        snapshot_rows=raw["rows"],
    )
    assert product.base_price == Decimal("399000")
    assert product.is_available is False
    assert product.name == "SHOULD_STAY"
    assert len(restored) == 1


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
            image_state_by_id={},
        )


def test_transaction_rollback_semantics(sample_xlsx: Path, tmp_path: Path):
    cat = load_workbook_catalog(sample_xlsx)
    good = _plan()
    bad = _plan(
        product_id=2,
        sku="NO-SUCH",
        workbook_code="NO-SUCH",
        new_base_price=Decimal("1"),
        toman_price=Decimal("1"),
        rial_price=Decimal("10"),
        usd_price=Decimal("0.004"),
    )
    p1 = _db_product()
    with pytest.raises(PilotGateError):
        apply_pilot_plans(
            products_by_id={1: p1},
            plans=[good, bad],
            workbook_by_code=cat.by_code,
            catalog=cat,
            image_state_by_id={1: (1, "/media/x.webp")},
            recovery_snapshot_path=tmp_path / "r.json",
        )
    assert p1.base_price == Decimal("399000")
    assert p1.is_available is False


def test_only_allowlisted_skus_in_apply_set(sample_xlsx: Path, tmp_path: Path):
    cat = load_workbook_catalog(sample_xlsx)
    p1 = _db_product()
    p2 = _db_product(id=2, sku="OTHER", base_price=Decimal("100"), is_available=False)
    apply_pilot_plans(
        products_by_id={1: p1, 2: p2},
        plans=[_plan()],
        workbook_by_code=cat.by_code,
        catalog=cat,
        image_state_by_id={1: (1, "/media/x.webp")},
        recovery_snapshot_path=tmp_path / "r.json",
    )
    assert p2.base_price == Decimal("100")
    assert p2.is_available is False


def test_category_inconsistency_rules():
    assert category_inconsistency_reason(
        "SMART DIGITAL MULTIMETER", "عمق سنج"
    )
    assert category_inconsistency_reason("WELDING GAGE", "انواع کولیس")
    assert category_inconsistency_reason("VOLTAGE TESTER", "متر")
    assert category_inconsistency_reason("TAPE", "متر") is None


def test_synthetic_fixture_has_no_real_skus():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "fixtures"
        / "insize_pilot_manifest_synthetic.json"
    )
    raw = json.loads(path.read_text(encoding="utf-8"))
    for sku in raw["selected_skus"]:
        assert sku.startswith("FAKE-")
    for plan in raw["plans"]:
        assert plan["sku"].startswith("FAKE-")
        assert int(plan["product_id"]) >= 900000
        assert Decimal(plan["new_base_price"]) <= Decimal("500000")
