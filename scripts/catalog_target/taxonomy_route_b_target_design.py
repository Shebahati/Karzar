"""Phase 1B Route B — exhaustive Current → Target taxonomy design (design-only, no APPLY)."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from catalog_target.taxonomy_phase1b_baseline import (
    CCT1_ALLOWED,
    MAX_CATEGORY_DEPTH,
    MIN_PRODUCT_CATEGORY_DEPTH,
    MIXED_SEMANTIC_PARENT_MARKERS,
    PHASE0B_ANCHOR,
    REMOVED_L1_HELICOIL_ROOT_IDS,
    TARGET_DOMAINS,
    TX_OWNER_SCOPE_CATEGORY_IDS,
    CategoryRow,
    compare_category_ids_phase0b,
    global_product_counts,
    helicoil_token_present,
    is_live_product,
    is_tx_owner_scope_category,
    mixed_semantic_parent,
    product_type_summary_for_category,
    sha256_file,
    write_csv,
    write_sha256sums,
)

ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = ROOT / "audit/taxonomy-phase1b-baseline-2026-10-15"
TX_OWNER_REVIEW = ROOT / "audit/taxonomy-phase1b-tx-owner-001-review/01-262-PRODUCT-SEMANTIC-REVIEW.csv"
EVIDENCE_RECON = (
    ROOT
    / "audit/taxonomy-phase1b-tx-owner-001-evidence-111-recovery-2026-10-18/06-RECONCILIATION.json"
)

DOMAIN_CODES = frozenset(d["code"] for d in TARGET_DOMAINS)
DOMAIN_ROOT_CAT: dict[str, str] = {
    "KZ.DOM.METROLOGY": "KZ.CAT.DOM_METROLOGY",
    "KZ.DOM.CUTTING": "KZ.CAT.DOM_CUTTING",
    "KZ.DOM.TOOLHOLDING": "KZ.CAT.DOM_TOOLHOLDING",
    "KZ.DOM.WORKHOLDING": "KZ.CAT.DOM_WORKHOLDING",
    "KZ.DOM.MACHINES": "KZ.CAT.DOM_MACHINES",
    "KZ.DOM.THREAD_REPAIR": "KZ.CAT.DOM_THREAD_REPAIR",
    "KZ.DOM.FLUIDS": "KZ.CAT.DOM_FLUIDS",
}

# Current live L1 category_id → engineering Domain (None = decompose per child).
L1_DOMAIN_MAP: dict[int, str] = {
    1: "KZ.DOM.TOOLHOLDING",
    2: "KZ.DOM.CUTTING",
    4: "KZ.DOM.CUTTING",
    5: "KZ.DOM.CUTTING",
    6: "KZ.DOM.CUTTING",
    8: "KZ.DOM.WORKHOLDING",
    9: "KZ.DOM.MACHINES",
    56: "KZ.DOM.METROLOGY",
    81: "KZ.DOM.METROLOGY",
    87: "KZ.DOM.METROLOGY",
    165: "KZ.DOM.CUTTING",
}

MIXED_SEMANTIC_CATEGORY_IDS = frozenset({116, 117, 118, 154, 155, 156, 157, 158, 159, 160, 163, 164})
HELICOIL_CATEGORY_ID = 55
INDUSTRIAL_OIL_CATEGORY_ID = 156
ACCESSORIES_L1_ID = 154

DEPRECATED_HISTORICAL_CODES: dict[int, str] = {
    186: "KZ.CAT.DEPRECATED_HELICOIL_L1_REMOVED",
    187: "KZ.CAT.DEPRECATED_HELICOIL_L1_REMOVED",
    188: "KZ.CAT.DEPRECATED_HELICOIL_L1_REMOVED",
}

MANIFEST_FIELDS: list[str] = [
    "current_category_id",
    "current_name",
    "current_slug",
    "current_full_path",
    "current_depth",
    "direct_product_count",
    "descendant_product_count",
    "engineering_semantic_interpretation",
    "cct1_result",
    "category_migration_action",
    "target_domain_code",
    "target_domain_name_en",
    "target_category_code",
    "target_parent_code",
    "target_tree_depth",
    "target_name_fa",
    "target_name_en",
    "target_is_selectable",
    "product_type_relationship",
    "product_decomposition_required",
    "decision_class",
    "confidence",
    "evidence_sources",
    "owner_steward_review_required",
    "migration_dependency",
    "seo_redirect_consequence",
    "notes",
]

PRODUCT_MAP_FIELDS: list[str] = [
    "product_id",
    "sku",
    "current_category_id",
    "current_category_path",
    "mapping_mode",
    "proposed_target_category_code",
    "proposed_target_domain_code",
    "tx_owner_cohort",
    "tx_owner_journal_disposition",
    "owner_review_required",
    "evidence_class",
    "notes",
]


@dataclass(frozen=True)
class RouteBInputs:
    category_rows: list[CategoryRow]
    products: list[dict[str, str]]
    by_id: dict[int, CategoryRow]
    parent_of: dict[int, int | None]
    tx_owner_review: dict[int, dict[str, str]]
    evidence_recon: dict[str, Any]


def load_baseline_categories() -> list[CategoryRow]:
    path = BASELINE_DIR / "01-CATEGORY-CENSUS.csv"
    rows: list[CategoryRow] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            rows.append(
                CategoryRow(
                    category_id=int(raw["category_id"]),
                    name=raw["name"],
                    slug=raw["slug"],
                    parent_id=int(raw["parent_id"]) if (raw.get("parent_id") or "").strip() else None,
                    parent_name=raw.get("parent_name") or "",
                    full_path=raw["full_path"],
                    depth=int(raw["depth"]),
                    is_leaf=raw["is_leaf"] in ("True", "true", "1"),
                    is_selectable=raw["is_selectable"] in ("True", "true", "1"),
                    child_count=int(raw.get("child_count") or 0),
                    megamenu_hidden=raw.get("megamenu_hidden") in ("True", "true", "1"),
                    megamenu_as_leaf=raw.get("megamenu_as_leaf") in ("True", "true", "1"),
                    hesabfa_category_code=raw.get("hesabfa_category_code") or "",
                    spec_template_key=raw.get("spec_template_key") or "",
                    direct_live=int(raw.get("direct_product_count") or 0),
                    descendant_live=int(raw.get("descendant_product_count") or 0),
                    active=int(raw.get("active_count") or 0),
                    available=int(raw.get("available_count") or 0),
                    priced=int(raw.get("priced_count") or 0),
                    imaged=int(raw.get("imaged_count") or 0),
                    visible=int(raw.get("visible_count") or 0),
                    sellable=int(raw.get("sellable_count") or 0),
                    pt_assigned=int(raw.get("product_type_assigned_count") or 0),
                    pt_missing=int(raw.get("product_type_missing_count") or 0),
                )
            )
    return rows


def load_baseline_products() -> list[dict[str, str]]:
    path = BASELINE_DIR / "02-PRODUCT-CATEGORY-CENSUS.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_tx_owner_review() -> dict[int, dict[str, str]]:
    out: dict[int, dict[str, str]] = {}
    if not TX_OWNER_REVIEW.is_file():
        return out
    with TX_OWNER_REVIEW.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            out[int(row["product_id"])] = row
    return out


def load_evidence_recon() -> dict[str, Any]:
    if not EVIDENCE_RECON.is_file():
        return {}
    return json.loads(EVIDENCE_RECON.read_text(encoding="utf-8"))


def l1_ancestor(category_id: int, parent_of: dict[int, int | None]) -> int:
    cur = category_id
    seen: set[int] = set()
    while cur in parent_of and parent_of[cur] is not None:
        if cur in seen:
            break
        seen.add(cur)
        cur = parent_of[cur]  # type: ignore[assignment]
    return cur


def slug_token(slug: str) -> str:
    token = re.sub(r"[^A-Z0-9]+", "_", slug.upper().replace("-", "_"))
    token = re.sub(r"_+", "_", token).strip("_")
    return token[:56] or "UNNAMED"


def en_name_from_slug(slug: str) -> str:
    return slug.replace("-", " ").replace("_", " ").title()


def domain_for_row(row: CategoryRow, parent_of: dict[int, int | None]) -> str | None:
    if row.category_id == HELICOIL_CATEGORY_ID:
        return "KZ.DOM.THREAD_REPAIR"
    if row.category_id in {155, 156} or row.parent_id in {155, 156}:
        return "KZ.DOM.FLUIDS"
    if is_tx_owner_scope_category(row.category_id) or row.parent_id in TX_OWNER_SCOPE_CATEGORY_IDS:
        return None
    if row.category_id == ACCESSORIES_L1_ID or (row.parent_id == ACCESSORIES_L1_ID and row.category_id not in {155, 156}):
        if row.category_id in TX_OWNER_SCOPE_CATEGORY_IDS or row.parent_id in {157, 159}:
            return None
    l1 = l1_ancestor(row.category_id, parent_of)
    if l1 == ACCESSORIES_L1_ID:
        if row.category_id in {155, 156}:
            return "KZ.DOM.FLUIDS"
        return None
    return L1_DOMAIN_MAP.get(l1)


def engineering_interpretation(row: CategoryRow, domain: str | None) -> str:
    if row.category_id == HELICOIL_CATEGORY_ID:
        return (
            "Thread repair / wire thread insert trade vocabulary (Helicoil); "
            "not generic indexable cutting insert semantics."
        )
    if row.category_id == INDUSTRIAL_OIL_CATEGORY_ID:
        return "Metalworking industrial lubricant SKUs (protected cohort; Fluids domain)."
    if is_tx_owner_scope_category(row.category_id):
        return "TX-OWNER-001 Workshop/Hand/Woodworking scope — Owner-approved catalog exit cohort."
    if row.category_id == ACCESSORIES_L1_ID:
        return "Mixed-semantics industrial accessories parent; decompose by descendant meaning."
    if row.category_id in MIXED_SEMANTIC_CATEGORY_IDS:
        return "Mixed-semantics commerce parent; product-level meaning required."
    if domain:
        return f"Buyer-facing hub under {domain} aligned with preserved production path."
    return "Requires decomposition or Owner evidence before domain assignment."


def cct1_for_row(row: CategoryRow, domain: str | None) -> str:
    if is_tx_owner_scope_category(row.category_id):
        return "DEPRECATE_REMOVE"
    if row.category_id in {157, 158, 159, 160}:
        return "DEPRECATE_REMOVE"
    if row.category_id == ACCESSORIES_L1_ID:
        return "NOT_ENOUGH_EVIDENCE"
    if row.category_id == 155:
        return "BETTER_AS_FACET"
    if row.category_id in MIXED_SEMANTIC_CATEGORY_IDS:
        if row.category_id == INDUSTRIAL_OIL_CATEGORY_ID:
            return "KEEP_AS_CATEGORY"
        return "NOT_ENOUGH_EVIDENCE"
    if row.depth == 1 and row.descendant_live == 0:
        return "DEPRECATE_REMOVE"
    if row.depth == 1 and not row.is_selectable:
        return "KEEP_AS_CATEGORY"
    if row.descendant_live == 0 and row.direct_live == 0:
        return "KEEP_AS_CATEGORY"
    return "KEEP_AS_CATEGORY"


def migration_action(row: CategoryRow, cct1: str) -> str:
    if cct1 == "DEPRECATE_REMOVE":
        return "DEPRECATE_REMOVE"
    if row.category_id in {154, 155, 163}:
        return "DECOMPOSE_HUB"
    if row.category_id in MIXED_SEMANTIC_CATEGORY_IDS - {156}:
        return "DECOMPOSE_OR_EVIDENCE_GATED"
    if row.depth == 1 and row.category_id not in {154}:
        return "RETIRE_LEGACY_L1_HUB"
    return "RETAIN_REHOME"


def decision_class(row: CategoryRow, cct1: str) -> str:
    if is_tx_owner_scope_category(row.category_id) or row.category_id in {157, 158, 159, 160}:
        return "OWNER_APPROVED"
    if row.category_id in MIXED_SEMANTIC_CATEGORY_IDS or row.category_id == ACCESSORIES_L1_ID:
        if row.category_id == INDUSTRIAL_OIL_CATEGORY_ID:
            return "PROPOSED"
        return "EVIDENCE_GATED"
    if row.category_id == HELICOIL_CATEGORY_ID:
        return "PROPOSED"
    return "PROPOSED"


def product_disposition_note(row: CategoryRow) -> str:
    if is_tx_owner_scope_category(row.category_id) or row.category_id in {158, 160}:
        return "CATALOG_EXIT"
    if row.category_id == INDUSTRIAL_OIL_CATEGORY_ID:
        return "RETAIN_REHOME"
    if row.category_id in {116, 117, 118, 164}:
        return "PRODUCT_LEVEL_REVIEW"
    return "CATEGORY_LEVEL_HYPOTHESIS"


def assign_target_codes(rows: list[CategoryRow]) -> dict[int, str]:
    used: set[str] = set(DOMAIN_ROOT_CAT.values())
    mapping: dict[int, str] = {}
    parent_of = {r.category_id: r.parent_id for r in rows}
    for row in sorted(rows, key=lambda r: r.category_id):
        domain = domain_for_row(row, parent_of)
        if cct1_for_row(row, domain) == "DEPRECATE_REMOVE" and is_tx_owner_scope_category(row.category_id):
            code = f"KZ.CAT.DEPRECATED_TX_OWNER_{row.category_id}"
        elif row.category_id in DEPRECATED_HISTORICAL_CODES:
            code = DEPRECATED_HISTORICAL_CODES[row.category_id]
        elif domain:
            dom_short = domain.replace("KZ.DOM.", "")
            code = f"KZ.CAT.{dom_short}_{slug_token(row.slug)}"
        else:
            code = f"KZ.CAT.UNRESOLVED_{row.category_id}"
        base = code
        n = 2
        while code in used:
            code = f"{base}_{n}"
            n += 1
        used.add(code)
        mapping[row.category_id] = code
    return mapping


def target_parent_code(
    row: CategoryRow,
    code_by_id: dict[int, str],
    parent_of: dict[int, int | None],
) -> str:
    if cct1_for_row(row, domain_for_row(row, parent_of)) == "DEPRECATE_REMOVE":
        return ""
    if row.category_id == ACCESSORIES_L1_ID:
        return ""
    domain = domain_for_row(row, parent_of)
    if domain is None:
        return ""
    if row.depth <= 1:
        return ""
    if row.depth == 2:
        return DOMAIN_ROOT_CAT[domain]
    pid = row.parent_id
    if pid is None:
        return DOMAIN_ROOT_CAT[domain]
    if pid == ACCESSORIES_L1_ID and row.category_id in {155, 156}:
        return DOMAIN_ROOT_CAT["KZ.DOM.FLUIDS"]
    if pid in code_by_id:
        return code_by_id[pid]
    return DOMAIN_ROOT_CAT[domain]


def target_depth(row: CategoryRow, parent_of: dict[int, int | None]) -> int:
    if row.depth == 1:
        return 1
    if row.depth == 2:
        return 2
    return 3


def build_manifest(inputs: RouteBInputs) -> list[dict[str, str]]:
    parent_of = {r.category_id: r.parent_id for r in inputs.category_rows}
    code_by_id = assign_target_codes(inputs.category_rows)
    domain_name = {d["code"]: d["en"] for d in TARGET_DOMAINS}
    manifest: list[dict[str, str]] = []
    for row in sorted(inputs.category_rows, key=lambda r: r.category_id):
        domain = domain_for_row(row, parent_of)
        cct1 = cct1_for_row(row, domain)
        action = migration_action(row, cct1)
        dclass = decision_class(row, cct1)
        tcode = code_by_id[row.category_id]
        tparent = target_parent_code(row, code_by_id, parent_of)
        tdepth = target_depth(row, parent_of)
        selectable = "YES" if row.is_selectable and cct1 != "DEPRECATE_REMOVE" else "NO"
        if row.category_id in {154, 155, 163}:
            selectable = "NO"
        pt_summary = product_type_summary_for_category(inputs.products, row.category_id)
        decomp = "YES" if row.category_id in MIXED_SEMANTIC_CATEGORY_IDS or row.category_id == ACCESSORIES_L1_ID else "NO"
        owner_review = "YES" if dclass in {"EVIDENCE_GATED", "OWNER_APPROVED"} or row.category_id in MIXED_SEMANTIC_CATEGORY_IDS else "NO"
        seo = "REDIRECT_REVIEW"
        if cct1 == "DEPRECATE_REMOVE":
            seo = "DEPRECATE_HUB_410_OR_STAGED_REDIRECT"
        elif action == "RETAIN_REHOME":
            seo = "SLUG_STABLE_PREFERRED"
        mig_dep = "PHASE1B_OWNER_REVIEW"
        if row.category_id == INDUSTRIAL_OIL_CATEGORY_ID:
            mig_dep = "NONE_PROTECTED_FLUIDS_COHORT"
        elif is_tx_owner_scope_category(row.category_id):
            mig_dep = "TX_OWNER_001_EXIT_EXECUTION_GATE"
        evidence = "PRESERVED_CENSUS_2026-10-15"
        if row.category_id in MIXED_SEMANTIC_CATEGORY_IDS:
            evidence += ";MIXED_SEMANTIC_COHORT"
        if row.category_id == HELICOIL_CATEGORY_ID:
            evidence += ";HELICOIL_THREAD_REPAIR_COHORT"
        manifest.append(
            {
                "current_category_id": str(row.category_id),
                "current_name": row.name,
                "current_slug": row.slug,
                "current_full_path": row.full_path,
                "current_depth": str(row.depth),
                "direct_product_count": str(row.direct_live),
                "descendant_product_count": str(row.descendant_live),
                "engineering_semantic_interpretation": engineering_interpretation(row, domain),
                "cct1_result": cct1,
                "category_migration_action": action,
                "target_domain_code": domain or "",
                "target_domain_name_en": domain_name.get(domain or "", ""),
                "target_category_code": tcode,
                "target_parent_code": tparent,
                "target_tree_depth": str(tdepth),
                "target_name_fa": row.name,
                "target_name_en": en_name_from_slug(row.slug),
                "target_is_selectable": selectable,
                "product_type_relationship": pt_summary or "PT_ASSIGNMENT_GAP",
                "product_decomposition_required": decomp,
                "decision_class": dclass,
                "confidence": "MEDIUM" if dclass == "PROPOSED" else "LOW",
                "evidence_sources": evidence,
                "owner_steward_review_required": owner_review,
                "migration_dependency": mig_dep,
                "seo_redirect_consequence": seo,
                "notes": product_disposition_note(row),
            }
        )
    return manifest


def build_target_tree(manifest: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for dom in TARGET_DOMAINS:
        code = DOMAIN_ROOT_CAT[dom["code"]]
        rows.append(
            {
                "target_category_code": code,
                "target_parent_code": "",
                "target_tree_depth": "1",
                "target_domain_code": dom["code"],
                "target_name_en": dom["en"],
                "target_name_fa": "",
                "target_is_selectable": "NO",
                "node_kind": "DOMAIN_COMMERCE_ROOT",
            }
        )
    for row in manifest:
        if row["cct1_result"] == "DEPRECATE_REMOVE" and row["decision_class"] == "OWNER_APPROVED":
            continue
        if not row["target_domain_code"]:
            continue
        rows.append(
            {
                "target_category_code": row["target_category_code"],
                "target_parent_code": row["target_parent_code"],
                "target_tree_depth": row["target_tree_depth"],
                "target_domain_code": row["target_domain_code"],
                "target_name_en": row["target_name_en"],
                "target_name_fa": row["target_name_fa"],
                "target_is_selectable": row["target_is_selectable"],
                "node_kind": "PROPOSED_COMMERCE_NODE",
                "source_current_category_id": row["current_category_id"],
            }
        )
    return rows


def build_historical_reconciliation(
    category_ids: set[int],
) -> dict[str, Any]:
    report = compare_category_ids_phase0b(repo_root=ROOT, current_category_ids=category_ids)
    historical_rows: list[dict[str, str]] = []
    phase0b_ids = set(report.get("removed_category_ids", [])) | category_ids
    for cid in sorted(phase0b_ids):
        if cid in category_ids:
            status = "CURRENT_LIVE"
        elif cid in REMOVED_L1_HELICOIL_ROOT_IDS:
            status = "REMOVED_EMPTY_HELICOIL_L1_ROOT"
        else:
            status = "REMOVED_OR_NEVER_LIVE"
        historical_rows.append(
            {
                "category_id": str(cid),
                "reconciliation_status": status,
                "deprecated_target_code": DEPRECATED_HISTORICAL_CODES.get(cid, ""),
                "product_deletion_inferred": "NO",
            }
        )
    report["historical_reconciliation_rows"] = historical_rows
    report["expected_removed_helicoil_roots"] = sorted(REMOVED_L1_HELICOIL_ROOT_IDS)
    return report


def build_product_mapping(
    inputs: RouteBInputs,
    manifest_by_id: dict[int, dict[str, str]],
) -> list[dict[str, str]]:
    open_evidence = inputs.evidence_recon.get("open_evidence_request_count", 111)
    documentary_exit = inputs.evidence_recon.get("documentary_exit_count_in_journals", 151)
    rows: list[dict[str, str]] = []
    for prod in inputs.products:
        if not is_live_product(prod):
            continue
        pid = int(prod["product_id"])
        cid = int(prod.get("category_id") or 0)
        review = inputs.tx_owner_review.get(pid, {})
        in_tx = pid in inputs.tx_owner_review
        man = manifest_by_id.get(cid, {})
        mode = "CATEGORY_HOMOGENEOUS_HYPOTHESIS"
        notes: list[str] = []
        if cid in MIXED_SEMANTIC_CATEGORY_IDS or cid == ACCESSORIES_L1_ID:
            mode = "PRODUCT_LEVEL_REQUIRED"
        if in_tx:
            mode = "TX_OWNER_001_FROZEN"
            notes.append("No rehome authorization from Route B")
        if is_tx_owner_scope_category(cid):
            notes.append("Owner-approved CATALOG_EXIT design only")
        target_code = man.get("target_category_code", "")
        if mode == "TX_OWNER_001_FROZEN":
            target_code = ""
        rows.append(
            {
                "product_id": str(pid),
                "sku": prod.get("sku") or "",
                "current_category_id": str(cid),
                "current_category_path": prod.get("category_full_path") or "",
                "mapping_mode": mode,
                "proposed_target_category_code": target_code,
                "proposed_target_domain_code": man.get("target_domain_code", ""),
                "tx_owner_cohort": "YES" if in_tx else "NO",
                "tx_owner_journal_disposition": review.get("proposed_disposition", ""),
                "owner_review_required": review.get("owner_review_required", "NO") if in_tx else "NO",
                "evidence_class": "PRODUCTION_CENSUS",
                "notes": " | ".join(notes),
            }
        )
    rows.append(
        {
            "product_id": "_SUMMARY_",
            "sku": "",
            "current_category_id": "",
            "current_category_path": "",
            "mapping_mode": "INTEGRITY",
            "proposed_target_category_code": "",
            "proposed_target_domain_code": "",
            "tx_owner_cohort": str(sum(1 for r in rows if r["tx_owner_cohort"] == "YES")),
            "tx_owner_journal_disposition": f"documentary_exit={documentary_exit};open_evidence={open_evidence}",
            "owner_review_required": "",
            "evidence_class": "TX_OWNER_001_RECON",
            "notes": "Counts exclude summary row",
        }
    )
    return rows


def build_identity_registry(manifest: list[dict[str, str]]) -> list[dict[str, str]]:
    reg: list[dict[str, str]] = []
    for dom in TARGET_DOMAINS:
        reg.append(
            {
                "code": DOMAIN_ROOT_CAT[dom["code"]],
                "entity": "commerce_category",
                "status": "PROPOSED",
                "deprecation_semantic": "NONE",
                "maps_from_current_category_id": "",
            }
        )
    for cid, code in DEPRECATED_HISTORICAL_CODES.items():
        reg.append(
            {
                "code": code,
                "entity": "commerce_category",
                "status": "DEPRECATED_HISTORICAL",
                "deprecation_semantic": "REMOVED_EMPTY_L1_NO_PRODUCTS",
                "maps_from_current_category_id": str(cid),
            }
        )
    for row in manifest:
        reg.append(
            {
                "code": row["target_category_code"],
                "entity": "commerce_category",
                "status": "DEPRECATED" if row["cct1_result"] == "DEPRECATE_REMOVE" else "PROPOSED",
                "deprecation_semantic": row["category_migration_action"],
                "maps_from_current_category_id": row["current_category_id"],
            }
        )
    return reg


def build_mixed_decomposition_matrix(
    inputs: RouteBInputs,
    manifest_by_id: dict[int, dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for cid in sorted(MIXED_SEMANTIC_CATEGORY_IDS):
        row = inputs.by_id.get(cid)
        if not row:
            continue
        man = manifest_by_id.get(cid, {})
        rows.append(
            {
                "category_id": str(cid),
                "category_name": row.name,
                "full_path": row.full_path,
                "direct_live_products": str(row.direct_live),
                "descendant_live_products": str(row.descendant_live),
                "decomposition_strategy": man.get("category_migration_action", ""),
                "cct1_result": man.get("cct1_result", ""),
                "product_level_review_required": man.get("product_decomposition_required", ""),
                "protected_cohort": "YES" if cid == INDUSTRIAL_OIL_CATEGORY_ID else "NO",
                "owner_scope": "YES" if is_tx_owner_scope_category(cid) else "NO",
            }
        )
    return rows


def build_unresolved_register(manifest: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in manifest:
        if row["decision_class"] == "EVIDENCE_GATED" or row["cct1_result"] == "NOT_ENOUGH_EVIDENCE":
            out.append(
                {
                    "current_category_id": row["current_category_id"],
                    "current_name": row["current_name"],
                    "issue": "MIXED_OR_ACCESSORY_DECOMPOSITION",
                    "required_action": "PRODUCT_LEVEL_STEWARD_REVIEW",
                    "blocking_migration": "YES",
                }
            )
    out.append(
        {
            "current_category_id": "TX_OWNER_001",
            "current_name": "262 SKU review cohort",
            "issue": "111_OPEN_EVIDENCE_REQUESTS",
            "required_action": "OWNER_EVIDENCE_COMPLETION_BEFORE_REHOME",
            "blocking_migration": "YES",
        }
    )
    return out


def validate_package(
    *,
    manifest: list[dict[str, str]],
    target_tree: list[dict[str, str]],
    product_rows: list[dict[str, str]],
    inputs: RouteBInputs,
    reconciliation: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    current_ids = {int(r["current_category_id"]) for r in manifest}
    if len(current_ids) != 135:
        errors.append(f"expected 135 categories got {len(current_ids)}")
    if len(manifest) != 135:
        errors.append("manifest row count != 135")
    manifest_codes = [r["target_category_code"] for r in manifest]
    if len(manifest_codes) != len(set(manifest_codes)):
        errors.append("duplicate KZ.CAT codes in manifest")
    tree_codes = [r["target_category_code"] for r in target_tree]
    if len(tree_codes) != len(set(tree_codes)):
        errors.append("duplicate KZ.CAT codes in target tree")
    domains = {r["target_domain_code"] for r in manifest if r["target_domain_code"]}
    if not domains.issubset(DOMAIN_CODES):
        errors.append("unknown target domain codes")
    if "KZ.DOM.WORKSHOP" in domains or any("WORKSHOP" in c for c in manifest_codes):
        errors.append("forbidden workshop domain/catch-all")
    depths = [int(r["target_tree_depth"]) for r in target_tree if r.get("target_tree_depth")]
    if max(depths, default=0) > MAX_CATEGORY_DEPTH:
        errors.append("target tree exceeds max depth")
    live_products = [p for p in inputs.products if is_live_product(p)]
    if len(live_products) != PHASE0B_ANCHOR["live_products"]:
        errors.append("live product census mismatch")
    oil_row = next((r for r in manifest if int(r["current_category_id"]) == INDUSTRIAL_OIL_CATEGORY_ID), None)
    if not oil_row or oil_row["target_domain_code"] != "KZ.DOM.FLUIDS":
        errors.append("category 156 fluids protection failed")
    if int(oil_row["direct_product_count"]) != 27:
        errors.append("category 156 must retain 27 products")
    tx_count = sum(1 for r in product_rows if r.get("tx_owner_cohort") == "YES" and r["product_id"] != "_SUMMARY_")
    if tx_count != 262:
        errors.append(f"tx_owner cohort expected 262 got {tx_count}")
    recon = inputs.evidence_recon
    if recon:
        if recon.get("open_evidence_request_count") != 111:
            errors.append("TX-OWNER open evidence count drift")
        if recon.get("documentary_exit_count_in_journals") != 151:
            errors.append("TX-OWNER documentary exit count drift")
    removed = set(reconciliation.get("removed_category_ids", []))
    if not REMOVED_L1_HELICOIL_ROOT_IDS.issubset(removed):
        errors.append("helicoil root reconciliation incomplete")
    for row in manifest:
        if row["cct1_result"] not in CCT1_ALLOWED:
            errors.append(f"invalid cct1 {row['current_category_id']}")
    if len(MIXED_SEMANTIC_CATEGORY_IDS) != 12:
        errors.append("mixed semantic cohort size drift")
    domain_roots_in_tree = sum(1 for r in target_tree if r.get("node_kind") == "DOMAIN_COMMERCE_ROOT")
    if domain_roots_in_tree != 7:
        errors.append("seven domain roots required in target tree")
    # Parent cycle check on proposed tree
    parent_map = {r["target_category_code"]: r.get("target_parent_code") or "" for r in target_tree}
    for code in parent_map:
        seen: set[str] = set()
        cur = code
        while parent_map.get(cur):
            if cur in seen:
                errors.append(f"cycle at {code}")
                break
            seen.add(cur)
            cur = parent_map[cur]
    status = "PASS" if not errors else "FAIL"
    return {"status": status, "errors": errors, "checks_run": True}


def generate_route_b_package(out_dir: Path, *, base_git_sha: str, head_git_sha: str) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    category_rows = load_baseline_categories()
    products = load_baseline_products()
    by_id = {r.category_id: r for r in category_rows}
    parent_of = {r.category_id: r.parent_id for r in category_rows}
    inputs = RouteBInputs(
        category_rows=category_rows,
        products=products,
        by_id=by_id,
        parent_of=parent_of,
        tx_owner_review=load_tx_owner_review(),
        evidence_recon=load_evidence_recon(),
    )
    manifest = build_manifest(inputs)
    manifest_by_id = {int(r["current_category_id"]): r for r in manifest}
    target_tree = build_target_tree(manifest)
    reconciliation = build_historical_reconciliation(set(by_id))
    product_map = build_product_mapping(inputs, manifest_by_id)
    identity_reg = build_identity_registry(manifest)
    unresolved = build_unresolved_register(manifest)

    write_csv(out_dir / "A-135-CURRENT-TARGET-MANIFEST.csv", MANIFEST_FIELDS, manifest)
    write_csv(
        out_dir / "B-HISTORICAL-138-TO-135-RECONCILIATION.csv",
        ["category_id", "reconciliation_status", "deprecated_target_code", "product_deletion_inferred"],
        reconciliation["historical_reconciliation_rows"],
    )
    write_csv(
        out_dir / "C-TARGET-TAXONOMY-TREE.csv",
        [
            "target_category_code",
            "target_parent_code",
            "target_tree_depth",
            "target_domain_code",
            "target_name_en",
            "target_name_fa",
            "target_is_selectable",
            "node_kind",
            "source_current_category_id",
        ],
        target_tree,
    )
    write_csv(out_dir / "D-PRODUCT-MAPPING-READINESS.csv", PRODUCT_MAP_FIELDS, product_map)
    mixed_matrix = build_mixed_decomposition_matrix(inputs, manifest_by_id)
    write_csv(
        out_dir / "D2-MIXED-CATEGORY-DECOMPOSITION-MATRIX.csv",
        [
            "category_id",
            "category_name",
            "full_path",
            "direct_live_products",
            "descendant_live_products",
            "decomposition_strategy",
            "cct1_result",
            "product_level_review_required",
            "protected_cohort",
            "owner_scope",
        ],
        mixed_matrix,
    )
    write_csv(
        out_dir / "E-TARGET-IDENTITY-REGISTRY.csv",
        ["code", "entity", "status", "deprecation_semantic", "maps_from_current_category_id"],
        identity_reg,
    )

    seo_path = BASELINE_DIR / "09-SEO-MEGAMENU-IMPACT-BASELINE.csv"
    seo_notes = {
        "helicoil_dangling_roots": sorted(REMOVED_L1_HELICOIL_ROOT_IDS),
        "megamenu_action": "Retarget helicoil nav group to live category 55 or retire; no unrelated redirects",
        "owner_scope_redirects": "Do not redirect Workshop/Hand/Woodworking hubs to industrial catch-alls",
    }
    megamenu_baseline = BASELINE_DIR / "11-MEGAMENU-REFERENTIAL-IMPACT.json"
    dep_summary = BASELINE_DIR / "08-NUMERIC-DEPENDENCY-SCAN-SUMMARY.json"
    (out_dir / "F-SEO-MEGAMENU-IMPORT-IMPACT.json").write_text(
        json.dumps(
            {
                "baseline_seo_csv": str(seo_path.relative_to(ROOT)),
                "baseline_megamenu_json": str(megamenu_baseline.relative_to(ROOT)),
                "numeric_dependency_summary": json.loads(dep_summary.read_text(encoding="utf-8"))
                if dep_summary.is_file()
                else {},
                "importer_remap_design": {
                    "wave": "Phase 1B design",
                    "semantic_key": "KZ.CAT.*",
                    "runtime_key": "categories.id (internal only)",
                    "mapping_table": "E-TARGET-IDENTITY-REGISTRY.csv",
                    "forbid": "bare integer category_id as import semantic key (governance)",
                },
                "proposed_redirect_policy": seo_notes,
                "manifest_redirect_fields": dict(Counter(r["seo_redirect_consequence"] for r in manifest)),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    write_csv(
        out_dir / "G-UNRESOLVED-DECISION-REGISTER.csv",
        ["current_category_id", "current_name", "issue", "required_action", "blocking_migration"],
        unresolved,
    )

    fa_lines = [
        "# یادداشت اجرایی مالک — فاز ۱ب مسیر B",
        "",
        "## وضعیت",
        "READY_FOR_OWNER_REVIEW — طراحی فقط؛ بدون APPLY.",
        "",
        f"## پایه و هدف Git",
        f"- BASE: `{base_git_sha}`",
        f"- HEAD: `{head_git_sha}`",
        "",
        "## خلاصه درخت",
        "- هفت دامنه هدف (بدون ابزار دستی/کارگاهی).",
        "- ۱۳۵ دسته فعلی با مانیفست یک‌به‌یک.",
        "- دسته ۱۵۶ (۲۷ روغن صنعتی) تحت سیالات فلزکاری.",
        "- هلی‌کویل (۵۵) تحت تعمیر رزوه؛ ریشه‌های ۱۸۶/۱۸۷/۱۸۸ حذف تاریخی بدون حذف محصول.",
        "- محدوده TX-OWNER-001 (۱۵۷–۱۶۰): خروج از کاتالوگ — تصمیم مالک، بدون اجرا.",
        "",
        "## شمارش",
        f"- محصولات زنده: {PHASE0B_ANCHOR['live_products']}",
        f"- کدهای هدف پیشنهادی: {len({r['target_category_code'] for r in manifest})}",
        "",
    ]
    (out_dir / "H-OWNER-EXECUTIVE-MEMO-FA.md").write_text("\n".join(fa_lines), encoding="utf-8")

    validation = validate_package(
        manifest=manifest,
        target_tree=target_tree,
        product_rows=product_map,
        inputs=inputs,
        reconciliation=reconciliation,
    )
    recon_payload = {
        "base_git_sha": base_git_sha,
        "head_git_sha": head_git_sha,
        "category_manifest_rows": len(manifest),
        "target_tree_nodes": len(target_tree),
        "product_mapping_rows": len([r for r in product_map if r["product_id"] != "_SUMMARY_"]),
        "global_product_counts": global_product_counts(products),
        "historical_reconciliation": reconciliation,
        "validation": validation,
        "zero_mutation": {
            "RESEARCH_AND_DESIGN_ONLY": "YES",
            "PRODUCTION_MUTATION": "NO",
            "CATEGORY_APPLY": "NO",
            "PRODUCT_REASSIGNMENT": "NO",
        },
    }
    (out_dir / "I-RECONCILIATION-REPORT.json").write_text(
        json.dumps(recon_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    artifact_names = [
        "A-135-CURRENT-TARGET-MANIFEST.csv",
        "B-HISTORICAL-138-TO-135-RECONCILIATION.csv",
        "C-TARGET-TAXONOMY-TREE.csv",
        "D-PRODUCT-MAPPING-READINESS.csv",
        "D2-MIXED-CATEGORY-DECOMPOSITION-MATRIX.csv",
        "E-TARGET-IDENTITY-REGISTRY.csv",
        "F-SEO-MEGAMENU-IMPORT-IMPACT.json",
        "G-UNRESOLVED-DECISION-REGISTER.csv",
        "H-OWNER-EXECUTIVE-MEMO-FA.md",
        "I-RECONCILIATION-REPORT.json",
        "FINAL_REPORT.md",
        "README.md",
    ]
    readme = [
        "# Phase 1B Route B — Target Taxonomy Design",
        "",
        "Design-only package. Regenerate:",
        "",
        "```bash",
        "python3 scripts/audit_taxonomy_phase1b_route_b_target_design.py",
        "```",
        "",
        f"Baseline census: `{BASELINE_DIR.relative_to(ROOT)}` (immutable).",
    ]
    (out_dir / "README.md").write_text("\n".join(readme), encoding="utf-8")
    final = [
        "# Phase 1B Route B — FINAL REPORT",
        "",
        f"Validation: **{validation['status']}**",
        "",
        json.dumps(validation, indent=2),
    ]
    (out_dir / "FINAL_REPORT.md").write_text("\n".join(final), encoding="utf-8")
    write_sha256sums(out_dir, artifact_names)
    if validation["status"] != "PASS":
        raise RuntimeError("ROUTE_B_VALIDATION_FAILED: " + "; ".join(validation["errors"]))
    return recon_payload
