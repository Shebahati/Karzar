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
import shutil
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
    CANONICAL_POLICY,
    PHASE2C_FROZEN_ROWS,
    PHASE2C_FROZEN_SHA256,
    TERMINAL_CLASSIFICATIONS,  # noqa: E402
    Phase2DAuditRow,
    Phase2DProductInput,
    apply_collision_holds,
    apply_policy_review_holds,
    audit_logic_fingerprint,
    authoritative_policy_path,
    build_owner_review_sample,
    build_policy_review_sample,
    build_variant_semantic_audit_rows,
    canonical_candidate_rows,
    canonical_candidate_sha256,
    classify_product_phase2d,
    compute_freeze_status,
    count_ready_variant_policies,
    detect_collisions,
    deterministic_human_review_sample,
    evaluate_policy_review_status,
    reconcile_classifications,
    reject_forbidden_cli_args,
    scan_semantic_anomaly_audit,
    sha256_file,
    validate_canonical_policy_registry,
    write_canonical_candidate_csv,
)

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
) -> tuple[list[Phase2DAuditRow], dict[str, Any], list[dict[str, str]], dict[str, Any]]:
    audits: list[Phase2DAuditRow] = []
    for inp in inputs:
        reg = brand_registry.get(str(inp.brand_id)) if inp.brand_id is not None else None
        audit, _ = classify_product_phase2d(inp, brand_registry_row=reg)
        audits.append(audit)
    collision_report = detect_collisions(audits, catalog_names)
    apply_collision_holds(audits, collision_report)
    policy_review = apply_policy_review_holds(audits)
    from app.domain.product_naming_phase2d_oem import (  # noqa: PLC0415
        apply_oem_semantic_holds,
        default_identity_registry,
    )

    identity_registry = default_identity_registry()
    if not identity_registry:
        raise RuntimeError("oem_identity_registry_missing")
    oem_authority_rows, oem_meta = apply_oem_semantic_holds(audits, identity_registry)
    return audits, policy_review, oem_authority_rows, oem_meta


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
        profile_code, _, _, _ = resolve_naming_profile_phase2d(inp.product_type_code)
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


def _md_cell(value: str, max_len: int = 48) -> str:
    text = (value or "").replace("|", "/").replace("\n", " ").strip()
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text


def human_review_markdown(sample: list[Phase2DAuditRow]) -> str:
    lines = [
        "# Phase 2D human review sample (historical row sample)",
        "",
        "Deterministic stratified sample preserved for Phase 2D evidence history.",
        "",
        "| product_id | brand | terminal_classification | product_type_code | canonical_title_fa | "
        "current_name | proposed_name | variant_policy | automated_policy_validation_status | validation_note |",
        "|---:|---|---|---|---|---|---|---|---|---|",
    ]
    for a in sample:
        verdict = "PASS"
        note = ""
        if a.terminal_classification.startswith("HOLD_"):
            verdict = "REVIEW"
            note = "hold_row"
        elif a.terminal_classification == "READY_RENAME":
            verdict, note = evaluate_policy_review_status(a)
        lines.append(
            "| "
            + " | ".join(
                [
                    str(a.product_id),
                    _md_cell(a.brand_name, 20),
                    a.terminal_classification,
                    a.product_type_code or "",
                    _md_cell(a.canonical_title_fa),
                    _md_cell(a.current_name),
                    _md_cell(a.proposed_name),
                    a.variant_policy or "",
                    verdict,
                    _md_cell(note, 32),
                ]
            )
            + " |"
        )
    pass_n = sum(1 for line in lines if "| PASS |" in line)
    fail_n = sum(1 for line in lines if "| FAIL |" in line)
    review_n = sum(1 for line in lines if "| REVIEW |" in line)
    lines.extend(
        [
            "",
            f"**PASS:** {pass_n}",
            f"**FAIL:** {fail_n}",
            f"**REVIEW:** {review_n}",
            "",
            "Policy-level review supersedes this row sample for owner-freeze eligibility.",
        ]
    )
    return "\n".join(lines) + "\n"


def policy_review_markdown(sample: list[Phase2DAuditRow]) -> str:
    lines = [
        "# Phase 2D policy-level automated validation",
        "",
        "**AUTOMATED VALIDATION ONLY — NOT OWNER APPROVAL**",
        "",
        "One or more representative READY rows per Product Type plus governance edge cases.",
        "",
        "| product_id | brand | terminal_classification | product_type_code | canonical_title_fa | "
        "current_name | proposed_name | variant_policy | automated_policy_validation_status | validation_note |",
        "|---:|---|---|---|---|---|---|---|---|---|",
    ]
    pass_n = fail_n = review_n = 0
    for a in sample:
        status, note = evaluate_policy_review_status(a)
        if status == "PASS":
            pass_n += 1
        elif status == "FAIL":
            fail_n += 1
        else:
            review_n += 1
        lines.append(
            "| "
            + " | ".join(
                [
                    str(a.product_id),
                    _md_cell(a.brand_name, 20),
                    a.terminal_classification,
                    a.product_type_code or "",
                    _md_cell(a.canonical_title_fa),
                    _md_cell(a.current_name),
                    _md_cell(a.proposed_name),
                    a.variant_policy or "",
                    status,
                    _md_cell(note, 32),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            f"**PASS:** {pass_n}",
            f"**FAIL:** {fail_n}",
            f"**REVIEW:** {review_n}",
            "",
            "READY Product Types require PASS on all sampled representatives for that policy.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_audit(
    out_dir: Path,
    ssh_host: str,
    git_sha: str,
    *,
    logic_git_sha: str | None = None,
) -> dict[str, Any]:
    proof = read_only_session_proof(ssh_host)
    if proof.get("transaction_read_only") != "on":
        raise RuntimeError(f"read_only_not_proven: {proof}")

    auth_policy = authoritative_policy_path()
    authoritative_policy_sha256 = sha256_file(auth_policy)
    policy_snapshot_path = out_dir / "PHASE2D_PRODUCT_TYPE_NAMING_POLICY.csv"
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(auth_policy, policy_snapshot_path)
    audit_snapshot_policy_sha256 = sha256_file(policy_snapshot_path)
    if authoritative_policy_sha256 != audit_snapshot_policy_sha256:
        raise RuntimeError("policy_snapshot_sha_mismatch")

    registry_errors = validate_canonical_policy_registry()
    if registry_errors:
        raise RuntimeError(f"canonical_policy_registry_invalid: {registry_errors[:5]}")

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

    audits, policy_review_meta, oem_authority_rows, oem_meta = run_classification(
        inputs, brand_registry, catalog_names
    )
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
    candidate_rows = canonical_candidate_rows(audits)
    first_run_candidate_sha256 = canonical_candidate_sha256(candidate_rows)
    write_canonical_candidate_csv(proposed_path, candidate_rows)
    written_candidate_file_sha256 = sha256_file(proposed_path)

    audits2, _, _, _ = run_classification(inputs, brand_registry, catalog_names)
    replay_rows = canonical_candidate_rows(audits2)
    replay_candidate_sha256 = canonical_candidate_sha256(replay_rows)
    replay_identical = (
        first_run_candidate_sha256 == replay_candidate_sha256 == written_candidate_file_sha256
    )

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

    policy_sample = build_policy_review_sample(audits)
    write_csv(
        out_dir / "PHASE2D_POLICY_REVIEW_SAMPLE.csv",
        list(AUDIT_CSV_FIELDS),
        [audit_row_to_dict(a) for a in policy_sample],
    )
    (out_dir / "PHASE2D_POLICY_REVIEW_RESULT.md").write_text(
        policy_review_markdown(policy_sample),
        encoding="utf-8",
    )

    oem_by_pid = {int(r["product_id"]): r for r in oem_authority_rows}
    write_csv(
        out_dir / "PHASE2D_OEM_SEMANTIC_AUTHORITY.csv",
        list(oem_authority_rows[0].keys()) if oem_authority_rows else ["product_id"],
        oem_authority_rows,
    )
    remediation_rows = [
        {
            "product_id": r["product_id"],
            "manufacturer_code": r["manufacturer_code"],
            "current_product_type": r["persisted_product_type_code"],
            "OEM_identity": r["oem_category_or_family"],
            "recommended_product_type": r["recommended_product_type_code"],
            "recommended_title": r["recommended_canonical_title_fa"],
            "reason": r["semantic_conflict_reason"],
            "OEM_locator": f"{r['oem_source']}#page={r['oem_page_pdf']};code={r['oem_code']}",
        }
        for r in oem_authority_rows
        if r.get("candidate_eligible_after_oem_gate") != "yes"
    ]
    write_csv(
        out_dir / "PHASE2D_PRODUCT_TYPE_REMEDIATION_PROPOSALS.csv",
        list(remediation_rows[0].keys()) if remediation_rows else ["product_id"],
        remediation_rows,
    )

    owner_sample = build_owner_review_sample(audits)
    owner_rows = []
    for a in owner_sample:
        oem_row = oem_by_pid.get(a.product_id, {})
        owner_rows.append(
            {
                "product_id": str(a.product_id),
                "manufacturer_code": a.manufacturer_code,
                "OEM_product_heading": oem_row.get("oem_product_heading", ""),
                "OEM_family": oem_row.get("oem_category_or_family", ""),
                "OEM_subtype": oem_row.get("OEM_subtype", ""),
                "exact_pdf_page": oem_row.get("exact_pdf_page", oem_row.get("oem_page_pdf", "")),
                "product_type_code": a.product_type_code,
                "canonical_title_fa": a.canonical_title_fa,
                "title_qualifier": oem_row.get("title_qualifier", ""),
                "current_name": a.current_name,
                "proposed_name": a.proposed_name,
                "product_type_semantic_status": oem_row.get("semantic_match_status", ""),
                "canonical_title_semantic_status": oem_row.get("canonical_title_verdict", ""),
                "owner_review_status": "PENDING",
                "owner_note": "",
            }
        )
    write_csv(
        out_dir / "PHASE2D_OWNER_REVIEW_SAMPLE.csv",
        list(owner_rows[0].keys()) if owner_rows else ["product_id"],
        owner_rows,
    )

    semantic_rows = build_variant_semantic_audit_rows(audits)
    write_csv(
        out_dir / "PHASE2D_VARIANT_SEMANTIC_AUDIT.csv",
        list(semantic_rows[0].keys()) if semantic_rows else ["product_type_code"],
        semantic_rows,
    )
    semantic_anomaly = scan_semantic_anomaly_audit(audits)
    (out_dir / "PHASE2D_SEMANTIC_ANOMALY_AUDIT.json").write_text(
        json.dumps(semantic_anomaly, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    variant_counts = count_ready_variant_policies(audits)
    semantic_dimension_failures = sum(
        1 for r in semantic_rows if r.get("semantic_validation") != "PASS"
    )

    _write_gap_and_summaries(out_dir, audits, inputs)
    (out_dir / "PHASE2D_COLLISION_AUDIT.json").write_text(
        json.dumps(collision_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    counts = recon["counts"]
    hold_total = sum(v for k, v in counts.items() if k.startswith("HOLD_"))
    spec_v1 = ROOT / "docs/architecture/specs/product-naming-v1"
    oem_occurrence_sha = sha256_file(spec_v1 / "INSIZE_OEM_CODE_OCCURRENCES.csv")
    oem_identity_sha = sha256_file(spec_v1 / "INSIZE_OEM_PRODUCT_IDENTITY_REGISTRY.csv")
    oem_canonical_policy_sha = sha256_file(spec_v1 / "OEM_CANONICAL_IDENTITY_POLICY.csv")
    from app.domain.product_naming_phase2d_oem import governed_oem_source_shas  # noqa: PLC0415

    sha_108a, sha_108b = governed_oem_source_shas()
    ready_oem_fail = 0
    for a in audits:
        if a.terminal_classification != "READY_RENAME":
            continue
        oem_row = oem_by_pid.get(a.product_id)
        if not oem_row or oem_row.get("candidate_eligible_after_oem_gate") != "yes":
            ready_oem_fail += 1
    ready_collision_count = len(collision_report.get("ready_rename_affected") or [])
    logic_sha256 = audit_logic_fingerprint(DOMAIN_PATH, SCRIPT_PATH)
    phase2d_logic_git_sha = logic_git_sha or git_sha
    latest_main_sha = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "origin/main"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    approved_title = sum(1 for p in CANONICAL_POLICY.values() if p.title_label_status == "APPROVED")
    approved_variant = sum(
        1
        for p in CANONICAL_POLICY.values()
        if p.variant_policy in ("VARIANT_REQUIRED", "VARIANT_NOT_REQUIRED_APPROVED")
    )
    status = compute_freeze_status(
        reconciles=recon["reconciles"],
        identity_drift=drift,
        replay_identical=replay_identical,
        ready_collision_count=ready_collision_count,
        policy_review=policy_review_meta,
        read_only_ok=proof.get("transaction_read_only") == "on",
        semantic_dimension_failures=semantic_dimension_failures,
        wrong_unit_canary_failures=semantic_anomaly.get("wrong_unit_canary_failures", 0),
        variant_not_required_with_suffix=variant_counts.get("variant_not_required_with_suffix", 0),
        ready_oem_semantic_failures=ready_oem_fail,
    )
    if status == "READY_FOR_OWNER_RENAME_REVIEW" and counts.get("READY_RENAME", 0) == 0:
        status = "PARTIAL"

    manifest = {
        "status": status,
        "generated_at": datetime.now(UTC).isoformat(),
        "latest_main_sha": latest_main_sha,
        "phase2d_semantic_logic_git_sha": phase2d_logic_git_sha,
        "phase2d_logic_git_sha": phase2d_logic_git_sha,
        "phase2d_logic_sha256": logic_sha256,
        "audit_logic_sha256": logic_sha256,
        "audit_logic_git_sha": phase2d_logic_git_sha,
        "phase2d_exact_oem_logic_git_sha": phase2d_logic_git_sha,
        "phase2d_oem_semantic_logic_git_sha": phase2d_logic_git_sha,
        "authoritative_run_logic_sha": phase2d_logic_git_sha,
        "artifact_generated_from_logic_sha": phase2d_logic_git_sha,
        "108A_sha256": sha_108a,
        "108B_sha256": sha_108b,
        "OEM_occurrence_registry_sha256": oem_occurrence_sha,
        "OEM_identity_registry_sha256": oem_identity_sha,
        "OEM_canonical_policy_sha256": oem_canonical_policy_sha,
        "oem_evidence_registry_sha256": oem_identity_sha,
        "pre_exact_gate_candidates": oem_meta.get("pre_exact_gate_candidates", 0),
        "pre_oem_READY": oem_meta.get("pre_oem_READY", 0),
        "post_oem_READY": counts.get("READY_RENAME", 0),
        "final_READY_RENAME": counts.get("READY_RENAME", 0),
        "exact_occurrence_count": oem_meta.get("occurrence_EXACT_PRODUCT_IDENTITY", 0),
        "ambiguous_occurrence_count": oem_meta.get("occurrence_AMBIGUOUS", 0),
        "accessory_only_count": oem_meta.get("occurrence_INSUFFICIENT", 0),
        "evidence_insufficient_count": oem_meta.get("OEM_EVIDENCE_INSUFFICIENT", 0),
        "product_type_semantic_pass": oem_meta.get("OEM_SEMANTIC_MATCH", 0)
        + oem_meta.get("OEM_SEMANTIC_BROADER_BUT_ACCEPTABLE", 0),
        "product_type_conflicts": oem_meta.get("OEM_PRODUCT_TYPE_CONFLICT", 0),
        "canonical_title_pass": oem_meta.get("title_OEM_TITLE_EXACT", 0)
        + oem_meta.get("title_OEM_TITLE_BROADER_BUT_SUFFICIENT", 0),
        "canonical_title_conflicts": oem_meta.get("title_OEM_TITLE_CONFLICT", 0),
        "canonical_title_requires_qualifier": oem_meta.get("title_OEM_TITLE_REQUIRES_QUALIFIER", 0),
        "OEM_EVIDENCE_AMBIGUOUS": oem_meta.get("OEM_EVIDENCE_AMBIGUOUS", 0),
        "all_READY_have_exact_OEM_product_evidence": ready_oem_fail == 0,
        "all_READY_have_product_type_semantic_pass": ready_oem_fail == 0,
        "all_READY_have_canonical_title_semantic_pass": ready_oem_fail == 0,
        "OEM_semantic_validated_rows": oem_meta.get("OEM_semantic_validated_rows", 0),
        "OEM_SEMANTIC_MATCH": oem_meta.get("OEM_SEMANTIC_MATCH", 0),
        "OEM_SEMANTIC_BROADER_BUT_ACCEPTABLE": oem_meta.get("OEM_SEMANTIC_BROADER_BUT_ACCEPTABLE", 0),
        "OEM_PRODUCT_TYPE_CONFLICT": oem_meta.get("OEM_PRODUCT_TYPE_CONFLICT", 0),
        "OEM_CANONICAL_TITLE_CONFLICT": oem_meta.get("title_OEM_TITLE_CONFLICT", 0),
        "OEM_MULTI_FUNCTION_TITLE_CONFLICT": oem_meta.get("OEM_MULTI_FUNCTION_TITLE_CONFLICT", 0),
        "OEM_EVIDENCE_INSUFFICIENT": oem_meta.get("OEM_EVIDENCE_INSUFFICIENT", 0),
        "HOLD_PRODUCT_TYPE_AUTHORITY_CONFLICT": counts.get("HOLD_PRODUCT_TYPE_AUTHORITY_CONFLICT", 0),
        "HOLD_CANONICAL_TITLE_AUTHORITY_CONFLICT": counts.get(
            "HOLD_CANONICAL_TITLE_AUTHORITY_CONFLICT", 0
        ),
        "HOLD_MULTI_FUNCTION_IDENTITY_CONFLICT": counts.get("HOLD_MULTI_FUNCTION_IDENTITY_CONFLICT", 0),
        "HOLD_OEM_SEMANTIC_EVIDENCE_MISSING": counts.get("HOLD_OEM_SEMANTIC_EVIDENCE_MISSING", 0),
        "all_READY_have_OEM_semantic_pass": ready_oem_fail == 0,
        "authoritative_policy_path": str(auth_policy.relative_to(ROOT)),
        "authoritative_policy_sha256": authoritative_policy_sha256,
        "policy_snapshot_sha256": audit_snapshot_policy_sha256,
        "phase2c_cohort_sha256": PHASE2C_FROZEN_SHA256,
        "phase2d_input_snapshot_sha256": snap_sha,
        "total_rows": PHASE2C_FROZEN_ROWS,
        "total_phase2c_rows": PHASE2C_FROZEN_ROWS,
        "READY_RENAME": counts.get("READY_RENAME", 0),
        "READY_NO_CHANGE": counts.get("READY_NO_CHANGE", 0),
        "HOLD": hold_total,
        "READY_RENAME_rows": counts.get("READY_RENAME", 0),
        "READY_NO_CHANGE_rows": counts.get("READY_NO_CHANGE", 0),
        "HOLD_rows": hold_total,
        "classification_reconciles": recon["reconciles"],
        "first_run_candidate_sha256": first_run_candidate_sha256,
        "replay_candidate_sha256": replay_candidate_sha256,
        "written_candidate_file_sha256": written_candidate_file_sha256,
        "replay_identical": replay_identical,
        "approved_title_policy_count": approved_title,
        "approved_variant_policy_count": approved_variant,
        "policy_review_PASS_count": policy_review_meta.get("PASS", 0),
        "policy_review_FAIL_count": policy_review_meta.get("FAIL", 0),
        "policy_review_REVIEW_count": policy_review_meta.get("REVIEW", 0),
        "owner_review_status": "PENDING",
        "VARIANT_REQUIRED_READY": variant_counts.get("VARIANT_REQUIRED_READY", 0),
        "VARIANT_NOT_REQUIRED_READY": variant_counts.get("VARIANT_NOT_REQUIRED_READY", 0),
        "variant_not_required_with_suffix": variant_counts.get("variant_not_required_with_suffix", 0),
        "semantic_dimension_failures": semantic_dimension_failures,
        "wrong_unit_canary_failures": semantic_anomaly.get("wrong_unit_canary_failures", 0),
        "collision_groups": {
            "exact_in_cohort": len(collision_report.get("exact_proposed_within_cohort") or {}),
            "normalized_in_cohort": len(collision_report.get("normalized_proposed_within_cohort") or {}),
            "versus_catalog": len(collision_report.get("versus_existing_catalog") or {}),
            "ready_rename_affected": ready_collision_count,
        },
        "SEO_impact_rows": sum(1 for r in seo_rows if r["SEO_TITLE_IMPACT"] == "YES"),
        "brand_counts": _brand_counts(audits),
        "product_type_counts": _pt_counts(audits),
        "read_only_proof": proof,
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
        "HOLD_PRODUCT_TYPE_TITLE_LABEL_UNAPPROVED": "Approve canonical_title_fa in naming policy registry",
        "HOLD_POLICY_REVIEW_BLOCKED": "Resolve policy-level review FAIL/REVIEW for Product Type",
        "HOLD_SEMANTIC_SUFFIX_LEAKAGE": "Remove variant suffix under NOT_REQUIRED policy",
        "HOLD_SEMANTIC_UNIT_MISMATCH": "Fix formatter/dimension or variant governance",
        "HOLD_PRODUCT_TYPE_AUTHORITY_CONFLICT": "Reassign Product Type per OEM catalogue (proposal only)",
        "HOLD_CANONICAL_TITLE_AUTHORITY_CONFLICT": "Refine canonical_title_fa policy for OEM subtype",
        "HOLD_MULTI_FUNCTION_IDENTITY_CONFLICT": "Govern multi-function title/Product Type before rename",
        "HOLD_OEM_SEMANTIC_EVIDENCE_MISSING": "Locate OEM catalogue evidence for manufacturer code",
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
            "blocked_products": 0,
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
        if a.terminal_classification.startswith("HOLD_"):
            bucket["blocked_products"] += 1
        if a.terminal_classification in ("READY_RENAME", "READY_NO_CHANGE"):
            bucket["READY"] += 1
        if not bucket["sample_current"]:
            bucket["sample_current"] = a.current_name
            bucket["sample_proposed"] = a.proposed_name

    gap_rows = sorted(
        [
            {
                "product_type_code": k,
                "blocked_products": str(v["blocked_products"]),
                **{kk: str(vv) for kk, vv in v.items() if kk != "blocked_products"},
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
