#!/usr/bin/env python3
"""#258 / #391 — INSIZE final commercial source reconciliation (read-only, no APPLY)."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.core import normalize_sku  # noqa: E402,I001
from catalog_target.insize_commercial_reconcile_258 import state_hash  # noqa: E402
from catalog_target.insize_trailing_a_identity import (  # noqa: E402
    MATCH_DETAIL as INSIZE_TRAILING_A_DETAIL,
    match_source_code_to_catalog_skus,
)
from catalog_target.supplier_stock import file_sha256, parse_quantity  # noqa: E402
from catalog_target.xlsx import iter_xlsx_rows, read_xlsx_cell  # noqa: E402
from phase2c_live_readonly_census import _read_only_session_proof, _run_ssh_psql  # noqa: E402

FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|UPSERT|TRUNCATE|DROP|ALTER|CREATE|GRANT|REVOKE)\b",
    re.I,
)

INSIZE_FINAL_XLSX = Path(
    "/home/shebahati/KaZar/DOCS/موجودی توزیع کننده 11 شهریور - دلار 300 هزار تومان - نهایی.xlsx"
)
INSIZE_FINAL_SHA = "8324b2c175a703ab0ff7364da4a33f82c440d592cdc10d990c133bed39ac2989"
INSIZE_OWNER_SOURCE_XLSX = INSIZE_FINAL_XLSX
INSIZE_OWNER_SOURCE_SHA = INSIZE_FINAL_SHA
SUPERSEDED_SHA_BEB549 = "beb549109165a1fd0d156af8d9b8a9622eb3a04e7fc92b07c548993ee98669cf"
FX_TOMAN_PER_USD = Decimal("300000")
AVAILABLE_TOKENS = {"موجود"}
UNAVAILABLE_TOKENS = {"نا موجود", "ناموجود"}

PLACEHOLDER_ILIKE = (
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


def _git_origin_main() -> str:
    return subprocess.run(
        ["git", "rev-parse", "origin/main"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


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
        (i for i, line in enumerate(lines) if "," in line and "product_id" in line),
        None,
    )
    if header_idx is None:
        return []
    return list(csv.DictReader(lines[header_idx:]))


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


def export_live_insize(ssh_host: str, snapshot_utc: str) -> list[dict[str, str]]:
    imaged = _image_exists_sql("p")
    sql = f"""
    COPY (
      SELECT
        '{snapshot_utc}' AS snapshot_utc,
        p.id::text AS product_id,
        COALESCE(p.sku, '') AS sku,
        COALESCE(p.manufacturer_code, '') AS manufacturer_code,
        COALESCE(p.name, '') AS name,
        COALESCE(b.name, '') AS brand,
        COALESCE(p.brand_id::text, '') AS brand_id,
        p.is_active::text AS is_active,
        p.is_available::text AS is_available,
        COALESCE(p.base_price::text, '') AS base_price,
        COALESCE(p.original_price::text, '') AS original_price,
        COALESCE(p.deleted_at::text, '') AS deleted_at,
        ({imaged})::text AS image_present,
        ({imaged} AND p.is_active IS TRUE AND p.is_available IS TRUE
         AND p.base_price IS NOT NULL AND p.base_price > 0)::text AS current_sellable
      FROM products p
      LEFT JOIN brands b ON b.id = p.brand_id
      WHERE p.deleted_at IS NULL
        AND (
          upper(trim(split_part(COALESCE(b.name,''), '|', 1))) = 'INSIZE'
          OR COALESCE(b.name,'') ILIKE '%INSIZE%'
          OR COALESCE(b.name,'') ILIKE '%اینسایز%'
        )
      ORDER BY p.id
    ) TO STDOUT WITH (FORMAT CSV, HEADER true, ENCODING 'UTF8');
    """
    rows = _copy_csv(sql, ssh_host)
    return [r for r in rows if (r.get("product_id") or "").isdigit()]


def _scalar_sellable_counts(ssh_host: str) -> dict[str, int]:
    imaged = _image_exists_sql("p")
    brand_filter = """
      p.deleted_at IS NULL
      AND (
        upper(trim(split_part(COALESCE(b.name,''), '|', 1))) = 'INSIZE'
        OR COALESCE(b.name,'') ILIKE '%INSIZE%'
        OR COALESCE(b.name,'') ILIKE '%اینسایز%'
      )
    """
    sellable = f"""
      {imaged} AND p.is_active IS TRUE AND p.is_available IS TRUE
      AND p.base_price IS NOT NULL AND p.base_price > 0
    """
    sql = f"""
    SELECT COUNT(*) FROM products p
    LEFT JOIN brands b ON b.id = p.brand_id
    WHERE {brand_filter} AND {sellable};
    """
    raw = _run_ssh_psql(sql, ssh_host=ssh_host)
    before = int((raw.splitlines() or ["0"])[-1] or 0)
    return {"sellable_before_insize_scope": before}


@dataclass
class SourceRow:
    source_row: int
    code: str
    description: str
    qty_ghods: str
    qty_tehran: str
    showroom_ghods: str
    showroom_tehran: str
    total_qty: str
    status_raw: str
    price_usd_raw: str
    price_usd_valid: bool
    price_usd: Decimal | None
    derived_price_toman: Decimal | None
    formula_qty_ok: bool
    formula_status_ok: bool


def _cell(row: dict[str, Any], *names: str) -> str:
    for n in names:
        if n in row and row[n] not in (None, ""):
            return str(row[n]).strip()
    for k, v in row.items():
        if str(k).startswith("__"):
            continue
        kn = str(k).strip()
        for n in names:
            if kn == n:
                return "" if v is None else str(v).strip()
    return ""


def parse_usd_price(raw: str) -> tuple[bool, Decimal | None]:
    s = (raw or "").strip()
    if not s or s.upper() in {"#N/A", "N/A", "NA"}:
        return False, None
    s = s.replace(",", "").replace("،", "")
    try:
        val = Decimal(s)
    except InvalidOperation:
        return False, None
    if val <= 0:
        return False, None
    return True, val


def normalize_status(raw: str) -> str:
    token = re.sub(r"\s+", " ", (raw or "").strip())
    if token in AVAILABLE_TOKENS:
        return "AVAILABLE"
    if token in UNAVAILABLE_TOKENS:
        return "UNAVAILABLE"
    return "UNKNOWN"


def load_source_rows(path: Path) -> list[SourceRow]:
    out: list[SourceRow] = []
    for raw in iter_xlsx_rows(path):
        code = normalize_sku(_cell(raw, "CODE", "code"))
        if not code:
            continue
        qg = _cell(raw, "موجودی قدس")
        qt = _cell(raw, "موجودی تهران")
        sg = _cell(raw, "شوروم قدس")
        st = _cell(raw, "شوروم تهران")
        total = _cell(raw, "موجودی کل")
        status_raw = _cell(raw, "وضعیت")
        price_raw = _cell(raw, "قیمت دلاری")
        valid, usd = parse_usd_price(price_raw)
        derived = usd * FX_TOMAN_PER_USD if usd is not None else None
        def _wh_qty(raw: str) -> int | None:
            q, inv = parse_quantity(raw)
            if inv:
                return None
            return 0 if q is None else q

        parts = [_wh_qty(x) for x in (qg, qt, sg, st)]
        sum_parts = sum(parts) if all(p is not None for p in parts) else None
        total_n, total_inv = parse_quantity(total)
        formula_qty_ok = (
            sum_parts is not None
            and total_n is not None
            and not total_inv
            and sum_parts == total_n
        )
        norm = normalize_status(status_raw)
        formula_status_ok = (
            total_n is not None
            and ((total_n > 5 and norm == "AVAILABLE") or (total_n <= 5 and norm == "UNAVAILABLE"))
        )
        out.append(
            SourceRow(
                source_row=int(raw.get("__source_row") or 0),
                code=code,
                description=_cell(raw, "DESCRIPTION"),
                qty_ghods=qg,
                qty_tehran=qt,
                showroom_ghods=sg,
                showroom_tehran=st,
                total_qty=total,
                status_raw=status_raw,
                price_usd_raw=price_raw,
                price_usd_valid=valid,
                price_usd=usd,
                derived_price_toman=derived,
                formula_qty_ok=formula_qty_ok,
                formula_status_ok=formula_status_ok,
            )
        )
    return out


def toman_decimal_str(val: Decimal | None) -> str:
    if val is None:
        return ""
    return str(val.quantize(Decimal("1")))


def parse_site_price(raw: str) -> Decimal | None:
    s = (raw or "").strip()
    if not s:
        return None
    try:
        return Decimal(s).quantize(Decimal("1"))
    except InvalidOperation:
        return None


def propose_commercial(sr: SourceRow) -> tuple[bool | None, Decimal | None, str]:
    norm = normalize_status(sr.status_raw)
    if norm == "UNAVAILABLE":
        return False, None, "CASE_B"
    if norm == "AVAILABLE":
        if sr.price_usd_valid and sr.price_usd is not None:
            return True, sr.derived_price_toman, "CASE_A"
        return True, None, "CASE_C"
    return None, None, "CASE_D_UNKNOWN_STATUS"


def classify_actions(
    cur_avail: bool,
    cur_price: Decimal | None,
    prop_avail: bool | None,
    prop_price: Decimal | None,
) -> tuple[str, str, str]:
    if prop_avail is None:
        return "HOLD_SOURCE_CONFLICT", "HOLD_SOURCE_CONFLICT", "HOLD"
    avail_action = "NO_CHANGE"
    if cur_avail and not prop_avail:
        avail_action = "SET_UNAVAILABLE"
    elif not cur_avail and prop_avail:
        avail_action = "SET_AVAILABLE"
    price_action = "NO_CHANGE"
    if prop_price is None and cur_price is not None:
        price_action = "CLEAR_PRICE"
    elif prop_price is not None and cur_price is None:
        price_action = "SET_PRICE"
    elif prop_price is not None and cur_price is not None and prop_price != cur_price:
        price_action = "SET_PRICE"
    if avail_action == "SET_AVAILABLE" and price_action == "SET_PRICE":
        combo = "SET_AVAILABLE_AND_PRICE"
    elif avail_action == "SET_UNAVAILABLE" and price_action == "CLEAR_PRICE":
        combo = "SET_UNAVAILABLE_AND_CLEAR_PRICE"
    elif avail_action == "SET_AVAILABLE" and price_action == "CLEAR_PRICE":
        combo = "SET_AVAILABLE_CLEAR_PRICE"
    else:
        combo = avail_action if price_action == "NO_CHANGE" else price_action
        if avail_action != "NO_CHANGE" and price_action != "NO_CHANGE" and combo not in {
            "SET_AVAILABLE_AND_PRICE",
            "SET_UNAVAILABLE_AND_CLEAR_PRICE",
            "SET_AVAILABLE_CLEAR_PRICE",
        }:
            combo = f"{avail_action}+{price_action}"
    return avail_action, price_action, combo


def price_compliance(
    prop_avail: bool | None,
    prop_price: Decimal | None,
    cur_price: Decimal | None,
    mapped: bool,
) -> str:
    if not mapped:
        if cur_price is not None:
            return "PRICED_BUT_NO_AUTHORITATIVE_SOURCE_MATCH"
        return "UNMATCHED"
    if prop_avail is True and prop_price is None:
        return "AVAILABLE_WITHOUT_VALID_PRICE"
    if prop_price is None:
        if cur_price is not None:
            return "PRICE_MUST_BE_CLEARED"
        return "PRICE_ALREADY_EXACT"
    if cur_price == prop_price:
        return "PRICE_ALREADY_EXACT"
    return "PRICE_NEEDS_UPDATE"


def availability_compliance(cur_avail: bool, prop_avail: bool | None) -> str:
    if prop_avail is None:
        return "HOLD"
    if cur_avail == prop_avail:
        return "AVAILABILITY_ALREADY_CORRECT"
    return "TRUE_TO_FALSE" if cur_avail and not prop_avail else "FALSE_TO_TRUE"


def is_sellable_state(
    prod: dict[str, str],
    *,
    is_available: bool,
    base_price: Decimal | None,
) -> bool:
    active = (prod.get("is_active") or "").lower() in {"t", "true", "1"}
    imaged = (prod.get("image_present") or "").lower() in {"t", "true", "1"}
    return (
        active
        and imaged
        and is_available
        and base_price is not None
        and base_price > 0
    )


def post_apply_state(
    prod: dict[str, str],
    dr: dict[str, str],
) -> tuple[bool, Decimal | None]:
    """Simulate post-APPLY state for one catalog row from dry-run plan."""
    cur_avail = (prod.get("is_available") or "").lower() in {"t", "true", "1"}
    cur_price = parse_site_price(prod.get("base_price") or "")
    if dr.get("eligibility") != "APPLY_ELIGIBLE":
        return cur_avail, cur_price
    prop_a = (dr.get("proposed_is_available") or "").strip().lower()
    if prop_a in {"true", "t", "1"}:
        avail = True
    elif prop_a in {"false", "f", "0"}:
        avail = False
    else:
        avail = cur_avail
    prop_p_raw = (dr.get("proposed_base_price") or "").strip()
    price = parse_site_price(prop_p_raw) if prop_p_raw else None
    return avail, price


def sellability_projection(catalog: list[dict[str, str]], dry_rows: list[dict[str, str]]) -> dict:
    by_pid = {r["product_id"]: r for r in dry_rows}
    before = sum(
        1
        for p in catalog
        if is_sellable_state(
            p,
            is_available=(p.get("is_available") or "").lower() in {"t", "true", "1"},
            base_price=parse_site_price(p.get("base_price") or ""),
        )
    )
    gain = loss = 0
    after = 0
    for p in catalog:
        dr = by_pid[p["product_id"]]
        pre = is_sellable_state(
            p,
            is_available=(p.get("is_available") or "").lower() in {"t", "true", "1"},
            base_price=parse_site_price(p.get("base_price") or ""),
        )
        avail, price = post_apply_state(p, dr)
        post = is_sellable_state(p, is_available=avail, base_price=price)
        if post and not pre:
            gain += 1
        if pre and not post:
            loss += 1
        if post:
            after += 1
    return {
        "SELLABLE_BEFORE": before,
        "SELLABLE_GAIN": gain,
        "SELLABLE_LOSS": loss,
        "SELLABLE_AFTER_PROJECTED": after,
    }


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
        lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  ./{p.name}")
    (out_dir / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ssh-host", default="karzar-vps")
    p.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "audit" / "insize-commercial-reconcile-258-2026-10-13",
    )
    args = p.parse_args(argv)

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    snapshot_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    if not INSIZE_FINAL_XLSX.is_file():
        raise SystemExit(f"missing workbook: {INSIZE_FINAL_XLSX}")
    sha = file_sha256(INSIZE_FINAL_XLSX)
    if sha != INSIZE_FINAL_SHA:
        raise SystemExit(f"sha_mismatch got {sha}")

    k6 = read_xlsx_cell(INSIZE_FINAL_XLSX, "K6")
    k6_num = parse_quantity(str(k6) if k6 is not None else "")[0]
    if k6_num != 3_000_000:
        raise SystemExit(f"K6_expected_3000000_rial got {k6}")

    ro = _read_only_session_proof(args.ssh_host)
    identity = {
        "snapshot_utc": snapshot_utc,
        "origin_main": _git_origin_main(),
        "branch": "audit/catalog-258-insize-final-commercial-source",
        "transaction_read_only": ro.get("transaction_read_only"),
        "mutation": {
            "PRODUCTION_MUTATION": "NO",
            "DATABASE_MUTATION": "NO",
            "PRICE_APPLY": "NO",
            "AVAILABILITY_APPLY": "NO",
            "HESABFA_MUTATION": "NO",
            "DEPLOYMENT": "NO",
        },
        "read_only_proof": ro,
    }
    json.dump(identity, (out_dir / "PRODUCTION_IDENTITY.json").open("w"), indent=2)
    json.dump(
        {
            "source_id": "insize.distributor.final.300k_toman.8324b2c1",
            "sha256": INSIZE_FINAL_SHA,
            "path": str(INSIZE_FINAL_XLSX),
            "original_filename": "موجودی توزیع کننده 11 شهریور - دلار 300 هزار تومان - نهایی (1).xlsx",
            "supersedes_sha256": [SUPERSEDED_SHA_BEB549],
            "source_date": None,
            "source_date_note": "Exact calendar date unknown — not inferred from filename/metadata/mtime",
            "freshness": "CURRENT_ENOUGH",
            "freshness_basis": "OWNER_CONFIRMED_RECENCY",
            "owner_recency_statement": (
                "Owner confirms final file is approximately one week old and is the current commercial source"
            ),
            "fx_cell_k6_rial_per_usd": str(k6_num),
            "fx_toman_per_usd": str(FX_TOMAN_PER_USD),
            "price_formula": "base_price_toman = source_USD × 300000 (Decimal, no +20%, no tax)",
            "inspected_at": snapshot_utc,
        },
        (out_dir / "SOURCE_MANIFEST.json").open("w"),
        indent=2,
    )

    source_rows = load_source_rows(INSIZE_FINAL_XLSX)
    by_code: dict[str, list[SourceRow]] = {}
    for sr in source_rows:
        by_code.setdefault(sr.code, []).append(sr)
    duplicate_codes = {c for c, rows in by_code.items() if len(rows) > 1}

    src_stats = Counter()
    for sr in source_rows:
        norm = normalize_status(sr.status_raw)
        src_stats["rows"] += 1
        if norm == "AVAILABLE":
            src_stats["موجود"] += 1
            if sr.price_usd_valid:
                src_stats["موجود_valid_price"] += 1
            else:
                src_stats["موجود_invalid_price"] += 1
        elif norm == "UNAVAILABLE":
            src_stats["نا موجود"] += 1
            if sr.price_usd_valid:
                src_stats["نا موجود_valid_price"] += 1
            else:
                src_stats["نا موجود_invalid_price"] += 1
    src_stats["duplicate_codes"] = len(duplicate_codes)
    formula_ok = sum(1 for sr in source_rows if sr.formula_qty_ok and sr.formula_status_ok)
    json.dump(
        {
            **dict(src_stats),
            "formula_consistency_rows_ok": formula_ok,
            "formula_consistency_pct": round(100.0 * formula_ok / max(len(source_rows), 1), 2),
            "known_duplicate_codes": sorted(duplicate_codes)[:50],
        },
        (out_dir / "SOURCE_PARSE_SUMMARY.json").open("w"),
        indent=2,
    )

    catalog = export_live_insize(args.ssh_host, snapshot_utc)
    write_csv(
        out_dir / "CURRENT_INSIZE_CATALOG.csv",
        list(catalog[0].keys()) if catalog else ["product_id"],
        catalog,
    )

    catalog_by_sku: dict[str, list[dict[str, str]]] = {}
    for r in catalog:
        catalog_by_sku.setdefault(normalize_sku(r.get("sku") or ""), []).append(r)

    mapping_rows: list[dict] = []
    dry_rows: list[dict] = []
    unmatched_rows: list[dict] = []
    merch_conflicts: list[dict] = []

    price_classes = Counter()
    avail_classes = Counter()
    action_counts = Counter()

    for prod in catalog:
        pid = prod["product_id"]
        sku_n = normalize_sku(prod.get("sku") or "")
        mfg_n = normalize_sku(prod.get("manufacturer_code") or "")
        identity_method = "NOT_FOUND"
        map_class = "NOT_FOUND"
        hold_reason = ""
        source_code = ""
        sr: SourceRow | None = None

        candidates: list[tuple[str, str]] = []
        if mfg_n:
            candidates.append(("EXACT", mfg_n))
        xa_code = f"{sku_n}A" if sku_n else ""
        if xa_code and xa_code in by_code and xa_code not in duplicate_codes:
            id_res = match_source_code_to_catalog_skus(
                brand="INSIZE",
                source_sku=xa_code,
                catalog_by_sku=catalog_by_sku,
            )
            if (
                id_res.outcome == "EXACT_MATCH"
                and id_res.detail == INSIZE_TRAILING_A_DETAIL
                and id_res.catalog_sku == sku_n
            ):
                candidates.append(("GOVERNED_ALIAS", xa_code))
        if sku_n and sku_n != mfg_n:
            skip_exact_sku = any(c[0] == "GOVERNED_ALIAS" and c[1] == f"{sku_n}A" for c in candidates)
            if not skip_exact_sku:
                candidates.append(("EXACT", sku_n))

        chosen: tuple[str, str] | None = None
        for method, code in candidates:
            if code in duplicate_codes:
                map_class = "SOURCE_DUPLICATE"
                identity_method = method
                source_code = code
                hold_reason = f"duplicate_source_code:{code}"
                break
            rows = by_code.get(code, [])
            if len(rows) > 1:
                map_class = "SOURCE_DUPLICATE"
                identity_method = method
                source_code = code
                hold_reason = f"duplicate_source_code:{code}"
                break
            if len(rows) == 1:
                if chosen is not None and chosen[1] != code:
                    map_class = "SOURCE_CONFLICT"
                    hold_reason = f"multiple_identity_paths:{chosen[1]}_vs_{code}"
                    break
                chosen = (method, code)
                sr = rows[0]
                source_code = code
                identity_method = method
                map_class = "EXACT" if method == "EXACT" else "GOVERNED_ALIAS"

        if map_class in {"SOURCE_DUPLICATE", "SOURCE_CONFLICT"}:
            sr = None
        elif chosen is None:
            map_class = "NOT_FOUND"

        cur_avail = (prod.get("is_available") or "").lower() in {"t", "true", "1"}
        cur_price = parse_site_price(prod.get("base_price") or "")
        prop_avail: bool | None = None
        prop_price: Decimal | None = None
        owner_case = ""
        if sr is not None and map_class in {"EXACT", "GOVERNED_ALIAS"}:
            prop_avail, prop_price, owner_case = propose_commercial(sr)
            if prop_avail is None:
                map_class = "SOURCE_CONFLICT"
                hold_reason = "unknown_source_status"

        mapped_ok = sr is not None and map_class in {"EXACT", "GOVERNED_ALIAS"}

        if not mapped_ok:
            prop_avail = None
            prop_price = None
            avail_action = "NO_CHANGE"
            price_action = "CLEAR_PRICE" if cur_price is not None else "NO_CHANGE"
            combo = "HOLD_CLEAR_PRICE" if price_action == "CLEAR_PRICE" else "HOLD_IDENTITY"
            eligibility = "APPLY_ELIGIBLE" if price_action == "CLEAR_PRICE" else "NO_CHANGE"
            if not hold_reason:
                hold_reason = map_class
            pclass = "PRICE_MUST_BE_CLEARED" if cur_price is not None else "UNMATCHED"
            aclass = "HOLD"
        else:
            avail_action, price_action, combo = classify_actions(
                cur_avail, cur_price, prop_avail, prop_price
            )
            pclass = price_compliance(prop_avail, prop_price, cur_price, mapped_ok)
            aclass = availability_compliance(cur_avail, prop_avail)
            eligibility = (
                "APPLY_ELIGIBLE" if combo not in {"NO_CHANGE", "HOLD_IDENTITY"} else "NO_CHANGE"
            )

        price_classes[pclass] += 1
        avail_classes[aclass] += 1
        action_counts[avail_action] += 1
        action_counts[price_action] += 1
        action_counts[f"combined:{combo}"] += 1

        orig = parse_site_price(prod.get("original_price") or "")
        if prop_avail and prop_price is not None and orig is not None and orig != prop_price:
            merch_conflicts.append(
                {
                    "product_id": pid,
                    "sku": prod.get("sku"),
                    "base_price": toman_decimal_str(cur_price),
                    "original_price": toman_decimal_str(orig),
                    "proposed_base_price": toman_decimal_str(prop_price),
                    "note": "original_price != authoritative base_price",
                }
            )

        mapping_rows.append(
            {
                "product_id": pid,
                "sku": prod.get("sku"),
                "manufacturer_code": prod.get("manufacturer_code"),
                "map_class": map_class,
                "identity_method": identity_method,
                "source_code": source_code,
                "owner_case": owner_case,
            }
        )

        if map_class in {"NOT_FOUND", "AMBIGUOUS", "SOURCE_DUPLICATE", "SOURCE_CONFLICT"}:
            unmatched_rows.append(
                {
                    "product_id": pid,
                    "sku": prod.get("sku"),
                    "manufacturer_code": prod.get("manufacturer_code"),
                    "map_class": map_class,
                    "hold_reason": hold_reason or map_class,
                    "current_base_price": prod.get("base_price"),
                    "current_is_available": prod.get("is_available"),
                }
            )

        dry_rows.append(
            {
                "product_id": pid,
                "sku": prod.get("sku"),
                "manufacturer_code": prod.get("manufacturer_code"),
                "source_code": source_code,
                "identity_method": identity_method,
                "source_status": sr.status_raw if sr else "",
                "source_total_quantity": sr.total_qty if sr else "",
                "source_price_usd": sr.price_usd_raw if sr else "",
                "source_price_toman": toman_decimal_str(prop_price) if prop_price else "",
                "current_is_available": prod.get("is_available"),
                "proposed_is_available": (
                    prod.get("is_available")
                    if not mapped_ok
                    else (
                        "true"
                        if prop_avail is True
                        else ("false" if prop_avail is False else "")
                    )
                ),
                "current_base_price": prod.get("base_price"),
                "proposed_base_price": (
                    ""
                    if prop_price is None
                    else toman_decimal_str(prop_price)
                ),
                "availability_action": avail_action,
                "price_action": price_action,
                "combined_action": combo,
                "expected_current_hash": state_hash(prod),
                "eligibility": eligibility,
                "hold_reason": hold_reason,
                "owner_case": owner_case,
                "map_class": map_class,
                "price_compliance": pclass,
                "availability_compliance": aclass,
            }
        )

    plan_projection = sellability_projection(catalog, dry_rows)
    json.dump(
        {
            "ACTUAL_APPLY_PLAN_PROJECTION": plan_projection,
            "OWNER_POLICY_FULL_PROJECTION": plan_projection,
            "note": "INSIZE-scoped sellable (active, imaged, available, base_price>0); "
            "simulated from APPLY_ELIGIBLE mutations only",
        },
        (out_dir / "SELLABILITY_PROJECTION.json").open("w"),
        indent=2,
    )

    apply_eligible = sum(1 for r in dry_rows if r["eligibility"] == "APPLY_ELIGIBLE")
    hold_total = sum(1 for r in dry_rows if r.get("combined_action", "").startswith("HOLD"))
    hold_priced_before = sum(
        1
        for r in dry_rows
        if r.get("combined_action", "").startswith("HOLD")
        and parse_site_price(r.get("current_base_price") or "")
    )
    hold_price_clears = sum(1 for r in dry_rows if r.get("combined_action") == "HOLD_CLEAR_PRICE")
    hold_priced_after = sum(
        1
        for r in dry_rows
        if r.get("combined_action", "").startswith("HOLD")
        and parse_site_price(r.get("proposed_base_price") or "")
    )
    dry_by_pid = {r["product_id"]: r for r in dry_rows}
    priced_without_authority_after = 0
    for p in catalog:
        dr = dry_by_pid[p["product_id"]]
        _, post_price = post_apply_state(p, dr)
        if post_price is None:
            continue
        if dr.get("owner_case") != "CASE_A":
            priced_without_authority_after += 1

    map_counts = Counter(m["map_class"] for m in mapping_rows)
    json.dump(
        {
            "live_insize_products": len(catalog),
            "source_rows": len(source_rows),
            "identity_mapping": dict(map_counts),
            "mapped_exact_or_alias": sum(
                1 for m in mapping_rows if m["map_class"] in {"EXACT", "GOVERNED_ALIAS"}
            ),
            "unmatched_or_hold": len(unmatched_rows),
            "apply_eligible_rows": apply_eligible,
            "mutation_actions": {k: v for k, v in action_counts.items()},
            "hold_price_policy": {
                "hold_total": hold_total,
                "priced_hold_before": hold_priced_before,
                "hold_price_clears_added": hold_price_clears,
                "priced_hold_after_proposed": hold_priced_after,
            },
            "priced_insize_without_authoritative_source_after_plan": priced_without_authority_after,
            "price_compliance": dict(price_classes),
            "availability_compliance": dict(avail_classes),
            "pr488_superseded_note": (
                f"PR #488 Wave A/D evidence used SHA {SUPERSEDED_SHA_BEB549[:8]}… — "
                f"superseded by Owner final SHA {INSIZE_FINAL_SHA[:8]}…"
            ),
        },
        (out_dir / "COMMERCIAL_DELTA.json").open("w"),
        indent=2,
    )

    write_csv(
        out_dir / "INSIZE_SOURCE_MAPPING.csv",
        ["product_id", "sku", "manufacturer_code", "map_class", "identity_method", "source_code", "owner_case"],
        mapping_rows,
    )
    plan_fields = list(dry_rows[0].keys()) if dry_rows else ["product_id"]
    write_csv(out_dir / "INSIZE_COMMERCIAL_RECONCILE_PLAN.csv", plan_fields, dry_rows)
    rollback_rows = [
        {
            "product_id": dr["product_id"],
            "sku": dr["sku"],
            "pre_is_available": dr["current_is_available"],
            "pre_base_price": dr["current_base_price"],
            "proposed_is_available": dr["proposed_is_available"],
            "proposed_base_price": dr["proposed_base_price"],
            "expected_current_hash": dr["expected_current_hash"],
        }
        for dr in dry_rows
        if dr.get("eligibility") == "APPLY_ELIGIBLE"
    ]
    write_csv(
        out_dir / "INSIZE_COMMERCIAL_ROLLBACK_MANIFEST.csv",
        [
            "product_id",
            "sku",
            "pre_is_available",
            "pre_base_price",
            "proposed_is_available",
            "proposed_base_price",
            "expected_current_hash",
        ],
        rollback_rows,
    )
    write_csv(
        out_dir / "INSIZE_UNMATCHED_COMMERCIAL_REVIEW.csv",
        list(unmatched_rows[0].keys()) if unmatched_rows else ["product_id"],
        unmatched_rows,
    )
    write_csv(
        out_dir / "INSIZE_MERCHANDISING_PRICE_CONFLICTS.csv",
        list(merch_conflicts[0].keys()) if merch_conflicts else ["product_id"],
        merch_conflicts,
    )

    (out_dir / "INSIZE_COMMERCIAL_APPLY_PLAN.md").write_text(
        """# INSIZE commercial APPLY plan (NOT AUTHORIZED)

- Source SHA256: `{INSIZE_FINAL_SHA}`
- Plan CSV: `INSIZE_COMMERCIAL_RECONCILE_PLAN.csv`
- Rollback: `INSIZE_COMMERCIAL_ROLLBACK_MANIFEST.csv` (explicit pre/post values)
- CLI: `scripts/apply_insize_commercial_reconcile_258.py` (dry-run default)
- Future APPLY journal must record exact before/after, batch id, timestamp, success/failure
- **No `--apply` in this PR**
""",
        encoding="utf-8",
    )
    (out_dir / "INSIZE_COMMERCIAL_ROLLBACK_PLAN.md").write_text(
        """# INSIZE commercial rollback plan (evidence only)

Use `INSIZE_COMMERCIAL_ROLLBACK_MANIFEST.csv` for reversible pre-apply values
(`pre_is_available`, `pre_base_price`). Hashes are stale guards only — not rollback data.

Post-APPLY journal must capture exact before/after per row. Rollback not executed in this PR.
""",
        encoding="utf-8",
    )
    (out_dir / "README.md").write_text(
        """# INSIZE commercial source reconciliation (#258, #391)

**Status:** evidence only — **NO APPLY**

- Owner source SHA: `8324b2c1…` (300k Toman/USD, `K6=3,000,000` RIAL)
- Freshness: `CURRENT_ENOUGH` (`OWNER_CONFIRMED_RECENCY`)
- Supersedes PR #488 workbook `beb54910…`

See `INSIZE_COMMERCIAL_RECONCILE_PLAN.csv`, `COMMERCIAL_DELTA.json`, `SELLABILITY_PROJECTION.json`.
""",
        encoding="utf-8",
    )

    if formula_ok != len(source_rows):
        raise SystemExit(
            f"formula_consistency_failed:{formula_ok}/{len(source_rows)}"
        )

    sha256sums(out_dir)
    summary = {
        "catalog": len(catalog),
        "source_rows": len(source_rows),
        "formula_ok": formula_ok,
        "apply_eligible": apply_eligible,
        "hold_price_clears": hold_price_clears,
        "priced_without_authority_after": priced_without_authority_after,
        "sellable_projection": plan_projection,
        "price_compliance": dict(price_classes),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
