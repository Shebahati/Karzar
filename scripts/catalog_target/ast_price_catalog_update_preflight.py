"""UPDATE cohort owner preflight package (no production mutation)."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from catalog_target.ast_price_catalog_manifest_acceptance import manifest_file_sha256


def _load_catalog_by_id(catalog_csv: Path) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    with catalog_csv.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = str(row.get("id") or row.get("product_id") or "").strip()
            if pid:
                out[pid] = row
    return out


def write_update_cohort_preflight(
    *,
    audit_dir: Path,
    sanitized_dir: Path,
    catalog_csv: Path,
    update_rows: list[dict[str, Any]],
    abnormal_updates: list[dict[str, Any]],
) -> Path:
    sanitized_dir.mkdir(parents=True, exist_ok=True)
    catalog = _load_catalog_by_id(catalog_csv)
    drift: list[dict[str, str]] = []
    for row in update_rows:
        pid = str(row.get("product_id") or row.get("id") or "")
        live = catalog.get(pid)
        if live is None:
            drift.append({"product_id": pid, "reason": "missing_from_snapshot"})
            continue
        if str(live.get("sku") or "") != str(row.get("sku") or ""):
            drift.append({"product_id": pid, "reason": "sku_mismatch"})
        expected = row.get("expected_current_price") or row.get("current_price") or ""
        live_price = live.get("base_price") or live.get("current_price") or ""
        if str(expected) and str(live_price) and Decimal(str(live_price)) != Decimal(str(expected)):
            drift.append(
                {
                    "product_id": pid,
                    "reason": "price_drift",
                    "expected": str(expected),
                    "snapshot": str(live_price),
                }
            )

    abnormal_ids = {str(r.get("product_id")) for r in abnormal_updates}
    update_ids = {str(r.get("product_id")) for r in update_rows}
    leaked_abnormal = sorted(abnormal_ids & update_ids)

    update_path = audit_dir / "UPDATE_PRODUCTS.csv"
    payload = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "update_manifest_sha256": manifest_file_sha256(update_path),
        "update_row_count": len(update_rows),
        "abnormal_price_hold_count": len(abnormal_updates),
        "abnormal_ids_leaked_into_update_manifest": leaked_abnormal,
        "snapshot_drift_mismatches": drift,
        "snapshot_drift_count": len(drift),
        "canary_plan": {
            "stage_1": "5 low-risk brand-diverse UPDATE rows (excludes abnormal holds).",
            "stage_2": "50 additional low-risk rows; excludes stage1 product IDs.",
            "stage_3": "Remaining UPDATE rows; disjoint allowlists; see UPDATE_CANARY_MANIFESTS.json.",
            "registry_file": "sanitized/UPDATE_CANARY_MANIFESTS.json",
        },
        "post_commit_verification_plan": {
            "method": "fresh_async_connection",
            "checks": ["sku", "base_price", "no_create_side_effects", "no_hesabfa_calls"],
        },
        "scope_guarantee": "UPDATE SQL mutates base_price only; no original_price/is_available/Hesabfa.",
    }
    out = sanitized_dir / "UPDATE_COHORT_PREFLIGHT.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (sanitized_dir / "UPDATE_COHORT_OWNER_PACKAGE.md").write_text(
        "# UPDATE cohort owner package\n\n"
        f"- Manifest SHA256: `{payload['update_manifest_sha256']}`\n"
        f"- Rows: **{payload['update_row_count']}**\n"
        f"- Abnormal holds (must stay out): **{payload['abnormal_price_hold_count']}**\n"
        f"- Leaked abnormal IDs: `{leaked_abnormal}`\n"
        f"- Snapshot drift count: **{payload['snapshot_drift_count']}**\n"
        "- Accept `OWNER_MANIFEST_BUNDLE_UPDATE.json` before `--apply-cohort update`.\n",
        encoding="utf-8",
    )
    return out
