"""TX-OWNER-001 Phase 1B — remote-first evidence recovery for 111 open Owner requests."""

from __future__ import annotations

import csv
import hashlib
import re
import ssl
import subprocess
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, field
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
CANONICAL_ACTION_REGISTER_GIT_BLOB_SHA1 = "bb723a79314314edc080c80c79616f3478e94082"

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

P1A_SOURCE_REGISTER = (
    ROOT
    / "audit"
    / "taxonomy-phase1b-tx-owner-001-p1a-groz-chagan-2026-10-18"
    / "03-P1A-SOURCE-REGISTER.csv"
)
P1A_PRODUCT_EVIDENCE = (
    ROOT
    / "audit"
    / "taxonomy-phase1b-tx-owner-001-p1a-groz-chagan-2026-10-18"
    / "02-P1A-16-PRODUCT-TECHNICAL-EVIDENCE.csv"
)
WAVE_A_SOURCE_REGISTER = (
    ROOT
    / "audit"
    / "taxonomy-phase1b-tx-owner-001-p1-wave-a-23-oem-2026-10-18"
    / "02-BOUNDED-OEM-SOURCE-REGISTER.csv"
)

# Wave-A bounded register uses shorthand Groz source_ids; canonical URLs/claims live in P1A register.
WAVE_A_TO_P1A_SOURCE_ID: dict[str, str] = {
    "GROZ-HACKSAWS": "GROZ-HACKSAW-HANDBOOK",
    "GROZ-HPL": "GROZ-HOLLOW-PUNCH",
    "GROZ-PUNCHES": "GROZ-PUNCH-LIST",
    "GROZ-STAMPS": "GROZ-HANDBOOK",
}

SUPPLEMENTAL_GROZ_SOURCES: list[dict[str, str]] = [
    {
        "source_id": "GROZ-OEM-LATHE-TOOLS-CATEGORY",
        "source_url": "https://www.groz-tools.com/products/machine-shop-essentials/lathe-tools",
        "manufacturer": "Groz Tools (OEM)",
        "model_identity": "Lathe tools / turning accessories (category)",
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
        "evidence_match_type": "OEM_PRODUCT_FAMILY",
        "supported_claim": (
            "Groz machine-shop category includes jacks/support tooling families; "
            "SKU 4457 not resolved to MJ/01 or other article without physical Groz mark."
        ),
        "related_karzar_product_ids": "3238",
        "verification_status": "HUMAN_VERIFIED_URL_2026-10-18",
    },
]

# Explicit positive OEM page tiers (full-token semantics; no substring match on "EXACT_OEM" alone).
POSITIVE_EXACT_OEM_TIER_FRAGMENTS: tuple[str, ...] = (
    "EXACT_OEM_PRODUCT_PAGE_MODEL",
    "EXACT_OEM_MODEL_PRODUCT_PAGE",
    "EXACT_SKU_OEM_PAGE",
    "OEM_EXACT_INDIVIDUAL_PAGE_FETCHED",
    "EXACT_OEM_INDIVIDUAL_PAGE_FETCHED",
    "EXACT_OEM_MODEL_SEARCH_SNIPPET_DIRECT_FETCH_FAILED_NOT_STOCK",
    "EXACT_OEM_MODEL_PRODUCT_PAGE",
)

NEGATIVE_TIER_FRAGMENTS: tuple[str, ...] = (
    "UNRESOLVED_NO_EXACT",
    "NO_EXACT_OEM",
    "NO_VERIFIED_EXACT",
    "NO_VERIFIED_OEM",
    "NO_VERIFIED_EXACT_BLADEKAT",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha1(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()


def verify_action_register_identity() -> dict[str, str]:
    blob = git_blob_sha1(ACTION_REGISTER)
    digest = sha256_file(ACTION_REGISTER)
    if blob != CANONICAL_ACTION_REGISTER_GIT_BLOB_SHA1:
        raise RuntimeError(
            f"ACTION_REGISTER_SOURCE_DRIFT git_blob_sha1={blob} "
            f"expected={CANONICAL_ACTION_REGISTER_GIT_BLOB_SHA1}"
        )
    return {
        "canonical_action_register_git_blob_sha1": blob,
        "canonical_action_register_raw_sha256": digest,
        "register_identity_attestation": "MATCH_CANONICAL_GIT_BLOB",
    }


def load_action_register() -> list[dict[str, str]]:
    verify_action_register_identity()
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
    """Transport probe only; HTTP 200 is not model-content concordance."""
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
    except Exception as exc:  # noqa: BLE001
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


def classify_tier_semantics(tier: str) -> str:
    """Return semantic bucket; negatives must be checked before positive EXACT fragments."""
    u = tier.upper().strip()
    if not u:
        return "UNKNOWN_EMPTY"
    for neg in NEGATIVE_TIER_FRAGMENTS:
        if neg in u:
            return "NEGATIVE_UNRESOLVED"
    if u == "UNRESOLVED" or u.startswith("UNRESOLVED_"):
        return "NEGATIVE_UNRESOLVED"
    if "NEAR_MODEL" in u:
        return "NEAR_MODEL_PARTIAL"
    if any(
        token in u
        for token in (
            "DISTRIBUTOR",
            "APPLICATION_CLASS",
            "MARKET_REFERENCE",
            "MARKET",
            "HEURISTIC",
            "CENSUS_ONLY",
            "OEM_CATEGORY",
            "OEM_MODEL_INDEX",
            "OEM_INDEX",
            "OEM_GROUPED",
            "INDEX_TOKEN",
            "FAMILY",
        )
    ):
        return "PARTIAL_FAMILY_OR_MARKET"
    for pos in POSITIVE_EXACT_OEM_TIER_FRAGMENTS:
        if pos in u:
            return "POSITIVE_EXACT_OEM_PAGE"
    return "PARTIAL_FAMILY_OR_MARKET" if u else "UNKNOWN_EMPTY"


def provenance_class_for_source(src: dict[str, str]) -> str:
    url = src.get("source_url", "").strip()
    match = src.get("evidence_match_type", src.get("evidence_class", "")).upper()
    mfr = src.get("manufacturer", "").lower()
    if not url:
        return "PRIOR_INDEXED_REFERENCE_NO_URL"
    if "mighty-seven.com/product/" in url:
        return "OFFICIAL_INDIVIDUAL_PRODUCT_PAGE"
    if "mighty-seven.com" in url and ("product_list" in url or "other_category" in url):
        return "MANUFACTURER_FAMILY_OR_INDEX"
    if "groz-tools.com" in url:
        return "OFFICIAL_MANUFACTURER_SOURCE"
    if "DISTRIBUTOR" in match or "indiamart" in url or "fastenersweb" in url:
        return "INDEPENDENT_DISTRIBUTOR"
    if "APPLICATION_CLASS" in match or "MARKET" in match or "RETAIL" in match:
        return "GENERAL_MARKET_APPLICATION_COMPARATOR"
    if "mighty-seven" in mfr or "groz" in mfr:
        return "OFFICIAL_MANUFACTURER_SOURCE"
    return "GENERAL_MARKET_APPLICATION_COMPARATOR"


def normalize_source_id(source_id: str) -> str:
    sid = source_id.strip()
    return WAVE_A_TO_P1A_SOURCE_ID.get(sid, sid)


def link_product_to_source(catalog: SourceCatalog, product_id: int, source_id: str) -> None:
    sid = normalize_source_id(source_id)
    if not sid or sid not in catalog.by_id:
        return
    if sid not in catalog.by_product[product_id]:
        catalog.by_product[product_id].append(sid)
    ids = {x for x in catalog.by_id[sid]["related_product_ids"].split(",") if x}
    ids.add(str(product_id))
    catalog.by_id[sid]["related_product_ids"] = ",".join(sorted(ids))


def model_concordance_for_match_type(match_type: str) -> str:
    u = match_type.upper()
    if "NEAR_MODEL" in u:
        return "NEAR_MODEL_NOT_EXACT_SKU"
    if any(p in u for p in POSITIVE_EXACT_OEM_TIER_FRAGMENTS):
        return "OEM_MODEL_PAGE_DOCUMENTED_NOT_KARZAR_STOCK"
    if "DISTRIBUTOR" in u or "FAMILY" in u or "INDEX" in u:
        return "FAMILY_OR_DISTRIBUTOR_NOT_EXACT_ARTICLE"
    if "APPLICATION_CLASS" in u or "MARKET" in u:
        return "APPLICATION_CLASS_ONLY"
    return "UNRESOLVED_CONCORDANCE"


@dataclass
class SourceCatalog:
    by_id: dict[str, dict[str, str]] = field(default_factory=dict)
    by_product: dict[int, list[str]] = field(default_factory=lambda: defaultdict(list))

    def add(self, src: dict[str, str], origin: str, default_pid: str = "") -> None:
        sid = src.get("source_id", "").strip()
        if not sid:
            return
        url = src.get("source_url", "").strip()
        ids_blob = src.get(
            "related_karzar_product_ids",
            src.get("product_ids", src.get("affected_product_ids", default_pid)),
        )
        pids = sorted({int(x) for x in re.findall(r"\d+", ids_blob) if x.isdigit()})
        match_type = src.get("evidence_match_type", src.get("evidence_class", ""))
        row = {
            "source_id": sid,
            "source_url": url,
            "manufacturer": src.get("manufacturer", ""),
            "model_identity": src.get("model_identity", ""),
            "evidence_match_type": match_type,
            "provenance_class": provenance_class_for_source(src),
            "model_content_concordance": model_concordance_for_match_type(match_type),
            "evidence_origin": origin,
            "related_product_ids": ",".join(str(p) for p in pids),
            "prior_verification_status": src.get("verification_status", ""),
            "supports_exact_karzar_sku": src.get("supports_exact_karzar_sku", ""),
            "notes": (src.get("supported_claim", src.get("notes", "")) or "")[:400],
        }
        if sid in self.by_id:
            existing = self.by_id[sid]
            merged = set(existing["related_product_ids"].split(",")) | {str(p) for p in pids}
            existing["related_product_ids"] = ",".join(sorted(x for x in merged if x))
        else:
            self.by_id[sid] = row
        for pid in pids:
            if sid not in self.by_product[pid]:
                self.by_product[pid].append(sid)


def build_source_catalog(register_rows: list[dict[str, str]]) -> SourceCatalog:
    register_ids = {int(r["product_id"]) for r in register_rows}
    sku_to_pid = {_normalize_m7_token(r["sku"]): int(r["product_id"]) for r in register_rows}
    catalog = SourceCatalog()

    for src in P0_OEM_SOURCES:
        related = src.get("related_karzar_product_ids", "")
        if any(pid in register_ids for pid in (int(x) for x in re.findall(r"\d+", related) if x.isdigit())):
            catalog.add(src, "PRIOR_AUDIT_PACKAGE_REINDEX")
    for src in UNRESOLVED_11_SOURCES:
        catalog.add(src, "PRIOR_AUDIT_PACKAGE_REINDEX")
    for src in SUPPLEMENTAL_GROZ_SOURCES:
        catalog.add(src, "SUPPLEMENTAL_OEM_CATEGORY_PASS")

    if not P1A_SOURCE_REGISTER.is_file():
        raise RuntimeError(f"BLOCKED: missing P1A source register {P1A_SOURCE_REGISTER}")
    with P1A_SOURCE_REGISTER.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            catalog.add(
                {
                    "source_id": row["source_id"],
                    "source_url": row["source_url"],
                    "manufacturer": "Groz Tools (OEM)",
                    "model_identity": row.get("claim_limit", ""),
                    "evidence_match_type": row.get("source_type", ""),
                    "supported_claim": row.get("claim_limit", ""),
                    "supports_exact_karzar_sku": row.get("supports_exact_karzar_sku", "NO"),
                    "verification_status": "PRIOR_P1A_SOURCE_REGISTER_2026-10-18",
                },
                "PRIOR_AUDIT_PACKAGE_REINDEX",
            )

    if WAVE_A_SOURCE_REGISTER.is_file():
        with WAVE_A_SOURCE_REGISTER.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                sid = row.get("source_id", "").strip()
                if sid.startswith("GROZ-"):
                    continue
                catalog.add(
                    {
                        "source_id": sid,
                        "source_url": row.get("url", ""),
                        "manufacturer": "Mighty Seven (M7)" if sid.startswith("M7-") else "",
                        "model_identity": row.get("claim_limit", ""),
                        "evidence_match_type": row.get("evidence_scope", ""),
                        "supported_claim": row.get("claim_limit", ""),
                        "supports_exact_karzar_sku": "NO",
                        "verification_status": "PRIOR_WAVE_A_REGISTER_2026-10-18",
                    },
                    "PRIOR_AUDIT_PACKAGE_REINDEX",
                )

    if P1A_PRODUCT_EVIDENCE.is_file():
        with P1A_PRODUCT_EVIDENCE.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                pid_raw = row.get("product_id", "").strip()
                if not pid_raw.isdigit() or int(pid_raw) not in register_ids:
                    continue
                link_product_to_source(catalog, int(pid_raw), row.get("source_id", ""))

    wave_b_reg = (
        ROOT
        / "audit"
        / "taxonomy-phase1b-tx-owner-001-p1-wave-b-37-oem-pages-2026-10-18"
        / "02-P1-WAVE-B-37-OEM-SOURCE-REGISTER.csv"
    )
    if wave_b_reg.is_file():
        with wave_b_reg.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                sku = row.get("karzar_catalog_sku", row.get("karzar_sku", ""))
                pid = sku_to_pid.get(_normalize_m7_token(sku))
                if pid is None:
                    continue
                catalog.add(
                    {
                        "source_id": row.get("source_id", f"M7-WB-{sku}"),
                        "source_url": row.get("oem_evidence_url", ""),
                        "manufacturer": "Mighty Seven (M7)",
                        "model_identity": row.get("bounded_oem_claim", ""),
                        "evidence_match_type": row.get("fetch_evidence_tier", ""),
                        "related_karzar_product_ids": str(pid),
                        "supported_claim": row.get("claim_limit", ""),
                        "verification_status": "PRIOR_PACKAGE_2026-10-18",
                    },
                    "PRIOR_AUDIT_PACKAGE_REINDEX",
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
                catalog.add(
                    {
                        "source_id": row["source_id"],
                        "source_url": row.get("official_url", row.get("source_url", "")),
                        "manufacturer": "Mighty Seven (M7)",
                        "model_identity": row.get("limit", ""),
                        "evidence_match_type": row.get("evidence_kind", ""),
                        "related_karzar_product_ids": "",
                        "supported_claim": row.get("limit", ""),
                        "verification_status": "PRIOR_PACKAGE_2026-10-18",
                    },
                    "PRIOR_AUDIT_PACKAGE_REINDEX",
                )

    for pid in register_ids:
        for src in p0_sources_for_product(pid):
            catalog.add(src, "PRIOR_AUDIT_PACKAGE_REINDEX", default_pid=str(pid))
        for src in unresolved_11_sources_for_product(pid):
            catalog.add(src, "PRIOR_AUDIT_PACKAGE_REINDEX", default_pid=str(pid))

    for _package, path in PRIOR_MATRIX_PATHS:
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                pid_raw = row.get("product_id", "").strip()
                if not pid_raw.isdigit() or int(pid_raw) not in register_ids:
                    continue
                pid = int(pid_raw)
                for key in ("source_id", "oem_source_id"):
                    link_product_to_source(catalog, pid, row.get(key, ""))
                blob = row.get("oem_source_ids", "")
                for sid in (s.strip() for s in blob.split("|") if s.strip()):
                    link_product_to_source(catalog, pid, sid)

    return catalog


def finalize_source_register(
    catalog: SourceCatalog,
    access_date: str,
    live_probe: bool,
) -> list[dict[str, str]]:
    probed: dict[str, tuple[str, str]] = {}
    rows: list[dict[str, str]] = []
    for sid in sorted(catalog.by_id):
        base = catalog.by_id[sid]
        url = base["source_url"]
        if not url:
            retrieval = "PRIOR_REFERENCE_NO_URL"
            detail = "not_a_live_recovery"
        elif not live_probe:
            retrieval = "TRANSPORT_PROBE_SKIPPED_REPRODUCIBLE_BUILD"
            detail = ""
        elif url in probed:
            retrieval, detail = probed[url]
        else:
            retrieval, detail = probe_url(url)
            probed[url] = (retrieval, detail)
        rows.append(
            {
                **base,
                "access_date_utc": access_date,
                "http_transport_status": retrieval,
                "http_detail": detail,
                "transport_note": (
                    "HTTP status is transport-only; not verified product-content concordance."
                    if url
                    else "Empty URL — prior indexed reference only."
                ),
            }
        )
    return rows


def _conflict_note(slices: list[PriorSlice], register_row: dict[str, str], catalog: SourceCatalog) -> str:
    notes: list[str] = []
    pid = int(register_row["product_id"])
    for sl in slices:
        for key in ("model_vs_title_or_identity_issue", "review_note_and_specific_gap", "competing_interpretations"):
            val = sl.row.get(key, "").strip()
            if val and ("mismatch" in val.lower() or "not " in val.lower() or "do not" in val.lower()):
                notes.append(val[:280])
    for sid in catalog.by_product.get(pid, []):
        src = catalog.by_id[sid]
        if src["model_content_concordance"] == "NEAR_MODEL_NOT_EXACT_SKU":
            notes.append(f"{sid}: near-model OEM reference; Karzar catalog token not exact match.")
    title = register_row.get("historical_title", "")
    if "5 کاره" in title and any(
        "ratchet" in (s.row.get("bounded_manufacturer_model_class", "") or "").lower() for s in slices
    ):
        notes.append("Owner/title saw-accessory wording conflicts with OEM air-ratchet kit class (prior M7 research).")
    return " | ".join(dict.fromkeys(notes))[:500]


def classify_recovery(
    register_row: dict[str, str],
    prior_slices: list[PriorSlice],
    catalog: SourceCatalog,
) -> dict[str, str]:
    ws = register_row["evidence_workstream"]
    pid = int(register_row["product_id"])
    tier_raw = _tier_from_prior(prior_slices)
    tier_sem = classify_tier_semantics(tier_raw)
    source_ids = catalog.by_product.get(pid, [])
    conflict = _conflict_note(prior_slices, register_row, catalog)

    has_official_product_page = any(
        catalog.by_id[sid]["provenance_class"] == "OFFICIAL_INDIVIDUAL_PRODUCT_PAGE" for sid in source_ids
    )
    has_near_model_source = any(
        catalog.by_id[sid]["model_content_concordance"] == "NEAR_MODEL_NOT_EXACT_SKU" for sid in source_ids
    )

    exact_oem = (
        tier_sem == "POSITIVE_EXACT_OEM_PAGE"
        and has_official_product_page
        and not has_near_model_source
        and register_row["product_id"] not in ("5146", "5147")
    )

    partial = tier_sem in ("NEAR_MODEL_PARTIAL", "PARTIAL_FAMILY_OR_MARKET") or has_near_model_source
    if tier_sem == "NEGATIVE_UNRESOLVED":
        partial = partial or bool(source_ids)

    unresolved_remote = tier_sem in ("NEGATIVE_UNRESOLVED", "UNKNOWN_EMPTY") and not exact_oem
    if ws.startswith("BLADEKAT") and tier_sem == "NEGATIVE_UNRESOLVED":
        unresolved_remote = True
        exact_oem = False

    if register_row["product_id"] in ("5146", "5147"):
        exact_oem = False
        partial = True
        conflict = conflict or "Karzar SKU omits Q suffix; OEM pages document NC-4277Q / NC-4299Q — not exact token match."

    if exact_oem and conflict:
        exact_oem = False

    if partial and not source_ids:
        partial = False
        if not exact_oem and not conflict:
            unresolved_remote = True
            recovery_status_preflight = "REMOTE_RESEARCH_UNRESOLVED"
        else:
            recovery_status_preflight = ""
    else:
        recovery_status_preflight = ""

    if exact_oem:
        recovery_status = "EXACT_OEM_MODEL_DOCUMENTARY"
    elif partial and conflict:
        recovery_status = "CONFLICTING_EVIDENCE_DOCUMENTED"
    elif partial:
        recovery_status = "PARTIAL_OR_FAMILY_LEVEL_EVIDENCE"
    elif conflict:
        recovery_status = "CONFLICTING_EVIDENCE_DOCUMENTED"
    elif unresolved_remote or recovery_status_preflight == "REMOTE_RESEARCH_UNRESOLVED":
        recovery_status = "REMOTE_RESEARCH_UNRESOLVED"
    else:
        recovery_status = "REMOTE_RESEARCH_UNRESOLVED"

    physical_required = "YES"
    if ws.startswith("BLADEKAT") or tier_sem == "NEGATIVE_UNRESOLVED" or "NOT_PHYSICAL" in tier_raw.upper():
        physical_required = "YES"

    return {
        "evidence_recovery_status": recovery_status,
        "exact_oem_documentary_recovered": "YES" if exact_oem else "NO",
        "partial_or_family_evidence": "YES" if partial else "NO",
        "conflicting_evidence_flag": "YES" if conflict else "NO",
        "conflicting_evidence_summary": conflict,
        "physical_stock_evidence_required": physical_required,
        "remote_research_unresolved": "YES" if recovery_status == "REMOTE_RESEARCH_UNRESOLVED" else "NO",
        "owner_disposition_unchanged": "REQUEST_MORE_EVIDENCE_UNCHANGED",
        "prior_bounded_evidence_tier_echo": tier_raw[:240],
        "evidence_tier_semantics": tier_sem,
        "traceable_source_ids": "|".join(source_ids),
    }


def boundary_assessment_row(
    register_row: dict[str, str],
    recovery: dict[str, str],
    prior_slices: list[PriorSlice],
) -> dict[str, str]:
    pid = register_row["product_id"]
    ws = register_row["evidence_workstream"]
    assessment_kind = "OWNER_GATE_PLACEHOLDER"
    domain = "UNASSESSED_REQUIRES_OWNER_GATE"
    bounded_note = ""

    for sl in prior_slices:
        if sl.package == "p1b_eight_domain":
            assessment_kind = "BOUNDED_PRIOR_SEVEN_DOMAIN_RESEARCH"
            domain = sl.row.get("seven_domain_fit_assessment_not_owner_authority", domain)
            bounded_note = sl.row.get("domain_boundary_rationale", "")[:300]
            break
        if sl.package == "p0_industrial_boundary":
            assessment_kind = "BOUNDED_P0_INDUSTRIAL_BOUNDARY"
            spec = P0_PRODUCTS.get(int(pid))
            if spec:
                domain = spec.get("approved_domain_fit_assessment", domain)
                bounded_note = spec.get("approved_domain_fit_assessment", "")
            break

    if ws.startswith("BLADEKAT"):
        assessment_kind = "BOUNDED_WOOD_VS_METAL_CUTTING_OPEN"
        bounded_note = (
            "Wood-router versus metal-cutting boundary open until substrate/material and exact article are proven; "
            "CNC token does not imply metal-cutting; no Workshop catch-all."
        )
    elif ws.startswith("EARLY_TECH_BOUNDARY"):
        assessment_kind = "BOUNDED_GROZ_IDENTITY_OPEN"
        bounded_note = "Groz article and physical application (metal vs wood / jack class) unresolved; no invented exception."
    elif "M7" in ws:
        if assessment_kind == "OWNER_GATE_PLACEHOLDER":
            assessment_kind = "BOUNDED_PNEUMATIC_OEM_CLASS_VS_DOMAIN"
        bounded_note = (bounded_note or "") + " Pneumatic power does not imply industrial machinery domain."

    return {
        "product_id": pid,
        "sku": register_row["sku"],
        "evidence_workstream": ws,
        "parallel_work_wave": register_row["parallel_work_wave"],
        "technical_assessment_kind": assessment_kind,
        "seven_domain_boundary_note": bounded_note[:400],
        "approved_domain_fit_assessment": domain,
        "owner_final_gate_required": "YES",
        "category_154_protected": "YES",
        "category_156_oils_protected": "YES",
        "workshop_catch_all_forbidden": "YES",
        "industrial_exception_invented": "NO",
        "evidence_recovery_status": recovery["evidence_recovery_status"],
    }


def build_recovery_matrix(
    register_rows: list[dict[str, str]],
    prior_index: PriorIndex,
    catalog: SourceCatalog,
) -> list[dict[str, str]]:
    matrix: list[dict[str, str]] = []
    for reg in register_rows:
        pid = int(reg["product_id"])
        slices = prior_index.by_product.get(pid, [])
        if not slices:
            raise RuntimeError(f"missing_prior_research_slice product_id={pid}")
        recovery = classify_recovery(reg, slices, catalog)
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
        grouped[reg["requested_from_role_RECOMMENDATION"]].append(reg)
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


def fail_closed_reconciliation(
    register_rows: list[dict[str, str]],
    matrix: list[dict[str, str]],
    physical: list[dict[str, str]],
    register_identity: dict[str, str],
    catalog: SourceCatalog | None = None,
) -> dict[str, Any]:
    errors: list[str] = []

    waves = Counter(r["parallel_work_wave"] for r in register_rows)
    if dict(waves) != WAVE_COUNTS:
        errors.append(f"wave_count_mismatch got={dict(waves)} expected={WAVE_COUNTS}")
    workstreams = Counter(r["evidence_workstream"] for r in register_rows)
    if dict(workstreams) != WORKSTREAMS:
        errors.append(f"workstream_count_mismatch got={dict(workstreams)}")

    with PR499_REVIEW.open(encoding="utf-8", newline="") as handle:
        pr499 = list(csv.DictReader(handle))
    pr499_ids = [int(r["product_id"]) for r in pr499]
    if len(pr499) != 262 or len(set(pr499_ids)) != 262:
        errors.append(f"pr499_frozen_cohort expected=262_unique got_rows={len(pr499)} unique={len(set(pr499_ids))}")

    batch_paths = sorted(OWNER_PKG.glob("OWNER-AUTHORIZATION-BATCH-*-2026-10-1*.csv"))
    if len(batch_paths) != 11:
        errors.append(f"owner_journal_csv_count expected=11 got={len(batch_paths)}")

    journal_pids: list[int] = []
    evidence_requests: list[int] = []
    exits = 0
    apply_yes = 0
    for path in batch_paths:
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                pid_raw = row.get("product_id", "").strip()
                if not pid_raw.isdigit():
                    errors.append(f"journal_missing_product_id file={path.name}")
                    continue
                pid = int(pid_raw)
                journal_pids.append(pid)
                od = row.get("owner_decision", row.get("owner_response", "")).strip()
                apply = row.get("apply_authorization", "NO").strip().upper()
                if apply not in ("NO", ""):
                    apply_yes += 1
                if od == "REQUEST_MORE_EVIDENCE":
                    evidence_requests.append(pid)
                elif od == "APPROVE_CATALOG_EXIT":
                    exits += 1
                else:
                    errors.append(f"unexpected_owner_decision pid={pid} decision={od}")

    reg_ids = {int(r["product_id"]) for r in register_rows}
    pr499_id_set = set(pr499_ids)
    journal_id_set = set(journal_pids)
    if len(journal_pids) != 262 or len(journal_id_set) != 262:
        errors.append(f"journal_row_integrity expected=262_unique got={len(journal_pids)} unique={len(journal_id_set)}")
    if pr499_id_set != journal_id_set:
        errors.append(
            f"pr499_journal_product_id_set_mismatch "
            f"only_pr499={sorted(pr499_id_set - journal_id_set)[:5]} "
            f"only_journal={sorted(journal_id_set - pr499_id_set)[:5]}"
        )
    if set(evidence_requests) != reg_ids:
        errors.append("journal_evidence_request_set_mismatch_register")
    if exits != 151:
        errors.append(f"documentary_exit_count expected=151 got={exits}")
    if apply_yes != 0:
        errors.append(f"apply_authorization_in_journals count={apply_yes}")

    matrix_ids = {r["product_id"] for r in matrix}
    manifest_ids = {r["product_id"] for r in physical}
    if len(matrix) != 111 or matrix_ids != {r["product_id"] for r in register_rows}:
        errors.append("matrix_id_integrity_failed")
    if manifest_ids != matrix_ids:
        errors.append("physical_manifest_id_mismatch_matrix")

    if any(r.get("apply_authorization") != "NO" for r in matrix):
        errors.append("matrix_apply_authorization_not_all_no")
    if any(r.get("production_mutation") != "NO" for r in matrix):
        errors.append("matrix_production_mutation_not_all_no")
    if any(r.get("owner_decision_unchanged") != "REQUEST_MORE_EVIDENCE" for r in matrix):
        errors.append("matrix_owner_decision_not_all_REQUEST_MORE_EVIDENCE")
    if any((r.get("new_owner_disposition") or "").strip() for r in matrix):
        errors.append("matrix_new_owner_disposition_must_be_blank")

    physical_pids = [r["product_id"] for r in physical]
    if len(physical_pids) != len(set(physical_pids)):
        errors.append("physical_manifest_duplicate_product_id")

    if catalog is not None:
        for row in matrix:
            pid = row["product_id"]
            trace = [s for s in row.get("traceable_source_ids", "").split("|") if s]
            if row.get("partial_or_family_evidence") == "YES" and not trace:
                errors.append(f"partial_evidence_without_source product_id={pid}")
            if row.get("exact_oem_documentary_recovered") == "YES" and not trace:
                errors.append(f"exact_oem_without_source product_id={pid}")
            for sid in trace:
                if sid not in catalog.by_id:
                    errors.append(f"matrix_references_unknown_source product_id={pid} source_id={sid}")
                    continue
                related = {x for x in catalog.by_id[sid]["related_product_ids"].split(",") if x}
                if pid not in related:
                    errors.append(f"source_product_backlink_missing product_id={pid} source_id={sid}")

    if errors:
        raise RuntimeError("RECONCILIATION_FAILED: " + "; ".join(errors))

    status_counts = Counter(r["evidence_recovery_status"] for r in matrix)
    return {
        "status": "PASS",
        **register_identity,
        "frozen_262_review_blob_note": FROZEN_REVIEW_BLOB_NOTE,
        "pr499_row_count": len(pr499),
        "pr499_unique_product_ids": len(set(pr499_ids)),
        "owner_journal_csv_count": len(batch_paths),
        "owner_journal_unique_product_ids": len(set(journal_pids)),
        "open_evidence_request_count": len(reg_ids),
        "documentary_exit_count_in_journals": exits,
        "apply_authorization_rows": apply_yes,
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


# Back-compat aliases for audit script imports
def collect_source_rows(
    register_rows: list[dict[str, str]],
    access_date: str,
    live_probe: bool = False,
) -> list[dict[str, str]]:
    catalog = build_source_catalog(register_rows)
    return finalize_source_register(catalog, access_date, live_probe=live_probe)


def build_source_catalog_public(register_rows: list[dict[str, str]]) -> SourceCatalog:
    return build_source_catalog(register_rows)
