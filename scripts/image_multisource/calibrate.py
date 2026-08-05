"""Per-source calibration (≤20 eligible products) for IMG-02C."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import MultisourceError
from .eligibility import select_calibration_sample
from .matching import host_allowed, host_of
from .output import write_json
from .registry import SourceDeclaration
from .robots import classify_robots_text

FetchFn = Callable[[str], tuple[int, str, bytes]]


@dataclass
class CalibrationResult:
    source_id: str
    source_class: str
    sample_size: int
    robots_status: str
    parser_drift_rate: float
    sku_mismatch_systematic: bool
    unapproved_redirect: bool
    generic_category_accepted: bool
    robots_blocks_crawl: bool
    enabled_after_calibration: bool
    disable_reason: str
    product_results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _default_fetch(_url: str) -> tuple[int, str, bytes]:
    raise MultisourceError("calibrate", "live fetch not configured")


def calibrate_source(
    *,
    source: SourceDeclaration,
    eligibility_report: dict[str, Any],
    worklist_csv: Path,
    output_dir: Path,
    limit: int = 20,
    user_agent: str = "KarzarImageMultisource/0.1",
    robots_txt: str | None = None,
    fetch: FetchFn | None = None,
    probe: Callable[[SourceDeclaration, dict[str, str]], dict[str, Any]] | None = None,
) -> CalibrationResult:
    if limit < 1 or limit > 20:
        raise MultisourceError("calibrate", "limit must be 1..20")
    brand = source.brand_keys[0]
    sample = select_calibration_sample(
        eligibility_report, worklist_csv, brand_key=brand, limit=limit
    )
    fetch_fn = fetch or _default_fetch

    robots_status = source.robots_status
    robots_blocks = False
    if robots_txt is not None:
        # Probe first allowed host root path
        host = source.allowed_page_hosts[0]
        target = f"https://{host}/"
        rob = classify_robots_text(robots_txt, user_agent=user_agent, url=target)
        robots_status = rob["robots_status"]
        robots_blocks = rob["crawl_permitted"] != "true"

    product_results: list[dict[str, Any]] = []
    drift_flags = 0
    sku_mismatches = 0
    unapproved_redirect = False
    generic_hits = 0

    for row in sample:
        if probe is not None:
            result = probe(source, row)
        else:
            # Offline / fixture-safe default: record pending_live_probe without network.
            result = {
                "product_id": row.get("product_id") or "",
                "sku": row.get("sku") or "",
                "status": "pending_live_probe",
                "page_identity_ok": False,
                "exact_sku_ok": False,
                "redirect_ok": True,
                "generic_category": False,
                "parser_drift": False,
                "asset_host_ok": False,
                "notes": "calibration probe not injected; no network performed",
            }
            # Optional: if fetch provided, hit robots only once already handled; do not invent pages.
            _ = fetch_fn  # reserved for future live probe adapters
        product_results.append(result)
        if result.get("parser_drift"):
            drift_flags += 1
        if result.get("exact_sku_ok") is False and result.get("status") not in {
            "pending_live_probe",
            "skipped",
        }:
            sku_mismatches += 1
        if result.get("redirect_ok") is False:
            unapproved_redirect = True
        if result.get("generic_category"):
            generic_hits += 1

    n = max(len(product_results), 1)
    drift_rate = drift_flags / n
    systematic_sku = sku_mismatches >= max(3, int(0.5 * n))
    generic_accepted = generic_hits > 0

    disable_reason = ""
    enabled = True
    if robots_blocks:
        enabled = False
        disable_reason = "robots_policy_prevents_crawling"
    elif drift_rate > 0.20:
        enabled = False
        disable_reason = f"parser_drift_rate={drift_rate:.2f}>0.20"
    elif systematic_sku:
        enabled = False
        disable_reason = "systematic_sku_mismatch"
    elif unapproved_redirect:
        enabled = False
        disable_reason = "unapproved_redirect"
    elif generic_accepted:
        enabled = False
        disable_reason = "generic_or_category_images_accepted"
    elif all(r.get("status") == "pending_live_probe" for r in product_results):
        # Not yet proven — keep disabled until live probe evidence exists.
        enabled = False
        disable_reason = "calibration_pending_live_probe"
    elif source.authorization_status == "unknown":
        enabled = False
        disable_reason = "unknown_authorization"

    # Source already declared disabled stays disabled unless calibration explicitly proves enable.
    if not source.enabled and disable_reason == "":
        # Only enable if calibration produced at least one exact SKU ok.
        if not any(r.get("exact_sku_ok") for r in product_results):
            enabled = False
            disable_reason = "insufficient_exact_identity_evidence"

    result = CalibrationResult(
        source_id=source.source_id,
        source_class=source.source_class,
        sample_size=len(sample),
        robots_status=robots_status,
        parser_drift_rate=round(drift_rate, 4),
        sku_mismatch_systematic=systematic_sku,
        unapproved_redirect=unapproved_redirect,
        generic_category_accepted=generic_accepted,
        robots_blocks_crawl=robots_blocks,
        enabled_after_calibration=enabled,
        disable_reason=disable_reason,
        product_results=product_results,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / f"{source.source_id}.json", result.to_dict())
    return result


def validate_redirect(
    *,
    requested_url: str,
    final_url: str,
    source: SourceDeclaration,
) -> bool:
    if host_of(final_url) == host_of(requested_url):
        return host_allowed(final_url, source.allowed_page_hosts)
    # Cross-host redirect must land on an approved page host.
    return host_allowed(final_url, source.allowed_page_hosts)


def summarize_calibrations(results: list[CalibrationResult]) -> dict[str, Any]:
    enabled = [r for r in results if r.enabled_after_calibration]
    disabled = [r for r in results if not r.enabled_after_calibration]
    by_class: dict[str, int] = {}
    for r in enabled:
        by_class[r.source_class] = by_class.get(r.source_class, 0) + 1
    return {
        "enabled_source_count": len(enabled),
        "enabled_sources_by_class": dict(sorted(by_class.items())),
        "disabled_sources": [
            {"source_id": r.source_id, "reason": r.disable_reason} for r in disabled
        ],
        "calibration_results": [r.to_dict() for r in results],
    }
