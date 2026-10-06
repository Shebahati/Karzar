"""Phase 2D — owner canonical title precision gate (exact-OEM READY cohort only)."""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.domain.product_naming_phase2d import Phase2DAuditRow, normalize_persian_text
from app.domain.product_naming_phase2d_oem_policy import normalize_oem_heading

OWNER_POLICY_CSV = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "architecture"
    / "specs"
    / "product-naming-v1"
    / "OWNER_CANONICAL_TITLE_POLICY.csv"
)

OWNER_TITLE_VERDICTS = frozenset(
    {
        "OWNER_TITLE_EXACT",
        "OWNER_TITLE_BROADER_BUT_APPROVED",
        "OWNER_TITLE_REQUIRES_QUALIFIER",
        "OWNER_TITLE_HOLD",
    }
)


@dataclass(frozen=True)
class OwnerTitlePolicyRow:
    oem_product_heading: str
    product_type_code: str
    base_canonical_title_fa: str
    required_identity_qualifier_fa: str
    final_canonical_title_fa: str
    owner_title_status: str
    policy_basis: str


def load_owner_title_policy(path: Path | None = None) -> dict[tuple[str, str], OwnerTitlePolicyRow]:
    src = path or OWNER_POLICY_CSV
    out: dict[tuple[str, str], OwnerTitlePolicyRow] = {}
    if not src.is_file():
        return out
    with src.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            heading = normalize_oem_heading(row.get("OEM_product_heading") or "")
            pt = (row.get("product_type_code") or "").strip()
            if not heading or not pt:
                continue
            out[(heading, pt)] = OwnerTitlePolicyRow(
                oem_product_heading=heading,
                product_type_code=pt,
                base_canonical_title_fa=(row.get("base_canonical_title_fa") or "").strip(),
                required_identity_qualifier_fa=(row.get("required_identity_qualifier_fa") or "").strip(),
                final_canonical_title_fa=(row.get("final_canonical_title_fa") or "").strip(),
                owner_title_status=(row.get("owner_title_status") or "").strip(),
                policy_basis=(row.get("policy_basis") or "").strip(),
            )
    return out


@lru_cache(maxsize=1)
def default_owner_title_policy() -> dict[tuple[str, str], OwnerTitlePolicyRow]:
    return load_owner_title_policy()


def lookup_owner_policy(
    oem_heading: str,
    product_type_code: str,
    policies: Mapping[tuple[str, str], OwnerTitlePolicyRow] | None = None,
) -> OwnerTitlePolicyRow | None:
    pol = policies if policies is not None else default_owner_title_policy()
    key = (normalize_oem_heading(oem_heading), (product_type_code or "").strip())
    return pol.get(key)


def _owner_title_verdict(
    policy: OwnerTitlePolicyRow,
    current_canonical: str,
) -> tuple[str, str]:
    if policy.owner_title_status != "APPROVED":
        return "OWNER_TITLE_HOLD", policy.policy_basis or "owner_policy_hold"
    final = policy.final_canonical_title_fa
    base = policy.base_canonical_title_fa
    qual = policy.required_identity_qualifier_fa
    cur = (current_canonical or "").strip()
    if final == cur and final == base and not qual:
        return "OWNER_TITLE_EXACT", "matches_base_and_current"
    if final == cur:
        return "OWNER_TITLE_EXACT", "matches_governed_final_title"
    if qual and qual in final and final != base:
        return "OWNER_TITLE_BROADER_BUT_APPROVED", "governed_identity_qualifiers_in_final_title"
    if final == base:
        return "OWNER_TITLE_BROADER_BUT_APPROVED", "owner_approved_base_without_extra_qualifier"
    return "OWNER_TITLE_BROADER_BUT_APPROVED", "owner_approved_final_canonical_title"


def rebuild_proposed_name_with_title(
    audit: Phase2DAuditRow,
    new_title: str,
) -> str:
    prop = audit.proposed_name or ""
    old_title = (audit.canonical_title_fa or "").strip()
    code = (audit.manufacturer_code or "").strip()
    marker = f"کد {code}"
    if not code or marker not in prop:
        return prop
    idx = prop.index(marker)
    tail = prop[idx + len(marker) :]
    before_marker = prop[:idx].strip()
    if old_title and before_marker.startswith(old_title):
        rest = before_marker[len(old_title) :].strip()
        return f"{new_title} {rest} {marker}{tail}".strip()
    brand = (audit.brand_display or audit.brand_name or "اینسایز").strip()
    return f"{new_title} {brand} {marker}{tail}".strip()


def evaluate_owner_title(
    *,
    oem_product_heading: str,
    product_type_code: str,
    canonical_title_fa: str,
    policies: Mapping[tuple[str, str], OwnerTitlePolicyRow] | None = None,
) -> tuple[str, str, str, str, str]:
    """Return verdict, reason, owner_status, final_title, required_qualifiers."""
    policy = lookup_owner_policy(oem_product_heading, product_type_code, policies)
    if policy is None:
        return (
            "OWNER_TITLE_HOLD",
            "no_owner_title_policy_row",
            "HOLD",
            "",
            "",
        )
    if policy.owner_title_status != "APPROVED":
        return (
            "OWNER_TITLE_HOLD",
            policy.policy_basis or "owner_policy_hold",
            "HOLD",
            "",
            policy.required_identity_qualifier_fa,
        )
    verdict, reason = _owner_title_verdict(policy, canonical_title_fa)
    return (
        verdict,
        reason,
        "APPROVED",
        policy.final_canonical_title_fa,
        policy.required_identity_qualifier_fa,
    )


def apply_owner_title_holds(
    audits: list[Phase2DAuditRow],
    oem_authority_rows: list[dict[str, str]],
    policies: Mapping[tuple[str, str], OwnerTitlePolicyRow] | None = None,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    oem_by_pid = {int(r["product_id"]): r for r in oem_authority_rows}
    review_rows: list[dict[str, str]] = []
    verdict_counts: dict[str, int] = defaultdict(int)
    pre_candidates = sum(1 for a in audits if a.terminal_classification == "READY_RENAME")

    for audit in audits:
        if audit.terminal_classification != "READY_RENAME":
            continue
        oem = oem_by_pid.get(audit.product_id, {})
        heading = oem.get("oem_product_heading") or ""
        verdict, reason, owner_status, final_title, req_quals = evaluate_owner_title(
            oem_product_heading=heading,
            product_type_code=audit.product_type_code or "",
            canonical_title_fa=audit.canonical_title_fa,
            policies=policies,
        )
        verdict_counts[verdict] += 1
        variant_suffix = ""
        prop = audit.proposed_name or ""
        if "، " in prop and f"کد {audit.manufacturer_code}" in prop:
            pos = prop.find("، ")
            if pos > prop.find(f"کد {audit.manufacturer_code}"):
                variant_suffix = prop[pos + 2 :]

        review_rows.append(
            {
                "product_id": str(audit.product_id),
                "manufacturer_code": audit.manufacturer_code,
                "OEM_product_heading": heading,
                "product_type_code": audit.product_type_code or "",
                "current_name": audit.current_name,
                "current_proposed_name": audit.proposed_name,
                "required_identity_qualifiers": req_quals,
                "owner_final_canonical_title": final_title,
                "variant_suffix": variant_suffix,
                "owner_title_status": owner_status,
                "owner_title_verdict": verdict,
                "owner_title_reason": reason,
            }
        )

        if owner_status != "APPROVED" or verdict == "OWNER_TITLE_HOLD":
            audit.terminal_classification = "HOLD_OWNER_CANONICAL_TITLE_REVIEW"
            audit.classification_reason = reason
            continue

        if not final_title:
            audit.terminal_classification = "HOLD_OWNER_CANONICAL_TITLE_REVIEW"
            audit.classification_reason = "missing_final_canonical_title"
            continue

        new_proposed = rebuild_proposed_name_with_title(audit, final_title)
        audit.canonical_title_fa = final_title
        audit.proposed_name = new_proposed
        audit.comparison_normalized_proposed = normalize_persian_text(audit.proposed_name)

    approved = sum(1 for r in review_rows if r["owner_title_status"] == "APPROVED")
    hold = len(review_rows) - approved
    meta = {
        "pre_owner_title_candidates": pre_candidates,
        "owner_title_approved": approved,
        "owner_title_hold": hold,
        **{k: verdict_counts[k] for k in sorted(verdict_counts)},
    }
    return review_rows, meta


def required_qualifiers_preserved(final_title: str, required: str) -> bool:
    if not required:
        return True
    for part in re.split(r"\s+", required.strip()):
        if part and part not in final_title:
            return False
    return True
