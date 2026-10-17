"""Post-research effective proposals (PR #500); PR #499 proposals preserved."""

from __future__ import annotations

from typing import Any

from catalog_target.tx_owner_001_owner_research import (
    CRITICAL_CASE_ASSESSMENTS,
    OEM_TECHNICAL_SOURCES,
    resolve_m7_sku_exact,
    sources_for_product_id,
)

PR499_ANCHOR_DISPOSITIONS: dict[str, int] = {
    "CATALOG_EXIT_CANDIDATE": 242,
    "NEEDS_MORE_EVIDENCE": 18,
    "INDUSTRIAL_EXCEPTION_CANDIDATE": 1,
    "OWNER_DECISION_REQUIRED": 1,
    "SEMANTIC_CONFLICT": 0,
}

POST_RESEARCH_EXPECTED: dict[str, int] = {
    "CATALOG_EXIT_CANDIDATE": 248,
    "NEEDS_MORE_EVIDENCE": 12,
    "INDUSTRIAL_EXCEPTION_CANDIDATE": 1,
    "OWNER_DECISION_REQUIRED": 1,
    "SEMANTIC_CONFLICT": 0,
}

M7_POST_RESEARCH_EXIT_IDS = frozenset({5139, 5140, 5174, 5176, 5177, 5178})


def historical_pr499_proposal(row: dict[str, str]) -> str:
    return row["proposed_disposition"]


def post_research_evidence_basis(
    row: dict[str, str],
    *,
    m7: dict[str, str] | None,
) -> str:
    if m7:
        return m7.get("evidence_match_type", "OEM_EXACT_SKU_PAGE")
    pid = int(row["product_id"])
    if pid in CRITICAL_CASE_ASSESSMENTS:
        assess = CRITICAL_CASE_ASSESSMENTS[pid]
        if assess.get("oem_status") == "UNRESOLVED":
            return "UNRESOLVED"
        if assess.get("evidence_assessment", "").startswith("UNRESOLVED"):
            return "UNRESOLVED"
    hist = historical_pr499_proposal(row)
    basis = row.get("confidence_basis", "HEURISTIC")
    if hist == "NEEDS_MORE_EVIDENCE":
        return "CENSUS_ONLY" if basis == "CENSUS_ONLY" else basis
    return basis or "HEURISTIC"


def post_research_proposal(row: dict[str, str]) -> str:
    """Effective agent proposal after Owner-package research; not Owner approval."""
    pid = int(row["product_id"])
    sku = row.get("sku", "")
    m7 = resolve_m7_sku_exact(sku)
    if m7 and m7.get("post_research_disposition"):
        return m7["post_research_disposition"]
    if pid in M7_POST_RESEARCH_EXIT_IDS:
        return "CATALOG_EXIT_CANDIDATE"
    assess = CRITICAL_CASE_ASSESSMENTS.get(pid)
    if assess and assess.get("post_research_disposition"):
        return assess["post_research_disposition"]
    if assess and assess.get("pr499_proposal"):
        return assess["pr499_proposal"]
    return historical_pr499_proposal(row)


def enrich_row(row: dict[str, str]) -> dict[str, str]:
    hist = historical_pr499_proposal(row)
    sku = row.get("sku", "")
    m7 = resolve_m7_sku_exact(sku)
    post = post_research_proposal(row)
    basis = post_research_evidence_basis(row, m7=m7)
    oem_ids = "|".join(s["source_id"] for s in sources_for_product_id(int(row["product_id"])))
    return {
        **row,
        "historical_pr499_proposal": hist,
        "post_research_proposal": post,
        "post_research_evidence_basis": basis,
        "oem_source_ids": oem_ids,
        "proposal_status": "AGENT_PROPOSAL_NOT_OWNER_APPROVED",
        "owner_decision": "",
        "authorization_status": "PENDING",
    }


def disposition_counts(rows: list[dict[str, str]], *, field: str) -> dict[str, int]:
    counts: dict[str, int] = {k: 0 for k in PR499_ANCHOR_DISPOSITIONS}
    for row in rows:
        disp = row[field]
        counts[disp] = counts.get(disp, 0) + 1
    return counts


def validate_post_research_counts(enriched: list[dict[str, str]]) -> None:
    counts = disposition_counts(enriched, field="post_research_proposal")
    for key, expected in POST_RESEARCH_EXPECTED.items():
        if counts.get(key, 0) != expected:
            raise RuntimeError(
                f"post_research_count_mismatch {key} expected={expected} got={counts.get(key)}"
            )
    if sum(counts.values()) != 262:
        raise RuntimeError("post_research_total_not_262")
