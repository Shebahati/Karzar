"""Auditable page-render transcriptions of AST کد کالا tables.

These rows were read from rendered enumerator pages. They are not inferred
from prices, dimensions, or page numbers. Catalog/datasheet pages without a
product-code column are recorded as non-membership.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Filenames whose rendered pages contain an explicit کد کالا / SKU column.
CODE_TABLE_ENUMERATORS = {
    "همکاری قلاویززن اتومات.pdf",
    "همکاری قلاویززن برقی.pdf",
    "همکاری مته برگی.pdf",
}

# Inspected cooperation PDFs that are datasheets/catalogs, not SKU tables.
CATALOG_DATASHEET_ENUMERATORS = {
    "همکاری ابزار تیزکن.pdf": "34-page single-model datasheets; no کد کالا table; page 1 model 13MA is catalog-only",
    "همکاری اسپارک.pdf": "datasheets SP600/SP1500/SP3000; model present, no کد کالا table, no price",
    "تایکوپ همکاری.pdf": "datasheets (BS0 etc.) plus taper-size ranges; BT30/SK40 are not unique SKUs",
    "همکاری دریل مگنت.pdf": "13-page datasheets (DM35, TUMT5, …); no کد کالا table, no price",
    "همکاری کرگیری.pdf": "datasheets (COR80, TURBOCUT 355, …); no کد کالا table, no price",
    "ET همکاری.pdf": "tap family ranges, not discrete SKUs; no price",
    "همکاری روغن اب صابون.pdf": "product-name list without SKU or price",
    "همکاری گردبر.pdf": "diameter/depth ranges, not discrete SKUs; no price",
}

# Page-render transcriptions: only rows whose identity came from a کد کالا column.
_AST_CODE_ROWS: dict[str, list[dict[str, Any]]] = {
    "همکاری قلاویززن اتومات.pdf": [
        {"page": "1", "sku": "AST-GAT7", "description": "M2-M7 Morse auto-reverse tapping head"},
        {"page": "1", "sku": "AST-GAT12", "description": "M3-M12 Morse auto-reverse tapping head"},
        {"page": "1", "sku": "AST-GAT20", "description": "M8-M20 Morse auto-reverse tapping head"},
    ],
    "همکاری قلاویززن برقی.pdf": [
        {"page": "1", "sku": "AST-TRM10", "description": "TRM servo tapping machine M2-M10"},
        {"page": "1", "sku": "AST-TRM12", "description": "TRM servo tapping machine M2-M12"},
        {"page": "1", "sku": "AST-TRM16", "description": "TRM servo tapping machine M2-M16"},
        {"page": "1", "sku": "AST-TRM24", "description": "TRM servo tapping machine M2-M24"},
        {"page": "1", "sku": "AST-TRM36", "description": "TRM servo tapping machine M2-M36"},
        {"page": "1", "sku": "AST-TRM48", "description": "TRM servo tapping machine M5-M48"},
        {"page": "2", "sku": "AST-NSBM10", "description": "NSBM servo tapping machine M2-M10"},
        {"page": "2", "sku": "AST-NSBM12", "description": "NSBM servo tapping machine M2-M12"},
        {"page": "2", "sku": "AST-NSBM16", "description": "NSBM servo tapping machine M2-M16"},
        {"page": "2", "sku": "AST-NSBM24", "description": "NSBM servo tapping machine M2-M24"},
        {"page": "2", "sku": "AST-NSBM36", "description": "NSBM servo tapping machine M2-M36"},
        {"page": "3", "sku": "AST-T800500", "description": "tapping machine table 500x800"},
        {"page": "3", "sku": "AST-T900600", "description": "tapping machine table 600x900"},
        {"page": "4", "sku": "AST-TAPCHUCK19", "description": "drill chuck adapter 13mm TC312"},
        {"page": "4", "sku": "AST-TAPCHUCK31", "description": "drill chuck adapter 16mm TC820"},
        {"page": "4", "sku": "AST-DP19", "description": "angle adapter TC312 M10/12/16"},
        {"page": "4", "sku": "AST-DP31", "description": "angle adapter TC820 M24/36/48"},
        {"page": "4", "sku": "AST-DID19/20", "description": "die holder TC312 M3-M6"},
        {"page": "4", "sku": "AST-DID19/25", "description": "die holder TC312 M8"},
        {"page": "4", "sku": "AST-DID19/30", "description": "die holder TC312 M10"},
        {"page": "4", "sku": "AST-DID19/38", "description": "die holder TC312 M12-M14"},
        {"page": "4", "sku": "AST-DID31/20", "description": "die holder M3-M6"},
        {"page": "4", "sku": "AST-DID31/25", "description": "die holder M8"},
        {"page": "4", "sku": "AST-DID31/30", "description": "die holder M10"},
        {"page": "4", "sku": "AST-DID31/38", "description": "die holder M12-M14"},
        {"page": "4", "sku": "AST-DID31/45", "description": "die holder M16-M20"},
        {"page": "4", "sku": "AST-DID31/55", "description": "die holder M22-M24"},
    ],
    "همکاری مته برگی.pdf": [
        {"page": "3", "sku": "D20/9.5-11", "description": "helical flange spade holder 9.5-11"},
        {"page": "3", "sku": "D20/11.5-12.5", "description": "helical flange spade holder 11.5-12.5"},
        {"page": "3", "sku": "D20/13-17.5", "description": "helical flange spade holder 13-17.5"},
        {"page": "3", "sku": "D25/18-24", "description": "helical flange spade holder 18-24"},
        {"page": "3", "sku": "D32/25-35", "description": "helical flange spade holder 25-35"},
        {"page": "3", "sku": "D40/36-47", "description": "helical flange spade holder 36-47"},
        {"page": "3", "sku": "D40/48-65", "description": "helical flange spade holder 48-65"},
        {"page": "4", "sku": "ATH2-9.511", "description": "Morse 4D spade holder 9.5-11"},
        {"page": "4", "sku": "ATH2-11.512.5", "description": "Morse 4D spade holder 11.5-12.5"},
        {"page": "4", "sku": "ATH2-1317.5", "description": "Morse 4D spade holder 13-17.5"},
        {"page": "4", "sku": "ATH3-1824", "description": "Morse 4D spade holder 18-24"},
        {"page": "4", "sku": "ATH4-2535", "description": "Morse 4D spade holder 25-35"},
        {"page": "4", "sku": "ATH4-3647", "description": "Morse 4D spade holder 36-47"},
        {"page": "4", "sku": "ATH5-4865", "description": "Morse 4D spade holder 48-65"},
        {"page": "4", "sku": "ATH5-6488", "description": "Morse 4D spade holder 64-88"},
        {"page": "4", "sku": "ATH5-90114", "description": "Morse 4D spade holder 90-114"},
        {"page": "5", "sku": "437201", "description": "oil ring 9.5-17.5"},
        {"page": "5", "sku": "437202", "description": "oil ring 18-35"},
        {"page": "5", "sku": "437203", "description": "oil ring 36-47"},
        {"page": "5", "sku": "437204", "description": "oil ring 48-65"},
        {"page": "5", "sku": "437205", "description": "oil ring 64-114"},
    ],
}

# Page-3 magnetic-base labels are descriptions, not manufacturer codes.
REJECTED_DESCRIPTIVE_CODES = (
    {
        "filename": "همکاری قلاویززن برقی.pdf",
        "page": "3",
        "raw_sku": "M16-Magnetic base",
        "reason": "descriptive_label_not_manufacturer_sku",
    },
    {
        "filename": "همکاری قلاویززن برقی.pdf",
        "page": "3",
        "raw_sku": "M36-Magnetic base",
        "reason": "descriptive_label_not_manufacturer_sku",
    },
    {
        "filename": "همکاری قلاویززن برقی.pdf",
        "page": "3",
        "raw_sku": "M48-Magnetic base",
        "reason": "descriptive_label_not_manufacturer_sku",
    },
)


def enumerator_filename(path: Path | str) -> str:
    return Path(path).name


def ast_enumerator_kind(path: Path | str) -> str:
    name = enumerator_filename(path)
    if name in CODE_TABLE_ENUMERATORS:
        return "code_table"
    if name in CATALOG_DATASHEET_ENUMERATORS:
        return "catalog_datasheet"
    return "unknown"


def verified_ast_rows_for(path: Path | str) -> list[dict[str, Any]]:
    name = enumerator_filename(path)
    out: list[dict[str, Any]] = []
    for item in _AST_CODE_ROWS.get(name) or []:
        sku = str(item["sku"])
        page = str(item["page"])
        desc = str(item.get("description") or "")
        out.append(
            {
                "sku": sku,
                "CODE": sku,
                "price": "",
                "currency": "",
                "description": desc,
                "page": page,
                "__source_row": f"page {page} کد کالا {sku}",
                "__extraction_method": "page_render_manual_structure",
            }
        )
    return out


def ast_review_records(
    *,
    family: str,
    path: Path | str,
    duplicate_relationship: str,
) -> list[dict[str, str]]:
    name = enumerator_filename(path)
    kind = ast_enumerator_kind(path)
    records: list[dict[str, str]] = []
    if kind == "code_table":
        for row in verified_ast_rows_for(path):
            records.append(
                {
                    "family": family,
                    "source_file": str(path),
                    "page": str(row.get("page") or ""),
                    "raw_row": str(row.get("__source_row") or ""),
                    "raw_sku": str(row.get("sku") or ""),
                    "normalized_sku": str(row.get("sku") or "").upper(),
                    "description": str(row.get("description") or ""),
                    "raw_price": "",
                    "currency": "",
                    "base_price_toman": "",
                    "confidence": "high",
                    "decision": "promote_target_member_review",
                    "review_reason": "code_table_no_price;manual_structure",
                    "duplicate_original_relationship": duplicate_relationship,
                }
            )
        for rejected in REJECTED_DESCRIPTIVE_CODES:
            if rejected["filename"] != name:
                continue
            records.append(
                {
                    "family": family,
                    "source_file": str(path),
                    "page": rejected["page"],
                    "raw_row": rejected["raw_sku"],
                    "raw_sku": rejected["raw_sku"],
                    "normalized_sku": "",
                    "description": "",
                    "raw_price": "",
                    "currency": "",
                    "base_price_toman": "",
                    "confidence": "high",
                    "decision": "reject",
                    "review_reason": rejected["reason"],
                    "duplicate_original_relationship": duplicate_relationship,
                }
            )
        return records
    if kind == "catalog_datasheet":
        records.append(
            {
                "family": family,
                "source_file": str(path),
                "page": "inspected",
                "raw_row": "",
                "raw_sku": "",
                "normalized_sku": "",
                "description": CATALOG_DATASHEET_ENUMERATORS[name],
                "raw_price": "",
                "currency": "",
                "base_price_toman": "",
                "confidence": "high",
                "decision": "catalog_not_membership",
                "review_reason": "enumerator_is_catalog_or_datasheet_without_sku_table",
                "duplicate_original_relationship": duplicate_relationship,
            }
        )
    return records
