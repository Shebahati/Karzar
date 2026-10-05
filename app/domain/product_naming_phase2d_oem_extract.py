"""Page-aware INSIZE catalogue extraction (108A/108B) → occurrence + identity registries."""

from __future__ import annotations

import csv
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.domain.product_naming_phase2d import sha256_file

INSIZE_108A_SHA256 = "4b251dbbd6b662e64dcc1703dd373886f8e3df8e3363a5406bc706c8aa85123b"
INSIZE_108B_SHA256 = "31fd0d0eec73bab9cdd750701ec999368536d909e40b340f8420580f7691eb26"

DEFAULT_INSIZE_CATALOG_DIR = Path(
    "/home/shebahati/KaZar/Product and Data Complete/اندازه گیری/اینسایز/کاتالوگ اینسایز"
)

SPECS_DIR = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "architecture"
    / "specs"
    / "product-naming-v1"
)
OCCURRENCES_CSV = SPECS_DIR / "INSIZE_OEM_CODE_OCCURRENCES.csv"
IDENTITY_REGISTRY_CSV = SPECS_DIR / "INSIZE_OEM_PRODUCT_IDENTITY_REGISTRY.csv"

OCCURRENCE_TYPES = frozenset(
    {
        "PRODUCT_ROW",
        "PRODUCT_HEADING_CONTEXT",
        "ACCESSORY_REFERENCE",
        "OPTIONAL_ACCESSORY",
        "CROSS_REFERENCE",
        "UNKNOWN",
    }
)

PRIMARY_AUTHORITY_TYPES = frozenset({"PRODUCT_ROW", "PRODUCT_HEADING_CONTEXT"})
REJECTED_AUTHORITY_TYPES = frozenset(
    {"OPTIONAL_ACCESSORY", "ACCESSORY_REFERENCE", "CROSS_REFERENCE"}
)

_CODE_RE = re.compile(
    r"\b(?:\d{3,4}-[A-Z0-9]{1,10}|\d{4}-[A-Z]{2}\d{2}|[A-Z]{0,4}\d{3,4}-[A-Z0-9]+)\b"
)
_SECTION_RE = re.compile(r"^[A-Z][A-Z0-9 ,/&().'-]{10,}$")
_PRINTED_PAGE_RE = re.compile(r"^\d{1,4}$")

_SECTION_STOPWORDS = frozenset(
    {
        "POPULAR",
        "MODEL",
        "STANDARD DELIVERY",
        "SPECIFICATION",
        "VIDEO",
        "OPTIONAL ACCESSORIES",
        "STANDARD ACCESSORIES",
    }
)


@dataclass(frozen=True)
class OemOccurrence:
    manufacturer_code: str
    source_pdf: str
    source_sha256: str
    pdf_page: int
    printed_page: str
    section_heading: str
    nearest_product_heading: str
    line_context_before: str
    code_line: str
    line_context_after: str
    occurrence_type: str


@dataclass(frozen=True)
class OemProductIdentity:
    manufacturer_code: str
    source_pdf: str
    source_sha256: str
    pdf_page: int
    printed_page: str
    oem_product_heading: str
    oem_family: str
    oem_subtype_or_qualifier: str
    product_occurrence_class: str
    evidence_context: str
    evidence_status: str  # EXACT_PRODUCT_IDENTITY | AMBIGUOUS | INSUFFICIENT


def insize_catalog_paths(catalog_dir: Path | None = None) -> tuple[Path, Path]:
    base = catalog_dir or DEFAULT_INSIZE_CATALOG_DIR
    return base / "108A.pdf", base / "108B.pdf"


def verify_catalog_sha256(pdf_path: Path, expected_sha: str) -> None:
    if sha256_file(pdf_path) != expected_sha:
        raise RuntimeError(f"oem_catalog_sha_mismatch:{pdf_path.name}")


def pdf_pages(pdf_path: Path) -> list[str]:
    proc = subprocess.run(
        ["pdftotext", str(pdf_path), "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 and not proc.stdout:
        raise RuntimeError(f"pdftotext_failed:{pdf_path}:{proc.stderr[:200]}")
    pages = proc.stdout.split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    return pages


def extract_printed_page(page_text: str) -> str:
    lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
    for ln in lines[:6]:
        if _PRINTED_PAGE_RE.fullmatch(ln):
            return ln
    for ln in lines[-6:]:
        if _PRINTED_PAGE_RE.fullmatch(ln):
            return ln
    return "UNKNOWN"


def _normalize_heading(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().upper())


def _is_valid_product_heading(section: str) -> bool:
    sec = _normalize_heading(section)
    if not sec or sec.startswith("CODE "):
        return False
    if sec in _SECTION_STOPWORDS:
        return False
    if len(sec) < 12:
        return False
    keywords = (
        "METER",
        "GAUGE",
        "MICROMETER",
        "CALIPER",
        "LEVEL",
        "INDICATOR",
        "RULE",
        "TAPE",
        "WHEEL",
        "SCALE",
        "MULTIMETER",
        "TACHOMETER",
        "ANEMOMETER",
        "PROTRACTOR",
        "SQUARE",
        "VISE",
        "PLATE",
        "WELD",
        "SETTER",
        "TEMPLATE",
        "SQUARE",
    )
    return any(k in sec for k in keywords)


def _is_bare_code_line(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and stripped.upper() == stripped and bool(_CODE_RE.fullmatch(stripped))


def _classify_occurrence(
    section: str,
    code_line: str,
    prev_line: str,
    next_line: str = "",
) -> str:
    sec = _normalize_heading(section)
    line_u = code_line.upper()
    if _is_bare_code_line(code_line) and (
        _is_bare_code_line(prev_line)
        or _is_bare_code_line(next_line)
        or not (prev_line or "").strip()
    ):
        return "CROSS_REFERENCE"
    if "REFER TO PAGE" in sec:
        return "CROSS_REFERENCE"
    if "(OPTIONAL)" in sec or sec.endswith(" OPTIONAL"):
        return "OPTIONAL_ACCESSORY"
    if "OPTIONAL ACCESSOR" in sec or "STANDARD ACCESSOR" in sec:
        return "ACCESSORY_REFERENCE"
    if "ACCESSOR" in sec and "GAUGE" not in sec and "MICROMETER" not in sec:
        return "ACCESSORY_REFERENCE"
    prev_u = (prev_line or "").strip().upper()
    if prev_u == "CODE" or line_u.startswith("CODE "):
        return "PRODUCT_ROW"
    if _is_valid_product_heading(sec):
        return "PRODUCT_HEADING_CONTEXT"
    return "UNKNOWN"


def _extract_codes_from_line(line: str) -> list[str]:
    return [m.group(0).upper() for m in _CODE_RE.finditer(line)]


def extract_occurrences_from_pdf(
    pdf_path: Path,
    source_sha256: str,
) -> list[OemOccurrence]:
    verify_catalog_sha256(pdf_path, source_sha256)
    pages = pdf_pages(pdf_path)
    source_pdf = str(pdf_path)
    out: list[OemOccurrence] = []
    for pdf_page, page_text in enumerate(pages, start=1):
        printed = extract_printed_page(page_text)
        lines = page_text.splitlines()
        section = ""
        for idx, raw in enumerate(lines):
            line = raw.strip()
            if not line:
                continue
            if _SECTION_RE.match(line) and sum(1 for c in line if c.isalpha()) > 5:
                if _is_valid_product_heading(line) or "(OPTIONAL)" in line.upper():
                    section = line
            for code in _extract_codes_from_line(line):
                prev_line = lines[idx - 1].strip() if idx > 0 else ""
                nxt = lines[idx + 1].strip() if idx + 1 < len(lines) else ""
                occ_type = _classify_occurrence(section, line, prev_line, nxt)
                heading = section if _is_valid_product_heading(section) else section
                out.append(
                    OemOccurrence(
                        manufacturer_code=code,
                        source_pdf=source_pdf,
                        source_sha256=source_sha256,
                        pdf_page=pdf_page,
                        printed_page=printed,
                        section_heading=section,
                        nearest_product_heading=heading,
                        line_context_before=prev_line[:200],
                        code_line=line[:200],
                        line_context_after=nxt[:200],
                        occurrence_type=occ_type,
                    )
                )
    return out


def build_all_occurrences(catalog_dir: Path | None = None) -> list[OemOccurrence]:
    path_a, path_b = insize_catalog_paths(catalog_dir)
    if not path_a.is_file():
        raise FileNotFoundError(path_a)
    occ: list[OemOccurrence] = []
    occ.extend(extract_occurrences_from_pdf(path_a, INSIZE_108A_SHA256))
    if path_b.is_file():
        occ.extend(extract_occurrences_from_pdf(path_b, INSIZE_108B_SHA256))
    return occ


def _canonical_family_key(heading: str) -> str:
    h = _normalize_heading(heading)
    h = h.replace(" AND SLOPE METER", " AND SLOPE METERS")
    h = re.sub(r"\s+", " ", h)
    return h


def _subtype_from_heading(heading: str) -> str:
    h = _normalize_heading(heading)
    if "CYLINDER" in h:
        return "cylinder_square"
    if "GRANITE" in h:
        return "granite_square"
    if "WIDE BASE" in h:
        return "wide_base_square"
    if "ADJUSTABLE" in h and "SQUARE" in h:
        return "adjustable_square"
    if "PLASTIC" in h and "ANGLE" in h:
        return "plastic_angle_square"
    if "TEMPERATURE AND HUMIDITY" in h or "HUMIDITY METER" in h:
        return "temperature_humidity_meter"
    return ""


def select_product_identity(
    code: str,
    occurrences: Iterable[OemOccurrence],
) -> OemProductIdentity | None:
    occ_list = list(occurrences)
    if not occ_list:
        return None

    primary = [
        o
        for o in occ_list
        if o.occurrence_type in PRIMARY_AUTHORITY_TYPES
        and o.occurrence_type not in REJECTED_AUTHORITY_TYPES
    ]
    rejected_only = all(o.occurrence_type in REJECTED_AUTHORITY_TYPES for o in occ_list)
    if not primary:
        if rejected_only:
            best = occ_list[0]
            return OemProductIdentity(
                manufacturer_code=code,
                source_pdf=best.source_pdf,
                source_sha256=best.source_sha256,
                pdf_page=best.pdf_page,
                printed_page=best.printed_page,
                oem_product_heading=best.nearest_product_heading,
                oem_family=best.nearest_product_heading,
                oem_subtype_or_qualifier=_subtype_from_heading(best.nearest_product_heading),
                product_occurrence_class="accessory_only",
                evidence_context="accessory_only_occurrence",
                evidence_status="INSUFFICIENT",
            )
        return OemProductIdentity(
            manufacturer_code=code,
            source_pdf=occ_list[0].source_pdf,
            source_sha256=occ_list[0].source_sha256,
            pdf_page=occ_list[0].pdf_page,
            printed_page=occ_list[0].printed_page,
            oem_product_heading=occ_list[0].nearest_product_heading,
            oem_family=occ_list[0].nearest_product_heading,
            oem_subtype_or_qualifier="",
            product_occurrence_class=occ_list[0].occurrence_type,
            evidence_context="no_primary_product_occurrence",
            evidence_status="INSUFFICIENT",
        )

    def rank(o: OemOccurrence) -> tuple[int, int]:
        type_rank = 0 if o.occurrence_type == "PRODUCT_ROW" else 1
        return (type_rank, o.pdf_page)

    by_heading: dict[str, list[OemOccurrence]] = defaultdict(list)
    for o in primary:
        heading = _canonical_family_key(o.nearest_product_heading) or "UNSPECIFIED"
        by_heading[heading].append(o)

    if len(by_heading) > 1:
        headings = sorted(by_heading)
        first = min(primary, key=rank)
        return OemProductIdentity(
            manufacturer_code=code,
            source_pdf=first.source_pdf,
            source_sha256=first.source_sha256,
            pdf_page=first.pdf_page,
            printed_page=first.printed_page,
            oem_product_heading=first.nearest_product_heading,
            oem_family=first.nearest_product_heading,
            oem_subtype_or_qualifier=_subtype_from_heading(first.nearest_product_heading),
            product_occurrence_class="conflicting_headings",
            evidence_context=f"ambiguous_headings:{';'.join(headings[:5])}",
            evidence_status="AMBIGUOUS",
        )

    chosen = min(primary, key=rank)
    heading = chosen.nearest_product_heading
    family = heading
    if "REFER TO PAGE" in _normalize_heading(heading):
        family = heading.split("REFER")[0].strip()
    return OemProductIdentity(
        manufacturer_code=code,
        source_pdf=chosen.source_pdf,
        source_sha256=chosen.source_sha256,
        pdf_page=chosen.pdf_page,
        printed_page=chosen.printed_page,
        oem_product_heading=heading,
        oem_family=family,
        oem_subtype_or_qualifier=_subtype_from_heading(heading),
        product_occurrence_class=chosen.occurrence_type,
        evidence_context=chosen.code_line[:120],
        evidence_status="EXACT_PRODUCT_IDENTITY",
    )


def build_identity_registry(
    occurrences: list[OemOccurrence],
) -> dict[str, OemProductIdentity]:
    by_code: dict[str, list[OemOccurrence]] = defaultdict(list)
    for o in occurrences:
        by_code[o.manufacturer_code].append(o)
    out: dict[str, OemProductIdentity] = {}
    for code in sorted(by_code):
        ident = select_product_identity(code, by_code[code])
        if ident:
            out[code] = ident
    return out


def write_occurrences_csv(path: Path, occurrences: list[OemOccurrence]) -> None:
    fields = [
        "manufacturer_code",
        "source_pdf",
        "source_sha256",
        "pdf_page",
        "printed_page",
        "section_heading",
        "nearest_product_heading",
        "line_context_before",
        "code_line",
        "line_context_after",
        "occurrence_type",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for o in sorted(occurrences, key=lambda x: (x.manufacturer_code, x.pdf_page, x.code_line)):
            w.writerow(
                {
                    "manufacturer_code": o.manufacturer_code,
                    "source_pdf": o.source_pdf,
                    "source_sha256": o.source_sha256,
                    "pdf_page": str(o.pdf_page),
                    "printed_page": o.printed_page,
                    "section_heading": o.section_heading,
                    "nearest_product_heading": o.nearest_product_heading,
                    "line_context_before": o.line_context_before,
                    "code_line": o.code_line,
                    "line_context_after": o.line_context_after,
                    "occurrence_type": o.occurrence_type,
                }
            )


def write_identity_registry_csv(path: Path, registry: dict[str, OemProductIdentity]) -> None:
    fields = [
        "manufacturer_code",
        "source_pdf",
        "source_sha256",
        "pdf_page",
        "printed_page",
        "OEM_product_heading",
        "OEM_family",
        "OEM_subtype_or_qualifier",
        "product_occurrence_class",
        "evidence_context",
        "evidence_status",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for code in sorted(registry):
            r = registry[code]
            w.writerow(
                {
                    "manufacturer_code": r.manufacturer_code,
                    "source_pdf": r.source_pdf,
                    "source_sha256": r.source_sha256,
                    "pdf_page": str(r.pdf_page),
                    "printed_page": r.printed_page,
                    "OEM_product_heading": r.oem_product_heading,
                    "OEM_family": r.oem_family,
                    "OEM_subtype_or_qualifier": r.oem_subtype_or_qualifier,
                    "product_occurrence_class": r.product_occurrence_class,
                    "evidence_context": r.evidence_context,
                    "evidence_status": r.evidence_status,
                }
            )


def load_identity_registry(path: Path | None = None) -> dict[str, OemProductIdentity]:
    src = path or IDENTITY_REGISTRY_CSV
    out: dict[str, OemProductIdentity] = {}
    if not src.is_file():
        return out
    with src.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            code = (row.get("manufacturer_code") or "").strip().upper()
            if not code:
                continue
            out[code] = OemProductIdentity(
                manufacturer_code=code,
                source_pdf=(row.get("source_pdf") or "").strip(),
                source_sha256=(row.get("source_sha256") or "").strip(),
                pdf_page=int(row.get("pdf_page") or 0),
                printed_page=(row.get("printed_page") or "").strip(),
                oem_product_heading=(row.get("OEM_product_heading") or "").strip(),
                oem_family=(row.get("OEM_family") or "").strip(),
                oem_subtype_or_qualifier=(row.get("OEM_subtype_or_qualifier") or "").strip(),
                product_occurrence_class=(row.get("product_occurrence_class") or "").strip(),
                evidence_context=(row.get("evidence_context") or "").strip(),
                evidence_status=(row.get("evidence_status") or "").strip(),
            )
    return out
