"""Phase 2D — INSIZE exact OEM product identity + canonical title authority."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.domain.product_naming_phase2d import Phase2DAuditRow
from app.domain.product_naming_phase2d_oem_extract import (
    INSIZE_108A_SHA256,
    INSIZE_108B_SHA256,
    OemProductIdentity,
    load_identity_registry,
)
from app.domain.product_naming_phase2d_oem_policy import (
    OemCanonicalPolicyRow,
    default_oem_canonical_policy,
    lookup_policy,
    normalize_oem_heading,
)

OEM_SEMANTIC_STATUSES = frozenset(
    {
        "OEM_SEMANTIC_MATCH",
        "OEM_SEMANTIC_BROADER_BUT_ACCEPTABLE",
        "OEM_PRODUCT_TYPE_CONFLICT",
        "OEM_CANONICAL_TITLE_CONFLICT",
        "OEM_MULTI_FUNCTION_TITLE_CONFLICT",
        "OEM_EVIDENCE_INSUFFICIENT",
        "OEM_EVIDENCE_AMBIGUOUS",
    }
)

TITLE_VERDICTS = frozenset(
    {
        "OEM_TITLE_EXACT",
        "OEM_TITLE_BROADER_BUT_SUFFICIENT",
        "OEM_TITLE_REQUIRES_QUALIFIER",
        "OEM_TITLE_CONFLICT",
        "OEM_TITLE_EVIDENCE_INSUFFICIENT",
    }
)

READY_TITLE_VERDICTS = frozenset({"OEM_TITLE_EXACT", "OEM_TITLE_BROADER_BUT_SUFFICIENT"})
READY_PT_STATUSES = frozenset({"OEM_SEMANTIC_MATCH", "OEM_SEMANTIC_BROADER_BUT_ACCEPTABLE"})


@dataclass(frozen=True)
class OemEvaluation:
    semantic_match_status: str
    semantic_conflict_reason: str
    hold_terminal: str
    recommended_product_type_code: str
    recommended_canonical_title_fa: str
    canonical_title_verdict: str
    canonical_title_reason: str
    title_qualifier: str
    occurrence_type: str
    occurrence_authoritative: str
    evidence_status: str


def _evaluate_product_type(
    *,
    product_type_code: str,
    identity: OemProductIdentity,
    policy: OemCanonicalPolicyRow,
) -> tuple[str, str, str]:
    code_pt = (product_type_code or "").strip()
    allowed = policy.allowed_product_type_code
    if code_pt == allowed:
        return (
            "OEM_SEMANTIC_MATCH",
            "oem_product_type_matches_governed_policy",
            code_pt,
        )
    norm_heading = normalize_oem_heading(identity.oem_product_heading)
    if (
        code_pt == "OUTSIDE_MICROMETER"
        and allowed == "OUTSIDE_MICROMETER"
        and "MICROMETER" in norm_heading
    ):
        return (
            "OEM_SEMANTIC_BROADER_BUT_ACCEPTABLE",
            "digital_oem_subtype_maps_to_governed_product_type",
            code_pt,
        )
    if code_pt != allowed:
        return (
            "OEM_PRODUCT_TYPE_CONFLICT",
            f"persisted_{code_pt}_policy_requires_{allowed}",
            allowed,
        )
    return ("OEM_SEMANTIC_MATCH", "match", code_pt)


def _evaluate_canonical_title(
    *,
    canonical_title_fa: str,
    identity: OemProductIdentity,
    policy: OemCanonicalPolicyRow,
) -> tuple[str, str, str]:
    title = (canonical_title_fa or "").strip()
    governed = policy.canonical_title_fa
    qualifier = (policy.required_title_qualifier or "").strip()

    if identity.oem_subtype_or_qualifier == "temperature_humidity_meter":
        if "رطوبت" in title and "دما" not in title and "حرارت" not in title:
            return (
                "OEM_TITLE_CONFLICT",
                "multi_function_temperature_humidity_title_drops_temperature",
                "دما و رطوبت‌سنج",
            )

    if qualifier:
        if qualifier not in title:
            return (
                "OEM_TITLE_REQUIRES_QUALIFIER",
                f"oem_subtype_requires_qualifier:{qualifier}",
                qualifier,
            )
        if title == governed or governed in title:
            return ("OEM_TITLE_EXACT", "title_includes_governed_qualifier", qualifier)
        return ("OEM_TITLE_EXACT", "title_with_qualifier", qualifier)

    if title == governed:
        return ("OEM_TITLE_EXACT", "canonical_title_matches_policy", "")

    if policy.semantic_scope == "broader_title_acceptable" and title == governed:
        return ("OEM_TITLE_BROADER_BUT_SUFFICIENT", "policy_broader_title", "")

    if title == governed or (governed and title.startswith(governed)):
        return ("OEM_TITLE_BROADER_BUT_SUFFICIENT", "title_covers_governed_base", "")

    if title != governed:
        return (
            "OEM_TITLE_CONFLICT",
            f"canonical_title_{title}_policy_requires_{governed}",
            "",
        )
    return ("OEM_TITLE_EXACT", "match", "")


def evaluate_oem_semantic(
    *,
    product_type_code: str,
    canonical_title_fa: str,
    identity: OemProductIdentity | None,
    policies: Mapping[str, OemCanonicalPolicyRow] | None = None,
) -> OemEvaluation:
    pol_map = policies if policies is not None else default_oem_canonical_policy()
    if identity is None:
        return OemEvaluation(
            semantic_match_status="OEM_EVIDENCE_INSUFFICIENT",
            semantic_conflict_reason="no_identity_registry_entry",
            hold_terminal="HOLD_OEM_SEMANTIC_EVIDENCE_MISSING",
            recommended_product_type_code="",
            recommended_canonical_title_fa="",
            canonical_title_verdict="OEM_TITLE_EVIDENCE_INSUFFICIENT",
            canonical_title_reason="no_identity_registry_entry",
            title_qualifier="",
            occurrence_type="",
            occurrence_authoritative="no",
            evidence_status="INSUFFICIENT",
        )

    occ_type = identity.product_occurrence_class
    auth_yes = identity.evidence_status == "EXACT_PRODUCT_IDENTITY" and occ_type in (
        "PRODUCT_ROW",
        "PRODUCT_HEADING_CONTEXT",
    )

    if identity.evidence_status == "AMBIGUOUS":
        return OemEvaluation(
            semantic_match_status="OEM_EVIDENCE_AMBIGUOUS",
            semantic_conflict_reason=identity.evidence_context,
            hold_terminal="HOLD_OEM_SEMANTIC_EVIDENCE_MISSING",
            recommended_product_type_code="",
            recommended_canonical_title_fa="",
            canonical_title_verdict="OEM_TITLE_EVIDENCE_INSUFFICIENT",
            canonical_title_reason="ambiguous_product_occurrence",
            title_qualifier="",
            occurrence_type=occ_type,
            occurrence_authoritative="no",
            evidence_status="AMBIGUOUS",
        )

    if identity.evidence_status != "EXACT_PRODUCT_IDENTITY" or not auth_yes:
        return OemEvaluation(
            semantic_match_status="OEM_EVIDENCE_INSUFFICIENT",
            semantic_conflict_reason=identity.evidence_context or "no_exact_product_occurrence",
            hold_terminal="HOLD_OEM_SEMANTIC_EVIDENCE_MISSING",
            recommended_product_type_code="",
            recommended_canonical_title_fa="",
            canonical_title_verdict="OEM_TITLE_EVIDENCE_INSUFFICIENT",
            canonical_title_reason=identity.evidence_context,
            title_qualifier="",
            occurrence_type=occ_type,
            occurrence_authoritative="no",
            evidence_status=identity.evidence_status,
        )

    policy = lookup_policy(identity.oem_product_heading, pol_map)
    if policy is None:
        return OemEvaluation(
            semantic_match_status="OEM_EVIDENCE_INSUFFICIENT",
            semantic_conflict_reason="oem_heading_not_in_canonical_identity_policy",
            hold_terminal="HOLD_OEM_SEMANTIC_EVIDENCE_MISSING",
            recommended_product_type_code="",
            recommended_canonical_title_fa="",
            canonical_title_verdict="OEM_TITLE_EVIDENCE_INSUFFICIENT",
            canonical_title_reason="no_approved_policy_row",
            title_qualifier="",
            occurrence_type=occ_type,
            occurrence_authoritative="yes",
            evidence_status="EXACT_PRODUCT_IDENTITY",
        )

    pt_status, pt_reason, rec_pt = _evaluate_product_type(
        product_type_code=product_type_code,
        identity=identity,
        policy=policy,
    )
    title_verdict, title_reason, title_qual = _evaluate_canonical_title(
        canonical_title_fa=canonical_title_fa,
        identity=identity,
        policy=policy,
    )

    hold = ""
    if pt_status == "OEM_PRODUCT_TYPE_CONFLICT":
        hold = "HOLD_PRODUCT_TYPE_AUTHORITY_CONFLICT"
    elif title_verdict == "OEM_TITLE_REQUIRES_QUALIFIER":
        hold = "HOLD_CANONICAL_TITLE_AUTHORITY_CONFLICT"
    elif title_verdict == "OEM_TITLE_CONFLICT":
        if identity.oem_subtype_or_qualifier == "temperature_humidity_meter":
            hold = "HOLD_MULTI_FUNCTION_IDENTITY_CONFLICT"
            pt_status = "OEM_MULTI_FUNCTION_TITLE_CONFLICT"
            pt_reason = title_reason
        else:
            hold = "HOLD_CANONICAL_TITLE_AUTHORITY_CONFLICT"
    elif title_verdict == "OEM_TITLE_EVIDENCE_INSUFFICIENT":
        hold = "HOLD_OEM_SEMANTIC_EVIDENCE_MISSING"

    rec_title = policy.canonical_title_fa
    if title_qual:
        rec_title = f"{policy.canonical_title_fa} {title_qual}".strip()

    return OemEvaluation(
        semantic_match_status=pt_status,
        semantic_conflict_reason=pt_reason if hold else "",
        hold_terminal=hold,
        recommended_product_type_code=rec_pt if hold else product_type_code,
        recommended_canonical_title_fa=rec_title if hold else canonical_title_fa,
        canonical_title_verdict=title_verdict,
        canonical_title_reason=title_reason,
        title_qualifier=title_qual or policy.required_title_qualifier,
        occurrence_type=occ_type,
        occurrence_authoritative="yes",
        evidence_status="EXACT_PRODUCT_IDENTITY",
    )


def oem_authority_row(
    audit: Phase2DAuditRow,
    identity: OemProductIdentity | None,
    ev: OemEvaluation,
) -> dict[str, str]:
    eligible = (
        "yes"
        if ev.semantic_match_status in READY_PT_STATUSES
        and ev.canonical_title_verdict in READY_TITLE_VERDICTS
        and ev.occurrence_authoritative == "yes"
        and ev.evidence_status == "EXACT_PRODUCT_IDENTITY"
        else "no"
    )
    oem_source = identity.source_pdf if identity else ""
    oem_sha = identity.source_sha256 if identity else ""
    pdf_page = str(identity.pdf_page) if identity else ""
    printed = identity.printed_page if identity else ""
    heading = identity.oem_product_heading if identity else ""
    family = identity.oem_family if identity else ""
    subtype = identity.oem_subtype_or_qualifier if identity else ""
    return {
        "product_id": str(audit.product_id),
        "manufacturer_code": audit.manufacturer_code,
        "persisted_product_type_id": str(audit.product_type_id or ""),
        "persisted_product_type_code": audit.product_type_code or "",
        "persisted_product_type_name_fa": audit.product_type_name_fa or "",
        "canonical_title_fa": audit.canonical_title_fa or "",
        "oem_source": oem_source,
        "oem_source_sha256": oem_sha,
        "exact_pdf_page": pdf_page,
        "printed_page": printed,
        "oem_page_pdf": pdf_page,
        "oem_page_printed": printed,
        "oem_section": heading,
        "oem_product_heading": heading,
        "oem_category_or_family": family,
        "oem_code": audit.manufacturer_code,
        "OEM_subtype": subtype,
        "occurrence_type": ev.occurrence_type,
        "occurrence_authoritative": ev.occurrence_authoritative,
        "evidence_status": ev.evidence_status,
        "semantic_match_status": ev.semantic_match_status,
        "semantic_conflict_reason": ev.semantic_conflict_reason,
        "canonical_title_verdict": ev.canonical_title_verdict,
        "canonical_title_reason": ev.canonical_title_reason,
        "title_qualifier": ev.title_qualifier,
        "recommended_product_type_code": ev.recommended_product_type_code,
        "recommended_canonical_title_fa": ev.recommended_canonical_title_fa,
        "candidate_eligible_after_oem_gate": eligible,
    }


def apply_oem_semantic_holds(
    audits: list[Phase2DAuditRow],
    identity_registry: Mapping[str, OemProductIdentity],
    policies: Mapping[str, OemCanonicalPolicyRow] | None = None,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    authority_rows: list[dict[str, str]] = []
    counts: dict[str, int] = defaultdict(int)
    title_counts: dict[str, int] = defaultdict(int)
    occurrence_counts: dict[str, int] = defaultdict(int)
    pre_gate = sum(1 for a in audits if a.terminal_classification == "READY_RENAME")

    for audit in audits:
        if audit.terminal_classification != "READY_RENAME":
            continue
        key = (audit.manufacturer_code or "").strip().upper()
        identity = identity_registry.get(key)
        ev = evaluate_oem_semantic(
            product_type_code=audit.product_type_code,
            canonical_title_fa=audit.canonical_title_fa,
            identity=identity,
            policies=policies,
        )
        counts[ev.semantic_match_status] += 1
        title_counts[ev.canonical_title_verdict] += 1
        if identity:
            occurrence_counts[identity.evidence_status] += 1
        authority_rows.append(oem_authority_row(audit, identity, ev))

        ready_ok = (
            ev.semantic_match_status in READY_PT_STATUSES
            and ev.canonical_title_verdict in READY_TITLE_VERDICTS
            and ev.occurrence_authoritative == "yes"
        )
        if not ready_ok and ev.hold_terminal:
            audit.terminal_classification = ev.hold_terminal
            audit.classification_reason = (
                ev.semantic_conflict_reason or ev.canonical_title_reason
            )

    meta = {
        "pre_exact_gate_candidates": pre_gate,
        "pre_oem_READY": pre_gate,
        "OEM_semantic_validated_rows": len(authority_rows),
        **{k: counts[k] for k in sorted(counts)},
        **{f"title_{k}": title_counts[k] for k in sorted(title_counts)},
        **{f"occurrence_{k}": occurrence_counts[k] for k in sorted(occurrence_counts)},
    }
    return authority_rows, meta


@lru_cache(maxsize=1)
def default_identity_registry() -> dict[str, OemProductIdentity]:
    return load_identity_registry()


def governed_oem_source_shas() -> tuple[str, str]:
    return INSIZE_108A_SHA256, INSIZE_108B_SHA256
