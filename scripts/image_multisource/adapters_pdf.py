"""Official catalog PDF adapter (EU261 / poppler CLI; no new Python deps)."""

from __future__ import annotations

import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import MultisourceError
from .pdf import build_pdf_record, sha256_bytes
from .sku_norm import normalize_sku, skus_in_text


@dataclass(frozen=True)
class PdfSkuHit:
    sku: str
    page_number: int
    page_text: str
    other_skus_on_page: tuple[str, ...]


@dataclass(frozen=True)
class ExactProductCropProvenance:
    catalog_url: str
    catalog_sha256: str
    pdf_page_number: int
    printed_page_number: str
    bounding_box: str
    crop_sha256: str
    crop_width: int
    crop_height: int
    target_sku_text_box: str
    product_block_identity: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def pdf_tools_available() -> bool:
    for tool in ("pdftotext", "pdftoppm", "pdfinfo"):
        try:
            subprocess.run([tool, "-v"], capture_output=True, check=False)
        except FileNotFoundError:
            return False
    return True


def pdf_page_count(pdf_path: Path) -> int:
    proc = subprocess.run(
        ["pdfinfo", str(pdf_path)], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        raise MultisourceError("pdf", f"pdfinfo failed: {proc.stderr.strip()}")
    for line in proc.stdout.splitlines():
        if line.lower().startswith("pages:"):
            return int(line.split(":", 1)[1].strip())
    raise MultisourceError("pdf", "pdfinfo missing Pages field")


def extract_pdf_text(pdf_path: Path, *, first: int | None = None, last: int | None = None) -> str:
    cmd = ["pdftotext", "-layout"]
    if first is not None:
        cmd.extend(["-f", str(first)])
    if last is not None:
        cmd.extend(["-l", str(last)])
    cmd.extend([str(pdf_path), "-"])
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise MultisourceError("pdf", f"pdftotext failed: {proc.stderr.strip()}")
    return proc.stdout


def index_skus_in_pdf(
    pdf_path: Path,
    skus: list[str],
    *,
    page_texts: list[str] | None = None,
) -> dict[str, PdfSkuHit]:
    """Map governed SKU → first page hit. Uses injected page_texts in tests."""
    wanted = {normalize_sku(s): s for s in skus if (s or "").strip()}
    if not wanted:
        return {}
    if page_texts is None:
        full = extract_pdf_text(pdf_path)
        pages = full.split("\f")
    else:
        pages = list(page_texts)
    out: dict[str, PdfSkuHit] = {}
    for idx, page in enumerate(pages, start=1):
        present = skus_in_text(page)
        for norm, original in wanted.items():
            if norm in out:
                continue
            if norm in present or norm in page.casefold():
                others = tuple(sorted(t for t in present if t != norm))
                out[norm] = PdfSkuHit(
                    sku=original,
                    page_number=idx,
                    page_text=page[:4000],
                    other_skus_on_page=others,
                )
        if len(out) == len(wanted):
            break
    return out


def render_pdf_page_jpeg(pdf_path: Path, page_number: int, dest_stem: Path, *, dpi: int = 110) -> Path:
    dest_stem.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            "pdftoppm",
            "-f",
            str(page_number),
            "-l",
            str(page_number),
            "-jpeg",
            "-r",
            str(dpi),
            str(pdf_path),
            str(dest_stem),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise MultisourceError("pdf", f"pdftoppm failed: {proc.stderr.strip()}")
    matches = sorted(dest_stem.parent.glob(f"{dest_stem.name}-*.jpg"))
    if not matches:
        raise MultisourceError("pdf", f"pdftoppm produced no jpeg for page {page_number}")
    return matches[0]


def discover_pdf_sku(
    *,
    pdf_path: Path,
    pdf_bytes: bytes,
    catalog_url: str,
    sku: str,
    hit: PdfSkuHit | None,
    rendered_page_path: Path | None,
    exact_crop: ExactProductCropProvenance | None = None,
) -> dict[str, Any]:
    """PDF discovery. Whole-page renders are catalog_page_evidence only."""
    if hit is None:
        return {
            "status": "not_found",
            "exact_sku_ok": False,
            "false_match": False,
            "page_identity_ok": False,
            "parser_drift": False,
            "notes": "sku absent from catalog text index",
            "evidence_kind": "",
        }
    multi = bool(hit.other_skus_on_page)
    record = build_pdf_record(
        source_url=catalog_url,
        data=pdf_bytes,
        catalog_title="INSIZE Measuring Instruments Catalogue EU261",
        catalog_date="2024-2025",
        sku=sku,
        matched_page_number=hit.page_number,
        text_evidence=hit.page_text,
        image_ref=(
            f"page-{hit.page_number}-render:{rendered_page_path.name}"
            if rendered_page_path
            else f"page-{hit.page_number}"
        ),
    )
    if record.identity_status != "exact_sku_or_model_confirmed":
        return {
            "status": "rejected",
            "exact_sku_ok": False,
            "false_match": False,
            "page_identity_ok": False,
            "parser_drift": False,
            "pdf_record": record.to_dict(),
            "notes": record.identity_status,
            "evidence_kind": "",
        }

    detail = f"{catalog_url}#page={hit.page_number}"
    base = {
        "status": "matched",
        "exact_sku_ok": True,
        "false_match": False,
        "page_identity_ok": True,
        "parser_drift": False,
        "matched_page_number": hit.page_number,
        "multi_sku_page": multi,
        "multi_product_blocks": multi or True,  # fail-closed: page may have blocks outside wanted set
        "source_detail_url": detail,
        "pdf_record": record.to_dict(),
        "pdf_sha256": sha256_bytes(pdf_bytes),
        "local_page_image": str(rendered_page_path) if rendered_page_path else "",
    }

    if exact_crop is not None:
        return {
            **base,
            "evidence_kind": "exact_product_image_crop",
            "discovery_status": "candidate_ready",
            "eligible_for_automatic_acceptance": "true",
            "match_basis": "exact_sku_official_catalog",
            "source_image_url": detail,
            "crop_provenance": exact_crop.to_dict(),
            "notes": "exact_product_image_crop",
        }

    # Whole-page render is review evidence only — never automatic product image.
    return {
        **base,
        "evidence_kind": "catalog_page_evidence",
        "discovery_status": "manual_review",
        "eligible_for_automatic_acceptance": "false",
        "match_basis": "catalog_page_evidence",
        "source_image_url": detail,
        "reason_code": "catalog_page_requires_product_crop",
        "notes": "catalog_page_requires_product_crop",
    }


_CODE_RE = re.compile(
    r"(?ix)(?<![0-9A-Z])("
    r"[A-Z]{2,}[A-Z0-9]*-(?:[A-Z]{0,4}\d+[A-Z0-9]*|\d+[A-Z][A-Z0-9]*)"
    r"|"
    r"\d{3,5}-(?:[A-Z]\d+[A-Z0-9]*|\d{1,5}[A-Z][A-Z0-9]*)"
    r"|"
    r"\d{3,5}-\d{1,5}"
    r")(?![0-9A-Z])"
)


def index_dasqua_sitemap_urls(urls: list[str]) -> dict[str, str]:
    """Map uppercase SKU token → product URL from Dasqua-style slug URLs."""
    out: dict[str, str] = {}
    for url in urls:
        for token in _CODE_RE.findall(url):
            out.setdefault(token.upper(), url)
    return out
