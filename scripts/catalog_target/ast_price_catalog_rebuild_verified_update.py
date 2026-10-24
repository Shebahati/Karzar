"""Rebuild UPDATE master + canary from PDF-verified rows only."""

from __future__ import annotations

import csv
import json
import zipfile
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from catalog_target.ast_price_catalog_manifest_acceptance import (
    manifest_file_sha256,
    write_update_stage_owner_bundles,
)
from catalog_target.ast_price_catalog_source_verification import (
    build_verification_record,
    verify_update_row_on_pdf,
)
from catalog_target.ast_price_catalog_update_canary import (
    product_id_allowlist_sha256,
    select_canary_partitions,
    write_update_canary_artifacts,
)
from catalog_target.ast_price_catalog_update_owner_package import write_update_owner_package

STAGE1_PINNED_PRODUCT_IDS = (1680, 1168, 1078, 1176, 1067)


def _manufacturer_from_row(brand_hint: str, source_file: str) -> str:
    hint = (brand_hint or "").upper()
    if "DASQUA" in hint or "داسکوا" in source_file:
        return "DASQUA"
    if "CHUMPOWER" in hint or "چام" in source_file:
        return "CHUMPOWER"
    if "ET" in hint:
        return "ET"
    if "ASTPOWER" in hint or "AST" in hint:
        return "ASTPOWER"
    return "UNRESOLVED"


def _pdf_cache_path(audit_dir: Path, source_file: str) -> Path:
    cache = audit_dir / "work" / "pdf_cache"
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / source_file
    if target.is_file():
        return target
    zpath = audit_dir / "source" / "AST(2).zip"
    with zipfile.ZipFile(zpath) as zf:
        zf.extract(source_file, path=cache)
    return target


def rebuild_verified_update_cohort(audit_dir: Path) -> dict[str, Any]:
    ledger = list(csv.DictReader((audit_dir / "SOURCE_ROW_LEDGER.csv").open(encoding="utf-8")))
    update_rows_raw = list(csv.DictReader((audit_dir / "UPDATE_PRODUCTS.csv").open(encoding="utf-8")))
    upd_by_pid = {int(r["product_id"]): r for r in update_rows_raw}

    qa_report = Counter()
    for row in ledger:
        if row.get("primary_outcome") != "UPDATE":
            continue
        es = row.get("extraction_status") or ""
        qf = row.get("qa_flags") or ""
        if "VISUAL" in es:
            qa_report["visual_unresolved"] += 1
        if "QA_MANUFACTURER_IDENTITY_REVIEW" in qf:
            qa_report["manufacturer_unresolved"] += 1

    page_text_cache: dict[tuple[str, int], str] = {}

    def page_text(source_file: str, page: int) -> str:
        key = (source_file, page)
        if key in page_text_cache:
            return page_text_cache[key]
        pdf = _pdf_cache_path(audit_dir, source_file)
        import subprocess

        proc = subprocess.run(
            ["pdftotext", "-f", str(page), "-l", str(page), "-layout", str(pdf), "-"],
            capture_output=True,
            text=True,
            check=False,
        )
        page_text_cache[key] = proc.stdout if proc.returncode == 0 else ""
        return page_text_cache[key]

    verified_records: list[dict[str, Any]] = []
    verified_updates: list[dict[str, str]] = []
    for row in ledger:
        if row.get("primary_outcome") != "UPDATE":
            continue
        if "QA_MANUFACTURER_IDENTITY_REVIEW" in (row.get("qa_flags") or ""):
            continue
        pid = int(row["product_id"])
        base = upd_by_pid.get(pid)
        if base is None:
            continue
        pdf = _pdf_cache_path(audit_dir, row["source_file"])
        mfg = _manufacturer_from_row(row.get("brand_hint") or "", row.get("source_file") or "")
        result = verify_update_row_on_pdf(
            pdf_path=pdf,
            source_page=int(row.get("source_page") or 1),
            sku=row["code"],
            proposed_price_toman=row["proposed_price"],
            manufacturer_identity=mfg,
        )
        record = build_verification_record(
            result,
            product_id=pid,
            brand_hint=row.get("brand_hint") or "",
        )
        if result.verified:
            verified_records.append(record)
            verified_updates.append(base)

    # Stage 1: pinned verified IDs only (must all pass verification)
    stage1_ids = set(STAGE1_PINNED_PRODUCT_IDS)
    stage1_rows = [r for r in verified_updates if int(r["product_id"]) in stage1_ids]
    if len(stage1_rows) != len(stage1_pins := STAGE1_PINNED_PRODUCT_IDS):
        missing = set(stage1_pins) - {int(r["product_id"]) for r in stage1_rows}
        raise RuntimeError(f"stage1_pinned_verification_failed:{sorted(missing)}")

    remaining = [r for r in verified_updates if int(r["product_id"]) not in stage1_ids]
    if len(remaining) < 50:
        raise RuntimeError("verified_cohort_too_small_for_stage2")
    ranked_rest = sorted(
        remaining,
        key=lambda r: (
            abs(Decimal((r.get("percent_diff") or "0").strip() or "0")),
            abs(Decimal((r.get("absolute_diff") or "0").strip() or "0")),
        ),
    )
    stage2 = ranked_rest[:50]
    stage3 = ranked_rest[50:]
    partitions = {
        "stage1": stage1_rows,
        "stage2": stage2,
        "stage3": stage3,
        "full": verified_updates,
    }

    work = audit_dir / "work"
    sanitized = audit_dir / "sanitized"
    work.mkdir(parents=True, exist_ok=True)
    verified_path = audit_dir / "UPDATE_PRODUCTS.csv"
    _write_csv(verified_path, verified_updates)
    master_sha = manifest_file_sha256(verified_path)

    registry_path = sanitized / "UPDATE_SOURCE_VERIFICATION_REGISTRY.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
                "verified_row_count": len(verified_records),
                "qa_report_update_ledger": dict(qa_report),
                "records": verified_records,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    canary_registry = write_update_canary_artifacts(
        audit_dir=audit_dir,
        update_rows=verified_updates,
        master_manifest_sha256=master_sha,
    )
    # overwrite stage partitions with verified disjoint sets
    for stage in ("stage1", "stage2", "stage3"):
        rel = canary_registry["stages"][stage]["manifest_relpath"].replace("work/", "")
        _write_csv(work / rel, partitions[stage])
        sha = manifest_file_sha256(work / rel)
        pids = [int(r["product_id"]) for r in partitions[stage]]
        canary_registry["stages"][stage].update(
            {
                "manifest_sha256": sha,
                "row_count": len(partitions[stage]),
                "product_id_allowlist_sha256": product_id_allowlist_sha256(pids),
                "product_ids": pids,
            }
        )
    canary_registry["total_update_rows"] = len(verified_updates)
    (sanitized / "UPDATE_CANARY_MANIFESTS.json").write_text(
        json.dumps(canary_registry, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    ledger_sha = manifest_file_sha256(audit_dir / "SOURCE_ROW_LEDGER.csv")
    write_update_stage_owner_bundles(
        sanitized,
        ledger_manifest_sha256=ledger_sha,
        canary_registry=canary_registry,
    )

    catalog = next(audit_dir.glob("CATALOG_SNAPSHOT_*.csv"))
    abnormal = list(csv.DictReader((audit_dir / "ABNORMAL_UPDATE_REVIEW.csv").open(encoding="utf-8")))
    write_update_owner_package(
        audit_dir=audit_dir,
        sanitized_dir=sanitized,
        catalog_csv=catalog,
        update_rows=verified_updates,
        abnormal_updates=abnormal,
        canary_registry=canary_registry,
    )

    return {
        "verified_update_count": len(verified_updates),
        "master_sha256": master_sha,
        "stage1_sha256": canary_registry["stages"]["stage1"]["manifest_sha256"],
        "stage1_allowlist_sha256": canary_registry["stages"]["stage1"]["product_id_allowlist_sha256"],
        "qa_report": dict(qa_report),
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
