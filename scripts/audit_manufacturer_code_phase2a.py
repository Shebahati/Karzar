#!/usr/bin/env python3
"""Phase 2A read-only manufacturer identity census + backfill readiness.

Never mutates catalog/DB. --apply is rejected (exit 2).

Modes:
  --database-url   Full non-deleted product census from local/isolated DB
  --snapshot-dir   PARTIAL census from Phase 0/1 public snapshot JSON
  (default)        Prefer DB env if reachable, else snapshot PARTIAL
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.domain.product_naming import extract_manufacturer_code_candidates  # noqa: E402

DEFAULT_OUT = ROOT / "audit" / "product-manufacturer-code-phase2a"
DEFAULT_SNAPSHOT = ROOT / "audit" / "product-naming-v1" / "snapshots"

_CODE_LABEL_RE = re.compile(r"(?:^|[\s،,])کد\s+", re.UNICODE)
_MODEL_LABEL_RE = re.compile(r"(?:^|[\s،,])مدل\s+", re.UNICODE)
_REVERSED_HINT = re.compile(r"^(\d{2,4})-(\d{2,4})(?:-(\d+))?$")


def _reject_apply(argv: list[str]) -> None:
    if any(a == "--apply" or a.startswith("--apply=") for a in argv):
        print("ERROR: --apply is rejected. This audit is READ-ONLY only.", file=sys.stderr)
        raise SystemExit(2)


def _norm_brand(name: str | None) -> str:
    if not name:
        return ""
    return name.split("|", 1)[0].strip().upper()


def _title_token(name: str | None) -> str | None:
    if not name:
        return None
    for rx in (_CODE_LABEL_RE, _MODEL_LABEL_RE):
        m = rx.search(name)
        if not m:
            continue
        tail = name[m.end() :].strip()
        token = re.split(r"[،,]", tail, maxsplit=1)[0].strip()
        token = re.split(r"\s+برای\s+", token, maxsplit=1)[0].strip()
        token = re.sub(r"\s{2,}", " ", token)
        if token:
            return token
    return None


def _specs_get(specs: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        val = specs.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def classify_identity(row: dict[str, Any]) -> dict[str, Any]:
    """Classify candidate manufacturer identity — never writes canonical field."""
    specs = row.get("specifications") or {}
    if not isinstance(specs, dict):
        specs = {}
    brand = _norm_brand(row.get("brand_name"))
    sku = (row.get("sku") or "").strip()
    name = row.get("name") or ""
    canonical = row.get("manufacturer_code")
    canonical = canonical.strip() if isinstance(canonical, str) and canonical.strip() else None

    specs_mc = _specs_get(specs, "manufacturer_code")
    specs_model = _specs_get(specs, "model", "oem_model", "official_model")
    specs_pn = _specs_get(specs, "part_number")
    title = _title_token(name)
    source_id = _specs_get(specs, "source_product_id", "source_identity_key", "distributor_code")

    candidates = extract_manufacturer_code_candidates(name=name, sku=sku, specs=specs)

    # Authority / state heuristics (audit only)
    identity_state = "MISSING"
    candidate_code = None
    candidate_source = None
    authority_tier = 7
    candidate_confidence = "none"
    conflict_reason = ""
    action = "HOLD_MISSING"

    # Strong structured ZCC-style evidence in live specs.model
    if specs_mc:
        identity_state = "SOURCE_STRUCTURED_CANDIDATE"
        candidate_code = specs_mc
        candidate_source = "specs.manufacturer_code"
        authority_tier = 4
        candidate_confidence = "medium"
        action = "MANUAL_REVIEW"
    elif specs_model and brand in {"ZCC.CT", "ZCC", "SAN OU", "STC"}:
        identity_state = "SOURCE_STRUCTURED_CANDIDATE"
        candidate_code = specs_model
        candidate_source = "specs.model"
        authority_tier = 4
        candidate_confidence = "medium"
        # ZCC parse uses manufacturer_code=model; still not auto-canonical
        action = "MANUAL_REVIEW"
    elif specs_model and brand in {"INSIZE"}:
        identity_state = "SPECS_MODEL_CANDIDATE"
        candidate_code = specs_model
        candidate_source = "specs.model"
        authority_tier = 4
        candidate_confidence = "medium"
        action = "MANUAL_REVIEW"
    elif specs_pn:
        identity_state = "SOURCE_STRUCTURED_CANDIDATE"
        candidate_code = specs_pn
        candidate_source = "specs.part_number"
        authority_tier = 4
        candidate_confidence = "low"
        action = "HOLD_WEAK_EVIDENCE"
    elif title:
        identity_state = "TITLE_CANDIDATE"
        candidate_code = title
        candidate_source = "name_label"
        authority_tier = 6
        candidate_confidence = "low"
        action = "HOLD_WEAK_EVIDENCE"
        # Reversed Order-No class (Mitutoyo-style): both sides must be pure NNN-NNN codes.
        if sku and _looks_reversed(sku, title):
            identity_state = "CONFLICT"
            conflict_reason = "reversed_title_vs_sku"
            action = "HOLD_IDENTITY_CONFLICT"
    elif sku:
        identity_state = "SKU_ONLY_CANDIDATE"
        candidate_code = sku
        candidate_source = "sku"
        authority_tier = 7
        candidate_confidence = "low"
        action = "HOLD_WEAK_EVIDENCE"
    else:
        identity_state = "MISSING"
        action = "HOLD_MISSING"

    if identity_state != "CONFLICT":
        # Conflict only when two structured (non-title, non-sku) codes disagree.
        structured = {
            _normalize_code(c)
            for c, e in candidates
            if e.startswith("specs.") and _normalize_code(c)
        }
        if len(structured) > 1:
            identity_state = "CONFLICT"
            conflict_reason = conflict_reason or "multiple_structured_candidates"
            action = "HOLD_IDENTITY_CONFLICT"

    if not brand and candidate_code:
        action = "HOLD_BRAND_AMBIGUOUS"

    # INSIZE official-looking SKU+title agreement → research candidate, not BACKFILL_EXACT
    # BACKFILL_EXACT reserved for Tier 1–3 with OEM catalogue proof (not auto here).
    if (
        brand == "INSIZE"
        and sku
        and title
        and _normalize_code(sku) == _normalize_code(title)
        and action in {"HOLD_WEAK_EVIDENCE", "MANUAL_REVIEW"}
    ):
        action = "MANUAL_REVIEW"
        candidate_confidence = "medium"
        # Still not BACKFILL_EXACT without OEM catalogue linkage in this phase.

    if canonical:
        # Should be rare in Phase 2A (migration leaves NULL). Treat as already set.
        identity_state = "KARZAR_VERIFIED_STRUCTURED"
        candidate_code = canonical
        candidate_source = "products.manufacturer_code"
        authority_tier = 3
        candidate_confidence = "high"
        action = "MANUAL_REVIEW"

    return {
        "candidate_code": candidate_code or "",
        "candidate_source": candidate_source or "",
        "authority_tier": authority_tier,
        "candidate_confidence": candidate_confidence,
        "identity_state": identity_state,
        "conflict_reason": conflict_reason,
        "recommended_phase2c_action": action,
        "source_id_evidence": source_id or "",
        "specs_model": specs_model or "",
        "title_token": title or "",
    }


def _normalize_code(code: str) -> str:
    return re.sub(r"\s+", "", code or "").upper()


def _looks_reversed(a: str, b: str) -> bool:
    """True only for pure numeric Order-No swaps like 118-102 vs 102-118."""
    a_s, b_s = a.strip(), b.strip()
    # Title tokens often include brand/prose — require exact OEM-like tokens only.
    if " " in a_s or " " in b_s:
        return False
    ma, mb = _REVERSED_HINT.match(a_s), _REVERSED_HINT.match(b_s)
    if not ma or not mb:
        return False
    if _normalize_code(a_s) == _normalize_code(b_s):
        return False
    return ma.group(1) == mb.group(2) and ma.group(2) == mb.group(1)


def load_snapshot_rows(snapshot_dir: Path) -> list[dict[str, Any]]:
    details_path = snapshot_dir / "products_details.json"
    if not details_path.exists():
        raise FileNotFoundError(details_path)
    raw = json.loads(details_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "items" in raw:
        items = raw["items"]
    elif isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        # Phase 0/1 snapshot shape: { "<product_id>": {product detail}, ... }
        items = list(raw.values())
    else:
        raise ValueError("unexpected products_details.json shape")

    rows: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        brand = item.get("brand") or {}
        rows.append(
            {
                "product_id": item.get("id"),
                "sku": item.get("sku"),
                "name": item.get("name"),
                "slug": item.get("slug"),
                "brand_id": item.get("brand_id") or brand.get("id"),
                "brand_name": brand.get("name") if isinstance(brand, dict) else None,
                "category_id": item.get("category_id"),
                "product_type_id": item.get("product_type_id"),
                "manufacturer_code": item.get("manufacturer_code"),
                "is_active": item.get("is_active"),
                "is_available": item.get("is_available", item.get("availability")),
                "deleted_at": item.get("deleted_at"),
                "specifications": item.get("specifications") or {},
            }
        )
    return rows


def load_db_rows(database_url: str) -> list[dict[str, Any]]:
    """Sync read-only census via SQLAlchemy. Caller must use isolated/local DB."""
    from sqlalchemy import create_engine, text

    # Force sync driver
    url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    engine = create_engine(url)
    sql = text(
        """
        SELECT p.id AS product_id, p.sku, p.name, p.slug, p.brand_id,
               b.name AS brand_name, p.category_id, p.product_type_id,
               p.manufacturer_code, p.is_active, p.is_available, p.deleted_at,
               p.specifications
        FROM products p
        LEFT JOIN brands b ON b.id = p.brand_id
        WHERE p.deleted_at IS NULL
        ORDER BY p.id
        """
    )
    rows: list[dict[str, Any]] = []
    with engine.connect() as conn:
        # Prefer read-only transaction when supported
        try:
            conn.execute(text("SET TRANSACTION READ ONLY"))
        except Exception:
            pass
        for r in conn.execute(sql):
            m = r._mapping
            specs = m["specifications"] or {}
            if isinstance(specs, str):
                specs = json.loads(specs)
            rows.append(
                {
                    "product_id": m["product_id"],
                    "sku": m["sku"],
                    "name": m["name"],
                    "slug": m["slug"],
                    "brand_id": m["brand_id"],
                    "brand_name": m["brand_name"],
                    "category_id": m["category_id"],
                    "product_type_id": m["product_type_id"],
                    "manufacturer_code": m["manufacturer_code"],
                    "is_active": m["is_active"],
                    "is_available": m["is_available"],
                    "deleted_at": m["deleted_at"],
                    "specifications": specs,
                }
            )
    return rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    _reject_apply(argv)

    parser = argparse.ArgumentParser(description="Phase 2A manufacturer identity audit (read-only)")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--snapshot-dir", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--database-url", type=str, default=os.environ.get("DATABASE_URL", ""))
    parser.add_argument("--force-snapshot", action="store_true")
    parser.add_argument("--apply", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.apply:
        print("ERROR: --apply is rejected. This audit is READ-ONLY only.", file=sys.stderr)
        return 2

    census_status = "PARTIAL"
    source = "snapshot"
    rows: list[dict[str, Any]] = []

    if args.database_url and not args.force_snapshot:
        try:
            rows = load_db_rows(args.database_url)
            census_status = "FULL"
            source = "database"
        except Exception as exc:
            print(f"WARN: DB census failed ({exc}); falling back to snapshot", file=sys.stderr)
            rows = load_snapshot_rows(args.snapshot_dir)
            census_status = "PARTIAL"
            source = "snapshot_fallback"
    else:
        rows = load_snapshot_rows(args.snapshot_dir)
        census_status = "PARTIAL"
        source = "snapshot"

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    census_fields = [
        "product_id",
        "sku",
        "name",
        "slug",
        "brand_id",
        "brand_name",
        "category_id",
        "product_type_id",
        "manufacturer_code",
        "is_active",
        "is_available",
        "deleted_at",
    ]
    write_csv(out / "FULL_PRODUCT_IDENTITY_CENSUS.csv", census_fields, rows)

    classified: list[dict[str, Any]] = []
    for row in rows:
        meta = classify_identity(row)
        classified.append(
            {
                "product_id": row.get("product_id"),
                "sku": row.get("sku"),
                "brand_id": row.get("brand_id"),
                "brand_name": row.get("brand_name"),
                "current_name": row.get("name"),
                "product_type_id": row.get("product_type_id"),
                "current_manufacturer_code": row.get("manufacturer_code") or "",
                **meta,
            }
        )

    backfill_fields = [
        "product_id",
        "sku",
        "brand_id",
        "brand_name",
        "current_name",
        "product_type_id",
        "current_manufacturer_code",
        "candidate_code",
        "candidate_source",
        "authority_tier",
        "candidate_confidence",
        "identity_state",
        "conflict_reason",
        "recommended_phase2c_action",
    ]
    write_csv(out / "MANUFACTURER_CODE_BACKFILL_CANDIDATES.csv", backfill_fields, classified)

    # Collisions: same brand + same candidate_code → multiple products
    collision_map: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in classified:
        code = (row.get("candidate_code") or "").strip()
        brand = _norm_brand(row.get("brand_name"))
        if not code or not brand:
            continue
        collision_map[(brand, _normalize_code(code))].append(row)

    collision_rows: list[dict[str, Any]] = []
    for (brand, code_key), group in sorted(collision_map.items()):
        if len(group) < 2:
            continue
        collision_rows.append(
            {
                "brand": brand,
                "candidate_code_normalized": code_key,
                "candidate_code_sample": group[0].get("candidate_code"),
                "product_ids": "|".join(str(g["product_id"]) for g in group),
                "skus": "|".join(str(g.get("sku") or "") for g in group),
                "count": len(group),
                "notes": "brand+candidate collision; no auto-winner",
            }
        )

    # Explicit ASTPOWER TU-DR230 check
    ast_hits = [
        r
        for r in classified
        if _norm_brand(r.get("brand_name")) == "ASTPOWER"
        and "TU-DR230" in _normalize_code(r.get("candidate_code") or r.get("sku") or "")
    ]
    if ast_hits and not any(
        r["brand"] == "ASTPOWER" and "TU-DR230" in r["candidate_code_normalized"]
        for r in collision_rows
    ):
        collision_rows.append(
            {
                "brand": "ASTPOWER",
                "candidate_code_normalized": "TU-DR230",
                "candidate_code_sample": "TU-DR230",
                "product_ids": "|".join(str(g["product_id"]) for g in ast_hits),
                "skus": "|".join(str(g.get("sku") or "") for g in ast_hits),
                "count": len(ast_hits),
                "notes": "historical Phase 0/1 collision class",
            }
        )

    # Reversed-code conflicts
    reversed_rows = [r for r in classified if r.get("conflict_reason") == "reversed_title_vs_sku"]
    for r in reversed_rows:
        collision_rows.append(
            {
                "brand": _norm_brand(r.get("brand_name")),
                "candidate_code_normalized": _normalize_code(r.get("candidate_code") or ""),
                "candidate_code_sample": r.get("candidate_code"),
                "product_ids": str(r.get("product_id")),
                "skus": str(r.get("sku") or ""),
                "count": 1,
                "notes": "reversed_title_vs_sku",
            }
        )

    write_csv(
        out / "MANUFACTURER_CODE_COLLISIONS.csv",
        [
            "brand",
            "candidate_code_normalized",
            "candidate_code_sample",
            "product_ids",
            "skus",
            "count",
            "notes",
        ],
        collision_rows,
    )

    state_counts = Counter(r["identity_state"] for r in classified)
    action_counts = Counter(r["recommended_phase2c_action"] for r in classified)
    with_pt = sum(1 for r in rows if r.get("product_type_id") not in (None, "", 0))
    active = sum(1 for r in rows if r.get("is_active") in (True, 1, "1", "true", "True"))
    inactive = len(rows) - active
    canonical_populated = sum(
        1 for r in rows if isinstance(r.get("manufacturer_code"), str) and r["manufacturer_code"].strip()
    )

    summary = {
        "phase": "2A",
        "generated_at": datetime.now(UTC).isoformat(),
        "census_status": census_status,
        "source": source,
        "total_non_deleted": len(rows),
        "active": active,
        "inactive": inactive,
        "with_product_type": with_pt,
        "without_product_type": len(rows) - with_pt,
        "canonical_manufacturer_code_populated": canonical_populated,
        "identity_state_counts": dict(state_counts),
        "backfill_action_counts": dict(action_counts),
        "collision_groups": len([r for r in collision_rows if int(r["count"]) >= 2]),
        "astpower_tu_dr230_products": len(ast_hits),
        "reversed_code_conflicts": len(reversed_rows),
        "notes": [
            "BACKFILL_EXACT count is intentionally 0 in Phase 2A without OEM catalogue linkage.",
            "Candidates must not populate products.manufacturer_code.",
            "No production mutation performed.",
        ],
    }
    (out / "PHASE2A_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(json.dumps({"ok": True, **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
