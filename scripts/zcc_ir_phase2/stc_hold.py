"""STC vs non-STC HOLD_BRAND_REVIEW classification (read-only)."""

from __future__ import annotations

from typing import Any


def summarize_hold_brand_review(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify HOLD_BRAND_REVIEW rows from reconciliation records."""
    hold = [r for r in rows if r.get("primary_state") == "HOLD_BRAND_REVIEW"]
    true_stc = sum(1 for r in hold if r.get("brand_normalized") == "STC")
    non_stc_brand_review = sum(1 for r in hold if not r.get("brand_normalized"))
    other = len(hold) - true_stc - non_stc_brand_review
    total = len(hold)
    stc_plus_review = true_stc + non_stc_brand_review
    return {
        "TRUE_STC_ROWS": true_stc,
        "NON_STC_BRAND_REVIEW_ROWS": non_stc_brand_review,
        "OTHER_HOLD_BRAND_REVIEW_ROWS": other,
        "HOLD_BRAND_REVIEW_TOTAL": total,
        "COUNT_INVARIANT_VALID": stc_plus_review == total and other == 0,
    }
