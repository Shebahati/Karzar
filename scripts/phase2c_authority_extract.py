"""Deterministic OEM code extraction from local authority documents (read-only)."""

from __future__ import annotations

import hashlib
import re
import subprocess
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.domain.phase2c_evidence import normalized_match_key

DEFAULT_PRODUCT_DATA_ROOT = Path(
    "/home/shebahati/KaZar/Product and Data Complete"
)

INSIZE_NUMERIC_CODE = re.compile(r"\b(\d{4}-[A-Z0-9][A-Z0-9\-]*)\b", re.IGNORECASE)
DASQUA_NUMERIC_CODE = INSIZE_NUMERIC_CODE
TERMA_CODE = re.compile(
    r"\b("
    r"[A-Z]{2,4}\d{2,4}[A-Z]?(?:-\d+[A-Z]?)?"
    r"|D\d+/[\d./\-]+"
    r"|ATH\d+-[\d.]+"
    r")\b",
    re.IGNORECASE,
)
AST_TEXT_CODE = re.compile(
    r"\b(AST-[A-Z0-9/]+|\d{6}|TU-[A-Z0-9]+|ATH\d+-[\d.]+|D\d+/[\d./\-]+)\b",
    re.IGNORECASE,
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pdf_page_count(path: Path) -> int:
    try:
        out = subprocess.run(
            ["pdfinfo", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        for line in out.stdout.splitlines():
            if line.startswith("Pages:"):
                return int(line.split(":", 1)[1].strip())
    except (OSError, ValueError):
        pass
    return 0


def pdftotext_page(path: Path, page: int) -> str:
    try:
        out = subprocess.run(
            ["pdftotext", "-f", str(page), "-l", str(page), "-layout", str(path), "-"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if out.returncode != 0:
            return ""
        return out.stdout or ""
    except OSError:
        return ""


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


@dataclass
class ExtractedRow:
    source_id: str
    brand: str
    authority_tier: int
    source_type: str
    source_path: Path
    source_sha256: str
    source_document_title: str
    source_page_index: int
    source_row: int
    source_field_label: str
    raw_source_code: str
    source_item_description: str
    extraction_method: str
    mapping_basis: str
    oem_identity_field_proven: str
    notes: str = ""

    def to_registry_dict(self) -> dict[str, Any]:
        raw = self.raw_source_code
        canon = raw
        return {
            "source_id": self.source_id,
            "brand": self.brand,
            "manufacturer_code": canon,
            "authority_tier": str(self.authority_tier),
            "source_type": self.source_type,
            "source_path": str(self.source_path),
            "source_sha256": self.source_sha256,
            "source_document_title": self.source_document_title,
            "source_page_index": str(self.source_page_index),
            "source_printed_page": "",
            "source_table": "price_list",
            "source_row": str(self.source_row),
            "source_cell_or_column": self.source_field_label,
            "source_field_label": self.source_field_label,
            "raw_source_code": raw,
            "canonical_candidate_code": canon,
            "normalized_match_key": normalized_match_key(canon),
            "source_item_description": _nfc(self.source_item_description),
            "source_variant_description": "",
            "extraction_method": self.extraction_method,
            "mapping_basis": self.mapping_basis,
            "oem_identity_field_proven": self.oem_identity_field_proven,
            "source_path_or_url": str(self.source_path),
            "source_page_or_row": f"page={self.source_page_index};line={self.source_row}",
            "source_quote_or_field": self.source_field_label,
            "sha256": self.source_sha256,
            "notes": self.notes,
        }


def _description_from_line(line: str, code: str) -> str:
    desc = line.replace(code, " ")
    desc = re.sub(r"\s+", " ", desc).strip()
    desc = re.sub(r"^[\d\s.,]+", "", desc).strip()
    return desc[:500]


def extract_codes_from_pdf_table(
    *,
    path: Path,
    brand: str,
    source_id: str,
    authority_tier: int,
    source_type: str,
    code_re: re.Pattern[str],
    source_document_title: str,
    source_field_label: str,
    mapping_basis: str,
    oem_identity_field_proven: str,
    extraction_method: str = "pdftotext_layout_line_scan",
) -> list[ExtractedRow]:
    if not path.is_file():
        return []
    digest = sha256_file(path)
    pages = pdf_page_count(path) or 1
    rows: list[ExtractedRow] = []
    for page in range(1, pages + 1):
        text = pdftotext_page(path, page)
        if not text.strip():
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            for m in code_re.finditer(line):
                raw = m.group(1)
                if len(raw) < 3:
                    continue
                rows.append(
                    ExtractedRow(
                        source_id=source_id,
                        brand=brand,
                        authority_tier=authority_tier,
                        source_type=source_type,
                        source_path=path,
                        source_sha256=digest,
                        source_document_title=source_document_title,
                        source_page_index=page,
                        source_row=line_no,
                        source_field_label=source_field_label,
                        raw_source_code=raw,
                        source_item_description=_description_from_line(line, raw),
                        extraction_method=extraction_method,
                        mapping_basis=mapping_basis,
                        oem_identity_field_proven=oem_identity_field_proven,
                    )
                )
    return rows


def extract_insize_product_list(root: Path) -> list[ExtractedRow]:
    path = root / "اندازه گیری/اینسایز/لیست محصولات.pdf"
    return extract_codes_from_pdf_table(
        path=path,
        brand="INSIZE",
        source_id="insize.product_list",
        authority_tier=1,
        source_type="oem_product_list",
        code_re=INSIZE_NUMERIC_CODE,
        source_document_title="لیست فروش محصولات اینسایز",
        source_field_label="کد کالا",
        mapping_basis="oem_field_کد_کالا",
        oem_identity_field_proven="true",
    )


def extract_dasqua_price_list(root: Path) -> list[ExtractedRow]:
    path = root / "اندازه گیری/داسکوا/لیست قیمت داسکوا +10 درصد.pdf"
    return extract_codes_from_pdf_table(
        path=path,
        brand="DASQUA",
        source_id="dasqua.price_list",
        authority_tier=2,
        source_type="authorized_supplier_price_list",
        code_re=DASQUA_NUMERIC_CODE,
        source_document_title="لیست قیمت داسکوا",
        source_field_label="کد کالا",
        mapping_basis="supplier_price_list_order_code_verified_column",
        oem_identity_field_proven="true",
    )


def extract_terma_price_list(root: Path) -> list[ExtractedRow]:
    path = root / "اندازه گیری/ترما/لیست قیمت ترما +25درصد.pdf"
    return extract_codes_from_pdf_table(
        path=path,
        brand="TERMA",
        source_id="terma.price_list",
        authority_tier=2,
        source_type="authorized_supplier_price_list",
        code_re=TERMA_CODE,
        source_document_title="لیست قیمت ترما",
        source_field_label="کد کالا",
        mapping_basis="supplier_price_list_order_code_verified_column",
        oem_identity_field_proven="true",
    )


def extract_ast_image_pdfs(root: Path) -> list[ExtractedRow]:
    """Image-only cooperation PDFs: deterministic text extraction yields no locators."""
    ast_root = root / "آذرصنعت/AST Power"
    profiles = [
        ("ast.spade", "مته برگی/همکاری مته برگی.pdf"),
        ("ast.electric_tapping", "قلاویززن برقی/کاتالوگ همکاری/همکاری قلاویززن برقی.pdf"),
        ("ast.automatic_tapping", "قلاویززن اتومات/همکاری قلاویززن اتومات.pdf"),
    ]
    out: list[ExtractedRow] = []
    for source_id, rel in profiles:
        path = ast_root / rel
        if not path.is_file():
            continue
        digest = sha256_file(path)
        pages = pdf_page_count(path) or 1
        any_text = False
        for page in range(1, min(pages, 50) + 1):
            text = pdftotext_page(path, page)
            if text.strip():
                any_text = True
            for line_no, line in enumerate(text.splitlines(), start=1):
                for m in AST_TEXT_CODE.finditer(line):
                    out.append(
                        ExtractedRow(
                            source_id=source_id,
                            brand="ASTPOWER",
                            authority_tier=3,
                            source_type="ast_supplier_enumerator",
                            source_path=path,
                            source_sha256=digest,
                            source_document_title=path.name,
                            source_page_index=page,
                            source_row=line_no,
                            source_field_label="unverified_sku_column",
                            raw_source_code=m.group(1),
                            source_item_description=_description_from_line(line, m.group(1)),
                            extraction_method="pdftotext_layout_line_scan",
                            mapping_basis="supplier_sku_column_unproven_oem",
                            oem_identity_field_proven="false",
                            notes="image_pdf_or_unproven_identity_field",
                        )
                    )
        if not any_text:
            out.append(
                ExtractedRow(
                    source_id=source_id,
                    brand="ASTPOWER",
                    authority_tier=3,
                    source_type="image_pdf_without_text_layer",
                    source_path=path,
                    source_sha256=digest,
                    source_document_title=path.name,
                    source_page_index=0,
                    source_row=0,
                    source_field_label="n/a",
                    raw_source_code="",
                    source_item_description="",
                    extraction_method="pdftotext_no_text_layer",
                    mapping_basis="not_extractable_without_ocr",
                    oem_identity_field_proven="false",
                    notes="placeholder_row_documents_non_extractable_source",
                )
            )
    return [r for r in out if r.raw_source_code]


def build_all_extractions(root: Path) -> list[dict[str, Any]]:
    rows: list[ExtractedRow] = []
    rows.extend(extract_insize_product_list(root))
    rows.extend(extract_dasqua_price_list(root))
    rows.extend(extract_terma_price_list(root))
    rows.extend(extract_ast_image_pdfs(root))
    return [r.to_registry_dict() for r in rows]
