"""Phase 1B Route B — target taxonomy design (design-only, fail-closed validation)."""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from catalog_target.taxonomy_phase1b_baseline import (
    PHASE0B_ANCHOR,
    TARGET_DOMAINS,
    TX_OWNER_SCOPE_CATEGORY_IDS,
    CategoryRow,
    compare_category_ids_phase0b,
    global_product_counts,
    is_live_product,
    is_tx_owner_scope_category,
    mixed_semantic_parent,
    product_type_summary_for_category,
    write_csv,
    write_sha256sums,
)
from catalog_target.taxonomy_route_b_semantics import (
    BUYER_COMMERCE_L1,
    HISTORICAL_DEPRECATED_CODES,
    METROLOGY_FAMILY,
    METROLOGY_FAMILY_META,
    MIXED_STAGING_CODES,
    OWNER_DEPRECATED_CODES,
    TRANSITIONAL_HUB_CODES,
    buyer_l1_for_domain,
    commerce_parent_for,
    load_category_semantics,
    l1_ancestor,
    registry_code_for_category,
    scientific_domain_for,
)
from catalog_target.taxonomy_route_b_validation import validate_route_b_package

ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = ROOT / "audit/taxonomy-phase1b-baseline-2026-10-15"
OWNER_PKG = ROOT / "audit/taxonomy-phase1b-tx-owner-001-owner-decision-package"
TX_OWNER_REVIEW = ROOT / "audit/taxonomy-phase1b-tx-owner-001-review/01-262-PRODUCT-SEMANTIC-REVIEW.csv"
EVIDENCE_111_REGISTER = (
    ROOT
    / "audit/taxonomy-phase1b-tx-owner-001-evidence-111-action-2026-10-18"
    / "01-EXACT-111-OPEN-EVIDENCE-ACTION-REGISTER.csv"
)
EVIDENCE_RECON = (
    ROOT
    / "audit/taxonomy-phase1b-tx-owner-001-evidence-111-recovery-2026-10-18/06-RECONCILIATION.json"
)

MIXED_SEMANTIC_CATEGORY_IDS = frozenset({116, 117, 118, 154, 155, 156, 157, 158, 159, 160, 163, 164})
HELICOIL_CATEGORY_ID = 55
INDUSTRIAL_OIL_CATEGORY_ID = 156
ACCESSORIES_L1_ID = 154

MANIFEST_FIELDS = [
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
    "scientific_domain_code",
    "scientific_domain_name_en",
    "identity_status",
    "published_kz_cat_code",
    "staging_registry_code",
    "commerce_parent_code",
    "commerce_tree_depth",
    "target_name_fa",
    "target_name_en",
    "commerce_is_selectable",
    "product_type_relationship",
    "product_decomposition_required",
    "decision_class",
    "confidence",
    "evidence_sources",
    "owner_steward_review_required",
    "migration_dependency",
    "seo_redirect_proposal",
    "notes",
]

PRODUCT_MAP_FIELDS = [
    "product_id",
    "sku",
    "current_category_id",
    "current_category_path",
    "mapping_mode",
    "suggested_scientific_domain_code",
    "target_category_candidate_code",
    "approved_target_category_code",
    "mapping_authorization",
    "tx_owner_cohort",
    "owner_authoritative_decision",
    "owner_decision_batch",
    "historical_pr499_proposal",
    "apply_authorization",
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
    owner_journal: dict[int, dict[str, str]]
    pr499_review: dict[int, dict[str, str]]
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
    with (BASELINE_DIR / "02-PRODUCT-CATEGORY-CENSUS.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_owner_authorization_journals() -> dict[int, dict[str, str]]:
    out: dict[int, dict[str, str]] = {}
    for path in sorted(OWNER_PKG.glob("OWNER-AUTHORIZATION-BATCH-*-2026-10-1*.csv")):
        match = re.search(r"BATCH-(\d+)", path.name)
        batch = match.group(1) if match else ""
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                pid = int(row["product_id"])
                out[pid] = {
                    "owner_decision": row.get("owner_decision", row.get("owner_response", "")).strip(),
                    "owner_decision_batch": batch,
                    "historical_pr499_proposal": row.get("historical_pr499_proposal", "").strip(),
                    "apply_authorization": row.get("apply_authorization", "NO").strip(),
                    "authorization_status": row.get("authorization_status", "").strip(),
                    "source_journal": str(path.relative_to(ROOT)),
                }
    return out


def load_pr499_review() -> dict[int, dict[str, str]]:
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


def cct1_for_row(row: CategoryRow, domain: str | None) -> str:
    if is_tx_owner_scope_category(row.category_id):
        return "DEPRECATE_REMOVE"
    if row.category_id == ACCESSORIES_L1_ID:
        return "NOT_ENOUGH_EVIDENCE"
    if row.category_id == 155:
        return "BETTER_AS_FACET"
    if row.category_id in MIXED_SEMANTIC_CATEGORY_IDS:
        if row.category_id == INDUSTRIAL_OIL_CATEGORY_ID:
            return "KEEP_AS_CATEGORY"
        return "NOT_ENOUGH_EVIDENCE"
    if row.depth == 1:
        return "KEEP_AS_CATEGORY" if row.descendant_live else "DEPRECATE_REMOVE"
    return "KEEP_AS_CATEGORY"


def migration_action(row: CategoryRow, cct1: str) -> str:
    if cct1 == "DEPRECATE_REMOVE":
        return "DEPRECATE_REMOVE"
    if row.category_id in {154, 155, 163}:
        return "DECOMPOSE_HUB"
    if row.category_id in MIXED_SEMANTIC_CATEGORY_IDS - {156}:
        return "DECOMPOSE_OR_EVIDENCE_GATED"
    if row.depth == 1:
        return "RETIRE_LEGACY_L1_HUB"
    return "RETAIN_REHOME"


def decision_class(row: CategoryRow) -> str:
    if is_tx_owner_scope_category(row.category_id):
        return "OWNER_APPROVED"
    if row.category_id in MIXED_SEMANTIC_CATEGORY_IDS or row.category_id == ACCESSORIES_L1_ID:
        return "EVIDENCE_GATED" if row.category_id != INDUSTRIAL_OIL_CATEGORY_ID else "PROPOSED"
    return "PROPOSED"


def build_manifest(inputs: RouteBInputs) -> list[dict[str, str]]:
    semantics = load_category_semantics()
    domain_name = {d["code"]: d["en"] for d in TARGET_DOMAINS}
    manifest: list[dict[str, str]] = []
    for row in sorted(inputs.category_rows, key=lambda r: r.category_id):
        domain = scientific_domain_for(row, inputs.parent_of)
        sem = semantics[row.category_id]
        cct1 = cct1_for_row(row, domain)
        action = migration_action(row, cct1)
        reg_code, identity_status = registry_code_for_category(row)
        published = sem.kz_cat_code if identity_status == "PUBLISHED_PROPOSED" else ""
        staging = reg_code if identity_status != "PUBLISHED_PROPOSED" else ""
        parent_code, depth = commerce_parent_for(row, inputs.parent_of, semantics)
        selectable = "YES" if sem.publish_in_commerce_tree and row.is_selectable else "NO"
        seo = "UNCHANGED_PATH"
        if identity_status.startswith("DEPRECATED"):
            seo = "PROPOSED_410_OR_DEFER"
        elif action == "RETIRE_LEGACY_L1_HUB":
            seo = "PROPOSED_301_TO_CHILDREN"
        elif identity_status == "PUBLISHED_PROPOSED" and parent_code:
            seo = "PROPOSED_301_IF_SLUG_CHANGE"
        elif row.category_id in MIXED_SEMANTIC_CATEGORY_IDS:
            seo = "DEFER_PRODUCT_LEVEL"
        manifest.append(
            {
                "current_category_id": str(row.category_id),
                "current_name": row.name,
                "current_slug": row.slug,
                "current_full_path": row.full_path,
                "current_depth": str(row.depth),
                "direct_product_count": str(row.direct_live),
                "descendant_product_count": str(row.descendant_live),
                "engineering_semantic_interpretation": sem.design_note or sem.name_en,
                "cct1_result": cct1,
                "category_migration_action": action,
                "scientific_domain_code": domain or "",
                "scientific_domain_name_en": domain_name.get(domain or "", ""),
                "identity_status": identity_status,
                "published_kz_cat_code": published,
                "staging_registry_code": staging,
                "commerce_parent_code": parent_code,
                "commerce_tree_depth": str(depth) if depth else "",
                "target_name_fa": row.name,
                "target_name_en": sem.name_en,
                "commerce_is_selectable": selectable,
                "product_type_relationship": product_type_summary_for_category(inputs.products, row.category_id)
                or "PT_ASSIGNMENT_GAP",
                "product_decomposition_required": "YES"
                if row.category_id in MIXED_SEMANTIC_CATEGORY_IDS or row.category_id == ACCESSORIES_L1_ID
                else "NO",
                "decision_class": decision_class(row),
                "confidence": "MEDIUM",
                "evidence_sources": "PRESERVED_CENSUS_2026-10-15;route_b_semantics_v2",
                "owner_steward_review_required": "YES"
                if row.category_id in MIXED_SEMANTIC_CATEGORY_IDS or is_tx_owner_scope_category(row.category_id)
                else "NO",
                "migration_dependency": "TX_OWNER_001_EXIT_EXECUTION_GATE"
                if is_tx_owner_scope_category(row.category_id)
                else "PHASE1B_OWNER_REVIEW",
                "seo_redirect_proposal": seo,
                "notes": sem.design_note,
            }
        )
    return manifest


def build_commerce_tree(
    inputs: RouteBInputs,
    manifest_by_id: dict[int, dict[str, str]],
) -> list[dict[str, str]]:
    semantics = load_category_semantics()
    nodes: dict[str, dict[str, str]] = {}

    for code, (domain, en, fa) in BUYER_COMMERCE_L1.items():
        nodes[code] = {
            "commerce_category_code": code,
            "parent_commerce_code": "",
            "commerce_depth": "1",
            "scientific_domain_code": domain,
            "name_en": en,
            "name_fa": fa,
            "commerce_is_selectable": "NO",
            "node_kind": "BUYER_COMMERCE_L1",
            "source_current_category_id": "",
        }

    for fam_code, (domain, en, fa) in METROLOGY_FAMILY_META.items():
        buyer = buyer_l1_for_domain(domain)
        nodes[fam_code] = {
            "commerce_category_code": fam_code,
            "parent_commerce_code": buyer or "",
            "commerce_depth": "2",
            "scientific_domain_code": domain,
            "name_en": en,
            "name_fa": fa,
            "commerce_is_selectable": "NO",
            "node_kind": "BUYER_COMMERCE_L2_FAMILY",
            "source_current_category_id": "",
        }

    for row in inputs.category_rows:
        sem = semantics[row.category_id]
        if not sem.publish_in_commerce_tree or not sem.kz_cat_code:
            continue
        man = manifest_by_id[row.category_id]
        parent, depth = commerce_parent_for(row, inputs.parent_of, semantics)
        nodes[sem.kz_cat_code] = {
            "commerce_category_code": sem.kz_cat_code,
            "parent_commerce_code": parent,
            "commerce_depth": str(depth),
            "scientific_domain_code": man["scientific_domain_code"],
            "name_en": sem.name_en,
            "name_fa": row.name,
            "commerce_is_selectable": man["commerce_is_selectable"],
            "node_kind": "BUYER_COMMERCE_PUBLISHABLE",
            "source_current_category_id": str(row.category_id),
        }

    return sorted(nodes.values(), key=lambda r: r["commerce_category_code"])


def build_historical_reconciliation(category_ids: set[int]) -> dict[str, Any]:
    report = compare_category_ids_phase0b(repo_root=ROOT, current_category_ids=category_ids)
    rows: list[dict[str, str]] = []
    all_ids = category_ids | set(HISTORICAL_DEPRECATED_CODES)
    for cid in sorted(all_ids):
        if cid in category_ids:
            status = "CURRENT_LIVE"
        elif cid in HISTORICAL_DEPRECATED_CODES:
            status = "REMOVED_EMPTY_HELICOIL_L1_ROOT"
        else:
            status = "UNKNOWN"
        rows.append(
            {
                "category_id": str(cid),
                "reconciliation_status": status,
                "deprecated_registry_code": HISTORICAL_DEPRECATED_CODES.get(cid, ""),
                "product_deletion_inferred": "NO",
            }
        )
    report["historical_reconciliation_rows"] = rows
    return report


def products_by_category(products: list[dict[str, str]]) -> dict[int, list[int]]:
    out: dict[int, list[int]] = defaultdict(list)
    for p in products:
        if not is_live_product(p):
            continue
        cid = int(p.get("category_id") or 0)
        out[cid].append(int(p["product_id"]))
    return out


def build_product_mapping(
    inputs: RouteBInputs,
    manifest_by_id: dict[int, dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    mixed_ids = MIXED_SEMANTIC_CATEGORY_IDS | {ACCESSORIES_L1_ID}
    for prod in inputs.products:
        if not is_live_product(prod):
            continue
        pid = int(prod["product_id"])
        cid = int(prod.get("category_id") or 0)
        man = manifest_by_id.get(cid, {})
        journal = inputs.owner_journal.get(pid, {})
        pr499 = inputs.pr499_review.get(pid, {})
        in_tx = pid in inputs.owner_journal

        mode = "CATEGORY_HOMOGENEOUS_HYPOTHESIS"
        mapping_auth = "DESIGN_CANDIDATE_ONLY"
        candidate = ""
        approved = ""
        owner_review = "NO"
        suggested_domain = man.get("scientific_domain_code", "")

        if cid in mixed_ids:
            mode = "PRODUCT_LEVEL_REQUIRED"
            mapping_auth = "BLOCKED_PENDING_DECOMPOSITION"
            owner_review = "YES"
        if in_tx:
            mode = "TX_OWNER_001_FROZEN"
            od = journal.get("owner_decision", "")
            if od == "REQUEST_MORE_EVIDENCE":
                mapping_auth = "BLOCKED_EVIDENCE_PENDING"
            elif od == "APPROVE_CATALOG_EXIT":
                mapping_auth = "BLOCKED_DOCUMENTARY_EXIT_NO_APPLY"
            suggested_domain = ""
            candidate = ""
        elif man.get("identity_status") == "PUBLISHED_PROPOSED" and cid not in mixed_ids:
            candidate = man.get("published_kz_cat_code", "")
            if man.get("product_decomposition_required") == "NO":
                mode = "CATEGORY_LEVEL_CANDIDATE"

        rows.append(
            {
                "product_id": str(pid),
                "sku": prod.get("sku") or "",
                "current_category_id": str(cid),
                "current_category_path": prod.get("category_full_path") or "",
                "mapping_mode": mode,
                "suggested_scientific_domain_code": suggested_domain,
                "target_category_candidate_code": candidate,
                "approved_target_category_code": approved,
                "mapping_authorization": mapping_auth,
                "tx_owner_cohort": "YES" if in_tx else "NO",
                "owner_authoritative_decision": journal.get("owner_decision", ""),
                "owner_decision_batch": journal.get("owner_decision_batch", ""),
                "historical_pr499_proposal": pr499.get("proposed_disposition", "")
                or journal.get("historical_pr499_proposal", ""),
                "apply_authorization": journal.get("apply_authorization", "NO"),
                "owner_review_required": owner_review,
                "evidence_class": "PRODUCTION_CENSUS",
                "notes": "No execution authorization from Route B",
            }
        )
    return rows


def build_mixed_decomposition(
    inputs: RouteBInputs,
    manifest_by_id: dict[int, dict[str, str]],
    by_cat_products: dict[int, list[int]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for cid in sorted(MIXED_SEMANTIC_CATEGORY_IDS | {ACCESSORIES_L1_ID}):
        row = inputs.by_id[cid]
        man = manifest_by_id[cid]
        pids = sorted(by_cat_products.get(cid, []))
        homogeneous = "NO"
        protected = "NO"
        destination = ""
        if cid == INDUSTRIAL_OIL_CATEGORY_ID:
            homogeneous = "YES"
            protected = "YES_PROTECTED_27"
            destination = man.get("published_kz_cat_code", "")
        elif cid in TX_OWNER_SCOPE_CATEGORY_IDS or cid in {158, 160}:
            destination = "CATALOG_EXIT_OWNER_APPROVED_DESIGN_ONLY"
        elif cid in {116, 117, 118, 164}:
            destination = "STAGING_PRODUCT_REVIEW"
        rows.append(
            {
                "category_id": str(cid),
                "category_name": row.name,
                "structural_decision": man.get("category_migration_action", ""),
                "cct1_result": man.get("cct1_result", ""),
                "homogeneous_assortment": homogeneous,
                "protected_cohort": protected,
                "live_product_count": str(len(pids)),
                "product_ids_requiring_review": "|".join(str(x) for x in pids) if pids else "",
                "proposed_destination_concept": destination,
                "blanket_removal_blocked": "YES",
            }
        )
    return rows


def build_identity_registry(manifest: list[dict[str, str]]) -> list[dict[str, str]]:
    reg: list[dict[str, str]] = []
    for code, (domain, en, _fa) in BUYER_COMMERCE_L1.items():
        reg.append(
            {
                "code": code,
                "entity": "commerce_category",
                "status": "PROPOSED_BUYER_L1",
                "scientific_domain_code": domain,
                "maps_from_current_category_id": "",
                "name_en": en,
            }
        )
    for fam, (domain, en, _fa) in METROLOGY_FAMILY_META.items():
        reg.append(
            {
                "code": fam,
                "entity": "commerce_category",
                "status": "PROPOSED_BUYER_L2_FAMILY",
                "scientific_domain_code": domain,
                "maps_from_current_category_id": "",
                "name_en": en,
            }
        )
    for row in manifest:
        for field, status in (
            ("published_kz_cat_code", "PROPOSED_PUBLISHED"),
            ("staging_registry_code", "STAGING_OR_DEPRECATED"),
        ):
            code = row.get(field, "")
            if not code:
                continue
            reg.append(
                {
                    "code": code,
                    "entity": "commerce_category",
                    "status": status if field == "published_kz_cat_code" else row["identity_status"],
                    "scientific_domain_code": row.get("scientific_domain_code", ""),
                    "maps_from_current_category_id": row["current_category_id"],
                    "name_en": row.get("target_name_en", ""),
                }
            )
    return reg


def build_unresolved_register(
    inputs: RouteBInputs,
    by_cat_products: dict[int, list[int]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for cid in sorted(MIXED_SEMANTIC_CATEGORY_IDS | {ACCESSORIES_L1_ID}):
        if cid == INDUSTRIAL_OIL_CATEGORY_ID:
            continue
        row = inputs.by_id[cid]
        rows.append(
            {
                "register_key": f"category:{cid}",
                "category_id": str(cid),
                "product_id": "",
                "issue": "MIXED_OR_STRUCTURAL_DECOMPOSITION",
                "required_action": "STEWARD_PRODUCT_LEVEL_REVIEW",
                "canonical_evidence_register": str(EVIDENCE_111_REGISTER.relative_to(ROOT)),
            }
        )
    if EVIDENCE_111_REGISTER.is_file():
        with EVIDENCE_111_REGISTER.open(encoding="utf-8", newline="") as handle:
            for erow in csv.DictReader(handle):
                pid = erow["product_id"]
                rows.append(
                    {
                        "register_key": f"product:{pid}",
                        "category_id": "",
                        "product_id": pid,
                        "issue": "TX_OWNER_REQUEST_MORE_EVIDENCE",
                        "required_action": erow.get("evidence_required_specific_to_this_SKU", "")[:240],
                        "canonical_evidence_register": str(EVIDENCE_111_REGISTER.relative_to(ROOT)),
                    }
                )
    return rows


def build_seo_impact(manifest: list[dict[str, str]], commerce_tree: list[dict[str, str]]) -> list[dict[str, str]]:
    tree_by_source = {r["source_current_category_id"]: r for r in commerce_tree if r.get("source_current_category_id")}
    rows: list[dict[str, str]] = []
    for row in manifest:
        cid = row["current_category_id"]
        published = tree_by_source.get(cid)
        rows.append(
            {
                "current_category_id": cid,
                "current_slug": row["current_slug"],
                "current_path": row["current_full_path"],
                "identity_status": row["identity_status"],
                "proposed_commerce_code": published["commerce_category_code"] if published else "",
                "proposed_url_slug": "defer" if not published else "review_on_apply",
                "redirect_proposal": row["seo_redirect_proposal"],
                "indexable_hub": "NO" if row["commerce_is_selectable"] == "NO" else "REVIEW",
                "megamenu_note": "helicoil_nav_186_187_188" if cid == "55" else "",
            }
        )
    for hid, code in HISTORICAL_DEPRECATED_CODES.items():
        rows.append(
            {
                "current_category_id": str(hid),
                "current_slug": f"removed-historical-{hid}",
                "current_path": "REMOVED_FROM_LIVE_TREE",
                "identity_status": "DEPRECATED_HISTORICAL",
                "proposed_commerce_code": code,
                "proposed_url_slug": "n/a",
                "redirect_proposal": "NO_UNRELATED_REDIRECT;megamenu_dangling_ref",
                "indexable_hub": "NO",
                "megamenu_note": "update_helicoil_nav_group_or_retire",
            }
        )
    return rows


def build_owner_memo_fa(stats: dict[str, Any], pinned_input_sha: str) -> str:
    return "\n".join(
        [
            "# یادداشت اجرایی مالک — فاز ۱ب مسیر B (نسخه اصلاحی)",
            "",
            "## وضعیت",
            "**READY_FOR_OWNER_REVIEW** — پذیرش طراحی ≠ مجوز APPLY یا تغییر Production.",
            "",
            "## تفکیک لایه‌ها",
            "- **دامنه علمی (`KZ.DOM.*`):** هفت دامنه منجمد؛ بدون دامنه ابزار دستی/کارگاهی.",
            "- **درخت خریدار (`KZ.CAT.*`):** ریشه‌های تجاری L1 پیشنهادی + خانواده‌های L2 (اندازه‌گیری) + برگ‌های قابل انتخاب.",
            "- **مانیفست ۱۳۵ ردیف:** نگاشت تاریخی Current → Target با وضعیت هویت (منتشرشده / staging / منسوخ).",
            "",
            f"## ورودی پین‌شده (census immutable)",
            f"`{pinned_input_sha}`",
            "",
            "## شمارش درخت پیشنهادی (واقعی)",
            f"- گره‌های commerce در `C-TARGET-TAXONOMY-TREE.csv`: **{stats['commerce_tree_nodes']}**",
            f"- ریشه‌های L1 خریدار: **{stats['buyer_l1_roots']}**",
            f"- منتشرشده در commerce: **{stats['publishable_leaves']}**",
            f"- منسوخ / staging / بازنشسته: **{stats['non_publishable_manifest']}**",
            "",
            "## TX-OWNER-001",
            "- ۱۵۱ `APPROVE_CATALOG_EXIT` (سندی؛ بدون APPLY)",
            "- ۱۱۱ `REQUEST_MORE_EVIDENCE` (ثبت ۱۱۱-ID)",
            "- ۰ APPLY",
            "",
            "## دسته‌های حساس",
            "- **۱۵۴:** تجزیه ساختاری؛ بدون حذف دسته‌ای.",
            "- **۱۵۶:** ۲۷ روغن صنعتی محافظت‌شده → Fluids.",
            "- **۵۵ / هلی‌کویل:** Thread Repair؛ ریشه‌های ۱۸۶/۱۸۷/۱۸۸ منسوخ مجزا.",
            "",
        ]
    )


def generate_route_b_package(
    out_dir: Path,
    *,
    pinned_input_git_sha: str,
    generator_run_git_sha: str,
) -> dict[str, Any]:
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
        owner_journal=load_owner_authorization_journals(),
        pr499_review=load_pr499_review(),
        evidence_recon=load_evidence_recon(),
    )
    manifest = build_manifest(inputs)
    manifest_by_id = {int(r["current_category_id"]): r for r in manifest}
    commerce_tree = build_commerce_tree(inputs, manifest_by_id)
    reconciliation = build_historical_reconciliation(set(by_id))
    by_cat = products_by_category(products)
    oil_ids = set(by_cat.get(INDUSTRIAL_OIL_CATEGORY_ID, []))
    product_map = build_product_mapping(inputs, manifest_by_id)
    mixed = build_mixed_decomposition(inputs, manifest_by_id, by_cat)
    identity_reg = build_identity_registry(manifest)
    unresolved = build_unresolved_register(inputs, by_cat)
    seo_rows = build_seo_impact(manifest, commerce_tree)

    write_csv(out_dir / "A-135-CURRENT-TARGET-MANIFEST.csv", MANIFEST_FIELDS, manifest)
    write_csv(
        out_dir / "B-HISTORICAL-138-TO-135-RECONCILIATION.csv",
        ["category_id", "reconciliation_status", "deprecated_registry_code", "product_deletion_inferred"],
        reconciliation["historical_reconciliation_rows"],
    )
    write_csv(
        out_dir / "C-TARGET-TAXONOMY-TREE.csv",
        [
            "commerce_category_code",
            "parent_commerce_code",
            "commerce_depth",
            "scientific_domain_code",
            "name_en",
            "name_fa",
            "commerce_is_selectable",
            "node_kind",
            "source_current_category_id",
        ],
        commerce_tree,
    )
    write_csv(out_dir / "D-PRODUCT-MAPPING-READINESS.csv", PRODUCT_MAP_FIELDS, product_map)
    write_csv(
        out_dir / "D2-MIXED-CATEGORY-DECOMPOSITION-MATRIX.csv",
        [
            "category_id",
            "category_name",
            "structural_decision",
            "cct1_result",
            "homogeneous_assortment",
            "protected_cohort",
            "live_product_count",
            "product_ids_requiring_review",
            "proposed_destination_concept",
            "blanket_removal_blocked",
        ],
        mixed,
    )
    write_csv(
        out_dir / "E-TARGET-IDENTITY-REGISTRY.csv",
        ["code", "entity", "status", "scientific_domain_code", "maps_from_current_category_id", "name_en"],
        identity_reg,
    )
    write_csv(
        out_dir / "F-SEO-MEGAMENU-IMPORT-IMPACT.csv",
        [
            "current_category_id",
            "current_slug",
            "current_path",
            "identity_status",
            "proposed_commerce_code",
            "proposed_url_slug",
            "redirect_proposal",
            "indexable_hub",
            "megamenu_note",
        ],
        seo_rows,
    )
    dep_summary_path = BASELINE_DIR / "08-NUMERIC-DEPENDENCY-SCAN-SUMMARY.json"
    dep_csv_path = BASELINE_DIR / "08-NUMERIC-CATEGORY-ID-DEPENDENCIES.csv"
    dep_summary = json.loads(dep_summary_path.read_text(encoding="utf-8")) if dep_summary_path.is_file() else {}
    (out_dir / "F2-IMPORTER-NUMERIC-DEPENDENCY-PROPOSAL.json").write_text(
        json.dumps(
            {
                "scan_summary_path": str(dep_summary_path.relative_to(ROOT)),
                "dependencies_csv": str(dep_csv_path.relative_to(ROOT)),
                "deduped_hits": dep_summary.get("deduped_hit_count"),
                "remap_design": "semantic KZ.CAT.* → runtime categories.id via E-TARGET-IDENTITY-REGISTRY.csv",
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    write_csv(
        out_dir / "G-UNRESOLVED-DECISION-REGISTER.csv",
        [
            "register_key",
            "category_id",
            "product_id",
            "issue",
            "required_action",
            "canonical_evidence_register",
        ],
        unresolved,
    )

    publishable = sum(1 for r in manifest if r["identity_status"] == "PUBLISHED_PROPOSED")
    stats = {
        "commerce_tree_nodes": len(commerce_tree),
        "buyer_l1_roots": len(BUYER_COMMERCE_L1),
        "publishable_leaves": sum(1 for r in commerce_tree if r["commerce_is_selectable"] == "YES"),
        "non_publishable_manifest": 135 - publishable,
    }
    (out_dir / "H-OWNER-EXECUTIVE-MEMO-FA.md").write_text(
        build_owner_memo_fa(stats, pinned_input_git_sha),
        encoding="utf-8",
    )

    validation = validate_route_b_package(
        manifest=manifest,
        commerce_tree=commerce_tree,
        product_rows=product_map,
        identity_registry=identity_reg,
        owner_journal=inputs.owner_journal,
        reconciliation=reconciliation,
        oil_product_ids=oil_ids,
        inputs_products=products,
    )
    product_summary = {
        "live_product_count": len([p for p in products if is_live_product(p)]),
        "product_mapping_rows": len(product_map),
        "tx_owner_cohort": sum(1 for r in product_map if r["tx_owner_cohort"] == "YES"),
        "owner_exit_documentary": sum(
            1 for r in product_map if r.get("owner_authoritative_decision") == "APPROVE_CATALOG_EXIT"
        ),
        "owner_evidence_pending": sum(
            1 for r in product_map if r.get("owner_authoritative_decision") == "REQUEST_MORE_EVIDENCE"
        ),
        "category_156_oil_product_ids": sorted(oil_ids),
    }
    recon_payload = {
        "pinned_input_git_sha": pinned_input_git_sha,
        "generator_run_git_sha": generator_run_git_sha,
        "pr532_merge_base_sha": "0d04e794712206e1421a596e28993002d05e338c",
        "category_manifest_rows": len(manifest),
        "commerce_tree_nodes": len(commerce_tree),
        "tree_stats": stats,
        "product_summary": product_summary,
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

    closeout = [
        "# Phase 1B Route B — validation closeout",
        "",
        f"Validation: **{validation['status']}**",
        "",
        "```json",
        json.dumps(validation, indent=2),
        "```",
    ]
    (out_dir / "J-VALIDATION-CLOSEOUT-REPORT.md").write_text("\n".join(closeout), encoding="utf-8")
    (out_dir / "README.md").write_text(
        "\n".join(
            [
                "# Phase 1B Route B — Target Taxonomy Design",
                "",
                "Design-only. Regenerate:",
                "",
                "```bash",
                "python3 scripts/audit_taxonomy_phase1b_route_b_target_design.py",
                "```",
            ]
        ),
        encoding="utf-8",
    )

    artifact_names = [
        "A-135-CURRENT-TARGET-MANIFEST.csv",
        "B-HISTORICAL-138-TO-135-RECONCILIATION.csv",
        "C-TARGET-TAXONOMY-TREE.csv",
        "D-PRODUCT-MAPPING-READINESS.csv",
        "D2-MIXED-CATEGORY-DECOMPOSITION-MATRIX.csv",
        "E-TARGET-IDENTITY-REGISTRY.csv",
        "F-SEO-MEGAMENU-IMPORT-IMPACT.csv",
        "F2-IMPORTER-NUMERIC-DEPENDENCY-PROPOSAL.json",
        "G-UNRESOLVED-DECISION-REGISTER.csv",
        "H-OWNER-EXECUTIVE-MEMO-FA.md",
        "I-RECONCILIATION-REPORT.json",
        "J-VALIDATION-CLOSEOUT-REPORT.md",
        "README.md",
    ]
    write_sha256sums(out_dir, artifact_names)
    if validation["status"] != "PASS":
        raise RuntimeError("ROUTE_B_VALIDATION_FAILED: " + "; ".join(validation["errors"]))
    return recon_payload
