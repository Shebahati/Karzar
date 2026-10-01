"""Phase 2C manufacturer identity evidence model (read-only discovery).

No database or catalog mutation. Evidence rows must carry stable source locators
and preserved raw OEM codes before BACKFILL_EXACT is allowed.
"""

from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

REGISTRY_FIELDNAMES: list[str] = [
    "source_id",
    "brand",
    "manufacturer_code",
    "authority_tier",
    "source_type",
    "source_path",
    "source_sha256",
    "source_document_title",
    "source_page_index",
    "source_printed_page",
    "source_table",
    "source_row",
    "source_cell_or_column",
    "source_field_label",
    "raw_source_code",
    "canonical_candidate_code",
    "normalized_match_key",
    "source_item_description",
    "source_variant_description",
    "extraction_method",
    "mapping_basis",
    "oem_identity_field_proven",
    "source_path_or_url",
    "source_page_or_row",
    "source_quote_or_field",
    "sha256",
    "notes",
]

CONFLICT_NO = "NO_CONFLICT"
CONFLICT_HEURISTIC_UNRESOLVED = "HEURISTIC_CONFLICT_UNRESOLVED"
CONFLICT_RESOLVED_T1 = "RESOLVED_BY_TIER1"
CONFLICT_RESOLVED_T2 = "RESOLVED_BY_TIER2"
CONFLICT_RESOLVED_T3 = "RESOLVED_BY_TIER3"
CONFLICT_STRONG = "STRONG_EVIDENCE_CONFLICT"

_RESOLVED_STATUSES = frozenset({CONFLICT_RESOLVED_T1, CONFLICT_RESOLVED_T2, CONFLICT_RESOLVED_T3})

# Source types that cannot auto-enter BACKFILL_EXACT (identity column not proven OEM).
_INELIGIBLE_SOURCE_TYPES = frozenset(
    {
        "ast_supplier_enumerator",
        "image_pdf_without_text_layer",
    },
)

_CATEGORY_A = frozenset({"میکرومتر", "micrometer", "ساعت", "گیج"})
_CATEGORY_B = frozenset({"کولیس", "caliper", "ورنیه", "vernier"})
_CATEGORY_C = frozenset({"دریل", "drill", "مگنت", "magnetic"})
_CATEGORY_CONTRADICTIONS: tuple[frozenset[str], frozenset[str]] = (
    (_CATEGORY_A, _CATEGORY_B),
    (_CATEGORY_C, _CATEGORY_A),
)


def norm_brand(name: str | None) -> str:
    if not name:
        return ""
    return name.split("|", 1)[0].strip().upper()


def detect_candidate_mismatch(
    title_candidate: str | None,
    sku_candidate: str | None,
) -> bool:
    """Title-derived code and SKU differ after whitespace normalization."""
    if not title_candidate or not sku_candidate:
        return False
    return title_candidate.replace(" ", "") != sku_candidate.replace(" ", "")


def detect_heuristic_identity_conflict(
    title_candidate: str | None,
    sku_candidate: str | None,
) -> bool:
    """Canonical predicate: mismatch plus digit in both signals (matches classifier)."""
    if not detect_candidate_mismatch(title_candidate, sku_candidate):
        return False
    if not re.search(r"\d", title_candidate or ""):
        return False
    if not re.search(r"\d", sku_candidate or ""):
        return False
    return True


def legacy_broad_heuristic_count_predicate(row: dict[str, Any]) -> bool:
    """Previous report over-count (title≠sku without digit gate). Diagnostic only."""
    title = row.get("title_candidate") or ""
    sku = row.get("sku_candidate") or ""
    if row.get("classification_reason") == "title_vs_sku":
        return True
    return detect_candidate_mismatch(title, sku)


def normalized_match_key(code: str | None) -> str:
    """Non-semantic join key: outer strip + NFC only."""
    if not code:
        return ""
    return unicodedata.normalize("NFC", code.strip())


def _row_get(row: dict[str, Any], *keys: str) -> str:
    for k in keys:
        v = row.get(k)
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return ""


def _tier_int(row: dict[str, Any]) -> int:
    try:
        return int(row.get("authority_tier") or 0)
    except (TypeError, ValueError):
        return 0


def evidence_registry_key(brand: str, code: str) -> str:
    return f"{norm_brand(brand)}|{normalized_match_key(code)}"


def load_evidence_registry_multimap(path: Any) -> dict[str, list[dict[str, Any]]]:
    """Preserve all Tier 1–3 rows per brand|normalized_match_key (no last-wins)."""
    from pathlib import Path

    p = Path(path) if path is not None else None
    out: dict[str, list[dict[str, Any]]] = {}
    if p is None or not p.exists():
        return out
    with p.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            brand = norm_brand(row.get("brand") or row.get("brand_name"))
            code = _row_get(
                row,
                "canonical_candidate_code",
                "manufacturer_code",
                "candidate_manufacturer_code",
            )
            tier = _tier_int(row)
            if not brand or not code or tier < 1 or tier > 3:
                continue
            key = evidence_registry_key(brand, code)
            out.setdefault(key, []).append(dict(row))
    return out


def has_stable_locator(row: dict[str, Any]) -> bool:
    source_type = _row_get(row, "source_type")
    if source_type in _INELIGIBLE_SOURCE_TYPES:
        return False
    page = _row_get(row, "source_page_index")
    sheet = _row_get(row, "source_sheet")
    line_rng = _row_get(row, "source_line_range")
    legacy_page = _row_get(row, "source_page_or_row")
    if page.isdigit() and int(page) >= 1:
        return True
    if sheet and _row_get(row, "source_row"):
        return True
    if line_rng:
        return True
    if legacy_page:
        return True
    return False


def source_type_eligible_for_exact(row: dict[str, Any]) -> bool:
    st = _row_get(row, "source_type")
    if st in _INELIGIBLE_SOURCE_TYPES:
        return False
    proven = _row_get(row, "oem_identity_field_proven").lower()
    if proven in {"0", "false", "no"}:
        return False
    if st == "ast_supplier_enumerator":
        return False
    return True


def evidence_completeness_ok(row: dict[str, Any]) -> tuple[bool, str]:
    brand = norm_brand(row.get("brand"))
    code = _row_get(
        row,
        "canonical_candidate_code",
        "manufacturer_code",
        "candidate_manufacturer_code",
    )
    tier = _tier_int(row)
    if not brand:
        return False, "missing_brand"
    if not code:
        return False, "missing_candidate_code"
    if tier not in (1, 2, 3):
        return False, "invalid_tier"
    if not _row_get(row, "source_id"):
        return False, "missing_source_id"
    if not _row_get(row, "source_path", "source_path_or_url"):
        return False, "missing_source_path"
    if not _row_get(row, "source_sha256", "sha256"):
        return False, "missing_source_sha256"
    raw = _row_get(row, "raw_source_code")
    if not raw:
        return False, "missing_raw_source_code"
    if not _row_get(row, "mapping_basis"):
        return False, "missing_mapping_basis"
    if not has_stable_locator(row):
        return False, "missing_stable_locator"
    if not source_type_eligible_for_exact(row):
        return False, "source_type_ineligible"
    return True, "ok"


def _lower_fold(text: str) -> str:
    return unicodedata.normalize("NFC", text).lower()


def _category_hits(text: str, bucket: frozenset[str]) -> bool:
    t = _lower_fold(text)
    return any(w in t for w in bucket)


def variant_compatible(product_name: str, source_description: str) -> tuple[bool, str]:
    name = product_name or ""
    desc = source_description or ""
    if not desc.strip():
        return True, "no_source_description"
    for a, b in _CATEGORY_CONTRADICTIONS:
        if _category_hits(name, a) and _category_hits(desc, b):
            return False, "category_contradiction"
        if _category_hits(name, b) and _category_hits(desc, a):
            return False, "category_contradiction"
    name_tokens = {
        t for t in re.split(r"[\s،,/|]+", _lower_fold(name)) if len(t) >= 3 and not t.isdigit()
    }
    desc_tokens = {
        t for t in re.split(r"[\s،,/|]+", _lower_fold(desc)) if len(t) >= 3 and not t.isdigit()
    }
    if name_tokens & desc_tokens:
        return True, "token_overlap"
    for nt in name_tokens:
        if len(nt) >= 4 and nt in _lower_fold(desc):
            return True, "substring_overlap"
    if len(desc_tokens) >= 2:
        return False, "variant_incompatible"
    return True, "sparse_description"


def _descriptions_conflict(a: str, b: str) -> bool:
    if not a.strip() or not b.strip():
        return False
    ok_a, _ = variant_compatible(a, b)
    ok_b, _ = variant_compatible(b, a)
    return not (ok_a and ok_b)


@dataclass(frozen=True)
class EvidencePick:
    row: dict[str, Any]
    conflict_status: str
    classification_reason: str
    heuristic_conflict: bool


def _tier_resolution_status(tier: int) -> str:
    if tier == 1:
        return CONFLICT_RESOLVED_T1
    if tier == 2:
        return CONFLICT_RESOLVED_T2
    if tier == 3:
        return CONFLICT_RESOLVED_T3
    return CONFLICT_HEURISTIC_UNRESOLVED


def _complete_usable_rows(
    records: Iterable[dict[str, Any]],
    *,
    product_name: str,
) -> list[dict[str, Any]]:
    usable: list[dict[str, Any]] = []
    for rec in records:
        ok, _ = evidence_completeness_ok(rec)
        if not ok:
            continue
        compat, _ = variant_compatible(product_name, _row_get(rec, "source_item_description"))
        if not compat:
            continue
        usable.append(rec)
    return usable


def detect_tier1_conflict(records: list[dict[str, Any]]) -> bool:
    tier1 = [r for r in records if _tier_int(r) == 1]
    if len(tier1) < 2:
        return False
    descs = [_row_get(r, "source_item_description") for r in tier1]
    for i, a in enumerate(descs):
        for b in descs[i + 1 :]:
            if _descriptions_conflict(a, b):
                return True
    raws = {_row_get(r, "raw_source_code") for r in tier1}
    if len(raws) > 1:
        return True
    return False


def pick_evidence_for_code(
    *,
    brand: str,
    code: str,
    product_name: str,
    evidence_map: dict[str, list[dict[str, Any]]],
    heuristic_conflict: bool,
    resolving_only: bool,
) -> EvidencePick | None:
    key = evidence_registry_key(brand, code)
    records = evidence_map.get(key, [])
    if not records:
        return None
    if detect_tier1_conflict(records):
        return EvidencePick(
            row=records[0],
            conflict_status=CONFLICT_STRONG,
            classification_reason="tier1_evidence_conflict",
            heuristic_conflict=heuristic_conflict,
        )
    usable = _complete_usable_rows(records, product_name=product_name)
    if not usable:
        return None
    usable.sort(key=lambda r: (_tier_int(r), _row_get(r, "source_id"), _row_get(r, "source_row")))
    best = usable[0]
    tier = _tier_int(best)
    if heuristic_conflict:
        if resolving_only:
            return EvidencePick(
                row=best,
                conflict_status=_tier_resolution_status(tier),
                classification_reason="authority_resolves_title_vs_sku",
                heuristic_conflict=True,
            )
        return None
    return EvidencePick(
        row=best,
        conflict_status=CONFLICT_NO,
        classification_reason="tier_registry_match",
        heuristic_conflict=False,
    )


def flatten_provenance(ev: dict[str, Any]) -> dict[str, str]:
    """Map evidence registry row → BACKFILL_EXACT audit columns."""
    return {
        "candidate_manufacturer_code": _row_get(
            ev, "canonical_candidate_code", "manufacturer_code"
        ),
        "raw_source_code": _row_get(ev, "raw_source_code"),
        "authority_tier": str(_tier_int(ev)),
        "source_id": _row_get(ev, "source_id"),
        "source_type": _row_get(ev, "source_type"),
        "source_path": _row_get(ev, "source_path", "source_path_or_url"),
        "source_sha256": _row_get(ev, "source_sha256", "sha256"),
        "source_page_index": _row_get(ev, "source_page_index"),
        "source_printed_page": _row_get(ev, "source_printed_page"),
        "source_sheet": _row_get(ev, "source_sheet"),
        "source_row": _row_get(ev, "source_row", "source_page_or_row"),
        "source_field_label": _row_get(ev, "source_field_label", "source_quote_or_field"),
        "source_item_description": _row_get(ev, "source_item_description"),
        "mapping_basis": _row_get(ev, "mapping_basis"),
    }


FREEZE_LOGIC_RELATIVE_PATHS: tuple[str, ...] = (
    "app/domain/phase2c_evidence.py",
    "scripts/audit_manufacturer_identity_phase2c_discovery.py",
    "scripts/phase2c_authority_extract.py",
    "scripts/build_phase2c_source_authority_registry.py",
    "scripts/phase2c_exact_cohort_freeze.py",
)


def _heuristic_outcome_bucket(row: dict[str, Any]) -> str:
    title = row.get("title_candidate") or ""
    sku = row.get("sku_candidate") or ""
    if not detect_heuristic_identity_conflict(title, sku):
        return "not_heuristic"
    if row.get("classification") == "HOLD_DUPLICATE_IDENTITY":
        return "duplicate_identity_conflicts"
    status = row.get("conflict_status") or ""
    if status == CONFLICT_RESOLVED_T1:
        return "resolved_by_tier_1"
    if status == CONFLICT_RESOLVED_T2:
        return "resolved_by_tier_2"
    if status == CONFLICT_RESOLVED_T3:
        return "resolved_by_tier_3"
    if status == CONFLICT_HEURISTIC_UNRESOLVED:
        return "heuristic_conflicts_unresolved"
    if status == CONFLICT_STRONG:
        return "strong_evidence_conflicts"
    return "heuristic_unclassified"


def conflict_resolution_report(classified: list[dict[str, Any]]) -> dict[str, Any]:
    candidate_mismatches = 0
    heuristic_conflicts = 0
    non_conflict_mismatches = 0
    buckets: dict[str, int] = {
        "resolved_by_tier_1": 0,
        "resolved_by_tier_2": 0,
        "resolved_by_tier_3": 0,
        "heuristic_conflicts_unresolved": 0,
        "strong_evidence_conflicts": 0,
        "duplicate_identity_conflicts": 0,
        "heuristic_unclassified": 0,
    }
    duplicate_all = 0
    for row in classified:
        title = row.get("title_candidate") or ""
        sku = row.get("sku_candidate") or ""
        mismatch = detect_candidate_mismatch(title, sku)
        heuristic = detect_heuristic_identity_conflict(title, sku)
        if mismatch:
            candidate_mismatches += 1
        if heuristic:
            heuristic_conflicts += 1
            bucket = _heuristic_outcome_bucket(row)
            buckets[bucket] = buckets.get(bucket, 0) + 1
        elif mismatch:
            non_conflict_mismatches += 1
        if row.get("classification") == "HOLD_DUPLICATE_IDENTITY":
            duplicate_all += 1

    heuristic_partition_sum = (
        buckets["resolved_by_tier_1"]
        + buckets["resolved_by_tier_2"]
        + buckets["resolved_by_tier_3"]
        + buckets["heuristic_conflicts_unresolved"]
        + buckets["strong_evidence_conflicts"]
        + buckets["duplicate_identity_conflicts"]
        + buckets["heuristic_unclassified"]
    )
    candidate_reconciles = candidate_mismatches == (
        heuristic_conflicts + non_conflict_mismatches
    )
    heuristic_reconciles = heuristic_conflicts == heuristic_partition_sum
    reconciles = candidate_reconciles and heuristic_reconciles

    legacy_broad = sum(1 for r in classified if legacy_broad_heuristic_count_predicate(r))

    return {
        "candidate_mismatches_total": candidate_mismatches,
        "heuristic_conflicts_total": heuristic_conflicts,
        "non_conflict_candidate_mismatches": non_conflict_mismatches,
        "resolved_by_tier_1": buckets["resolved_by_tier_1"],
        "resolved_by_tier_2": buckets["resolved_by_tier_2"],
        "resolved_by_tier_3": buckets["resolved_by_tier_3"],
        "heuristic_conflicts_unresolved": buckets["heuristic_conflicts_unresolved"],
        "strong_evidence_conflicts": buckets["strong_evidence_conflicts"],
        "duplicate_identity_conflicts": duplicate_all,
        "duplicate_identity_within_heuristic": buckets["duplicate_identity_conflicts"],
        "heuristic_unclassified": buckets["heuristic_unclassified"],
        "legacy_broad_heuristic_conflicts_total": legacy_broad,
        "legacy_broad_minus_canonical_heuristic": legacy_broad - heuristic_conflicts,
        "conflict_accounting_reconciles": reconciles,
        # Back-compat keys
        "unresolved_conflicts": buckets["heuristic_conflicts_unresolved"],
        "duplicate_identity_holds": duplicate_all,
    }


def build_conflict_accounting_delta_rows(
    classified: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Rows counted by legacy broad predicate but not canonical heuristic (or vice versa)."""
    delta: list[dict[str, str]] = []
    for row in classified:
        title = row.get("title_candidate") or ""
        sku = row.get("sku_candidate") or ""
        broad = legacy_broad_heuristic_count_predicate(row)
        canonical = detect_heuristic_identity_conflict(title, sku)
        if broad == canonical:
            continue
        why_report = []
        why_classifier = []
        if broad:
            why_report.append("legacy_broad_title_sku_mismatch_or_reason")
        if canonical:
            why_classifier.append("canonical_digit_mismatch")
        if detect_candidate_mismatch(title, sku) and not canonical:
            why_classifier.append("mismatch_without_both_digits")
        delta.append(
            {
                "product_id": str(row.get("product_id") or ""),
                "brand": str(row.get("brand_name") or ""),
                "name": str(row.get("name") or ""),
                "sku": str(row.get("sku") or ""),
                "title_candidate": title,
                "sku_candidate": sku,
                "classification": str(row.get("classification") or ""),
                "conflict_status": str(row.get("conflict_status") or ""),
                "why_counted_in_report": "|".join(why_report) or "not_in_legacy_broad",
                "why_not_counted_by_classifier": "|".join(why_classifier)
                or "not_canonical_heuristic",
            }
        )
    delta.sort(key=lambda r: r["product_id"])
    return delta


def frozen_exact_row_provenance_complete(row: dict[str, Any]) -> tuple[bool, str]:
    required = [
        "candidate_manufacturer_code",
        "raw_source_code",
        "source_id",
        "source_type",
        "source_path",
        "source_sha256",
        "source_field_label",
        "source_item_description",
        "mapping_basis",
        "conflict_status",
        "classification_reason",
    ]
    for key in required:
        if not str(row.get(key) or "").strip():
            return False, f"missing_{key}"
    try:
        tier = int(row.get("authority_tier") or 0)
    except (TypeError, ValueError):
        return False, "invalid_tier"
    if tier not in (1, 2, 3):
        return False, "invalid_tier"
    page = str(row.get("source_page_index") or "").strip()
    sheet = str(row.get("source_sheet") or "").strip()
    srow = str(row.get("source_row") or "").strip()
    if not (page.isdigit() or (sheet and srow)):
        return False, "missing_stable_locator"
    status = str(row.get("conflict_status") or "")
    if status in {CONFLICT_HEURISTIC_UNRESOLVED, CONFLICT_STRONG}:
        return False, "forbidden_conflict_status_on_exact"
    if status and status not in _RESOLVED_STATUSES | {CONFLICT_NO}:
        return False, f"unexpected_conflict_status_{status}"
    return True, "ok"


def freeze_manifest_logic_file_hashes(repo_root: Any) -> dict[str, str]:
    from pathlib import Path

    root = Path(repo_root)
    out: dict[str, str] = {}
    for rel in FREEZE_LOGIC_RELATIVE_PATHS:
        path = root / rel
        if path.is_file():
            h = hashlib.sha256()
            with path.open("rb") as fh:
                for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                    h.update(chunk)
            out[rel] = h.hexdigest()
    return out


BACKFILL_EXACT_COLUMNS: list[str] = [
    "product_id",
    "brand_id",
    "brand_name",
    "current_name",
    "sku",
    "current_manufacturer_code",
    "candidate_manufacturer_code",
    "raw_source_code",
    "authority_tier",
    "source_id",
    "source_type",
    "source_path",
    "source_sha256",
    "source_page_index",
    "source_printed_page",
    "source_sheet",
    "source_row",
    "source_field_label",
    "source_item_description",
    "mapping_basis",
    "conflict_status",
    "classification_reason",
]
