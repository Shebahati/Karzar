#!/usr/bin/env python3
"""Karzar Taxonomy Phase 1B — read-only production baseline + working manifest."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.taxonomy_phase1b_baseline import (  # noqa: E402
    TARGET_DOMAINS,
    aggregate_category_metrics,
    build_category_metadata,
    build_working_manifest,
    catchall_candidate,
    category_census_csv_fields,
    category_row_to_census_dict,
    detect_orphans_and_cycles,
    duplicate_sibling_names,
    duplicate_slugs,
    facet_like_category,
    global_product_counts,
    helicoil_related,
    historical_drift,
    mixed_semantic_parent,
    owner_scope_candidate,
    scan_numeric_category_dependencies,
    write_csv,
    write_sha256sums,
)

FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|UPSERT|TRUNCATE|DROP|ALTER|CREATE|GRANT|REVOKE)\b",
    re.I,
)

EXPECTED_VPS = "srv5944957438"
EXPECTED_DB = "karzar_staging"
EXPECTED_USER = "karzar_staging"
EXPECTED_PG_CONTAINER = "lathe_postgres"
EXPECTED_PG_SYSTEM_ID = "7664189378775347234"

IMAGE_NOT_PLACEHOLDER = " AND ".join(
    f"pi.image_url NOT ILIKE '%{token}%'" for token in (
        "placeholder",
        "woocommerce-placeholder",
        "no-image",
        "no_image",
        "noimage",
        "default-image",
        "default_image",
        "karzar-editorial",
        "/images/placeholders/",
    )
)


def _run_ssh_psql(sql: str, *, ssh_host: str) -> str:
    if FORBIDDEN_SQL.search(sql):
        raise RuntimeError(f"Refusing mutation-capable SQL: {sql[:120]}")
    inner = sql.replace('"', '\\"')
    cmd = [
        "ssh",
        "-o",
        "BatchMode=yes",
        ssh_host,
        f'docker exec -i {EXPECTED_PG_CONTAINER} psql -U {EXPECTED_USER} -d {EXPECTED_DB} '
        f'-v ON_ERROR_STOP=1 -At -c "{inner}"',
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def _read_only_proof(ssh_host: str) -> dict[str, str]:
    out = _run_ssh_psql(
        "BEGIN; SET TRANSACTION READ ONLY; SHOW transaction_read_only; SELECT 1; ROLLBACK;",
        ssh_host=ssh_host,
    )
    tro = "on" if "on" in out.lower() else "unknown"
    return {"transaction_read_only": tro}


def collect_identity(ssh_host: str, git_sha: str) -> dict:
    host_proof = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", ssh_host, "hostname"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if host_proof != EXPECTED_VPS:
        raise RuntimeError(f"BLOCKED_VPS_IDENTITY expected={EXPECTED_VPS} got={host_proof}")
    db = _run_ssh_psql("SELECT current_database();", ssh_host=ssh_host).splitlines()[-1].strip()
    user = _run_ssh_psql("SELECT current_user;", ssh_host=ssh_host).splitlines()[-1].strip()
    sys_id = _run_ssh_psql(
        "SELECT system_identifier::text FROM pg_control_system();", ssh_host=ssh_host
    ).splitlines()[-1].strip()
    if db != EXPECTED_DB or user != EXPECTED_USER:
        raise RuntimeError("BLOCKED_DATABASE_IDENTITY")
    if sys_id != EXPECTED_PG_SYSTEM_ID:
        raise RuntimeError(f"BLOCKED_PG_SYSTEM_ID expected={EXPECTED_PG_SYSTEM_ID} got={sys_id}")
    ro = _read_only_proof(ssh_host)
    if ro.get("transaction_read_only") != "on":
        raise RuntimeError("BLOCKED_READ_ONLY_PROOF")
    return {
        "collected_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expected_live_host": EXPECTED_VPS,
        "live_host_proof": host_proof,
        "current_database": db,
        "current_user": user,
        "postgres_container": EXPECTED_PG_CONTAINER,
        "pg_system_identifier": sys_id,
        "transaction_read_only": ro["transaction_read_only"],
        "repository_git_sha": git_sha,
        "production_mutation": "NO",
        "reverification_mode": "READ_ONLY",
    }


def export_categories_tsv(ssh_host: str) -> str:
    sql = """
    SELECT id, name, slug, parent_id, megamenu_hidden, megamenu_as_leaf,
           COALESCE(hesabfa_category_code,''), COALESCE(spec_template_key,'')
    FROM categories ORDER BY id;
    """
    return _run_ssh_psql(sql, ssh_host=ssh_host)


def parse_categories_tsv(raw: str) -> list[dict]:
    rows: list[dict] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) < 8:
            continue
        rows.append(
            {
                "id": int(parts[0]),
                "name": parts[1],
                "slug": parts[2],
                "parent_id": parts[3] if parts[3] else None,
                "megamenu_hidden": parts[4],
                "megamenu_as_leaf": parts[5],
                "hesabfa_category_code": parts[6],
                "spec_template_key": parts[7],
            }
        )
    return rows


def export_products_csv(path: Path, ssh_host: str) -> None:
    image_exists = f"""
EXISTS (
  SELECT 1 FROM product_images pi
  WHERE pi.product_id = p.id
    AND pi.image_url IS NOT NULL AND length(trim(pi.image_url)) > 0
    AND {IMAGE_NOT_PLACEHOLDER}
) AS has_valid_image
"""
    copy_body = f"""
COPY (
  SELECT
    p.id AS product_id,
    p.sku,
    COALESCE(p.manufacturer_code, '') AS manufacturer_code,
    p.name AS product_name,
    COALESCE(b.name, '') AS brand,
    p.category_id,
    COALESCE(c.name, '') AS category_name,
    p.is_active,
    p.is_available,
    p.base_price,
    {image_exists},
    p.product_type_id,
    COALESCE(pt.code, '') AS product_type_code,
    COALESCE(pt.name_fa, pt.name_en, '') AS product_type_name,
    p.deleted_at
  FROM products p
  LEFT JOIN brands b ON b.id = p.brand_id
  LEFT JOIN categories c ON c.id = p.category_id
  LEFT JOIN product_types pt ON pt.id = p.product_type_id
  WHERE p.deleted_at IS NULL
  ORDER BY p.id
) TO STDOUT WITH (FORMAT CSV, HEADER true, ENCODING 'UTF8');
"""
    script = f"""set -euo pipefail
docker exec -i {EXPECTED_PG_CONTAINER} psql -U {EXPECTED_USER} -d {EXPECTED_DB} -v ON_ERROR_STOP=1 <<'EOSQL'
BEGIN;
SET TRANSACTION READ ONLY;
{copy_body}
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
        raise RuntimeError(proc.stderr[-2000:] or proc.stdout[-2000:])
    lines = proc.stdout.splitlines()
    header_idx = next((i for i, line in enumerate(lines) if line.startswith("product_id,")), None)
    if header_idx is None:
        raise RuntimeError("product CSV header missing")
    body = [lines[header_idx]]
    for line in lines[header_idx + 1 :]:
        if not line.strip() or line.strip().upper() in {"ROLLBACK", "COMMIT", "BEGIN"}:
            continue
        if not line.split(",", 1)[0].isdigit():
            continue
        body.append(line)
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


def export_megamenu_nav(ssh_host: str) -> list[dict[str, str]]:
    sql = """
    SELECT id, slug, label, sort_order, is_enabled, highlight, root_category_ids::text
    FROM megamenu_nav_groups ORDER BY sort_order, id;
    """
    raw = _run_ssh_psql(sql, ssh_host=ssh_host)
    rows: list[dict[str, str]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) < 7:
            continue
        root_ids_raw = parts[6]
        root_ids = root_ids_raw
        try:
            parsed = json.loads(root_ids_raw)
            if isinstance(parsed, list):
                root_ids = "|".join(str(int(x)) for x in parsed)
        except json.JSONDecodeError:
            pass
        rows.append(
            {
                "nav_group_id": parts[0],
                "slug": parts[1],
                "label": parts[2],
                "sort_order": parts[3],
                "is_enabled": parts[4],
                "highlight": parts[5],
                "root_category_ids": root_ids,
            }
        )
    return rows


def enrich_product_export(
    products: list[dict[str, str]],
    meta: dict[int, dict],
) -> list[dict[str, str]]:
    enriched: list[dict[str, str]] = []
    for row in products:
        cid_raw = row.get("category_id") or ""
        full_path = ""
        depth = ""
        if str(cid_raw).strip():
            m = meta.get(int(cid_raw))
            if m:
                full_path = m.get("full_path", "")
                depth = str(m.get("depth", ""))
        from catalog_target.taxonomy_phase1b_baseline import (  # noqa: PLC0415
            is_sellable_product,
            is_storefront_visible_product,
        )

        enriched.append(
            {
                **row,
                "category_full_path": full_path,
                "category_depth": depth,
                "image_present": row.get("has_valid_image", ""),
                "storefront_visible": str(is_storefront_visible_product(row)),
                "sellable": str(is_sellable_product(row)),
            }
        )
    return enriched


def build_cohorts(
    category_rows: list,
    products: list[dict[str, str]],
    meta: dict[int, dict],
    by_id: dict[int, dict],
) -> dict[str, list[dict[str, str]]]:
    owner_scope: list[dict[str, str]] = []
    mixed: list[dict[str, str]] = []
    catchalls: list[dict[str, str]] = []
    empty: list[dict[str, str]] = []
    facet_like: list[dict[str, str]] = []
    low_pt: list[dict[str, str]] = []
    helicoil: list[dict[str, str]] = []
    depth_anomalies: list[dict[str, str]] = []

    for row in category_rows:
        base = category_row_to_census_dict(row)
        if owner_scope_candidate(row.name, row.full_path):
            owner_scope.append({**base, "cohort": "TX_OWNER_001_SCOPE"})
        if mixed_semantic_parent(row.name, row.full_path):
            mixed.append({**base, "cohort": "MIXED_SEMANTIC_PARENT"})
        if catchall_candidate(row.name, row.full_path):
            catchalls.append({**base, "cohort": "CATCHALL_GENERIC"})
        if row.descendant_live == 0:
            empty.append({**base, "cohort": "EMPTY"})
        if facet_like_category(row.name):
            facet_like.append({**base, "cohort": "FACET_LIKE"})
        if row.direct_live > 0 and row.pt_assigned == 0:
            low_pt.append({**base, "cohort": "ZERO_PT_IN_CATEGORY"})
        elif row.direct_live > 0 and row.pt_missing > row.pt_assigned:
            low_pt.append({**base, "cohort": "LOW_PT_COVERAGE"})
        if helicoil_related(row.name, row.full_path):
            helicoil.append({**base, "cohort": "HELICOIL_STRUCTURAL"})
        if row.depth > 3 or (row.is_selectable and not row.is_leaf):
            depth_anomalies.append({**base, "cohort": "DEPTH_SELECTABLE_ANOMALY"})

    owner_product_ids: set[int] = set()
    for row in products:
        cid = int(row.get("category_id") or 0)
        cat = by_id.get(cid)
        if not cat:
            continue
        m = meta.get(cid, {})
        path = m.get("full_path", "")
        if owner_scope_candidate(str(cat.get("name", "")), path):
            owner_product_ids.add(int(row["product_id"]))

    return {
        "owner_scope_categories": owner_scope,
        "owner_scope_product_count": len(owner_product_ids),
        "mixed_semantic": mixed,
        "catchall": catchalls,
        "empty": empty,
        "facet_like": facet_like,
        "low_pt": low_pt,
        "helicoil": helicoil,
        "depth_anomalies": depth_anomalies,
    }


def resolve_category_names_for_ids(ids: str, by_id: dict[int, dict]) -> str:
    names: list[str] = []
    for part in (ids or "").split("|"):
        if not part.strip().isdigit():
            continue
        cat = by_id.get(int(part))
        if cat:
            names.append(str(cat.get("name") or ""))
    return " | ".join(names)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-host", default="karzar-vps")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "audit" / "taxonomy-phase1b-baseline-2026-10-15",
    )
    parser.add_argument("--git-sha", default="")
    args = parser.parse_args(argv)

    git_sha = args.git_sha or subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_products = out_dir / "_tmp_live_products.csv"

    identity = collect_identity(args.ssh_host, git_sha)
    (out_dir / "00-PRODUCTION-IDENTITY.json").write_text(
        json.dumps(identity, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    categories = parse_categories_tsv(export_categories_tsv(args.ssh_host))
    meta = build_category_metadata(categories)
    orphans, cycles = detect_orphans_and_cycles(categories, meta)
    dup_names = duplicate_sibling_names(categories)
    dup_slugs = duplicate_slugs(categories)

    export_products_csv(tmp_products, args.ssh_host)
    with tmp_products.open(encoding="utf-8", newline="") as handle:
        products = list(csv.DictReader(handle))
    products = enrich_product_export(products, meta)

    category_rows, structure = aggregate_category_metrics(categories, products, meta)
    structure["orphans"] = orphans
    structure["cycles"] = cycles
    structure["duplicate_sibling_names"] = len(dup_names)
    structure["duplicate_slugs"] = len(dup_slugs)

    global_counts = global_product_counts(products)
    drift = historical_drift(structure, global_counts)

    write_csv(
        out_dir / "01-CATEGORY-CENSUS.csv",
        category_census_csv_fields(),
        [category_row_to_census_dict(r) for r in category_rows],
    )

    product_fields = [
        "product_id",
        "sku",
        "manufacturer_code",
        "product_name",
        "brand",
        "category_id",
        "category_name",
        "category_full_path",
        "category_depth",
        "is_active",
        "is_available",
        "base_price",
        "image_present",
        "storefront_visible",
        "sellable",
        "product_type_id",
        "product_type_code",
        "product_type_name",
    ]
    write_csv(out_dir / "02-PRODUCT-CATEGORY-CENSUS.csv", product_fields, products)

    metrics_fields = [
        "category_id",
        "category_name",
        "direct_live",
        "active",
        "available",
        "priced",
        "imaged",
        "visible",
        "sellable",
        "pt_assigned",
        "pt_missing",
    ]
    write_csv(
        out_dir / "03-CATEGORY-PRODUCT-METRICS.csv",
        metrics_fields,
        [
            {
                "category_id": str(r.category_id),
                "category_name": r.name,
                "direct_live": str(r.direct_live),
                "active": str(r.active),
                "available": str(r.available),
                "priced": str(r.priced),
                "imaged": str(r.imaged),
                "visible": str(r.visible),
                "sellable": str(r.sellable),
                "pt_assigned": str(r.pt_assigned),
                "pt_missing": str(r.pt_missing),
            }
            for r in category_rows
        ],
    )

    pt_rows: list[dict[str, str]] = []
    for row in category_rows:
        if row.direct_live == 0:
            continue
        pt_rows.append(
            {
                "category_id": str(row.category_id),
                "category_name": row.name,
                "direct_live": str(row.direct_live),
                "pt_assigned": str(row.pt_assigned),
                "pt_missing": str(row.pt_missing),
                "coverage_pct": f"{(row.pt_assigned / row.direct_live * 100):.2f}"
                if row.direct_live
                else "0",
            }
        )
    write_csv(
        out_dir / "04-CATEGORY-PT-COVERAGE.csv",
        list(pt_rows[0].keys()) if pt_rows else ["category_id"],
        pt_rows,
    )

    manifest = build_working_manifest(category_rows, products)
    manifest_fields = list(manifest[0].keys()) if manifest else ["current_category_id"]
    write_csv(out_dir / "05-PHASE1B-CURRENT-TARGET-WORKING-MANIFEST.csv", manifest_fields, manifest)

    by_id = {int(c["id"]): c for c in categories}
    cohorts = build_cohorts(category_rows, products, meta, by_id)
    cohort_fields = category_census_csv_fields() + ["cohort"]
    write_csv(out_dir / "06-OWNER-SCOPE-CANDIDATES.csv", cohort_fields, cohorts["owner_scope_categories"])
    write_csv(out_dir / "07-MIXED-SEMANTIC-CATEGORIES.csv", cohort_fields, cohorts["mixed_semantic"])

    deps = scan_numeric_category_dependencies(ROOT)
    for dep in deps:
        cid = dep.get("numeric_id")
        if cid and cid.isdigit():
            cat = by_id.get(int(cid))
            dep["resolved_live_category"] = str(cat.get("name")) if cat else ""
    write_csv(
        out_dir / "08-NUMERIC-CATEGORY-ID-DEPENDENCIES.csv",
        [
            "file",
            "line",
            "numeric_id",
            "context",
            "resolved_live_category",
            "runtime_relevance",
            "risk",
            "required_future_kz_cat",
        ],
        deps,
    )

    megamenu = export_megamenu_nav(args.ssh_host)
    seo_rows: list[dict[str, str]] = []
    redirect_path = ROOT / "frontend/Storefront/src/config/category-slug-redirects.ts"
    redirect_state = redirect_path.read_text(encoding="utf-8") if redirect_path.is_file() else ""
    for group in megamenu:
        seo_rows.append(
            {
                **group,
                "resolved_root_names": resolve_category_names_for_ids(
                    group.get("root_category_ids", ""), by_id
                ),
                "public_url_pattern": "/categories/{slug}",
                "category_slug_redirects_populated": "NO"
                if "};" in redirect_state and redirect_state.strip().endswith("};")
                and "Populated by" in redirect_state
                else "UNKNOWN",
            }
        )
    for row in category_rows:
        seo_rows.append(
            {
                "record_type": "category_hub",
                "category_id": str(row.category_id),
                "slug": row.slug,
                "name": row.name,
                "depth": str(row.depth),
                "is_selectable": str(row.is_selectable),
                "direct_live": str(row.direct_live),
                "megamenu_hidden": str(row.megamenu_hidden),
                "indexable_hub_candidate": "YES" if row.depth <= 2 and row.descendant_live > 0 else "REVIEW",
            }
        )
    write_csv(
        out_dir / "09-SEO-MEGAMENU-IMPACT-BASELINE.csv",
        sorted({k for row in seo_rows for k in row}),
        seo_rows,
    )

    (out_dir / "10-HISTORICAL-DRIFT.json").write_text(
        json.dumps(drift, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    reviewed = sum(1 for row in manifest if row.get("review_status") != "UNREVIEWED")
    summary = {
        "status": "READY_FOR_OWNER_REVIEW",
        "identity": identity,
        "structure": structure,
        "global_product_counts": global_counts,
        "sql_definitions": {
            "LIVE": "deleted_at IS NULL",
            "ACTIVE": "LIVE AND is_active",
            "AVAILABLE": "LIVE AND is_available",
            "PRICED": "LIVE AND base_price > 0",
            "IMAGED": "has_valid_image (non-placeholder product_images)",
            "STOREFRONT_VISIBLE": "ACTIVE AND IMAGED (phase0b-aligned census)",
            "SELLABLE": "STOREFRONT_VISIBLE AND is_available AND PRICED",
        },
        "manifest_rows": len(manifest),
        "manifest_reviewed": reviewed,
        "manifest_unreviewed": len(manifest) - reviewed,
        "owner_scope_categories": len(cohorts["owner_scope_categories"]),
        "owner_scope_products": cohorts["owner_scope_product_count"],
        "mixed_semantic_categories": len(cohorts["mixed_semantic"]),
        "target_domains": TARGET_DOMAINS,
        "legacy_script_warning": {
            "path": "scripts/catalog_taxonomy_migrate.py",
            "apply_forbidden": True,
            "reason": "Uses ad-hoc CATEGORY_ALIASES flat remapping and can create categories; not Phase 1B constitution/KZ.CAT.* truth.",
        },
        "cohort_counts": {
            "catchall": len(cohorts["catchall"]),
            "empty": len(cohorts["empty"]),
            "facet_like": len(cohorts["facet_like"]),
            "low_pt": len(cohorts["low_pt"]),
            "helicoil": len(cohorts["helicoil"]),
            "depth_anomalies": len(cohorts["depth_anomalies"]),
            "numeric_id_dependencies": len(deps),
        },
    }
    (out_dir / "SUMMARY.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    report_lines = [
        "# Karzar Taxonomy Phase 1B — Current Baseline",
        "",
        f"**Collected:** {identity['collected_at_utc']}",
        f"**Git SHA:** {git_sha}",
        "",
        "## Safety",
        "PRODUCTION_MUTATION=NO | CATEGORY_MUTATION=NO | PRODUCT_MUTATION=NO | DEPLOYMENT=NO",
        "",
        "## Current category truth",
        json.dumps(structure, indent=2, ensure_ascii=False),
        "",
        "## Drift vs Phase 0B (2026-09-27)",
        json.dumps(drift, indent=2, ensure_ascii=False),
        "",
        "## Legacy migration script",
        "Do **not** run `scripts/catalog_taxonomy_migrate.py --apply`. It relies on "
        "non-authoritative `CATEGORY_ALIASES`, can create categories via ORM, and predates "
        "the seven-domain Phase 1B constitution / `KZ.CAT.*` identity model.",
        "",
        "## Next review wave (recommendation)",
        "1. **TX-OWNER-001 scope cohort** (owner-scope candidates) — highest governance risk, "
        "product-level decomposition required before any exit.",
        "2. **Mixed-semantic parents** (e.g. لوازم جانبی صنعتی) — accessory decomposition.",
        "3. **Helicoil / thread-repair** structural cohort — domain boundary vs Cutting/Thread Repair.",
        "4. **Numeric category ID dependencies** in import scripts — remap planning.",
        "",
    ]
    (out_dir / "FINAL_REPORT.md").write_text("\n".join(report_lines), encoding="utf-8")

    artifact_names = [
        "00-PRODUCTION-IDENTITY.json",
        "01-CATEGORY-CENSUS.csv",
        "02-PRODUCT-CATEGORY-CENSUS.csv",
        "03-CATEGORY-PRODUCT-METRICS.csv",
        "04-CATEGORY-PT-COVERAGE.csv",
        "05-PHASE1B-CURRENT-TARGET-WORKING-MANIFEST.csv",
        "06-OWNER-SCOPE-CANDIDATES.csv",
        "07-MIXED-SEMANTIC-CATEGORIES.csv",
        "08-NUMERIC-CATEGORY-ID-DEPENDENCIES.csv",
        "09-SEO-MEGAMENU-IMPACT-BASELINE.csv",
        "10-HISTORICAL-DRIFT.json",
        "SUMMARY.json",
        "FINAL_REPORT.md",
    ]
    write_sha256sums(out_dir, artifact_names)
    tmp_products.unlink(missing_ok=True)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
