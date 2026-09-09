#!/usr/bin/env python3
"""Generate data/templates/supplier_stock_template.xlsx (stdlib only)."""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/templates/supplier_stock_template.xlsx"

EN_HEADERS = [
    "Brand",
    "SKU",
    "Model",
    "Availability",
    "Quantity",
    "Warehouse",
    "Last Updated",
    "Notes",
]
FA_HEADERS = [
    "برند",
    "کد کالا",
    "مدل",
    "وضعیت موجودی",
    "تعداد موجودی",
    "انبار",
    "تاریخ بروزرسانی",
    "توضیحات",
]
DOCS_LINES = [
    "Karzar supplier stock template — AVAILABILITY authority only",
    "PRICE AUTHORITY and AVAILABILITY AUTHORITY are independent",
    "Never infer AVAILABLE from price, row existence, or prior is_available",
    "Mandatory: Brand + (SKU or Model) + (Availability or Quantity) + source date",
    "Normalized statuses: AVAILABLE | UNAVAILABLE | UNKNOWN",
    "quantity>0 => AVAILABLE and quantity=0 => UNAVAILABLE only when quantity is sellable stock",
    "Do not invent inventory in this template",
    "See docs/catalog/SUPPLIER_STOCK_AUTHORITY.md",
]


def _col(idx: int) -> str:
    n = idx + 1
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _sheet_xml(rows: list[list[str]]) -> bytes:
    lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        "<sheetData>",
    ]
    for r_i, row in enumerate(rows, start=1):
        lines.append(f'<row r="{r_i}">')
        for c_i, val in enumerate(row):
            ref = f"{_col(c_i)}{r_i}"
            lines.append(
                f'<c r="{ref}" t="inlineStr"><is><t>{escape(val)}</t></is></c>'
            )
        lines.append("</row>")
    lines.append("</sheetData></worksheet>")
    return "\n".join(lines).encode("utf-8")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>
"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
"""
    wb = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="EN" sheetId="1" r:id="rId1"/>
    <sheet name="FA" sheetId="2" r:id="rId2"/>
    <sheet name="README" sheetId="3" r:id="rId3"/>
  </sheets>
</workbook>
"""
    wb_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/>
</Relationships>
"""
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/worksheets/sheet1.xml", _sheet_xml([EN_HEADERS]))
        z.writestr("xl/worksheets/sheet2.xml", _sheet_xml([FA_HEADERS]))
        z.writestr("xl/worksheets/sheet3.xml", _sheet_xml([[line] for line in DOCS_LINES]))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
