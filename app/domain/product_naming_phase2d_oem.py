"""Phase 2D — INSIZE OEM semantic authority (108A primary, 108B fallback).

Read-only governance: compares persisted Product Type to official catalogue identity.
"""

from __future__ import annotations

import csv
import re
import subprocess
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.domain.product_naming_phase2d import Phase2DAuditRow, sha256_file

INSIZE_108A_SHA256 = "4b251dbbd6b662e64dcc1703dd373886f8e3df8e3363a5406bc706c8aa85123b"
INSIZE_108B_SHA256 = "31fd0d0eec73bab9cdd750701ec999368536d909e40b340f8420580f7691eb26"

DEFAULT_INSIZE_CATALOG_DIR = Path(
    "/home/shebahati/KaZar/Product and Data Complete/اندازه گیری/اینسایز/کاتالوگ اینسایز"
)
OEM_CODE_INDEX_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "architecture"
    / "specs"
    / "product-naming-v1"
    / "INSIZE_108A_OEM_CODE_INDEX.csv"
)

OEM_SEMANTIC_STATUSES = frozenset(
    {
        "OEM_SEMANTIC_MATCH",
        "OEM_SEMANTIC_BROADER_BUT_ACCEPTABLE",
        "OEM_PRODUCT_TYPE_CONFLICT",
        "OEM_CANONICAL_TITLE_CONFLICT",
        "OEM_MULTI_FUNCTION_TITLE_CONFLICT",
        "OEM_EVIDENCE_INSUFFICIENT",
    }
)

READY_OEM_STATUSES = frozenset({"OEM_SEMANTIC_MATCH", "OEM_SEMANTIC_BROADER_BUT_ACCEPTABLE"})

_CODE_RE = re.compile(
    r"\b(?:\d{3,4}-[A-Z0-9]{1,10}|\d{4}-[A-Z]{2}\d{2}|[A-Z]{0,4}\d{3,4}-[A-Z0-9]+)\b"
)
_SECTION_RE = re.compile(r"^[A-Z][A-Z0-9 ,/&().'-]{10,}$")
_SECTION_STOPWORDS = frozenset(
    {
        "POPULAR",
        "MODEL",
        "STANDARD DELIVERY",
        "SPECIFICATION",
        "VIDEO",
        "OPTIONAL ACCESSORIES",
        "STANDARD ACCESSORIES",
        "CODE",
    }
)

# Higher index = stronger family signal when multiple sections mention a code.
_FAMILY_PRECEDENCE = (
    "DIGITAL LEVELS AND SLOPE METERS",
    "DIGITAL LEVEL AND SLOPE METER",
    "TEMPERATURE AND HUMIDITY METER",
    "DIGITAL OUTSIDE MICROMETER",
    "OUTSIDE MICROMETER",
    "INSIDE MICROMETER",
    "DEPTH MICROMETER",
    "DIGITAL CALIPER",
    "VERNIER CALIPER",
    "DIAL INDICATOR",
    "TEST INDICATOR",
    "HEIGHT GAUGE",
    "DEPTH GAUGE",
    "PIN GAUGE",
    "FEELER GAUGE",
    "PROTRACTOR",
)


@dataclass(frozen=True)
class OemCodeRecord:
    manufacturer_code: str
    oem_source: str
    oem_source_sha256: str
    oem_page_pdf: str
    oem_page_printed: str
    oem_section: str
    oem_product_heading: str
    oem_category_or_family: str
    oem_code: str


def insize_catalog_paths(catalog_dir: Path | None = None) -> tuple[Path, Path]:
    base = catalog_dir or DEFAULT_INSIZE_CATALOG_DIR
    return base / "108A.pdf", base / "108B.pdf"


def _pdf_to_text(pdf_path: Path) -> list[str]:
    proc = subprocess.run(
        ["pdftotext", str(pdf_path), "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 and not proc.stdout:
        raise RuntimeError(f"pdftotext_failed:{pdf_path}:{proc.stderr[:200]}")
    return proc.stdout.splitlines()


def _normalize_heading(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().upper())


def _is_valid_section(section: str) -> bool:
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
    )
    return any(k in sec for k in keywords)


def _section_score(section: str) -> int:
    sec = _normalize_heading(section)
    if not _is_valid_section(sec):
        return -1
    for idx, fam in enumerate(_FAMILY_PRECEDENCE):
        if fam in sec:
            return len(_FAMILY_PRECEDENCE) - idx
    return 1


def _extract_codes_from_line(line: str) -> list[str]:
    return [m.group(0) for m in _CODE_RE.finditer(line)]


def build_insize_oem_code_index(
    *,
    catalog_dir: Path | None = None,
) -> dict[str, OemCodeRecord]:
    """Scan official INSIZE PDF catalogues and index OEM codes → family heading."""
    path_108a, path_108b = insize_catalog_paths(catalog_dir)
    if not path_108a.is_file():
        raise FileNotFoundError(path_108a)

    hits: dict[str, list[tuple[int, str, str, str]]] = defaultdict(list)
    for pdf_path, sha in (
        (path_108a, INSIZE_108A_SHA256),
        (path_108b, INSIZE_108B_SHA256),
    ):
        if not pdf_path.is_file():
            continue
        if sha256_file(pdf_path) != sha:
            raise RuntimeError(f"oem_catalog_sha_mismatch:{pdf_path.name}")
        lines = _pdf_to_text(pdf_path)
        section = ""
        for line_no, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            if _SECTION_RE.match(line) and sum(1 for c in line if c.isalpha()) > 5:
                if _is_valid_section(line):
                    section = line
            for code in _extract_codes_from_line(line):
                page_est = str(max(1, line_no // 180))
                hits[code.upper()].append(
                    (line_no, section, pdf_path.name, page_est),
                )

    out: dict[str, OemCodeRecord] = {}
    for code, occurrences in hits.items():
        valid = [t for t in occurrences if _section_score(t[1]) >= 0]
        pool = valid or occurrences
        best = max(pool, key=lambda t: (_section_score(t[1]), -t[0]))
        line_no, section, src_name, page_est = best
        heading = section or "UNSPECIFIED SECTION"
        family = heading
        if "REFER TO PAGE" in heading:
            family = heading.split("REFER")[0].strip()
        sha = INSIZE_108A_SHA256 if src_name == "108A.pdf" else INSIZE_108B_SHA256
        out[code] = OemCodeRecord(
            manufacturer_code=code,
            oem_source=str((catalog_dir or DEFAULT_INSIZE_CATALOG_DIR) / src_name),
            oem_source_sha256=sha,
            oem_page_pdf=page_est,
            oem_page_printed=page_est,
            oem_section=heading,
            oem_product_heading=heading,
            oem_category_or_family=family,
            oem_code=code,
        )
    return out


def load_oem_code_index(path: Path | None = None) -> dict[str, OemCodeRecord]:
    src = path or OEM_CODE_INDEX_PATH
    out: dict[str, OemCodeRecord] = {}
    if not src.is_file():
        return out
    with src.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            code = (row.get("manufacturer_code") or row.get("oem_code") or "").strip().upper()
            if not code:
                continue
            out[code] = OemCodeRecord(
                manufacturer_code=code,
                oem_source=(row.get("oem_source") or "").strip(),
                oem_source_sha256=(row.get("oem_source_sha256") or "").strip(),
                oem_page_pdf=(row.get("oem_page_pdf") or "").strip(),
                oem_page_printed=(row.get("oem_page_printed") or "").strip(),
                oem_section=(row.get("oem_section") or "").strip(),
                oem_product_heading=(row.get("oem_product_heading") or "").strip(),
                oem_category_or_family=(row.get("oem_category_or_family") or "").strip(),
                oem_code=code,
            )
    return out


def write_oem_code_index(path: Path, records: Mapping[str, OemCodeRecord]) -> None:
    fields = [
        "manufacturer_code",
        "oem_source",
        "oem_source_sha256",
        "oem_page_pdf",
        "oem_page_printed",
        "oem_section",
        "oem_product_heading",
        "oem_category_or_family",
        "oem_code",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for code in sorted(records):
            rec = records[code]
            w.writerow(
                {
                    "manufacturer_code": rec.manufacturer_code,
                    "oem_source": rec.oem_source,
                    "oem_source_sha256": rec.oem_source_sha256,
                    "oem_page_pdf": rec.oem_page_pdf,
                    "oem_page_printed": rec.oem_page_printed,
                    "oem_section": rec.oem_section,
                    "oem_product_heading": rec.oem_product_heading,
                    "oem_category_or_family": rec.oem_category_or_family,
                    "oem_code": rec.oem_code,
                }
            )


def _allowed_product_types_for_oem(family: str) -> frozenset[str] | None:
    f = _normalize_heading(family)
    if "TEMPERATURE AND HUMIDITY" in f:
        return frozenset()
    if "DIGITAL LEVEL" in f or "SLOPE METER" in f:
        return frozenset({"DIGITAL_LEVEL", "LEVEL"})
    if "OUTSIDE MICROMETER" in f:
        return frozenset({"OUTSIDE_MICROMETER"})
    if "INSIDE MICROMETER" in f:
        return frozenset({"INSIDE_MICROMETER"})
    if "DEPTH MICROMETER" in f:
        return frozenset({"DEPTH_MICROMETER"})
    if "VERNIER CALIPER" in f or "DIGITAL CALIPER" in f or " CALIPER" in f:
        return frozenset(
            {
                "GEN_CALIPER",
                "BLADE_CALIPER",
                "OFFSET_CALIPER",
                "DEPTH_GAUGE",
                "HOOK_CALIPER",
                "POINT_CALIPER",
                "EXTERNAL_GROOVE_CALIPER",
                "INTERNAL_GROOVE_CALIPER",
                "INTERNAL_POINT_CALIPER",
                "INSIDE_KNIFE_EDGE_CALIPER",
                "INTERCHANGEABLE_POINT_CALIPER",
                "TUBE_THICKNESS_CALIPER",
                "INDICATING_CALIPER",
                "GEAR_TOOTH_CALIPER",
            }
        )
    if "DIAL INDICATOR" in f:
        return frozenset({"DIAL_INDICATOR"})
    if "TEST INDICATOR" in f or "LEVER TYPE DIAL TEST" in f:
        return frozenset({"TEST_INDICATOR"})
    if "HEIGHT GAUGE" in f:
        return frozenset({"HEIGHT_GAUGE"})
    if "DEPTH GAUGE" in f:
        return frozenset({"DEPTH_GAUGE"})
    if "PIN GAUGE" in f:
        return frozenset({"PIN_GAUGE"})
    if "FEELER GAUGE" in f:
        return frozenset({"FEELER_GAUGE", "FEELER_GAUGE_SET"})
    if "PROTRACTOR" in f and "LEVEL" not in f:
        return frozenset({"PROTRACTOR"})
    if "ANGLE" in f and "SQUARE" in f:
        return frozenset({"ENGINEERS_SQUARE", "ANGLE_GAUGE"})
    if "SQUARE" in f:
        return frozenset({"ENGINEERS_SQUARE"})
    if "LEVEL" in f and "DIGITAL" not in f:
        return frozenset({"LEVEL"})
    if "ANEMOMETER" in f or "AIR VELOCITY" in f:
        return frozenset({"ANEMOMETER"})
    if "MULTIMETER" in f:
        return frozenset({"DIGITAL_MULTIMETER"})
    if "VOLTAGE" in f and "TESTER" in f:
        return frozenset({"VOLTAGE_TESTER"})
    if "TACHOMETER" in f or "TACHO" in f:
        return frozenset({"TACHOMETER"})
    if "MOISTURE" in f and "TEMPERATURE" not in f:
        return frozenset({"MOISTURE_METER"})
    if "SCALE" in f or "BALANCE" in f:
        return frozenset({"DIGITAL_SCALE"})
    if "LASER DISTANCE" in f or "LASER METER" in f:
        return frozenset({"LASER_DISTANCE_METER"})
    if "MEASURING WHEEL" in f or "WHEEL" in f and "MEASURING" in f:
        return frozenset({"MEASURING_WHEEL"})
    if "STEEL RULE" in f or "STEEL RULER" in f:
        return frozenset({"STEEL_RULE"})
    if "MEASURING TAPE" in f:
        return frozenset({"MEASURING_TAPE"})
    if "WELD" in f:
        return frozenset({"WELDING_GAUGE", "FILLET_WELD_GAUGE"})
    if "CHAMFER" in f:
        return frozenset({"CHAMFER_GAUGE"})
    if "COATING THICKNESS" in f:
        return frozenset({"COATING_THICKNESS_GAUGE"})
    if "WET FILM" in f:
        return frozenset({"WET_FILM_THICKNESS_GAUGE"})
    if "THREAD PITCH" in f or "PITCH GAUGE" in f:
        return frozenset({"THREAD_PITCH_GAUGE", "GEAR_TOOTH_PITCH_GAUGE"})
    if "THREAD RING" in f:
        return frozenset({"THREAD_RING_GAUGE"})
    if "THREAD PLUG" in f:
        return frozenset({"THREAD_PLUG_GAUGE"})
    if "WIRE GAUGE" in f:
        return frozenset({"WIRE_GAUGE"})
    if "ZERO SETTER" in f or "ZERO SET" in f:
        return frozenset({"ZERO_SETTER"})
    return None


def _recommended_pt_from_oem(family: str) -> str:
    allowed = _allowed_product_types_for_oem(family)
    if not allowed:
        if "TEMPERATURE AND HUMIDITY" in _normalize_heading(family):
            return "HOLD_MULTI_FUNCTION_TITLE_POLICY"
        return ""
    return sorted(allowed)[0]


def evaluate_oem_semantic(
    *,
    product_type_code: str,
    canonical_title_fa: str,
    oem: OemCodeRecord | None,
) -> tuple[str, str, str, str, str]:
    """Return semantic_match_status, conflict_reason, hold_terminal, recommended_pt, recommended_title."""
    code_pt = (product_type_code or "").strip()
    if oem is None:
        return (
            "OEM_EVIDENCE_INSUFFICIENT",
            "no_official_catalogue_locator",
            "HOLD_OEM_SEMANTIC_EVIDENCE_MISSING",
            "",
            "",
        )

    family = oem.oem_category_or_family or oem.oem_product_heading
    norm_family = _normalize_heading(family)

    if "TEMPERATURE AND HUMIDITY" in norm_family:
        title = canonical_title_fa or ""
        if "رطوبت" in title and "دما" not in title and "حرارت" not in title:
            return (
                "OEM_MULTI_FUNCTION_TITLE_CONFLICT",
                "oem_temperature_and_humidity_meter_title_drops_temperature_function",
                "HOLD_MULTI_FUNCTION_IDENTITY_CONFLICT",
                "",
                "دما و رطوبت‌سنج",
            )

    allowed = _allowed_product_types_for_oem(family)
    if allowed is not None and len(allowed) == 0:
        return (
            "OEM_MULTI_FUNCTION_TITLE_CONFLICT",
            "oem_multi_function_identity_not_mapped_to_single_product_type",
            "HOLD_MULTI_FUNCTION_IDENTITY_CONFLICT",
            "",
            "",
        )

    if allowed is None:
        return (
            "OEM_EVIDENCE_INSUFFICIENT",
            "oem_family_not_governed_in_phase2d_mapper",
            "HOLD_OEM_SEMANTIC_EVIDENCE_MISSING",
            "",
            "",
        )

    if code_pt in allowed:
        if "DIGITAL" in norm_family and code_pt in allowed:
            return (
                "OEM_SEMANTIC_MATCH",
                "persisted_product_type_matches_oem_family",
                "",
                code_pt,
                canonical_title_fa,
            )
        return (
            "OEM_SEMANTIC_MATCH",
            "persisted_product_type_matches_oem_family",
            "",
            code_pt,
            canonical_title_fa,
        )

    # Digital subtype on micrometer/caliper is acceptable when base type matches.
    if code_pt == "OUTSIDE_MICROMETER" and "MICROMETER" in norm_family:
        return (
            "OEM_SEMANTIC_BROADER_BUT_ACCEPTABLE",
            "digital_oem_subtype_maps_to_outside_micrometer_product_type",
            "",
            "OUTSIDE_MICROMETER",
            canonical_title_fa,
        )

    rec = _recommended_pt_from_oem(family)
    return (
        "OEM_PRODUCT_TYPE_CONFLICT",
        f"persisted_{code_pt}_not_in_oem_allowed_{','.join(sorted(allowed))}",
        "HOLD_PRODUCT_TYPE_AUTHORITY_CONFLICT",
        rec,
        "",
    )


def oem_authority_row(
    audit: Phase2DAuditRow,
    oem: OemCodeRecord | None,
    semantic_status: str,
    conflict_reason: str,
    recommended_pt: str,
    recommended_title: str,
) -> dict[str, str]:
    eligible = "yes" if semantic_status in READY_OEM_STATUSES else "no"
    return {
        "product_id": str(audit.product_id),
        "manufacturer_code": audit.manufacturer_code,
        "persisted_product_type_id": str(audit.product_type_id or ""),
        "persisted_product_type_code": audit.product_type_code or "",
        "persisted_product_type_name_fa": audit.product_type_name_fa or "",
        "canonical_title_fa": audit.canonical_title_fa or "",
        "oem_source": oem.oem_source if oem else "",
        "oem_source_sha256": oem.oem_source_sha256 if oem else "",
        "oem_page_pdf": oem.oem_page_pdf if oem else "",
        "oem_page_printed": oem.oem_page_printed if oem else "",
        "oem_section": oem.oem_section if oem else "",
        "oem_product_heading": oem.oem_product_heading if oem else "",
        "oem_category_or_family": oem.oem_category_or_family if oem else "",
        "oem_code": oem.oem_code if oem else audit.manufacturer_code,
        "semantic_match_status": semantic_status,
        "semantic_conflict_reason": conflict_reason,
        "recommended_product_type_code": recommended_pt,
        "recommended_canonical_title_fa": recommended_title,
        "candidate_eligible_after_oem_gate": eligible,
    }


def apply_oem_semantic_holds(
    audits: list[Phase2DAuditRow],
    oem_index: Mapping[str, OemCodeRecord],
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    authority_rows: list[dict[str, str]] = []
    counts: dict[str, int] = defaultdict(int)
    pre_ready = sum(1 for a in audits if a.terminal_classification == "READY_RENAME")

    for audit in audits:
        if audit.terminal_classification != "READY_RENAME":
            continue
        key = (audit.manufacturer_code or "").strip().upper()
        oem = oem_index.get(key)
        status, reason, hold, rec_pt, rec_title = evaluate_oem_semantic(
            product_type_code=audit.product_type_code,
            canonical_title_fa=audit.canonical_title_fa,
            oem=oem,
        )
        counts[status] += 1
        authority_rows.append(
            oem_authority_row(audit, oem, status, reason, rec_pt, rec_title)
        )
        if status not in READY_OEM_STATUSES and hold:
            audit.terminal_classification = hold
            audit.classification_reason = reason

    meta = {
        "pre_oem_READY": pre_ready,
        "OEM_semantic_validated_rows": len(authority_rows),
        **{k: counts[k] for k in sorted(counts)},
    }
    return authority_rows, meta


@lru_cache(maxsize=1)
def default_oem_index() -> dict[str, OemCodeRecord]:
    return load_oem_code_index()
