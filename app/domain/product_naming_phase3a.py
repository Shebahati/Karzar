"""Phase 3A — read-only HOLD resolution discovery (frozen Phase 2D universe).

No Product.name / ProductType / KB / policy / OEM mutation. Discovery only.
"""

from __future__ import annotations

import csv
import hashlib
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

PHASE2D_HOLDS_REL = "audit/product-naming-phase2d/PHASE2D_HOLDS.csv"
PHASE2D_CANDIDATES_REL = "audit/product-naming-phase2d/PHASE2D_RENAME_CANDIDATES_PROPOSED.csv"
PHASE2D_AUDIT_REL = "audit/product-naming-phase2d/PHASE2D_CANONICAL_NAME_AUDIT.csv"
PHASE2D_OEM_REL = "audit/product-naming-phase2d/PHASE2D_OEM_SEMANTIC_AUTHORITY.csv"
PHASE2D_OWNER_REL = "audit/product-naming-phase2d/PHASE2D_OWNER_FINAL_TITLE_REVIEW.csv"
PHASE2D_MANIFEST_REL = "audit/product-naming-phase2d/PHASE2D_CANDIDATE_FREEZE_MANIFEST.json"
PHASE2D_CANDIDATE_SHA256 = "25d586e371431cc371b6ce6432abba6c2da5b1f15102cac9ed187f78ef0052ff"
PHASE2D_HOLDS_SHA256 = "f195fc04270e3d8fd1c1fc9a243688006c0d248828c5d7d627ed30b28043cf64"
PHASE2D_EXPECTED_HOLD_ROWS = 1303
PHASE2D_EXPECTED_APPLIED_ROWS = 47
HOLD_CANARY_OWNER_TITLE = "2223-153"
HOLD_CANARY_MULTI_FUNCTION = "0312-TH50"

EXPECTED_REASON_COUNTS: dict[str, int] = {
    "HOLD_MISSING_PRODUCT_TYPE": 778,
    "HOLD_OEM_SEMANTIC_EVIDENCE_MISSING": 330,
    "HOLD_PRODUCT_TYPE_NAMING_POLICY": 101,
    "HOLD_MISSING_VARIANT_FACT": 58,
    "HOLD_VARIANT_POLICY_UNDEFINED": 31,
    "HOLD_PRODUCT_TYPE_AUTHORITY_CONFLICT": 3,
    "HOLD_OWNER_CANONICAL_TITLE_REVIEW": 1,
    "HOLD_MULTI_FUNCTION_IDENTITY_CONFLICT": 1,
}

REASON_TO_LANE: dict[str, str] = {
    "HOLD_MISSING_PRODUCT_TYPE": "A_MISSING_PRODUCT_TYPE",
    "HOLD_OEM_SEMANTIC_EVIDENCE_MISSING": "B_OEM_SEMANTIC_EVIDENCE",
    "HOLD_PRODUCT_TYPE_NAMING_POLICY": "C_NAMING_POLICY",
    "HOLD_VARIANT_POLICY_UNDEFINED": "D_VARIANT_POLICY",
    "HOLD_MISSING_VARIANT_FACT": "E_VARIANT_FACT",
    "HOLD_PRODUCT_TYPE_AUTHORITY_CONFLICT": "F_AUTHORITY_CONFLICT",
    "HOLD_OWNER_CANONICAL_TITLE_REVIEW": "G_OWNER_TITLE",
    "HOLD_MULTI_FUNCTION_IDENTITY_CONFLICT": "H_MULTI_FUNCTION",
}

FORBIDDEN_MUTATION_FLAGS = frozenset(
    {
        "--apply",
        "--mutate",
        "--write-db",
        "--commit",
        "--force",
        "--reclassify-live",
    }
)

OEM_REGISTRY_REL = (
    "docs/architecture/specs/product-naming-v1/INSIZE_OEM_PRODUCT_IDENTITY_REGISTRY.csv"
)
NAMING_POLICY_REL = (
    "docs/architecture/specs/product-naming-v1/PRODUCT_TYPE_CANONICAL_NAMING_POLICY.csv"
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reject_mutation_flags(argv: Sequence[str]) -> None:
    import sys

    for a in argv:
        if a in FORBIDDEN_MUTATION_FLAGS or any(
            a.startswith(f"{f}=") for f in FORBIDDEN_MUTATION_FLAGS
        ):
            print(f"ERROR: Phase 3A forbids mutation flag {a}", file=sys.stderr)
            raise SystemExit(2)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def normalize_brand_bucket(brand: str, *, current_name: str = "", brand_name: str = "") -> str:
    b = (brand or "").strip()
    if b:
        upper = b.upper()
        if "INSIZE" in upper or "اینسایز" in b:
            return "INSIZE"
        if "DASQUA" in upper or "داسکوا" in b:
            return "DASQUA"
        if "TERMA" in upper or "ترما" in b:
            return "TERMA"
        return "OTHER"
    text = f"{brand_name} {current_name}"
    upper = text.upper()
    if "INSIZE" in upper or "اینسایز" in text:
        return "INSIZE_INFERRED"
    if "DASQUA" in upper or "داسکوا" in text:
        return "DASQUA_INFERRED"
    if "TERMA" in upper or "ترما" in text:
        return "TERMA_INFERRED"
    return "OTHER_EMPTY"


def load_holds(path: Path) -> list[dict[str, str]]:
    digest = sha256_file(path)
    if digest != PHASE2D_HOLDS_SHA256:
        raise ValueError(f"PHASE2D_HOLDS.csv SHA256 mismatch: got {digest}")
    rows = _read_csv(path)
    if len(rows) != PHASE2D_EXPECTED_HOLD_ROWS:
        raise ValueError(f"HOLD rows {len(rows)} != {PHASE2D_EXPECTED_HOLD_ROWS}")
    ids = [r["product_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate product_id in HOLD universe")
    reason_key = "hold reason"
    for r in rows:
        if reason_key not in r:
            raise ValueError("missing hold reason column")
        r["_hold_reason"] = (r[reason_key] or "").strip()
        r["_dependency"] = (r.get("missing/ambiguous governance dependency") or "").strip()
        r["_remediation"] = (r.get("recommended next remediation") or "").strip()
    return rows


def load_candidates(path: Path) -> list[dict[str, str]]:
    rows = _read_csv(path)
    digest = sha256_file(path)
    if digest != PHASE2D_CANDIDATE_SHA256:
        raise ValueError(f"candidate SHA256 mismatch: got {digest}")
    if len(rows) != PHASE2D_EXPECTED_APPLIED_ROWS:
        raise ValueError(f"candidate rows {len(rows)} != {PHASE2D_EXPECTED_APPLIED_ROWS}")
    return rows


def assert_no_applied_intersection(holds: list[dict[str, str]], candidates: list[dict[str, str]]) -> None:
    hold_ids = {r["product_id"] for r in holds}
    cand_ids = {r["product_id"] for r in candidates}
    inter = hold_ids & cand_ids
    if inter:
        raise ValueError(f"Phase3A HOLD intersects Phase2F applied cohort: {sorted(inter)[:10]}")


def reconcile_reason_counts(holds: list[dict[str, str]]) -> tuple[dict[str, int], list[str]]:
    counts = Counter(r["_hold_reason"] for r in holds)
    errors: list[str] = []
    for reason, expected in EXPECTED_REASON_COUNTS.items():
        actual = counts.get(reason, 0)
        if actual != expected:
            errors.append(f"{reason}: got {actual} expected {expected}")
    unexpected = set(counts) - set(EXPECTED_REASON_COUNTS)
    if unexpected:
        errors.append(f"unexpected reasons: {sorted(unexpected)}")
    if sum(counts.values()) != PHASE2D_EXPECTED_HOLD_ROWS:
        errors.append(f"total {sum(counts.values())} != {PHASE2D_EXPECTED_HOLD_ROWS}")
    return dict(counts), errors


def classify_oem_sublane(dependency: str, occurrence_type: str, evidence_status: str) -> str:
    dep = (dependency or "").strip()
    occ = (occurrence_type or "").strip().lower()
    if dep == "no_identity_registry_entry" or (not dep and not occ):
        return "B1_NO_IDENTITY_REGISTRY_ENTRY"
    if dep == "accessory_only_occurrence" or occ == "accessory_only":
        return "B2_ACCESSORY_ONLY_OCCURRENCE"
    if dep.startswith("ambiguous_headings") or occ in {"ambiguous", "conflicting_headings"}:
        return "B3_AMBIGUOUS_OCCURRENCE"
    if dep == "oem_heading_not_in_canonical_identity_policy":
        return "B4_EXACT_OCCURRENCE_BUT_HEADING_NOT_GOVERNED"
    if dep == "no_primary_product_occurrence":
        return "B5_OEM_SOURCE_NOT_EXTRACTED"
    if evidence_status in {"NOT_FOUND", ""} and dep:
        return "B6_CODE_NOT_FOUND" if "not_found" in dep.lower() else "B7_OTHER"
    return "B7_OTHER"


def classify_naming_policy_sublane(dependency: str) -> str:
    dep = (dependency or "").strip()
    if dep == "synonym_or_slash_label":
        return "C1_SYNONYM_OR_SLASH_LABEL"
    if dep == "generic_product_type_label":
        return "C2_GENERIC_LABEL_TOO_BROAD"
    if "qualifier" in dep:
        return "C3_REQUIRED_IDENTITY_QUALIFIER_MISSING"
    if "persian" in dep or "canonical" in dep:
        return "C4_PERSIAN_CANONICAL_LABEL_MISSING"
    if "incomplete" in dep:
        return "C5_EXISTING_POLICY_ROW_INCOMPLETE"
    return "C6_OTHER"


def classify_missing_pt_sublane(
    brand: str,
    registry_row: Mapping[str, str] | None,
) -> str:
    if brand in {"DASQUA", "TERMA", "OTHER", "OTHER_EMPTY"}:
        # No INSIZE OEM registry authority for non-INSIZE brands.
        if brand in {"DASQUA", "TERMA"}:
            return "A6_NO_AUTHORITATIVE_SOURCE"
        return "A6_NO_AUTHORITATIVE_SOURCE"
    if registry_row is None:
        return "A6_NO_AUTHORITATIVE_SOURCE"
    occ = (registry_row.get("product_occurrence_class") or "").strip().upper()
    es = (registry_row.get("evidence_status") or "").strip().upper()
    heading = (registry_row.get("OEM_product_heading") or "").strip()
    if es == "EXACT_PRODUCT_IDENTITY" and occ in {"PRODUCT_ROW", "PRODUCT_HEADING_CONTEXT"}:
        return "A1_EXACT_OEM_PRODUCT_FAMILY" if heading else "A2_EXACT_MANUFACTURER_LISTING"
    if occ == "PRODUCT_ROW":
        return "A2_EXACT_MANUFACTURER_LISTING"
    if occ == "PRODUCT_HEADING_CONTEXT" and heading:
        return "A1_EXACT_OEM_PRODUCT_FAMILY"
    if occ.lower() == "accessory_only":
        return "A5_AMBIGUOUS_PRODUCT_TYPE"
    if es == "AMBIGUOUS" or "CONFLICT" in occ:
        return "A5_AMBIGUOUS_PRODUCT_TYPE"
    if occ in {"UNKNOWN", ""} and es == "INSUFFICIENT":
        return "A4_CURRENT_NAME_ONLY_INSUFFICIENT"
    return "A3_EXISTING_CATEGORY_ONLY_INSUFFICIENT"


def classify_variant_fact_sublane(
    audit: Mapping[str, str],
) -> str:
    fact_id = (audit.get("variant_fact_id") or "").strip()
    published = (audit.get("variant_fact_published") or "").strip().lower()
    raw = (audit.get("variant_raw_value") or "").strip()
    if fact_id and published in {"false", "0", "no", ""}:
        return "E1_KB_FACT_EXISTS_UNPUBLISHED"
    if fact_id and published in {"true", "1", "yes"}:
        # Should not be HOLD_MISSING_VARIANT_FACT historically; treat as unpublished gate miss.
        return "E1_KB_FACT_EXISTS_UNPUBLISHED"
    if raw:
        return "E3_LEGACY_SPEC_REQUIRES_EVIDENCE"
    name = audit.get("current_name") or ""
    if re.search(r"\d", name):
        return "E4_ONLY_CURRENT_NAME_HINT"
    return "E5_NO_VALUE_FOUND"


def next_blocker_after_primary(
    reason: str,
    audit: Mapping[str, str],
    oem: Mapping[str, str] | None,
) -> str:
    """Simulate the subsequent blocker if the historical primary HOLD were cleared."""
    title_status = (audit.get("canonical_title_status") or "").strip().upper()
    variant_policy = (audit.get("variant_policy") or "").strip().upper()
    variant_policy_status = (audit.get("variant_policy_status") or "").strip().upper()
    fact_published = (audit.get("variant_fact_published") or "").strip().lower()
    fact_id = (audit.get("variant_fact_id") or "").strip()

    def naming_blocked() -> bool:
        return title_status in {"", "HOLD", "UNAPPROVED", "GENERIC", "SYNONYM"} or (
            audit.get("policy_review_status") or ""
        ).upper() in {"HOLD", "BLOCKED"}

    def variant_policy_blocked() -> bool:
        return "UNDEFINED" in variant_policy or "UNDEFINED" in variant_policy_status or not variant_policy

    def variant_fact_blocked() -> bool:
        if "NOT_REQUIRED" in variant_policy:
            return False
        if "REQUIRED" in variant_policy or (audit.get("variant_property_code") or "").strip():
            return not (fact_id and fact_published in {"true", "1", "yes"})
        return False

    if reason == "HOLD_MISSING_PRODUCT_TYPE":
        # After PT assignment: OEM identity, naming policy, then variant chain.
        if (oem or {}).get("semantic_match_status") in {
            "OEM_EVIDENCE_INSUFFICIENT",
            "OEM_EVIDENCE_AMBIGUOUS",
            "",
        } and (audit.get("brand_name") or "").upper().find("INSIZE") >= 0:
            # INSIZE missing-PT rows typically lack governed OEM semantic pass.
            return "OEM_SEMANTIC_OR_NAMING_POLICY"
        return "NAMING_POLICY_OR_VARIANT_POLICY"
    if reason == "HOLD_OEM_SEMANTIC_EVIDENCE_MISSING":
        if naming_blocked():
            return "PRODUCT_TYPE_NAMING_POLICY"
        if variant_policy_blocked():
            return "VARIANT_POLICY_UNDEFINED"
        if variant_fact_blocked():
            return "MISSING_VARIANT_FACT"
        return "NONE_DIRECT_UNLOCK_LIKELY"
    if reason == "HOLD_PRODUCT_TYPE_NAMING_POLICY":
        if variant_policy_blocked():
            return "VARIANT_POLICY_UNDEFINED"
        if variant_fact_blocked():
            return "MISSING_VARIANT_FACT"
        return "NONE_DIRECT_UNLOCK_LIKELY"
    if reason == "HOLD_VARIANT_POLICY_UNDEFINED":
        if variant_fact_blocked() or not (audit.get("variant_property_code") or "").strip():
            return "MISSING_VARIANT_FACT_AFTER_POLICY"
        return "NONE_DIRECT_UNLOCK_LIKELY"
    if reason == "HOLD_MISSING_VARIANT_FACT":
        return "NONE_DIRECT_UNLOCK_LIKELY"
    if reason in {
        "HOLD_PRODUCT_TYPE_AUTHORITY_CONFLICT",
        "HOLD_OWNER_CANONICAL_TITLE_REVIEW",
        "HOLD_MULTI_FUNCTION_IDENTITY_CONFLICT",
    }:
        return "OWNER_SEMANTIC_THEN_RECLASSIFY"
    return "UNRESOLVED"


def projected_unlock_state(
    reason: str,
    next_blocker: str,
    *,
    sublane: str,
) -> str:
    if reason in {
        "HOLD_PRODUCT_TYPE_AUTHORITY_CONFLICT",
        "HOLD_OWNER_CANONICAL_TITLE_REVIEW",
        "HOLD_MULTI_FUNCTION_IDENTITY_CONFLICT",
    }:
        return "OWNER_DECISION_REQUIRED"
    if reason == "HOLD_PRODUCT_TYPE_NAMING_POLICY":
        if next_blocker == "NONE_DIRECT_UNLOCK_LIKELY":
            return "DIRECT_UNLOCK"
        if next_blocker == "VARIANT_POLICY_UNDEFINED":
            return "OWNER_DECISION_REQUIRED"
        if next_blocker == "MISSING_VARIANT_FACT":
            return "TWO_STEP_UNLOCK"
        return "TWO_STEP_UNLOCK"
    if reason == "HOLD_VARIANT_POLICY_UNDEFINED":
        return "OWNER_DECISION_REQUIRED"
    if reason == "HOLD_MISSING_VARIANT_FACT":
        if sublane in {"E1_KB_FACT_EXISTS_UNPUBLISHED", "E2_OEM_EXTRACTABLE"}:
            return "DIRECT_UNLOCK"
        if sublane == "E3_LEGACY_SPEC_REQUIRES_EVIDENCE":
            return "TWO_STEP_UNLOCK"
        if sublane == "E4_ONLY_CURRENT_NAME_HINT":
            return "SOURCE_EVIDENCE_REQUIRED"
        return "SOURCE_EVIDENCE_REQUIRED"
    if reason == "HOLD_OEM_SEMANTIC_EVIDENCE_MISSING":
        if sublane in {"B4_EXACT_OCCURRENCE_BUT_HEADING_NOT_GOVERNED"}:
            return "OWNER_DECISION_REQUIRED"
        if sublane in {"B2_ACCESSORY_ONLY_OCCURRENCE", "B1_NO_IDENTITY_REGISTRY_ENTRY", "B5_OEM_SOURCE_NOT_EXTRACTED"}:
            return "SOURCE_EVIDENCE_REQUIRED"
        if sublane == "B3_AMBIGUOUS_OCCURRENCE":
            return "OWNER_DECISION_REQUIRED"
        return "SOURCE_EVIDENCE_REQUIRED"
    if reason == "HOLD_MISSING_PRODUCT_TYPE":
        if sublane in {"A1_EXACT_OEM_PRODUCT_FAMILY", "A2_EXACT_MANUFACTURER_LISTING"}:
            return "TWO_STEP_UNLOCK"
        if sublane in {"A5_AMBIGUOUS_PRODUCT_TYPE"}:
            return "OWNER_DECISION_REQUIRED"
        if sublane == "A6_NO_AUTHORITATIVE_SOURCE":
            return "SOURCE_EVIDENCE_REQUIRED"
        return "MULTI_STEP_UNLOCK"
    return "UNRESOLVED"


def assign_wave(reason: str, brand_bucket: str) -> str:
    if reason == "HOLD_PRODUCT_TYPE_NAMING_POLICY":
        return "WAVE_3B_GOVERNANCE_QUICK_WINS"
    if reason == "HOLD_VARIANT_POLICY_UNDEFINED":
        return "WAVE_3B_GOVERNANCE_QUICK_WINS"
    if reason == "HOLD_MISSING_VARIANT_FACT":
        return "WAVE_3C_VARIANT_FACTS"
    if reason == "HOLD_OEM_SEMANTIC_EVIDENCE_MISSING":
        return "WAVE_3D_INSIZE_OEM_EVIDENCE"
    if reason == "HOLD_MISSING_PRODUCT_TYPE" and brand_bucket.startswith("INSIZE"):
        return "WAVE_3E_INSIZE_MISSING_PT"
    if reason == "HOLD_MISSING_PRODUCT_TYPE" and brand_bucket.startswith("DASQUA"):
        return "WAVE_3F_DASQUA_PT"
    if reason == "HOLD_MISSING_PRODUCT_TYPE" and brand_bucket.startswith("TERMA"):
        return "WAVE_3G_TERMA_PT"
    if reason in {
        "HOLD_PRODUCT_TYPE_AUTHORITY_CONFLICT",
        "HOLD_OWNER_CANONICAL_TITLE_REVIEW",
        "HOLD_MULTI_FUNCTION_IDENTITY_CONFLICT",
    }:
        return "WAVE_3H_MANUAL_EXCEPTIONS"
    if reason == "HOLD_MISSING_PRODUCT_TYPE":
        return "WAVE_3H_MANUAL_EXCEPTIONS"
    return "WAVE_3H_MANUAL_EXCEPTIONS"


def automation_confidence(projected: str, reason: str) -> str:
    if projected == "DIRECT_UNLOCK" and reason == "HOLD_PRODUCT_TYPE_NAMING_POLICY":
        return "P0"
    if projected == "DIRECT_UNLOCK":
        return "P1"
    if projected == "TWO_STEP_UNLOCK":
        return "P1"
    if projected == "MULTI_STEP_UNLOCK":
        return "P2"
    if projected in {"OWNER_DECISION_REQUIRED", "SOURCE_EVIDENCE_REQUIRED"}:
        return "P3"
    return "P3"


def live_drift_flags(
    historical: Mapping[str, str],
    live: Mapping[str, str] | None,
) -> list[str]:
    if live is None:
        return ["MISSING_LIVE"]
    flags: list[str] = []
    if (live.get("deleted_at") or "").strip():
        flags.append("DELETED")
    if (live.get("name") or "").strip() != (historical.get("current_name") or "").strip():
        flags.append("NAME_DRIFT")
    if (live.get("sku") or "").strip() != (historical.get("sku") or "").strip():
        flags.append("SKU_DRIFT")
    if (live.get("manufacturer_code") or "").strip() != (
        historical.get("manufacturer_code") or ""
    ).strip():
        flags.append("MANUFACTURER_CODE_DRIFT")
    hist_pt = (historical.get("product_type_id") or "").strip()
    live_pt = (live.get("product_type_id") or "").strip()
    if hist_pt and live_pt and hist_pt != live_pt:
        flags.append("PRODUCT_TYPE_DRIFT")
    hist_brand = (historical.get("brand_id") or "").strip()
    live_brand = (live.get("brand_id") or "").strip()
    if hist_brand and live_brand and hist_brand != live_brand:
        flags.append("BRAND_DRIFT")
    return flags or ["NO_DRIFT"]


@dataclass
class RootCauseRow:
    product_id: str
    manufacturer_code: str
    brand_id: str
    brand_name: str
    brand_bucket: str
    historical_hold_reason: str
    current_name: str
    historical_name: str
    current_product_type_id: str
    current_product_type_code: str
    OEM_evidence_status: str
    OEM_occurrence_type: str
    OEM_heading: str
    canonical_title_status: str
    variant_policy_status: str
    variant_property: str
    variant_fact_status: str
    live_identity_drift: str
    primary_blocker: str
    secondary_blockers: str
    next_blocker_after_primary_fix: str
    resolution_lane: str
    resolution_sublane: str
    projected_unlock_state: str
    automation_confidence: str
    owner_decision_required: str
    source_evidence_required: str
    recommended_next_action: str
    future_mutation_type: str
    wave: str
    dependency: str
    name_quality_flags: str = ""


def build_root_cause_matrix(
    *,
    holds: list[dict[str, str]],
    audit_by_id: Mapping[str, dict[str, str]],
    oem_by_id: Mapping[str, dict[str, str]],
    registry_by_code: Mapping[str, dict[str, str]],
    live_by_id: Mapping[str, dict[str, str]] | None = None,
) -> list[RootCauseRow]:
    out: list[RootCauseRow] = []
    for hold in holds:
        pid = hold["product_id"]
        audit = audit_by_id.get(pid, {})
        oem = oem_by_id.get(pid)
        reason = hold["_hold_reason"]
        brand_bucket = normalize_brand_bucket(
            hold.get("brand", ""),
            current_name=hold.get("current_name", ""),
            brand_name=audit.get("brand_name", ""),
        )
        lane = REASON_TO_LANE[reason]
        dependency = hold["_dependency"]
        if reason == "HOLD_MISSING_PRODUCT_TYPE":
            sublane = classify_missing_pt_sublane(
                brand_bucket.replace("_INFERRED", ""),
                registry_by_code.get(hold["manufacturer_code"]),
            )
        elif reason == "HOLD_OEM_SEMANTIC_EVIDENCE_MISSING":
            sublane = classify_oem_sublane(
                dependency,
                (oem or {}).get("occurrence_type", ""),
                (oem or {}).get("evidence_status", ""),
            )
        elif reason == "HOLD_PRODUCT_TYPE_NAMING_POLICY":
            sublane = classify_naming_policy_sublane(dependency)
        elif reason == "HOLD_MISSING_VARIANT_FACT":
            sublane = classify_variant_fact_sublane(audit)
            # Promote to OEM extractable when INSIZE registry has exact identity.
            reg = registry_by_code.get(hold["manufacturer_code"])
            if sublane == "E5_NO_VALUE_FOUND" and reg and reg.get("evidence_status") == "EXACT_PRODUCT_IDENTITY":
                sublane = "E2_OEM_EXTRACTABLE"
        elif reason == "HOLD_VARIANT_POLICY_UNDEFINED":
            sublane = dependency or "D_OWNER_POLICY_PENDING"
        elif reason == "HOLD_PRODUCT_TYPE_AUTHORITY_CONFLICT":
            sublane = "F_PT_CONFLICT"
        elif reason == "HOLD_OWNER_CANONICAL_TITLE_REVIEW":
            sublane = "G_OWNER_TITLE"
        else:
            sublane = "H_MULTI_FUNCTION"

        next_blocker = next_blocker_after_primary(reason, audit, oem)
        projected = projected_unlock_state(reason, next_blocker, sublane=sublane)
        wave = assign_wave(reason, brand_bucket)
        live = (live_by_id or {}).get(pid)
        hist_for_drift = {
            "current_name": hold.get("current_name", ""),
            "sku": hold.get("sku", ""),
            "manufacturer_code": hold.get("manufacturer_code", ""),
            "product_type_id": audit.get("product_type_id", ""),
            "brand_id": audit.get("brand_id", ""),
        }
        drift = live_drift_flags(hist_for_drift, live) if live_by_id is not None else ["LIVE_NOT_QUERIED"]

        owner_req = projected == "OWNER_DECISION_REQUIRED" or reason in {
            "HOLD_VARIANT_POLICY_UNDEFINED",
            "HOLD_PRODUCT_TYPE_AUTHORITY_CONFLICT",
            "HOLD_OWNER_CANONICAL_TITLE_REVIEW",
            "HOLD_MULTI_FUNCTION_IDENTITY_CONFLICT",
        }
        source_req = projected == "SOURCE_EVIDENCE_REQUIRED" or reason in {
            "HOLD_OEM_SEMANTIC_EVIDENCE_MISSING",
            "HOLD_MISSING_PRODUCT_TYPE",
        }

        secondary: list[str] = []
        if next_blocker and next_blocker != "NONE_DIRECT_UNLOCK_LIKELY":
            secondary.append(next_blocker)

        fact_status = "MISSING"
        if (audit.get("variant_fact_id") or "").strip():
            fact_status = (
                "PUBLISHED"
                if (audit.get("variant_fact_published") or "").lower() in {"true", "1", "yes"}
                else "UNPUBLISHED"
            )
        elif reason != "HOLD_MISSING_VARIANT_FACT" and "NOT_REQUIRED" in (
            audit.get("variant_policy") or ""
        ).upper():
            fact_status = "NOT_REQUIRED"

        out.append(
            RootCauseRow(
                product_id=pid,
                manufacturer_code=hold.get("manufacturer_code", ""),
                brand_id=audit.get("brand_id", ""),
                brand_name=audit.get("brand_name", "") or hold.get("brand", ""),
                brand_bucket=brand_bucket,
                historical_hold_reason=reason,
                current_name=(live or {}).get("name", "") if live else hold.get("current_name", ""),
                historical_name=hold.get("current_name", ""),
                current_product_type_id=audit.get("product_type_id", ""),
                current_product_type_code=audit.get("product_type_code", ""),
                OEM_evidence_status=(oem or {}).get("evidence_status", ""),
                OEM_occurrence_type=(oem or {}).get("occurrence_type", ""),
                OEM_heading=(oem or {}).get("oem_product_heading", ""),
                canonical_title_status=audit.get("canonical_title_status", ""),
                variant_policy_status=audit.get("variant_policy_status", "")
                or audit.get("variant_policy", ""),
                variant_property=audit.get("variant_property_code", ""),
                variant_fact_status=fact_status,
                live_identity_drift="|".join(drift),
                primary_blocker=reason,
                secondary_blockers="|".join(secondary),
                next_blocker_after_primary_fix=next_blocker,
                resolution_lane=lane,
                resolution_sublane=sublane,
                projected_unlock_state=projected,
                automation_confidence=automation_confidence(projected, reason),
                owner_decision_required="yes" if owner_req else "no",
                source_evidence_required="yes" if source_req else "no",
                recommended_next_action=hold.get("_remediation", ""),
                future_mutation_type=_future_mutation_type(reason),
                wave=wave,
                dependency=dependency,
                name_quality_flags=audit.get("name_quality_flags", ""),
            )
        )
    out.sort(key=lambda r: int(r.product_id))
    return out


def _future_mutation_type(reason: str) -> str:
    return {
        "HOLD_MISSING_PRODUCT_TYPE": "PRODUCT_TYPE_ASSIGNMENT",
        "HOLD_OEM_SEMANTIC_EVIDENCE_MISSING": "OEM_EVIDENCE_THEN_RECLASSIFY",
        "HOLD_PRODUCT_TYPE_NAMING_POLICY": "NAMING_POLICY_GOVERNANCE",
        "HOLD_VARIANT_POLICY_UNDEFINED": "VARIANT_POLICY_GOVERNANCE",
        "HOLD_MISSING_VARIANT_FACT": "KB_VARIANT_FACT_PUBLICATION",
        "HOLD_PRODUCT_TYPE_AUTHORITY_CONFLICT": "PRODUCT_TYPE_CORRECTION",
        "HOLD_OWNER_CANONICAL_TITLE_REVIEW": "OWNER_TITLE_POLICY",
        "HOLD_MULTI_FUNCTION_IDENTITY_CONFLICT": "OWNER_MULTI_FUNCTION_POLICY",
    }.get(reason, "UNKNOWN")


def assert_matrix_invariants(rows: list[RootCauseRow]) -> list[str]:
    errors: list[str] = []
    if len(rows) != PHASE2D_EXPECTED_HOLD_ROWS:
        errors.append(f"matrix rows {len(rows)} != {PHASE2D_EXPECTED_HOLD_ROWS}")
    ids = [r.product_id for r in rows]
    if len(ids) != len(set(ids)):
        errors.append("duplicate product_id in matrix")
    for r in rows:
        if not r.primary_blocker:
            errors.append(f"{r.product_id}: missing primary_blocker")
        if not r.resolution_lane:
            errors.append(f"{r.product_id}: missing resolution_lane")
        if not r.wave:
            errors.append(f"{r.product_id}: missing wave")
    # one wave per product already; check no product in multiple waves is N/A
    wave_products: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        wave_products[r.wave].add(r.product_id)
    for a, set_a in wave_products.items():
        for b, set_b in wave_products.items():
            if a >= b:
                continue
            inter = set_a & set_b
            if inter:
                errors.append(f"wave overlap {a}/{b}: {sorted(inter)[:5]}")
    projected = Counter(r.projected_unlock_state for r in rows)
    if sum(projected.values()) != PHASE2D_EXPECTED_HOLD_ROWS:
        errors.append("projected unlock categories do not sum to 1303")
    # canaries
    owner = [r for r in rows if r.manufacturer_code == HOLD_CANARY_OWNER_TITLE]
    multi = [r for r in rows if r.manufacturer_code == HOLD_CANARY_MULTI_FUNCTION]
    if len(owner) != 1 or owner[0].historical_hold_reason != "HOLD_OWNER_CANONICAL_TITLE_REVIEW":
        errors.append("2223-153 owner-title canary failed")
    if len(multi) != 1 or multi[0].historical_hold_reason != "HOLD_MULTI_FUNCTION_IDENTITY_CONFLICT":
        errors.append("0312-TH50 multi-function canary failed")
    # DASQUA/TERMA must not get INSIZE OEM A1/A2 from INSIZE registry alone incorrectly —
    # they should be A6 when missing PT.
    for r in rows:
        if r.historical_hold_reason == "HOLD_MISSING_PRODUCT_TYPE" and r.brand_bucket.startswith(
            ("DASQUA", "TERMA")
        ):
            if r.resolution_sublane in {"A1_EXACT_OEM_PRODUCT_FAMILY", "A2_EXACT_MANUFACTURER_LISTING"}:
                errors.append(f"{r.product_id}: non-INSIZE assigned INSIZE OEM PT sublane")
    return errors


def prioritize_score(wave: str, count: int, owner_heavy: bool, source_heavy: bool) -> str:
    if wave == "WAVE_3B_GOVERNANCE_QUICK_WINS" and not source_heavy:
        return "P0"
    if wave == "WAVE_3C_VARIANT_FACTS":
        return "P1"
    if wave == "WAVE_3D_INSIZE_OEM_EVIDENCE":
        return "P2"
    if wave in {"WAVE_3E_INSIZE_MISSING_PT"}:
        return "P2"
    if wave in {"WAVE_3F_DASQUA_PT", "WAVE_3G_TERMA_PT"}:
        return "P2"
    if owner_heavy or wave == "WAVE_3H_MANUAL_EXCEPTIONS":
        return "P3"
    return "P2"


def family_cluster_key(row: RootCauseRow) -> str:
    if row.historical_hold_reason == "HOLD_PRODUCT_TYPE_NAMING_POLICY":
        return f"naming_policy:{row.current_product_type_code or 'UNKNOWN'}"
    if row.historical_hold_reason == "HOLD_VARIANT_POLICY_UNDEFINED":
        return f"variant_policy:{row.dependency or row.current_product_type_code}"
    if row.historical_hold_reason == "HOLD_MISSING_VARIANT_FACT":
        return f"variant_fact:{row.current_product_type_code}:{row.variant_property or 'UNKNOWN'}"
    if row.historical_hold_reason == "HOLD_OEM_SEMANTIC_EVIDENCE_MISSING":
        return f"oem:{row.resolution_sublane}:{row.OEM_heading or row.dependency or 'none'}"
    if row.historical_hold_reason == "HOLD_MISSING_PRODUCT_TYPE":
        prefix = (row.manufacturer_code or "").split("-")[0]
        return f"missing_pt:{row.brand_bucket}:{row.resolution_sublane}:prefix:{prefix}"
    return f"exception:{row.historical_hold_reason}:{row.manufacturer_code}"


OWNER_TITLE_OPTIONS = [
    {
        "option_id": "G1",
        "canonical_title_fa": "پرگار نشان‌گر داخلی با نوک‌های قابل تعویض",
        "tradeoff": "Closest to OEM heading; longer retail title; preserves interchangeable-points identity.",
    },
    {
        "option_id": "G2",
        "canonical_title_fa": "پرگار نشان‌گر داخلی",
        "tradeoff": "Shorter governed INDICATING_CALIPER label; drops interchangeable-points qualifier.",
    },
    {
        "option_id": "G3",
        "canonical_title_fa": "پرگار ساعتی داخل‌سنج",
        "tradeoff": "Matches common Persian market wording; weaker OEM-literal fidelity.",
    },
]

MULTI_FUNCTION_OPTIONS = [
    {
        "option_id": "H1",
        "proposal": "Keep MOISTURE_METER + require temperature qualifier in canonical title",
        "tradeoff": "Retains current PT; forces dual-function title governance.",
    },
    {
        "option_id": "H2",
        "proposal": "Introduce/select TEMPERATURE_HUMIDITY_METER Product Type",
        "tradeoff": "Cleaner identity; requires PT taxonomy change.",
    },
    {
        "option_id": "H3",
        "proposal": "Primary moisture PT + secondary temperature as non-title attribute",
        "tradeoff": "Avoids title bloat; may under-represent OEM dual function in name.",
    },
]
