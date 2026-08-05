"""Reconcile Dasqua candidate-stage vs SourceAdapter decisions (external)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from image_discovery.sources.dasqua_official import DasquaOfficialAdapter


def reconcile_dasqua_candidate_vs_adapter(
    *,
    candidate_csv: Path,
    rejected_materialization_csv: Path | None = None,
    saved_html_by_sku: dict[str, tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Build per-row reconciliation of discovery vs adapter validation.

    ``saved_html_by_sku`` maps governed SKU → (detail_url, html). When absent,
    adapter decision is taken from materialization rejected.csv when present.
    """
    candidates = list(csv.DictReader(candidate_csv.open(encoding="utf-8")))
    mat_by_sku: dict[str, dict[str, str]] = {}
    if rejected_materialization_csv and rejected_materialization_csv.is_file():
        for row in csv.DictReader(rejected_materialization_csv.open(encoding="utf-8")):
            sku = (row.get("sku") or "").strip()
            if sku:
                mat_by_sku[sku] = row

    adapter = DasquaOfficialAdapter()
    rows: list[dict[str, Any]] = []
    for cand in candidates:
        sku = (cand.get("sku") or "").strip()
        detail = cand.get("source_detail_url") or cand.get("detail_url") or ""
        image = cand.get("source_image_url") or cand.get("image_url") or ""
        candidate_decision = cand.get("discovery_status") or "candidate_ready"
        adapter_code = ""
        adapter_detail = ""
        adapter_decision = "not_evaluated"
        html_pair = (saved_html_by_sku or {}).get(sku)
        if html_pair:
            detail_url, html = html_pair
            ev = adapter.validate_page(sku=sku, page_html=html, detail_url=detail_url or detail)
            if ev.manufacturer_confirmed and ev.sku_confirmed:
                adapter_decision = "accepted"
            else:
                adapter_decision = "rejected"
                adapter_code = ev.reason_code or ""
                adapter_detail = ev.reason_detail or ""
        elif sku in mat_by_sku:
            adapter_decision = "rejected"
            adapter_code = mat_by_sku[sku].get("reason_code") or ""
            adapter_detail = mat_by_sku[sku].get("reason_detail") or ""
        rows.append(
            {
                "product_id": cand.get("product_id") or "",
                "governed_sku": sku,
                "candidate_detail_url": detail,
                "candidate_image_url": image,
                "candidate_stage_decision": candidate_decision,
                "adapter_stage_decision": adapter_decision,
                "adapter_reason_code": adapter_code,
                "adapter_reason_detail": adapter_detail,
            }
        )
    mismatches = [
        r
        for r in rows
        if r["candidate_stage_decision"] == "candidate_ready"
        and r["adapter_stage_decision"] == "rejected"
    ]
    return {
        "rows": rows,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "policy": (
            "candidate discovery must not label candidate_ready when the "
            "SourceAdapter rejects the same HTML"
        ),
    }


def write_dasqua_reconcile_report(report: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path
