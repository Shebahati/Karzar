"""Phase 1B Route B2 — architecture review over frozen B1 design (design-only)."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from catalog_target.taxonomy_phase1b_baseline import (
    PHASE0B_ANCHOR,
    TX_OWNER_SCOPE_CATEGORY_IDS,
    write_csv,
    write_sha256sums,
)
from catalog_target.taxonomy_route_b_semantics import HISTORICAL_DEPRECATED_CODES
from catalog_target.taxonomy_route_b_validation import validate_route_b_package

ROOT = Path(__file__).resolve().parents[2]
B1_DIR = ROOT / "audit/taxonomy-phase1b-route-b-target-design-2026-10-18"
BASELINE_DIR = ROOT / "audit/taxonomy-phase1b-baseline-2026-10-15"
OWNER_PKG = ROOT / "audit/taxonomy-phase1b-tx-owner-001-owner-decision-package"
EVIDENCE_111 = (
    ROOT
    / "audit/taxonomy-phase1b-tx-owner-001-evidence-111-action-2026-10-18"
    / "01-EXACT-111-OPEN-EVIDENCE-ACTION-REGISTER.csv"
)
B2_DIR_NAME = "audit/taxonomy-phase1b-route-b2-architecture-review-2026-10-18"
PR533_MERGE_SHA = "8be4a5807a2eeb25da26c802e74bb9b0fc301916"

SENSITIVE_CATEGORY_IDS = frozenset({116, 117, 118, 154, 155, 156, 157, 158, 159, 160, 163, 164})
HOLD_CATEGORY_IDS = frozenset({116, 117, 118, 154, 155, 157, 158, 159, 160, 163, 164})
HELICOIL_CATEGORY_ID = 55
INDUSTRIAL_OIL_CATEGORY_ID = 156

HELICOIL_PRODUCT_IDS: tuple[int, ...] = (
    2662,
    2663,
    4158,
    4159,
    4160,
    4161,
    4162,
    4163,
    4164,
    4165,
    4166,
    4167,
    4168,
    4169,
    4170,
    4171,
    4172,
    4173,
    4174,
    4175,
    4176,
    4177,
    4178,
    4179,
    4180,
    4181,
    4182,
    4183,
    4184,
)

DECOMPOSITION_REQUIRED_BY_CATEGORY: dict[int, int] = {
    116: 571,
    117: 40,
    118: 0,
    156: 27,
    164: 80,
}

METROLOGY_L2_FAMILY_CODES = frozenset(
    {
        "KZ.CAT.METROLOGY_FAMILY_PRECISION",
        "KZ.CAT.METROLOGY_FAMILY_CNC",
        "KZ.CAT.METROLOGY_FAMILY_LABORATORY",
    }
)

@dataclass(frozen=True)
class B2Inputs:
    manifest: list[dict[str, str]]
    commerce_tree: list[dict[str, str]]
    product_map: list[dict[str, str]]
    mixed_matrix: list[dict[str, str]]
    seo_rows: list[dict[str, str]]
    owner_journal: dict[int, dict[str, str]]
    evidence_111_ids: set[int]
    baseline_census: dict[int, dict[str, str]]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_owner_journals() -> dict[int, dict[str, str]]:
    out: dict[int, dict[str, str]] = {}
    for path in sorted(OWNER_PKG.glob("OWNER-AUTHORIZATION-BATCH-*-2026-10-1*.csv")):
        m = re.search(r"BATCH-(\d+)", path.name)
        batch = m.group(1) if m else ""
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                pid = int(row["product_id"])
                out[pid] = {
                    "owner_decision": row.get("owner_decision", "").strip(),
                    "owner_decision_batch": batch,
                    "apply_authorization": row.get("apply_authorization", "NO").strip(),
                    "historical_pr499_proposal": row.get("historical_pr499_proposal", "").strip(),
                }
    return out


def load_evidence_111_ids() -> set[int]:
    if not EVIDENCE_111.is_file():
        return set()
    return {int(r["product_id"]) for r in _read_csv(EVIDENCE_111)}


def load_baseline_census() -> dict[int, dict[str, str]]:
    path = BASELINE_DIR / "01-CATEGORY-CENSUS.csv"
    return {int(r["category_id"]): r for r in _read_csv(path)}


def load_b2_inputs() -> B2Inputs:
    return B2Inputs(
        manifest=_read_csv(B1_DIR / "A-135-CURRENT-TARGET-MANIFEST.csv"),
        commerce_tree=_read_csv(B1_DIR / "C-TARGET-TAXONOMY-TREE.csv"),
        product_map=_read_csv(B1_DIR / "D-PRODUCT-MAPPING-READINESS.csv"),
        mixed_matrix=_read_csv(B1_DIR / "D2-MIXED-CATEGORY-DECOMPOSITION-MATRIX.csv"),
        seo_rows=_read_csv(B1_DIR / "F-SEO-MEGAMENU-IMPORT-IMPACT.csv"),
        owner_journal=load_owner_journals(),
        evidence_111_ids=load_evidence_111_ids(),
        baseline_census=load_baseline_census(),
    )


@dataclass(frozen=True)
class CategoryProductImpactRef:
    direct_product_ids: frozenset[int]
    descendant_inclusive_product_ids: frozenset[int]
    descendant_inclusive_unresolved_product_ids: frozenset[int]


def build_category_children_index(baseline_census: dict[int, dict[str, str]]) -> dict[int, list[int]]:
    children: dict[int, list[int]] = defaultdict(list)
    for cid, row in baseline_census.items():
        parent_raw = (row.get("parent_id") or "").strip()
        if parent_raw.isdigit():
            children[int(parent_raw)].append(cid)
    return children


def category_subtree_category_ids(root: int, children: dict[int, list[int]]) -> frozenset[int]:
    seen: set[int] = set()
    stack = [root]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(children.get(current, ()))
    return frozenset(seen)


def product_row_is_unresolved(row: dict[str, str], pid: int, evidence_111_ids: set[int]) -> bool:
    if row.get("mapping_authorization", "").startswith("BLOCKED"):
        return True
    if pid in evidence_111_ids:
        return True
    if row.get("mapping_mode") == "PRODUCT_LEVEL_REQUIRED":
        return True
    return False


def build_category_product_impact_reference(inputs: B2Inputs) -> dict[int, CategoryProductImpactRef]:
    children = build_category_children_index(inputs.baseline_census)
    direct_by_cat: dict[int, set[int]] = defaultdict(set)
    row_by_pid: dict[int, dict[str, str]] = {}
    for row in inputs.product_map:
        if not row["product_id"].isdigit():
            continue
        pid = int(row["product_id"])
        cid = int(row["current_category_id"])
        direct_by_cat[cid].add(pid)
        row_by_pid[pid] = row

    manifest_ids = {int(r["current_category_id"]) for r in inputs.manifest}
    ref: dict[int, CategoryProductImpactRef] = {}
    for cid in manifest_ids:
        subtree = category_subtree_category_ids(cid, children)
        descendant_pids: set[int] = set()
        unresolved_pids: set[int] = set()
        for sub_cid in subtree:
            for pid in direct_by_cat.get(sub_cid, ()):
                descendant_pids.add(pid)
                if product_row_is_unresolved(row_by_pid[pid], pid, inputs.evidence_111_ids):
                    unresolved_pids.add(pid)
        ref[cid] = CategoryProductImpactRef(
            direct_product_ids=frozenset(direct_by_cat.get(cid, ())),
            descendant_inclusive_product_ids=frozenset(descendant_pids),
            descendant_inclusive_unresolved_product_ids=frozenset(unresolved_pids),
        )
    return ref


def census_semantic_evidence_label(row: dict[str, str]) -> str:
    dc = row.get("decision_class", "")
    if dc == "OWNER_APPROVED":
        return "TX_OWNER_DOCUMENTARY_ONLY"
    if dc == "EVIDENCE_GATED":
        return "EVIDENCE_GATED_B1"
    if dc == "PROPOSED":
        return "PROPOSED_B1"
    return "UNCLASSIFIED_B1"


def b2_interpretation_layer(row: dict[str, str], cid: int) -> str:
    if cid in HOLD_CATEGORY_IDS or row.get("product_decomposition_required") == "YES":
        return "B2_REVIEW_OVER_B1"
    if row.get("identity_status") == "LEGACY_HUB_RETIRED":
        return "B2_RETIRE_HUB_ALIGNMENT"
    return "B2_ALIGNS_B1_PROPOSAL"


def architecture_confidence(row: dict[str, str], cid: int) -> tuple[str, str]:
    if cid in HOLD_CATEGORY_IDS:
        return "LOW", "Hub/mixed/decomposition — owner decision required"
    if row.get("product_decomposition_required") == "YES":
        return "LOW", "PRODUCT_LEVEL_REQUIRED cohort"
    if row.get("identity_status") == "PUBLISHED_PROPOSED":
        if row.get("decision_class") == "PROPOSED" and row.get("cct1_result") == "KEEP_AS_CATEGORY":
            return "MEDIUM", "B1 commerce mapping; owner architecture still PENDING"
        return "LOW", "Published-proposed without completed owner architecture review"
    if row.get("identity_status") == "LEGACY_HUB_RETIRED":
        return "MEDIUM", "Census confirms hub retirement pattern"
    if row.get("decision_class") == "EVIDENCE_GATED":
        return "LOW", "B1 evidence-gated"
    return "MEDIUM", "Standard B1 manifest row"


def classify_node_kind(row: dict[str, str]) -> str:
    status = row.get("identity_status", "")
    if status == "PUBLISHED_PROPOSED":
        code = row.get("published_kz_cat_code", "")
        if code:
            return "BUYER_FACING_CATEGORY"
    if status == "LEGACY_HUB_RETIRED":
        return "TRANSITIONAL_LEGACY_HUB"
    if status.startswith("DEPRECATED"):
        return "DEPRECATED_OWNER_OR_HISTORICAL"
    if status in {"STAGING_EVIDENCE_GATED", "TRANSITIONAL_EXCLUDED"}:
        return "EVIDENCE_GATED_STAGING"
    if row.get("cct1_result") == "BETTER_AS_FACET":
        return "FACET_NOT_COMMERCE_NODE"
    return "REVIEW_OTHER"


def b2_recommended_disposition_category(row: dict[str, str], cid: int) -> str:
    if cid in HOLD_CATEGORY_IDS:
        return "HOLD"
    if cid == INDUSTRIAL_OIL_CATEGORY_ID:
        return "FREEZE"
    if row.get("identity_status") == "PUBLISHED_PROPOSED" and row.get("published_kz_cat_code"):
        if row.get("product_decomposition_required") == "YES":
            return "HOLD"
        return "FREEZE"
    if row.get("identity_status") == "LEGACY_HUB_RETIRED":
        return "FREEZE"
    if row.get("identity_status", "").startswith("DEPRECATED"):
        return "HOLD"
    return "FREEZE"


def owner_architecture_decision_status(_row: dict[str, str], _cid: int) -> str:
    return "PENDING"


def tx_owner_documentary_status(row: dict[str, str], cid: int) -> str:
    if cid not in TX_OWNER_SCOPE_CATEGORY_IDS:
        return "NOT_IN_TX_OWNER_SCOPE"
    if row.get("decision_class") == "OWNER_APPROVED":
        return "CATALOG_EXIT_DOCUMENTARY_ONLY"
    return "NONE"


def tree_b2_recommended_disposition(node: dict[str, str]) -> str:
    code = node.get("commerce_category_code", "")
    kind = node.get("node_kind", "")
    if kind == "BUYER_COMMERCE_L1":
        return "HOLD"
    if code in METROLOGY_L2_FAMILY_CODES:
        return "HOLD"
    if code == "KZ.CAT.FLUIDS_INDUSTRIAL_OIL":
        return "HOLD"
    if kind == "BUYER_COMMERCE_PUBLISHABLE":
        src = node.get("source_current_category_id", "")
        if src and int(src) in HOLD_CATEGORY_IDS:
            return "HOLD"
        if src and int(src) == INDUSTRIAL_OIL_CATEGORY_ID:
            return "HOLD"
        return "FREEZE"
    if kind == "BUYER_COMMERCE_L2_FAMILY":
        return "FREEZE"
    if kind.startswith("DEPRECATED") or code in HISTORICAL_DEPRECATED_CODES.values():
        return "HOLD"
    return "REVISE"


def classification_rationale(row: dict[str, str], cid: int) -> str:
    status = row.get("identity_status", "")
    action = row.get("category_migration_action", "")
    cct1 = row.get("cct1_result", "")
    if cid in HOLD_CATEGORY_IDS:
        if cid in {116, 117, 118}:
            return (
                "Mixed chuck/accessory leaf: B1 STAGING_EVIDENCE_GATED; "
                f"{DECOMPOSITION_REQUIRED_BY_CATEGORY.get(cid, 0)} PRODUCT_LEVEL_REQUIRED rows."
            )
        if cid == 154:
            return "Transitional L1 hub with 289 descendant SKUs; B1 DECOMPOSE_HUB — no blanket delete."
        if cid == 155:
            return (
                "B1 BETTER_AS_FACET: navigation facet under legacy 154 path; "
                "27 oils live under child 156 — facet vs BUYER_FLUIDS L1 must be owner-resolved."
            )
        if cid in TX_OWNER_SCOPE_CATEGORY_IDS:
            return (
                "TX-OWNER-001 deprecated scope; documentary exit may exist but "
                "no architecture APPLY or commerce republication inside scientific domains."
            )
        if cid in {163, 164}:
            return (
                "Machine accessories hub/leaf: B1 DECOMPOSE_HUB / EVIDENCE_GATED; "
                f"164 carries {DECOMPOSITION_REQUIRED_BY_CATEGORY.get(164, 0)} blocked decomposition SKUs."
            )
    if cid == INDUSTRIAL_OIL_CATEGORY_ID:
        return (
            "Protected 27-SKU cohort (B1 PROTECTED_27) maps to KZ.CAT.FLUIDS_INDUSTRIAL_OIL; "
            "cohort invariant ≠ owner publication freeze."
        )
    if cid == HELICOIL_CATEGORY_ID:
        return (
            "29 SKUs belong under THREAD_REPAIR commerce design; "
            "historic menu roots 186/187/188 remain deprecated identities."
        )
    if status == "LEGACY_HUB_RETIRED":
        return f"Legacy L1 hub ({action}); buyer tree retires hub — redirect planning deferred to execution tier D."
    if status == "PUBLISHED_PROPOSED" and row.get("published_kz_cat_code"):
        return f"Publishable commerce leaf proposed in B1 ({row['published_kz_cat_code']}); CCT1={cct1}."
    if cct1 == "BETTER_AS_FACET":
        return "Facet/navigation relationship — not a standalone buyer commerce leaf without owner confirmation."
    return f"B1 manifest classification: {status}; migration={action}."


def recalculate_invariants(inputs: B2Inputs) -> dict[str, Any]:
    manifest_ids = {int(r["current_category_id"]) for r in inputs.manifest}
    tree = inputs.commerce_tree
    depth_hist = Counter(int(r["commerce_depth"]) for r in tree)
    roots = [r for r in tree if not (r.get("parent_commerce_code") or "").strip()]
    inherited = [r for r in tree if r.get("source_current_category_id", "").strip()]
    selectable = [r for r in tree if r.get("commerce_is_selectable") == "YES"]
    products = [r for r in inputs.product_map if r["product_id"].isdigit()]
    product_level_required = [r for r in products if r.get("mapping_mode") == "PRODUCT_LEVEL_REQUIRED"]
    decomp = [
        r
        for r in products
        if r.get("mapping_mode") in ("PRODUCT_LEVEL_REQUIRED", "TX_OWNER_001_FROZEN")
        or r.get("mapping_authorization", "").startswith("BLOCKED")
    ]
    tx = [r for r in products if r.get("tx_owner_cohort") == "YES"]
    oils = [r for r in products if int(r["current_category_id"]) == INDUSTRIAL_OIL_CATEGORY_ID]
    approved_exec = [r for r in products if (r.get("approved_target_category_code") or "").strip()]
    return {
        "current_category_count": len(manifest_ids),
        "commerce_tree_nodes": len(tree),
        "commerce_l1_roots": len(roots),
        "depth_histogram": dict(sorted(depth_hist.items())),
        "inherited_from_current_category": len(inherited),
        "selectable_leaves": len(selectable),
        "live_product_rows": len(products),
        "product_level_decomposition_required": len(product_level_required),
        "product_decomposition_or_blocked_rows": len(decomp),
        "tx_owner_product_rows": len(tx),
        "category_156_product_rows": len(oils),
        "approved_executable_target_codes": len(approved_exec),
        "owner_journal_exits": sum(
            1 for j in inputs.owner_journal.values() if j["owner_decision"] == "APPROVE_CATALOG_EXIT"
        ),
        "owner_journal_evidence": sum(
            1 for j in inputs.owner_journal.values() if j["owner_decision"] == "REQUEST_MORE_EVIDENCE"
        ),
        "evidence_111_register_ids": len(inputs.evidence_111_ids),
    }


def build_architecture_review_matrix(
    inputs: B2Inputs,
    impact_ref: dict[int, CategoryProductImpactRef] | None = None,
) -> list[dict[str, str]]:
    impact_ref = impact_ref or build_category_product_impact_reference(inputs)
    tree_by_source = {
        r["source_current_category_id"]: r for r in inputs.commerce_tree if r.get("source_current_category_id")
    }

    rows: list[dict[str, str]] = []
    for m in sorted(inputs.manifest, key=lambda r: int(r["current_category_id"])):
        cid = int(m["current_category_id"])
        census = inputs.baseline_census.get(cid, {})
        tnode = tree_by_source.get(str(cid), {})
        direct = int(m.get("direct_product_count") or census.get("direct_product_count") or 0)
        descendant = int(m.get("descendant_product_count") or census.get("descendant_product_count") or 0)
        impact = impact_ref[cid]
        direct_unique = len(impact.direct_product_ids)
        descendant_unique = len(impact.descendant_inclusive_product_ids)
        descendant_unresolved = len(impact.descendant_inclusive_unresolved_product_ids)
        b2_disp = b2_recommended_disposition_category(m, cid)
        alt = ""
        if m.get("cct1_result") == "BETTER_AS_FACET":
            alt = "Retain 155 as importer-facing facet key until FLUIDS megamenu cutover (no 154 hub restore)"
        elif cid in {116, 117, 118}:
            alt = "Keep mixed staging leaf until SKU-level split evidence completes (no new catch-all hub)"
        elif cid == 154:
            alt = "Staged decomposition into domain-specific leaves without deleting category 154 identity"
        blocks_arch = "YES" if cid in HOLD_CATEGORY_IDS or cid == INDUSTRIAL_OIL_CATEGORY_ID else "NO"
        blocks_exec = "YES" if cid in TX_OWNER_SCOPE_CATEGORY_IDS or cid in {116, 117, 164} else "NO"
        homogeneity = "LOW" if cid in SENSITIVE_CATEGORY_IDS or descendant > direct else "MEDIUM"
        if cid in HOLD_CATEGORY_IDS and descendant > 100:
            homogeneity = "LOW"
        conf, conf_rationale = architecture_confidence(m, cid)
        rows.append(
            {
                "current_category_id": str(cid),
                "current_name": m["current_name"],
                "current_full_path": m["current_full_path"],
                "census_slug": census.get("slug", m.get("current_slug", "")),
                "scientific_domain_code": m.get("scientific_domain_code", ""),
                "published_kz_cat_code": m.get("published_kz_cat_code", ""),
                "staging_registry_code": m.get("staging_registry_code", ""),
                "commerce_parent_code": m.get("commerce_parent_code", "") or tnode.get("parent_commerce_code", ""),
                "commerce_tree_depth": m.get("commerce_tree_depth", "") or tnode.get("commerce_depth", ""),
                "node_classification": classify_node_kind(m),
                "b2_recommended_disposition": b2_disp,
                "owner_architecture_decision_status": owner_architecture_decision_status(m, cid),
                "tx_owner_001_documentary_status": tx_owner_documentary_status(m, cid),
                "apply_authorization_status": "NO",
                "buyer_intent_homogeneity": homogeneity,
                "alternative_disposition": alt,
                "classification_rationale": classification_rationale(m, cid),
                "confidence": conf,
                "confidence_rationale": conf_rationale,
                "evidence_sources": m.get("evidence_sources", "B1_MANIFEST"),
                "census_product_facts": "CONFIRMED_CENSUS",
                "b1_semantic_interpretation_evidence": census_semantic_evidence_label(m),
                "b2_architecture_interpretation_layer": b2_interpretation_layer(m, cid),
                "direct_live_product_count": str(direct),
                "descendant_live_product_count": str(descendant),
                "direct_distinct_product_ids_count": str(direct_unique),
                "descendant_inclusive_distinct_product_ids_count": str(descendant_unique),
                "descendant_inclusive_unresolved_product_ids_count": str(descendant_unresolved),
                "seo_redirect_proposal": m.get("seo_redirect_proposal", ""),
                "owner_explicit_decision_required": m.get("owner_steward_review_required", "NO"),
                "blocks_architecture_freeze": blocks_arch,
                "blocks_execution_release_gate": blocks_exec,
            }
        )
    return rows


def build_tree_disposition(inputs: B2Inputs) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for node in inputs.commerce_tree:
        code = node["commerce_category_code"]
        disp = tree_b2_recommended_disposition(node)
        if node.get("node_kind") == "BUYER_COMMERCE_L1":
            rationale = "Buyer L1 root: PROPOSED commerce identity — owner architecture freeze still PENDING."
        elif code in METROLOGY_L2_FAMILY_CODES:
            rationale = (
                "Metrology L2 family: B2 recommends structure but METROLOGY-L2-FAMILIES owner decision is PENDING."
            )
        elif code == "KZ.CAT.FLUIDS_INDUSTRIAL_OIL":
            rationale = (
                "27-oil cohort protected under FLUIDS; publication/identity freeze requires owner sign-off (not APPLY)."
            )
        elif disp == "FREEZE":
            rationale = "B1 tree edge consistent with manifest mapping; owner architecture decision still PENDING."
        else:
            rationale = "Sensitive, deprecated, or evidence-gated — hold until owner decision group resolved."
        rows.append(
            {
                "commerce_category_code": code,
                "parent_commerce_code": node.get("parent_commerce_code", ""),
                "commerce_depth": node["commerce_depth"],
                "scientific_domain_code": node.get("scientific_domain_code", ""),
                "name_en": node.get("name_en", ""),
                "name_fa": node.get("name_fa", ""),
                "commerce_is_selectable": node.get("commerce_is_selectable", ""),
                "node_kind": node.get("node_kind", ""),
                "source_current_category_id": node.get("source_current_category_id", ""),
                "b2_recommended_disposition": disp,
                "owner_architecture_decision_status": "PENDING",
                "apply_authorization_status": "NO",
                "rationale": rationale,
                "blocks_architecture_freeze": "YES"
                if node.get("node_kind") == "BUYER_COMMERCE_L1"
                or code in METROLOGY_L2_FAMILY_CODES
                or code == "KZ.CAT.FLUIDS_INDUSTRIAL_OIL"
                else "NO",
                "blocks_execution_release_gate": "NO",
            }
        )
    return rows


def build_grouped_owner_decisions(
    inputs: B2Inputs,
    impact_ref: dict[int, CategoryProductImpactRef] | None = None,
) -> list[dict[str, str]]:
    """Owner decision register — recommendations only; owner_architecture_decision_status always PENDING."""
    impact_ref = impact_ref or build_category_product_impact_reference(inputs)

    def _desc(cid: int) -> int:
        return len(impact_ref[cid].descendant_inclusive_product_ids)

    def _unres_desc(cid: int) -> int:
        return len(impact_ref[cid].descendant_inclusive_unresolved_product_ids)

    groups = [
        {
            "decision_group_id": "ARCH-7-L1-ROOTS",
            "freeze_tier": "A",
            "covers_hold_category_ids": "",
            "question_fa": "آیا هفت ریشه تجاری خریدار (مستقل از هفت دامنه علمی) به‌عنوان معماری نهایی پذیرفته شود؟",
            "b2_recommended_answer": "تأیید ساختار هفت L1 پیشنهادی B1 (بدون اجرای APPLY)",
            "alternative_answer": "بازنگری نام/مرز یک یا دو ریشه قبل از انجماد (مثلاً ادغام نمایشی Cutting/Toolholding)",
            "owner_architecture_decision_status": "PENDING",
            "affected_category_ids": "tree:L1×7",
            "affected_product_counts": "6536 کل کاتالوگ (ناوبری)",
            "navigation_consequence": "تعریف سفر خریدار و مگامنو",
            "blocks_architecture_freeze": "YES",
            "blocks_execution_release_gate": "NO",
            "owner_recorded_choice_field": "OWNER_ARCH_APPROVE_SEVEN_L1 | REVISE_L1 | DEFER",
        },
        {
            "decision_group_id": "METROLOGY-L2-FAMILIES",
            "freeze_tier": "A",
            "covers_hold_category_ids": "",
            "question_fa": "آیا تفکیک سه خانواده L2 اندازه‌گیری (دقیق / CNC / آزمایشگاهی) حفظ شود؟",
            "b2_recommended_answer": "حفظ سه METROLOGY_FAMILY_* تحت BUYER_METROLOGY",
            "alternative_answer": "دو خانواده (ادغام آزمایشگاهی با دقیق) با حفظ عمق ≤۳",
            "owner_architecture_decision_status": "PENDING",
            "affected_category_ids": "KZ.CAT.METROLOGY_FAMILY_PRECISION|CNC|LABORATORY",
            "affected_product_counts": "دامنه METROLOGY: ۴۲ دسته / ~۱۵۰۰+ SKU زیرمجموعه",
            "navigation_consequence": "ساختار PLP و فیلتر CNC vs دقیق",
            "blocks_architecture_freeze": "YES",
            "blocks_execution_release_gate": "NO",
            "owner_recorded_choice_field": "OWNER_ARCH_METROLOGY_L2_THREE | TWO_FAMILY | DEFER",
        },
        {
            "decision_group_id": "ACCESSORIES-154-DECOMPOSE",
            "freeze_tier": "B",
            "covers_hold_category_ids": "154",
            "question_fa": "هاب لوازم جانبی صنعتی (۱۵۴) چگونه بدون حذف دسته‌ای تجزیه شود؟",
            "b2_recommended_answer": "DECOMPOSE به برگ‌های دامنه‌محور؛ حفظ هویت ۱۵۴ به‌عنوان transitional تا پایان نقشه",
            "alternative_answer": "تمدید HOLD با مسیر انتشار مرحله‌ای (بدون 410 روی ۱۵۴)",
            "owner_architecture_decision_status": "PENDING",
            "affected_category_ids": "154",
            "affected_product_counts": f"direct=0 descendant_inclusive_distinct={_desc(154)} unresolved_desc={_unres_desc(154)}",
            "navigation_consequence": "حذف ناوبری اشتباه از L1 legacy",
            "blocks_architecture_freeze": "YES",
            "blocks_execution_release_gate": "YES",
            "owner_recorded_choice_field": "OWNER_ARCH_154_DECOMPOSE_PLAN | EXTEND_HOLD",
        },
        {
            "decision_group_id": "FLUIDS-155-FACET-NAV",
            "freeze_tier": "B",
            "covers_hold_category_ids": "155",
            "question_fa": "دسته ۱۵۵ (روغن و روانکار) در ناوبری FLUIDS چه نقشی داشته باشد؟",
            "b2_recommended_answer": "حذف هاب ۱۵۵ از درخت commerce؛ نمایش روغن‌ها فقط از L1 سیالات و برگ ۱۵۶",
            "alternative_answer": "نگه‌داری ۱۵۵ به‌عنوان facet غیرقابل‌انتخاب (نه برگ فروش) تا پایان ایمپورت",
            "owner_architecture_decision_status": "PENDING",
            "affected_category_ids": "155|156",
            "affected_product_counts": (
                f"155: descendant_inclusive_distinct={_desc(155)} | 156: direct={len(impact_ref[156].direct_product_ids)}"
            ),
            "navigation_consequence": "مرز facet در برابر دسته قابل‌انتخاب",
            "blocks_architecture_freeze": "YES",
            "blocks_execution_release_gate": "YES",
            "owner_recorded_choice_field": "OWNER_ARCH_155_RETIRE_FACET | KEEP_IMPORT_FACET",
        },
        {
            "decision_group_id": "FLUIDS-156-PUBLICATION",
            "freeze_tier": "B",
            "covers_hold_category_ids": "",
            "question_fa": "آیا هویت commerce KZ.CAT.FLUIDS_INDUSTRIAL_OIL برای ۲۷ روغن منتشر شود؟",
            "b2_recommended_answer": "تأیید برگ ۱۵۶ تحت BUYER_FLUIDS (کohort محافظت‌شده؛ بدون خروج کاتالوگ)",
            "alternative_answer": "تأخیر انتشار تا تکمیل مدرک برند/ایمپورت (cohort همچنان در FLUIDS)",
            "owner_architecture_decision_status": "PENDING",
            "affected_category_ids": "156",
            "affected_product_counts": "27 PRODUCT_LEVEL_REQUIRED (blocked APPLY)",
            "navigation_consequence": "مسیر خریدار سیالات صنعتی",
            "blocks_architecture_freeze": "YES",
            "blocks_execution_release_gate": "YES",
            "owner_recorded_choice_field": "OWNER_ARCH_156_PUBLISH | DEFER_PUBLICATION",
        },
        {
            "decision_group_id": "MACHINE-ACCESSORIES-163-164",
            "freeze_tier": "B",
            "covers_hold_category_ids": "163|164",
            "question_fa": "لوازم جانبی دستگاه (۱۶۳/۱۶۴) چگونه در MACHINES تجزیه شوند؟",
            "b2_recommended_answer": "تجزیه ۱۶۴ به برگ‌های تخصصی؛ ۱۶۳ transitional تا اتمام نقشه",
            "alternative_answer": "HOLD یکپارچه تا تکمیل مدارک ۸۰ SKU قلاویز‌زن",
            "owner_architecture_decision_status": "PENDING",
            "affected_category_ids": "163|164",
            "affected_product_counts": (
                f"163: descendant_inclusive_distinct={_desc(163)} | "
                f"164: direct={len(impact_ref[164].direct_product_ids)} "
                f"unresolved_desc={_unres_desc(164)}"
            ),
            "navigation_consequence": "جداسازی لوازم قلاویز‌زن از هاب ماشین",
            "blocks_architecture_freeze": "YES",
            "blocks_execution_release_gate": "YES",
            "owner_recorded_choice_field": "OWNER_ARCH_163_164_DECOMPOSE | EXTEND_HOLD",
        },
        {
            "decision_group_id": "TX-OWNER-SCOPE-157-160",
            "freeze_tier": "C",
            "covers_hold_category_ids": "157|158|159|160",
            "question_fa": "دامنه خروج سندی ابزار دستی/چوبی (۱۵۷–۱۶۰) در معماری commerce چگونه ثبت شود؟",
            "b2_recommended_answer": "حفظ DEPRECATED خارج از هفت دامنه؛ خروج سندی TX-OWNER ≠ APPLY",
            "alternative_answer": "توقف خروج برای SKU استثناء (فقط با ثبت مالک per-SKU)",
            "owner_architecture_decision_status": "PENDING",
            "affected_category_ids": "157|158|159|160",
            "affected_product_counts": "262 TX cohort (151 exit doc / 111 evidence)",
            "navigation_consequence": "عدم ایجاد Workshop/Hand Tools در دامنه علمی",
            "blocks_architecture_freeze": "YES",
            "blocks_execution_release_gate": "YES",
            "owner_recorded_choice_field": "OWNER_ARCH_CONFIRM_TX_DEPRECATION | REVIEW_EXCEPTIONS",
        },
        {
            "decision_group_id": "MIXED-CHUCKS-116-118",
            "freeze_tier": "C",
            "covers_hold_category_ids": "116|117|118",
            "question_fa": "برگ‌های mixed نظام تراش (۱۱۶–۱۱۸) چگونه تجزیه شوند؟",
            "b2_recommended_answer": "تجزیه PRODUCT_LEVEL: نظام vs لوازم جانبی پس از مدرک",
            "alternative_answer": "تمدید STAGING بدون برگ mixed جدید",
            "owner_architecture_decision_status": "PENDING",
            "affected_category_ids": "116|117|118",
            "affected_product_counts": "decomposition: 571|40|0",
            "navigation_consequence": "یکنواختی گیرش تراش",
            "blocks_architecture_freeze": "YES",
            "blocks_execution_release_gate": "YES",
            "owner_recorded_choice_field": "OWNER_ARCH_CHUCK_DECOMPOSE | EXTEND_STAGING",
        },
        {
            "decision_group_id": "HELICOIL-55-THREAD-REPAIR",
            "freeze_tier": "B",
            "covers_hold_category_ids": "",
            "question_fa": "دسته ۵۵ (هلی‌کویل) تحت THREAD_REPAIR بماند یا به Cutting بازگردد؟",
            "b2_recommended_answer": "THREAD_REPAIR + KZ.CAT.THREAD_REPAIR_HELICOIL_KITS (۲۹ SKU)",
            "alternative_answer": "برگ Cutting با حفظ دامنه THREAD_REPAIR برای کیت‌ها (دو مسیر ناوبری)",
            "owner_architecture_decision_status": "PENDING",
            "affected_category_ids": "55",
            "affected_product_counts": "29 live SKUs (IDs in E dossier)",
            "navigation_consequence": "جداسازی از قلاویز برشی",
            "blocks_architecture_freeze": "YES",
            "blocks_execution_release_gate": "NO",
            "owner_recorded_choice_field": "OWNER_ARCH_HELICOIL_THREAD_REPAIR | REVISE_PLACEMENT",
        },
        {
            "decision_group_id": "MEGAMENU-186-187-188",
            "freeze_tier": "D",
            "covers_hold_category_ids": "",
            "question_fa": "ارجاع منوی هلی‌کویل به شناسه‌های حذف‌شده ۱۸۶/۱۸۷/۱۸۸ چگونه اصلاح شود؟",
            "b2_recommended_answer": "به‌روزرسانی nav-group به cat 55 یا retire گروه",
            "alternative_answer": "صفحه راهنما موقت بدون 301 به هاب نامرتبط",
            "owner_architecture_decision_status": "PENDING",
            "affected_category_ids": "186|187|188|55",
            "affected_product_counts": "0 SKU on deprecated roots; 29 on 55",
            "navigation_consequence": "SEO/اجرای منو پس از انجماد معماری",
            "blocks_architecture_freeze": "NO",
            "blocks_execution_release_gate": "YES",
            "owner_recorded_choice_field": "OWNER_EXEC_MEGAMENU_HELICOIL_FIX | DEFER",
        },
    ]
    rows: list[dict[str, str]] = []
    for g in groups:
        rows.append(
            {
                **g,
                "traceability": (
                    f"B1:{B1_DIR.name};census:taxonomy-phase1b-baseline-2026-10-15;group={g['decision_group_id']}"
                ),
            }
        )
    return rows


def build_hold_category_decision_map(owner_groups: list[dict[str, str]]) -> list[dict[str, str]]:
    primary: dict[int, str] = {}
    for g in owner_groups:
        for cid in g.get("covers_hold_category_ids", "").split("|"):
            if cid.strip().isdigit():
                primary[int(cid)] = g["decision_group_id"]
    rows: list[dict[str, str]] = []
    for cid in sorted(HOLD_CATEGORY_IDS):
        rows.append(
            {
                "hold_category_id": str(cid),
                "decision_group_id": primary.get(cid, ""),
                "owner_architecture_decision_status": "PENDING",
            }
        )
        if cid not in primary:
            raise RuntimeError(f"HOLD category {cid} missing decision group mapping")
    return rows


def build_product_impact(inputs: B2Inputs) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in inputs.product_map:
        if not row["product_id"].isdigit():
            continue
        pid = int(row["product_id"])
        journal = inputs.owner_journal.get(pid, {})
        rows.append(
            {
                "product_id": str(pid),
                "sku": row.get("sku", ""),
                "current_category_id": row.get("current_category_id", ""),
                "mapping_mode": row.get("mapping_mode", ""),
                "target_category_candidate_code": row.get("target_category_candidate_code", ""),
                "approved_target_category_code": row.get("approved_target_category_code", ""),
                "mapping_authorization": row.get("mapping_authorization", ""),
                "owner_authoritative_decision": journal.get("owner_decision", row.get("owner_authoritative_decision", "")),
                "in_evidence_111_register": "YES" if pid in inputs.evidence_111_ids else "NO",
                "executable_in_b2": "NO",
                "notes": "B2 design-only; no APPLY",
            }
        )
    return rows


def build_sensitive_dossier(
    inputs: B2Inputs,
    impact_ref: dict[int, CategoryProductImpactRef] | None = None,
) -> list[dict[str, str]]:
    impact_ref = impact_ref or build_category_product_impact_reference(inputs)
    by_id = {int(r["current_category_id"]): r for r in inputs.manifest}
    mixed = {int(r["category_id"]): r for r in inputs.mixed_matrix}
    rows: list[dict[str, str]] = []
    for cid in sorted(SENSITIVE_CATEGORY_IDS):
        m = by_id[cid]
        mx = mixed.get(cid, {})
        imp = impact_ref[cid]
        rows.append(
            {
                "category_id": str(cid),
                "category_name": m["current_name"],
                "full_path": m["current_full_path"],
                "b1_identity_status": m.get("identity_status", ""),
                "published_code": m.get("published_kz_cat_code", ""),
                "structural_proposal": m.get("category_migration_action", ""),
                "product_ids": mx.get("product_ids_requiring_review", ""),
                "protected_cohort": mx.get("protected_cohort", ""),
                "direct_distinct_product_ids_count": str(len(imp.direct_product_ids)),
                "descendant_inclusive_distinct_product_ids_count": str(
                    len(imp.descendant_inclusive_product_ids)
                ),
                "descendant_inclusive_unresolved_product_ids_count": str(
                    len(imp.descendant_inclusive_unresolved_product_ids)
                ),
                "blanket_removal_blocked": mx.get("blanket_removal_blocked", "YES"),
                "owner_architecture_decision_status": "PENDING",
                "apply_authorization_status": "NO",
            }
        )
    helicoil_ids = "|".join(str(p) for p in HELICOIL_PRODUCT_IDS)
    rows.append(
        {
            "category_id": str(HELICOIL_CATEGORY_ID),
            "category_name": by_id[HELICOIL_CATEGORY_ID]["current_name"],
            "full_path": by_id[HELICOIL_CATEGORY_ID]["current_full_path"],
            "b1_identity_status": "PUBLISHED_PROPOSED",
            "published_code": by_id[HELICOIL_CATEGORY_ID].get("published_kz_cat_code", ""),
            "structural_proposal": "THREAD_REPAIR domain; historic 186/187/188 deprecated separately",
            "product_ids": helicoil_ids,
            "protected_cohort": "HELICOIL_29_EXACT",
            "direct_distinct_product_ids_count": str(len(impact_ref[HELICOIL_CATEGORY_ID].direct_product_ids)),
            "descendant_inclusive_distinct_product_ids_count": str(
                len(impact_ref[HELICOIL_CATEGORY_ID].descendant_inclusive_product_ids)
            ),
            "descendant_inclusive_unresolved_product_ids_count": str(
                len(impact_ref[HELICOIL_CATEGORY_ID].descendant_inclusive_unresolved_product_ids)
            ),
            "blanket_removal_blocked": "YES",
            "owner_architecture_decision_status": "PENDING",
            "apply_authorization_status": "NO",
        }
    )
    for hid, code in sorted(HISTORICAL_DEPRECATED_CODES.items()):
        rows.append(
            {
                "category_id": str(hid),
                "category_name": f"HISTORICAL_REMOVED_{hid}",
                "full_path": "REMOVED_FROM_LIVE_TREE",
                "b1_identity_status": "DEPRECATED_HISTORICAL",
                "published_code": code,
                "structural_proposal": "Do not recreate; no product deletion inferred",
                "product_ids": "",
                "protected_cohort": "MEGAMENU_DANGLING_REF",
                "blanket_removal_blocked": "YES",
                "owner_architecture_decision_status": "PENDING",
                "apply_authorization_status": "NO",
            }
        )
    return rows


def build_seo_dossier(inputs: B2Inputs) -> list[dict[str, str]]:
    f2 = json.loads((B1_DIR / "F2-IMPORTER-NUMERIC-DEPENDENCY-PROPOSAL.json").read_text(encoding="utf-8"))
    dep_rows = _read_csv(ROOT / f2["dependencies_csv"])
    importer_hits: dict[int, list[str]] = defaultdict(list)
    for d in dep_rows:
        if not d.get("numeric_id", "").isdigit():
            continue
        cid = int(d["numeric_id"])
        if d.get("runtime_relevance") in {"ACTIVE_SCRIPT", "FRONTEND_SOURCE"}:
            importer_hits[cid].append(d.get("file", ""))
    rows: list[dict[str, str]] = []
    for row in inputs.seo_rows:
        cid_s = row.get("current_category_id", "")
        hits = importer_hits.get(int(cid_s), []) if cid_s.isdigit() else []
        rows.append(
            {
                **row,
                "b2_execution_deferred": "YES",
                "auto_redirect_approved": "NO",
                "importer_script_hits": str(len(hits)),
                "importer_dependency_files": "|".join(sorted(set(hits))[:5]),
                "blocks_execution_release_gate": "YES" if cid_s in {"186", "187", "188", "55"} else "NO",
            }
        )
    return rows


def build_implementation_plan(inputs: B2Inputs) -> dict[str, Any]:
    f2 = json.loads((B1_DIR / "F2-IMPORTER-NUMERIC-DEPENDENCY-PROPOSAL.json").read_text(encoding="utf-8"))
    dep_rows = _read_csv(ROOT / f2["dependencies_csv"])
    taxonomy_ids = {
        int(r["numeric_id"])
        for r in dep_rows
        if r.get("resolved_live_category") and r.get("runtime_relevance") in {"ACTIVE_SCRIPT", "FRONTEND_SOURCE"}
    }
    return {
        "status": "PLAN_ONLY",
        "pinned_b1_importer_evidence": f2,
        "prerequisite_graph": [
            {
                "id": "P0_OWNER_ARCH_FREEZE",
                "depends_on": [],
                "verifies": ["C-GROUPED-OWNER-DECISION-REGISTER.csv", "C2-HOLD-CATEGORY-TO-DECISION-GROUP-MAP.csv"],
            },
            {
                "id": "P1_IDENTITY_REGISTRY",
                "depends_on": ["P0_OWNER_ARCH_FREEZE"],
                "verifies": ["B1/E-TARGET-IDENTITY-REGISTRY.csv", "KZ.CAT.* codes"],
            },
            {
                "id": "P2_PRODUCT_EVIDENCE",
                "depends_on": ["P0_OWNER_ARCH_FREEZE"],
                "verifies": ["111 evidence register", "718 decomposition rows"],
            },
            {
                "id": "P3_IMPORTER_REMAP",
                "depends_on": ["P1_IDENTITY_REGISTRY"],
                "verifies": [f2["dependencies_csv"], "numeric category_id hits"],
                "numeric_dependency_sample_count": len(taxonomy_ids),
            },
            {
                "id": "P4_APPLY_AUTHORIZATION",
                "depends_on": ["P2_PRODUCT_EVIDENCE", "P3_IMPORTER_REMAP"],
                "verifies": ["explicit OWNER APPLY gate — not in B2"],
            },
            {
                "id": "P5_SEO_REDIRECT_DEPLOY",
                "depends_on": ["P4_APPLY_AUTHORIZATION"],
                "verifies": ["F-SEO dossier", "no auto 301/410 in B2"],
            },
        ],
        "dependency_dimensions": {
            "category_identity": "current categories.id → proposed KZ.CAT.* (E-TARGET-IDENTITY-REGISTRY)",
            "product_mapping": "6536 rows D-PRODUCT-MAPPING-READINESS; 0 executable in B2",
            "megamenu": "nav_groups root_category_ids — see F dossier + helicoil dangling refs",
            "url_slug": "baseline census slugs; redirect proposals PROPOSED only",
            "importer_numeric_ids": sorted(taxonomy_ids),
            "backward_compatibility": "dual-read mapping table; rollback = revert mapping package",
        },
        "helicoil_megamenu": {
            "issue": "nav group references removed roots 186/187/188",
            "dangling_refs": [186, 187, 188],
            "proposal": "Retarget to category 55 or retire group; no unrelated 301",
            "blocks_execution_release_gate": "YES",
            "blocks_architecture_freeze": "NO",
        },
        "rollback": "Reversible mapping tables versioned per APPLY batch; B2 produces no runtime change",
    }


def build_owner_memo_fa(
    stats: dict[str, Any],
    disp_counts: Counter[str],
    owner_groups: list[dict[str, str]],
) -> str:
    lines = [
        "# یادداشت اجرایی تصمیم معماری — مسیر B2 (فاز ۱ب)",
        "",
        "**وضعیت:** `READY_FOR_OWNER_REVIEW` — این سند **تأیید مالک نیست**.",
        "",
        f"**ورودی B1 (ادغام PR #533):** `{PR533_MERGE_SHA}`",
        "",
        "## تفکیک وضعیت (اجباری)",
        "- **b2_recommended_*** = پیشنهاد تیم معماری برای بازبینی مالک.",
        "- **owner_architecture_decision_status** = همیشه `PENDING` تا ثبت صریح مالک.",
        "- **tx_owner_001_documentary** = مجوز خروج سندی (۱۵۱ SKU) ≠ APPLY.",
        "- **apply_authorization_status** = `NO` در تمام B2.",
        "",
        "## خلاصه کمی",
        f"- دسته‌های فعلی: {stats['current_category_count']}",
        f"- گره commerce: {stats['commerce_tree_nodes']} | عمق {stats['depth_histogram']}",
        f"- محصولات زنده: {stats['live_product_rows']}",
        f"- تجزیه PRODUCT_LEVEL_REQUIRED: {stats['product_level_decomposition_required']}",
        f"- TX-OWNER: {stats['owner_journal_exits']} خروج سندی / {stats['owner_journal_evidence']} مدرک باز",
        f"- روغن ۱۵۶: {stats['category_156_product_rows']} SKU محافظت‌شده",
        "",
        "## پیشنهاد B2 برای انجماد ساختاری (نه اجرا)",
        f"- FREEZE: {disp_counts.get('FREEZE', 0)} | HOLD: {disp_counts.get('HOLD', 0)} | REVISE: {disp_counts.get('REVISE', 0)}",
        f"- دسته‌های HOLD اجباری (۱۱): {sorted(HOLD_CATEGORY_IDS)}",
        "",
        "## سؤالات گروه‌بندی‌شده برای مالک",
    ]
    for i, g in enumerate(owner_groups, 1):
        lines.extend(
            [
                f"### {i}. {g['decision_group_id']} (سطح {g['freeze_tier']})",
                f"**سؤال:** {g['question_fa']}",
                f"**پیشنهاد B2:** {g['b2_recommended_answer']}",
                f"**گزینه دیگر:** {g['alternative_answer']}",
                f"**دامنه:** {g['affected_category_ids']} — {g['affected_product_counts']}",
                f"**اثر ناوبری:** {g['navigation_consequence']}",
                f"**بلوک انجماد معماری:** {g['blocks_architecture_freeze']} | **بلوک اجرا/انتشار:** {g['blocks_execution_release_gate']}",
                f"**ثبت انتخاب مالک:** `{g['owner_recorded_choice_field']}` (وضعیت فعلی: {g['owner_architecture_decision_status']})",
                "",
            ]
        )
    lines.extend(
        [
            "## یادآوری ایمنی",
            "`DESIGN_ONLY=YES` · `OWNER_DECISIONS_PENDING=YES` · بدون APPLY/SEO/تغییر production.",
            "",
            "ادغام PR در main به‌معنای تأیید معماری نیست.",
        ]
    )
    return "\n".join(lines)


def validate_b2_package(
    inputs: B2Inputs,
    invariants: dict[str, Any],
    arch_matrix: list[dict[str, str]],
    product_impact: list[dict[str, str]],
    *,
    tree_disposition: list[dict[str, str]] | None = None,
    owner_groups: list[dict[str, str]] | None = None,
    hold_category_map: list[dict[str, str]] | None = None,
    sensitive_dossier: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    if invariants["current_category_count"] != 135:
        errors.append("category_count")
    if invariants["commerce_tree_nodes"] != 123:
        errors.append("tree_nodes")
    if invariants["commerce_l1_roots"] != 7:
        errors.append("l1_roots")
    if invariants["depth_histogram"] != {1: 7, 2: 42, 3: 74}:
        errors.append(f"depth_histogram {invariants['depth_histogram']}")
    if invariants["live_product_rows"] != PHASE0B_ANCHOR["live_products"]:
        errors.append("live_products")
    if invariants["owner_journal_exits"] != 151 or invariants["owner_journal_evidence"] != 111:
        errors.append("owner_journal_counts")
    if invariants["evidence_111_register_ids"] != 111:
        errors.append("evidence_111_count")
    if invariants["category_156_product_rows"] != 27:
        errors.append("oil_count")
    if invariants["approved_executable_target_codes"] != 0:
        errors.append("executable_targets_present")
    if len(arch_matrix) != 135:
        errors.append("arch_matrix_rows")
    if len({int(r["current_category_id"]) for r in arch_matrix}) != 135:
        errors.append("arch_matrix_ids")
    for row in product_impact:
        if row.get("executable_in_b2") == "YES":
            errors.append("executable_flag")
            break
    if inputs.evidence_111_ids != {pid for pid, j in inputs.owner_journal.items() if j["owner_decision"] == "REQUEST_MORE_EVIDENCE"}:
        errors.append("evidence_111_set_mismatch_journal")

    b1_recon = json.loads((B1_DIR / "I-RECONCILIATION-REPORT.json").read_text(encoding="utf-8"))
    validation = validate_route_b_package(
        manifest=inputs.manifest,
        commerce_tree=inputs.commerce_tree,
        product_rows=inputs.product_map,
        identity_registry=_read_csv(B1_DIR / "E-TARGET-IDENTITY-REGISTRY.csv"),
        owner_journal=inputs.owner_journal,
        reconciliation=b1_recon["historical_reconciliation"],
        oil_product_ids=set(b1_recon["product_summary"]["category_156_oil_product_ids"]),
        inputs_products=_read_csv(BASELINE_DIR / "02-PRODUCT-CATEGORY-CENSUS.csv"),
    )
    if validation["status"] != "PASS":
        errors.append("b1_package_revalidation_failed")

    deliverable: dict[str, Any] = {"status": "SKIPPED"}
    if tree_disposition and owner_groups and hold_category_map and sensitive_dossier:
        from catalog_target.taxonomy_route_b2_deliverable_validation import validate_b2_deliverables

        b1_ids = {int(r["product_id"]) for r in inputs.product_map if r["product_id"].isdigit()}
        deliverable = validate_b2_deliverables(
            inputs=inputs,
            invariants=invariants,
            arch_matrix=arch_matrix,
            tree_disposition=tree_disposition,
            owner_groups=owner_groups,
            hold_category_map=hold_category_map,
            product_impact=product_impact,
            sensitive_dossier=sensitive_dossier,
            b1_product_ids=b1_ids,
        )
        if deliverable["status"] != "PASS":
            errors.extend(deliverable.get("errors", []))

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "b1_validation": validation,
        "b2_deliverable_validation": deliverable,
    }


def generate_b2_package(
    out_dir: Path,
    *,
    base_git_sha: str,
    generator_run_git_sha: str,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs = load_b2_inputs()
    invariants = recalculate_invariants(inputs)
    impact_ref = build_category_product_impact_reference(inputs)
    arch = build_architecture_review_matrix(inputs, impact_ref)
    tree_disp = build_tree_disposition(inputs)
    owner_groups = build_grouped_owner_decisions(inputs, impact_ref)
    hold_map = build_hold_category_decision_map(owner_groups)
    product_impact = build_product_impact(inputs)
    sensitive = build_sensitive_dossier(inputs, impact_ref)
    seo = build_seo_dossier(inputs)
    impl = build_implementation_plan(inputs)

    cat_disp = Counter(r["b2_recommended_disposition"] for r in arch)
    tree_disp_counts = Counter(r["b2_recommended_disposition"] for r in tree_disp)

    write_csv(
        out_dir / "A-135-ARCHITECTURE-REVIEW-MATRIX.csv",
        list(arch[0].keys()) if arch else [],
        arch,
    )
    write_csv(
        out_dir / "B-123-COMMERCE-TREE-DISPOSITION.csv",
        list(tree_disp[0].keys()) if tree_disp else [],
        tree_disp,
    )
    write_csv(
        out_dir / "C-GROUPED-OWNER-DECISION-REGISTER.csv",
        list(owner_groups[0].keys()) if owner_groups else [],
        owner_groups,
    )
    write_csv(
        out_dir / "C2-HOLD-CATEGORY-TO-DECISION-GROUP-MAP.csv",
        list(hold_map[0].keys()) if hold_map else [],
        hold_map,
    )
    write_csv(
        out_dir / "D-PRODUCT-IMPACT-RECONCILIATION.csv",
        list(product_impact[0].keys()) if product_impact else [],
        product_impact,
    )
    write_csv(
        out_dir / "E-SENSITIVE-CATEGORY-DOSSIER.csv",
        list(sensitive[0].keys()) if sensitive else [],
        sensitive,
    )
    write_csv(
        out_dir / "F-SEO-MEGAMENU-IMPORTER-DOSSIER.csv",
        list(seo[0].keys()) if seo else [],
        seo,
    )
    (out_dir / "G-IMPLEMENTATION-DEPENDENCY-PLAN.json").write_text(
        json.dumps(impl, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (out_dir / "H-OWNER-EXECUTIVE-DECISION-MEMO-FA.md").write_text(
        build_owner_memo_fa(invariants, cat_disp, owner_groups),
        encoding="utf-8",
    )

    validation = validate_b2_package(
        inputs,
        invariants,
        arch,
        product_impact,
        tree_disposition=tree_disp,
        owner_groups=owner_groups,
        hold_category_map=hold_map,
        sensitive_dossier=sensitive,
    )
    payload = {
        "base_git_sha": base_git_sha,
        "b1_merge_sha": PR533_MERGE_SHA,
        "b1_artifact_dir": str(B1_DIR.relative_to(ROOT)),
        "generator_run_git_sha": generator_run_git_sha,
        "invariants_recalculated": invariants,
        "category_disposition_counts": dict(cat_disp),
        "tree_disposition_counts": dict(tree_disp_counts),
        "hold_category_ids": sorted(HOLD_CATEGORY_IDS),
        "owner_decision_group_count": len(owner_groups),
        "decomposition_required_by_category": DECOMPOSITION_REQUIRED_BY_CATEGORY,
        "domain_summary": dict(Counter(r["scientific_domain_code"] for r in arch if r["scientific_domain_code"])),
        "validation": validation,
        "safety": {
            "DESIGN_ONLY": "YES",
            "OWNER_DECISIONS_PENDING": "YES",
            "PRODUCTION_MUTATION": "NO",
            "CATEGORY_APPLY": "NO",
        },
    }
    (out_dir / "I-B2-RECONCILIATION-REPORT.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    closeout = [
        "# Route B2 — validation closeout",
        "",
        f"**{validation['status']}**",
        "",
        json.dumps(validation, indent=2),
    ]
    (out_dir / "J-VALIDATION-CLOSEOUT-REPORT.md").write_text("\n".join(closeout), encoding="utf-8")
    (out_dir / "README.md").write_text(
        "\n".join(
            [
                "# Phase 1B Route B2 — Architecture Review",
                "",
                "Inputs: frozen B1 package under `audit/taxonomy-phase1b-route-b-target-design-2026-10-18/`.",
                "",
                "Owner HOLD coverage: `C2-HOLD-CATEGORY-TO-DECISION-GROUP-MAP.csv` (11 categories).",
                "",
                "```bash",
                "python3 scripts/audit_taxonomy_phase1b_route_b2_architecture_review.py",
                "```",
            ]
        ),
        encoding="utf-8",
    )
    artifacts = [
        "A-135-ARCHITECTURE-REVIEW-MATRIX.csv",
        "B-123-COMMERCE-TREE-DISPOSITION.csv",
        "C-GROUPED-OWNER-DECISION-REGISTER.csv",
        "C2-HOLD-CATEGORY-TO-DECISION-GROUP-MAP.csv",
        "D-PRODUCT-IMPACT-RECONCILIATION.csv",
        "E-SENSITIVE-CATEGORY-DOSSIER.csv",
        "F-SEO-MEGAMENU-IMPORTER-DOSSIER.csv",
        "G-IMPLEMENTATION-DEPENDENCY-PLAN.json",
        "H-OWNER-EXECUTIVE-DECISION-MEMO-FA.md",
        "I-B2-RECONCILIATION-REPORT.json",
        "J-VALIDATION-CLOSEOUT-REPORT.md",
        "README.md",
    ]
    write_sha256sums(out_dir, artifacts)
    if validation["status"] != "PASS":
        raise RuntimeError("B2_VALIDATION_FAILED: " + "; ".join(validation["errors"]))
    return payload
