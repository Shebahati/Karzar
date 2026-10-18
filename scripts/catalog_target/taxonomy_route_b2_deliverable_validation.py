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
    build_category_product_impact_reference,
)

FORBIDDEN_OWNER_ARCH_STATUSES = frozenset(
    {"OWNER_APPROVED", "OWNER_APPROVED_ARCHITECTURE", "OWNER_FREEZE_EXECUTED"}
)


def _parse_id_pipe(value: str) -> list[int]:
    if not (value or "").strip():
        return []
    return [int(x) for x in value.replace(",", "|").split("|") if x.strip().isdigit()]


def _group_covers_category(group: dict[str, str], cid: int) -> bool:
    return cid in _parse_id_pipe(group.get("covers_hold_category_ids", ""))


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

    manifest_category_ids = {int(r["current_category_id"]) for r in inputs.manifest}
    arch_ids_list = [int(r["current_category_id"]) for r in arch_matrix]
    arch_ids_set = set(arch_ids_list)
    if arch_ids_set != manifest_category_ids or len(arch_ids_list) != len(arch_ids_set):
        errors.append("arch_matrix_category_id_set_invalid")

    product_rows = [r for r in product_impact if r["product_id"].isdigit()]
    product_id_list = [int(r["product_id"]) for r in product_rows]
    product_id_set = set(product_id_list)
    if len(product_id_list) != len(product_id_set):
        errors.append("product_impact_duplicate_product_ids")
    if product_id_set != b1_product_ids:
        errors.append("b2_product_id_set_differs_from_b1")

    impact_ref = build_category_product_impact_reference(inputs)
    for row in arch_matrix:
        cid = int(row["current_category_id"])
        ref = impact_ref[cid]
        direct_n = int(row.get("direct_distinct_product_ids_count") or -1)
        desc_n = int(row.get("descendant_inclusive_distinct_product_ids_count") or -1)
        unres_n = int(row.get("descendant_inclusive_unresolved_product_ids_count") or -1)
        if direct_n != len(ref.direct_product_ids):
            errors.append(f"category_{cid}_direct_distinct_mismatch")
        if desc_n != len(ref.descendant_inclusive_product_ids):
            errors.append(f"category_{cid}_descendant_distinct_mismatch")
        if unres_n != len(ref.descendant_inclusive_unresolved_product_ids):
            errors.append(f"category_{cid}_descendant_unresolved_mismatch")
        census_desc = int(row.get("descendant_live_product_count") or 0)
        if census_desc != len(ref.descendant_inclusive_product_ids):
            errors.append(f"category_{cid}_census_descendant_vs_graph_mismatch")

    if impact_ref[154].descendant_inclusive_product_ids and int(
        next(r for r in arch_matrix if int(r["current_category_id"]) == 154).get(
            "descendant_inclusive_distinct_product_ids_count"
        )
        or 0
    ) == 0:
        errors.append("category_154_distinct_affected_zero")

    if len(hold_category_map) != len(HOLD_CATEGORY_IDS):
        errors.append("c2_hold_map_row_count_not_11")

    hold_map_ids = {int(r["hold_category_id"]) for r in hold_category_map}
    if hold_map_ids != HOLD_CATEGORY_IDS:
        errors.append("c2_hold_map_id_set_invalid")

    for map_row in hold_category_map:
        cid = int(map_row["hold_category_id"])
        gid = map_row["decision_group_id"]
        if map_row.get("owner_architecture_decision_status") != "PENDING":
            errors.append(f"c2_hold_{cid}_status_not_pending")
        group = next((g for g in owner_groups if g["decision_group_id"] == gid), None)
        if not group:
            errors.append(f"c2_hold_{cid}_orphan_group_{gid}")
        elif not _group_covers_category(group, cid):
            errors.append(f"c2_hold_{cid}_group_missing_covers_hold_ids")

    for g in owner_groups:
        if g.get("owner_architecture_decision_status") != "PENDING":
            errors.append(f"owner_group_{g['decision_group_id']}_not_pending")

    covered_from_groups: set[int] = set()
    for row in owner_groups:
        covered_from_groups.update(_parse_id_pipe(row.get("covers_hold_category_ids", "")))

    if covered_from_groups != HOLD_CATEGORY_IDS:
        errors.append("owner_groups_hold_coverage_mismatch")

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
        if row.get("census_product_facts") != "CONFIRMED_CENSUS":
            errors.append("census_facts_not_confirmed")
        sem = row.get("b1_semantic_interpretation_evidence", "")
        if sem in {"OWNER_APPROVED", "OWNER_APPROVED_ARCHITECTURE"}:
            errors.append("semantic_marked_owner_approved_architecture")

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
        got = _parse_id_pipe(helicoil_row.get("product_ids", ""))
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

    for cid in (154, 155, 163, 157, 159):
        row = next(r for r in arch_matrix if int(r["current_category_id"]) == cid)
        desc_distinct = int(row.get("descendant_inclusive_distinct_product_ids_count") or 0)
        if desc_distinct <= 0:
            errors.append(f"category_{cid}_descendant_distinct_zero")

    decomp_total = sum(1 for r in product_impact if r.get("mapping_mode") == "PRODUCT_LEVEL_REQUIRED")
    if decomp_total != 718:
        errors.append(f"decomposition_total_{decomp_total}_not_718")

    for g in owner_groups:
        if g.get("blocks_architecture_freeze") == "YES" and g.get("blocks_execution_release_gate") == "YES":
            if g.get("freeze_tier") == "D":
                errors.append("tier_d_contradictory_block_flags")

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "hold_coverage": sorted(hold_map_ids),
        "decision_group_count": len(owner_groups),
    }
