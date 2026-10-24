"""Owner acceptance evidence index (sensitive workbooks stay under audit/work/)."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from catalog_target.ast_price_catalog_manifest_acceptance import manifest_file_sha256


def _pct_change(before: Decimal, after: Decimal) -> str:
    if before == 0:
        return ""
    return str(((after - before) / before) * Decimal("100"))


def write_update_financial_workbook(
    *,
    audit_dir: Path,
    update_rows: list[dict[str, Any]],
) -> Path:
    work_dir = audit_dir / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    out = work_dir / "UPDATE_FINANCIAL_REVIEW_1706.csv"
    fieldnames = [
        "product_id",
        "sku",
        "brand",
        "expected_current_price",
        "proposed_price",
        "absolute_diff",
        "percent_diff",
        "source_document",
        "source_page",
        "pricing_policy_id",
    ]
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in update_rows:
            before_raw = row.get("expected_current_price") or row.get("current_price") or "0"
            after_raw = row.get("proposed_price") or row.get("base_price") or "0"
            try:
                before = Decimal(str(before_raw))
                after = Decimal(str(after_raw))
                abs_diff = after - before
                pct = _pct_change(before, after)
            except Exception:
                abs_diff = ""
                pct = row.get("percent_diff") or ""
            writer.writerow(
                {
                    "product_id": row.get("product_id"),
                    "sku": row.get("sku"),
                    "brand": row.get("brand") or row.get("brand_id"),
                    "expected_current_price": str(before_raw),
                    "proposed_price": str(after_raw),
                    "absolute_diff": str(abs_diff),
                    "percent_diff": pct or row.get("percent_diff") or "",
                    "source_document": row.get("source_document") or row.get("source_file"),
                    "source_page": row.get("source_page"),
                    "pricing_policy_id": row.get("pricing_policy_id"),
                }
            )
    return out


def write_update_owner_package(
    *,
    audit_dir: Path,
    sanitized_dir: Path,
    catalog_csv: Path,
    update_rows: list[dict[str, Any]],
    abnormal_updates: list[dict[str, Any]],
    canary_registry: dict[str, Any],
) -> Path:
    sanitized_dir.mkdir(parents=True, exist_ok=True)
    workbook = write_update_financial_workbook(audit_dir=audit_dir, update_rows=update_rows)
    snapshot_sha = manifest_file_sha256(catalog_csv) if catalog_csv.is_file() else ""
    abnormal_ids = sorted({str(r.get("product_id")) for r in abnormal_updates})
    payload = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "catalog_snapshot_path": str(catalog_csv.name),
        "catalog_snapshot_sha256": snapshot_sha,
        "master_update_manifest_sha256": canary_registry.get("master_update_manifest_sha256"),
        "update_row_count": len(update_rows),
        "abnormal_price_hold_product_ids": abnormal_ids,
        "abnormal_price_hold_count": len(abnormal_updates),
        "financial_workbook_relpath": "work/UPDATE_FINANCIAL_REVIEW_1706.csv",
        "financial_workbook_sha256": manifest_file_sha256(workbook),
        "canary_manifests": canary_registry,
        "expected_total_update_mutations": len(update_rows),
        "authorization_gates": [
            "OWNER_MANIFEST_ACCEPTED per stage bundle",
            "confirm_git_commit_sha",
            "confirm_stage_manifest_sha256",
            "confirm_master_update_manifest_sha256",
            "confirm_product_id_allowlist_sha256",
            "PRODUCTION_BACKUP_ATTESTATION with verified DB identity",
            "Category B production write flags",
        ],
        "post_commit_verification_plan": "fresh_async_connection sku+base_price",
    }
    out_json = sanitized_dir / "UPDATE_OWNER_EVIDENCE_INDEX.json"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_lines = [
        "# UPDATE cohort owner package",
        "",
        f"- Master UPDATE manifest SHA256: `{payload['master_update_manifest_sha256']}`",
        f"- UPDATE rows: **{len(update_rows)}**",
        f"- Abnormal-price HOLD exclusions: **{len(abnormal_updates)}**",
        f"- Financial workbook (off-repo path): `work/UPDATE_FINANCIAL_REVIEW_1706.csv`",
        f"- Workbook SHA256: `{payload['financial_workbook_sha256']}`",
        "",
        "## Canary stages",
        "",
    ]
    for stage, meta in (canary_registry.get("stages") or {}).items():
        if stage == "full":
            continue
        md_lines.append(
            f"- **{stage}**: {meta.get('row_count')} rows, manifest SHA256 `{meta.get('manifest_sha256')}`"
        )
    (sanitized_dir / "UPDATE_COHORT_OWNER_PACKAGE.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return out_json
