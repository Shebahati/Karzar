"""Fail-closed validation for Phase 1B Route B design artifacts."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from catalog_target.taxonomy_phase1b_baseline import (
    CCT1_ALLOWED,
    MAX_CATEGORY_DEPTH,
    PHASE0B_ANCHOR,
    REMOVED_L1_HELICOIL_ROOT_IDS,
    TARGET_DOMAINS,
    is_live_product,
)
from catalog_target.taxonomy_route_b_semantics import (
    BUYER_COMMERCE_L1,
    HISTORICAL_DEPRECATED_CODES,
    load_category_semantics,
)

DOMAIN_CODES = frozenset(d["code"] for d in TARGET_DOMAINS)
INDUSTRIAL_OIL_CATEGORY_ID = 156
MIXED_CATEGORY_IDS = frozenset({116, 117, 118, 154, 155, 156, 157, 158, 159, 160, 163, 164})
FORBIDDEN_PUBLISH_TOKENS = ("UNNAMED", "WORKSHOP", "HAND_TOOLS_CATCH")


def validate_route_b_package(
    *,
    manifest: list[dict[str, str]],
    commerce_tree: list[dict[str, str]],
    product_rows: list[dict[str, str]],
    identity_registry: list[dict[str, str]],
    owner_journal: dict[int, dict[str, str]],
    reconciliation: dict[str, Any],
    oil_product_ids: set[int],
    inputs_products: list[dict[str, str]],
) -> dict[str, Any]:
    errors: list[str] = []

    current_ids = {int(r["current_category_id"]) for r in manifest}
    if len(manifest) != 135 or len(current_ids) != 135:
        errors.append("category_manifest_must_be_135_unique")

    removed = set(reconciliation.get("removed_category_ids", []))
    if removed != REMOVED_L1_HELICOIL_ROOT_IDS:
        errors.append(f"historical_removed_set_mismatch got={sorted(removed)}")
    if reconciliation.get("current_category_count") != 135:
        errors.append("phase0b_current_count_not_135")

    live = [p for p in inputs_products if is_live_product(p)]
    live_ids = {int(p["product_id"]) for p in live}
    if len(live_ids) != PHASE0B_ANCHOR["live_products"]:
        errors.append(f"live_product_count expected={PHASE0B_ANCHOR['live_products']} got={len(live_ids)}")

    pmap = [r for r in product_rows if r.get("product_id", "").isdigit()]
    pmap_ids = {int(r["product_id"]) for r in pmap}
    if pmap_ids != live_ids:
        errors.append("product_mapping_id_set_mismatch_census")

    if len(owner_journal) != 262:
        errors.append(f"owner_journal_unique_ids expected=262 got={len(owner_journal)}")
    exits = [pid for pid, r in owner_journal.items() if r.get("owner_decision") == "APPROVE_CATALOG_EXIT"]
    evidence = [pid for pid, r in owner_journal.items() if r.get("owner_decision") == "REQUEST_MORE_EVIDENCE"]
    if len(exits) != 151 or len(evidence) != 111:
        errors.append(f"owner_decision_counts exit={len(exits)} evidence={len(evidence)}")
    if any(r.get("apply_authorization", "NO").upper() not in ("NO", "") for r in owner_journal.values()):
        errors.append("owner_journal_apply_not_zero")

    for row in pmap:
        pid = int(row["product_id"])
        if pid in owner_journal:
            if row.get("owner_authoritative_decision") != owner_journal[pid].get("owner_decision"):
                errors.append(f"product_owner_decision_mismatch pid={pid}")
                break
            if row.get("approved_target_category_code"):
                errors.append(f"tx_owner_product_has_approved_target pid={pid}")
                break
            if owner_journal[pid].get("owner_decision") == "REQUEST_MORE_EVIDENCE" and row.get(
                "mapping_authorization"
            ) not in ("BLOCKED_EVIDENCE_PENDING", "BLOCKED_OWNER_SCOPE"):
                errors.append(f"evidence_pending_not_blocked pid={pid}")
                break

    reg_codes = [r["code"] for r in identity_registry if r.get("code")]
    if len(reg_codes) != len(set(reg_codes)):
        errors.append("identity_registry_duplicate_codes")

    for code in reg_codes:
        if any(tok in code for tok in FORBIDDEN_PUBLISH_TOKENS):
            errors.append(f"forbidden_token_in_registry_code {code}")

    published_manifest_codes = [
        r["published_kz_cat_code"]
        for r in manifest
        if r.get("identity_status") == "PUBLISHED_PROPOSED" and r.get("published_kz_cat_code")
    ]
    for code in published_manifest_codes:
        if any(tok in code for tok in FORBIDDEN_PUBLISH_TOKENS):
            errors.append(f"unnamed_or_forbidden_publish_code {code}")

    for row in manifest:
        if row.get("cct1_result") not in CCT1_ALLOWED:
            errors.append(f"invalid_cct1 id={row['current_category_id']}")
        fa = row.get("target_name_fa", "")
        en = row.get("target_name_en", "")
        if row.get("identity_status") == "PUBLISHED_PROPOSED" and (not en or en == fa):
            errors.append(f"weak_english_name id={row['current_category_id']}")

    tree_codes = {r["commerce_category_code"] for r in commerce_tree}
    if len(tree_codes) != len(commerce_tree):
        errors.append("commerce_tree_duplicate_codes")
    parents = {r["commerce_category_code"]: (r.get("parent_commerce_code") or "").strip() for r in commerce_tree}
    depth_by_code = {r["commerce_category_code"]: int(r["commerce_depth"]) for r in commerce_tree}
    children_of: dict[str, list[str]] = defaultdict(list)
    for code, parent in parents.items():
        if parent:
            children_of[parent].append(code)
    for code, parent in parents.items():
        if parent and parent not in tree_codes:
            errors.append(f"commerce_tree_missing_parent child={code} parent={parent}")
    for code in parents:
        seen: set[str] = set()
        cur = code
        while parents.get(cur):
            if cur in seen:
                errors.append(f"commerce_tree_cycle_at {code}")
                break
            seen.add(cur)
            cur = parents[cur]

    depths = list(depth_by_code.values())
    if max(depths, default=0) > MAX_CATEGORY_DEPTH:
        errors.append("commerce_tree_depth_exceeded")
    if min(depths, default=1) < 1:
        errors.append("commerce_tree_invalid_depth")

    buyer_roots = set(BUYER_COMMERCE_L1)
    roots = [c for c, p in parents.items() if not p]
    if len(roots) != 7:
        errors.append(f"commerce_tree_root_count expected=7 got={len(roots)}")
    if set(roots) != buyer_roots:
        errors.append(f"commerce_tree_roots_mismatch got={sorted(roots)}")
    for root in roots:
        if depth_by_code.get(root) != 1:
            errors.append(f"commerce_root_not_depth_1 code={root}")

    for code, parent in parents.items():
        if not parent:
            continue
        child_d = depth_by_code[code]
        parent_d = depth_by_code[parent]
        if child_d != parent_d + 1:
            errors.append(f"commerce_depth_not_parent_plus_one child={code} got={child_d} parent={parent_d}")

    reachable: set[str] = set()
    stack = list(roots)
    while stack:
        node = stack.pop()
        if node in reachable:
            continue
        reachable.add(node)
        stack.extend(children_of.get(node, []))
    if reachable != tree_codes:
        errors.append(
            f"commerce_tree_unreachable_nodes count={len(tree_codes - reachable)}"
        )

    for row in commerce_tree:
        code = row["commerce_category_code"]
        depth = depth_by_code[code]
        if row.get("commerce_is_selectable") == "YES":
            if depth not in (2, 3):
                errors.append(f"selectable_not_depth_2_or_3 code={code} depth={depth}")
            if children_of.get(code):
                errors.append(f"selectable_not_leaf code={code}")

    for row in manifest:
        if row.get("identity_status") != "PUBLISHED_PROPOSED":
            continue
        code = row.get("published_kz_cat_code") or ""
        if not code:
            continue
        if code not in depth_by_code:
            errors.append(f"manifest_published_code_missing_from_tree id={row['current_category_id']}")
            continue
        if row.get("commerce_tree_depth") != str(depth_by_code[code]):
            errors.append(f"manifest_depth_mismatch_tree id={row['current_category_id']}")

    retire_in_tree = [
        r["commerce_category_code"]
        for r in commerce_tree
        if r.get("source_current_category_id") in {"1", "2", "4", "5", "6", "8", "9", "56", "81", "87", "165", "154", "155"}
    ]
    if retire_in_tree:
        errors.append("legacy_or_transitional_hub_published_in_tree")

    facet_155 = [r for r in commerce_tree if r.get("source_current_category_id") == "155"]
    if facet_155:
        errors.append("facet_155_must_not_publish")

    if len(oil_product_ids) != 27:
        errors.append(f"category_156_oil_ids expected=27 got={len(oil_product_ids)}")
    for pid in oil_product_ids:
        row = next((r for r in pmap if int(r["product_id"]) == pid), None)
        if not row or int(row["current_category_id"]) != INDUSTRIAL_OIL_CATEGORY_ID:
            errors.append(f"oil_product_not_in_cat_156 pid={pid}")
            break

    domains_in_tree = {r.get("scientific_domain_code") for r in commerce_tree}
    if not domains_in_tree.issubset(DOMAIN_CODES):
        errors.append("unknown_scientific_domain_in_tree")
    if len({d for d in domains_in_tree if d}) > 7:
        errors.append("too_many_domains_in_tree")

    shared_hist = len(set(HISTORICAL_DEPRECATED_CODES.values())) != len(HISTORICAL_DEPRECATED_CODES)
    if shared_hist:
        errors.append("historical_helicoil_deprecated_codes_not_unique")

    return {"status": "PASS" if not errors else "FAIL", "errors": errors, "checks_run": True}
