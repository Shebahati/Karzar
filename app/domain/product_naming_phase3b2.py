"""Phase 3B2 — owner decision freeze & governance apply rehearsal (no live mutation)."""

from __future__ import annotations

import csv
import hashlib
import re
import sqlite3
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PHASE3B1_DIR_REL = "audit/product-naming-phase3b1-governance-review"
PHASE2D_CANDIDATES_REL = "audit/product-naming-phase2d/PHASE2D_RENAME_CANDIDATES_PROPOSED.csv"
OEM_REGISTRY_REL = (
    "docs/architecture/specs/product-naming-v1/INSIZE_OEM_PRODUCT_IDENTITY_REGISTRY.csv"
)
POLICY_REL = "docs/architecture/specs/product-naming-v1/PRODUCT_TYPE_CANONICAL_NAMING_POLICY.csv"
PHASE3A_MATRIX_REL = "audit/product-naming-phase3a-hold-resolution/PHASE3A_ROOT_CAUSE_MATRIX.csv"

WAVE_3B_NAME = "WAVE_3B_GOVERNANCE_QUICK_WINS"
EXPECTED_WAVE_3B_ROWS = 132
EXPECTED_APPLIED_ROWS = 47
EXPECTED_DECISION_COUNT = 11
EXISTING_WAVE3C_ROWS = 58
PHASE3B1_MERGE_SHA = "a8a75026a26ec528fc102c40333b1327c73962eb"

FORBIDDEN_MUTATION_FLAGS = frozenset(
    {"--apply", "--mutate", "--write-db", "--commit", "--force", "--write-policy", "--live-apply"}
)
MUTATION_SQL_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|TRUNCATE|DROP|ALTER|CREATE)\b", re.I
)

# Owner-approved freeze — exact; do not reinterpret.
OWNER_APPROVED: dict[str, dict[str, str]] = {
    "D-GENCAL-01": {
        "product_type_code": "GEN_CALIPER",
        "approved_option": "OPTION_B",
        "approval_mode": "UNCONDITIONAL",
        "conditional_gate": "",
        "semantic_effect": "Immediate LONG_JAW_CALIPER split; residual GEN_CALIPER with qualifiers",
        "future_mutation_classes": "ProductType.create;ProductType.reassign;policy.delta",
    },
    "D-BORE-01": {
        "product_type_code": "BORE_GAUGE",
        "approved_option": "OPTION_A",
        "approval_mode": "UNCONDITIONAL",
        "conditional_gate": "",
        "semantic_effect": "Reassign 3127-300 to INSIDE_MICROMETER; residual BORE_GAUGE synonym-free title",
        "future_mutation_classes": "ProductType.reassign;policy.delta",
    },
    "D-DIVIDER-01": {
        "product_type_code": "DIVIDER",
        "approved_option": "OPTION_A",
        "approval_mode": "UNCONDITIONAL",
        "conditional_gate": "",
        "semantic_effect": "Split INSIDE_SPRING_CALIPER / OUTSIDE_SPRING_CALIPER; no STRAIGHT_DIVIDER from legacy name",
        "future_mutation_classes": "ProductType.create;ProductType.reassign;policy.delta",
    },
    "D-TAPER-01": {
        "product_type_code": "TAPER_GAUGE",
        "approved_option": "OPTION_A",
        "approval_mode": "UNCONDITIONAL",
        "conditional_gate": "",
        "semantic_effect": "Split GAP_TAPER_GAUGE / TAPER_BORE_GAUGE / TAPER_GAUGE_SET",
        "future_mutation_classes": "ProductType.create;ProductType.reassign;policy.delta",
    },
    "D-STRAIGHT-01": {
        "product_type_code": "STRAIGHT_EDGE",
        "approved_option": "OPTION_C",
        "approval_mode": "UNCONDITIONAL",
        "conditional_gate": "",
        "semantic_effect": "HOLD until exact OEM evidence; no PT/title apply",
        "future_mutation_classes": "none",
    },
    "D-OPTICAL-01": {
        "product_type_code": "OPTICAL_EDGE_FINDER",
        "approved_option": "CONDITIONAL_B_THEN_A_ON_EXACT_OEM_EVIDENCE",
        "approval_mode": "CONDITIONAL",
        "conditional_gate": "EXACT_OPTICAL_EDGE_FINDER_OEM",
        "semantic_effect": "Hold unless EXACT optical edge finder identity; then title مرکزیاب نوری eligible",
        "future_mutation_classes": "policy.delta_conditional",
    },
    "D-LEVEL-01": {
        "product_type_code": "LEVEL",
        "approved_option": "OPTION_A",
        "approval_mode": "UNCONDITIONAL",
        "conditional_gate": "",
        "semantic_effect": "Reassign digital/laser/inclinometer out; residual LEVEL uses body_length",
        "future_mutation_classes": "ProductType.create;ProductType.reassign;property.create;policy.delta",
    },
    "D-DLEVEL-01": {
        "product_type_code": "DIGITAL_LEVEL",
        "approved_option": "OPTION_A",
        "approval_mode": "UNCONDITIONAL",
        "conditional_gate": "",
        "semantic_effect": "Keep 4910-* DIGITAL_LEVEL+body_length; review 2199-1 multi-function",
        "future_mutation_classes": "ProductType.reassign;property.create;policy.delta",
    },
    "D-PLATE-01": {
        "product_type_code": "SURFACE_PLATE",
        "approved_option": "OPTION_A",
        "approval_mode": "UNCONDITIONAL",
        "conditional_gate": "",
        "semantic_effect": "Keep SURFACE_PLATE; plate_dimensions L×W×T mm",
        "future_mutation_classes": "property.create;PT.membership;policy.delta",
    },
    "D-VISE-01": {
        "product_type_code": "PRECISION_VISE",
        "approved_option": "CONDITIONAL_C_THEN_A_ON_EXACT_OEM_EVIDENCE",
        "approval_mode": "CONDITIONAL",
        "conditional_gate": "EXACT_JAW_OPENING_CAPACITY_OEM",
        "semantic_effect": "Hold until OEM proves jaw opening; then jaw_opening_capacity",
        "future_mutation_classes": "property.create_conditional;policy.delta_conditional",
    },
    "D-VBLOCK-01": {
        "product_type_code": "V_BLOCK",
        "approved_option": "OPTION_A_WITH_6890_702_HELD",
        "approval_mode": "UNCONDITIONAL_WITH_ROW_EXCEPTION",
        "conditional_gate": "6890-702_EXPLICIT_HOLD",
        "semantic_effect": "Block dimensions for evidenced rows; 6890-702 held separately",
        "future_mutation_classes": "property.create_conditional;policy.delta",
    },
}

EXPECTED_PT_COUNTS = {
    "GEN_CALIPER": 65,
    "BORE_GAUGE": 16,
    "DIVIDER": 9,
    "TAPER_GAUGE": 9,
    "STRAIGHT_EDGE": 1,
    "OPTICAL_EDGE_FINDER": 1,
    "LEVEL": 16,
    "DIGITAL_LEVEL": 3,
    "SURFACE_PLATE": 6,
    "PRECISION_VISE": 3,
    "V_BLOCK": 3,
}

DECISION_BY_PT = {v["product_type_code"]: k for k, v in OWNER_APPROVED.items()}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def reject_mutation_flags(argv: Sequence[str]) -> None:
    import sys

    for a in argv:
        if a in FORBIDDEN_MUTATION_FLAGS or any(
            a.startswith(f"{f}=") for f in FORBIDDEN_MUTATION_FLAGS
        ):
            print(f"ERROR: Phase 3B2 forbids mutation flag {a}", file=sys.stderr)
            raise SystemExit(2)


def assert_readonly_sql(sql: str) -> None:
    if MUTATION_SQL_RE.search(sql):
        raise RuntimeError("Phase 3B2 refuses mutation-capable live SQL")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_wave3b_scope(phase3b1_dir: Path) -> list[dict[str, str]]:
    rows = _read_csv(phase3b1_dir / "PHASE3B1_SCOPE.csv")
    if len(rows) != EXPECTED_WAVE_3B_ROWS:
        raise ValueError(f"Wave 3B scope {len(rows)} != {EXPECTED_WAVE_3B_ROWS}")
    return rows


def load_best_oem(path: Path, codes: set[str]) -> dict[str, dict[str, str]]:
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


def owner_decision_freeze_rows() -> list[dict[str, str]]:
    rows = []
    for did, meta in OWNER_APPROVED.items():
        rows.append(
            {
                "decision_id": did,
                "product_type_code": meta["product_type_code"],
                "approved_option": meta["approved_option"],
                "approval_mode": meta["approval_mode"],
                "conditional_gate": meta["conditional_gate"],
                "affected_rows": str(EXPECTED_PT_COUNTS[meta["product_type_code"]]),
                "owner_status": "APPROVED",
                "semantic_effect": meta["semantic_effect"],
                "future_mutation_classes": meta["future_mutation_classes"],
                "notes": "Owner-approved Phase 3B1 recommended path; frozen for Phase 3B2",
            }
        )
    rows.sort(key=lambda r: r["decision_id"])
    return rows


def owner_decision_sha256(rows: list[dict[str, str]]) -> str:
    # Deterministic canonical serialization
    lines = []
    for r in sorted(rows, key=lambda x: x["decision_id"]):
        lines.append(
            "|".join(
                [
                    r["decision_id"],
                    r["approved_option"],
                    r["approval_mode"],
                    r["conditional_gate"],
                    r["owner_status"],
                    r["affected_rows"],
                ]
            )
        )
    return sha256_text("\n".join(lines) + "\n")


@dataclass
class NewPTProposal:
    code: str
    english_concept: str
    persian_title: str
    semantic_definition: str
    inclusion_rule: str
    exclusion_rule: str
    parent_category: str
    naming_profile: str
    variant_policy_concept: str
    primary_variant_property: str
    oem_evidence_basis: str
    affected_rows: int
    decision_ids: str


NEW_PT_CATALOG: dict[str, NewPTProposal] = {
    "LONG_JAW_CALIPER": NewPTProposal(
        code="LONG_JAW_CALIPER",
        english_concept="Long jaw vernier/digital caliper",
        persian_title="کولیس فک‌بلند",
        semantic_definition="Caliper whose primary OEM identity is long-jaw measuring faces",
        inclusion_rule="OEM heading contains LONG JAW CALIPERS (or equivalent exact family)",
        exclusion_rule="Standard digital/vernier calipers; hook/point/blade/offset specialized PTs",
        parent_category="metrology.caliper",
        naming_profile="metrology.caliper.v1",
        variant_policy_concept="VARIANT_REQUIRED",
        primary_variant_property="measurement_range",
        oem_evidence_basis="INSIZE LONG JAW VERNIER CALIPERS headings",
        affected_rows=0,
        decision_ids="D-GENCAL-01",
    ),
    "INSIDE_SPRING_CALIPER": NewPTProposal(
        code="INSIDE_SPRING_CALIPER",
        english_concept="Inside spring caliper",
        persian_title="پرگار فنری داخل‌سنج",
        semantic_definition="Spring caliper for internal transfer/measurement per OEM INSIDE SPRING CALIPERS",
        inclusion_rule="OEM heading INSIDE SPRING CALIPERS",
        exclusion_rule="Outside spring calipers; indicating calipers; dividers for drafting",
        parent_category="metrology.transfer",
        naming_profile="metrology.caliper.v1",
        variant_policy_concept="VARIANT_REQUIRED",
        primary_variant_property="body_length",
        oem_evidence_basis="INSIZE INSIDE SPRING CALIPERS",
        affected_rows=0,
        decision_ids="D-DIVIDER-01",
    ),
    "OUTSIDE_SPRING_CALIPER": NewPTProposal(
        code="OUTSIDE_SPRING_CALIPER",
        english_concept="Outside spring caliper",
        persian_title="پرگار فنری خارج‌سنج",
        semantic_definition="Spring caliper for external transfer/measurement per OEM OUTSIDE SPRING CALIPERS",
        inclusion_rule="OEM heading OUTSIDE SPRING CALIPERS (incl. legacy 'straight' Persian labels under that heading)",
        exclusion_rule="Inside spring calipers; do not invent STRAIGHT_DIVIDER from Product.name",
        parent_category="metrology.transfer",
        naming_profile="metrology.caliper.v1",
        variant_policy_concept="VARIANT_REQUIRED",
        primary_variant_property="body_length",
        oem_evidence_basis="INSIZE OUTSIDE SPRING CALIPERS",
        affected_rows=0,
        decision_ids="D-DIVIDER-01",
    ),
    "GAP_TAPER_GAUGE": NewPTProposal(
        code="GAP_TAPER_GAUGE",
        english_concept="Gap / taper leaf gauge",
        persian_title="گپ‌سنج",
        semantic_definition="Leaf/gap taper gauge for clearance measurement (OEM TAPER GAUGES)",
        inclusion_rule="OEM heading TAPER GAUGES (gap family 4833)",
        exclusion_rule="Taper bore gauges; taper gauge + ruler sets",
        parent_category="metrology.gauge",
        naming_profile="metrology.micrometer.v1",
        variant_policy_concept="VARIANT_REQUIRED",
        primary_variant_property="measurement_range",
        oem_evidence_basis="INSIZE TAPER GAUGES",
        affected_rows=0,
        decision_ids="D-TAPER-01",
    ),
    "TAPER_BORE_GAUGE": NewPTProposal(
        code="TAPER_BORE_GAUGE",
        english_concept="Taper bore gauge",
        persian_title="گیج مخروطی داخل",
        semantic_definition="Gauge for measuring internal taper/bore (OEM TAPER BORE GAUGES)",
        inclusion_rule="OEM heading TAPER BORE GAUGES",
        exclusion_rule="Gap/leaf taper gauges; sets with steel ruler",
        parent_category="metrology.gauge",
        naming_profile="metrology.micrometer.v1",
        variant_policy_concept="VARIANT_REQUIRED",
        primary_variant_property="measurement_range",
        oem_evidence_basis="INSIZE TAPER BORE GAUGES",
        affected_rows=0,
        decision_ids="D-TAPER-01",
    ),
    "TAPER_GAUGE_SET": NewPTProposal(
        code="TAPER_GAUGE_SET",
        english_concept="Taper gauge and steel ruler set",
        persian_title="ست گپ‌سنج با خط‌کش",
        semantic_definition="Sold-as set combining taper/gap gauge with steel ruler",
        inclusion_rule="OEM heading TAPER GAUGE SET or TAPER GAUGE AND STEEL RULER SET",
        exclusion_rule="Standalone gap or taper bore gauges",
        parent_category="metrology.gauge",
        naming_profile="metrology.micrometer.v1",
        variant_policy_concept="VARIANT_REQUIRED",
        primary_variant_property="measurement_range",
        oem_evidence_basis="INSIZE TAPER GAUGE SET headings",
        affected_rows=0,
        decision_ids="D-TAPER-01",
    ),
    "LASER_LEVEL": NewPTProposal(
        code="LASER_LEVEL",
        english_concept="Cross-line / laser level",
        persian_title="تراز لیزری",
        semantic_definition="Laser projection level distinct from spirit/frame levels",
        inclusion_rule="OEM heading CROSS-LINE LASER LEVEL or equivalent laser level family",
        exclusion_rule="Conventional spirit levels; digital inclinometers without laser projection",
        parent_category="metrology.level",
        naming_profile="metrology.micrometer.v1",
        variant_policy_concept="VARIANT_NOT_REQUIRED_OR_MODEL",
        primary_variant_property="",
        oem_evidence_basis="INSIZE CROSS-LINE LASER LEVEL",
        affected_rows=0,
        decision_ids="D-LEVEL-01",
    ),
}


def _oem_status(oem: Mapping[str, str] | None) -> str:
    return ((oem or {}).get("evidence_status") or "missing").strip()


def _oem_heading(oem: Mapping[str, str] | None) -> str:
    return ((oem or {}).get("OEM_product_heading") or "").strip()


def route_product(
    row: Mapping[str, str],
    *,
    gen_by_id: Mapping[str, dict[str, str]],
    bore_by_id: Mapping[str, dict[str, str]],
    level_by_id: Mapping[str, dict[str, str]],
    oem_by_code: Mapping[str, dict[str, str]],
) -> dict[str, str]:
    pid = row["product_id"]
    code = row["manufacturer_code"]
    pt = row["product_type_code"]
    did = DECISION_BY_PT[pt]
    oem = oem_by_code.get(code)
    es = _oem_status(oem)
    heading = _oem_heading(oem)
    authority = "OEM_registry" if heading or es != "missing" else "phase3b1_analysis"

    def out(
        action: str,
        rec_pt: str,
        subfamily: str,
        *,
        hold: str = "",
        confidence: str = "HIGH",
        future_write: str = "yes",
    ) -> dict[str, str]:
        return {
            "product_id": pid,
            "manufacturer_code": code,
            "current_pt_code": pt,
            "approved_decision_id": did,
            "semantic_subfamily": subfamily,
            "recommended_pt_code": rec_pt,
            "recommended_pt_action": action,
            "evidence_status": es,
            "authority_source": authority,
            "confidence": confidence,
            "future_write_required": future_write if action not in {
                "SOURCE_EVIDENCE_HOLD",
                "SEMANTIC_HOLD",
            }
            else "no",
            "hold_reason_if_any": hold,
        }

    if pt == "GEN_CALIPER":
        g = gen_by_id[pid]
        sub = g["subfamily"]
        if sub == "LONG_JAW_CALIPER":
            return out("CREATE_NEW_PT_AND_ASSIGN", "LONG_JAW_CALIPER", sub)
        if sub in {
            "DIGITAL_CALIPER",
            "VERNIER_CALIPER",
            "MINI_CALIPER",
            "CARBIDE_TIPPED_CALIPER",
            "LARGE_FACE_CALIPER",
            "FRACTION_READING_CALIPER",
        }:
            return out("KEEP_EXISTING_PT", "GEN_CALIPER", sub, future_write="policy_only")
        return out(
            "SOURCE_EVIDENCE_HOLD",
            "GEN_CALIPER",
            sub,
            hold="generic_or_name_only_without_OEM_heading",
            confidence="LOW",
        )

    if pt == "BORE_GAUGE":
        b = bore_by_id[pid]
        sub = b["subfamily"]
        if sub == "THREE_POINT_INTERNAL_MICROMETER" or code == "3127-300":
            return out("REASSIGN_EXISTING_PT", "INSIDE_MICROMETER", sub)
        # Display/actuation (digital/dial) are not separate PTs — residual bore gauge family
        return out("KEEP_EXISTING_PT", "BORE_GAUGE", sub, future_write="policy_only")

    if pt == "DIVIDER":
        if code.startswith("7261"):
            return out("CREATE_NEW_PT_AND_ASSIGN", "INSIDE_SPRING_CALIPER", "INSIDE_SPRING_CALIPER")
        # 7247 under OUTSIDE SPRING CALIPERS OEM — not STRAIGHT_DIVIDER
        if code.startswith("7247") or code.startswith("7262"):
            return out(
                "CREATE_NEW_PT_AND_ASSIGN",
                "OUTSIDE_SPRING_CALIPER",
                "OUTSIDE_SPRING_CALIPER",
            )
        return out("SEMANTIC_HOLD", "DIVIDER", "DIVIDER_UNKNOWN", hold="unmapped_divider_code")

    if pt == "TAPER_GAUGE":
        if code.startswith("4833"):
            return out("CREATE_NEW_PT_AND_ASSIGN", "GAP_TAPER_GAUGE", "GAP_OR_TAPER_GAUGE")
        if code.startswith("4852"):
            return out("CREATE_NEW_PT_AND_ASSIGN", "TAPER_BORE_GAUGE", "TAPER_BORE_GAUGE")
        if code in {"4829-1", "4837-1"}:
            return out("CREATE_NEW_PT_AND_ASSIGN", "TAPER_GAUGE_SET", "TAPER_GAUGE_SET")
        return out("SEMANTIC_HOLD", "TAPER_GAUGE", "TAPER_UNKNOWN", hold="unmapped_taper_code")

    if pt == "STRAIGHT_EDGE":
        return out(
            "SOURCE_EVIDENCE_HOLD",
            "STRAIGHT_EDGE",
            "STRAIGHT_EDGE",
            hold="Option_C_hold_until_exact_OEM",
            confidence="LOW",
        )

    if pt == "OPTICAL_EDGE_FINDER":
        # Conditional — insufficient evidence cannot advance
        return out(
            "SOURCE_EVIDENCE_HOLD",
            "OPTICAL_EDGE_FINDER",
            "OPTICAL_EDGE_FINDER",
            hold="conditional_gate_EXACT_OEM_not_met",
            confidence="LOW",
        )

    if pt == "LEVEL":
        lv = level_by_id.get(pid, {})
        cls = lv.get("instrument_class") or ""
        if code == "4917-30" or cls == "LASER_LEVEL" or "LASER" in heading.upper():
            return out("CREATE_NEW_PT_AND_ASSIGN", "LASER_LEVEL", "LASER_LEVEL")
        if cls == "DIGITAL_LEVEL" or "DIGITAL LEVEL" in heading.upper() or "SLOPE" in heading.upper():
            return out("REASSIGN_EXISTING_PT", "DIGITAL_LEVEL", "DIGITAL_LEVEL")
        if cls == "INCLINOMETER":
            return out(
                "SEMANTIC_HOLD",
                "LEVEL",
                "INCLINOMETER",
                hold="inclinometer_needs_dedicated_review",
            )
        return out("KEEP_EXISTING_PT", "LEVEL", "CONVENTIONAL_LEVEL", future_write="property+policy")

    if pt == "DIGITAL_LEVEL":
        if code.startswith("2199"):
            return out(
                "SEMANTIC_HOLD",
                "DIGITAL_LEVEL",
                "MULTI_FUNCTION_METER",
                hold="2199-1_multi_function_not_forced_to_DIGITAL_LEVEL",
            )
        return out("KEEP_EXISTING_PT", "DIGITAL_LEVEL", "DIGITAL_LEVEL", future_write="property+policy")

    if pt == "SURFACE_PLATE":
        return out("KEEP_EXISTING_PT", "SURFACE_PLATE", "GRANITE_SURFACE_PLATE", future_write="property+policy")

    if pt == "PRECISION_VISE":
        return out(
            "SOURCE_EVIDENCE_HOLD",
            "PRECISION_VISE",
            "PRECISION_VISE",
            hold="conditional_gate_jaw_opening_OEM_not_met",
            confidence="LOW",
        )

    if pt == "V_BLOCK":
        if code == "6890-702":
            return out(
                "SOURCE_EVIDENCE_HOLD",
                "V_BLOCK",
                "V_BLOCK_LEGACY_NAME",
                hold="explicit_6890_702_hold",
                confidence="LOW",
            )
        # 6801-* — OEM insufficient for dimensions; hold property path
        if es != "EXACT_PRODUCT_IDENTITY":
            return out(
                "SOURCE_EVIDENCE_HOLD",
                "V_BLOCK",
                "V_BLOCK",
                hold="block_dimensions_require_exact_OEM",
                confidence="MEDIUM",
            )
        return out("KEEP_EXISTING_PT", "V_BLOCK", "V_BLOCK", future_write="property+policy")

    return out("SEMANTIC_HOLD", pt, "UNKNOWN", hold="unhandled_pt")


def source_evidence_closure(
    oem_by_code: Mapping[str, dict[str, str]],
) -> list[dict[str, str]]:
    targets = [
        ("4700-200", "STRAIGHT_EDGE", "D-STRAIGHT-01"),
        ("6566-2", "OPTICAL_EDGE_FINDER", "D-OPTICAL-01"),
        ("6520-67", "PRECISION_VISE", "D-VISE-01"),
        ("6520-87", "PRECISION_VISE", "D-VISE-01"),
        ("6520-102", "PRECISION_VISE", "D-VISE-01"),
        ("6801-1201", "V_BLOCK", "D-VBLOCK-01"),
        ("6801-1202", "V_BLOCK", "D-VBLOCK-01"),
        ("6890-702", "V_BLOCK", "D-VBLOCK-01"),
    ]
    out = []
    for code, pt, did in targets:
        oem = oem_by_code.get(code)
        es = _oem_status(oem)
        heading = _oem_heading(oem)
        if pt == "OPTICAL_EDGE_FINDER":
            classification = (
                "EXACT_OPTICAL_EDGE_FINDER"
                if es == "EXACT_PRODUCT_IDENTITY" and "OPTICAL" in heading.upper()
                else "NOT_FOUND"
                if es == "missing"
                else "AMBIGUOUS"
            )
            title_eligible = "yes" if classification == "EXACT_OPTICAL_EDGE_FINDER" else "no"
        elif pt == "PRECISION_VISE":
            classification = (
                "EXACT_CONFIRMED_JAW_OPENING"
                if es == "EXACT_PRODUCT_IDENTITY" and "VISE" in heading.upper() and False
                else "AMBIGUOUS"
                if heading
                else "NOT_FOUND"
            )
            # Heading PRECISION VISES alone does not prove 67/87/102 = jaw opening
            classification = "AMBIGUOUS" if heading else "NOT_FOUND"
            title_eligible = "no"
        elif pt == "STRAIGHT_EDGE":
            classification = "NOT_FOUND" if not heading else "AMBIGUOUS"
            title_eligible = "no"
        elif code == "6890-702":
            classification = "NOT_FOUND" if not heading else "AMBIGUOUS"
            title_eligible = "no"
        else:  # V_BLOCK 6801
            classification = "AMBIGUOUS" if heading or es == "INSUFFICIENT" else "NOT_FOUND"
            title_eligible = "no"
        out.append(
            {
                "manufacturer_code": code,
                "product_type_code": pt,
                "decision_id": did,
                "oem_evidence_status": es,
                "oem_heading": heading,
                "occurrence_class": "PRODUCT_HEADING" if heading else "INDEX_ONLY_OR_ABSENT",
                "closure_classification": classification,
                "governance_eligible": title_eligible,
                "product_name_used_as_authority": "no",
                "sku_used_as_authority": "no",
                "notes": "Local INSIZE registry only; no fake PDF pages",
            }
        )
    return out


def property_definition_proposals() -> list[dict[str, str]]:
    return [
        {
            "property_code": "body_length",
            "label_fa": "طول بدنه",
            "label_en": "Body length",
            "semantic_definition": "Physical body/frame length of level or spring caliper",
            "data_type": "number",
            "dimension": "length",
            "unit": "mm",
            "cardinality": "single",
            "normalization_rule": "store_mm_integer_or_decimal",
            "display_formatter": "body_length_mm",
            "validation_rule": "positive_finite_mm",
            "allowed_product_types": "LEVEL;DIGITAL_LEVEL;INSIDE_SPRING_CALIPER;OUTSIDE_SPRING_CALIPER",
            "source_authority_requirement": "OEM_catalog_body_length",
            "example_values": "150;200;300;400;600",
            "collision_with_existing": "must_not_alias_measurement_range",
            "proposal_status": "NEW_PROPERTY_REQUIRED",
        },
        {
            "property_code": "plate_dimensions",
            "label_fa": "ابعاد صفحه",
            "label_en": "Plate dimensions",
            "semantic_definition": "Surface plate length × width × thickness",
            "data_type": "tuple3",
            "dimension": "length_width_thickness",
            "unit": "mm",
            "cardinality": "ordered_triple",
            "normalization_rule": "L_x_W_x_T_mm_canonical_order",
            "display_formatter": "plate_lwt_mm",
            "validation_rule": "three_positive_mm",
            "allowed_product_types": "SURFACE_PLATE",
            "source_authority_requirement": "OEM_granite_surface_plate_table",
            "example_values": "500×315×70 میلی‌متر",
            "collision_with_existing": "not_measurement_range",
            "proposal_status": "NEW_PROPERTY_REQUIRED",
        },
        {
            "property_code": "jaw_opening_capacity",
            "label_fa": "ظرفیت باز شدن فک",
            "label_en": "Jaw opening capacity",
            "semantic_definition": "Maximum jaw opening of precision vise",
            "data_type": "number",
            "dimension": "length",
            "unit": "mm",
            "cardinality": "single",
            "normalization_rule": "store_mm",
            "display_formatter": "jaw_opening_mm",
            "validation_rule": "positive_finite_mm",
            "allowed_product_types": "PRECISION_VISE",
            "source_authority_requirement": "OEM_precision_vise_table_exact",
            "example_values": "67;87;102",
            "collision_with_existing": "not_inferred_from_SKU_or_name",
            "proposal_status": "NEW_PROPERTY_REQUIRED_CONDITIONAL",
        },
        {
            "property_code": "block_dimensions",
            "label_fa": "ابعاد بلوک",
            "label_en": "Block dimensions",
            "semantic_definition": "V-block overall L×W×H",
            "data_type": "tuple3",
            "dimension": "length_width_height",
            "unit": "mm",
            "cardinality": "ordered_triple",
            "normalization_rule": "L_x_W_x_H_mm",
            "display_formatter": "block_lwh_mm",
            "validation_rule": "three_positive_mm",
            "allowed_product_types": "V_BLOCK",
            "source_authority_requirement": "OEM_v_block_table_exact",
            "example_values": "95×70×80",
            "collision_with_existing": "not_workpiece_diameter_without_OEM",
            "proposal_status": "NEW_PROPERTY_REQUIRED_CONDITIONAL",
        },
    ]


def post_governance_state(routing: Mapping[str, str], pt: str, code: str) -> str:
    action = routing["recommended_pt_action"]
    if action in {"SOURCE_EVIDENCE_HOLD"}:
        return "SOURCE_EVIDENCE_HOLD"
    if action == "SEMANTIC_HOLD":
        return "SEMANTIC_HOLD"
    if action in {"CREATE_NEW_PT_AND_ASSIGN", "REASSIGN_EXISTING_PT"}:
        return "PT_APPLY_REQUIRED"
    # KEEP_EXISTING
    if pt == "SURFACE_PLATE":
        return "PROPERTY_APPLY_REQUIRED"
    if pt in {"LEVEL", "DIGITAL_LEVEL"} and routing["recommended_pt_code"] in {
        "LEVEL",
        "DIGITAL_LEVEL",
    }:
        return "PROPERTY_APPLY_REQUIRED"
    if pt == "GEN_CALIPER" and routing["recommended_pt_code"] == "GEN_CALIPER":
        return "READY_FOR_POLICY_APPLY_ONLY"
    if pt == "BORE_GAUGE" and routing["recommended_pt_code"] == "BORE_GAUGE":
        return "READY_FOR_POLICY_APPLY_ONLY"
    return "READY_FOR_POLICY_APPLY_ONLY"


def build_policy_delta(
    routing_rows: list[dict[str, str]],
    policy_by_code: Mapping[str, dict[str, str]],
) -> list[dict[str, str]]:
    deltas: list[dict[str, str]] = []
    # New PTs
    for code, prop in NEW_PT_CATALOG.items():
        deltas.append(
            {
                "product_type_code": code,
                "action": "ADD",
                "old_canonical_title_fa": "",
                "new_canonical_title_fa": prop.persian_title,
                "old_variant_policy": "",
                "new_variant_policy": prop.variant_policy_concept,
                "old_primary_variant_property": "",
                "new_primary_variant_property": prop.primary_variant_property,
                "reason": "Owner-approved new PT from Phase 3B2 routing",
                "decision_id": prop.decision_ids,
                "evidence_basis": prop.oem_evidence_basis,
            }
        )
    # Updates
    updates = [
        (
            "GEN_CALIPER",
            "کولیس",
            "VARIANT_REQUIRED",
            "measurement_range",
            "D-GENCAL-01",
            "Residual generic caliper after LONG_JAW split; title only with qualifier governance",
            "UPDATE",
        ),
        (
            "BORE_GAUGE",
            "گیج داخل سیلندر",
            "VARIANT_REQUIRED",
            "measurement_range",
            "D-BORE-01",
            "Synonym-free residual bore gauge title after micrometer reassignment",
            "UPDATE",
        ),
        (
            "LEVEL",
            "تراز",
            "VARIANT_REQUIRED",
            "body_length",
            "D-LEVEL-01",
            "body_length not measurement_range",
            "UPDATE",
        ),
        (
            "DIGITAL_LEVEL",
            "تراز دیجیتال",
            "VARIANT_REQUIRED",
            "body_length",
            "D-DLEVEL-01",
            "body_length for 4910 residual",
            "UPDATE",
        ),
        (
            "SURFACE_PLATE",
            "صفحه صافی",
            "VARIANT_REQUIRED",
            "plate_dimensions",
            "D-PLATE-01",
            "multi-dimensional plate_dimensions",
            "UPDATE",
        ),
        (
            "STRAIGHT_EDGE",
            "",
            "HOLD_VARIANT_POLICY_UNDEFINED",
            "",
            "D-STRAIGHT-01",
            "Option C hold",
            "HOLD",
        ),
        (
            "OPTICAL_EDGE_FINDER",
            "",
            "VARIANT_NOT_REQUIRED_APPROVED",
            "",
            "D-OPTICAL-01",
            "Conditional — exact OEM not met",
            "HOLD",
        ),
        (
            "PRECISION_VISE",
            "گیره دقیق",
            "HOLD_VARIANT_POLICY_UNDEFINED",
            "",
            "D-VISE-01",
            "Conditional jaw opening not proven",
            "HOLD",
        ),
        (
            "V_BLOCK",
            "وی‌بلوک",
            "HOLD_VARIANT_POLICY_UNDEFINED",
            "",
            "D-VBLOCK-01",
            "block_dimensions pending exact OEM; 6890-702 held",
            "HOLD",
        ),
        (
            "DIVIDER",
            "",
            "HOLD_VARIANT_POLICY_UNDEFINED",
            "",
            "D-DIVIDER-01",
            "Superseded by spring caliper PT split — legacy code retained but no new title",
            "HOLD",
        ),
        (
            "TAPER_GAUGE",
            "",
            "HOLD_VARIANT_POLICY_UNDEFINED",
            "",
            "D-TAPER-01",
            "Superseded by gap/bore/set split",
            "HOLD",
        ),
    ]
    for code, title, vp, prop, did, reason, action in updates:
        old = policy_by_code.get(code, {})
        deltas.append(
            {
                "product_type_code": code,
                "action": action,
                "old_canonical_title_fa": old.get("canonical_title_fa", ""),
                "new_canonical_title_fa": title if action != "HOLD" else old.get("canonical_title_fa", ""),
                "old_variant_policy": old.get("variant_policy", ""),
                "new_variant_policy": vp,
                "old_primary_variant_property": old.get("primary_variant_property", ""),
                "new_primary_variant_property": prop,
                "reason": reason,
                "decision_id": did,
                "evidence_basis": "owner_freeze+OEM",
            }
        )
    return deltas


def build_mutation_plan(
    routing_rows: list[dict[str, str]],
    new_pts_used: set[str],
) -> list[dict[str, str]]:
    plan: list[dict[str, str]] = []
    seq = 1
    for code in sorted(new_pts_used):
        prop = NEW_PT_CATALOG[code]
        plan.append(
            {
                "sequence": str(seq),
                "entity_type": "ProductType",
                "entity_id_or_key": code,
                "action": "CREATE",
                "old_value": "",
                "new_value": f"code={code};title_fa={prop.persian_title}",
                "affected_product_id": "",
                "decision_id": prop.decision_ids,
                "dependency": "none",
                "reversible": "yes",
                "rollback_action": f"DELETE ProductType {code} if unused",
            }
        )
        seq += 1
    # Properties (unconditional first)
    for pcode, did in [
        ("body_length", "D-LEVEL-01"),
        ("plate_dimensions", "D-PLATE-01"),
    ]:
        plan.append(
            {
                "sequence": str(seq),
                "entity_type": "Property",
                "entity_id_or_key": pcode,
                "action": "CREATE",
                "old_value": "",
                "new_value": pcode,
                "affected_product_id": "",
                "decision_id": did,
                "dependency": "none",
                "reversible": "yes",
                "rollback_action": f"DELETE Property {pcode}",
            }
        )
        seq += 1
    # Memberships
    for pt, pcode, did in [
        ("LEVEL", "body_length", "D-LEVEL-01"),
        ("DIGITAL_LEVEL", "body_length", "D-DLEVEL-01"),
        ("INSIDE_SPRING_CALIPER", "body_length", "D-DIVIDER-01"),
        ("OUTSIDE_SPRING_CALIPER", "body_length", "D-DIVIDER-01"),
        ("SURFACE_PLATE", "plate_dimensions", "D-PLATE-01"),
    ]:
        plan.append(
            {
                "sequence": str(seq),
                "entity_type": "ProductTypePropertyMembership",
                "entity_id_or_key": f"{pt}:{pcode}",
                "action": "CREATE",
                "old_value": "",
                "new_value": f"{pt}->{pcode}",
                "affected_product_id": "",
                "decision_id": did,
                "dependency": f"Property.{pcode};ProductType.{pt}",
                "reversible": "yes",
                "rollback_action": f"DELETE membership {pt}:{pcode}",
            }
        )
        seq += 1
    # Reassignments / assigns
    for r in sorted(routing_rows, key=lambda x: int(x["product_id"])):
        action = r["recommended_pt_action"]
        if action in {"CREATE_NEW_PT_AND_ASSIGN", "REASSIGN_EXISTING_PT"}:
            plan.append(
                {
                    "sequence": str(seq),
                    "entity_type": "Product.product_type_id",
                    "entity_id_or_key": r["product_id"],
                    "action": "REASSIGN",
                    "old_value": r["current_pt_code"],
                    "new_value": r["recommended_pt_code"],
                    "affected_product_id": r["product_id"],
                    "decision_id": r["approved_decision_id"],
                    "dependency": (
                        f"ProductType.{r['recommended_pt_code']}"
                        if action == "CREATE_NEW_PT_AND_ASSIGN"
                        else "none"
                    ),
                    "reversible": "yes",
                    "rollback_action": f"REASSIGN {r['product_id']} back to {r['current_pt_code']}",
                }
            )
            seq += 1
    # Sanity: no Product.name
    for row in plan:
        if "name" in row["entity_type"].lower() and "product_type" not in row["entity_type"].lower():
            raise ValueError(f"Product.name action forbidden: {row}")
        if row["entity_type"] == "Product.name":
            raise ValueError("Product.name action forbidden in Phase 3B2 plan")
    return plan


# --- Disposable SQLite rehearsal ---


def _init_rehearsal_db(conn: sqlite3.Connection, routing_rows: list[dict[str, str]]) -> None:
    conn.executescript(
        """
        CREATE TABLE product_types (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          code TEXT UNIQUE NOT NULL,
          title_fa TEXT
        );
        CREATE TABLE products (
          id INTEGER PRIMARY KEY,
          manufacturer_code TEXT,
          product_type_code TEXT NOT NULL,
          name TEXT NOT NULL
        );
        CREATE TABLE properties (
          code TEXT PRIMARY KEY,
          dimension TEXT,
          unit TEXT
        );
        CREATE TABLE pt_property_membership (
          product_type_code TEXT NOT NULL,
          property_code TEXT NOT NULL,
          PRIMARY KEY (product_type_code, property_code)
        );
        """
    )
    # Seed existing PTs + products
    existing = {
        r["current_pt_code"] for r in routing_rows
    } | {"INSIDE_MICROMETER", "DIGITAL_LEVEL", "LEVEL", "SURFACE_PLATE", "V_BLOCK", "PRECISION_VISE"}
    for code in sorted(existing):
        conn.execute(
            "INSERT OR IGNORE INTO product_types(code, title_fa) VALUES (?, ?)",
            (code, code),
        )
    for r in routing_rows:
        conn.execute(
            "INSERT INTO products(id, manufacturer_code, product_type_code, name) VALUES (?,?,?,?)",
            (
                int(r["product_id"]),
                r["manufacturer_code"],
                r["current_pt_code"],
                f"fixture-{r['manufacturer_code']}",
            ),
        )
    conn.commit()


def run_disposable_rehearsal(
    routing_rows: list[dict[str, str]],
    mutation_plan: list[dict[str, str]],
    *,
    fail_at: str | None = None,
) -> dict[str, Any]:
    """In-memory SQLite SERIALIZABLE-style txn; always rolls back."""
    conn = sqlite3.connect(":memory:")
    conn.isolation_level = None  # manual transactions
    _init_rehearsal_db(conn, routing_rows)
    pre_fp = _db_fingerprint(conn)
    created_pts: list[str] = []
    reassigned = 0
    props_created = 0
    memberships = 0
    error: str | None = None
    try:
        conn.execute("BEGIN")
        for step in mutation_plan:
            et = step["entity_type"]
            action = step["action"]
            if et == "ProductType" and action == "CREATE":
                code = step["entity_id_or_key"]
                conn.execute(
                    "INSERT INTO product_types(code, title_fa) VALUES (?, ?)",
                    (code, code),
                )
                created_pts.append(code)
                if fail_at == "after_first_pt_create" and len(created_pts) == 1:
                    raise RuntimeError("injected:after_first_pt_create")
            elif et == "Product.product_type_id" and action == "REASSIGN":
                conn.execute(
                    "UPDATE products SET product_type_code = ? WHERE id = ?",
                    (step["new_value"], int(step["affected_product_id"])),
                )
                reassigned += 1
                total_reassign = sum(
                    1
                    for s in mutation_plan
                    if s["entity_type"] == "Product.product_type_id"
                )
                mid = max(1, total_reassign // 2)
                if fail_at == "mid_pt_routing" and reassigned == mid:
                    raise RuntimeError("injected:mid_pt_routing")
                if fail_at == "after_pt_routing" and reassigned == total_reassign:
                    raise RuntimeError("injected:after_pt_routing")
            elif et == "Property" and action == "CREATE":
                if fail_at == "property_create":
                    raise RuntimeError("injected:property_create")
                conn.execute(
                    "INSERT INTO properties(code, dimension, unit) VALUES (?, ?, ?)",
                    (step["entity_id_or_key"], "length", "mm"),
                )
                props_created += 1
            elif et == "ProductTypePropertyMembership" and action == "CREATE":
                if fail_at == "property_membership":
                    raise RuntimeError("injected:property_membership")
                pt, pcode = step["entity_id_or_key"].split(":", 1)
                conn.execute(
                    "INSERT INTO pt_property_membership(product_type_code, property_code) VALUES (?, ?)",
                    (pt, pcode),
                )
                memberships += 1
            else:
                raise RuntimeError(f"unknown plan step {et}/{action}")
        # validation
        if fail_at == "validation_failure":
            raise RuntimeError("injected:validation_failure")
        # Ensure no product names changed
        names = conn.execute("SELECT COUNT(*) FROM products WHERE name NOT LIKE 'fixture-%'").fetchone()[0]
        if names:
            raise RuntimeError("product_name_mutated")
        conn.execute("ROLLBACK")
        status = "ROLLED_BACK_OK"
    except Exception as exc:  # noqa: BLE001 — capture injection
        error = str(exc)
        conn.execute("ROLLBACK")
        status = "ROLLED_BACK_AFTER_FAILURE"
    post_fp = _db_fingerprint(conn)
    persistent = 0 if post_fp == pre_fp else 1
    result = {
        "status": status,
        "error": error,
        "prestate_fingerprint": pre_fp,
        "post_rollback_fingerprint": post_fp,
        "persistent_mutations": persistent,
        "created_pts_in_tx": created_pts if status != "ROLLED_BACK_OK" else created_pts,
        "reassigned_in_tx": reassigned,
        "props_created_in_tx": props_created,
        "memberships_in_tx": memberships,
        "product_name_actions": 0,
        "db_engine": "sqlite3",
        "db_version": sqlite3.sqlite_version,
        "alembic_revision": "n/a_fixture_schema",
        "creation_method": "in_memory_sqlite_minimal_fixture",
        "isolation": "BEGIN/ROLLBACK (manual)",
    }
    conn.close()
    return result


def _db_fingerprint(conn: sqlite3.Connection) -> str:
    parts = []
    for table in ("product_types", "products", "properties", "pt_property_membership"):
        rows = conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
        parts.append(f"{table}:{rows}")
    return sha256_text("|".join(parts))


def run_failure_injections(
    routing_rows: list[dict[str, str]], mutation_plan: list[dict[str, str]]
) -> dict[str, Any]:
    points = [
        "after_first_pt_create",
        "mid_pt_routing",
        "after_pt_routing",
        "property_create",
        "property_membership",
        "validation_failure",
    ]
    results = {}
    for p in points:
        r = run_disposable_rehearsal(routing_rows, mutation_plan, fail_at=p)
        results[p] = {
            "status": r["status"],
            "persistent_mutations": r["persistent_mutations"],
            "error": r["error"],
            "rollback_ok": r["persistent_mutations"] == 0,
        }
    return results


def build_phase3b2_pack(root: Path) -> dict[str, Any]:
    b1 = root / PHASE3B1_DIR_REL
    scope = load_wave3b_scope(b1)
    counts = Counter(r["product_type_code"] for r in scope)
    if dict(counts) != EXPECTED_PT_COUNTS:
        raise ValueError(f"PT counts mismatch: {dict(counts)}")
    ids = [r["product_id"] for r in scope]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate product ids")

    candidates = _read_csv(root / PHASE2D_CANDIDATES_REL)
    if len(candidates) != EXPECTED_APPLIED_ROWS:
        raise ValueError("Phase 2F candidates count")
    inter = {r["product_id"] for r in scope} & {r["product_id"] for r in candidates}
    if inter:
        raise ValueError(f"Phase 2F intersection: {inter}")

    gen = {r["product_id"]: r for r in _read_csv(b1 / "PHASE3B1_GEN_CALIPER_SPLIT_ANALYSIS.csv")}
    bore = {r["product_id"]: r for r in _read_csv(b1 / "PHASE3B1_BORE_GAUGE_ANALYSIS.csv")}
    level = {r["product_id"]: r for r in _read_csv(b1 / "PHASE3B1_LEVEL_FAMILY_ANALYSIS.csv")}
    oem = load_best_oem(root / OEM_REGISTRY_REL, {r["manufacturer_code"] for r in scope})
    policy = {r["product_type_code"]: r for r in _read_csv(root / POLICY_REL)}

    freeze = owner_decision_freeze_rows()
    freeze_sha = owner_decision_sha256(freeze)
    if any(r["owner_status"] != "APPROVED" for r in freeze):
        raise ValueError("unapproved decisions")
    if len(freeze) != EXPECTED_DECISION_COUNT:
        raise ValueError("decision count")

    routing = [
        route_product(
            r,
            gen_by_id=gen,
            bore_by_id=bore,
            level_by_id=level,
            oem_by_code=oem,
        )
        for r in scope
    ]
    if len(routing) != 132:
        raise ValueError("routing length")
    if len({r["product_id"] for r in routing}) != 132:
        raise ValueError("routing duplicate")

    new_pts_used = {
        r["recommended_pt_code"]
        for r in routing
        if r["recommended_pt_action"] == "CREATE_NEW_PT_AND_ASSIGN"
    }
    # Update affected row counts on proposals
    new_pt_rows = []
    for code in sorted(new_pts_used):
        prop = NEW_PT_CATALOG[code]
        n = sum(1 for r in routing if r["recommended_pt_code"] == code)
        d = {
            "code": prop.code,
            "english_concept": prop.english_concept,
            "persian_canonical_title": prop.persian_title,
            "semantic_definition": prop.semantic_definition,
            "inclusion_rule": prop.inclusion_rule,
            "exclusion_rule": prop.exclusion_rule,
            "parent_category": prop.parent_category,
            "naming_profile": prop.naming_profile,
            "variant_policy_concept": prop.variant_policy_concept,
            "primary_variant_property": prop.primary_variant_property,
            "oem_evidence_basis": prop.oem_evidence_basis,
            "affected_rows": str(n),
            "decision_ids": prop.decision_ids,
        }
        new_pt_rows.append(d)

    props = property_definition_proposals()
    membership = [
        {
            "product_type_code": pt,
            "property_code": pcode,
            "membership_action": "CREATE",
            "decision_id": did,
            "status": "PROPOSED",
        }
        for pt, pcode, did in [
            ("LEVEL", "body_length", "D-LEVEL-01"),
            ("DIGITAL_LEVEL", "body_length", "D-DLEVEL-01"),
            ("INSIDE_SPRING_CALIPER", "body_length", "D-DIVIDER-01"),
            ("OUTSIDE_SPRING_CALIPER", "body_length", "D-DIVIDER-01"),
            ("SURFACE_PLATE", "plate_dimensions", "D-PLATE-01"),
        ]
    ]

    evidence = source_evidence_closure(oem)
    policy_delta = build_policy_delta(routing, policy)
    mutation_plan = build_mutation_plan(routing, new_pts_used)
    if any(r["entity_type"] == "Product.name" for r in mutation_plan):
        raise ValueError("Product.name in plan")

    post_states = []
    for r, scope_row in zip(routing, scope, strict=True):
        state = post_governance_state(r, scope_row["product_type_code"], scope_row["manufacturer_code"])
        post_states.append(
            {
                "product_id": r["product_id"],
                "manufacturer_code": r["manufacturer_code"],
                "current_pt_code": r["current_pt_code"],
                "recommended_pt_code": r["recommended_pt_code"],
                "recommended_pt_action": r["recommended_pt_action"],
                "post_governance_state": state,
                "decision_id": r["approved_decision_id"],
            }
        )
    state_counts = Counter(r["post_governance_state"] for r in post_states)
    if sum(state_counts.values()) != 132:
        raise ValueError("post state reconcile")

    # Wave 3C: existing 58 + rows that become READY_FOR_VARIANT_FACT from this wave
    # After 3B2, variant-fact ready is rare (need property+PT applied first).
    # Rows that will enter missing-variant-fact *after* future 3B3 PT/property apply:
    # residual GEN_CALIPER + BORE_GAUGE + LEVEL/DIGITAL with property path + spring calipers + new PTs with measurement_range
    enter_variant = []
    for r in post_states:
        # Projected next blocker after successful 3B3 governance apply for non-hold rows
        if r["post_governance_state"] in {
            "PT_APPLY_REQUIRED",
            "PROPERTY_APPLY_REQUIRED",
            "READY_FOR_POLICY_APPLY_ONLY",
        }:
            # After apply, most need variant facts (measurement_range or body_length or plate_dimensions)
            enter_variant.append(r["product_id"])
    # Deduped future total vs historical Wave 3C (outside Wave 3B)
    w3c = {
        "existing_wave3c_rows": EXISTING_WAVE3C_ROWS,
        "new_rows_entering_variant_fact_from_3b": len(enter_variant),
        "deduplicated_future_variant_fact_total": EXISTING_WAVE3C_ROWS + len(enter_variant),
        "product_ids_entering": sorted(enter_variant, key=int),
    }

    rehearsal = run_disposable_rehearsal(routing, mutation_plan)
    injections = run_failure_injections(routing, mutation_plan)
    if rehearsal["persistent_mutations"] != 0:
        raise ValueError("rehearsal leaked mutations")
    if any(not v["rollback_ok"] for v in injections.values()):
        raise ValueError("failure injection leak")

    # Live prestate from Phase 3B1 scope (read-only snapshot; optional live later)
    live_prestate = [
        {
            "product_id": r["product_id"],
            "manufacturer_code": r["manufacturer_code"],
            "current_product_type_code": r["product_type_code"],
            "current_name": r.get("historical_name", ""),
            "brand": "",
            "deleted_at": "",
            "kb_facts": "",
            "property_membership": "",
            "prestate_source": "phase3b1_scope_snapshot",
            "live_identity_drift": "not_fetched",
        }
        for r in scope
    ]

    phase3b1_inputs = {
        "PHASE3B1_SCOPE.csv": sha256_file(b1 / "PHASE3B1_SCOPE.csv"),
        "PHASE3B1_OWNER_DECISION_MATRIX.csv": sha256_file(
            b1 / "PHASE3B1_OWNER_DECISION_MATRIX.csv"
        ),
        "PHASE3B1_OWNER_DECISION_PACK.md": sha256_file(b1 / "PHASE3B1_OWNER_DECISION_PACK.md"),
        "PHASE3B1_SEMANTIC_HOMOGENEITY.csv": sha256_file(
            b1 / "PHASE3B1_SEMANTIC_HOMOGENEITY.csv"
        ),
        "PHASE3B1_GEN_CALIPER_SPLIT_ANALYSIS.csv": sha256_file(
            b1 / "PHASE3B1_GEN_CALIPER_SPLIT_ANALYSIS.csv"
        ),
        "PHASE3B1_BORE_GAUGE_ANALYSIS.csv": sha256_file(
            b1 / "PHASE3B1_BORE_GAUGE_ANALYSIS.csv"
        ),
        "PHASE3B1_LEVEL_FAMILY_ANALYSIS.csv": sha256_file(
            b1 / "PHASE3B1_LEVEL_FAMILY_ANALYSIS.csv"
        ),
        "PHASE3B1_PROPERTY_REQUIREMENTS.csv": sha256_file(
            b1 / "PHASE3B1_PROPERTY_REQUIREMENTS.csv"
        ),
        "PHASE3B1_POST_POLICY_BLOCKERS.csv": sha256_file(
            b1 / "PHASE3B1_POST_POLICY_BLOCKERS.csv"
        ),
        "PHASE3B1_REPORT.json": sha256_file(b1 / "PHASE3B1_REPORT.json"),
    }

    action_counts = Counter(r["recommended_pt_action"] for r in routing)
    delta_counts = Counter(r["action"] for r in policy_delta)

    return {
        "scope": scope,
        "freeze": freeze,
        "freeze_sha": freeze_sha,
        "routing": routing,
        "action_counts": dict(action_counts),
        "new_pt_rows": new_pt_rows,
        "props": props,
        "membership": membership,
        "evidence": evidence,
        "policy_delta": policy_delta,
        "delta_counts": dict(delta_counts),
        "mutation_plan": mutation_plan,
        "live_prestate": live_prestate,
        "post_states": post_states,
        "state_counts": dict(state_counts),
        "w3c": w3c,
        "rehearsal": rehearsal,
        "injections": injections,
        "phase3b1_inputs": phase3b1_inputs,
        "phase2f_intersection": 0,
        "policy_sha256": sha256_file(root / POLICY_REL),
        "candidates": candidates,
    }
