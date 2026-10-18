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
    REMOVED_L1_HELICOIL_ROOT_IDS,
    TARGET_DOMAINS,
    TX_OWNER_SCOPE_CATEGORY_IDS,
    is_live_product,
    write_csv,
    write_sha256sums,
)
from catalog_target.taxonomy_route_b_semantics import (
    BUYER_COMMERCE_L1,
    HISTORICAL_DEPRECATED_CODES,
)
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
HELICOIL_CATEGORY_ID = 55
INDUSTRIAL_OIL_CATEGORY_ID = 156
ACCESSORIES_L1_ID = 154

DOMAIN_FA = {d["code"]: d.get("fa", d["en"]) for d in TARGET_DOMAINS}


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


def authority_label(row: dict[str, str]) -> str:
    dc = row.get("decision_class", "")
    if dc == "OWNER_APPROVED":
        return "OWNER_APPROVED_DOCUMENTARY"
    if dc == "EVIDENCE_GATED":
        return "EVIDENCE_GATED"
    if row.get("owner_steward_review_required") == "YES":
        return "OWNER_DECISION_REQUIRED"
    return "PROPOSED"


def architecture_disposition_category(row: dict[str, str], cid: int) -> str:
    if cid in SENSITIVE_CATEGORY_IDS:
        if cid == INDUSTRIAL_OIL_CATEGORY_ID:
            return "FREEZE"
        if cid in TX_OWNER_SCOPE_CATEGORY_IDS or cid in {158, 160}:
            return "HOLD"
        return "HOLD"
    if row.get("identity_status") == "PUBLISHED_PROPOSED" and row.get("published_kz_cat_code"):
        if row.get("product_decomposition_required") == "YES":
            return "HOLD"
        return "FREEZE"
    if row.get("identity_status") == "LEGACY_HUB_RETIRED":
        return "FREEZE"
    return "HOLD"


def tree_node_disposition(node: dict[str, str]) -> str:
    kind = node.get("node_kind", "")
    if kind == "BUYER_COMMERCE_L1":
        return "HOLD"
    if kind == "BUYER_COMMERCE_L2_FAMILY":
        return "FREEZE"
    if kind == "BUYER_COMMERCE_PUBLISHABLE":
        src = node.get("source_current_category_id", "")
        if src and int(src) in SENSITIVE_CATEGORY_IDS:
            return "HOLD"
        return "FREEZE"
    return "REVISE"


def recalculate_invariants(inputs: B2Inputs) -> dict[str, Any]:
    manifest_ids = {int(r["current_category_id"]) for r in inputs.manifest}
    tree = inputs.commerce_tree
    depth_hist = Counter(int(r["commerce_depth"]) for r in tree)
    roots = [r for r in tree if not (r.get("parent_commerce_code") or "").strip()]
    inherited = [r for r in tree if r.get("source_current_category_id", "").strip()]
    selectable = [r for r in tree if r.get("commerce_is_selectable") == "YES"]
    products = [r for r in inputs.product_map if r["product_id"].isdigit()]
    pmap_ids = {int(r["product_id"]) for r in products}
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


def build_architecture_review_matrix(inputs: B2Inputs) -> list[dict[str, str]]:
    tree_by_source = {
        r["source_current_category_id"]: r for r in inputs.commerce_tree if r.get("source_current_category_id")
    }
    products_by_cat: dict[int, list[int]] = defaultdict(list)
    unresolved_products_by_cat: dict[int, int] = defaultdict(int)
    for row in inputs.product_map:
        if not row["product_id"].isdigit():
            continue
        cid = int(row["current_category_id"])
        products_by_cat[cid].append(int(row["product_id"]))
        if row.get("mapping_authorization", "").startswith("BLOCKED") or row.get("approved_target_category_code"):
            unresolved_products_by_cat[cid] += 1

    rows: list[dict[str, str]] = []
    for m in sorted(inputs.manifest, key=lambda r: int(r["current_category_id"])):
        cid = int(m["current_category_id"])
        census = inputs.baseline_census.get(cid, {})
        tnode = tree_by_source.get(str(cid), {})
        alt = ""
        if m.get("cct1_result") == "BETTER_AS_FACET":
            alt = "Fold lubricants facet under FLUIDS L1 without intermediate hub 155"
        elif cid in {116, 117, 118}:
            alt = "Split chucks vs accessories into separate commerce leaves after SKU review"
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
                "authority_status": authority_label(m),
                "buyer_intent_homogeneity": "LOW" if cid in SENSITIVE_CATEGORY_IDS else "MEDIUM",
                "architecture_disposition_b2": architecture_disposition_category(m, cid),
                "alternative_disposition": alt,
                "confidence": m.get("confidence", "MEDIUM"),
                "evidence_sources": "B1_MANIFEST;BASELINE_CENSUS_2026-10-15",
                "live_product_count": str(len(products_by_cat.get(cid, []))),
                "unresolved_product_mappings": str(unresolved_products_by_cat.get(cid, 0)),
                "seo_redirect_proposal": m.get("seo_redirect_proposal", ""),
                "owner_explicit_decision_required": m.get("owner_steward_review_required", "NO"),
                "blocks_architecture_freeze": "YES" if architecture_disposition_category(m, cid) == "HOLD" else "NO",
                "blocks_execution_only": "YES" if cid in TX_OWNER_SCOPE_CATEGORY_IDS else "NO",
            }
        )
    return rows


def build_tree_disposition(inputs: B2Inputs) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for node in inputs.commerce_tree:
        disp = tree_node_disposition(node)
        rows.append(
            {
                "commerce_category_code": node["commerce_category_code"],
                "parent_commerce_code": node.get("parent_commerce_code", ""),
                "commerce_depth": node["commerce_depth"],
                "scientific_domain_code": node.get("scientific_domain_code", ""),
                "name_en": node.get("name_en", ""),
                "name_fa": node.get("name_fa", ""),
                "commerce_is_selectable": node.get("commerce_is_selectable", ""),
                "node_kind": node.get("node_kind", ""),
                "source_current_category_id": node.get("source_current_category_id", ""),
                "b2_disposition": disp,
                "rationale": (
                    "Seven-root architecture requires Owner sign-off before FREEZE"
                    if node.get("node_kind") == "BUYER_COMMERCE_L1"
                    else "B1 proposal structurally consistent; pending Owner architecture freeze"
                    if disp == "FREEZE"
                    else "Blocked on evidence or sensitive cohort"
                ),
            }
        )
    return rows


def build_grouped_owner_decisions(inputs: B2Inputs) -> list[dict[str, str]]:
    groups = [
        (
            "ARCH-7-L1-ROOTS",
            "A",
            "آیا هفت ریشه تجاری خریدار (جدا از دامنه علمی) تأیید شود؟",
            "FREEZE پس از تأیید مالک",
            "ادغام L1های قدیمی تحت ریشه‌های واحد",
            "7 ریشه در C-TARGET-TAXONOMY-TREE",
            "بلوک معماری",
            "YES",
            "NO",
        ),
        (
            "METROLOGY-L2-FAMILIES",
            "A",
            "آیا سه خانواده L2 اندازه‌گیری (دقیق / CNC / آزمایشگاهی) حفظ شود؟",
            "FREEZE",
            "یک L2 واحد",
            "گره‌های METROLOGY_FAMILY_*",
            "بلوک معماری",
            "YES",
            "NO",
        ),
        (
            "ACCESSORIES-154-DECOMPOSE",
            "B",
            "لوازم جانبی صنعتی ۱۵۴: تجزیه بدون حذف دسته‌ای؟",
            "DECOMPOSE + HOLD",
            "حذف والد",
            "cat 154 و فرزندان غیر روغن",
            "هویت commerce",
            "YES",
            "NO",
        ),
        (
            "FLUIDS-156-PROTECT",
            "B",
            "۲۷ روغن صنعتی تحت FLUIDS بدون خروج؟",
            "FREEZE",
            "انتقال به دامنه دیگر",
            "cat 156 + 27 SKU",
            "هویت commerce",
            "NO",
            "NO",
        ),
        (
            "TX-OWNER-SCOPE-157-160",
            "C",
            "خروج کاتالوگ ابزار دستی/چوبی (طراحی سندی)؟",
            "OWNER_APPROVED_DOCUMENTARY فقط",
            "استثناء صنعتی",
            "157-160 + محصولات",
            "اجرای APPLY",
            "YES",
            "YES",
        ),
        (
            "MIXED-CHUCKS-116-118",
            "C",
            "تجزیه سه‌نظام/چهارنظام/دونظام در سطح محصول؟",
            "HOLD",
            "نگه‌داری برگ mixed",
            "116-118",
            "نقشه محصول",
            "YES",
            "YES",
        ),
        (
            "HELICOIL-55-THREAD-REPAIR",
            "B",
            "هلی‌کویل ۵۵ تحت THREAD_REPAIR (نه Cutting)؟",
            "FREEZE",
            "بازگشت به قلاویز",
            "cat 55 + 29 SKU",
            "هویت commerce",
            "YES",
            "NO",
        ),
        (
            "MEGAMENU-186-187-188",
            "D",
            "رفع ارجاع منوی هلی‌کویل به ۱۸۶/۱۸۷/۱۸۸؟",
            "به‌روزرسانی منو یا retire",
            "ریدایرکت به هاب نامرتبط",
            "megamenu",
            "SEO/اجراء",
            "YES",
            "YES",
        ),
    ]
    rows: list[dict[str, str]] = []
    for g in groups:
        rows.append(
            {
                "decision_group_id": g[0],
                "freeze_tier": g[1],
                "question_fa": g[2],
                "recommended_choice": g[3],
                "alternative": g[4],
                "affected_scope": g[5],
                "consequence": g[6],
                "blocks_architecture_freeze": g[7],
                "blocks_execution_only": g[8],
                "traceability": f"B1+CENSUS;group={g[0]}",
            }
        )
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


def build_sensitive_dossier(inputs: B2Inputs) -> list[dict[str, str]]:
    by_id = {int(r["current_category_id"]): r for r in inputs.manifest}
    mixed = {int(r["category_id"]): r for r in inputs.mixed_matrix}
    rows: list[dict[str, str]] = []
    for cid in sorted(SENSITIVE_CATEGORY_IDS):
        m = by_id[cid]
        mx = mixed.get(cid, {})
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
                "blanket_removal_blocked": mx.get("blanket_removal_blocked", "YES"),
                "owner_decision_required": "YES",
            }
        )
    rows.append(
        {
            "category_id": str(HELICOIL_CATEGORY_ID),
            "category_name": by_id[HELICOIL_CATEGORY_ID]["current_name"],
            "full_path": by_id[HELICOIL_CATEGORY_ID]["current_full_path"],
            "b1_identity_status": "PUBLISHED_PROPOSED",
            "published_code": by_id[HELICOIL_CATEGORY_ID].get("published_kz_cat_code", ""),
            "structural_proposal": "THREAD_REPAIR domain; historic 186/187/188 deprecated separately",
            "product_ids": "",
            "protected_cohort": "HELICOIL_29",
            "blanket_removal_blocked": "YES",
            "owner_decision_required": "YES",
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
                "owner_decision_required": "YES",
            }
        )
    return rows


def build_seo_dossier(inputs: B2Inputs) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in inputs.seo_rows:
        rows.append(
            {
                **row,
                "b2_execution_deferred": "YES",
                "auto_redirect_approved": "NO",
            }
        )
    return rows


def build_implementation_plan() -> dict[str, Any]:
    return {
        "status": "PLAN_ONLY",
        "phases": [
            "Owner architecture freeze (7 L1 + identity registry)",
            "Product-level evidence completion (111 SKUs)",
            "Schema KZ.CAT.* + importer remap",
            "Category/product APPLY (separate authorization)",
            "SEO redirect deployment",
        ],
        "helicoil_megamenu": {
            "issue": "nav group references removed roots 186/187/188",
            "proposal": "Retarget to live category 55 or retire group; no unrelated 301",
        },
        "rollback": "Reversible mapping tables; no production mutation in B2",
    }


def build_owner_memo_fa(stats: dict[str, Any], disp_counts: Counter[str]) -> str:
    return "\n".join(
        [
            "# بسته تصمیم معماری — فاز ۱ب مسیر B2",
            "",
            "**وضعیت:** READY_FOR_OWNER_REVIEW — این سند تأیید مالک نیست؛ آماده‌سازی انجماد معماری است.",
            "",
            f"**ورودی B1 (ادغام PR #533):** `{PR533_MERGE_SHA}`",
            "",
            "## خلاصه بازبینی",
            f"- دسته‌های فعلی: {stats['current_category_count']}",
            f"- گره‌های commerce پیشنهادی: {stats['commerce_tree_nodes']}",
            f"- توزیع عمق: {stats['depth_histogram']}",
            f"- محصولات زنده: {stats['live_product_rows']}",
            f"- TX-OWNER: {stats['owner_journal_exits']} خروج سندی / {stats['owner_journal_evidence']} در انتظار مدرک",
            "",
            "## انجماد پیشنهادی (B2)",
            f"- FREEZE: {disp_counts.get('FREEZE', 0)}",
            f"- REVISE: {disp_counts.get('REVISE', 0)}",
            f"- HOLD: {disp_counts.get('HOLD', 0)}",
            "",
            "## تفکیک تصمیم",
            "- **A:** انجماد معماری هفت ریشه",
            "- **B:** هویت‌های commerce تکی",
            "- **C:** وابسته به مدرک محصول",
            "- **D:** SEO/منو/ایمپورت — بعد از انجماد",
            "",
            "**OWNER_DECISIONS_PENDING=YES** — ادغام در main ≠ تأیید معماری.",
        ]
    )


def validate_b2_package(
    inputs: B2Inputs,
    invariants: dict[str, Any],
    arch_matrix: list[dict[str, str]],
    product_impact: list[dict[str, str]],
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

    return {"status": "PASS" if not errors else "FAIL", "errors": errors, "b1_validation": validation}


def generate_b2_package(
    out_dir: Path,
    *,
    base_git_sha: str,
    generator_run_git_sha: str,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs = load_b2_inputs()
    invariants = recalculate_invariants(inputs)
    arch = build_architecture_review_matrix(inputs)
    tree_disp = build_tree_disposition(inputs)
    owner_groups = build_grouped_owner_decisions(inputs)
    product_impact = build_product_impact(inputs)
    sensitive = build_sensitive_dossier(inputs)
    seo = build_seo_dossier(inputs)
    impl = build_implementation_plan()

    cat_disp = Counter(r["architecture_disposition_b2"] for r in arch)
    tree_disp_counts = Counter(r["b2_disposition"] for r in tree_disp)

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
        build_owner_memo_fa(invariants, cat_disp),
        encoding="utf-8",
    )

    validation = validate_b2_package(inputs, invariants, arch, product_impact)
    payload = {
        "base_git_sha": base_git_sha,
        "b1_merge_sha": PR533_MERGE_SHA,
        "b1_artifact_dir": str(B1_DIR.relative_to(ROOT)),
        "generator_run_git_sha": generator_run_git_sha,
        "invariants_recalculated": invariants,
        "category_disposition_counts": dict(cat_disp),
        "tree_disposition_counts": dict(tree_disp_counts),
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
