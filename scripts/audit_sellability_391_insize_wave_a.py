#!/usr/bin/env python3
"""Issue #391 — INSIZE Sellability Wave A read-only evidence (no mutations)."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import catalog_target.supplier_stock as supplier_stock  # noqa: E402
from catalog_target.brand_source_inventory_adapters import (  # noqa: E402
    DASQUA_GOOGLE_DRIVE_INVENTORY_LIST,
    TERMA_GOOGLE_DRIVE_INVENTORY_LIST,
    inventory_status_from_positive_price,
)
from catalog_target.core import canonicalize_brand, normalize_sku  # noqa: E402
from catalog_target.pdf import extract_pdf_row_parse, extract_pdf_text  # noqa: E402
from catalog_target.supplier_stock import (  # noqa: E402
    CatalogProduct,
    FreshnessPolicy,
    MapResultRow,
    file_sha256,
    map_stock_to_catalog,
    validate_stock_source,
    write_json,
)
from phase2c_live_readonly_census import _read_only_session_proof, _run_ssh_psql  # noqa: E402

FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|UPSERT|TRUNCATE|DROP|ALTER|CREATE|GRANT|REVOKE)\b",
    re.I,
)

INSIZE_CANONICAL_XLSX = Path(
    "/home/shebahati/KaZar/موجودی توزیع کننده 11 شهریور - افزایش 20 درصدی.xlsx"
)
INSIZE_CANONICAL_SHA = "65a9233762d5ff23148c06843c11c54db45a30ba9ee21f51d9a33f554679938a"
INSIZE_SOURCE_ID = "insize.distributor.11shahrivar.65a92337"

PLACEHOLDER_ILIKE = (
    "placeholder",
    "woocommerce-placeholder",
    "no-image",
    "no_image",
    "noimage",
    "default-image",
    "default_image",
    "default-product",
    "default_product",
    "karzar-editorial",
    "/images/placeholders/",
)

# Owner INSIZE workbook uses CODE (not in default HEADER_ALIASES).
supplier_stock.HEADER_ALIASES["code"] = "manufacturer_sku"


def _git_origin_main() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "origin/main"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _alembic_head(ssh_host: str) -> str:
    raw = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            ssh_host,
            "docker exec lathe_api alembic current 2>/dev/null | tail -1",
        ],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    if raw:
        parts = raw.split()
        return parts[0] if parts else raw
    return _run_ssh_psql(
        "SELECT version_num FROM alembic_version LIMIT 1;", ssh_host=ssh_host
    )


def _ssh(cmd: str, ssh_host: str) -> str:
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", ssh_host, cmd],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def _scalar(sql: str, ssh_host: str) -> int:
    raw = _run_ssh_psql(sql, ssh_host=ssh_host)
    line = raw.splitlines()[-1] if raw else "0"
    return int(line or 0)


def _copy_csv(copy_sql: str, ssh_host: str) -> list[dict[str, str]]:
    if FORBIDDEN_SQL.search(copy_sql):
        raise RuntimeError("mutation-capable SQL refused")
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
        raise RuntimeError(proc.stderr[-4000:] or proc.stdout[-4000:])
    lines = proc.stdout.splitlines()
    header_idx = next(
        (
            i
            for i, line in enumerate(lines)
            if "," in line
            and any(tok in line for tok in ("product_id", "brand_name", "snapshot_utc"))
        ),
        None,
    )
    if header_idx is None:
        header_idx = next((i for i, line in enumerate(lines) if "," in line), None)
    if header_idx is None:
        return []
    reader = csv.DictReader(lines[header_idx:])
    return [row for row in reader if any(v for v in row.values() if v)]


def _image_exists_sql(alias: str = "p") -> str:
    clauses = " AND ".join(
        f"pi.image_url NOT ILIKE '%{tok}%'" for tok in PLACEHOLDER_ILIKE
    )
    return f"""
    EXISTS (
      SELECT 1 FROM product_images pi
      WHERE pi.product_id = {alias}.id
        AND pi.image_url IS NOT NULL AND length(trim(pi.image_url)) > 0
        AND {clauses}
    )
    """


def collect_fresh_census(ssh_host: str, snapshot_utc: str) -> dict:
    imaged = _image_exists_sql("p")
    live = "p.deleted_at IS NULL"
    active = f"{live} AND p.is_active IS TRUE"
    priced = f"{live} AND p.base_price IS NOT NULL AND p.base_price > 0"
    available = f"{live} AND p.is_available IS TRUE"
    visible = f"{active} AND {imaged}"
    sellable = f"{visible} AND p.is_available IS TRUE AND p.base_price IS NOT NULL AND p.base_price > 0"
    only_avail = (
        f"{visible} AND p.is_available IS FALSE AND p.base_price IS NOT NULL AND p.base_price > 0"
    )

    counts = {
        "live": _scalar(f"SELECT COUNT(*) FROM products p WHERE {live};", ssh_host),
        "soft_deleted": _scalar(
            "SELECT COUNT(*) FROM products WHERE deleted_at IS NOT NULL;", ssh_host
        ),
        "active": _scalar(f"SELECT COUNT(*) FROM products p WHERE {active};", ssh_host),
        "available": _scalar(f"SELECT COUNT(*) FROM products p WHERE {available};", ssh_host),
        "priced_commercial": _scalar(f"SELECT COUNT(*) FROM products p WHERE {priced};", ssh_host),
        "visible": _scalar(f"SELECT COUNT(*) FROM products p WHERE {visible};", ssh_host),
        "sellable": _scalar(f"SELECT COUNT(*) FROM products p WHERE {sellable};", ssh_host),
        "only_availability": _scalar(f"SELECT COUNT(*) FROM products p WHERE {only_avail};", ssh_host),
    }
    counts["non_sellable"] = counts["live"] - counts["sellable"]

    brand_sql = f"""
    COPY (
      SELECT COALESCE(b.name, 'UNKNOWN') AS brand_name, COUNT(*)::text AS cnt
      FROM products p
      LEFT JOIN brands b ON b.id = p.brand_id
      WHERE {only_avail}
      GROUP BY b.name
      ORDER BY COUNT(*) DESC
    ) TO STDOUT WITH (FORMAT CSV, HEADER true, ENCODING 'UTF8');
    """
    brand_rows = _copy_csv(brand_sql, ssh_host)
    by_brand: dict[str, int] = {}
    for r in brand_rows:
        cnt_raw = (r.get("cnt") or "").strip()
        if not cnt_raw.isdigit():
            continue
        name = (r.get("brand_name") or "UNKNOWN").strip()
        by_brand[name] = int(cnt_raw)

    return {
        "snapshot_utc": snapshot_utc,
        **counts,
        "one_blocker_cohorts": {"ONLY_AVAILABILITY": counts["only_availability"]},
        "only_availability_by_brand": by_brand,
        "read_only_proven": True,
        "contract": "audit/sellability-global-root-cause-2026-10-07/CODE_SELLABILITY_CONTRACT.md",
    }


def export_only_availability(ssh_host: str, snapshot_utc: str) -> list[dict[str, str]]:
    imaged = _image_exists_sql("p")
    sql = f"""
    COPY (
      SELECT
        '{snapshot_utc}' AS snapshot_utc,
        p.id::text AS product_id,
        COALESCE(p.sku, '') AS sku,
        COALESCE(p.manufacturer_code, '') AS manufacturer_code,
        COALESCE(p.name, '') AS product_name,
        COALESCE(p.brand_id::text, '') AS brand_id,
        COALESCE(b.name, '') AS brand_name,
        COALESCE(p.category_id::text, '') AS category_id,
        COALESCE(c.name, '') AS category_name,
        p.is_active::text AS active,
        p.is_available::text AS available,
        (p.base_price IS NOT NULL AND p.base_price > 0)::text AS priced,
        ({imaged})::text AS imaged,
        ({imaged} AND p.is_active IS TRUE)::text AS visible,
        ({imaged} AND p.is_active IS TRUE AND p.is_available IS TRUE
         AND p.base_price IS NOT NULL AND p.base_price > 0)::text AS sellable,
        COALESCE(p.base_price::text, '') AS base_price
      FROM products p
      LEFT JOIN brands b ON b.id = p.brand_id
      LEFT JOIN categories c ON c.id = p.category_id
      WHERE p.deleted_at IS NULL
        AND p.is_active IS TRUE
        AND p.is_available IS FALSE
        AND p.base_price IS NOT NULL AND p.base_price > 0
        AND {imaged}
      ORDER BY p.id
    ) TO STDOUT WITH (FORMAT CSV, HEADER true, ENCODING 'UTF8');
    """
    return _copy_csv(sql, ssh_host)


def export_catalog_products(ssh_host: str, product_ids: list[int]) -> list[CatalogProduct]:
    if not product_ids:
        return []
    id_list = ",".join(str(i) for i in sorted(product_ids))
    sql = f"""
    COPY (
      SELECT
        p.id::text AS product_id,
        COALESCE(b.name, '') AS brand,
        COALESCE(p.sku, '') AS sku,
        '' AS model,
        p.is_active::text AS is_active,
        (p.deleted_at IS NOT NULL)::text AS deleted
      FROM products p
      LEFT JOIN brands b ON b.id = p.brand_id
      WHERE p.id IN ({id_list})
    ) TO STDOUT WITH (FORMAT CSV, HEADER true, ENCODING 'UTF8');
    """
    rows = _copy_csv(sql, ssh_host)
    out: list[CatalogProduct] = []
    for r in rows:
        if not (r.get("product_id") or "").isdigit():
            continue
        out.append(
            CatalogProduct(
                product_id=r["product_id"],
                brand=r["brand"],
                sku=r["sku"],
                model=r.get("model") or "",
                is_active=(r.get("is_active") or "").lower() in {"t", "true", "1"},
                deleted=(r.get("deleted") or "").lower() in {"t", "true", "1"},
            )
        )
    return out


def discover_insize_sources() -> list[dict]:
    roots = [
        Path("/home/shebahati/KaZar"),
    ]
    patterns = ["*11*شهریور*.xlsx", "*insize*.xlsx"]
    seen: dict[str, dict] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for pat in patterns:
            for path in root.rglob(pat):
                if not path.is_file():
                    continue
                try:
                    sha = file_sha256(path)
                except OSError:
                    continue
                st = path.stat()
                seen[sha] = {
                    "path": str(path),
                    "sha256": sha,
                    "size_bytes": st.st_size,
                    "mtime_utc": datetime.fromtimestamp(st.st_mtime, tz=UTC).isoformat(),
                    "canonical": sha == INSIZE_CANONICAL_SHA,
                }
    # Ensure canonical path present
    if INSIZE_CANONICAL_XLSX.is_file():
        sha = file_sha256(INSIZE_CANONICAL_XLSX)
        seen[sha] = {
            "path": str(INSIZE_CANONICAL_XLSX),
            "sha256": sha,
            "size_bytes": INSIZE_CANONICAL_XLSX.stat().st_size,
            "mtime_utc": datetime.fromtimestamp(
                INSIZE_CANONICAL_XLSX.stat().st_mtime, tz=UTC
            ).isoformat(),
            "canonical": True,
        }
    return sorted(seen.values(), key=lambda x: (not x["canonical"], x["path"]))


def insize_validation_report() -> supplier_stock.ValidationReport:
    return validate_stock_source(
        INSIZE_CANONICAL_XLSX,
        brand="INSIZE",
        supplier="INSIZE distributor",
        authority_type="AVAILABILITY",
        quantity_is_sellable_stock=False,
        source_date_override=None,
        freshness=FreshnessPolicy(),
    )


def match_method_label(m: MapResultRow) -> str:
    if m.match_class != "EXACT_MATCH":
        return m.match_class
    d = (m.match_detail or "").lower()
    if "insize_trailing" in d or INSIZE_TRAILING_A_DETAIL in (m.match_detail or ""):
        return "INSIZE_TRAILING_A_IDENTITY"
    if m.catalog_sku and normalize_sku(m.manufacturer_sku) == normalize_sku(m.catalog_sku):
        return "EXACT_SKU"
    return "manufacturer_code"


INSIZE_TRAILING_A_DETAIL = supplier_stock.INSIZE_TRAILING_A_MATCH_DETAIL


def candidate_state(
    *,
    match_class: str,
    normalized_status: str,
    freshness: str,
    source_authority_valid: bool,
) -> str:
    if match_class not in {"EXACT_MATCH"}:
        if match_class == "NOT_FOUND":
            return "NO_SOURCE_IDENTITY"
        return f"BLOCKED_{match_class}"
    if normalized_status == "UNAVAILABLE":
        return "AUTHORITATIVE_UNAVAILABLE"
    if normalized_status == "UNKNOWN":
        return "SOURCE_UNKNOWN_STATUS"
    if normalized_status == "AVAILABLE":
        if not source_authority_valid or freshness == "UNKNOWN":
            return "AVAILABLE_BUT_DATE_UNPROVEN"
        if freshness == "STALE":
            return "AVAILABLE_BUT_STALE"
        if freshness == "AGING_BUT_USABLE":
            return "AVAILABLE_AGING_REVIEW"
        if freshness == "CURRENT_ENOUGH":
            return "STRICT_UNLOCK_CANDIDATE"
    return "BLOCKED_OTHER"


def strict_unlock_row(
    product: dict[str, str],
    m: MapResultRow,
    validation: supplier_stock.ValidationReport,
) -> bool:
    if m.match_class != "EXACT_MATCH":
        return False
    if m.normalized_status != "AVAILABLE":
        return False
    if validation.freshness != "CURRENT_ENOUGH":
        return False
    if not validation.source_authority_valid:
        return False
    if product.get("visible", "").lower() not in {"t", "true", "1"}:
        return False
    if product.get("priced", "").lower() not in {"t", "true", "1"}:
        return False
    return True


def pdf_price_index(path: Path, sku_kind: str) -> dict[str, float]:
    extracted = extract_pdf_text(path)
    parsed = extract_pdf_row_parse(extracted.text, sku_kind=sku_kind, default_currency="toman")
    out: dict[str, float] = {}
    for row in parsed.rows:
        sku = normalize_sku(row.get("sku") or row.get("CODE") or "")
        if not sku:
            continue
        raw_price = row.get("price") or row.get("قیمت")
        try:
            price = float(raw_price) if raw_price not in (None, "") else None
        except (TypeError, ValueError):
            price = None
        if price is not None:
            out[sku] = price
    return out


def scan_adapter_cohort(
    cohort_rows: list[dict[str, str]],
    *,
    brand_key: str,
    adapter,
    price_index: dict[str, float],
    source_date: str | None,
    freshness_policy: FreshnessPolicy,
) -> list[dict]:
    today = date.today()
    age_days = None
    freshness = "UNKNOWN"
    if source_date:
        try:
            d = date.fromisoformat(source_date)
            age_days = (today - d).days
            freshness = freshness_policy.classify(age_days)
        except ValueError:
            pass

    results = []
    for row in cohort_rows:
        if canonicalize_brand(row.get("brand_name", "")) != brand_key:
            continue
        sku = normalize_sku(row.get("sku") or "")
        mfg = normalize_sku(row.get("manufacturer_code") or "") or sku
        lookup = mfg or sku
        price = price_index.get(lookup)
        if price is None and brand_key == "DASQUA":
            base = lookup
            price = price_index.get(f"{base}-A")
        status = inventory_status_from_positive_price(
            adapter_id=adapter.adapter_id,
            source_path=adapter.source_path,
            sku=lookup,
            price=price,
        )
        results.append(
            {
                "product_id": row["product_id"],
                "sku": row.get("sku"),
                "manufacturer_code": row.get("manufacturer_code"),
                "brand": row.get("brand_name"),
                "adapter_id": adapter.adapter_id,
                "source_path": adapter.source_path,
                "source_date": source_date or "",
                "freshness_class": freshness,
                "freshness_days": age_days if age_days is not None else "",
                "pdf_price": price if price is not None else "",
                "normalized_availability": status,
                "strict_apply_eligible": "YES"
                if status == "AVAILABLE" and freshness == "CURRENT_ENOUGH"
                else "NO",
                "blocker": "STALE_SOURCE" if freshness == "STALE" else (
                    "UNKNOWN_DATE" if freshness == "UNKNOWN" else ""
                ),
            }
        )
    return results


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def sha256sums(out_dir: Path) -> None:
    lines = []
    for p in sorted(out_dir.iterdir()):
        if p.name == "SHA256SUMS.txt" or p.is_dir():
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f"{h}  ./{p.name}")
    (out_dir / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ssh-host", default="karzar-vps")
    p.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "audit" / "sellability-391-wave-a-insize-2026-10-13",
    )
    args = p.parse_args(argv)

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    snapshot_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    origin_main = _git_origin_main()

    ro = _read_only_session_proof(args.ssh_host)
    host = _ssh("hostname", args.ssh_host)
    vol = _ssh(
        "docker inspect -f '{{range .Mounts}}{{.Name}} {{end}}' lathe_postgres",
        args.ssh_host,
    )
    alembic = _alembic_head(args.ssh_host)
    db_name = _run_ssh_psql("SELECT current_database();", ssh_host=args.ssh_host)
    db_user = _run_ssh_psql("SELECT current_user;", ssh_host=args.ssh_host)

    identity = {
        "snapshot_utc": snapshot_utc,
        "transaction_read_only": ro.get("transaction_read_only", "unknown"),
        "database": db_name,
        "db_user": db_user,
        "host": host,
        "host_expected": "srv5944957438",
        "db_container": "lathe_postgres",
        "api_container": "lathe_api",
        "database_volume": "karzar_postgres_data",
        "database_volume_verified": "karzar_postgres_data" in vol,
        "alembic": alembic,
        "origin_main": origin_main,
        "branch": "audit/catalog-391-insize-wave-a",
        "HESABFA_STOCK_SEMANTICS": "UNPROVEN",
        "mutation": {
            "PRODUCTION_MUTATION": "NO",
            "DATABASE_MUTATION": "NO",
            "HESABFA_MUTATION": "NO",
            "DEPLOYMENT": "NO",
            "AVAILABILITY_APPLY": "NO",
        },
        "read_only_proof": ro,
    }
    write_json(out_dir / "PRODUCTION_IDENTITY.json", identity)

    census = collect_fresh_census(args.ssh_host, snapshot_utc)
    census["identity"] = {
        k: identity[k]
        for k in (
            "snapshot_utc",
            "transaction_read_only",
            "database",
            "db_user",
            "alembic",
            "host",
        )
    }
    write_json(out_dir / "FRESH_CENSUS.json", census)

    only_avail = export_only_availability(args.ssh_host, snapshot_utc)
    write_csv(
        out_dir / "CURRENT_ONLY_AVAILABILITY.csv",
        list(only_avail[0].keys()) if only_avail else ["snapshot_utc"],
        only_avail,
    )

    insize_cohort = [
        r
        for r in only_avail
        if (r.get("product_id") or "").isdigit()
        and canonicalize_brand(r.get("brand_name", "")) == "INSIZE"
    ]
    write_csv(
        out_dir / "CURRENT_INSIZE_ONLY_AVAILABILITY.csv",
        list(insize_cohort[0].keys()) if insize_cohort else ["snapshot_utc"],
        insize_cohort,
    )

    sources = discover_insize_sources()
    canonical = next((s for s in sources if s["sha256"] == INSIZE_CANONICAL_SHA), None)
    if canonical is None:
        raise RuntimeError(f"canonical INSIZE workbook SHA not found: {INSIZE_CANONICAL_SHA}")

    manifest_payload = {
        "primary_source_id": INSIZE_SOURCE_ID,
        "SOURCE_AUTHORITY_VALID": "NO",
        "freshness_class": "UNKNOWN",
        "source_date_proven": False,
        "sources": sources,
        "canonical": {
            **canonical,
            "original_filename": Path(canonical["path"]).name,
            "authority_type": "AVAILABILITY",
            "parser_version": supplier_stock.PARSER_VERSION,
            "normalization_policy_version": supplier_stock.NORMALIZATION_POLICY_VERSION,
            "received_at": snapshot_utc,
            "supplier": "INSIZE distributor",
            "brand": "INSIZE",
        },
    }
    write_json(out_dir / "SOURCE_AUTHORITY_MANIFEST.json", manifest_payload)

    validation = insize_validation_report()
    # Semantics valid when CODE+وضعیت present; date still unproven.
    semantics_valid = validation.input_rows > 0 and validation.unknown == 0
    validation.source_authority_valid = semantics_valid and validation.freshness != "STALE"
    # Force fail closed: no proven calendar source_date (Wave 1A.1 policy).
    validation.source_authority_valid = False
    validation.freshness = "UNKNOWN"
    validation.deny_reasons = list(
        dict.fromkeys(
            [
                *validation.deny_reasons,
                "SOURCE_YEAR_UNPROVEN",
                "filename_shahrivar_11_without_calendar_year",
            ]
        )
    )

    catalog = export_catalog_products(
        args.ssh_host, [int(r["product_id"]) for r in insize_cohort]
    )
    mapped = map_stock_to_catalog(validation, catalog, brand="INSIZE")
    by_pid: dict[str, MapResultRow] = {}
    for m in mapped:
        if m.product_id:
            by_pid[m.product_id] = m

    stock_by_code: dict[str, supplier_stock.StockRow] = {}
    for sr in validation.rows:
        if sr.identity_key:
            stock_by_code.setdefault(sr.identity_key, sr)

    mapping_rows = []
    strict_rows = []
    counters = Counter()
    for prod in insize_cohort:
        pid = prod["product_id"]
        m = by_pid.get(pid)
        if m is None:
            counters["NOT_MAPPED"] += 1
            mapping_rows.append(
                {
                    "product_id": pid,
                    "sku": prod.get("sku"),
                    "manufacturer_code": prod.get("manufacturer_code"),
                    "match_method": "NOT_FOUND",
                    "source_code": "",
                    "source_status_raw": "",
                    "normalized_availability": "UNKNOWN",
                    "candidate_state": "NO_SOURCE_IDENTITY",
                    "freshness_class": validation.freshness,
                    "strict_unlock": "NO",
                }
            )
            continue
        method = match_method_label(m)
        src_code = m.manufacturer_sku or ""
        sr = stock_by_code.get(normalize_sku(src_code) or normalize_sku(m.catalog_sku))
        status_raw = sr.availability_status_raw if sr else ""
        state = candidate_state(
            match_class=m.match_class,
            normalized_status=m.normalized_status,
            freshness=validation.freshness,
            source_authority_valid=validation.source_authority_valid,
        )
        counters[m.match_class] += 1
        counters[m.normalized_status] += 1
        counters[state] += 1
        is_strict = strict_unlock_row(prod, m, validation)
        row = {
            "product_id": pid,
            "sku": prod.get("sku"),
            "manufacturer_code": prod.get("manufacturer_code"),
            "match_method": method,
            "source_code": src_code,
            "match_detail": m.match_detail,
            "source_status_raw": status_raw,
            "normalized_availability": m.normalized_status,
            "candidate_state": state,
            "freshness_class": validation.freshness,
            "strict_unlock": "YES" if is_strict else "NO",
        }
        mapping_rows.append(row)
        if is_strict:
            strict_rows.append(
                {
                    **row,
                    "proposed_future_change": "is_available=true (PLAN NOT APPLY)",
                    "source_id": INSIZE_SOURCE_ID,
                    "source_sha256": INSIZE_CANONICAL_SHA,
                }
            )

    write_csv(
        out_dir / "INSIZE_SOURCE_MAPPING.csv",
        [
            "product_id",
            "sku",
            "manufacturer_code",
            "match_method",
            "source_code",
            "match_detail",
            "source_status_raw",
            "normalized_availability",
            "candidate_state",
            "freshness_class",
            "strict_unlock",
        ],
        mapping_rows,
    )
    write_csv(
        out_dir / "INSIZE_WAVE_A_STRICT_UNLOCK_CANDIDATES.csv",
        [
            "product_id",
            "sku",
            "manufacturer_code",
            "match_method",
            "source_code",
            "normalized_availability",
            "candidate_state",
            "freshness_class",
            "source_id",
            "source_sha256",
            "proposed_future_change",
        ],
        strict_rows,
    )

    # Commercial delta
    available_non_strict = sum(
        1
        for r in mapping_rows
        if r["normalized_availability"] == "AVAILABLE"
        and r["strict_unlock"] != "YES"
    )
    theoretical_upper = sum(
        1 for r in mapping_rows if r["normalized_availability"] == "AVAILABLE"
    )
    commercial = {
        "SELLABLE_BEFORE": census["sellable"],
        "STRICT_CANDIDATES": len(strict_rows),
        "PROJECTED_SELLABLE_AFTER_STRICT": census["sellable"] + len(strict_rows),
        "THEORETICAL_INSIZE_UPPER_BOUND": census["sellable"] + theoretical_upper,
        "INSIZE_COHORT_ONLY_AVAILABILITY": len(insize_cohort),
        "INSIZE_EXACT_MATCHED": sum(
            1 for r in mapping_rows if r["match_method"] != "NOT_FOUND"
        ),
        "INSIZE_AVAILABLE_NORMALIZED": theoretical_upper,
        "INSIZE_UNAVAILABLE_NORMALIZED": sum(
            1 for r in mapping_rows if r["normalized_availability"] == "UNAVAILABLE"
        ),
        "INSIZE_UNKNOWN_NORMALIZED": sum(
            1 for r in mapping_rows if r["normalized_availability"] == "UNKNOWN"
        ),
        "AVAILABLE_BUT_NOT_STRICT": available_non_strict,
    }
    write_json(out_dir / "COMMERCIAL_DELTA.json", commercial)

    hist = {
        "wave_a_2026_10_07_reference": {
            "INSIZE_COHORT": 476,
            "EXACT_MATCHED": 475,
            "AVAILABLE": 10,
            "UNAVAILABLE": 465,
            "NOT_FOUND": 1,
            "STRICT": 0,
        },
        "fresh_2026_10_13": {
            "INSIZE_COHORT": len(insize_cohort),
            "EXACT_MATCHED": sum(
                1
                for r in mapping_rows
                if r["match_method"] not in {"NOT_FOUND", "NOT_MAPPED"}
            ),
            "AVAILABLE": theoretical_upper,
            "UNAVAILABLE": commercial["INSIZE_UNAVAILABLE_NORMALIZED"],
            "UNKNOWN": commercial["INSIZE_UNKNOWN_NORMALIZED"],
            "NOT_FOUND": sum(1 for r in mapping_rows if r["match_method"] == "NOT_FOUND"),
            "STRICT": len(strict_rows),
        },
        "reproducibility_notes": (
            "Counts comparable when live ONLY_AVAILABILITY membership stable; "
            "strict gate requires proven source_date CURRENT_ENOUGH."
        ),
    }
    write_json(out_dir / "HISTORICAL_REPRODUCIBILITY.json", hist)

    dasqua_pdf = Path(DASQUA_GOOGLE_DRIVE_INVENTORY_LIST.source_path)
    terma_pdf = Path(TERMA_GOOGLE_DRIVE_INVENTORY_LIST.source_path)
    dasqua_prices = pdf_price_index(dasqua_pdf, "dasqua") if dasqua_pdf.is_file() else {}
    terma_prices = pdf_price_index(terma_pdf, "term") if terma_pdf.is_file() else {}
    fp = FreshnessPolicy()
    dasqua_scan = scan_adapter_cohort(
        only_avail,
        brand_key="DASQUA",
        adapter=DASQUA_GOOGLE_DRIVE_INVENTORY_LIST,
        price_index=dasqua_prices,
        source_date="2026-05-02",
        freshness_policy=fp,
    )
    terma_scan = scan_adapter_cohort(
        only_avail,
        brand_key="TERMA",
        adapter=TERMA_GOOGLE_DRIVE_INVENTORY_LIST,
        price_index=terma_prices,
        source_date=None,
        freshness_policy=fp,
    )
    md_lines = [
        "# Secondary read-only DASQUA / TERMA scan",
        "",
        f"Snapshot UTC: {snapshot_utc}",
        "",
        "## DASQUA (ONLY_AVAILABILITY cohort)",
        f"- Rows scanned: {len(dasqua_scan)} (expected 22)",
        f"- Adapter: `{DASQUA_GOOGLE_DRIVE_INVENTORY_LIST.adapter_id}`",
        f"- Source date used: 2026-05-02 (in-PDF Jalali; STALE >45d)",
        f"- Normalized AVAILABLE: {sum(1 for r in dasqua_scan if r['normalized_availability']=='AVAILABLE')}",
        f"- Strict eligible: {sum(1 for r in dasqua_scan if r['strict_apply_eligible']=='YES')}",
        "",
        "## TERMA (ONLY_AVAILABILITY cohort)",
        f"- Rows scanned: {len(terma_scan)} (expected 4)",
        f"- Adapter: `{TERMA_GOOGLE_DRIVE_INVENTORY_LIST.adapter_id}`",
        "- Source date: UNPROVEN → freshness UNKNOWN",
        f"- Normalized AVAILABLE: {sum(1 for r in terma_scan if r['normalized_availability']=='AVAILABLE')}",
        f"- Strict eligible: {sum(1 for r in terma_scan if r['strict_apply_eligible']=='YES')}",
        "",
        "No APPLY. Price column from PDF is adapter input only; not Karzar base_price authority.",
    ]
    (out_dir / "SECONDARY_DASQUA_TERMA_SCAN.md").write_text(
        "\n".join(md_lines) + "\n", encoding="utf-8"
    )
    write_csv(
        out_dir / "SECONDARY_DASQUA_SCAN.csv",
        list(dasqua_scan[0].keys()) if dasqua_scan else ["product_id"],
        dasqua_scan,
    )
    write_csv(
        out_dir / "SECONDARY_TERMA_SCAN.csv",
        list(terma_scan[0].keys()) if terma_scan else ["product_id"],
        terma_scan,
    )

    if len(strict_rows) == 0:
        req = out_dir / "INSIZE_FRESH_STOCK_SOURCE_REQUEST.md"
        req.write_text(
            """# INSIZE fresh stock source request (distributor)

Wave A strict unlock requires **proven calendar `source_date`** and `CURRENT_ENOUGH` freshness (≤14 days per `docs/catalog/SUPPLIER_STOCK_AUTHORITY.md`).

## Please provide

1. Excel or CSV export of distributor inventory (same family as `موجودی توزیع کننده … 11 شهریور`).
2. Columns: **CODE** (manufacturer code), **وضعیت** (`موجود` / `نا موجود`), optional warehouse qty columns.
3. Explicit **calendar date** of the snapshot (Gregorian or Jalali with year) in the file or cover email.
4. Do **not** rely on filename month/day without year.

## Karzar will

- SHA256 the file, record manifest metadata, and rematch the **INSIZE ONLY_AVAILABILITY** cohort using governed identity only (`manufacturer_code`, exact SKU, `INSIZE_TRAILING_A_IDENTITY`).
- Produce a strict allowlist for Owner review before any `is_available` APPLY.

## Current blocker

Canonical workbook SHA `65a92337…` has clear `وضعیت` semantics but **SOURCE_YEAR_UNPROVEN** → freshness **UNKNOWN** → **0** strict candidates.
""",
            encoding="utf-8",
        )

    source_semantics = {
        "INSIZE_workbook": {
            "columns": ["CODE", "وضعیت", "warehouse qty columns (not used for status)"],
            "availability_rule": "وضعیت موجود/نا موجود only; quantity_is_sellable_stock=false",
            "price_not_availability": True,
            "identity_rules": [
                "EXACT manufacturer_code/SKU",
                "INSIZE_TRAILING_A_IDENTITY (identity only)",
            ],
            "freshness": validation.freshness,
            "source_date_proven": False,
            "SOURCE_AUTHORITY_VALID": validation.source_authority_valid,
        }
    }
    write_json(out_dir / "SOURCE_SEMANTICS.json", source_semantics)

    status = (
        "BLOCKED_ON_FRESH_INSIZE_STOCK_AUTHORITY"
        if len(strict_rows) == 0
        else "READY_FOR_OWNER_WAVE_D_REVIEW"
    )
    owner = (
        "REQUEST_FRESH_INSIZE_STOCK_SOURCE"
        if len(strict_rows) == 0
        else "AUTHORIZE_WAVE_D_ALLOWLIST_REVIEW"
    )

    readme = f"""# INSIZE Sellability Wave A — Issue #391 ({snapshot_utc[:10]})

Read-only production evidence. **No APPLY.**

## Status

- `{status}`
- Owner decision: `{owner}`
- Strict unlock candidates: **{len(strict_rows)}**
- Sellable now: **{census['sellable']}**

## Safety

```text
PRODUCTION_MUTATION = NO
DATABASE_MUTATION = NO (transaction_read_only={identity['transaction_read_only']})
HESABFA_MUTATION = NO
AVAILABILITY_APPLY = NO
```

## Start here

1. [`FINAL_REPORT.md`](FINAL_REPORT.md)
2. [`FRESH_CENSUS.json`](FRESH_CENSUS.json)
3. [`INSIZE_SOURCE_MAPPING.csv`](INSIZE_SOURCE_MAPPING.csv)
4. [`INSIZE_WAVE_A_STRICT_UNLOCK_CANDIDATES.csv`](INSIZE_WAVE_A_STRICT_UNLOCK_CANDIDATES.csv)

## Canonical INSIZE source

- SHA256: `{INSIZE_CANONICAL_SHA}`
- Path (local): `{canonical['path']}`

Hashes: [`SHA256SUMS.txt`](SHA256SUMS.txt)
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")

    final = f"""# Issue #391 — INSIZE Wave A Final Report

**Status:** {status}  
**Snapshot UTC:** {snapshot_utc}  
**origin/main:** `{origin_main}`  
**Strict unlock candidates:** {len(strict_rows)}  
**APPLY authorized:** NO

## Fresh census

| Metric | Count |
|--------|------:|
| Live | {census['live']} |
| Sellable | {census['sellable']} |
| ONLY_AVAILABILITY | {census['only_availability']} |
| INSIZE ONLY_AVAILABILITY | {len(insize_cohort)} |

## INSIZE stock mapping (canonical workbook)

| Class | Count |
|-------|------:|
| Cohort | {len(insize_cohort)} |
| Exact matched | {commercial['INSIZE_EXACT_MATCHED']} |
| AVAILABLE (normalized) | {commercial['INSIZE_AVAILABLE_NORMALIZED']} |
| UNAVAILABLE | {commercial['INSIZE_UNAVAILABLE_NORMALIZED']} |
| UNKNOWN | {commercial['INSIZE_UNKNOWN_NORMALIZED']} |
| **Strict unlock** | **{len(strict_rows)}** |

## Historical reproducibility (Wave A 2026-10-07)

| Metric | 2026-10-07 | Fresh |
|--------|----------:|------:|
| INSIZE cohort | 476 | {len(insize_cohort)} |
| Exact matched | 475 | {commercial['INSIZE_EXACT_MATCHED']} |
| AVAILABLE | 10 | {commercial['INSIZE_AVAILABLE_NORMALIZED']} |
| UNAVAILABLE | 465 | {commercial['INSIZE_UNAVAILABLE_NORMALIZED']} |
| NOT_FOUND | 1 | {hist['fresh_2026_10_13']['NOT_FOUND']} |
| STRICT | 0 | {len(strict_rows)} |

## SOURCE_SEMANTICS

- `وضعیت` → AVAILABLE/UNAVAILABLE (quantity columns not used).
- Freshness **UNKNOWN** (`SOURCE_YEAR_UNPROVEN`); `SOURCE_AUTHORITY_VALID=NO` for strict APPLY.
- See [`SOURCE_SEMANTICS.json`](SOURCE_SEMANTICS.json).

## Commercial delta

See [`COMMERCIAL_DELTA.json`](COMMERCIAL_DELTA.json).

## Owner decision

**{owner}**
"""
    (out_dir / "FINAL_REPORT.md").write_text(final, encoding="utf-8")

    sha256sums(out_dir)

    summary = {
        "status": status,
        "owner_decision": owner,
        "strict_count": len(strict_rows),
        "insize_cohort": len(insize_cohort),
        "sellable": census["sellable"],
        "out_dir": str(out_dir),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
