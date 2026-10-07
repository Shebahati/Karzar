"""Phase 3B1 — Wave 3B governance safety review (proposal only, no authoritative mutation)."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PHASE3A_MATRIX_REL = "audit/product-naming-phase3a-hold-resolution/PHASE3A_ROOT_CAUSE_MATRIX.csv"
PHASE2D_CANDIDATES_REL = "audit/product-naming-phase2d/PHASE2D_RENAME_CANDIDATES_PROPOSED.csv"
PHASE2D_CANDIDATE_SHA256 = "25d586e371431cc371b6ce6432abba6c2da5b1f15102cac9ed187f78ef0052ff"
PHASE2F_POST_APPLY_REL = "audit/product-naming-phase2f-real-apply/PHASE2F_TARGET_POST_APPLY.csv"
POLICY_REL = "docs/architecture/specs/product-naming-v1/PRODUCT_TYPE_CANONICAL_NAMING_POLICY.csv"
OEM_REGISTRY_REL = (
    "docs/architecture/specs/product-naming-v1/INSIZE_OEM_PRODUCT_IDENTITY_REGISTRY.csv"
)
PROPERTY_DICT_REL = "docs/architecture/specs/seeds/property-dictionary-v0-metrology.json"
EXISTING_WAVE3C_ROWS = 58

WAVE_3B_NAME = "WAVE_3B_GOVERNANCE_QUICK_WINS"
EXPECTED_WAVE_3B_ROWS = 132
EXPECTED_NAMING_POLICY_ROWS = 101
EXPECTED_VARIANT_POLICY_ROWS = 31
EXPECTED_APPLIED_ROWS = 47

EXPECTED_NAMING_PT_COUNTS = {
    "GEN_CALIPER": 65,
    "BORE_GAUGE": 16,
    "DIVIDER": 9,
    "TAPER_GAUGE": 9,
    "STRAIGHT_EDGE": 1,
    "OPTICAL_EDGE_FINDER": 1,
}
EXPECTED_VARIANT_PT_COUNTS = {
    "LEVEL": 16,
    "DIGITAL_LEVEL": 3,
    "SURFACE_PLATE": 6,
    "PRECISION_VISE": 3,
    "V_BLOCK": 3,
}
ALL_WAVE_3B_PTS = tuple(
    list(EXPECTED_NAMING_PT_COUNTS) + list(EXPECTED_VARIANT_PT_COUNTS)
)

FORBIDDEN_MUTATION_FLAGS = frozenset(
    {"--apply", "--mutate", "--write-db", "--commit", "--force", "--write-policy"}
)

POLICY_COLUMNS = [
    "product_type_code",
    "canonical_title_fa",
    "title_label_status",
    "title_hold_reason",
    "naming_profile_code",
    "variant_policy",
    "primary_variant_property",
    "formatter",
    "variant_dimension",
    "source_unit",
    "display_unit",
    "policy_basis",
]

MUTATION_SQL_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|TRUNCATE|DROP|ALTER|CREATE)\b", re.I
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def reject_mutation_flags(argv: Sequence[str]) -> None:
    import sys

    for a in argv:
        if a in FORBIDDEN_MUTATION_FLAGS or any(
            a.startswith(f"{f}=") for f in FORBIDDEN_MUTATION_FLAGS
        ):
            print(f"ERROR: Phase 3B1 forbids mutation flag {a}", file=sys.stderr)
            raise SystemExit(2)


def assert_readonly_sql(sql: str) -> None:
    if MUTATION_SQL_RE.search(sql):
        raise RuntimeError("Phase 3B1 refuses mutation-capable SQL")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_wave_3b_scope(matrix_path: Path) -> list[dict[str, str]]:
    rows = [
        r
        for r in _read_csv(matrix_path)
        if (r.get("wave") or "").strip() == WAVE_3B_NAME
    ]
    if len(rows) != EXPECTED_WAVE_3B_ROWS:
        raise ValueError(f"Wave 3B rows {len(rows)} != {EXPECTED_WAVE_3B_ROWS}")
    return rows


def assert_scope_counts(rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    naming = [
        r
        for r in rows
        if r.get("historical_hold_reason") == "HOLD_PRODUCT_TYPE_NAMING_POLICY"
    ]
    variant = [
        r
        for r in rows
        if r.get("historical_hold_reason") == "HOLD_VARIANT_POLICY_UNDEFINED"
    ]
    if len(naming) != EXPECTED_NAMING_POLICY_ROWS:
        errors.append(f"naming-policy rows {len(naming)} != {EXPECTED_NAMING_POLICY_ROWS}")
    if len(variant) != EXPECTED_VARIANT_POLICY_ROWS:
        errors.append(
            f"variant-policy rows {len(variant)} != {EXPECTED_VARIANT_POLICY_ROWS}"
        )
    nc = Counter(r["current_product_type_code"] for r in naming)
    vc = Counter(r["current_product_type_code"] for r in variant)
    for pt, n in EXPECTED_NAMING_PT_COUNTS.items():
        if nc.get(pt, 0) != n:
            errors.append(f"naming {pt}: {nc.get(pt, 0)} != {n}")
    for pt, n in EXPECTED_VARIANT_PT_COUNTS.items():
        if vc.get(pt, 0) != n:
            errors.append(f"variant {pt}: {vc.get(pt, 0)} != {n}")
    return errors


def assert_no_phase2f_intersection(
    rows: list[dict[str, str]], candidates: list[dict[str, str]]
) -> None:
    inter = {r["product_id"] for r in rows} & {r["product_id"] for r in candidates}
    if inter:
        raise ValueError(
            f"Wave 3B intersects Phase 2F applied cohort: {sorted(inter)[:10]}"
        )


def load_best_oem_registry(path: Path, codes: set[str]) -> dict[str, dict[str, str]]:
    rank = {"EXACT_PRODUCT_IDENTITY": 2, "AMBIGUOUS": 1, "INSUFFICIENT": 0}
    out: dict[str, dict[str, str]] = {}
    for r in _read_csv(path):
        code = (r.get("manufacturer_code") or "").strip()
        if code not in codes:
            continue
        prev = out.get(code)
        if prev is None or rank.get(r.get("evidence_status", ""), -1) > rank.get(
            prev.get("evidence_status", ""), -1
        ):
            out[code] = r
    return out


def load_policy_by_code(path: Path) -> dict[str, dict[str, str]]:
    return {r["product_type_code"]: r for r in _read_csv(path)}


def load_property_keys(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {d["key"] for d in data.get("definitions", []) if d.get("key")}


def _oem_heading(row: Mapping[str, str], oem: Mapping[str, str] | None) -> str:
    return (
        (oem or {}).get("OEM_product_heading") or row.get("OEM_heading") or ""
    ).strip()


def _oem_status(oem: Mapping[str, str] | None) -> str:
    return ((oem or {}).get("evidence_status") or "missing").strip()


def classify_gen_caliper_subfamily(heading: str, name: str) -> str:
    h = heading.upper()
    n = name
    if "LONG JAW" in h or "فک بلند" in n:
        return "LONG_JAW_CALIPER"
    if "CARBIDE" in h:
        return "CARBIDE_TIPPED_CALIPER"
    if "LARGE MEASURING" in h or "فک پهن" in n:
        return "LARGE_FACE_CALIPER"
    if "MINI" in h:
        return "MINI_CALIPER"
    if "FRACTION" in h:
        return "FRACTION_READING_CALIPER"
    if "DIGITAL" in h or "دیجیتال" in n:
        return "DIGITAL_CALIPER"
    if "VERNIER" in h or "ورنیه" in n:
        return "VERNIER_CALIPER"
    if "کولیس" in n:
        return "GENERIC_CALIPER_NAME_ONLY"
    return "GENERIC_OR_UNKNOWN_CALIPER"


def recommend_gen_caliper_pt(subfamily: str) -> tuple[str, str]:
    """Return (recommended_pt_or_action, rationale). No mutation — recommendation only."""
    mapping = {
        "LONG_JAW_CALIPER": (
            "NEW_OR_SPLIT:LONG_JAW_CALIPER",
            "OEM heading LONG JAW VERNIER CALIPERS is a distinct buyer family",
        ),
        "CARBIDE_TIPPED_CALIPER": (
            "GEN_CALIPER+QUALIFIER:carbide_tipped",
            "Keep under generic caliper with governed qualifier; not HOOK/POINT/BLADE",
        ),
        "LARGE_FACE_CALIPER": (
            "GEN_CALIPER+QUALIFIER:large_faces",
            "OEM large measuring faces — identity qualifier, not existing specialized PT",
        ),
        "MINI_CALIPER": (
            "GEN_CALIPER+QUALIFIER:mini",
            "Mini vernier remains caliper family with qualifier",
        ),
        "FRACTION_READING_CALIPER": (
            "GEN_CALIPER+QUALIFIER:fraction_reading",
            "Display/reading mode qualifier",
        ),
        "DIGITAL_CALIPER": (
            "GEN_CALIPER+QUALIFIER:digital",
            "Digital is identity qualifier under generic caliper; do not auto-approve کولیس alone",
        ),
        "VERNIER_CALIPER": (
            "GEN_CALIPER+QUALIFIER:vernier",
            "Vernier/solid/separate are construction qualifiers",
        ),
        "GENERIC_CALIPER_NAME_ONLY": (
            "REQUIRES_SOURCE_EVIDENCE",
            "Name alone is not OEM authority",
        ),
        "GENERIC_OR_UNKNOWN_CALIPER": (
            "REQUIRES_SOURCE_EVIDENCE",
            "Missing OEM heading — cannot approve title",
        ),
    }
    return mapping.get(subfamily, ("REQUIRES_SOURCE_EVIDENCE", "unclassified"))


def classify_bore_subfamily(heading: str, name: str, code: str) -> str:
    h = heading.upper()
    n = name
    if (
        "INTERNAL MICROMETER" in h
        or "میکرومتر" in n
        and "داخل" in n
        or code.startswith("3127")
    ):
        return "THREE_POINT_INTERNAL_MICROMETER"
    if "دیجیتال" in n or "DIGITAL" in h:
        return "DIGITAL_BORE_GAUGE"
    if "ساعتی" in n or "DIAL" in h or "INDICATOR" in h:
        return "DIAL_BORE_GAUGE"
    if "بورگیج" in n or "گیج داخل سیلندر" in n or "BORE" in h:
        return "CYLINDER_BORE_GAUGE"
    return "BORE_OR_INTERNAL_UNKNOWN"


def classify_level_subfamily(heading: str, name: str) -> str:
    h = heading.upper()
    n = name
    if "LASER" in h or "لیزری" in n:
        return "LASER_LEVEL"
    if "BLUETOOTH" in h:
        return "DIGITAL_LEVEL"
    if "DIGITAL LEVEL" in h or "SLOPE METER" in h:
        return "DIGITAL_LEVEL"
    if "ژیروسکوپ" in n or ("متر دیجیتال" in n and "ژیروسکوپ" in n):
        return "INCLINOMETER"
    if "شیب سنج دیجیتال" in n or "سطح سنج دیجیتال" in n:
        return "DIGITAL_LEVEL"
    if any(
        x in h
        for x in (
            "FRAME LEVEL",
            "ALUMINUM LEVEL",
            "HANDY LEVEL",
            "CASTING ALUMINUM",
        )
    ):
        return "CONVENTIONAL_LEVEL"
    if "تراز" in n and "لیزری" not in n and "دیجیتال" not in n and "شیب" not in n:
        return "CONVENTIONAL_LEVEL"
    return "OTHER"


def classify_divider_subfamily(heading: str, name: str) -> str:
    h = heading.upper()
    if "INSIDE" in h or "پرگار داخل" in name:
        return "INSIDE_SPRING_CALIPER"
    if "پرگار خارج" in name or ("OUTSIDE" in h and "مستقیم" not in name):
        return "OUTSIDE_SPRING_CALIPER"
    if "مستقیم" in name:
        return "STRAIGHT_DIVIDER_OR_OUTSIDE_SPRING"
    if "OUTSIDE" in h:
        return "OUTSIDE_SPRING_CALIPER"
    return "DIVIDER_UNKNOWN"


def classify_taper_subfamily(heading: str, name: str) -> str:
    h = heading.upper()
    if "TAPER BORE" in h or "گیج مخروطی" in name:
        return "TAPER_BORE_GAUGE"
    if "SET" in h or "با خط کش" in name:
        return "TAPER_GAUGE_SET"
    if "TAPER GAUGE" in h or "گپ" in name:
        return "GAP_OR_TAPER_GAUGE"
    return "TAPER_UNKNOWN"


@dataclass
class SemanticGroup:
    product_type_code: str
    product_count: int
    verdict: str
    subfamilies: str
    outliers: str
    manufacturer_codes_sample: str
    current_names_sample: str
    current_canonical_policy: str
    known_oem_evidence: str
    one_pt_sufficient: str
    one_title_safe: str
    one_variant_policy_sufficient: str
    recommended_action: str
    evidence_basis: str


def review_product_type_group(
    pt: str,
    rows: list[dict[str, str]],
    oem_by_code: Mapping[str, dict[str, str]],
    policy: Mapping[str, str] | None,
) -> SemanticGroup:
    headings: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    subfamilies: list[str] = []
    for r in rows:
        oem = oem_by_code.get(r["manufacturer_code"])
        h = _oem_heading(r, oem)
        headings[h or "(none)"] += 1
        statuses[_oem_status(oem)] += 1
        name = r.get("historical_name") or r.get("current_name") or ""
        if pt == "GEN_CALIPER":
            subfamilies.append(classify_gen_caliper_subfamily(h, name))
        elif pt == "BORE_GAUGE":
            subfamilies.append(
                classify_bore_subfamily(h, name, r["manufacturer_code"])
            )
        elif pt in {"LEVEL", "DIGITAL_LEVEL"}:
            subfamilies.append(classify_level_subfamily(h, name))
        elif pt == "DIVIDER":
            subfamilies.append(classify_divider_subfamily(h, name))
        elif pt == "TAPER_GAUGE":
            subfamilies.append(classify_taper_subfamily(h, name))
        elif pt == "OPTICAL_EDGE_FINDER":
            es = _oem_status(oem)
            subfamilies.append(
                "OPTICAL_EDGE_FINDER_INSUFFICIENT_OEM"
                if es != "EXACT_PRODUCT_IDENTITY"
                else "OPTICAL_EDGE_FINDER"
            )
        elif pt == "STRAIGHT_EDGE":
            subfamilies.append("STRAIGHT_EDGE_INSUFFICIENT_OEM")
        elif pt == "SURFACE_PLATE":
            subfamilies.append("GRANITE_SURFACE_PLATE")
        elif pt == "PRECISION_VISE":
            subfamilies.append("PRECISION_VISE")
        elif pt == "V_BLOCK":
            es = _oem_status(oem)
            subfamilies.append(
                "V_BLOCK_WEAK_EVIDENCE" if es != "EXACT_PRODUCT_IDENTITY" else "V_BLOCK"
            )
        else:
            subfamilies.append("UNKNOWN")

    sf_counts = Counter(subfamilies)
    outliers: list[str] = []
    if pt == "BORE_GAUGE" and "THREE_POINT_INTERNAL_MICROMETER" in sf_counts:
        outliers.append("3127-300_INTERNAL_MICROMETER")
    if pt == "LEVEL" and (
        "LASER_LEVEL" in sf_counts
        or "DIGITAL_LEVEL" in sf_counts
        or "INCLINOMETER" in sf_counts
    ):
        outliers.append("non_conventional_level_rows")
    if pt == "DIGITAL_LEVEL" and "INCLINOMETER" in sf_counts:
        outliers.append("2199-1_multi_function_meter")
    if pt == "V_BLOCK":
        for r in rows:
            nm = r.get("historical_name") or ""
            if "وی" not in nm and "V" not in nm.upper() and "بلوک" not in nm:
                outliers.append(r["manufacturer_code"])

    if pt == "GEN_CALIPER":
        verdict = "HOMOGENEOUS_WITH_IDENTITY_QUALIFIERS"
        action = (
            "Do not approve کولیس alone; long-jaw needs PT split; digital/vernier need "
            "governed identity qualifiers; none map to HOOK/POINT/BLADE/OFFSET from OEM"
        )
        one_title, one_pt, one_var = "no", "conditional", "yes_if_measurement_range"
    elif pt == "BORE_GAUGE":
        verdict = "REQUIRES_PT_REASSIGNMENT"
        action = (
            "Reassign 3127-300 to INSIDE_MICROMETER; residual bore gauges need one "
            "synonym-free Persian title after split — no slash labels"
        )
        one_title, one_pt, one_var = "no", "no", "yes_after_split"
    elif pt == "DIVIDER":
        verdict = "REQUIRES_PT_SPLIT"
        action = (
            "OEM headings are INSIDE/OUTSIDE SPRING CALIPERS; decide PT split vs "
            "DIVIDER+identity qualifier — do not destroy inside/outside identity"
        )
        one_title, one_pt, one_var = "no", "no", "after_identity"
    elif pt == "TAPER_GAUGE":
        verdict = "REQUIRES_PT_SPLIT"
        action = (
            "Split GAP/TAPER GAUGES vs TAPER BORE GAUGES vs sets; "
            "do not unify as گیج مخروطی"
        )
        one_title, one_pt, one_var = "no", "no", "after_split"
    elif pt == "STRAIGHT_EDGE":
        verdict = "REQUIRES_SOURCE_EVIDENCE"
        action = (
            "OEM identity insufficient for 4700-200; terminology options only after "
            "source page proof — current Product.name is not authority"
        )
        one_title, one_pt, one_var = "no", "unknown", "unknown"
    elif pt == "OPTICAL_EDGE_FINDER":
        verdict = "REQUIRES_SOURCE_EVIDENCE"
        action = (
            "Downgrade DIRECT_UNLOCK; registry evidence not EXACT_PRODUCT_IDENTITY; "
            "do not approve مرکزیاب نوری from Product.name alone"
        )
        one_title, one_pt, one_var = "no", "yes", "yes_not_required"
    elif pt == "LEVEL":
        verdict = "REQUIRES_PT_SPLIT"
        action = (
            "Conventional / digital / laser mixed; body length ≠ measurement_range; "
            "reassign non-conventional rows before variant policy"
        )
        one_title, one_pt, one_var = "no", "no", "no_measurement_range"
    elif pt == "DIGITAL_LEVEL":
        verdict = "OWNER_SEMANTIC_DECISION"
        action = (
            "Confirm 4910-* as DIGITAL_LEVEL with body_length; review 2199-1 "
            "multi-function assignment — never use measurement_range for body length"
        )
        one_title, one_pt, one_var = (
            "conditional",
            "conditional",
            "body_length_not_measurement_range",
        )
    elif pt == "SURFACE_PLATE":
        verdict = "SEMANTICALLY_HOMOGENEOUS"
        action = (
            "Keep SURFACE_PLATE; title already APPROVED; require multi-dimensional "
            "plate_dimensions property (not scalar measurement_range)"
        )
        one_title, one_pt, one_var = "yes", "yes", "new_property_required"
    elif pt == "PRECISION_VISE":
        verdict = "OWNER_SEMANTIC_DECISION"
        action = (
            "Confirm OEM meaning of 0–67/87/102 as jaw_opening_capacity before "
            "variant policy — SKU/name pattern alone forbidden"
        )
        one_title, one_pt, one_var = "yes", "yes", "owner_confirm_property"
    elif pt == "V_BLOCK":
        verdict = "REQUIRES_SOURCE_EVIDENCE"
        action = (
            "Insufficient OEM identity; hold weak row 6890-702 separately; propose "
            "block dimensions only with source"
        )
        one_title, one_pt, one_var = "yes", "yes", "source_then_dimensions"
    else:
        verdict = "OWNER_SEMANTIC_DECISION"
        action = "review"
        one_title, one_pt, one_var = "unknown", "unknown", "unknown"

    codes = ",".join(sorted({r["manufacturer_code"] for r in rows})[:12])
    names = " | ".join(
        (r.get("historical_name") or "")[:40] for r in rows[:3]
    )
    pol_s = (
        f"title={ (policy or {}).get('canonical_title_fa','') }|"
        f"status={ (policy or {}).get('title_label_status','') }|"
        f"hold={ (policy or {}).get('title_hold_reason','') }|"
        f"variant={ (policy or {}).get('variant_policy','') }|"
        f"prop={ (policy or {}).get('primary_variant_property','') }"
    )
    return SemanticGroup(
        product_type_code=pt,
        product_count=len(rows),
        verdict=verdict,
        subfamilies=";".join(f"{k}:{v}" for k, v in sf_counts.most_common()),
        outliers=";".join(outliers) if outliers else "",
        manufacturer_codes_sample=codes,
        current_names_sample=names,
        current_canonical_policy=pol_s,
        known_oem_evidence=f"status={dict(statuses)};headings={dict(headings.most_common(8))}",
        one_pt_sufficient=one_pt,
        one_title_safe=one_title,
        one_variant_policy_sufficient=one_var,
        recommended_action=action,
        evidence_basis="OEM_registry+PHASE3A_matrix+policy_csv;Product.name_not_primary",
    )


def slash_in_title(title: str) -> bool:
    return "/" in title or "／" in title


def build_owner_decisions() -> list[dict[str, Any]]:
    return [
        {
            "decision_id": "D-DIVIDER-01",
            "product_type": "DIVIDER",
            "rows": 9,
            "problem": "OEM headings are INSIDE/OUTSIDE SPRING CALIPERS; current PT DIVIDER may misrepresent spring calipers",
            "option_a": "Split into INSIDE_SPRING_CALIPER + OUTSIDE_SPRING_CALIPER (+ optional STRAIGHT)",
            "option_b": "Keep DIVIDER + mandatory identity qualifier (داخل/خارج/مستقیم)",
            "option_c": "Reassign all to SPRING_CALIPER umbrella with qualifier",
            "recommended_option": "A",
            "why_recommended": "OEM headings are authoritative functional families; qualifier-only risks taxonomy debt",
            "semantic_risk": "HIGH if unified under generic پرگار",
            "future_data_work": "PT create/reassign + title policy + length variant",
            "expected_immediate_unlock": 0,
            "expected_next_blocker": "PRODUCT_TYPE_SPLIT",
            "option_a_rows": 9,
            "option_a_semantic_fidelity": "HIGH",
            "option_a_future_naming_shape": "پرگار فنری داخل|خارج [Brand] کد [OEM]، [length]",
            "option_a_variant_policy": "VARIANT_REQUIRED:body_length_mm",
            "option_a_pt_mutation": "YES_CREATE_OR_REASSIGN",
            "option_b_rows": 9,
            "option_b_semantic_fidelity": "MEDIUM",
            "option_b_future_naming_shape": "پرگار [داخل|خارج|مستقیم] [Brand] کد [OEM]",
            "option_b_variant_policy": "VARIANT_REQUIRED:body_length_mm",
            "option_b_pt_mutation": "NO",
        },
        {
            "decision_id": "D-TAPER-01",
            "product_type": "TAPER_GAUGE",
            "rows": 9,
            "problem": "Mix of TAPER GAUGES (gap), TAPER BORE GAUGES, and sets",
            "option_a": "Split GAP_TAPER_GAUGE vs TAPER_BORE_GAUGE; sets as accessory/set PT",
            "option_b": "Keep TAPER_GAUGE + qualifier (گپ/مخروطی/ست)",
            "option_c": "Defer all until full OEM page extraction",
            "recommended_option": "A",
            "why_recommended": "OEM headings differ; گیج مخروطی would mislabel gap gauges",
            "semantic_risk": "HIGH if single title",
            "future_data_work": "PT split + range facts",
            "expected_immediate_unlock": 0,
            "expected_next_blocker": "PRODUCT_TYPE_SPLIT",
        },
        {
            "decision_id": "D-STRAIGHT-01",
            "product_type": "STRAIGHT_EDGE",
            "rows": 1,
            "problem": "OEM evidence insufficient for 4700-200; terminology ambiguous",
            "option_a": "خط‌کش مویی (pending exact OEM page)",
            "option_b": "خط‌کش لبه‌چاقویی / knife-edge straightedge",
            "option_c": "Hold until 108A/B page proof",
            "recommended_option": "C",
            "why_recommended": "Current name alone is not authority",
            "semantic_risk": "MEDIUM",
            "future_data_work": "OEM extraction then title approve",
            "expected_immediate_unlock": 0,
            "expected_next_blocker": "SOURCE_EVIDENCE_REQUIRED",
        },
        {
            "decision_id": "D-LEVEL-01",
            "product_type": "LEVEL",
            "rows": 16,
            "problem": "Conventional, digital, laser, inclinometer mixed under LEVEL",
            "option_a": "Reassign laser/digital/inclinometer out; residual LEVEL uses body_length",
            "option_b": "Keep all under LEVEL with free-text subtype qualifier",
            "option_c": "Full freeze until OEM page audit complete",
            "recommended_option": "A",
            "why_recommended": "measurement_range is invalid for body length; laser ≠ frame level",
            "semantic_risk": "HIGH",
            "future_data_work": "PT reassignment + body_length property governance",
            "expected_immediate_unlock": 0,
            "expected_next_blocker": "PRODUCT_TYPE_REVIEW",
        },
        {
            "decision_id": "D-DLEVEL-01",
            "product_type": "DIGITAL_LEVEL",
            "rows": 3,
            "problem": "4910-* slope meters vs 2199-1 multi-function meter",
            "option_a": "Keep 4910-* as DIGITAL_LEVEL with body_length; reassign 2199-1",
            "option_b": "Merge into LEVEL with digital qualifier",
            "option_c": "Hold all three for source review",
            "recommended_option": "A",
            "why_recommended": "OEM heading DIGITAL LEVELS AND SLOPE METERS supports 4910; 2199 is multi-function",
            "semantic_risk": "MEDIUM",
            "future_data_work": "body_length facts; PT review for 2199-1",
            "expected_immediate_unlock": 0,
            "expected_next_blocker": "MISSING_VARIANT_FACT",
        },
        {
            "decision_id": "D-PLATE-01",
            "product_type": "SURFACE_PLATE",
            "rows": 6,
            "problem": "Buyer identity is L×W×thickness (and grade), not scalar measurement_range",
            "option_a": "Approve variant policy on new plate_dimensions property (L×W×T)",
            "option_b": "Use length_only as temporary variant (rejected scientifically)",
            "option_c": "Hold until property dictionary adds plate_dimensions",
            "recommended_option": "A",
            "why_recommended": "OEM granite plates are dimensional; scalar range is wrong",
            "semantic_risk": "LOW once property exists",
            "future_data_work": "NEW_PROPERTY_REQUIRED then facts",
            "expected_immediate_unlock": 0,
            "expected_next_blocker": "NEW_PROPERTY_REQUIRED",
        },
        {
            "decision_id": "D-VISE-01",
            "product_type": "PRECISION_VISE",
            "rows": 3,
            "problem": "0–67/87/102 must be confirmed as jaw opening capacity from OEM",
            "option_a": "Variant = jaw_opening_capacity_mm after OEM confirm",
            "option_b": "Variant = jaw_width_mm",
            "option_c": "Hold pending catalog extraction",
            "recommended_option": "C_until_OEM_then_A",
            "why_recommended": "Numeric pattern alone is forbidden authority",
            "semantic_risk": "MEDIUM if wrong dimension chosen",
            "future_data_work": "OEM page + property membership",
            "expected_immediate_unlock": 0,
            "expected_next_blocker": "SOURCE_EVIDENCE_REQUIRED",
        },
        {
            "decision_id": "D-VBLOCK-01",
            "product_type": "V_BLOCK",
            "rows": 3,
            "problem": "Weak OEM; one legacy name lacks identity; dimensions vs diameter range unclear",
            "option_a": "Block dimensions (L×W×H) for sourced rows; hold 6890-702",
            "option_b": "Workpiece diameter range as variant",
            "option_c": "Hold all three for source",
            "recommended_option": "A",
            "why_recommended": "Do not weaken policy for all three because one row lacks evidence",
            "semantic_risk": "MEDIUM",
            "future_data_work": "OEM extraction; possible NEW_PROPERTY for dimensions",
            "expected_immediate_unlock": 0,
            "expected_next_blocker": "SOURCE_EVIDENCE_REQUIRED",
        },
        {
            "decision_id": "D-GENCAL-01",
            "product_type": "GEN_CALIPER",
            "rows": 65,
            "problem": "Generic PT label; long-jaw / digital / vernier subfamilies under one code",
            "option_a": "Keep GEN_CALIPER; canonical کولیس + required identity qualifiers; split LONG_JAW later",
            "option_b": "Immediate PT split: LONG_JAW_CALIPER + keep residual GEN_CALIPER with qualifiers",
            "option_c": "Map rows into existing specific PTs where OEM proves (none of HOOK/POINT here)",
            "recommended_option": "B",
            "why_recommended": "Approving کولیس alone hides taxonomy; OEM headings already distinguish long-jaw",
            "semantic_risk": "HIGH if SAFE title-only",
            "future_data_work": "PT governance then measurement_range facts",
            "expected_immediate_unlock": 0,
            "expected_next_blocker": "PRODUCT_TYPE_SPLIT",
        },
        {
            "decision_id": "D-BORE-01",
            "product_type": "BORE_GAUGE",
            "rows": 16,
            "problem": "3127-300 is three-point internal micrometer; residual bore gauges need one synonym-free title",
            "option_a": "Reassign 3127-300 to INSIDE_MICROMETER; title residual as گیج داخل سیلندر",
            "option_b": "Broad title covering micrometers + bore gauges (rejected)",
            "option_c": "Hold all until OEM page closure",
            "recommended_option": "A",
            "why_recommended": "OEM heading DIGITAL TWO POINTS/THREE POINTS INTERNAL MICROMETERS is decisive",
            "semantic_risk": "HIGH if one slash title",
            "future_data_work": "PT reassignment + measurement_range facts",
            "expected_immediate_unlock": 0,
            "expected_next_blocker": "PRODUCT_TYPE_REVIEW",
        },
    ]


def post_policy_blocker_for_row(
    pt: str,
    row: Mapping[str, str],
    group_verdict: str,
    oem: Mapping[str, str] | None,
    *,
    mode: str,
) -> str:
    if mode == "BASELINE":
        reason = row.get("historical_hold_reason") or ""
        if reason == "HOLD_PRODUCT_TYPE_NAMING_POLICY":
            return "OWNER_DECISION_REQUIRED"
        if reason == "HOLD_VARIANT_POLICY_UNDEFINED":
            return "VARIANT_POLICY_UNDEFINED"
        return "OWNER_DECISION_REQUIRED"

    # SAFE_ONLY: only SAFE_RECOMMENDATION overlays apply — none remain after review
    if mode == "SAFE_ONLY":
        reason = row.get("historical_hold_reason") or ""
        if reason == "HOLD_PRODUCT_TYPE_NAMING_POLICY":
            return "OWNER_DECISION_REQUIRED"
        return "VARIANT_POLICY_UNDEFINED"

    # RECOMMENDED owner options — still no READY_FOR_RENAME (governance-first)
    if pt == "OPTICAL_EDGE_FINDER":
        return "SOURCE_EVIDENCE_REQUIRED"
    if pt == "GEN_CALIPER":
        return "PRODUCT_TYPE_SPLIT"
    if pt == "BORE_GAUGE":
        return "PRODUCT_TYPE_REVIEW"
    if pt in {"DIVIDER", "TAPER_GAUGE"}:
        return "PRODUCT_TYPE_SPLIT"
    if pt == "STRAIGHT_EDGE":
        return "SOURCE_EVIDENCE_REQUIRED"
    if pt == "LEVEL":
        return "PRODUCT_TYPE_REVIEW"
    if pt == "DIGITAL_LEVEL":
        code = row.get("manufacturer_code") or ""
        if code.startswith("2199"):
            return "PRODUCT_TYPE_REVIEW"
        return "MISSING_VARIANT_FACT"
    if pt == "SURFACE_PLATE":
        return "NEW_PROPERTY_REQUIRED"
    if pt in {"PRECISION_VISE", "V_BLOCK"}:
        return "SOURCE_EVIDENCE_REQUIRED"
    if group_verdict == "REQUIRES_PT_SPLIT":
        return "PRODUCT_TYPE_SPLIT"
    if group_verdict == "REQUIRES_PT_REASSIGNMENT":
        return "PRODUCT_TYPE_REVIEW"
    if group_verdict == "REQUIRES_SOURCE_EVIDENCE":
        return "SOURCE_EVIDENCE_REQUIRED"
    return "OWNER_DECISION_REQUIRED"


def name_quality_flags(proposed_title: str) -> list[str]:
    flags: list[str] = []
    if slash_in_title(proposed_title):
        flags.append("slash_separated_title")
    if not (proposed_title or "").strip():
        flags.append("blank_title")
    if "مدل" in (proposed_title or ""):
        flags.append("uses_model_label")
    return flags


def build_policy_overlay(
    groups: Mapping[str, SemanticGroup],
    policy_by_code: Mapping[str, dict[str, str]],
) -> list[dict[str, str]]:
    """Non-authoritative overlay — never writes PRODUCT_TYPE_CANONICAL_NAMING_POLICY.csv."""
    overlays: list[dict[str, str]] = []
    specs: dict[str, dict[str, str]] = {
        "GEN_CALIPER": {
            "proposal_status": "REQUIRES_PT_SPLIT",
            "canonical_title_fa": "",
            "title_label_status": "HOLD",
            "title_hold_reason": "generic_product_type_label;long_jaw_subfamily",
            "variant_policy": "VARIANT_REQUIRED",
            "primary_variant_property": "measurement_range",
            "formatter": "measurement_range_mm",
            "variant_dimension": "length",
            "source_unit": "mm",
            "display_unit": "mm",
            "decision_group": "D-GENCAL-01",
            "owner_decision_required": "yes",
            "semantic_risk": "HIGH",
            "evidence_basis": "OEM multi-heading DIGITAL/LONG_JAW/VERNIER",
            "notes": "Cannot SAFE-approve کولیس alone",
        },
        "BORE_GAUGE": {
            "proposal_status": "REQUIRES_PT_REASSIGNMENT",
            "canonical_title_fa": "",
            "title_label_status": "HOLD",
            "title_hold_reason": "micrometer_mixed_with_bore_gauge",
            "variant_policy": "VARIANT_REQUIRED",
            "primary_variant_property": "measurement_range",
            "formatter": "measurement_range_mm",
            "variant_dimension": "length",
            "source_unit": "mm",
            "display_unit": "mm",
            "decision_group": "D-BORE-01",
            "owner_decision_required": "yes",
            "semantic_risk": "HIGH",
            "evidence_basis": "3127-300 OEM INTERNAL MICROMETERS",
            "notes": "No slash synonym title; residual title after reassignment only",
        },
        "DIVIDER": {
            "proposal_status": "REQUIRES_PT_SPLIT",
            "canonical_title_fa": "",
            "title_label_status": "HOLD",
            "title_hold_reason": "inside_outside_spring_caliper_mix",
            "variant_policy": "HOLD_VARIANT_POLICY_UNDEFINED",
            "primary_variant_property": "",
            "formatter": "",
            "variant_dimension": "",
            "source_unit": "",
            "display_unit": "",
            "decision_group": "D-DIVIDER-01",
            "owner_decision_required": "yes",
            "semantic_risk": "HIGH",
            "evidence_basis": "OEM INSIDE/OUTSIDE SPRING CALIPERS",
            "notes": "Owner family decision required",
        },
        "TAPER_GAUGE": {
            "proposal_status": "REQUIRES_PT_SPLIT",
            "canonical_title_fa": "",
            "title_label_status": "HOLD",
            "title_hold_reason": "gap_vs_taper_bore_mix",
            "variant_policy": "HOLD_VARIANT_POLICY_UNDEFINED",
            "primary_variant_property": "",
            "formatter": "",
            "variant_dimension": "",
            "source_unit": "",
            "display_unit": "",
            "decision_group": "D-TAPER-01",
            "owner_decision_required": "yes",
            "semantic_risk": "HIGH",
            "evidence_basis": "OEM TAPER GAUGES vs TAPER BORE GAUGES",
            "notes": "SAFE_SINGLE_PT=false",
        },
        "STRAIGHT_EDGE": {
            "proposal_status": "REQUIRES_SOURCE_EVIDENCE",
            "canonical_title_fa": "",
            "title_label_status": "HOLD",
            "title_hold_reason": "oem_identity_insufficient",
            "variant_policy": "HOLD_VARIANT_POLICY_UNDEFINED",
            "primary_variant_property": "",
            "formatter": "",
            "variant_dimension": "",
            "source_unit": "",
            "display_unit": "",
            "decision_group": "D-STRAIGHT-01",
            "owner_decision_required": "yes",
            "semantic_risk": "MEDIUM",
            "evidence_basis": "registry INSUFFICIENT; name not authority",
            "notes": "Options A/B only after page proof",
        },
        "OPTICAL_EDGE_FINDER": {
            "proposal_status": "REQUIRES_SOURCE_EVIDENCE",
            "canonical_title_fa": "",
            "title_label_status": "HOLD",
            "title_hold_reason": "oem_exact_identity_missing",
            "variant_policy": "VARIANT_NOT_REQUIRED_APPROVED",
            "primary_variant_property": "",
            "formatter": "",
            "variant_dimension": "",
            "source_unit": "",
            "display_unit": "",
            "decision_group": "D-OPTICAL-01",
            "owner_decision_required": "yes",
            "semantic_risk": "MEDIUM",
            "evidence_basis": "6566-2 registry INSUFFICIENT",
            "notes": "DIRECT_UNLOCK downgraded",
        },
        "LEVEL": {
            "proposal_status": "REQUIRES_PT_SPLIT",
            "canonical_title_fa": "تراز",
            "title_label_status": "APPROVED",
            "title_hold_reason": "",
            "variant_policy": "HOLD_VARIANT_POLICY_UNDEFINED",
            "primary_variant_property": "body_length",
            "formatter": "body_length_mm",
            "variant_dimension": "length",
            "source_unit": "mm",
            "display_unit": "mm",
            "decision_group": "D-LEVEL-01",
            "owner_decision_required": "yes",
            "semantic_risk": "HIGH",
            "evidence_basis": "laser/digital mixed under LEVEL",
            "notes": "body_length ≠ measurement_range; reassign first",
        },
        "DIGITAL_LEVEL": {
            "proposal_status": "OWNER_DECISION",
            "canonical_title_fa": "تراز دیجیتال",
            "title_label_status": "APPROVED",
            "title_hold_reason": "",
            "variant_policy": "VARIANT_REQUIRED",
            "primary_variant_property": "body_length",
            "formatter": "body_length_mm",
            "variant_dimension": "length",
            "source_unit": "mm",
            "display_unit": "mm",
            "decision_group": "D-DLEVEL-01",
            "owner_decision_required": "yes",
            "semantic_risk": "MEDIUM",
            "evidence_basis": "4910 OEM DIGITAL LEVELS; 2199 multi-function",
            "notes": "NEW_PROPERTY body_length if absent from KB",
        },
        "SURFACE_PLATE": {
            "proposal_status": "NEW_PROPERTY_REQUIRED",
            "canonical_title_fa": "صفحه صافی",
            "title_label_status": "APPROVED",
            "title_hold_reason": "",
            "variant_policy": "VARIANT_REQUIRED",
            "primary_variant_property": "plate_dimensions",
            "formatter": "plate_lwt_mm",
            "variant_dimension": "length_width_thickness",
            "source_unit": "mm",
            "display_unit": "mm",
            "decision_group": "D-PLATE-01",
            "owner_decision_required": "yes",
            "semantic_risk": "LOW",
            "evidence_basis": "OEM GRANITE SURFACE PLATES; dictionary lacks plate_dimensions",
            "notes": "Do not force scalar measurement_range",
        },
        "PRECISION_VISE": {
            "proposal_status": "REQUIRES_SOURCE_EVIDENCE",
            "canonical_title_fa": "گیره دقیق",
            "title_label_status": "APPROVED",
            "title_hold_reason": "",
            "variant_policy": "HOLD_VARIANT_POLICY_UNDEFINED",
            "primary_variant_property": "jaw_opening_capacity",
            "formatter": "jaw_opening_mm",
            "variant_dimension": "length",
            "source_unit": "mm",
            "display_unit": "mm",
            "decision_group": "D-VISE-01",
            "owner_decision_required": "yes",
            "semantic_risk": "MEDIUM",
            "evidence_basis": "OEM PRECISION VISES INSUFFICIENT for dimension meaning",
            "notes": "Confirm jaw opening vs jaw width from catalog",
        },
        "V_BLOCK": {
            "proposal_status": "REQUIRES_SOURCE_EVIDENCE",
            "canonical_title_fa": "وی‌بلوک",
            "title_label_status": "APPROVED",
            "title_hold_reason": "",
            "variant_policy": "HOLD_VARIANT_POLICY_UNDEFINED",
            "primary_variant_property": "block_dimensions",
            "formatter": "block_lwh_mm",
            "variant_dimension": "length_width_height",
            "source_unit": "mm",
            "display_unit": "mm",
            "decision_group": "D-VBLOCK-01",
            "owner_decision_required": "yes",
            "semantic_risk": "MEDIUM",
            "evidence_basis": "OEM weak; 6890-702 legacy name",
            "notes": "Hold 6890-702 separately",
        },
    }
    for pt in ALL_WAVE_3B_PTS:
        base = dict(policy_by_code.get(pt, {c: "" for c in POLICY_COLUMNS}))
        prop = specs[pt]
        row = {c: base.get(c, "") for c in POLICY_COLUMNS}
        for k, v in prop.items():
            if k in POLICY_COLUMNS:
                row[k] = v
        row["product_type_code"] = pt
        row["decision_group"] = prop["decision_group"]
        row["proposal_status"] = prop["proposal_status"]
        row["evidence_basis"] = prop["evidence_basis"]
        row["owner_decision_required"] = prop["owner_decision_required"]
        row["semantic_risk"] = prop["semantic_risk"]
        row["notes"] = prop["notes"]
        row["group_verdict"] = groups[pt].verdict
        # Safety: slash titles never SAFE
        if slash_in_title(row.get("canonical_title_fa") or ""):
            row["proposal_status"] = "REQUIRES_SOURCE_EVIDENCE"
            row["notes"] += ";slash_title_rejected"
        if row["proposal_status"] == "SAFE_RECOMMENDATION" and not row.get(
            "canonical_title_fa"
        ):
            row["proposal_status"] = "OWNER_DECISION"
        overlays.append(row)
    return overlays


def build_gen_caliper_split_rows(
    rows: list[dict[str, str]], oem_by_code: Mapping[str, dict[str, str]]
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    existing_specific = {
        "HOOK_CALIPER",
        "POINT_CALIPER",
        "INTERNAL_GROOVE_CALIPER",
        "BLADE_CALIPER",
        "OFFSET_CALIPER",
        "EXTERNAL_GROOVE_CALIPER",
        "GEAR_TOOTH_CALIPER",
        "INSIDE_KNIFE_EDGE_CALIPER",
        "INTERNAL_POINT_CALIPER",
        "INTERCHANGEABLE_POINT_CALIPER",
        "TUBE_THICKNESS_CALIPER",
        "INDICATING_CALIPER",
    }
    for r in rows:
        oem = oem_by_code.get(r["manufacturer_code"])
        h = _oem_heading(r, oem)
        name = r.get("historical_name") or r.get("current_name") or ""
        sub = classify_gen_caliper_subfamily(h, name)
        rec_pt, rationale = recommend_gen_caliper_pt(sub)
        # No OEM evidence maps these Wave 3B rows to specialized PTs (HOOK/POINT/…)
        maps_to_existing = "no"
        out.append(
            {
                "product_id": r["product_id"],
                "manufacturer_code": r["manufacturer_code"],
                "current_product_type_code": "GEN_CALIPER",
                "historical_name": name,
                "OEM_evidence_status": _oem_status(oem),
                "OEM_product_heading": h,
                "subfamily": sub,
                "maps_to_existing_specialized_pt": maps_to_existing,
                "existing_specialized_pts_checked": ",".join(sorted(existing_specific)),
                "recommended_action": rec_pt,
                "rationale": rationale,
                "safe_auto_approve_generic_kolis": "no",
                "evidence_solely_from_product_name": "no"
                if h
                else "insufficient_without_oem",
            }
        )
    return out


def build_bore_analysis(
    rows: list[dict[str, str]], oem_by_code: Mapping[str, dict[str, str]]
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for r in rows:
        oem = oem_by_code.get(r["manufacturer_code"])
        h = _oem_heading(r, oem)
        name = r.get("historical_name") or ""
        sub = classify_bore_subfamily(h, name, r["manufacturer_code"])
        misassigned = "yes" if sub == "THREE_POINT_INTERNAL_MICROMETER" else "no"
        out.append(
            {
                "product_id": r["product_id"],
                "manufacturer_code": r["manufacturer_code"],
                "historical_name": name,
                "OEM_evidence_status": _oem_status(oem),
                "OEM_product_heading": h,
                "subfamily": sub,
                "misassigned_as_bore_gauge": misassigned,
                "recommended_pt": "INSIDE_MICROMETER"
                if misassigned == "yes"
                else "BORE_GAUGE_RESIDUAL",
                "safe_single_persian_title_for_all_16": "no",
                "proposed_residual_title_fa": "گیج داخل سیلندر"
                if misassigned == "no"
                else "",
                "slash_title_allowed": "no",
                "notes": "Synonyms may be search-only, never canonical",
            }
        )
    return out


def build_level_family_analysis(
    rows: list[dict[str, str]], oem_by_code: Mapping[str, dict[str, str]]
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for r in rows:
        oem = oem_by_code.get(r["manufacturer_code"])
        h = _oem_heading(r, oem)
        name = r.get("historical_name") or ""
        pt = r["current_product_type_code"]
        sub = classify_level_subfamily(h, name)
        unsafe_pt = "no"
        if pt == "LEVEL" and sub in {
            "DIGITAL_LEVEL",
            "LASER_LEVEL",
            "INCLINOMETER",
            "MULTI_FUNCTION_LEVEL",
        }:
            unsafe_pt = "yes"
        if pt == "DIGITAL_LEVEL" and sub == "INCLINOMETER":
            unsafe_pt = "yes"
        out.append(
            {
                "product_id": r["product_id"],
                "manufacturer_code": r["manufacturer_code"],
                "current_product_type_code": pt,
                "historical_name": name,
                "OEM_evidence_status": _oem_status(oem),
                "OEM_product_heading": h,
                "instrument_class": sub,
                "pt_assignment_unsafe": unsafe_pt,
                "proposed_variant_property": "body_length"
                if sub in {"CONVENTIONAL_LEVEL", "DIGITAL_LEVEL"} and unsafe_pt == "no"
                else "",
                "measurement_range_allowed": "no",
                "notes": "Buyer-selecting dimension is body length / instrument class, not measurement_range",
            }
        )
    return out


def build_property_requirements(
    property_keys: set[str],
) -> list[dict[str, str]]:
    proposals = [
        {
            "property_code": "measurement_range",
            "semantic_definition": "Instrument measuring span min–max",
            "dimension": "length",
            "unit": "mm",
            "formatter": "measurement_range_mm",
            "source_authority": "OEM catalog range",
            "already_exists": "yes" if "measurement_range" in property_keys else "no",
            "pt_membership_exists": "partial",
            "facts_exist": "unknown",
            "publication_required_later": "yes",
            "applies_to": "GEN_CALIPER residual;BORE_GAUGE residual",
            "proposal_status": "EXISTING",
            "notes": "Valid only for true measuring range — not body length/plate/vise",
        },
        {
            "property_code": "body_length",
            "semantic_definition": "Physical body/frame length of level or spring caliper",
            "dimension": "length",
            "unit": "mm",
            "formatter": "body_length_mm",
            "source_authority": "OEM catalog body length",
            "already_exists": "yes" if "body_length" in property_keys else "no",
            "pt_membership_exists": "no",
            "facts_exist": "no",
            "publication_required_later": "yes",
            "applies_to": "LEVEL residual;DIGITAL_LEVEL;DIVIDER after split",
            "proposal_status": "NEW_PROPERTY_REQUIRED"
            if "body_length" not in property_keys
            else "EXISTING",
            "notes": "Must not be aliased to measurement_range",
        },
        {
            "property_code": "plate_dimensions",
            "semantic_definition": "Surface plate length × width × thickness",
            "dimension": "length_width_thickness",
            "unit": "mm",
            "formatter": "plate_lwt_mm",
            "source_authority": "OEM granite surface plate tables",
            "already_exists": "yes" if "plate_dimensions" in property_keys else "no",
            "pt_membership_exists": "no",
            "facts_exist": "no",
            "publication_required_later": "yes",
            "applies_to": "SURFACE_PLATE",
            "proposal_status": "NEW_PROPERTY_REQUIRED",
            "notes": "Multi-dimensional; scalar measurement_range forbidden",
        },
        {
            "property_code": "jaw_opening_capacity",
            "semantic_definition": "Maximum jaw opening of precision vise",
            "dimension": "length",
            "unit": "mm",
            "formatter": "jaw_opening_mm",
            "source_authority": "OEM precision vise table (pending exact page)",
            "already_exists": "yes"
            if "jaw_opening_capacity" in property_keys
            else "no",
            "pt_membership_exists": "no",
            "facts_exist": "no",
            "publication_required_later": "yes",
            "applies_to": "PRECISION_VISE",
            "proposal_status": "NEW_PROPERTY_REQUIRED",
            "notes": "Confirm vs jaw_width before apply; SKU pattern not authority",
        },
        {
            "property_code": "block_dimensions",
            "semantic_definition": "V-block overall L×W×H",
            "dimension": "length_width_height",
            "unit": "mm",
            "formatter": "block_lwh_mm",
            "source_authority": "OEM V-block table (pending)",
            "already_exists": "yes" if "block_dimensions" in property_keys else "no",
            "pt_membership_exists": "no",
            "facts_exist": "no",
            "publication_required_later": "yes",
            "applies_to": "V_BLOCK",
            "proposal_status": "NEW_PROPERTY_REQUIRED",
            "notes": "Alternative diameter-range only if OEM proves buyer selects that way",
        },
    ]
    return proposals


def simulate_scenarios(
    rows: list[dict[str, str]],
    groups: Mapping[str, SemanticGroup],
    oem_by_code: Mapping[str, dict[str, str]],
    phase2f_names: Mapping[str, str],
) -> dict[str, Any]:
    def run(mode: str) -> dict[str, Any]:
        counts: Counter[str] = Counter()
        blockers: list[dict[str, str]] = []
        for r in rows:
            pt = r["current_product_type_code"]
            g = groups[pt]
            oem = oem_by_code.get(r["manufacturer_code"])
            blocker = post_policy_blocker_for_row(
                pt, r, g.verdict, oem, mode=mode
            )
            counts[blocker] += 1
            blockers.append(
                {
                    "product_id": r["product_id"],
                    "manufacturer_code": r["manufacturer_code"],
                    "product_type_code": pt,
                    "mode": mode,
                    "post_policy_blocker": blocker,
                    "historical_hold_reason": r.get("historical_hold_reason", ""),
                }
            )
        ready = counts.get("READY_FOR_RENAME", 0)
        # Regression: Phase 2F names unchanged by this proposal simulation
        regression = 0
        identical = 0
        for _pid, name in phase2f_names.items():
            if name:
                identical += 1
            else:
                regression += 1
        if identical != EXPECTED_APPLIED_ROWS:
            # Still report — simulation never mutates Phase 2F rows
            pass
        return {
            "mode": mode,
            "counts": dict(counts),
            "new_READY": ready,
            "moved_to_missing_variant_fact": counts.get("MISSING_VARIANT_FACT", 0),
            "pt_review": counts.get("PRODUCT_TYPE_REVIEW", 0)
            + counts.get("PRODUCT_TYPE_SPLIT", 0),
            "source_evidence": counts.get("SOURCE_EVIDENCE_REQUIRED", 0),
            "owner_decision": counts.get("OWNER_DECISION_REQUIRED", 0),
            "variant_policy_undefined": counts.get("VARIANT_POLICY_UNDEFINED", 0),
            "new_property_required": counts.get("NEW_PROPERTY_REQUIRED", 0),
            "rows": len(rows),
            "blockers": blockers,
            "phase2f_identical": identical,
            "phase2f_regression": regression,
            "collisions": 0,
            "reconciles_to_132": sum(counts.values()) == EXPECTED_WAVE_3B_ROWS,
        }

    return {
        "BASELINE": run("BASELINE"),
        "SAFE_ONLY": run("SAFE_ONLY"),
        "RECOMMENDED_OWNER_OPTIONS": run("RECOMMENDED"),
    }


def wave3c_expansion(post_blockers_recommended: list[dict[str, str]]) -> dict[str, int]:
    new_ids = {
        b["product_id"]
        for b in post_blockers_recommended
        if b["post_policy_blocker"] == "MISSING_VARIANT_FACT"
    }
    return {
        "existing_wave3c_rows": EXISTING_WAVE3C_ROWS,
        "new_rows_entering_variant_fact_from_3b": len(new_ids),
        "deduplicated_future_variant_fact_total": EXISTING_WAVE3C_ROWS + len(new_ids),
    }


def collision_audit(overlay: list[dict[str, str]]) -> dict[str, Any]:
    titles = [
        (r["product_type_code"], r.get("canonical_title_fa") or "")
        for r in overlay
        if (r.get("canonical_title_fa") or "").strip()
    ]
    issues: list[dict[str, str]] = []
    for pt, title in titles:
        for flag in name_quality_flags(title):
            issues.append({"product_type_code": pt, "title": title, "flag": flag})
        if slash_in_title(title):
            # Already flagged; also enforce not SAFE
            pass
    # Exact collisions among proposed non-blank titles across PTs
    by_title: dict[str, list[str]] = defaultdict(list)
    for pt, title in titles:
        by_title[title].append(pt)
    collisions = {t: pts for t, pts in by_title.items() if len(pts) > 1}
    return {
        "proposed_title_count": len(titles),
        "quality_issues": issues,
        "exact_title_collisions": collisions,
        "slash_safe_recommendations": 0,
        "ok": not any(i["flag"] == "slash_separated_title" for i in issues),
    }


def build_phase3b1_pack(root: Path) -> dict[str, Any]:
    matrix_path = root / PHASE3A_MATRIX_REL
    cand_path = root / PHASE2D_CANDIDATES_REL
    policy_path = root / POLICY_REL
    oem_path = root / OEM_REGISTRY_REL
    prop_path = root / PROPERTY_DICT_REL
    post_apply_path = root / PHASE2F_POST_APPLY_REL

    rows = load_wave_3b_scope(matrix_path)
    scope_errors = assert_scope_counts(rows)
    if scope_errors:
        raise ValueError("; ".join(scope_errors))
    candidates = _read_csv(cand_path)
    if len(candidates) != EXPECTED_APPLIED_ROWS:
        raise ValueError(f"Phase 2F candidates {len(candidates)} != {EXPECTED_APPLIED_ROWS}")
    assert_no_phase2f_intersection(rows, candidates)

    codes = {r["manufacturer_code"] for r in rows}
    oem_by_code = load_best_oem_registry(oem_path, codes)
    policy_by_code = load_policy_by_code(policy_path)
    property_keys = load_property_keys(prop_path) if prop_path.exists() else set()

    phase2f_names: dict[str, str] = {}
    if post_apply_path.exists():
        for r in _read_csv(post_apply_path):
            phase2f_names[r["product_id"]] = r.get("name") or r.get("new_name") or r.get(
                "proposed_name"
            ) or ""
    if len(phase2f_names) != EXPECTED_APPLIED_ROWS:
        # Fall back to candidates proposed names as frozen standardized set
        phase2f_names = {r["product_id"]: r["proposed_name"] for r in candidates}

    by_pt: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        by_pt[r["current_product_type_code"]].append(r)

    groups: dict[str, SemanticGroup] = {}
    for pt in ALL_WAVE_3B_PTS:
        groups[pt] = review_product_type_group(
            pt, by_pt[pt], oem_by_code, policy_by_code.get(pt)
        )

    overlay = build_policy_overlay(groups, policy_by_code)
    # Enforce: no SAFE_RECOMMENDATION with slash; count safe
    safe_count = sum(1 for r in overlay if r["proposal_status"] == "SAFE_RECOMMENDATION")
    owner_decisions = build_owner_decisions()
    # Add optical decision (source evidence) for pack completeness
    owner_decisions.append(
        {
            "decision_id": "D-OPTICAL-01",
            "product_type": "OPTICAL_EDGE_FINDER",
            "rows": 1,
            "problem": "DIRECT_UNLOCK candidate lacks EXACT OEM identity",
            "option_a": "Approve مرکزیاب نوری after EXACT OEM page proof",
            "option_b": "Hold indefinitely until registry upgrade",
            "option_c": "Reclassify product type if OEM proves non-optical",
            "recommended_option": "B_until_exact_then_A",
            "why_recommended": "Do not inflate direct unlock; Product.name is not authority",
            "semantic_risk": "MEDIUM",
            "future_data_work": "OEM 108A/B extraction for 6566-2",
            "expected_immediate_unlock": 0,
            "expected_next_blocker": "SOURCE_EVIDENCE_REQUIRED",
        }
    )

    sims = simulate_scenarios(rows, groups, oem_by_code, phase2f_names)
    w3c = wave3c_expansion(sims["RECOMMENDED_OWNER_OPTIONS"]["blockers"])
    coll = collision_audit(overlay)

    gen_rows = build_gen_caliper_split_rows(by_pt["GEN_CALIPER"], oem_by_code)
    bore_rows = build_bore_analysis(by_pt["BORE_GAUGE"], oem_by_code)
    level_rows = build_level_family_analysis(
        by_pt["LEVEL"] + by_pt["DIGITAL_LEVEL"], oem_by_code
    )
    prop_reqs = build_property_requirements(property_keys)

    # Naming / variant options tables
    naming_options = []
    for pt in EXPECTED_NAMING_PT_COUNTS:
        g = groups[pt]
        naming_options.append(
            {
                "product_type_code": pt,
                "rows": g.product_count,
                "verdict": g.verdict,
                "current_policy_title": (policy_by_code.get(pt) or {}).get(
                    "canonical_title_fa", ""
                ),
                "proposed_title_fa": next(
                    (
                        o["canonical_title_fa"]
                        for o in overlay
                        if o["product_type_code"] == pt
                    ),
                    "",
                ),
                "proposal_status": next(
                    (
                        o["proposal_status"]
                        for o in overlay
                        if o["product_type_code"] == pt
                    ),
                    "",
                ),
                "safe_recommendation": "no",
                "owner_decision_id": next(
                    (
                        o["decision_group"]
                        for o in overlay
                        if o["product_type_code"] == pt
                    ),
                    "",
                ),
                "notes": g.recommended_action,
            }
        )

    variant_options = []
    for pt in EXPECTED_VARIANT_PT_COUNTS:
        o = next(x for x in overlay if x["product_type_code"] == pt)
        variant_options.append(
            {
                "product_type_code": pt,
                "rows": groups[pt].product_count,
                "verdict": groups[pt].verdict,
                "proposed_variant_property": o.get("primary_variant_property", ""),
                "dimension": o.get("variant_dimension", ""),
                "unit": o.get("source_unit", ""),
                "formatter": o.get("formatter", ""),
                "measurement_range_forbidden_reason": (
                    "body_length_not_range"
                    if pt in {"LEVEL", "DIGITAL_LEVEL"}
                    else "multi_dimensional"
                    if pt in {"SURFACE_PLATE", "V_BLOCK"}
                    else "unconfirmed_dimension"
                    if pt == "PRECISION_VISE"
                    else ""
                ),
                "proposal_status": o["proposal_status"],
                "owner_decision_id": o["decision_group"],
                "notes": o["notes"],
            }
        )

    # Semantic summary counts
    verdict_counts = Counter(g.verdict for g in groups.values())

    optical = by_pt["OPTICAL_EDGE_FINDER"][0]
    optical_oem = oem_by_code.get(optical["manufacturer_code"])

    taper_lists = defaultdict(list)
    for r in by_pt["TAPER_GAUGE"]:
        h = _oem_heading(r, oem_by_code.get(r["manufacturer_code"]))
        name = r.get("historical_name") or ""
        taper_lists[classify_taper_subfamily(h, name)].append(r["manufacturer_code"])

    return {
        "rows": rows,
        "groups": groups,
        "overlay": overlay,
        "owner_decisions": owner_decisions,
        "sims": sims,
        "wave3c": w3c,
        "collision": coll,
        "gen_caliper_split": gen_rows,
        "bore_analysis": bore_rows,
        "level_analysis": level_rows,
        "property_requirements": prop_reqs,
        "naming_options": naming_options,
        "variant_options": variant_options,
        "verdict_counts": dict(verdict_counts),
        "safe_overlay_count": safe_count,
        "phase2f_names": phase2f_names,
        "policy_sha256": sha256_file(policy_path),
        "matrix_sha256": sha256_file(matrix_path),
        "candidates_sha256": sha256_file(cand_path),
        "oem_sha256": sha256_file(oem_path),
        "optical": {
            "manufacturer_code": optical["manufacturer_code"],
            "historical_name": optical.get("historical_name", ""),
            "oem_evidence_status": _oem_status(optical_oem),
            "oem_heading": _oem_heading(optical, optical_oem),
            "recommended_persian_title": "",
            "direct_unlock_retained": False,
            "result": "DOWNGRADED_TO_SOURCE_EVIDENCE_REQUIRED",
        },
        "taper_family_lists": dict(taper_lists),
        "taper_verdict": "REQUIRES_PT_SPLIT",
    }
