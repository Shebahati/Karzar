"""PDF/catalog provenance records (stdlib only; no new PDF dependency)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Any

from . import MultisourceError


@dataclass
class CatalogPdfRecord:
    source_url: str
    file_sha256: str
    page_count: int | None
    catalog_title: str
    catalog_date: str
    exact_sku_or_model_index: str
    matched_page_number: int | None
    text_evidence: str
    image_identity_or_bounding_ref: str
    identity_status: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


_PDF_PAGE_RE = re.compile(rb"/Type\s*/Page\b")


def estimate_pdf_page_count(data: bytes) -> int | None:
    if not data.startswith(b"%PDF"):
        return None
    # Heuristic only; exact count may require a PDF library (not added).
    return len(_PDF_PAGE_RE.findall(data)) or None


def build_pdf_record(
    *,
    source_url: str,
    data: bytes,
    catalog_title: str = "",
    catalog_date: str = "",
    sku: str,
    matched_page_number: int | None,
    text_evidence: str,
    image_ref: str,
) -> CatalogPdfRecord:
    if not data.startswith(b"%PDF"):
        raise MultisourceError("pdf", "not a PDF payload")
    sku_ok = bool(sku) and sku.casefold() in (text_evidence or "").casefold()
    if not sku_ok:
        return CatalogPdfRecord(
            source_url=source_url,
            file_sha256=sha256_bytes(data),
            page_count=estimate_pdf_page_count(data),
            catalog_title=catalog_title,
            catalog_date=catalog_date,
            exact_sku_or_model_index="",
            matched_page_number=matched_page_number,
            text_evidence=text_evidence[:2000],
            image_identity_or_bounding_ref=image_ref,
            identity_status="rejected_family_or_missing_exact_sku",
            notes="family-page proximity is not exact product identity",
        )
    return CatalogPdfRecord(
        source_url=source_url,
        file_sha256=sha256_bytes(data),
        page_count=estimate_pdf_page_count(data),
        catalog_title=catalog_title,
        catalog_date=catalog_date,
        exact_sku_or_model_index=sku,
        matched_page_number=matched_page_number,
        text_evidence=text_evidence[:2000],
        image_identity_or_bounding_ref=image_ref,
        identity_status="exact_sku_or_model_confirmed",
        notes="",
    )
