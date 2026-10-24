"""AST supplier reconcile: ledger, manifests, commercial and CREATE QA reports."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal

from catalog_target.ast_price_catalog_category_map import classify_create_category
from catalog_target.ast_price_catalog_constants import (
    BRAND_HINT_TO_ID,
    BRAND_HINT_TO_KEY,
    HOLD_EXTRACTION_STATUSES,
    OWNER_AUTH_APPLY,
    OWNER_AUTH_ROLLBACK,
    OWNER_COMMERCIAL_PRICING_POLICY_APPROVED,
    PRICE_DECREASE_REVIEW_PCT,
    PRICE_INCREASE_REVIEW_PCT,
    PRICING_POLICY_ID,
    QA_DEVICE_SPARE_DISCOUNT_SPLIT,
    SOURCE_ARCHIVE_SHA256,
)
from catalog_target.ast_price_catalog_hold_recovery import write_create_hold_recovery_plan
from catalog_target.ast_price_catalog_manifest_acceptance import write_update_stage_owner_bundles
from catalog_target.ast_price_catalog_update_canary import write_update_canary_artifacts
from catalog_target.ast_price_catalog_update_owner_package import write_update_owner_package
from catalog_target.ast_price_catalog_manifest_acceptance import (
    MANIFEST_ABSENT,
    write_owner_manifest_bundles,
)
from catalog_target.ast_price_catalog_update_preflight import write_update_cohort_preflight
from catalog_target.core import normalize_sku

PrimaryOutcome = Literal["UPDATE", "CREATE", "UNCHANGED", "HOLD", "REJECTED"]

QA_MANUFACTURER_IDENTITY_REVIEW = "QA_MANUFACTURER_IDENTITY_REVIEW"
CREATE_APPROVAL_PROPOSED = "PROPOSED"
CREATE_APPROVAL_OWNER = "OWNER_APPROVED_FOR_APPLY"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_code(code: str) -> str:
    return normalize_sku(code or "").replace("×", "X")


def parse_discount_percent(label: str) -> tuple[int | None, list[str]]:
    """Parse supplier cash discount for procurement evidence only (never blocks sell price)."""
    flags: list[str] = []
    if not label:
        return None, flags
    if "REVIEW" in label.upper():
        flags.append(QA_DEVICE_SPARE_DISCOUNT_SPLIT)
    m = re.match(r"^(\d+)", label.strip())
    if not m:
        return None, flags
    return int(m.group(1)), flags


def list_toman_from_rial(rial: int) -> Decimal | None:
    if rial <= 0:
        return None
    toman = (Decimal(rial) / Decimal(10)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return toman if toman > 0 else None


def net_purchase_toman(list_toman: Decimal, discount_pct: int | None) -> Decimal | None:
    if discount_pct is None:
        return None
    factor = Decimal(1) - (Decimal(discount_pct) / Decimal(100))
    return (list_toman * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def proposed_customer_price(rial: int, discount_label: str) -> tuple[Decimal | None, str, list[str]]:
    _, proc_flags = parse_discount_percent(discount_label)
    list_t = list_toman_from_rial(rial)
    if list_t is None:
        return None, "INVALID_SOURCE_PRICE", proc_flags
    return list_t, PRICING_POLICY_ID, proc_flags


@dataclass
class CatalogRow:
    product_id: str
    sku: str
    manufacturer_code: str
    name: str
    brand_id: str
    brand: str
    category_id: str
    base_price: Decimal | None
    original_price: Decimal | None
    is_active: bool
    is_available: bool
    deleted_at: str


@dataclass
class LedgerRow:
    brand_hint: str
    code: str
    source_file: str
    source_page: str
    source_date: str
    extraction_status: str
    primary_outcome: PrimaryOutcome
    hold_reason: str
    qa_flags: str
    product_id: str
    proposed_price: str
    current_price: str
    pricing_policy_id: str


def load_catalog_snapshot(path: Path) -> list[CatalogRow]:
    rows: list[CatalogRow] = []
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            bp = r.get("base_price") or ""
            op = r.get("original_price") or ""
            try:
                base = Decimal(bp) if bp else None
            except InvalidOperation:
                base = None
            try:
                orig = Decimal(op) if op else None
            except InvalidOperation:
                orig = None
            rows.append(
                CatalogRow(
                    product_id=str(r["id"]),
                    sku=str(r.get("sku") or ""),
                    manufacturer_code=str(r.get("manufacturer_code") or ""),
                    name=str(r.get("name") or ""),
                    brand_id=str(r.get("brand_id") or ""),
                    brand=str(r.get("brand") or ""),
                    category_id=str(r.get("category_id") or ""),
                    base_price=base,
                    original_price=orig,
                    is_active=str(r.get("is_active", "")).lower() in {"t", "true", "1"},
                    is_available=str(r.get("is_available", "")).lower() in {"t", "true", "1"},
                    deleted_at=str(r.get("deleted_at") or ""),
                )
            )
    return rows


def load_categories_metadata(path: Path) -> dict[int, dict[str, Any]]:
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    child_count: Counter[int] = Counter()
    by_id: dict[int, dict[str, str]] = {}
    for r in rows:
        cid = int(r["id"])
        by_id[cid] = r
        pid = r.get("parent_id") or ""
        if pid:
            child_count[int(pid)] += 1
    meta: dict[int, dict[str, Any]] = {}
    for cid, r in by_id.items():
        chain = [cid]
        cur = cid
        while by_id[cur].get("parent_id"):
            cur = int(by_id[cur]["parent_id"])
            chain.append(cur)
        depth = len(chain)
        meta[cid] = {
            "depth": depth,
            "is_leaf": child_count[cid] == 0,
            "selectable": child_count[cid] == 0 and 2 <= depth <= 3,
            "name": r["name"],
        }
    return meta


def index_catalog(rows: list[CatalogRow]) -> dict[tuple[str, str], list[CatalogRow]]:
    idx: dict[tuple[str, str], list[CatalogRow]] = defaultdict(list)
    for row in rows:
        for code in {norm_code(row.sku), norm_code(row.manufacturer_code)} - {""}:
            idx[(row.brand_id, code)].append(row)
    return idx


def index_sku_global(rows: list[CatalogRow]) -> dict[str, list[CatalogRow]]:
    out: dict[str, list[CatalogRow]] = defaultdict(list)
    for row in rows:
        sku = norm_code(row.sku)
        if sku:
            out[sku].append(row)
    return out


def load_candidate_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def build_authoritative_rows(
    all_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[LedgerRow], Counter]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    rejected_ledger: list[LedgerRow] = []
    stats: Counter = Counter()

    for r in all_rows:
        code = norm_code(r.get("code_candidate") or "")
        if not code:
            stats["raw_no_code"] += 1
            continue
        grouped[(r.get("brand_hint") or "", code)].append(r)

    authoritative: list[dict[str, str]] = []

    for (brand_hint, code), members in grouped.items():
        statuses = {m.get("status") or "" for m in members}
        if "CONFLICTING_SOURCE_QUOTES_HOLD" in statuses:
            rejected_ledger.append(
                LedgerRow(
                    brand_hint=brand_hint,
                    code=code,
                    source_file="",
                    source_page="",
                    source_date="",
                    extraction_status="CONFLICTING_SOURCE_QUOTES_HOLD",
                    primary_outcome="REJECTED",
                    hold_reason="SOURCE_PRICE_CONFLICT",
                    qa_flags="",
                    product_id="",
                    proposed_price="",
                    current_price="",
                    pricing_policy_id="",
                )
            )
            stats["rejected_conflict_keys"] += 1
            continue

        valid_members = [m for m in members if (m.get("status") or "") not in HOLD_EXTRACTION_STATUSES]
        if not valid_members:
            reason = next(iter(statuses & HOLD_EXTRACTION_STATUSES), "EXTRACTION_REJECTED")
            rejected_ledger.append(
                LedgerRow(
                    brand_hint=brand_hint,
                    code=code,
                    source_file=members[0].get("file") or "",
                    source_page=members[0].get("page") or "",
                    source_date=members[0].get("source_date") or "",
                    extraction_status=reason,
                    primary_outcome="REJECTED",
                    hold_reason=reason,
                    qa_flags="",
                    product_id="",
                    proposed_price="",
                    current_price="",
                    pricing_policy_id="",
                )
            )
            stats["rejected_extraction_keys"] += 1
            continue

        winner = max(valid_members, key=lambda m: m.get("source_date") or "")
        authoritative.append(winner)
        stats["authoritative_keys"] += 1

    return authoritative, rejected_ledger, stats


def extraction_visual_qa_cleared(r: dict[str, str]) -> bool:
    status = (r.get("status") or "").strip()
    if status != "CANDIDATE_EXACT_VISUAL_QA_REQUIRED":
        return True
    verified = (r.get("visual_pdf_qa_verified") or r.get("extraction_visual_qa_verified") or "").strip().upper()
    return verified == "YES"


def pct_change(old: Decimal | None, new: Decimal | None) -> Decimal | None:
    if old is None or new is None or old == 0:
        return None
    return ((new - old) / old * Decimal(100)).quantize(Decimal("0.01"))


def swing_explanation(
    current: Decimal | None, proposed: Decimal, list_toman: Decimal, pct: Decimal | None
) -> str:
    if pct is not None and abs(pct) >= Decimal("200"):
        return "Suspect extraction/currency/match — change exceeds 200%; manual PDF QA required."
    if current and list_toman and proposed == list_toman and pct and pct > 0:
        return "Consistent with supplier list refresh (cooperation Rial÷10); site price lagged older list."
    if current and proposed < current:
        return "Proposed decrease vs current site — verify not a mis-extracted row or wrong variant code."
    return "Large increase vs current site — verify supplier list row matches exact SKU/variant."


def persian_product_name(brand_key: str, code: str, family_label: str) -> str:
    brand_fa = {
        "ASTPOWER": "ای اس تی پاور",
        "ET": "ای تی",
        "DASQUA": "داسکوا",
        "CHUMPOWER": "چام پاور",
    }.get(brand_key, brand_key)
    family = family_label or "محصول صنعتی"
    return f"{family} {brand_fa} مدل {code}"


def validate_create_candidate(
    *,
    code: str,
    brand_id: str,
    category_id: int | None,
    cat_meta: dict[int, dict[str, Any]],
    global_sku: dict[str, list[CatalogRow]],
    name: str,
    proposed: Decimal | None,
) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if not code or len(code) < 3:
        issues.append("invalid_identity_code")
    if brand_id not in set(BRAND_HINT_TO_ID.values()):
        issues.append("invalid_brand")
    hits = global_sku.get(code, [])
    if [h for h in hits if not h.deleted_at]:
        issues.append("duplicate_sku_active")
    if [h for h in hits if h.deleted_at]:
        issues.append("soft_deleted_sku_conflict")
    if category_id is None:
        issues.append("HOLD_CATEGORY_MAPPING")
    else:
        cm = cat_meta.get(category_id)
        if not cm or not cm.get("selectable"):
            issues.append("category_not_selectable_leaf")
    if code not in name:
        issues.append("name_missing_model_token")
    if proposed is None:
        issues.append("missing_selling_price")
    return not issues, issues


def run_reconcile(
    *,
    audit_dir: Path,
    candidates_csv: Path,
    catalog_csv: Path,
    categories_csv: Path,
    source_docs_csv: Path,
    source_zip: Path,
) -> dict[str, Any]:
    audit_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()

    zip_sha = sha256_file(source_zip)
    if zip_sha != SOURCE_ARCHIVE_SHA256:
        raise ValueError(f"SOURCE_SHA_MISMATCH expected={SOURCE_ARCHIVE_SHA256} got={zip_sha}")

    catalog = load_catalog_snapshot(catalog_csv)
    idx = index_catalog(catalog)
    global_sku = index_sku_global(catalog)
    cat_meta = load_categories_metadata(categories_csv) if categories_csv.is_file() else {}

    all_rows = load_candidate_rows(candidates_csv)
    auth_rows, rejected_ledger, auth_stats = build_authoritative_rows(all_rows)

    ledger: list[LedgerRow] = list(rejected_ledger)
    updates: list[dict[str, Any]] = []
    creates: list[dict[str, Any]] = []
    unchanged: list[dict[str, Any]] = []
    holds: list[dict[str, Any]] = []
    abnormal_updates: list[dict[str, Any]] = []
    create_qa: list[dict[str, Any]] = []

    outcome_counts: Counter = Counter()
    sum_before = Decimal(0)
    sum_after = Decimal(0)

    for r in auth_rows:
        brand_hint = r.get("brand_hint") or ""
        brand_id = BRAND_HINT_TO_ID.get(brand_hint)
        brand_key = BRAND_HINT_TO_KEY.get(brand_hint, "")
        code = norm_code(r.get("code_candidate") or "")
        rial = int(r.get("source_price_rial") or 0)
        disc, proc_flags = parse_discount_percent(r.get("cash_discount_label") or "")
        proposed, policy_id, proc_flags2 = proposed_customer_price(rial, r.get("cash_discount_label") or "")
        list_t = list_toman_from_rial(rial)

        qa_flags: list[str] = list(proc_flags) + list(proc_flags2)
        if brand_hint == "ASTPOWER_OR_SOURCE_BRAND_REVIEW":
            qa_flags.append(QA_MANUFACTURER_IDENTITY_REVIEW)
        hold_reason = ""

        if not brand_id:
            hold_reason = "UNKNOWN_BRAND_HINT"
            ledger.append(_ledger_from(r, code, "HOLD", hold_reason, qa_flags, "", "", "", policy_id))
            holds.append(_hold_row(r, code, hold_reason, qa_flags))
            outcome_counts["HOLD"] += 1
            continue

        hits = idx.get((brand_id, code), [])
        product = hits[0] if len(hits) == 1 else None
        if len(hits) > 1:
            hold_reason = "AMBIGUOUS_IDENTITY"
            ledger.append(_ledger_from(r, code, "HOLD", hold_reason, qa_flags, "", "", "", policy_id))
            holds.append(_hold_row(r, code, hold_reason, qa_flags))
            outcome_counts["HOLD"] += 1
            continue

        if proposed is None or policy_id != PRICING_POLICY_ID:
            hold_reason = policy_id if proposed is None else "INVALID_SOURCE_PRICE"
            pid = product.product_id if product else ""
            ledger.append(_ledger_from(r, code, "HOLD", hold_reason, qa_flags, pid, "", "", policy_id))
            holds.append(
                {
                    **_hold_row(r, code, hold_reason, qa_flags),
                    **({"product_id": pid, "sku": product.sku} if product else {}),
                }
            )
            outcome_counts["HOLD"] += 1
            continue

        if product:
            current = product.base_price
            if proposed is not None and current is not None and proposed == current:
                ledger.append(
                    _ledger_from(
                        r, code, "UNCHANGED", "", qa_flags, product.product_id,
                        str(proposed), str(current), policy_id,
                    )
                )
                unchanged.append(
                    {
                        "product_id": product.product_id,
                        "sku": product.sku,
                        "brand": product.brand,
                        "current_price": str(current),
                        "proposed_price": str(proposed),
                        "source_document": r.get("file"),
                        "source_page": r.get("page"),
                    }
                )
                outcome_counts["UNCHANGED"] += 1
                continue

            pct = pct_change(current, proposed)
            if pct is not None and (
                pct <= -PRICE_DECREASE_REVIEW_PCT or pct >= PRICE_INCREASE_REVIEW_PCT
            ):
                qa_flags.append("QA_LARGE_PRICE_SWING")
                hold_reason = qa_flags[0]
                ledger.append(
                    _ledger_from(
                        r, code, "HOLD", hold_reason, qa_flags, product.product_id,
                        str(proposed) if proposed else "", str(current) if current else "", policy_id,
                    )
                )
                holds.append(
                    {
                        "product_id": product.product_id,
                        "sku": product.sku,
                        "code": code,
                        "hold_reason": hold_reason,
                        "qa_flags": "|".join(qa_flags),
                        "current_price": str(current) if current else "",
                        "proposed_price": str(proposed) if proposed else "",
                        "source_document": r.get("file"),
                        "source_page": r.get("page"),
                    }
                )
                abnormal_updates.append(
                    {
                        "product_id": product.product_id,
                        "sku": product.sku,
                        "current_site_price": str(current) if current else "",
                        "supplier_list_toman": str(list_t) if list_t else "",
                        "supplier_rial": str(rial),
                        "cash_discount_percent": disc if disc is not None else "",
                        "net_purchase_toman": str(net_purchase_toman(list_t, disc)) if list_t and disc else "",
                        "proposed_selling_price": str(proposed) if proposed else "",
                        "percent_change": str(pct) if pct else "",
                        "source_document": r.get("file"),
                        "source_page": r.get("page"),
                        "explanation": swing_explanation(
                            current, proposed or Decimal(0), list_t or Decimal(0), pct
                        ),
                        "qa_result": "HOLD_PENDING_OWNER_QA",
                    }
                )
                outcome_counts["HOLD"] += 1
                continue

            diff = (proposed or Decimal(0)) - (current or Decimal(0))
            if current is not None and proposed is not None:
                sum_before += current
                sum_after += proposed
            ledger.append(
                _ledger_from(
                    r, code, "UPDATE", "", qa_flags, product.product_id,
                    str(proposed) if proposed else "", str(current) if current else "", policy_id,
                )
            )
            updates.append(
                {
                    "product_id": product.product_id,
                    "sku": product.sku,
                    "brand": product.brand,
                    "current_price": str(current) if current is not None else "",
                    "proposed_price": str(proposed) if proposed else "",
                    "absolute_diff": str(diff),
                    "percent_diff": str(pct) if pct else "",
                    "pricing_policy_id": policy_id,
                    "cash_discount_percent": disc if disc is not None else "",
                    "source_document": r.get("file"),
                    "source_page": r.get("page"),
                    "source_checksum": r.get("file_sha256"),
                    "archive_checksum": zip_sha,
                    "expected_current_price": str(current) if current is not None else "",
                    "validation_result": "OK",
                }
            )
            outcome_counts["UPDATE"] += 1
            continue

        if not extraction_visual_qa_cleared(r):
            hold_reason = "HOLD_VISUAL_PDF_QA_REQUIRED"
            ledger.append(
                _ledger_from(r, code, "HOLD", hold_reason, qa_flags, "", str(proposed or ""), "", policy_id)
            )
            holds.append(_hold_row(r, code, hold_reason, qa_flags))
            outcome_counts["HOLD"] += 1
            continue

        if QA_MANUFACTURER_IDENTITY_REVIEW in qa_flags:
            hold_reason = "HOLD_MANUFACTURER_IDENTITY_UNVERIFIED"
            ledger.append(
                _ledger_from(r, code, "HOLD", hold_reason, qa_flags, "", str(proposed or ""), "", policy_id)
            )
            holds.append(_hold_row(r, code, hold_reason, qa_flags))
            outcome_counts["HOLD"] += 1
            continue

        cat_decision = classify_create_category(
            source_file=r.get("file") or "",
            brand_hint=brand_hint,
            code=code,
            code_nearby=r.get("code_nearby") or "",
            cat_meta=cat_meta,
        )
        cat_id = cat_decision.category_id
        family_label = cat_decision.family_label
        if cat_decision.hold_reason and cat_id is None:
            hold_reason = cat_decision.hold_reason
            ledger.append(
                _ledger_from(r, code, "HOLD", hold_reason, qa_flags, "", str(proposed or ""), "", policy_id)
            )
            holds.append(_hold_row(r, code, hold_reason, qa_flags + [cat_decision.mapping_rule]))
            outcome_counts["HOLD"] += 1
            continue
        name = persian_product_name(brand_key, code, family_label)
        ok, issues = validate_create_candidate(
            code=code,
            brand_id=brand_id,
            category_id=cat_id,
            cat_meta=cat_meta,
            global_sku=global_sku,
            name=name,
            proposed=proposed,
        )
        create_qa.append(
            {
                "sku": code,
                "brand_id": brand_id,
                "category_id": cat_id or "",
                "qa_pass": "YES" if ok else "NO",
                "issues": "|".join(issues),
                "name": name,
                "source_document": r.get("file"),
            }
        )
        if not ok:
            hold_reason = issues[0]
            ledger.append(_ledger_from(r, code, "HOLD", hold_reason, qa_flags, "", str(proposed or ""), "", policy_id))
            holds.append(_hold_row(r, code, hold_reason, qa_flags + issues))
            outcome_counts["HOLD"] += 1
            continue

        ledger.append(_ledger_from(r, code, "CREATE", "", qa_flags, "", str(proposed or ""), "", policy_id))
        creates.append(
            {
                "sku": code,
                "manufacturer_code": code,
                "brand_id": brand_id,
                "brand_key": brand_key,
                "category_id": str(cat_id),
                "category_mapping_rule": cat_decision.mapping_rule,
                "name": name,
                "base_price": str(proposed) if proposed else "",
                "is_active": "true",
                "is_available": "false",
                "apply_eligible": "YES",
                "approval_status": CREATE_APPROVAL_PROPOSED,
                "pricing_policy_id": policy_id,
                "cash_discount_percent": disc if disc is not None else "",
                "source_document": r.get("file"),
                "source_page": r.get("page"),
                "source_checksum": r.get("file_sha256"),
                "archive_checksum": zip_sha,
            }
        )
        outcome_counts["CREATE"] += 1

    outcome_counts["REJECTED"] = len(rejected_ledger)
    total_auth = len(auth_rows)
    primary_sum = (
        outcome_counts["UPDATE"]
        + outcome_counts["CREATE"]
        + outcome_counts["UNCHANGED"]
        + outcome_counts["HOLD"]
    )
    if primary_sum != total_auth:
        raise RuntimeError(
            f"LEDGER_IMBALANCE primary={primary_sum} authoritative={total_auth} counts={dict(outcome_counts)}"
        )

    commercial = _build_commercial_report(auth_rows, catalog, idx)
    sanitized = audit_dir / "sanitized"
    sanitized.mkdir(parents=True, exist_ok=True)

    _write_csv(audit_dir / "SOURCE_ROW_LEDGER.csv", [ledger_row_dict(x) for x in ledger])
    _write_csv(audit_dir / "UPDATE_PRODUCTS.csv", updates)
    _write_csv(audit_dir / "CREATE_PRODUCTS.csv", creates)
    _write_csv(audit_dir / "UNCHANGED_PRODUCTS.csv", unchanged)
    _write_csv(audit_dir / "HOLD_PRODUCTS.csv", holds)
    _write_csv(audit_dir / "ABNORMAL_UPDATE_REVIEW.csv", abnormal_updates)
    _write_csv(audit_dir / "CREATE_IDENTITY_QA.csv", create_qa)

    if source_docs_csv.is_file():
        (audit_dir / "SOURCE_DOCUMENTS.csv").write_bytes(source_docs_csv.read_bytes())

    manifest_hashes = _write_execution_manifest(audit_dir)
    if not creates:
        manifest_hashes["CREATE_PRODUCTS.csv"] = MANIFEST_ABSENT
    write_owner_manifest_bundles(
        sanitized,
        manifest_hashes,
        update_count=outcome_counts["UPDATE"],
        create_count=outcome_counts["CREATE"],
    )
    master_update_sha = manifest_hashes.get("UPDATE_PRODUCTS.csv", "")
    canary_registry = write_update_canary_artifacts(
        audit_dir=audit_dir,
        update_rows=updates,
        master_manifest_sha256=master_update_sha,
    )
    write_update_stage_owner_bundles(
        sanitized,
        ledger_manifest_sha256=manifest_hashes.get("SOURCE_ROW_LEDGER.csv", ""),
        canary_registry=canary_registry,
    )
    write_update_owner_package(
        audit_dir=audit_dir,
        sanitized_dir=sanitized,
        catalog_csv=catalog_csv,
        update_rows=updates,
        abnormal_updates=abnormal_updates,
        canary_registry=canary_registry,
    )
    write_update_cohort_preflight(
        audit_dir=audit_dir,
        sanitized_dir=sanitized,
        catalog_csv=catalog_csv,
        update_rows=updates,
        abnormal_updates=abnormal_updates,
    )
    write_create_hold_recovery_plan(audit_dir=audit_dir, sanitized_dir=sanitized, holds=holds)

    with source_docs_csv.open(encoding="utf-8-sig") as f:
        pdf_count = len(list(csv.DictReader(f)))

    identity_keys_total = total_auth + len(rejected_ledger)
    inclusive_sum = primary_sum + len(rejected_ledger)
    report = {
        "generated_at": generated_at,
        "source_pdfs_processed": pdf_count,
        "source_archive_sha256": zip_sha,
        "catalog_snapshot_sha256": sha256_file(catalog_csv),
        "candidate_rows_raw": len(all_rows),
        "total_authoritative_source_rows": identity_keys_total,
        "authoritative_passed_extraction_rows": total_auth,
        "primary_outcomes": dict(outcome_counts),
        "ledger_balance_check": primary_sum == total_auth,
        "inclusive_outcome_equation": (
            f"UPDATE+CREATE+UNCHANGED+HOLD+REJECTED={inclusive_sum} "
            f"== total_source_identity_keys={identity_keys_total}"
        ),
        "inclusive_outcome_balanced": inclusive_sum == identity_keys_total,
        "raw_extraction_rejected_row_events": sum(
            1 for r in all_rows if (r.get("status") or "") in HOLD_EXTRACTION_STATUSES
        ),
        "rejected_unique_keys": len(rejected_ledger),
        "auth_build_stats": dict(auth_stats),
        "owner_commercial_pricing_policy_status": OWNER_COMMERCIAL_PRICING_POLICY_APPROVED,
        "pricing_policy_id": PRICING_POLICY_ID,
        "matched_not_in_update_explanation": (
            f"Matched existing SKUs not in UPDATE manifest: UNCHANGED={outcome_counts.get('UNCHANGED', 0)}, "
            f"QA_LARGE_PRICE_SWING HOLD={len(abnormal_updates)}. "
            f"Cash-discount REVIEW labels are procurement QA flags only (not pricing holds)."
        ),
        "sum_selling_price_before_update_scope": str(sum_before),
        "sum_selling_price_after_update_scope": str(sum_after),
        **{f"manifest_sha256_{k}": v for k, v in manifest_hashes.items()},
    }

    (audit_dir / "RECONCILIATION_REPORT.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (sanitized / "RECONCILIATION_SUMMARY.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    policy_evidence = _price_policy_evidence(manifest_hashes)
    (audit_dir / "PRICE_POLICY_EVIDENCE.md").write_text(policy_evidence, encoding="utf-8")
    (sanitized / "PRICE_POLICY_EVIDENCE.md").write_text(policy_evidence, encoding="utf-8")
    (audit_dir / "COMMERCIAL_PRICING_DECISION.md").write_text(commercial, encoding="utf-8")
    (sanitized / "COMMERCIAL_PRICING_DECISION.md").write_text(commercial, encoding="utf-8")
    plan = _production_apply_plan(manifest_hashes)
    (audit_dir / "PRODUCTION_APPLY_PLAN.md").write_text(plan, encoding="utf-8")
    (sanitized / "PRODUCTION_APPLY_PLAN.md").write_text(plan, encoding="utf-8")
    hold_breakdown = Counter(h.get("hold_reason", "") for h in holds)
    (audit_dir / "OWNER_DECISION_REPORT.md").write_text(
        "# Owner decision report\n\n"
        f"- Identity keys: **{identity_keys_total}** (passed extraction: {total_auth}, REJECTED: {len(rejected_ledger)})\n"
        f"- UPDATE: **{outcome_counts['UPDATE']}** | CREATE: **{outcome_counts['CREATE']}** | "
        f"UNCHANGED: **{outcome_counts.get('UNCHANGED', 0)}** | HOLD: **{outcome_counts['HOLD']}** | "
        f"REJECTED: **{outcome_counts['REJECTED']}**\n"
        f"- Large-swing QA holds: **{len(abnormal_updates)}** (see `ABNORMAL_UPDATE_REVIEW.csv`)\n"
        f"- Hold reasons: `{dict(hold_breakdown)}`\n"
        f"- Commercial policy: **`{OWNER_COMMERCIAL_PRICING_POLICY_APPROVED}`** (`{PRICING_POLICY_ID}`)\n",
        encoding="utf-8",
    )
    return report


def _price_policy_evidence(manifest_hashes: dict[str, str]) -> str:
    return f"""# AST price policy evidence

## Owner commercial approval

- **Status:** `{OWNER_COMMERCIAL_PRICING_POLICY_APPROVED}`
- **Policy ID:** `{PRICING_POLICY_ID}`
- **Formula:** `base_price = verified_pdf_rial / 10` (Toman, Decimal)
- **Scope:** One-time AST supplier archive SHA256 `{SOURCE_ARCHIVE_SHA256}` only.

## Cash discount handling

- Recorded in manifests as `cash_discount_percent` for procurement analysis.
- **Not** subtracted from customer `base_price`.
- **Not** applied as storefront promotion; **do not** modify `original_price`.
- Labels with device/spare split (`*_REVIEW`) set QA flag `{QA_DEVICE_SPARE_DISCOUNT_SPLIT}` only.

## Manifest fingerprints (post-approval regeneration)

- UPDATE: `{manifest_hashes.get("UPDATE_PRODUCTS.csv", "")}`
- CREATE: `{manifest_hashes.get("CREATE_PRODUCTS.csv", "")}`
- LEDGER: `{manifest_hashes.get("SOURCE_ROW_LEDGER.csv", "")}`
"""


def _ledger_from(
    r: dict[str, str],
    code: str,
    outcome: PrimaryOutcome,
    hold_reason: str,
    qa_flags: list[str],
    product_id: str,
    proposed: str,
    current: str,
    policy_id: str,
) -> LedgerRow:
    return LedgerRow(
        brand_hint=r.get("brand_hint") or "",
        code=code,
        source_file=r.get("file") or "",
        source_page=r.get("page") or "",
        source_date=r.get("source_date") or "",
        extraction_status=r.get("status") or "",
        primary_outcome=outcome,
        hold_reason=hold_reason,
        qa_flags="|".join(qa_flags),
        product_id=product_id,
        proposed_price=proposed,
        current_price=current,
        pricing_policy_id=policy_id,
    )


def ledger_row_dict(row: LedgerRow) -> dict[str, str]:
    return {
        "brand_hint": row.brand_hint,
        "code": row.code,
        "source_file": row.source_file,
        "source_page": row.source_page,
        "source_date": row.source_date,
        "extraction_status": row.extraction_status,
        "primary_outcome": row.primary_outcome,
        "hold_reason": row.hold_reason,
        "qa_flags": row.qa_flags,
        "product_id": row.product_id,
        "proposed_price": row.proposed_price,
        "current_price": row.current_price,
        "pricing_policy_id": row.pricing_policy_id,
    }


def _hold_row(r: dict[str, str], code: str, hold_reason: str, qa_flags: list[str]) -> dict[str, str]:
    return {
        "brand_hint": r.get("brand_hint") or "",
        "code": code,
        "hold_reason": hold_reason,
        "qa_flags": "|".join(qa_flags),
        "source_file": r.get("file") or "",
        "source_page": r.get("page") or "",
        "extraction_status": r.get("status") or "",
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_execution_manifest(audit_dir: Path) -> dict[str, str]:
    names = [
        "SOURCE_ROW_LEDGER.csv",
        "UPDATE_PRODUCTS.csv",
        "CREATE_PRODUCTS.csv",
        "UNCHANGED_PRODUCTS.csv",
        "HOLD_PRODUCTS.csv",
        "SOURCE_DOCUMENTS.csv",
    ]
    hashes: dict[str, str] = {}
    lines: list[str] = []
    for name in names:
        path = audit_dir / name
        if path.is_file() and path.stat().st_size:
            digest = sha256_file(path)
            hashes[name] = digest
            lines.append(f"{digest}  {name}")
    (audit_dir / "EXECUTION_MANIFEST.sha256").write_text(
        "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8"
    )
    return hashes


def _build_commercial_report(
    auth_rows: list[dict[str, str]],
    catalog: list[CatalogRow],
    idx: dict[tuple[str, str], list[CatalogRow]],
) -> str:
    by_file: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in auth_rows:
        by_file[r.get("file") or "unknown"].append(r)

    lines = [
        "# Commercial pricing decision report (AST)",
        "",
        f"## Approved policy (`{OWNER_COMMERCIAL_PRICING_POLICY_APPROVED}`)",
        "",
        f"- **Policy ID:** `{PRICING_POLICY_ID}`",
        "- **Supplier list (Rial):** raw PDF comma-grouped values.",
        "- **List Toman:** `Rial ÷ 10`.",
        "- **Cash discount:** purchase-side only (not storefront promo).",
        "- **Net acquisition (info):** `list_toman × (1 − discount/100)`.",
        "- **Customer `base_price`:** `list_toman` (no invented margin).",
        f"- **Procurement QA flag:** `{QA_DEVICE_SPARE_DISCOUNT_SPLIT}` (does not block sell price).",
        "",
        "| PDF family | SKU | Current | List Toman | Cash % | Net purchase | Proposed sell | Basis |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]

    for fname in sorted(by_file, key=lambda k: -len(by_file[k]))[:15]:
        sample = by_file[fname][0]
        code = norm_code(sample.get("code_candidate") or "")
        brand_id = BRAND_HINT_TO_ID.get(sample.get("brand_hint") or "", "")
        product = (idx.get((brand_id, code)) or [None])[0]
        rial = int(sample.get("source_price_rial") or 0)
        list_t = list_toman_from_rial(rial)
        disc, _ = parse_discount_percent(sample.get("cash_discount_label") or "")
        proposed, pol, _ = proposed_customer_price(rial, sample.get("cash_discount_label") or "")
        current = product.base_price if product else None
        net = net_purchase_toman(list_t, disc) if list_t and disc else None
        basis = pol if proposed else "n/a"
        lines.append(
            f"| {fname[:36]} | {code} | {current or ''} | {list_t or ''} | {disc or 'HOLD'} | "
            f"{net or ''} | {proposed or ''} | {basis} |"
        )

    lines += ["", f"## Owner approval recorded: `{OWNER_COMMERCIAL_PRICING_POLICY_APPROVED}`.", ""]
    return "\n".join(lines)


def _production_apply_plan(hashes: dict[str, str]) -> str:
    return f"""# Production APPLY plan

1. Owner accepts `{PRICING_POLICY_ID}` in COMMERCIAL_PRICING_DECISION.md.
2. Resolve HOLD / ABNORMAL_UPDATE_REVIEW rows (large-swing and duplicate-SKU collisions stay out of UPDATE; see `ABNORMAL_UPDATE_REVIEW.csv` for current count).
3. Per-row CREATE QA: set `approval_status={CREATE_APPROVAL_OWNER}` only on validated CREATE manifest rows.
4. Backup production DB.
5. Fresh catalog snapshot + stale-state check (UPDATE `expected_current_price` / SKU guards).
6. Dry-run: `python scripts/ops/ast_price_catalog_apply_once.py` (default; no DB write).
7. UPDATE canary → post-commit verify → CREATE canary → verify.
8. Full cohort APPLY (single transaction journal): `ast_price_catalog_apply_once.py --apply` with Category B env +
   manifest SHA/count confirmations. CLI returns `APPLIED` only after real UPDATE/CREATE execution and post-verify.
9. Post-verify API + storefront.

**Rollback (committed journal only):** `ast_price_catalog_apply_once.py --rollback --rollback-journal audit/.../journals/AST_APPLY_<batch>.json`
— UPDATE rollback only when current price still equals the applied price; CREATE rollback soft-deletes exact journal IDs
with no `order_items` activity.

**Authorization tokens:** `{OWNER_AUTH_APPLY}` / `{OWNER_AUTH_ROLLBACK}`

**Manifest SHA256**
- UPDATE: `{hashes.get("UPDATE_PRODUCTS.csv", "")}`
- CREATE: `{hashes.get("CREATE_PRODUCTS.csv", "")}`
- LEDGER: `{hashes.get("SOURCE_ROW_LEDGER.csv", "")}`
"""
