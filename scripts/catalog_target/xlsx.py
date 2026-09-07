"""Minimal XLSX reader (stdlib zipfile + XML). No openpyxl dependency."""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def _col_letters_to_idx(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _cell_ref_col(ref: str) -> str:
    return "".join(ch for ch in ref if ch.isalpha())


def _load_shared_strings(z: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    out: list[str] = []
    for si in root.findall("m:si", _NS):
        out.append("".join(t.text or "" for t in si.findall(".//m:t", _NS)))
    return out


def _cell_value(cell: ET.Element, shared: list[str]) -> Any:
    t = cell.get("t")
    v = cell.find("m:v", _NS)
    if v is None:
        is_el = cell.find("m:is", _NS)
        if is_el is not None:
            return "".join(t.text or "" for t in is_el.findall(".//m:t", _NS))
        return None
    if t == "s":
        return shared[int(v.text or "0")]
    return v.text


def _sheet_path(z: zipfile.ZipFile, wanted: str | None) -> str:
    if "xl/workbook.xml" not in z.namelist():
        return "xl/worksheets/sheet1.xml"
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid_to_target: dict[str, str] = {}
    for rel in rels:
        rid = rel.get("Id")
        target = rel.get("Target")
        if rid and target:
            rid_to_target[rid] = target
    sheets = wb.findall("m:sheets/m:sheet", _NS)
    chosen = None
    for sh in sheets:
        if wanted and sh.get("name") == wanted:
            chosen = sh
            break
    if chosen is None and sheets:
        chosen = sheets[0]
    if chosen is None:
        return "xl/worksheets/sheet1.xml"
    rid = chosen.get(_REL)
    target = rid_to_target.get(rid or "", "worksheets/sheet1.xml")
    if not target.startswith("xl/"):
        target = f"xl/{target.lstrip('/')}"
    return target


def iter_xlsx_rows(
    path: Path,
    *,
    sheet_name: str | None = None,
) -> list[dict[str, Any]]:
    """Return rows as dicts keyed by header text (first row)."""
    path = Path(path)
    with zipfile.ZipFile(path) as z:
        shared = _load_shared_strings(z)
        sheet_path = _sheet_path(z, sheet_name)
        if sheet_path not in z.namelist():
            sheet_path = "xl/worksheets/sheet1.xml"
        sheet = ET.fromstring(z.read(sheet_path))
        xml_rows = sheet.findall("m:sheetData/m:row", _NS)
        if not xml_rows:
            return []

        def row_values(row_el: ET.Element) -> dict[int, Any]:
            out: dict[int, Any] = {}
            for c in row_el.findall("m:c", _NS):
                ref = c.get("r", "A1")
                out[_col_letters_to_idx(_cell_ref_col(ref))] = _cell_value(c, shared)
            return out

        header_vals = row_values(xml_rows[0])
        if not header_vals:
            return []
        max_idx = max(header_vals)
        headers = [str(header_vals.get(i) or "").strip() for i in range(max_idx + 1)]
        rows: list[dict[str, Any]] = []
        for row_el in xml_rows[1:]:
            vals = row_values(row_el)
            if not any(v not in (None, "") for v in vals.values()):
                continue
            item = {headers[i]: vals.get(i) for i in range(len(headers)) if headers[i]}
            item["__source_row"] = int(row_el.get("r") or (len(rows) + 2))
            rows.append(item)
        return rows


def read_xlsx_cell(path: Path, cell_ref: str, *, sheet_name: str | None = None) -> Any:
    """Read one cell (e.g. K6) from an xlsx workbook."""
    path = Path(path)
    wanted = cell_ref.strip().upper()
    with zipfile.ZipFile(path) as z:
        shared = _load_shared_strings(z)
        sheet_path = _sheet_path(z, sheet_name)
        if sheet_path not in z.namelist():
            sheet_path = "xl/worksheets/sheet1.xml"
        sheet = ET.fromstring(z.read(sheet_path))
        for row in sheet.findall("m:sheetData/m:row", _NS):
            for c in row.findall("m:c", _NS):
                if (c.get("r") or "").upper() == wanted:
                    return _cell_value(c, shared)
    return None
