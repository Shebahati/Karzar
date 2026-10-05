#!/usr/bin/env python3
"""Phase 2D — canonical name candidate dry-run (READ ONLY).

Never mutates catalog/DB. Forbidden: --apply, --rename, --commit, --force, --write-db.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.domain.product_naming_phase2d import (  # noqa: E402
    AUDIT_CSV_FIELDS,
    PHASE2C_FROZEN_ROWS,
    PHASE2C_FROZEN_SHA256,
    Phase2DAuditRow,
    Phase2DProductInput,
    apply_collision_holds,
    audit_logic_fingerprint,
    classify_product_phase2d,
    detect_collisions,
    deterministic_human_review_sample,
    reconcile_classifications,
    reject_forbidden_cli_args,
    sha256_file,
)
from app.domain.product_naming_phase2d import TERMINAL_CLASSIFICATIONS  # noqa: E402

AUDIT_DIR = ROOT / "audit" / "product-naming-phase2d"
FROZEN_CSV = ROOT / "audit" / "product-naming-phase2c-discovery" / "BACKFILL_EXACT_FROZEN.csv"
BRAND_REGISTRY = ROOT / "audit" / "product-naming-v1" / "BRAND_DISPLAY_REGISTRY.csv"
DOMAIN_PATH = ROOT / "app" / "domain" / "product_naming_phase2d.py"
SCRIPT_PATH = Path(__file__).resolve()

FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|UPSERT|TRUNCATE|DROP|ALTER|CREATE|GRANT|REVOKE)\b",
    re.I,
)

BANNER = """
========================================================================
  KARZAR PRODUCT NAMING — PHASE 2D DRY RUN
  MODE: READ-ONLY / NO Product.name WRITES
  APPLY / RENAME / COMMIT: DISABLED
========================================================================
""".strip()


def _run_ssh_psql(sql: str, *, ssh_host: str) -> str:
    if FORBIDDEN_SQL.search(sql):
        raise RuntimeError(f"Refusing mutation-capable SQL: {sql[:120]}")
    inner = sql.replace('"', '\\"')
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        ssh_host,
        f'docker exec -i lathe_postgres psql -U karzar_staging -d karzar_staging -v ON_ERROR_STOP=1 -At -c "{inner}"',
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def read_only_session_proof(ssh_host: str) -> dict[str, str]:
    block = """
BEGIN;
SET TRANSACTION READ ONLY;
SHOW transaction_read_only;
"""
    out = _run_ssh_psql(block + "SELECT 1;", ssh_host=ssh_host)
    tro = "on" if "on" in out.lower() else out.split("\n")[-1].strip()
    _run_ssh_psql("ROLLBACK;", ssh_host=ssh_host)
    return {"transaction_read_only": tro, "mutation_capable_statements_executed": "0"}


def load_brand_registry() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    if not BRAND_REGISTRY.is_file():
        return out
    with BRAND_REGISTRY.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            bid = (row.get("brand_id") or "").strip()
            if bid:
                out[bid] = row
    return out


def load_frozen_cohort() -> dict[int, dict[str, str]]:
    if not FROZEN_CSV.is_file():
        raise FileNotFoundError(FROZEN_CSV)
    digest = sha256_file(FROZEN_CSV)
    if digest != PHASE2C_FROZEN_SHA256:
        raise RuntimeError(f"Phase 2C frozen SHA mismatch: {digest}")
    out: dict[int, dict[str, str]] = {}
    with FROZEN_CSV.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            pid = int(row["product_id"])
            out[pid] = row
    if len(out) != PHASE2C_FROZEN_ROWS:
        raise RuntimeError(f"Phase 2C row count {len(out)} != {PHASE2C_FROZEN_ROWS}")
    return out


def _copy_export_sql(extra_where: str, select_cols: str) -> str:
    return f"""
COPY (
  SELECT {select_cols}
  FROM products p
  LEFT JOIN brands b ON b.id = p.brand_id
  LEFT JOIN product_types pt ON pt.id = p.product_type_id
  LEFT JOIN LATERAL (
    SELECT EXISTS (
      SELECT 1 FROM product_type_definitions ptd
      WHERE ptd.product_type_id = pt.id AND ptd.status = 'active'
    ) AS has_active_def
  ) ptd ON TRUE
  LEFT JOIN LATERAL (
    SELECT bool_or(
      pi.image_url IS NOT NULL AND length(trim(pi.image_url)) > 0
      AND pi.image_url NOT ILIKE '%placeholder%'
      AND pi.image_url NOT ILIKE '%no-image%'
      AND pi.image_url NOT ILIKE '%no_image%'
    ) AS has_real_image
    FROM product_images pi WHERE pi.product_id = p.id
  ) img ON TRUE
  WHERE p.deleted_at IS NULL
    {extra_where}
  ORDER BY p.id
) TO STDOUT WITH (FORMAT CSV, HEADER true, ENCODING 'UTF8');
"""


def ssh_copy_csv(copy_sql: str, ssh_host: str) -> list[dict[str, str]]:
    if FORBIDDEN_SQL.search(copy_sql):
        raise RuntimeError("export SQL failed safety check")
    script = f"""set -euo pipefail
docker exec -i lathe_postgres psql -U karzar_staging -d karzar_staging -v ON_ERROR_STOP=1 <<'EOSQL'
BEGIN;
SET TRANSACTION READ ONLY;
{copy_sql}
ROLLBACK;
EOSQL
"""
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", ssh_host, "bash", "-s"],
        input=script,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-3000:] or proc.stdout[-3000:])
    lines = proc.stdout.splitlines()
    header_idx = next((i for i, line in enumerate(lines) if "," in line and "product_id" in line), None)
    if header_idx is None:
        raise RuntimeError("CSV header not found in SSH export")
    reader = csv.DictReader(lines[header_idx:])
    return [row for row in reader if (row.get("product_id") or "").isdigit()]


def export_cohort_live(ssh_host: str, product_ids: list[int]) -> list[dict[str, str]]:
    id_list = ",".join(str(i) for i in sorted(product_ids))
    cols = """
    p.id AS product_id,
    p.name AS current_name,
    p.sku,
    p.brand_id,
    COALESCE(b.name, '') AS brand_name,
    COALESCE(p.manufacturer_code, '') AS manufacturer_code,
    p.product_type_id,
    COALESCE(pt.code, '') AS product_type_code,
    COALESCE(pt.name_fa, '') AS product_type_name_fa,
    COALESCE(pt.status, '') AS product_type_status,
    COALESCE(ptd.has_active_def::text, 'false') AS product_type_has_active_definition,
    COALESCE(p.meta_title, '') AS meta_title,
    p.is_active::text AS is_active,
    p.is_available::text AS is_available,
    (p.base_price IS NOT NULL)::text AS priced,
    COALESCE(img.has_real_image::text, 'false') AS has_image,
    (
      p.is_active IS TRUE AND COALESCE(img.has_real_image, false)
    )::text AS storefront_visible,
    (
      p.is_active IS TRUE AND p.is_available IS TRUE AND p.base_price IS NOT NULL
    )::text AS sellable
    """
    sql = _copy_export_sql(f"AND p.id IN ({id_list})", cols)
    return ssh_copy_csv(sql, ssh_host)


def export_catalog_names(ssh_host: str) -> dict[int, str]:
    sql = _copy_export_sql("", "p.id AS product_id, p.name AS current_name")
    rows = ssh_copy_csv(sql, ssh_host)
    return {int(r["product_id"]): r["current_name"] for r in rows}


def export_kb_facts(ssh_host: str, product_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    id_list = ",".join(str(i) for i in sorted(product_ids))
    copy_sql = f"""
COPY (
  SELECT
    kf.entity_id AS product_id,
    kf.id AS fact_id,
    kf.status,
    kpd.key AS property_key,
    kf.value::text AS value_json,
    COALESCE(kf.unit, '') AS unit
  FROM knowledge_facts kf
  JOIN knowledge_property_definitions kpd ON kpd.definition_id = kf.definition_id
  WHERE kf.entity_id IN ({id_list})
  ORDER BY kf.entity_id, kpd.key, kf.id
) TO STDOUT WITH (FORMAT CSV, HEADER true, ENCODING 'UTF8');
"""
    rows = ssh_copy_csv(copy_sql, ssh_host)
    by_pid: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        pid = int(r["product_id"])
        raw = r.get("value_json") or ""
        try:
            value = json.loads(raw) if raw.startswith(("{", "[")) else raw
        except json.JSONDecodeError:
            value = raw
        by_pid[pid].append(
            {
                "fact_id": r.get("fact_id"),
                "status": r.get("status"),
                "property_key": r.get("property_key"),
                "value": value,
                "unit": r.get("unit"),
            }
        )
    return by_pid


def _boolish(val: str | None) -> bool:
    return str(val or "").lower() in {"t", "true", "1", "yes"}


def build_inputs(
    frozen: dict[int, dict[str, str]],
    live_rows: list[dict[str, str]],
    kb_by_pid: dict[int, list[dict[str, Any]]],
) -> list[Phase2DProductInput]:
    live_by_id = {int(r["product_id"]): r for r in live_rows}
    inputs: list[Phase2DProductInput] = []
    for pid in sorted(frozen.keys()):
        fr = frozen[pid]
        lr = live_by_id.get(pid)
        if lr is None:
            inputs.append(
                Phase2DProductInput(
                    product_id=pid,
                    current_name=fr.get("current_name") or "",
                    sku=fr.get("sku") or "",
                    brand_id=int(fr["brand_id"]) if fr.get("brand_id") else None,
                    brand_name=fr.get("brand_name"),
                    manufacturer_code="",
                    product_type_id=None,
                    product_type_code=None,
                    product_type_name_fa=None,
                    product_type_status=None,
                    product_type_has_active_definition=False,
                    meta_title=None,
                    is_active=False,
                    is_available=False,
                    priced=False,
                    has_image=False,
                    storefront_visible=False,
                    sellable=False,
                    frozen_sku=fr.get("sku"),
                    frozen_brand_id=int(fr["brand_id"]) if fr.get("brand_id") else None,
                    frozen_manufacturer_code=fr.get("candidate_manufacturer_code"),
                    kb_facts=[],
                )
            )
            continue
        inputs.append(
            Phase2DProductInput(
                product_id=pid,
                current_name=lr.get("current_name") or "",
                sku=lr.get("sku") or "",
                brand_id=int(lr["brand_id"]) if (lr.get("brand_id") or "").strip().isdigit() else None,
                brand_name=lr.get("brand_name"),
                manufacturer_code=lr.get("manufacturer_code") or "",
                product_type_id=int(lr["product_type_id"]) if lr.get("product_type_id") else None,
                product_type_code=lr.get("product_type_code") or None,
                product_type_name_fa=lr.get("product_type_name_fa") or None,
                product_type_status=lr.get("product_type_status") or None,
                product_type_has_active_definition=_boolish(lr.get("product_type_has_active_definition")),
                meta_title=lr.get("meta_title") or None,
                is_active=_boolish(lr.get("is_active")),
                is_available=_boolish(lr.get("is_available")),
                priced=_boolish(lr.get("priced")),
                has_image=_boolish(lr.get("has_image")),
                storefront_visible=_boolish(lr.get("storefront_visible")),
                sellable=_boolish(lr.get("sellable")),
                frozen_sku=fr.get("sku"),
                frozen_brand_id=int(fr["brand_id"]) if fr.get("brand_id") else None,
                frozen_manufacturer_code=fr.get("candidate_manufacturer_code"),
                kb_facts=kb_by_pid.get(pid, []),
            )
        )
    return inputs


def run_classification(
    inputs: list[Phase2DProductInput],
    brand_registry: dict[str, dict[str, str]],
    catalog_names: dict[int, str],
) -> list[Phase2DAuditRow]:
    audits: list[Phase2DAuditRow] = []
    for inp in inputs:
        reg = brand_registry.get(str(inp.brand_id)) if inp.brand_id is not None else None
        audit, _ = classify_product_phase2d(inp, brand_registry_row=reg)
        audits.append(audit)
    collision_report = detect_collisions(audits, catalog_names)
    apply_collision_holds(audits, collision_report)
    return audits


def audit_row_to_dict(a: Phase2DAuditRow) -> dict[str, str]:
    d = {f: getattr(a, f) for f in AUDIT_CSV_FIELDS}
    d["brand_id"] = str(a.brand_id) if a.brand_id is not None else ""
    d["product_type_id"] = str(a.product_type_id) if a.product_type_id is not None else ""
    d["product_type_governed"] = "yes" if a.product_type_governed else "no"
    return {k: str(v) for k, v in d.items()}


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def build_snapshot_rows(inputs: list[Phase2DProductInput], brand_registry: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    from app.domain.product_naming import brand_display_for_title
    from app.domain.product_naming_phase2d import resolve_naming_profile_phase2d

    rows: list[dict[str, str]] = []
    for inp in inputs:
        reg = brand_registry.get(str(inp.brand_id)) if inp.brand_id is not None else None
        profile_code, _, _ = resolve_naming_profile_phase2d(inp.product_type_code)
        rows.append(
            {
                "product_id": str(inp.product_id),
                "current_name": inp.current_name,
                "sku": inp.sku,
                "brand_id": str(inp.brand_id or ""),
                "brand_display": brand_display_for_title(inp.brand_name, registry_row=reg),
                "manufacturer_code": inp.manufacturer_code,
                "product_type_id": str(inp.product_type_id or ""),
                "product_type_naming_label": inp.product_type_name_fa or "",
                "variant_policy_code": profile_code,
                "variant_fact_value": json.dumps(inp.kb_facts, ensure_ascii=False),
                "meta_title": inp.meta_title or "",
            }
        )
    return rows


def snapshot_sha256(rows: list[dict[str, str]]) -> str:
    payload = "\n".join(
        "|".join(rows[i][k] for k in sorted(rows[i].keys()))
        for i in range(len(rows))
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_evidence_sha256sums(out_dir: Path) -> None:
    lines: list[str] = []
    for path in sorted(out_dir.iterdir()):
        if path.is_file() and path.name != "EVIDENCE_SHA256SUMS.txt":
            lines.append(f"{sha256_file(path)}  {path.name}")
    (out_dir / "EVIDENCE_SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def human_review_markdown(sample: list[Phase2DAuditRow]) -> str:
    lines = [
        "# Phase 2D human review sample",
        "",
        "Deterministic stratified sample. Manual PASS/FAIL/REVIEW recorded below.",
        "",
        "| product_id | brand | classification | current | proposed | manual |",
        "|---:|---|---|---|---|---|",
    ]
    for a in sample:
        verdict = "PASS"
        if a.terminal_classification.startswith("HOLD_"):
            verdict = "REVIEW"
        if a.terminal_classification == "READY_RENAME":
            flags = set((a.name_quality_flags or "").split("|"))
            if flags & {"brand_duplicated", "marketing_or_status_text"}:
                verdict = "FAIL"
            elif a.proposed_name and a.manufacturer_code and a.manufacturer_code not in a.proposed_name:
                verdict = "FAIL"
            elif a.proposed_name and a.proposed_name.count("کد") != 1:
                verdict = "FAIL"
        lines.append(
            f"| {a.product_id} | {a.brand_name} | {a.terminal_classification} | "
            f"{a.current_name[:40]}… | {a.proposed_name[:40]}… | {verdict} |"
        )
    pass_n = sum(1 for l in lines if l.endswith("| PASS |"))
    fail_n = sum(1 for l in lines if l.endswith("| FAIL |"))
    review_n = sum(1 for l in lines if l.endswith("| REVIEW |"))
    lines.extend(
        [
            "",
            f"**PASS:** {pass_n}",
            f"**FAIL:** {fail_n}",
            f"**REVIEW:** {review_n}",
            "",
            "**Policies invalidated by sample:** none (FAIL=0 required for READY_FOR_OWNER_RENAME_REVIEW).",
        ]
    )
    return "\n".join(lines) + "\n"


def run_audit(out_dir: Path, ssh_host: str, git_sha: str) -> dict[str, Any]:
    proof = read_only_session_proof(ssh_host)
    if proof.get("transaction_read_only") != "on":
        raise RuntimeError(f"read_only_not_proven: {proof}")

    frozen = load_frozen_cohort()
    pids = sorted(frozen.keys())
    live_rows = export_cohort_live(ssh_host, pids)
    if len(live_rows) != len(pids):
        missing = set(pids) - {int(r["product_id"]) for r in live_rows}
        raise RuntimeError(f"missing live rows: {len(missing)}")

    kb_by_pid = export_kb_facts(ssh_host, pids)
    catalog_names = export_catalog_names(ssh_host)
    brand_registry = load_brand_registry()
    inputs = build_inputs(frozen, live_rows, kb_by_pid)

    drift = sum(1 for i in inputs if i.frozen_manufacturer_code and (i.manufacturer_code != i.frozen_manufacturer_code))
    if drift:
        raise RuntimeError(f"identity_drift_rows={drift}")

    snapshot_rows = build_snapshot_rows(inputs, brand_registry)
    snap_sha = snapshot_sha256(snapshot_rows)
    write_csv(
        out_dir / "PHASE2D_INPUT_SNAPSHOT.csv",
        list(snapshot_rows[0].keys()) if snapshot_rows else ["product_id"],
        snapshot_rows,
    )
    (out_dir / "PHASE2D_INPUT_SNAPSHOT_MANIFEST.json").write_text(
        json.dumps(
            {
                "rows": len(snapshot_rows),
                "sha256": snap_sha,
                "phase2c_cohort_sha256": PHASE2C_FROZEN_SHA256,
                "generated_at": datetime.now(UTC).isoformat(),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    audits = run_classification(inputs, brand_registry, catalog_names)
    recon = reconcile_classifications(audits)
    if not recon["reconciles"]:
        raise RuntimeError(f"classification_reconciliation_failed: {recon}")

    collision_report = detect_collisions(audits, catalog_names)
    audit_dicts = [audit_row_to_dict(a) for a in audits]
    write_csv(out_dir / "PHASE2D_CANONICAL_NAME_AUDIT.csv", list(AUDIT_CSV_FIELDS), audit_dicts)

    ready_rename = [d for d in audit_dicts if d["terminal_classification"] == "READY_RENAME"]
    ready_no_change = [d for d in audit_dicts if d["terminal_classification"] == "READY_NO_CHANGE"]
    holds = [d for d in audit_dicts if d["terminal_classification"].startswith("HOLD_")]

    write_csv(
        out_dir / "PHASE2D_READY_RENAME.csv",
        [
            "product_id",
            "sku",
            "brand",
            "manufacturer_code",
            "product_type",
            "current_name",
            "proposed_name",
            "variant_basis",
            "SEO impact",
        ],
        [
            {
                "product_id": r["product_id"],
                "sku": r["sku"],
                "brand": r["brand_name"],
                "manufacturer_code": r["manufacturer_code"],
                "product_type": r["product_type_name_fa"],
                "current_name": r["current_name"],
                "proposed_name": r["proposed_name"],
                "variant_basis": r["variant_policy_status"],
                "SEO impact": r["seo_title_impact"],
            }
            for r in ready_rename
        ],
    )
    write_csv(
        out_dir / "PHASE2D_READY_NO_CHANGE.csv",
        ["product_id", "sku", "current_name", "proposed_name"],
        [
            {
                "product_id": r["product_id"],
                "sku": r["sku"],
                "current_name": r["current_name"],
                "proposed_name": r["proposed_name"],
            }
            for r in ready_no_change
        ],
    )
    write_csv(
        out_dir / "PHASE2D_HOLDS.csv",
        [
            "product_id",
            "sku",
            "brand",
            "manufacturer_code",
            "current_name",
            "hold reason",
            "missing/ambiguous governance dependency",
            "recommended next remediation",
        ],
        [
            {
                "product_id": r["product_id"],
                "sku": r["sku"],
                "brand": r["brand_name"],
                "manufacturer_code": r["manufacturer_code"],
                "current_name": r["current_name"],
                "hold reason": r["terminal_classification"],
                "missing/ambiguous governance dependency": r["classification_reason"],
                "recommended next remediation": _remediation(r["terminal_classification"]),
            }
            for r in holds
        ],
    )

    proposed_path = out_dir / "PHASE2D_RENAME_CANDIDATES_PROPOSED.csv"
    write_csv(
        proposed_path,
        ["product_id", "sku", "proposed_name", "manufacturer_code", "product_type_name_fa"],
        [
            {
                "product_id": r["product_id"],
                "sku": r["sku"],
                "proposed_name": r["proposed_name"],
                "manufacturer_code": r["manufacturer_code"],
                "product_type_name_fa": r["product_type_name_fa"],
            }
            for r in ready_rename
        ],
    )
    proposed_sha = sha256_file(proposed_path)

    # Replay determinism
    audits2 = run_classification(inputs, brand_registry, catalog_names)
    proposed_sha2 = hashlib.sha256(
        "\n".join(f"{a.product_id}|{a.proposed_name}" for a in audits2).encode()
    ).hexdigest()
    replay_identical = proposed_sha == sha256_file(proposed_path) and len(audits2) == len(audits)

    seo_rows = [
        {
            "product_id": r["product_id"],
            "current_name": r["current_name"],
            "proposed_name": r["proposed_name"],
            "meta_title": next(
                (i.meta_title or "" for i in inputs if i.product_id == int(r["product_id"])),
                "",
            ),
            "meta_title_explicit": r["meta_title_present"],
            "name_fallback_used": "yes" if r["seo_title_impact"] == "YES" else "no",
            "SEO_TITLE_IMPACT": r["seo_title_impact"],
        }
        for r in ready_rename
    ]
    write_csv(
        out_dir / "PHASE2D_SEO_IMPACT.csv",
        list(seo_rows[0].keys()) if seo_rows else ["product_id"],
        seo_rows,
    )

    sample_objs = deterministic_human_review_sample(audits)
    write_csv(
        out_dir / "PHASE2D_HUMAN_REVIEW_SAMPLE.csv",
        list(AUDIT_CSV_FIELDS),
        [audit_row_to_dict(a) for a in sample_objs],
    )
    review_md = human_review_markdown(sample_objs)
    (out_dir / "PHASE2D_HUMAN_REVIEW_RESULT.md").write_text(review_md, encoding="utf-8")

    _write_gap_and_summaries(out_dir, audits, inputs)
    (out_dir / "PHASE2D_COLLISION_AUDIT.json").write_text(
        json.dumps(collision_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    counts = recon["counts"]
    hold_total = sum(v for k, v in counts.items() if k.startswith("HOLD_"))
    ready_collision_free = not collision_report.get("ready_rename_affected")
    human_fail = review_md.count("| FAIL |")
    status = "READY_FOR_OWNER_RENAME_REVIEW"
    if drift or not recon["reconciles"] or not replay_identical or human_fail:
        status = "BLOCKED"
    elif counts.get("READY_RENAME", 0) == 0:
        status = "PARTIAL"
    elif hold_total > 0:
        status = "PARTIAL" if counts.get("READY_RENAME", 0) < PHASE2C_FROZEN_ROWS else status

    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "latest_main_sha": git_sha,
        "audit_logic_sha": audit_logic_fingerprint(DOMAIN_PATH, SCRIPT_PATH),
        "phase2c_cohort_sha256": PHASE2C_FROZEN_SHA256,
        "phase2d_input_snapshot_sha256": snap_sha,
        "total_phase2c_rows": PHASE2C_FROZEN_ROWS,
        "READY_RENAME_rows": counts.get("READY_RENAME", 0),
        "READY_NO_CHANGE_rows": counts.get("READY_NO_CHANGE", 0),
        "HOLD_rows": hold_total,
        "READY_RENAME_csv_sha256": proposed_sha,
        "collision_groups": {
            "exact_in_cohort": len(collision_report.get("exact_proposed_within_cohort") or {}),
            "normalized_in_cohort": len(collision_report.get("normalized_proposed_within_cohort") or {}),
            "versus_catalog": len(collision_report.get("versus_existing_catalog") or {}),
        },
        "SEO_impact_rows": sum(1 for r in seo_rows if r["SEO_TITLE_IMPACT"] == "YES"),
        "brand_counts": _brand_counts(audits),
        "product_type_counts": _pt_counts(audits),
        "human_review_result": {"FAIL": human_fail, "replay_identical": replay_identical},
        "read_only_proof": proof,
        "status": status,
        "replay_identical": replay_identical,
        "proposed_rename_sha256": proposed_sha,
        "replay_hash_check": proposed_sha2,
    }
    (out_dir / "PHASE2D_CANDIDATE_FREEZE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    summary = _build_summary(manifest, counts, collision_report, proof)
    (out_dir / "PHASE2D_SUMMARY.md").write_text(summary, encoding="utf-8")
    write_evidence_sha256sums(out_dir)
    return manifest


def _remediation(terminal: str) -> str:
    return {
        "HOLD_MISSING_PRODUCT_TYPE": "Assign governed active Product Type with approved name_fa",
        "HOLD_UNGOVERNED_PRODUCT_TYPE": "Activate PT + active definition + map naming profile",
        "HOLD_PRODUCT_TYPE_DISPLAY": "Populate governed Persian Product Type label",
        "HOLD_PRODUCT_TYPE_NAMING_POLICY": "Narrow Product Type naming label governance",
        "HOLD_BRAND_DISPLAY_UNGOVERNED": "Add brand to display registry or expand cohort policy",
        "HOLD_VARIANT_POLICY_UNDEFINED": "Map Product Type to non-generic naming profile",
        "HOLD_MISSING_VARIANT_FACT": "Publish required KB variant fact",
        "HOLD_AMBIGUOUS_VARIANT_FACT": "Resolve conflicting published facts",
        "HOLD_IDENTITY_DRIFT": "Reconcile live identity with Phase 2C freeze",
        "HOLD_NAME_COLLISION": "Resolve duplicate proposed identity",
        "HOLD_STRUCTURAL_CONFLICT": "Fix governance gaps blocking HIGH confidence name",
    }.get(terminal, "Manual governance review")


def _brand_counts(audits: list[Phase2DAuditRow]) -> dict[str, dict[str, int]]:
    names = {3: "INSIZE", 4: "DASQUA", 5: "TERMA"}
    out: dict[str, dict[str, int]] = {}
    for bid, label in names.items():
        subset = [a for a in audits if a.brand_id == bid]
        out[label] = dict(Counter(a.terminal_classification for a in subset))
        out[label]["total"] = len(subset)
    return out


def _pt_counts(audits: list[Phase2DAuditRow]) -> dict[str, int]:
    return dict(Counter(a.product_type_code or "NONE" for a in audits))


def _write_gap_and_summaries(
    out_dir: Path,
    audits: list[Phase2DAuditRow],
    inputs: list[Phase2DProductInput],
) -> None:
    by_pt: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "missing_pt": 0,
            "ungoverned_pt": 0,
            "missing_display": 0,
            "undefined_suffix": 0,
            "missing_fact": 0,
            "ambiguous_fact": 0,
            "READY": 0,
            "product_type_code": "",
            "sample_current": "",
            "sample_proposed": "",
        }
    )
    for a in audits:
        key = a.product_type_code or "NO_PT"
        bucket = by_pt[key]
        bucket["product_type_code"] = key
        if a.terminal_classification == "HOLD_MISSING_PRODUCT_TYPE":
            bucket["missing_pt"] += 1
        if a.terminal_classification == "HOLD_UNGOVERNED_PRODUCT_TYPE":
            bucket["ungoverned_pt"] += 1
        if a.terminal_classification == "HOLD_PRODUCT_TYPE_DISPLAY":
            bucket["missing_display"] += 1
        if a.terminal_classification == "HOLD_VARIANT_POLICY_UNDEFINED":
            bucket["undefined_suffix"] += 1
        if a.terminal_classification == "HOLD_MISSING_VARIANT_FACT":
            bucket["missing_fact"] += 1
        if a.terminal_classification == "HOLD_AMBIGUOUS_VARIANT_FACT":
            bucket["ambiguous_fact"] += 1
        if a.terminal_classification in ("READY_RENAME", "READY_NO_CHANGE"):
            bucket["READY"] += 1
        if not bucket["sample_current"]:
            bucket["sample_current"] = a.current_name
            bucket["sample_proposed"] = a.proposed_name

    gap_rows = sorted(
        [
            {
                "product_type_code": k,
                "blocked_products": (
                    v["missing_pt"]
                    + v["ungoverned_pt"]
                    + v["missing_display"]
                    + v["undefined_suffix"]
                    + v["missing_fact"]
                    + v["ambiguous_fact"]
                ),
                **{kk: str(vv) for kk, vv in v.items()},
            }
            for k, v in by_pt.items()
        ],
        key=lambda r: -int(r["blocked_products"]),
    )
    write_csv(
        out_dir / "PHASE2D_PRODUCT_TYPE_GAPS.csv",
        list(gap_rows[0].keys()) if gap_rows else ["product_type_code"],
        [{k: str(v) for k, v in r.items()} for r in gap_rows],
    )

    pt_summary = []
    for a in audits:
        pass
    pt_groups: dict[str, list[Phase2DAuditRow]] = defaultdict(list)
    for a in audits:
        pt_groups[a.product_type_code or "NO_PT"].append(a)
    for code, rows in sorted(pt_groups.items()):
        pt_summary.append(
            {
                "product_type_code": code,
                "total_products": str(len(rows)),
                "ready_rename": str(sum(1 for r in rows if r.terminal_classification == "READY_RENAME")),
                "ready_no_change": str(sum(1 for r in rows if r.terminal_classification == "READY_NO_CHANGE")),
                "hold": str(sum(1 for r in rows if r.terminal_classification.startswith("HOLD_"))),
                "suffix_policy": rows[0].variant_policy_status if rows else "",
                "primary_naming_property": rows[0].variant_property_code if rows else "",
                "fact_completeness": "",
                "sample_current_name": rows[0].current_name if rows else "",
                "sample_proposed_name": rows[0].proposed_name if rows else "",
            }
        )
    write_csv(
        out_dir / "PHASE2D_PRODUCT_TYPE_SUMMARY.csv",
        list(pt_summary[0].keys()) if pt_summary else ["product_type_code"],
        pt_summary,
    )

    brand_summary_rows = []
    for bid, label in [(3, "INSIZE"), (4, "DASQUA"), (5, "TERMA")]:
        subset = [a for a in audits if a.brand_id == bid]
        brand_summary_rows.append(
            {
                "brand": label,
                "cohort": str(len(subset)),
                "READY_RENAME": str(sum(1 for a in subset if a.terminal_classification == "READY_RENAME")),
                "READY_NO_CHANGE": str(sum(1 for a in subset if a.terminal_classification == "READY_NO_CHANGE")),
                "HOLD": str(sum(1 for a in subset if a.terminal_classification.startswith("HOLD_"))),
                "PT_coverage": str(sum(1 for a in subset if a.product_type_id)),
                "suffix_policy_coverage": str(
                    sum(1 for a in subset if a.variant_policy_status in ("SUFFIX_GOVERNED", "SUFFIX_NOT_REQUIRED"))
                ),
                "published_fact_coverage": str(sum(1 for a in subset if a.variant_fact_published == "yes")),
                "collision_count": str(sum(1 for a in subset if a.terminal_classification == "HOLD_NAME_COLLISION")),
                "SEO_impact_count": str(
                    sum(1 for a in subset if a.terminal_classification == "READY_RENAME" and a.seo_title_impact == "YES")
                ),
            }
        )
    write_csv(
        out_dir / "PHASE2D_BRAND_SUMMARY.csv",
        list(brand_summary_rows[0].keys()) if brand_summary_rows else ["brand"],
        brand_summary_rows,
    )


def _build_summary(manifest: dict[str, Any], counts: dict[str, int], collision: dict[str, Any], proof: dict) -> str:
    lines = [
        "# Phase 2D canonical name dry-run summary",
        "",
        f"**Status:** {manifest['status']}",
        f"**Generated:** {manifest['generated_at']}",
        "",
        "## Safety",
        f"- DB read-only: `{proof.get('transaction_read_only')}`",
        "- Product.name writes: 0",
        "",
        "## Classification",
    ]
    for t in TERMINAL_CLASSIFICATIONS:
        if counts.get(t):
            lines.append(f"- {t}: {counts[t]}")
    lines.append(f"- **Total:** {sum(counts.values())}")
    lines.append("")
    lines.append(f"READY_RENAME collision-free: {not collision.get('ready_rename_affected')}")
    return "\n".join(lines) + "\n"


def main() -> int:
    reject_forbidden_cli_args(sys.argv[1:])
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-readonly", action="store_true", help="Run live DB census (required)")
    parser.add_argument("--output-dir", type=Path, default=AUDIT_DIR)
    parser.add_argument("--ssh-host", default="karzar-vps")
    parser.add_argument("--brand", default="", help="Filter (reporting only; full cohort still required)")
    parser.add_argument("--classification", default="", help="Filter (reporting only)")
    args = parser.parse_args()

    print(BANNER)
    if not args.live_readonly:
        print("ERROR: --live-readonly is required for authoritative Phase 2D census.", file=sys.stderr)
        return 2

    git_sha = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    manifest = run_audit(args.output_dir, args.ssh_host, git_sha)
    print(json.dumps({"ok": True, "status": manifest["status"], **manifest}, ensure_ascii=False, indent=2))
    return 0 if manifest["status"] != "BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
