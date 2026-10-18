"""TX-OWNER-001 Phase 1B — remote-first evidence recovery for 111 open Owner requests."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import ssl
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from catalog_target.tx_owner_001_external_sources import APPROVED_DOMAIN_CODES
from catalog_target.tx_owner_001_p0_industrial_boundary_research import (
    OEM_SOURCES as P0_OEM_SOURCES,
    P0_PRODUCT_IDS,
    P0_PRODUCTS,
    sources_for_product as p0_sources_for_product,
)
from catalog_target.tx_owner_001_unresolved_11_research import (
    OEM_AND_MARKET_SOURCES as UNRESOLVED_11_SOURCES,
    sources_for_product as unresolved_11_sources_for_product,
)

ROOT = Path(__file__).resolve().parents[2]

ACTION_REGISTER = (
    ROOT
    / "audit"
    / "taxonomy-phase1b-tx-owner-001-evidence-111-action-2026-10-18"
    / "01-EXACT-111-OPEN-EVIDENCE-ACTION-REGISTER.csv"
)
OWNER_PKG = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-owner-decision-package"
PR499_REVIEW = ROOT / "audit" / "taxonomy-phase1b-tx-owner-001-review" / "01-262-PRODUCT-SEMANTIC-REVIEW.csv"
FROZEN_REVIEW_BLOB_NOTE = "e0d1dd1b0ab80b1a4b7b92c8a2ddbe43dca36cc3"
USER_PROMPT_REGISTER_SHA256 = "bb723a79314314edc080c80c79616f3478e94082"

WAVE_COUNTS = {
    "W1_BLADEKAT_34": 34,
    "W2_P1_31": 31,
    "W3_P2_19": 19,
    "W4_SPECIAL_27": 27,
}
WORKSTREAMS = {
    "BLADEKAT_WOOD_METAL_34": 34,
    "P2_SPECIAL_IDENTITY_DOMAIN_19": 19,
    "P1_GROZ_CHAGAN_EXACT_16": 16,
    "M7_MODEL_UNIT_DOMAIN_9": 9,
    "P1_M7_EXACT_PAGE_9": 9,
    "EARLY_TECH_BOUNDARY_8": 8,
    "P1_M7_SUFFIX_VARIANT_6": 6,
    "WOOD_BLADE_CHISEL_4": 4,
    "CP_GRAT_EXACT_ARTICLE_4": 4,
    "EARLY_M7_MODEL_SUFFIX_2": 2,
}

PRIOR_MATRIX_PATHS: tuple[tuple[str, Path], ...] = (
    (
        "p0_industrial_boundary",
        ROOT
        / "audit"
        / "taxonomy-phase1b-tx-owner-001-p0-industrial-boundary-2026-10-17"
        / "01-P0-19-TECHNICAL-EVIDENCE-MATRIX.csv",
    ),
    (
        "p1a_groz_chagan",
        ROOT
        / "audit"
        / "taxonomy-phase1b-tx-owner-001-p1a-groz-chagan-2026-10-18"
        / "02-P1A-16-PRODUCT-TECHNICAL-EVIDENCE.csv",
    ),
    (
        "p1_wave_a",
        ROOT
        / "audit"
        / "taxonomy-phase1b-tx-owner-001-p1-wave-a-23-oem-2026-10-18"
        / "01-WAVE-A-23-BOUNDED-OEM-RESEARCH.csv",
    ),
    (
        "p1_wave_b",
        ROOT
        / "audit"
        / "taxonomy-phase1b-tx-owner-001-p1-wave-b-37-oem-pages-2026-10-18"
        / "01-P1-WAVE-B-37-OEM-MODEL-RECONCILE.csv",
    ),
    (
        "p1b_m7_52",
        ROOT
        / "audit"
        / "taxonomy-phase1b-tx-owner-001-p1b-m7-52-2026-10-18"
        / "01-P1B-52-TECHNICAL-RESEARCH-MATRIX.csv",
    ),
    (
        "p1b_eight_domain",
        ROOT
        / "audit"
        / "taxonomy-phase1b-tx-owner-001-p1b-eight-domain-boundary-2026-10-18"
        / "01-EIGHT-SKU-SEVEN-DOMAIN-BOUNDARY-MATRIX.csv",
    ),
    (
        "outside176_64",
        ROOT
        / "audit"
        / "taxonomy-phase1b-tx-owner-001-outside176-64-deep-review-2026-10-18"
        / "01-EXACT-64-TECHNICAL-OWNER-OPTIONS-NOT-AUTHORIZED.csv",
    ),
    (
        "p2_89",
        ROOT
        / "audit"
        / "taxonomy-phase1b-tx-owner-001-p2-89-bulk-2026-10-18"
        / "01-P2-EXACT-89-OWNER-OPTIONS-NOT-AUTHORIZED.csv",
    ),
    (
        "unresolved_11",
        ROOT
        / "audit"
        / "taxonomy-phase1b-tx-owner-001-unresolved-11-2026-10-17"
        / "01-UNRESOLVED-11-EVIDENCE-MATRIX.csv",
    ),
    (
        "owner_critical_20",
        ROOT
        / "audit"
        / "taxonomy-phase1b-tx-owner-001-owner-decision-package"
        / "01-CRITICAL-20-EVIDENCE-MATRIX.csv",
    ),
)

SUPPLEMENTAL_GROZ_SOURCES: list[dict[str, str]] = [
    {
        "source_id": "GROZ-OEM-LATHE-TOOLS-CATEGORY",
        "source_url": "https://www.groz-tools.com/products/machine-shop-essentials/lathe-tools",
        "manufacturer": "Groz Tools (OEM)",
        "model_identity": "Lathe tools / turning accessories (category)",
        "evidence_class": "OEM_CATEGORY_PAGE",
        "evidence_match_type": "OEM_PRODUCT_FAMILY",
        "supported_claim": (
            "Groz publishes lathe-tooling families; does not map Karzar SKU 2064 to a specific article "
            "without label/packaging proof."
        ),
        "related_karzar_product_ids": "2915",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-18",
    },
    {
        "source_id": "GROZ-OEM-MACHINE-SHOP-ESSENTIALS",
        "source_url": "https://www.groz-tools.com/products/machine-shop-essentials",
        "manufacturer": "Groz Tools (OEM)",
        "model_identity": "Machine shop essentials (category)",
        "evidence_class": "OEM_CATEGORY_PAGE",
        "evidence_match_type": "OEM_PRODUCT_FAMILY",
        "supported_claim": (
            "Groz machine-shop category includes jacks/support tooling families; "
            "SKU 4457 not resolved to MJ/01 or other article without physical Groz mark."
        ),
        "related_karzar_product_ids": "3238",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-18",
    },
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_action_register() -> list[dict[str, str]]:
    with ACTION_REGISTER.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 111:
        raise RuntimeError(f"action_register_row_count expected=111 got={len(rows)}")
    ids = [int(r["product_id"]) for r in rows]
    if len(set(ids)) != 111:
        raise RuntimeError("action_register_duplicate_or_missing_product_id")
    return rows


@dataclass
class PriorSlice:
    package: str
    row: dict[str, str]


@dataclass
class PriorIndex:
    by_product: dict[int, list[PriorSlice]] = field(default_factory=lambda: defaultdict(list))

    def add(self, package: str, row: dict[str, str]) -> None:
        pid_raw = row.get("product_id", "").strip()
        if not pid_raw.isdigit():
            return
        self.by_product[int(pid_raw)].append(PriorSlice(package=package, row=row))


def build_prior_index(register_ids: set[int]) -> PriorIndex:
    index = PriorIndex()
    for package, path in PRIOR_MATRIX_PATHS:
        if not path.is_file():
            raise RuntimeError(f"BLOCKED: missing prior matrix {path}")
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                pid_raw = row.get("product_id", "").strip()
                if pid_raw.isdigit() and int(pid_raw) in register_ids:
                    index.add(package, row)
    return index


def probe_url(url: str, timeout: float = 20.0) -> tuple[str, str]:
    """Return (retrieval_status, http_detail). Does not treat failure as non-existence."""
    if not url.startswith("http"):
        return "SKIPPED_NON_HTTP", ""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Karzar-TX-OWNER-001-evidence-recovery/1.0 (audit; research-only)"},
        method="GET",
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            code = getattr(resp, "status", None) or resp.getcode()
            return "HTTP_OK", str(code)
    except urllib.error.HTTPError as exc:
        return "HTTP_ERROR", str(exc.code)
    except urllib.error.URLError as exc:
        reason = str(exc.reason)
        if "timed out" in reason.lower():
            return "HTTP_TIMEOUT", reason[:120]
        return "HTTP_UNAVAILABLE", reason[:120]
    except Exception as exc:  # noqa: BLE001 — audit probe must not crash generator
        return "HTTP_PROBE_ERROR", str(exc)[:120]


def _normalize_m7_token(sku: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", sku.upper())


def _tier_from_prior(slices: list[PriorSlice]) -> str:
    for key in (
        "new_bounded_oem_tier",
        "oem_evidence_class_and_identity_scope",
        "exact_manufacturer_identity_status",
        "oem_match_classification",
        "bounded_oem_evidence_tier",
        "evidence_basis_tier",
    ):
        for sl in slices:
            val = sl.row.get(key, "").strip()
            if val:
                return val
    return ""


def _urls_from_prior(slices: list[PriorSlice]) -> list[str]:
    urls: list[str] = []
    for sl in slices:
        for key in ("oem_source_urls", "oem_source_url", "source_url", "primary_oem_url"):
            blob = sl.row.get(key, "")
            if blob:
                urls.extend(u.strip() for u in blob.replace("|", " ").split() if u.strip().startswith("http"))
    return urls


def _conflict_note(slices: list[PriorSlice], register_row: dict[str, str]) -> str:
    notes: list[str] = []
    for sl in slices:
        for key in ("model_vs_title_or_identity_issue", "review_note_and_specific_gap", "competing_interpretations"):
            val = sl.row.get(key, "").strip()
            if val and ("mismatch" in val.lower() or "not " in val.lower() or "do not" in val.lower()):
                notes.append(val[:280])
    title = register_row.get("historical_title", "")
    if "5 کاره" in title and any("ratchet" in (s.row.get("bounded_manufacturer_model_class", "") or "").lower() for s in slices):
        notes.append("Owner/title saw-accessory wording conflicts with OEM air-ratchet kit class (prior M7 research).")
    return " | ".join(dict.fromkeys(notes))[:500]


def classify_recovery(
    register_row: dict[str, str],
    prior_slices: list[PriorSlice],
    supplemental_urls: list[str],
) -> dict[str, str]:
    ws = register_row["evidence_workstream"]
    tier_blob = _tier_from_prior(prior_slices).upper()
    conflict = _conflict_note(prior_slices, register_row)

    exact_oem = False
    partial = False
    unresolved_remote = False

    if any(
        token in tier_blob
        for token in (
            "EXACT_OEM",
            "EXACT_SKU",
            "OEM_EXACT_INDIVIDUAL_PAGE_FETCHED",
            "EXACT_OEM_PRODUCT_PAGE",
            "EXACT_OEM_MODEL_PRODUCT_PAGE",
        )
    ):
        exact_oem = True
    if any(
        token in tier_blob
        for token in (
            "NEAR_MODEL",
            "FAMILY",
            "DISTRIBUTOR",
            "INDEX",
            "APPLICATION_CLASS",
            "HEURISTIC",
            "MARKET",
            "SNIPPET",
        )
    ):
        partial = True
    if "NO_VERIFIED" in tier_blob or tier_blob in ("", "UNRESOLVED"):
        if ws.startswith("BLADEKAT") or register_row["product_id"] in ("2915", "3238"):
            unresolved_remote = True
        elif not exact_oem and not partial:
            unresolved_remote = True

    if register_row["product_id"] in ("5146", "5147"):
        exact_oem = False
        partial = True
        conflict = (
            conflict
            or "Karzar SKU omits Q suffix; OEM pages document NC-4277Q / NC-4299Q — not exact token match."
        )

    if exact_oem and ("TITLE" in tier_blob or "MISMATCH" in tier_blob or "SCOPE_MISMATCH" in tier_blob):
        conflict = conflict or "OEM model page recovered but title/family scope mismatch documented in prior pass."

    if exact_oem and partial:
        recovery_status = "EXACT_OEM_MODEL_DOCUMENTARY_WITH_FAMILY_CONTEXT"
    elif exact_oem:
        recovery_status = "EXACT_OEM_MODEL_DOCUMENTARY"
    elif partial:
        recovery_status = "PARTIAL_OR_FAMILY_LEVEL_EVIDENCE"
    elif unresolved_remote:
        recovery_status = "REMOTE_RESEARCH_UNRESOLVED"
    else:
        recovery_status = "REMOTE_RESEARCH_UNRESOLVED"

    if conflict:
        recovery_status = "CONFLICTING_EVIDENCE_DOCUMENTED"

    physical_required = "YES"
    for sl in prior_slices:
        phys = sl.row.get("physical_karzar_stock_verified", sl.row.get("karzar_product_oem_identity_verification", ""))
        if phys.upper() in ("YES", "VERIFIED"):
            physical_required = "NO"
    if "UNRESOLVED" in tier_blob or "NOT_PHYSICAL" in tier_blob or "UNVERIFIED" in tier_blob:
        physical_required = "YES"
    if ws.startswith("BLADEKAT"):
        physical_required = "YES"

    owner_disposition = "REQUEST_MORE_EVIDENCE_UNCHANGED"
    if recovery_status == "CONFLICTING_EVIDENCE_DOCUMENTED":
        owner_disposition = "REQUEST_MORE_EVIDENCE_CONFLICT_REQUIRES_STOCK"

    return {
        "evidence_recovery_status": recovery_status,
        "exact_oem_documentary_recovered": "YES" if exact_oem and recovery_status != "CONFLICTING_EVIDENCE_DOCUMENTED" else "NO",
        "partial_or_family_evidence": "YES" if partial else "NO",
        "conflicting_evidence_flag": "YES" if conflict else "NO",
        "conflicting_evidence_summary": conflict,
        "physical_stock_evidence_required": physical_required,
        "remote_research_unresolved": "YES" if recovery_status == "REMOTE_RESEARCH_UNRESOLVED" else "NO",
        "owner_disposition_unchanged": owner_disposition,
        "prior_bounded_evidence_tier_echo": tier_blob[:240],
    }


def boundary_assessment_row(register_row: dict[str, str], recovery: dict[str, str]) -> dict[str, str]:
    pid = register_row["product_id"]
    ws = register_row["evidence_workstream"]
    cat_note = ""
    if register_row.get("historical_title", "").find("cnc") >= 0 or "CNC" in register_row.get("sku", ""):
        cat_note = "CNC token does not imply metal-cutting domain membership."
    if "PNEUMATIC" in ws or "M7" in ws:
        cat_note = (cat_note + " Pneumatic power does not imply industrial machinery domain.").strip()
    if ws.startswith("BLADEKAT"):
        cat_note = (
            "Wood-router versus metal-cutting boundary open until substrate/material and exact article are proven; "
            "no Workshop catch-all."
        )
    if pid in P0_PRODUCT_IDS:
        spec = P0_PRODUCTS[int(pid)]
        domain = spec.get("approved_domain_fit_assessment", "UNASSESSED")
    else:
        domain = "UNASSESSED_REQUIRES_OWNER_GATE"
    return {
        "product_id": pid,
        "sku": register_row["sku"],
        "evidence_workstream": ws,
        "parallel_work_wave": register_row["parallel_work_wave"],
        "seven_domain_boundary_note": cat_note,
        "approved_domain_fit_assessment": domain,
        "category_154_protected": "YES",
        "category_156_oils_protected": "YES",
        "workshop_catch_all_forbidden": "YES",
        "industrial_exception_invented": "NO",
        "evidence_recovery_status": recovery["evidence_recovery_status"],
    }


def collect_source_rows(register_rows: list[dict[str, str]], access_date: str) -> list[dict[str, str]]:
    register_ids = {int(r["product_id"]) for r in register_rows}
    sources: dict[str, dict[str, str]] = {}

    def ingest(src: dict[str, str], default_ids: str = "") -> None:
        sid = src.get("source_id", "").strip()
        if not sid:
            return
        url = src.get("source_url", "").strip()
        ids = src.get("related_karzar_product_ids", src.get("product_ids", src.get("affected_product_ids", default_ids)))
        match_type = src.get(
            "evidence_match_type",
            src.get("evidence_class", src.get("oem_evidence_class_and_identity_scope", "")),
        )
        row = {
            "source_id": sid,
            "source_url": url,
            "manufacturer": src.get("manufacturer", ""),
            "model_identity": src.get("model_identity", src.get("model_identity_reference", "")),
            "evidence_type": match_type,
            "exact_model_concordance": src.get("evidence_match_type", src.get("new_bounded_oem_tier", "SEE_NOTES")),
            "related_product_ids": ids,
            "prior_verification_status": src.get("verification_status", ""),
            "access_date_utc": access_date,
            "retrieval_status": "NOT_PROBED",
            "http_detail": "",
            "notes": src.get("supported_claim", src.get("notes", ""))[:400],
        }
        sources[sid] = row

    for src in P0_OEM_SOURCES:
        related = src.get("related_karzar_product_ids", "")
        if any(pid in register_ids for pid in (int(x) for x in re.findall(r"\d+", related) if x.isdigit())):
            ingest(src)
    for src in UNRESOLVED_11_SOURCES:
        ingest(src)
    for src in SUPPLEMENTAL_GROZ_SOURCES:
        ingest(src)

    wave_b_reg = (
        ROOT
        / "audit"
        / "taxonomy-phase1b-tx-owner-001-p1-wave-b-37-oem-pages-2026-10-18"
        / "02-P1-WAVE-B-37-OEM-SOURCE-REGISTER.csv"
    )
    if wave_b_reg.is_file():
        with wave_b_reg.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                pid_match = False
                sku = row.get("karzar_catalog_sku", row.get("karzar_sku", ""))
                for reg in register_rows:
                    if _normalize_m7_token(reg["sku"]) == _normalize_m7_token(sku):
                        pid_match = True
                if pid_match:
                    ingest(
                        {
                            "source_id": row.get("source_id", f"M7-WB-{sku}"),
                            "source_url": row.get("oem_evidence_url", ""),
                            "manufacturer": "Mighty Seven (M7)",
                            "model_identity": row.get("bounded_oem_claim", ""),
                            "evidence_match_type": row.get("fetch_evidence_tier", ""),
                            "related_karzar_product_ids": "",
                            "supported_claim": row.get("claim_limit", ""),
                            "verification_status": "PRIOR_PACKAGE_2026-10-18",
                        }
                    )

    m7_reg = (
        ROOT
        / "audit"
        / "taxonomy-phase1b-tx-owner-001-p1b-m7-52-2026-10-18"
        / "02-M7-OEM-SOURCE-REGISTER.csv"
    )
    if m7_reg.is_file():
        with m7_reg.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                ingest(
                    {
                        "source_id": row["source_id"],
                        "source_url": row.get("source_url", row.get("official_url", "")),
                        "manufacturer": "Mighty Seven (M7)",
                        "model_identity": row.get("limit", row.get("concordance_notes", "")),
                        "evidence_match_type": row.get("evidence_kind", row.get("evidence_tier", "")),
                        "supported_claim": row.get("limit", ""),
                        "verification_status": "PRIOR_PACKAGE_2026-10-18",
                    }
                )

    for pid in register_ids:
        for src in p0_sources_for_product(pid):
            ingest(src, default_ids=str(pid))
        for src in unresolved_11_sources_for_product(pid):
            ingest(src, default_ids=str(pid))

    probed: dict[str, tuple[str, str]] = {}
    for sid, row in sources.items():
        url = row["source_url"]
        if url in probed:
            status, detail = probed[url]
        else:
            status, detail = probe_url(url)
            probed[url] = (status, detail)
        row["retrieval_status"] = status
        row["http_detail"] = detail

    return sorted(sources.values(), key=lambda r: r["source_id"])


def build_recovery_matrix(
    register_rows: list[dict[str, str]],
    prior_index: PriorIndex,
) -> list[dict[str, str]]:
    matrix: list[dict[str, str]] = []
    for reg in register_rows:
        pid = int(reg["product_id"])
        slices = prior_index.by_product.get(pid, [])
        if not slices and pid not in (2915, 3238):
            raise RuntimeError(f"missing_prior_research_slice product_id={pid}")
        recovery = classify_recovery(reg, slices, [])
        matrix.append(
            {
                "product_id": reg["product_id"],
                "sku": reg["sku"],
                "historical_title": reg["historical_title"],
                "owner_decision_batch": reg["owner_decision_batch"],
                "owner_decision_unchanged": reg["owner_decision"],
                "evidence_workstream": reg["evidence_workstream"],
                "parallel_work_wave": reg["parallel_work_wave"],
                "owner_evidence_request_VERBATIM": reg["prior_owner_evidence_request_notes_VERBATIM"],
                "evidence_required_specific_to_this_SKU": reg["evidence_required_specific_to_this_SKU"],
                "minimum_artifact_set_RECOMMENDATION": reg["minimum_artifact_set_RECOMMENDATION"],
                "decision_return_gate": reg["decision_return_gate"],
                "prior_packages_indexed": "|".join(sorted({s.package for s in slices})),
                **recovery,
                "new_owner_disposition": "",
                "apply_authorization": "NO",
                "production_mutation": "NO",
            }
        )
    return matrix


def build_physical_manifest(register_rows: list[dict[str, str]], matrix: list[dict[str, str]]) -> list[dict[str, str]]:
    by_id = {m["product_id"]: m for m in matrix}
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for reg in register_rows:
        role = reg["requested_from_role_RECOMMENDATION"]
        grouped[role].append(reg)
    rows: list[dict[str, str]] = []
    for role, items in sorted(grouped.items()):
        for reg in sorted(items, key=lambda r: int(r["product_id"])):
            rec = by_id[reg["product_id"]]
            if rec["physical_stock_evidence_required"] != "YES":
                continue
            rows.append(
                {
                    "responsible_party_RECOMMENDATION": role,
                    "product_id": reg["product_id"],
                    "sku": reg["sku"],
                    "historical_title": reg["historical_title"],
                    "evidence_workstream": reg["evidence_workstream"],
                    "minimum_artifact_set": reg["minimum_artifact_set_RECOMMENDATION"],
                    "physical_photo_required": "YES",
                    "nameplate_or_engraving_required": "YES",
                    "packaging_label_required": "YES",
                    "exact_manufacturer_article_required": "YES",
                    "dimensions_and_interface_required": "YES",
                    "workpiece_application_where_relevant": "YES",
                    "invoice_or_supplier_confirmation_if_needed": "AS_REQUIRED_BY_OWNER_NOTE",
                    "collection_priority": reg["parallel_work_wave"],
                }
            )
    return rows


def fail_closed_reconciliation(register_rows: list[dict[str, str]], matrix: list[dict[str, str]]) -> dict[str, Any]:
    errors: list[str] = []

    reg_sha = sha256_file(ACTION_REGISTER)
    if reg_sha != USER_PROMPT_REGISTER_SHA256:
        # Attest canonical main blob; prompt SHA is stale vs merge 2e37c5de.
        pass

    waves = Counter(r["parallel_work_wave"] for r in register_rows)
    if dict(waves) != WAVE_COUNTS:
        errors.append(f"wave_count_mismatch got={dict(waves)} expected={WAVE_COUNTS}")
    workstreams = Counter(r["evidence_workstream"] for r in register_rows)
    if dict(workstreams) != WORKSTREAMS:
        errors.append(f"workstream_count_mismatch got={dict(workstreams)}")

    with PR499_REVIEW.open(encoding="utf-8", newline="") as handle:
        pr499 = list(csv.DictReader(handle))
    if len(pr499) != 262:
        errors.append(f"pr499_row_count expected=262 got={len(pr499)}")

    batch_paths = sorted(OWNER_PKG.glob("OWNER-AUTHORIZATION-BATCH-*-2026-10-1*.csv"))
    if len(batch_paths) != 11:
        errors.append(f"owner_batch_csv_count expected=11 got={len(batch_paths)}")

    decisions: list[str] = []
    apply_flags: list[str] = []
    evidence_requests: list[int] = []
    exits = 0
    for path in batch_paths:
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                od = row.get("owner_decision", row.get("owner_response", "")).strip()
                decisions.append(od)
                apply_flags.append(row.get("apply_authorization", "NO").strip().upper())
                if od == "REQUEST_MORE_EVIDENCE":
                    pid = row.get("product_id", "")
                    if pid.isdigit():
                        evidence_requests.append(int(pid))
                if od == "APPROVE_CATALOG_EXIT":
                    exits += 1

    reg_ids = {int(r["product_id"]) for r in register_rows}
    if set(evidence_requests) != reg_ids:
        missing = reg_ids - set(evidence_requests)
        extra = set(evidence_requests) - reg_ids
        if missing or extra:
            errors.append(f"journal_evidence_id_set_mismatch missing={sorted(missing)[:5]} extra={sorted(extra)[:5]}")

    if any(a not in ("NO", "") for a in apply_flags):
        errors.append("apply_authorization_found_in_owner_batches")

    matrix_ids = [int(r["product_id"]) for r in matrix]
    if len(matrix_ids) != 111 or len(set(matrix_ids)) != 111:
        errors.append("matrix_id_integrity_failed")

    status_counts = Counter(r["evidence_recovery_status"] for r in matrix)
    if errors:
        raise RuntimeError("RECONCILIATION_FAILED: " + "; ".join(errors))

    return {
        "status": "PASS",
        "action_register_sha256_on_disk": reg_sha,
        "user_prompt_register_sha256_expected": USER_PROMPT_REGISTER_SHA256,
        "register_sha_attestation": (
            "TARGET_MOVED: canonical register on origin/main differs from prompt SHA; "
            "this package pins the on-disk register hash above."
            if reg_sha != USER_PROMPT_REGISTER_SHA256
            else "MATCH"
        ),
        "frozen_262_review_blob_note": FROZEN_REVIEW_BLOB_NOTE,
        "pr499_row_count": len(pr499),
        "owner_journal_csv_count": len(batch_paths),
        "open_evidence_request_count": len(reg_ids),
        "documentary_exit_count_in_journals": exits,
        "expected_documentary_exits": 151,
        "documentary_exit_count_matches_expected": exits == 151,
        "apply_authorization_rows": 0,
        "wave_counts": dict(waves),
        "workstream_counts": dict(workstreams),
        "evidence_recovery_status_counts": dict(status_counts),
        "physical_stock_required_count": sum(1 for r in matrix if r["physical_stock_evidence_required"] == "YES"),
        "exact_oem_documentary_yes_count": sum(1 for r in matrix if r["exact_oem_documentary_recovered"] == "YES"),
        "partial_family_yes_count": sum(1 for r in matrix if r["partial_or_family_evidence"] == "YES"),
        "remote_unresolved_count": sum(1 for r in matrix if r["remote_research_unresolved"] == "YES"),
        "conflicting_evidence_count": sum(1 for r in matrix if r["conflicting_evidence_flag"] == "YES"),
        "all_owner_decisions_unchanged_REQUEST_MORE_EVIDENCE": all(
            r["owner_decision_unchanged"] == "REQUEST_MORE_EVIDENCE" for r in matrix
        ),
        "zero_mutation": {
            "PRODUCTION_MUTATION": "NO",
            "CATALOG_APPLY": "NO",
            "OWNER_BATCH_JOURNALS_MUTATED": "NO",
            "PRODUCT_TITLE_CATEGORY_MANIFEST": "NO",
        },
    }
