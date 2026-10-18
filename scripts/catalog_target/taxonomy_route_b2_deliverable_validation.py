"""Fail-closed validation of generated B2 deliverables (not only B1 revalidation)."""

from __future__ import annotations

from typing import Any

from catalog_target.taxonomy_phase1b_baseline import PHASE0B_ANCHOR
from catalog_target.taxonomy_route_b2_architecture_review import (
    DECOMPOSITION_REQUIRED_BY_CATEGORY,
    HELICOIL_CATEGORY_ID,
    HELICOIL_PRODUCT_IDS,
    HOLD_CATEGORY_IDS,
    INDUSTRIAL_OIL_CATEGORY_ID,
    B2Inputs,
)

FORBIDDEN_OWNER_ARCH_STATUSES = frozenset(
    {"OWNER_APPROVED", "OWNER_APPROVED_ARCHITECTURE", "OWNER_FREEZE_EXECUTED"}
)


def _parse_id_pipe(value: str) -> list[int]:
    if not (value or "").strip():
        return []
    return [int(x) for x in value.split("|") if x.strip().isdigit()]


def validate_b2_deliverables(
    *,
    inputs: B2Inputs,
    invariants: dict[str, Any],
    arch_matrix: list[dict[str, str]],
    tree_disposition: list[dict[str, str]],
    owner_groups: list[dict[str, str]],
    hold_category_map: list[dict[str, str]],
    product_impact: list[dict[str, str]],
    sensitive_dossier: list[dict[str, str]],
    b1_product_ids: set[int],
) -> dict[str, Any]:
    errors: list[str] = []

    if invariants["live_product_rows"] != PHASE0B_ANCHOR["live_products"]:
        errors.append("live_product_count_drift")
    if invariants["owner_journal_exits"] != 151 or invariants["owner_journal_evidence"] != 111:
        errors.append("owner_journal_151_111")
    if invariants["evidence_111_register_ids"] != 111:
        errors.append("evidence_111_register")
    if invariants["category_156_product_rows"] != 27:
        errors.append("oil_cohort_27")
    if invariants["approved_executable_target_codes"] != 0:
        errors.append("executable_targets")

    arch_ids = [int(r["current_category_id"]) for r in arch_matrix]
    if len(arch_ids) != 135 or len(set(arch_ids)) != 135:
        errors.append("arch_matrix_135_unique")

    b2_ids = {int(r["product_id"]) for r in product_impact if r["product_id"].isdigit()}
    if b2_ids != b1_product_ids:
        errors.append("b2_product_id_set_differs_from_b1")

    covered_hold: set[int] = set()
    for row in owner_groups:
        covered_hold.update(_parse_id_pipe(row.get("covers_hold_category_ids", "")))
    for row in hold_category_map:
        cid = int(row["hold_category_id"])
        gid = row["decision_group_id"]
        if cid not in HOLD_CATEGORY_IDS:
            errors.append(f"hold_map_invalid_category_{cid}")
        if not any(g["decision_group_id"] == gid for g in owner_groups):
            errors.append(f"hold_map_unknown_group_{gid}")
        covered_hold.add(cid)

    if covered_hold != HOLD_CATEGORY_IDS:
        missing = sorted(HOLD_CATEGORY_IDS - covered_hold)
        extra = sorted(covered_hold - HOLD_CATEGORY_IDS)
        if missing:
            errors.append(f"hold_categories_missing_from_register:{missing}")
        if extra:
            errors.append(f"hold_map_extra_categories:{extra}")

    for cid in HOLD_CATEGORY_IDS:
        row = next(r for r in arch_matrix if int(r["current_category_id"]) == cid)
        if row.get("b2_recommended_disposition") != "HOLD":
            errors.append(f"hold_category_{cid}_not_hold_in_matrix")
        if row.get("owner_architecture_decision_status") != "PENDING":
            errors.append(f"hold_category_{cid}_owner_arch_not_pending")

    for row in arch_matrix:
        if row.get("owner_architecture_decision_status") in FORBIDDEN_OWNER_ARCH_STATUSES:
            errors.append("owner_architecture_marked_approved")
        if row.get("apply_authorization_status") != "NO":
            errors.append("apply_authorization_not_no")

    for row in tree_disposition:
        if row.get("owner_architecture_decision_status") in FORBIDDEN_OWNER_ARCH_STATUSES:
            errors.append("tree_owner_arch_approved")
        code = row.get("commerce_category_code", "")
        if code.startswith("KZ.CAT.METROLOGY_FAMILY_") and row.get("b2_recommended_disposition") == "FREEZE":
            errors.append("metrology_l2_marked_freeze_while_decision_pending")

    megamenu = next((g for g in owner_groups if g["decision_group_id"] == "MEGAMENU-186-187-188"), None)
    if megamenu and megamenu.get("blocks_architecture_freeze") == "YES":
        errors.append("tier_d_blocks_architecture_freeze")

    helicoil_row = next(
        (r for r in sensitive_dossier if r.get("category_id") == str(HELICOIL_CATEGORY_ID)),
        None,
    )
    if helicoil_row:
        got = _parse_id_pipe(helicoil_row.get("product_ids", "").replace(",", "|"))
        if sorted(got) != sorted(HELICOIL_PRODUCT_IDS):
            errors.append("helicoil_product_ids_incomplete")
    else:
        errors.append("helicoil_dossier_missing")

    for cid, expected in DECOMPOSITION_REQUIRED_BY_CATEGORY.items():
        actual = sum(
            1
            for r in product_impact
            if r["product_id"].isdigit()
            and int(r["current_category_id"]) == cid
            and r.get("mapping_mode") == "PRODUCT_LEVEL_REQUIRED"
        )
        if actual != expected:
            errors.append(f"decomposition_count_cat_{cid}_{actual}_not_{expected}")

    for row in product_impact:
        if row.get("executable_in_b2") == "YES":
            errors.append("executable_in_b2_yes")
            break
        if (row.get("approved_target_category_code") or "").strip():
            errors.append("approved_target_in_deliverable")

    evidence_pending = {
        pid for pid, j in inputs.owner_journal.items() if j["owner_decision"] == "REQUEST_MORE_EVIDENCE"
    }
    if evidence_pending != inputs.evidence_111_ids:
        errors.append("evidence_111_journal_mismatch")

    for pid in evidence_pending:
        prow = next((r for r in product_impact if int(r["product_id"]) == pid), None)
        if not prow or prow.get("in_evidence_111_register") != "YES":
            errors.append(f"evidence_pending_pid_{pid}_not_traceable")

    oil_rows = [
        r
        for r in product_impact
        if r["product_id"].isdigit() and int(r["current_category_id"]) == INDUSTRIAL_OIL_CATEGORY_ID
    ]
    if len(oil_rows) != 27:
        errors.append("fluids_oil_rows_not_27")
    for r in oil_rows:
        if (r.get("approved_target_category_code") or "").strip():
            errors.append("oil_has_executable_target")

    for cid in (154, 155, 163):
        row = next(r for r in arch_matrix if int(r["current_category_id"]) == cid)
        desc = int(row.get("descendant_live_product_count") or 0)
        if desc <= 0:
            errors.append(f"category_{cid}_descendant_impact_zero_hidden")

    decomp_total = sum(
        1 for r in product_impact if r.get("mapping_mode") == "PRODUCT_LEVEL_REQUIRED"
    )
    if decomp_total != 718:
        errors.append(f"decomposition_total_{decomp_total}_not_718")

    for g in owner_groups:
        if g.get("blocks_architecture_freeze") == "YES" and g.get("blocks_execution_release_gate") == "YES":
            if g.get("freeze_tier") == "D":
                errors.append("tier_d_contradictory_block_flags")

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "hold_coverage": sorted(covered_hold),
        "decision_group_count": len(owner_groups),
    }
