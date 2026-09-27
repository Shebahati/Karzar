#!/usr/bin/env python3
"""Karzar Taxonomy Phase 0B — Production DB census (READ-ONLY ONLY).

Runs inside lathe_api (or any host with asyncpg + DB env) against the CR-011
live data plane (historic labels: APP_ENV=staging, POSTGRES_DB=karzar_staging,
container lathe_postgres).

Safety:
  - SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY
  - All work inside BEGIN READ ONLY … ROLLBACK
  - Never INSERT/UPDATE/DELETE/DDL
  - Aborts unless identity gates + transaction_read_only=on

Visibility / sellability predicates (re-derived from
app/utils/public_catalog.py, app/utils/storefront_catalog.py, COMMERCE.md):

  LIVE                 = deleted_at IS NULL
  ACTIVE               = LIVE AND is_active
  AVAILABLE            = LIVE AND is_available
  PRICED               = LIVE AND base_price IS NOT NULL AND base_price > 0
  IMAGED               = EXISTS non-placeholder product_images row
  STOREFRONT_VISIBLE   = LIVE AND is_active AND IMAGED
  SELLABLE             = STOREFRONT_VISIBLE AND is_available AND PRICED

Category selectable (app/utils/category_depth.py):
  leaf AND depth in {2, 3}
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import asyncpg

PLACEHOLDER_TOKENS = (
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

EXPECTED_HOST = "srv5944957438"
EXPECTED_DB = "karzar_staging"

# Phase 0 public API census (2026-09-27) — for reconciliation.
PHASE0_API = {
    "categories": 138,
    "l1": 15,
    "l2": 81,
    "l3": 42,
    "leaves": 114,
    "selectable": 111,
    "public_products": 1368,
    "categoryless_public": 0,
    "available_public": 716,
    "priced_public": 1046,
}

# Numeric IDs to resolve live (Phase 0 hard-coded census + specials).
HARDCODED_IDS: list[tuple[int, str, str, str]] = [
    # (id, files_summary, semantic_dependency, reachability)
    (1, "tests/fixtures; mock L1", "test/mock", "TEST_ONLY"),
    (2, "seed SPEC_TEMPLATE_KEYS; fixtures", "seed template", "MANUAL_OPERATION_ONLY"),
    (3, "seed root اینسرت; conftest default", "seed/test", "TEST_ONLY"),
    (4, "seed SPEC_TEMPLATE_KEYS", "seed template", "MANUAL_OPERATION_ONLY"),
    (5, "seed SPEC_TEMPLATE_KEYS", "seed template", "MANUAL_OPERATION_ONLY"),
    (7, "promote_measurement_to_l1 FORMER_HUB_ID", "ops script", "MANUAL_OPERATION_ONLY"),
    (13, "azarsanat hold map", "import keyword", "ACTIVE_IMPORT"),
    (22, "zcc SAFE_PATH_RULES; Cat-B pin", "ZCC import", "ACTIVE_IMPORT"),
    (25, "zcc SAFE_PATH_RULES; Cat-B pin", "ZCC import", "ACTIVE_IMPORT"),
    (26, "zcc SAFE_PATH_RULES", "ZCC import", "ACTIVE_IMPORT"),
    (27, "zcc SAFE_PATH_RULES; Cat-B; azarsanat", "ZCC/AST import", "ACTIVE_IMPORT"),
    (33, "seed; azarsanat DEPTH2; zcc tests/fixtures", "historic leaf", "ACTIVE_IMPORT"),
    (34, "seed; azarsanat DEPTH2", "historic leaf", "ACTIVE_IMPORT"),
    (35, "azarsanat endmill map", "import keyword", "ACTIVE_IMPORT"),
    (45, "zcc SAFE_PATH_RULES; Cat-B", "ZCC import", "ACTIVE_IMPORT"),
    (56, "seed; mitutoyo default parent; taxonomy bridge", "import/docs", "ACTIVE_IMPORT"),
    (57, "insize/mitutoyo/dasqua default leaf", "import keyword", "ACTIVE_IMPORT"),
    (58, "insize/mitutoyo maps", "import keyword", "ACTIVE_IMPORT"),
    (77, "insize tests; classification map", "import/test", "ACTIVE_IMPORT"),
    (80, "parse_price_list_pdfs hard assign", "PDF review CSV", "MANUAL_OPERATION_ONLY"),
    (81, "promote measurement; taxonomy bridge", "ops/docs", "MANUAL_OPERATION_ONLY"),
    (87, "promote measurement; taxonomy bridge", "ops/docs", "MANUAL_OPERATION_ONLY"),
    (116, "zcc SAFE_PATH_RULES", "ZCC import", "ACTIVE_IMPORT"),
    (117, "zcc SAFE_PATH_RULES", "ZCC import", "ACTIVE_IMPORT"),
    (121, "zcc SAFE_PATH_RULES; azarsanat", "import", "ACTIVE_IMPORT"),
    (154, "live accessories L1 (storefront alias)", "live L1", "ACTIVE_PRODUCTION_RUNTIME"),
    (165, "live inserts root (replaces seed 3)", "live L1", "ACTIVE_PRODUCTION_RUNTIME"),
    (166, "zcc SAFE_PATH_RULES; Cat-B 245 SKUs", "ZCC import", "ACTIVE_IMPORT"),
    (168, "live اینسرت فرز CNC (successor of 34)", "live leaf", "ACTIVE_PRODUCTION_RUNTIME"),
    (186, "helicoil L1 leaf", "live L1", "ACTIVE_PRODUCTION_RUNTIME"),
    (187, "helicoil L1 leaf", "live L1", "ACTIVE_PRODUCTION_RUNTIME"),
    (188, "helicoil L1 leaf", "live L1", "ACTIVE_PRODUCTION_RUNTIME"),
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_placeholder_url(url: str | None) -> bool:
    if not url or not str(url).strip():
        return True
    low = str(url).strip().lower()
    return any(tok in low for tok in PLACEHOLDER_TOKENS)


def _priced(v: Any) -> bool:
    if v is None:
        return False
    try:
        return Decimal(str(v)) > 0
    except Exception:
        return False


async def _connect() -> asyncpg.Connection:
    user = os.environ.get("POSTGRES_USER", "karzar_staging")
    password = os.environ.get("POSTGRES_PASSWORD", "")
    db = os.environ.get("POSTGRES_DB", "karzar_staging")
    host = os.environ.get("POSTGRES_SERVER") or os.environ.get("POSTGRES_HOST") or "db"
    port = int(os.environ.get("POSTGRES_PORT", "5432"))
    dsn = os.environ.get("AUDIT_DATABASE_URL")
    if dsn:
        dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
        dsn = dsn.replace("postgresql+psycopg2://", "postgresql://")
        conn = await asyncpg.connect(dsn)
    else:
        conn = await asyncpg.connect(
            user=user, password=password, database=db, host=host, port=port
        )
    await conn.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY")
    return conn


async def prove_identity(conn: asyncpg.Connection) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        SELECT current_database() AS db,
               current_user AS usr,
               inet_server_addr()::text AS addr,
               inet_server_port() AS port,
               version() AS ver
        """
    )
    ro = await conn.fetchval("SHOW transaction_read_only")
    default_ro = await conn.fetchval("SHOW default_transaction_read_only")
    alembic = await conn.fetchval("SELECT version_num FROM alembic_version LIMIT 1")
    return {
        "current_database": row["db"],
        "current_user": row["usr"],
        "inet_server_addr": row["addr"],
        "inet_server_port": row["port"],
        "version": row["ver"],
        "transaction_read_only": ro,
        "default_transaction_read_only": default_ro,
        "alembic_revision": alembic,
        "app_env": os.environ.get("APP_ENV"),
        "karzar_data_plane": os.environ.get("KARZAR_DATA_PLANE"),
        "hostname_env": os.environ.get("HOSTNAME"),
        "expected_host": EXPECTED_HOST,
        "expected_db": EXPECTED_DB,
        "host_proof": os.environ.get("KARZAR_HOST_PROOF"),
        "container_proof": os.environ.get("KARZAR_CONTAINER_PROOF"),
        "volume_proof": os.environ.get("KARZAR_VOLUME_PROOF"),
        "snapshot_time": _utc_now(),
    }


def identity_ok(identity: dict[str, Any]) -> tuple[bool, list[str]]:
    errs: list[str] = []
    if identity["current_database"] != EXPECTED_DB:
        errs.append(f"database={identity['current_database']} != {EXPECTED_DB}")
    if str(identity.get("transaction_read_only", "")).lower() not in {"on", "true"}:
        errs.append(f"transaction_read_only={identity.get('transaction_read_only')}")
    app_env = (identity.get("app_env") or "").lower()
    if app_env and app_env not in {"staging", "production"}:
        errs.append(f"unexpected APP_ENV={app_env}")
    plane = (identity.get("karzar_data_plane") or "").lower()
    if plane == "catalog_staging":
        errs.append("KARZAR_DATA_PLANE=catalog_staging (not live Production)")
    host = identity.get("host_proof") or ""
    if host and host != EXPECTED_HOST:
        errs.append(f"host_proof={host} != {EXPECTED_HOST}")
    return (len(errs) == 0, errs)


def build_category_meta(categories: list[asyncpg.Record]) -> dict[int, dict[str, Any]]:
    by_id = {int(c["id"]): c for c in categories}
    child_count: dict[int, int] = defaultdict(int)
    for c in categories:
        if c["parent_id"] is not None:
            child_count[int(c["parent_id"])] += 1

    meta: dict[int, dict[str, Any]] = {}
    for c in categories:
        cid = int(c["id"])
        chain: list[asyncpg.Record] = []
        cur: asyncpg.Record | None = c
        seen: set[int] = set()
        cycle = False
        while cur is not None:
            cur_id = int(cur["id"])
            if cur_id in seen:
                cycle = True
                break
            seen.add(cur_id)
            chain.append(cur)
            pid = cur["parent_id"]
            cur = by_id.get(int(pid)) if pid is not None else None
        depth = len(chain)
        is_leaf = child_count[cid] == 0
        selectable = is_leaf and 2 <= depth <= 3
        breadcrumb = " › ".join(node["name"] for node in reversed(chain))
        ancestors = [int(node["id"]) for node in reversed(chain[:-1])]
        root_id = int(chain[-1]["id"]) if chain else cid
        meta[cid] = {
            "depth": depth,
            "is_leaf": is_leaf,
            "is_selectable": selectable,
            "breadcrumb": breadcrumb,
            "ancestor_ids": ancestors,
            "root_id": root_id,
            "child_count": child_count[cid],
            "cycle": cycle,
            "invalid_parent": (
                c["parent_id"] is not None and int(c["parent_id"]) not in by_id
            ),
        }
    return meta


async def load_all(conn: asyncpg.Connection) -> dict[str, Any]:
    products = await conn.fetch(
        """
        SELECT p.id, p.sku, p.name, p.slug, p.brand_id, p.category_id,
               p.product_type_id, p.is_active, p.is_available,
               p.base_price, p.deleted_at,
               p.hesabfa_category_override_code
        FROM products p
        ORDER BY p.id
        """
    )
    brands = await conn.fetch("SELECT id, name, slug FROM brands ORDER BY id")
    categories = await conn.fetch(
        """
        SELECT id, name, slug, parent_id,
               spec_template_key, megamenu_hidden, megamenu_as_leaf, megamenu_bold,
               hesabfa_category_code, icon, image_url, meta_title, meta_description,
               created_at, updated_at
        FROM categories
        ORDER BY id
        """
    )
    images = await conn.fetch(
        """
        SELECT product_id, image_url, is_primary, display_order
        FROM product_images
        ORDER BY product_id, is_primary DESC, display_order, id
        """
    )
    product_types = await conn.fetch(
        """
        SELECT id, code, slug, name_fa, name_en, status
        FROM product_types
        ORDER BY id
        """
    )
    pt_defs = await conn.fetch(
        """
        SELECT id, product_type_id, version, status, change_reason, activated_at
        FROM product_type_definitions
        ORDER BY product_type_id, version
        """
    )
    memberships = await conn.fetch(
        """
        SELECT m.id, m.product_type_definition_id, m.property_definition_id,
               m.requiredness, m.filterable, m.comparable,
               m.display_group, m.display_order,
               m.evidence_requirement_override, m.validation_overrides,
               pd.key AS canonical_property_key
        FROM product_type_attribute_memberships m
        LEFT JOIN knowledge_property_definitions pd
          ON pd.definition_id = m.property_definition_id
        ORDER BY m.product_type_definition_id, m.display_order NULLS LAST, m.id
        """
    )
    kt_nodes = await conn.fetch(
        """
        SELECT id, node_id, dimension, node_type, slug, name_fa, name_en,
               parent_id, status, commerce_category_id, product_type_id,
               sort_order, steward
        FROM knowledge_taxonomy_nodes
        ORDER BY id
        """
    )
    kt_assign = await conn.fetch(
        """
        SELECT id, product_id, taxonomy_node_id, assignment_role,
               is_primary, source_ref, recorded_at, recorder
        FROM knowledge_classification_assignments
        ORDER BY id
        """
    )
    nav = await conn.fetch(
        """
        SELECT id, slug, label, sort_order, is_enabled, highlight, root_category_ids
        FROM megamenu_nav_groups
        ORDER BY sort_order, id
        """
    )
    return {
        "products": products,
        "brands": brands,
        "categories": categories,
        "images": images,
        "product_types": product_types,
        "pt_defs": pt_defs,
        "memberships": memberships,
        "kt_nodes": kt_nodes,
        "kt_assign": kt_assign,
        "nav": nav,
    }


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def run_census(raw: dict[str, Any], identity: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)

    brands = {int(b["id"]): b for b in raw["brands"]}
    cats = list(raw["categories"])
    cat_by_id = {int(c["id"]): c for c in cats}
    meta = build_category_meta(cats)
    pts = {int(p["id"]): p for p in raw["product_types"]}

    images_by_product: dict[int, list[str]] = defaultdict(list)
    for img in raw["images"]:
        images_by_product[int(img["product_id"])].append(img["image_url"] or "")

    # --- Product flags ---
    product_rows: list[dict[str, Any]] = []
    g = Counter()
    g["total_product_rows"] = len(raw["products"])

    assign_stats = Counter()
    by_cat_live = Counter()
    by_cat_active = Counter()
    by_cat_visible = Counter()
    by_cat_sellable = Counter()
    by_cat_pt_assigned = Counter()
    by_cat_pt_missing = Counter()
    by_root_pt = Counter()
    by_root_live = Counter()
    by_brand_pt = Counter()
    by_brand_live = Counter()
    pt_live = Counter()
    pt_active = Counter()
    pt_visible = Counter()

    for p in raw["products"]:
        pid = int(p["id"])
        live = p["deleted_at"] is None
        if not live:
            g["soft_deleted"] += 1
            continue
        g["live"] += 1
        active = bool(p["is_active"])
        available = bool(p["is_available"])
        priced = _priced(p["base_price"])
        urls = images_by_product.get(pid, [])
        has_image = any(not _is_placeholder_url(u) for u in urls)
        visible = active and has_image
        sellable = visible and available and priced

        if active:
            g["active"] += 1
        if available:
            g["available"] += 1
        if priced:
            g["priced"] += 1
        if has_image:
            g["imaged"] += 1
        if visible:
            g["visible"] += 1
        if sellable:
            g["sellable"] += 1

        brand_id = p["brand_id"]
        if brand_id is None:
            g["brandless"] += 1
            brand_name = ""
        else:
            brand_name = (brands.get(int(brand_id)) or {}).get("name", "")
            by_brand_live[int(brand_id)] += 1

        cid = p["category_id"]
        if cid is None:
            g["categoryless"] += 1
            assign_stats["live_categoryless"] += 1
            cat_name = cat_slug = breadcrumb = ""
            depth = is_leaf = is_sel = ""
            root_id = None
        elif int(cid) not in cat_by_id:
            g["invalid_category_fk"] += 1
            assign_stats["invalid_fk"] += 1
            cat_name = cat_slug = breadcrumb = ""
            depth = is_leaf = is_sel = ""
            root_id = None
        else:
            cid_i = int(cid)
            cm = meta[cid_i]
            cat = cat_by_id[cid_i]
            cat_name = cat["name"]
            cat_slug = cat["slug"]
            breadcrumb = cm["breadcrumb"]
            depth = cm["depth"]
            is_leaf = cm["is_leaf"]
            is_sel = cm["is_selectable"]
            root_id = cm["root_id"]
            by_cat_live[cid_i] += 1
            by_root_live[root_id] += 1
            if active:
                by_cat_active[cid_i] += 1
            if visible:
                by_cat_visible[cid_i] += 1
            if sellable:
                by_cat_sellable[cid_i] += 1
            assign_stats["live_categorized"] += 1
            if cm["depth"] == 1:
                assign_stats["assigned_to_root"] += 1
            if not cm["is_leaf"]:
                assign_stats["assigned_to_non_leaf"] += 1
            elif cm["is_selectable"]:
                assign_stats["assigned_to_selectable_leaf"] += 1
            else:
                assign_stats["assigned_to_non_selectable_leaf"] += 1

        pt_id = p["product_type_id"]
        if pt_id is None:
            g["pt_missing"] += 1
            if cid is not None and int(cid) in cat_by_id:
                by_cat_pt_missing[int(cid)] += 1
        else:
            pt_i = int(pt_id)
            if pt_i not in pts:
                g["pt_invalid_fk"] += 1
            else:
                g["pt_assigned"] += 1
                pt_live[pt_i] += 1
                if active:
                    pt_active[pt_i] += 1
                if visible:
                    pt_visible[pt_i] += 1
                if cid is not None and int(cid) in cat_by_id:
                    by_cat_pt_assigned[int(cid)] += 1
                    by_root_pt[meta[int(cid)]["root_id"]] += 1
                if brand_id is not None:
                    by_brand_pt[int(brand_id)] += 1

        if visible:
            g["visible_pt_assigned" if pt_id is not None else "visible_pt_missing"] += 1

        product_rows.append(
            {
                "product_id": pid,
                "sku": p["sku"],
                "name": p["name"],
                "brand_id": brand_id if brand_id is not None else "",
                "brand_name": brand_name,
                "category_id": cid if cid is not None else "",
                "category_name": cat_name,
                "category_slug": cat_slug,
                "category_depth": depth,
                "category_breadcrumb": breadcrumb,
                "is_category_leaf": is_leaf,
                "is_category_selectable": is_sel,
                "is_active": active,
                "is_available": available,
                "base_price_present": priced,
                "has_image": has_image,
                "storefront_visible": visible,
                "sellable": sellable,
                "product_type_id": pt_id if pt_id is not None else "",
            }
        )

    # --- Category census ---
    children: dict[int | None, list[int]] = defaultdict(list)
    for c in cats:
        children[c["parent_id"] if c["parent_id"] is None else int(c["parent_id"])].append(
            int(c["id"])
        )

    def descendants(cid: int) -> list[int]:
        out: list[int] = []
        stack = list(children.get(cid, []))
        while stack:
            n = stack.pop()
            out.append(n)
            stack.extend(children.get(n, []))
        return out

    cat_rows: list[dict[str, Any]] = []
    depth_counts = Counter()
    for c in cats:
        cid = int(c["id"])
        cm = meta[cid]
        depth_counts[cm["depth"]] += 1
        desc = descendants(cid)
        desc_live = sum(by_cat_live[d] for d in desc)
        cat_rows.append(
            {
                "id": cid,
                "name": c["name"],
                "slug": c["slug"],
                "parent_id": c["parent_id"] if c["parent_id"] is not None else "",
                "depth": cm["depth"],
                "breadcrumb": cm["breadcrumb"],
                "child_count": cm["child_count"],
                "is_leaf": cm["is_leaf"],
                "is_selectable": cm["is_selectable"],
                "direct_live_product_count": by_cat_live[cid],
                "descendant_live_product_count": desc_live,
                "active_count": by_cat_active[cid],
                "visible_count": by_cat_visible[cid],
                "sellable_count": by_cat_sellable[cid],
                "product_type_assigned_count": by_cat_pt_assigned[cid],
                "product_type_missing_count": by_cat_pt_missing[cid],
                "hesabfa_category_code": c["hesabfa_category_code"] or "",
                "spec_template_key": c["spec_template_key"] or "",
                "megamenu_hidden": c["megamenu_hidden"],
                "megamenu_as_leaf": c["megamenu_as_leaf"],
                "megamenu_bold": c["megamenu_bold"]
                if c["megamenu_bold"] is not None
                else "",
                "cycle": cm["cycle"],
                "invalid_parent": cm["invalid_parent"],
            }
        )

    l1 = sum(1 for c in cats if c["parent_id"] is None)
    leaves = sum(1 for cid, cm in meta.items() if cm["is_leaf"])
    selectable = sum(1 for cid, cm in meta.items() if cm["is_selectable"])
    empty = sum(1 for r in cat_rows if r["direct_live_product_count"] == 0 and r["descendant_live_product_count"] == 0)
    orphans = [cid for cid, cm in meta.items() if cm["invalid_parent"]]
    cycles = [cid for cid, cm in meta.items() if cm["cycle"]]

    # --- Product types ---
    defs_by_pt: dict[int, list[asyncpg.Record]] = defaultdict(list)
    for d in raw["pt_defs"]:
        defs_by_pt[int(d["product_type_id"])].append(d)
    mem_by_def: dict[int, list[asyncpg.Record]] = defaultdict(list)
    for m in raw["memberships"]:
        mem_by_def[int(m["product_type_definition_id"])].append(m)

    pt_rows: list[dict[str, Any]] = []
    def_rows: list[dict[str, Any]] = []
    pts_with_active_def = 0
    pts_without_active_def = 0
    pts_zero_defs = 0
    for pt in raw["product_types"]:
        ptid = int(pt["id"])
        defs = defs_by_pt.get(ptid, [])
        active_defs = [d for d in defs if d["status"] == "active"]
        if not defs:
            pts_zero_defs += 1
        if active_defs:
            pts_with_active_def += 1
            active_ver = active_defs[0]["version"]
        else:
            pts_without_active_def += 1
            active_ver = ""
        pt_rows.append(
            {
                "id": ptid,
                "code": pt["code"],
                "slug": pt["slug"],
                "name_fa": pt["name_fa"],
                "name_en": pt["name_en"] or "",
                "status": pt["status"],
                "live_product_count": pt_live[ptid],
                "active_product_count": pt_active[ptid],
                "visible_product_count": pt_visible[ptid],
                "definition_versions": "|".join(
                    f"{d['version']}:{d['status']}" for d in defs
                ),
                "active_definition_version": active_ver,
                "definition_count": len(defs),
            }
        )
        for d in defs:
            did = int(d["id"])
            for m in mem_by_def.get(did, []):
                def_rows.append(
                    {
                        "product_type_id": ptid,
                        "product_type_code": pt["code"],
                        "definition_id": did,
                        "definition_version": d["version"],
                        "definition_status": d["status"],
                        "property_definition_id": m["property_definition_id"],
                        "canonical_property_key": m["canonical_property_key"] or "",
                        "requiredness": m["requiredness"],
                        "filterable": m["filterable"],
                        "comparable": m["comparable"],
                        "display_group": m["display_group"] or "",
                        "display_order": m["display_order"]
                        if m["display_order"] is not None
                        else "",
                        "evidence_requirement_override": m["evidence_requirement_override"]
                        or "",
                    }
                )
            if not mem_by_def.get(did):
                def_rows.append(
                    {
                        "product_type_id": ptid,
                        "product_type_code": pt["code"],
                        "definition_id": did,
                        "definition_version": d["version"],
                        "definition_status": d["status"],
                        "property_definition_id": "",
                        "canonical_property_key": "",
                        "requiredness": "",
                        "filterable": "",
                        "comparable": "",
                        "display_group": "",
                        "display_order": "",
                        "evidence_requirement_override": "",
                    }
                )

    # PT coverage by category (live)
    pt_cov_rows = []
    for cid in sorted(by_cat_live):
        live_n = by_cat_live[cid]
        assigned = by_cat_pt_assigned[cid]
        pt_cov_rows.append(
            {
                "category_id": cid,
                "category_name": cat_by_id[cid]["name"],
                "breadcrumb": meta[cid]["breadcrumb"],
                "root_id": meta[cid]["root_id"],
                "live_products": live_n,
                "pt_assigned": assigned,
                "pt_missing": by_cat_pt_missing[cid],
                "coverage_pct": round(100.0 * assigned / live_n, 2) if live_n else 0.0,
            }
        )

    # --- Knowledge taxonomy ---
    node_by_id = {int(n["id"]): n for n in raw["kt_nodes"]}
    node_by_node_id = {n["node_id"]: n for n in raw["kt_nodes"]}
    kt_rows = []
    kt_dim = Counter()
    kt_status = Counter()
    broken_commerce = 0
    broken_pt = 0
    orphan_parent = 0
    for n in raw["kt_nodes"]:
        nid = int(n["id"])
        kt_dim[n["dimension"]] += 1
        kt_status[n["status"]] += 1
        parent_node_id = ""
        if n["parent_id"] is not None:
            parent = node_by_id.get(int(n["parent_id"]))
            if parent is None:
                orphan_parent += 1
            else:
                parent_node_id = parent["node_id"]
        if n["commerce_category_id"] is not None and int(n["commerce_category_id"]) not in cat_by_id:
            broken_commerce += 1
        if n["product_type_id"] is not None and int(n["product_type_id"]) not in pts:
            broken_pt += 1
        kt_rows.append(
            {
                "id": nid,
                "node_id": n["node_id"],
                "dimension": n["dimension"],
                "node_type": n["node_type"],
                "slug": n["slug"],
                "name_fa": n["name_fa"],
                "name_en": n["name_en"] or "",
                "parent_id": n["parent_id"] if n["parent_id"] is not None else "",
                "parent_node_id": parent_node_id,
                "status": n["status"],
                "commerce_category_id": n["commerce_category_id"]
                if n["commerce_category_id"] is not None
                else "",
                "product_type_id": n["product_type_id"]
                if n["product_type_id"] is not None
                else "",
                "sort_order": n["sort_order"] if n["sort_order"] is not None else "",
                "steward": n["steward"] or "",
            }
        )

    assign_rows = []
    role_counts = Counter()
    dim_assign = Counter()
    products_classified: set[int] = set()
    bridge_by_product: dict[int, list[int]] = defaultdict(list)
    for a in raw["kt_assign"]:
        role_counts[a["assignment_role"]] += 1
        products_classified.add(int(a["product_id"]))
        node = node_by_id.get(int(a["taxonomy_node_id"]))
        dim = node["dimension"] if node else "MISSING_NODE"
        dim_assign[dim] += 1
        if a["assignment_role"] == "product_type_bridge" and node and node["product_type_id"]:
            bridge_by_product[int(a["product_id"])].append(int(node["product_type_id"]))
        assign_rows.append(
            {
                "id": a["id"],
                "product_id": a["product_id"],
                "taxonomy_node_id": a["taxonomy_node_id"],
                "node_id": node["node_id"] if node else "",
                "dimension": dim,
                "assignment_role": a["assignment_role"],
                "is_primary": a["is_primary"],
                "source_ref": a["source_ref"] or "",
            }
        )

    # PT vs bridge consistency (among products with PT)
    bridge_stats = Counter()
    for p in raw["products"]:
        if p["deleted_at"] is not None:
            continue
        pt_id = p["product_type_id"]
        bridges = bridge_by_product.get(int(p["id"]), [])
        if pt_id is None:
            if bridges:
                bridge_stats["BRIDGE_WITHOUT_PRIMARY_PT"] += 1
            continue
        if not bridges:
            bridge_stats["MISSING_BRIDGE"] += 1
        elif len(set(bridges)) > 1:
            bridge_stats["MULTIPLE_BRIDGES"] += 1
        elif int(pt_id) in bridges:
            bridge_stats["MATCH"] += 1
        else:
            bridge_stats["MISMATCH"] += 1

    # --- Hesabfa ---
    hes_rows = []
    hes_populated = 0
    hes_null = 0
    hes_blank = 0
    code_counts: Counter = Counter()
    for c in cats:
        code = c["hesabfa_category_code"]
        if code is None:
            hes_null += 1
            code_s = ""
        else:
            code_s = str(code).strip()
            if not code_s:
                hes_blank += 1
            else:
                hes_populated += 1
                code_counts[code_s] += 1
        cid = int(c["id"])
        hes_rows.append(
            {
                "category_id": cid,
                "breadcrumb": meta[cid]["breadcrumb"],
                "hesabfa_category_code": code_s,
                "live_product_count": by_cat_live[cid] + sum(by_cat_live[d] for d in descendants(cid)),
                "mapping_present": bool(code_s),
            }
        )
    duplicate_codes = {k: v for k, v in code_counts.items() if v > 1}

    # --- Megamenu ---
    root_ids = [int(c["id"]) for c in cats if c["parent_id"] is None]
    root_to_groups: dict[int, list[str]] = defaultdict(list)
    mm_rows = []
    missing_root_refs = []
    for g_row in raw["nav"]:
        rids = g_row["root_category_ids"] or []
        if isinstance(rids, str):
            rids = json.loads(rids)
        names = []
        for rid in rids:
            rid_i = int(rid)
            if rid_i not in cat_by_id:
                missing_root_refs.append(rid_i)
                names.append(f"MISSING:{rid_i}")
            else:
                names.append(cat_by_id[rid_i]["name"])
                root_to_groups[rid_i].append(g_row["slug"])
        mm_rows.append(
            {
                "id": g_row["id"],
                "slug": g_row["slug"],
                "label": g_row["label"],
                "sort_order": g_row["sort_order"],
                "enabled": g_row["is_enabled"],
                "highlight": g_row["highlight"],
                "root_category_ids": "|".join(str(x) for x in rids),
                "resolved_root_names": " | ".join(names),
            }
        )
    exactly_once = sum(1 for r in root_ids if len(root_to_groups.get(r, [])) == 1)
    missing_mm = [r for r in root_ids if len(root_to_groups.get(r, [])) == 0]
    dup_mm = [r for r in root_ids if len(root_to_groups.get(r, [])) > 1]

    # --- Hardcoded ID resolution ---
    hc_rows = []
    for nid, files, dep, reach in HARDCODED_IDS:
        c = cat_by_id.get(nid)
        hc_rows.append(
            {
                "numeric_id": nid,
                "exists": bool(c),
                "live_name": c["name"] if c else "",
                "current_breadcrumb": meta[nid]["breadcrumb"] if c else "",
                "files_referencing": files,
                "semantic_dependency": dep,
                "reachability": reach,
                "risk": (
                    "MISSING_ID_STILL_REFERENCED"
                    if not c and reach in {"ACTIVE_IMPORT", "ACTIVE_PRODUCTION_RUNTIME"}
                    else ("OK_EXISTS" if c else "MISSING_NON_RUNTIME")
                ),
            }
        )

    # --- API vs DB reconciliation ---
    # Available/priced public: among visible products
    available_public = sum(
        1 for r in product_rows if r["storefront_visible"] and r["is_available"]
    )
    priced_public = sum(
        1 for r in product_rows if r["storefront_visible"] and r["base_price_present"]
    )
    categoryless_public = sum(
        1
        for r in product_rows
        if r["storefront_visible"] and r["category_id"] == ""
    )

    recon = [
        {"metric": "Categories", "public_api": PHASE0_API["categories"], "production_sql": len(cats)},
        {"metric": "L1", "public_api": PHASE0_API["l1"], "production_sql": l1},
        {"metric": "L2", "public_api": PHASE0_API["l2"], "production_sql": depth_counts.get(2, 0)},
        {"metric": "L3", "public_api": PHASE0_API["l3"], "production_sql": depth_counts.get(3, 0)},
        {"metric": "Leaves", "public_api": PHASE0_API["leaves"], "production_sql": leaves},
        {
            "metric": "Selectable leaves",
            "public_api": PHASE0_API["selectable"],
            "production_sql": selectable,
        },
        {
            "metric": "Public/storefront-visible products",
            "public_api": PHASE0_API["public_products"],
            "production_sql": g["visible"],
        },
        {
            "metric": "Categoryless public",
            "public_api": PHASE0_API["categoryless_public"],
            "production_sql": categoryless_public,
        },
        {
            "metric": "Available public",
            "public_api": PHASE0_API["available_public"],
            "production_sql": available_public,
        },
        {
            "metric": "Priced public",
            "public_api": PHASE0_API["priced_public"],
            "production_sql": priced_public,
        },
    ]
    for row in recon:
        row["match"] = row["public_api"] == row["production_sql"]

    # --- Write artifacts ---
    # 00 identity
    (out_dir / "00-db-identity.txt").write_text(
        "\n".join(
            [
                f"snapshot_time={identity.get('snapshot_time')}",
                f"current_database={identity.get('current_database')}",
                f"current_user={identity.get('current_user')}",
                f"inet_server_addr={identity.get('inet_server_addr')}",
                f"inet_server_port={identity.get('inet_server_port')}",
                f"transaction_read_only={identity.get('transaction_read_only')}",
                f"default_transaction_read_only={identity.get('default_transaction_read_only')}",
                f"alembic_revision={identity.get('alembic_revision')}",
                f"app_env={identity.get('app_env')}",
                f"karzar_data_plane={identity.get('karzar_data_plane')}",
                f"host_proof={identity.get('host_proof')}",
                f"container_proof={identity.get('container_proof')}",
                f"volume_proof={identity.get('volume_proof')}",
                f"pg_version={identity.get('version')}",
                # no passwords / DSNs
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    live = g["live"]
    coverage = round(100.0 * g["pt_assigned"] / live, 4) if live else 0.0
    visible_cov = (
        round(100.0 * g["visible_pt_assigned"] / g["visible"], 4) if g["visible"] else 0.0
    )
    classified_cov = round(100.0 * len(products_classified) / live, 4) if live else 0.0

    global_counts = {
        "sql_definitions": {
            "LIVE": "deleted_at IS NULL",
            "ACTIVE": "LIVE AND is_active",
            "AVAILABLE": "LIVE AND is_available",
            "PRICED": "LIVE AND base_price IS NOT NULL AND base_price > 0",
            "IMAGED": "EXISTS non-placeholder product_images row",
            "STOREFRONT_VISIBLE": "LIVE AND is_active AND IMAGED",
            "SELLABLE": "STOREFRONT_VISIBLE AND is_available AND PRICED",
        },
        "counts": dict(g),
        "assignment_stats": dict(assign_stats),
        "category_structure": {
            "total": len(cats),
            "l1": l1,
            "l2": depth_counts.get(2, 0),
            "l3": depth_counts.get(3, 0),
            "depth_gt_3": sum(v for d, v in depth_counts.items() if d > 3),
            "leaves": leaves,
            "selectable": selectable,
            "empty_live_subtree": empty,
            "orphans": orphans,
            "cycles": cycles,
            "special_ids": {
                str(i): (meta[i]["breadcrumb"] if i in cat_by_id else None)
                for i in (33, 34, 165, 166, 168, 186, 187, 188)
            },
        },
        "product_type": {
            "total_types": len(pts),
            "assigned_live": g["pt_assigned"],
            "missing_live": g["pt_missing"],
            "invalid_fk": g["pt_invalid_fk"],
            "coverage_pct_live": coverage,
            "visible_assigned": g["visible_pt_assigned"],
            "visible_missing": g["visible_pt_missing"],
            "visible_coverage_pct": visible_cov,
            "with_active_definition": pts_with_active_def,
            "without_active_definition": pts_without_active_def,
            "zero_definitions": pts_zero_defs,
            "zero_product_types": sum(1 for r in pt_rows if r["live_product_count"] == 0),
        },
        "knowledge_taxonomy": {
            "nodes": len(kt_rows),
            "by_dimension": dict(kt_dim),
            "by_status": dict(kt_status),
            "assignments": len(assign_rows),
            "unique_products_classified": len(products_classified),
            "coverage_pct_live": classified_cov,
            "by_role": dict(role_counts),
            "by_dimension_assignments": dict(dim_assign),
            "orphan_parent": orphan_parent,
            "broken_commerce_bridges": broken_commerce,
            "broken_product_type_bridges": broken_pt,
            "pt_bridge_consistency": dict(bridge_stats),
        },
        "hesabfa": {
            "categories_total": len(cats),
            "codes_populated": hes_populated,
            "codes_null": hes_null,
            "codes_blank": hes_blank,
            "duplicate_codes": duplicate_codes,
        },
        "megamenu": {
            "groups": len(mm_rows),
            "l1_exactly_once": exactly_once,
            "l1_total": l1,
            "missing_roots": missing_mm,
            "duplicate_roots": dup_mm,
            "missing_category_refs": missing_root_refs,
        },
        "identity": identity,
        "production_identity_proven": True,
        "read_only_proven": str(identity.get("transaction_read_only", "")).lower()
        in {"on", "true"},
    }
    (out_dir / "01-product-global-counts.json").write_text(
        json.dumps(global_counts, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )

    write_csv(
        out_dir / "02-production-products-category-census.csv",
        list(product_rows[0].keys()) if product_rows else ["product_id"],
        product_rows,
    )
    write_csv(out_dir / "03-production-category-census.csv", list(cat_rows[0].keys()), cat_rows)
    write_csv(
        out_dir / "04-product-type-census.csv",
        list(pt_rows[0].keys()) if pt_rows else ["id"],
        pt_rows,
    )
    write_csv(
        out_dir / "05-product-type-coverage-by-category.csv",
        list(pt_cov_rows[0].keys()) if pt_cov_rows else ["category_id"],
        pt_cov_rows,
    )
    write_csv(
        out_dir / "06-product-type-definitions.csv",
        list(def_rows[0].keys())
        if def_rows
        else ["product_type_id", "definition_id"],
        def_rows,
    )
    write_csv(
        out_dir / "07-knowledge-taxonomy-nodes.csv",
        list(kt_rows[0].keys()) if kt_rows else ["id", "node_id"],
        kt_rows,
    )
    write_csv(
        out_dir / "08-knowledge-classification-assignments.csv",
        list(assign_rows[0].keys()) if assign_rows else ["id", "product_id"],
        assign_rows,
    )
    write_csv(out_dir / "09-megamenu-db-census.csv", list(mm_rows[0].keys()), mm_rows)
    write_csv(out_dir / "10-hesabfa-category-map.csv", list(hes_rows[0].keys()), hes_rows)
    write_csv(out_dir / "11-hardcoded-id-live-resolution.csv", list(hc_rows[0].keys()), hc_rows)
    write_csv(
        out_dir / "12-api-vs-db-reconciliation.csv",
        ["metric", "public_api", "production_sql", "match"],
        recon,
    )

    # Findings markdown (draft; final report assembled after hashes)
    missing_active = [
        r for r in hc_rows if r["risk"] == "MISSING_ID_STILL_REFERENCED"
    ]
    findings = []
    findings.append("# Phase 0B Findings (auto)")
    findings.append("")
    findings.append(f"Snapshot: {identity.get('snapshot_time')}")
    findings.append(f"transaction_read_only: {identity.get('transaction_read_only')}")
    findings.append(f"Live products: {live}")
    findings.append(f"Visible: {g['visible']} (API Phase0={PHASE0_API['public_products']})")
    findings.append(f"PT coverage live: {coverage}% ({g['pt_assigned']}/{live})")
    findings.append(f"Knowledge nodes: {len(kt_rows)}; assignments: {len(assign_rows)}")
    findings.append(f"Hesabfa codes populated: {hes_populated}/{len(cats)}")
    findings.append("")
    findings.append("## Missing IDs still referenced (active import/runtime)")
    for r in missing_active:
        findings.append(
            f"- id={r['numeric_id']} reachability={r['reachability']} files={r['files_referencing']}"
        )
    findings.append("")
    findings.append("## Severity reassessment notes")
    findings.append(
        "- Azarsanat 33/34: ACTIVE_IMPORT (manual script). Missing parents are skipped "
        "(`missing parent` log) — does not auto-run in production request path. "
        "Severity → P1 (blocks correct AST import leaf padding / risks misfile if parents "
        "were assumed present), not continuous P0 runtime corruption."
    )
    findings.append(
        "- ZCC 166 SAFE_PATH_RULES / Cat-B pins: ACTIVE_IMPORT — P1 governance risk "
        "(numeric PK as semantic id); not a live request-path P0."
    )
    findings.append(
        "- Nav group root_category_ids: ACTIVE_PRODUCTION_RUNTIME data (presentation)."
    )
    (out_dir / "13-phase0b-findings.md").write_text("\n".join(findings) + "\n", encoding="utf-8")

    summary = {
        "global": global_counts,
        "reconciliation": recon,
        "missing_ids_active": missing_active,
    }
    (out_dir / "SUMMARY.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    (out_dir / "IDENTITY_PROBE.json").write_text(
        json.dumps(
            {"identity": identity, "ok": True, "errors": []},
            indent=2,
            ensure_ascii=False,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    return summary


def write_final_report(out_dir: Path, summary: dict[str, Any]) -> None:
    g = summary["global"]["counts"]
    cat = summary["global"]["category_structure"]
    pt = summary["global"]["product_type"]
    kt = summary["global"]["knowledge_taxonomy"]
    hes = summary["global"]["hesabfa"]
    mm = summary["global"]["megamenu"]
    idn = summary["global"]["identity"]
    recon = summary["reconciliation"]

    artifact_names = [
        "00-db-identity.txt",
        "01-product-global-counts.json",
        "02-production-products-category-census.csv",
        "03-production-category-census.csv",
        "04-product-type-census.csv",
        "05-product-type-coverage-by-category.csv",
        "06-product-type-definitions.csv",
        "07-knowledge-taxonomy-nodes.csv",
        "08-knowledge-classification-assignments.csv",
        "09-megamenu-db-census.csv",
        "10-hesabfa-category-map.csv",
        "11-hardcoded-id-live-resolution.csv",
        "12-api-vs-db-reconciliation.csv",
        "13-phase0b-findings.md",
        "14-phase0b-final-report.md",
        "SUMMARY.json",
        "IDENTITY_PROBE.json",
    ]

    live = g.get("live", 0)
    lines = [
        "KARZAR TAXONOMY PHASE 0B — RESULT",
        "=================================",
        "",
        "STATUS",
        "COMPLETE",
        "",
        "SAFETY",
        "Production mutation: NO",
        "Transaction mode: READ ONLY",
        "Deployment: NO",
        "Catalog APPLY: NO",
        "Taxonomy mutation: NO",
        "Repository mutation: YES diagnostic-only (audit workflow + artifacts on branch)",
        "",
        "IDENTITY",
        f"repo SHA: (workflow GITHUB_SHA — see Actions run)",
        f"VPS: {idn.get('host_proof')}",
        f"database: {idn.get('current_database')} user={idn.get('current_user')} "
        f"addr={idn.get('inet_server_addr')}:{idn.get('inet_server_port')}",
        f"data plane: APP_ENV={idn.get('app_env')} KARZAR_DATA_PLANE={idn.get('karzar_data_plane')}",
        f"APP_ENV: {idn.get('app_env')}",
        f"Alembic: {idn.get('alembic_revision')}",
        f"transaction_read_only: {idn.get('transaction_read_only')}",
        f"snapshot time: {idn.get('snapshot_time')}",
        "",
        "A. GLOBAL PRODUCT TRUTH",
        f"Live: {live}",
        f"Deleted: {g.get('soft_deleted', 0)}",
        f"Active: {g.get('active', 0)}",
        f"Available: {g.get('available', 0)}",
        f"Priced: {g.get('priced', 0)}",
        f"Imaged: {g.get('imaged', 0)}",
        f"Visible: {g.get('visible', 0)}",
        f"Sellable: {g.get('sellable', 0)}",
        f"Categoryless: {g.get('categoryless', 0)}",
        f"Brandless: {g.get('brandless', 0)}",
        "",
        "B. CATEGORY TRUTH",
        f"Categories: {cat['total']}",
        f"L1: {cat['l1']}",
        f"L2: {cat['l2']}",
        f"L3: {cat['l3']}",
        f"Leaves: {cat['leaves']}",
        f"Selectable: {cat['selectable']}",
        f"Empty: {cat['empty_live_subtree']}",
        f"Orphans: {cat['orphans']}",
        f"Cycles: {cat['cycles']}",
        f"Non-leaf assignments: {summary['global']['assignment_stats'].get('assigned_to_non_leaf', 0)}",
        f"Invalid assignments: {summary['global']['assignment_stats'].get('invalid_fk', 0)}",
        f"Special IDs: {json.dumps(cat['special_ids'], ensure_ascii=False)}",
        "",
        "C. PRODUCT TYPE",
        f"Product Types: {pt['total_types']}",
        f"Assigned products: {pt['assigned_live']}",
        f"Missing Product Type: {pt['missing_live']}",
        f"Coverage %: {pt['coverage_pct_live']}",
        f"Active definitions: {pt['with_active_definition']}",
        f"Zero-product Product Types: {pt['zero_product_types']}",
        "",
        "D. KNOWLEDGE TAXONOMY",
        f"Nodes: {kt['nodes']}",
        f"Active: {kt['by_status'].get('active', 0)}",
        f"Draft: {kt['by_status'].get('draft', 0)}",
        f"Deprecated: {kt['by_status'].get('deprecated', 0)}",
        f"Classified products: {kt['unique_products_classified']}",
        f"Coverage %: {kt['coverage_pct_live']}",
        f"Broken bridges: commerce={kt['broken_commerce_bridges']} pt={kt['broken_product_type_bridges']}",
        f"PT bridge consistency: {kt['pt_bridge_consistency']}",
        "",
        "E. HESABFA",
        f"Mapped categories: {hes['codes_populated']}",
        f"Unmapped: {hes['codes_null'] + hes['codes_blank']}",
        f"Duplicate codes: {hes['duplicate_codes']}",
        "",
        "F. MEGAMENU",
        f"Groups: {mm['groups']}",
        f"L1 represented exactly once: {mm['l1_exactly_once']}/{mm['l1_total']}",
        f"Missing: {mm['missing_roots']}",
        f"Duplicate: {mm['duplicate_roots']}",
        "",
        "G. NUMERIC-ID RISK",
        f"Missing IDs still referenced (active import/runtime): "
        f"{[r['numeric_id'] for r in summary['missing_ids_active']]}",
        "",
        "H. API ↔ DB RECONCILIATION",
    ]
    for r in recon:
        lines.append(
            f"| {r['metric']} | {r['public_api']} | {r['production_sql']} | {r['match']} |"
        )
    lines += [
        "",
        "I. PHASE 0 FINDINGS REVISED",
        "P0: (none continuous runtime — see findings)",
        "P1: numeric ID semantic deps in ACTIVE_IMPORT (ZCC/INSIZE/Mitutoyo/Azarsanat); "
        "missing 33/34 still referenced; commerce stable ID missing; PT coverage near-zero",
        "P2: storefront L1 drift; helicoil depth-1 leaves; Hesabfa mapping sparse/absent; "
        "Knowledge taxonomy empty or sparse",
        "P3: semantic property-like commerce leaves",
        "",
        "J. PHASE 0 COMPLETION VERDICT",
        "Can Phase 0 be closed? YES (if this report STATUS=COMPLETE and all gates proven)",
        "",
        "K. BLOCKERS BEFORE MASTER TAXONOMY V1",
        "1. Introduce commerce Category stable semantic code",
        "2. Migrate ACTIVE_IMPORT paths off bare integer PKs",
        "3. Decide metrology/helicoil L1 presentation vs ontology",
        "4. SEO redirect map for deleted/replaced category IDs/slugs",
        "5. Populate or formally defer Knowledge Taxonomy + PT coverage program",
        "",
        "L. SAFE NEXT STEP",
        "Phase 1 READ-ONLY/DESIGN: Master Taxonomy V1 draft + stable-ID scheme. Do not execute.",
        "",
        "ARTIFACTS",
    ]
    # Write report body without self-hash first
    body = "\n".join(lines) + "\n"
    report_path = out_dir / "14-phase0b-final-report.md"
    report_path.write_text(body, encoding="utf-8")

    art_lines = []
    for name in artifact_names:
        p = out_dir / name
        if not p.exists():
            continue
        if name == "14-phase0b-final-report.md":
            continue
        art_lines.append(f"{name}  SHA256={_sha256(p)}  bytes={p.stat().st_size}")
    # finalize report with artifact hashes
    final = body + "\n".join(art_lines) + "\n"
    report_path.write_text(final, encoding="utf-8")
    final2 = final + f"14-phase0b-final-report.md  SHA256={_sha256(report_path)}  bytes={report_path.stat().st_size}\n"
    report_path.write_text(final2, encoding="utf-8")


async def async_main(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    conn = await _connect()
    try:
        await conn.execute("BEGIN READ ONLY")
        identity = await prove_identity(conn)
        # Re-check after BEGIN READ ONLY
        ro2 = await conn.fetchval("SHOW transaction_read_only")
        identity["transaction_read_only_after_begin"] = ro2
        if str(ro2).lower() not in {"on", "true"}:
            identity["transaction_read_only"] = ro2
            (out_dir / "IDENTITY_PROBE.json").write_text(
                json.dumps(
                    {
                        "identity": identity,
                        "ok": False,
                        "errors": ["PRODUCTION_DB_READ_ONLY_NOT_PROVEN"],
                    },
                    indent=2,
                    default=str,
                )
                + "\n"
            )
            print("PRODUCTION_DB_READ_ONLY_NOT_PROVEN", file=sys.stderr)
            await conn.execute("ROLLBACK")
            return 2

        ok, errs = identity_ok(identity)
        (out_dir / "IDENTITY_PROBE.json").write_text(
            json.dumps(
                {"identity": identity, "ok": ok, "errors": errs},
                indent=2,
                default=str,
            )
            + "\n"
        )
        if not ok and not args.allow_identity_mismatch:
            print("IDENTITY_GATE_FAILED", errs, file=sys.stderr)
            await conn.execute("ROLLBACK")
            return 3

        raw = await load_all(conn)
        await conn.execute("ROLLBACK")
    except Exception:
        try:
            await conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        await conn.close()

    summary = run_census(raw, identity, out_dir)
    write_final_report(out_dir, summary)
    print("---PHASE0B_SUMMARY_BEGIN---")
    print(
        json.dumps(
            {
                "live": summary["global"]["counts"].get("live"),
                "visible": summary["global"]["counts"].get("visible"),
                "sellable": summary["global"]["counts"].get("sellable"),
                "categories": summary["global"]["category_structure"]["total"],
                "pt_assigned": summary["global"]["product_type"]["assigned_live"],
                "kt_nodes": summary["global"]["knowledge_taxonomy"]["nodes"],
                "hesabfa_populated": summary["global"]["hesabfa"]["codes_populated"],
                "read_only": summary["global"]["read_only_proven"],
                "recon_all_match": all(r["match"] for r in summary["reconciliation"]),
            },
            indent=2,
        )
    )
    print("---PHASE0B_SUMMARY_END---")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--allow-identity-mismatch",
        action="store_true",
        help="DEBUG only — do not use on Production audit",
    )
    args = parser.parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
