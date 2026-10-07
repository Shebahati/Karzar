"""Phase 3B2 closure helpers: live read-only prestate + schema-faithful Postgres rehearsal.

No live catalog mutation. Disposable Postgres only.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from app.domain.product_naming_phase3b2 import NEW_PT_CATALOG, sha256_text

NEW_PT_CODES = (
    "LONG_JAW_CALIPER",
    "INSIDE_SPRING_CALIPER",
    "OUTSIDE_SPRING_CALIPER",
    "GAP_TAPER_GAUGE",
    "TAPER_BORE_GAUGE",
    "TAPER_GAUGE_SET",
    "LASER_LEVEL",
)
PROPERTY_CODES = ("body_length", "plate_dimensions")
MEMBERSHIPS = (
    ("LEVEL", "body_length"),
    ("DIGITAL_LEVEL", "body_length"),
    ("INSIDE_SPRING_CALIPER", "body_length"),
    ("OUTSIDE_SPRING_CALIPER", "body_length"),
    ("SURFACE_PLATE", "plate_dimensions"),
)


def load_live_dump(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def classify_identity_drift(
    frozen_row: dict[str, str],
    live_row: dict[str, str],
) -> list[str]:
    flags: list[str] = []
    if live_row.get("deleted_at"):
        flags.append("DELETED")
    if (frozen_row.get("historical_name") or frozen_row.get("current_name") or "") and live_row.get(
        "name"
    ) not in {
        frozen_row.get("historical_name", ""),
        frozen_row.get("current_name", ""),
        frozen_row.get("name", ""),
    }:
        # compare against phase3b1 snapshot name when present
        snap = (
            frozen_row.get("historical_name")
            or frozen_row.get("current_name")
            or frozen_row.get("name")
            or ""
        )
        if snap and snap != live_row.get("name", ""):
            flags.append("NAME_DRIFT")
    if frozen_row.get("manufacturer_code") and frozen_row["manufacturer_code"] != live_row.get(
        "manufacturer_code", ""
    ):
        flags.append("MANUFACTURER_CODE_DRIFT")
    # sku often == manufacturer_code for this cohort
    if frozen_row.get("manufacturer_code") and live_row.get("sku") not in {
        frozen_row["manufacturer_code"],
        live_row.get("manufacturer_code", ""),
    }:
        # only flag if sku differs from both frozen mfr and live mfr
        if live_row.get("sku") != frozen_row.get("manufacturer_code"):
            flags.append("SKU_DRIFT")
    frozen_pt = (
        frozen_row.get("product_type_code")
        or frozen_row.get("current_product_type_code")
        or frozen_row.get("current_pt_code")
        or ""
    )
    if frozen_pt and frozen_pt != live_row.get("product_type_code", ""):
        flags.append("PRODUCT_TYPE_DRIFT")
    if frozen_row.get("brand_id") and frozen_row.get("brand_id") != live_row.get("brand_id", ""):
        flags.append("BRAND_DRIFT")
    if not flags:
        flags.append("NO_DRIFT")
    return flags


def build_live_prestate_artifacts(
    *,
    dump: dict[str, Any],
    scope_rows: list[dict[str, str]],
    routing_rows: list[dict[str, str]],
    mutation_plan: list[dict[str, str]],
) -> dict[str, Any]:
    live_by_id = {r["product_id"]: r for r in dump["products"]}
    scope_by_id = {r["product_id"]: r for r in scope_rows}
    routing_by_id = {r["product_id"]: r for r in routing_rows}

    requested = [r["product_id"] for r in scope_rows]
    found_ids = [pid for pid in requested if pid in live_by_id]
    missing = [pid for pid in requested if pid not in live_by_id]
    dupes = [pid for pid, n in Counter(requested).items() if n > 1]

    prestate_rows: list[dict[str, str]] = []
    drift_counts: Counter[str] = Counter()
    for pid in requested:
        live = live_by_id.get(pid)
        scope = scope_by_id[pid]
        routing = routing_by_id.get(pid, {})
        if not live:
            flags = ["MISSING"]
            drift_counts["MISSING"] += 1
            prestate_rows.append(
                {
                    "product_id": pid,
                    "sku": "",
                    "manufacturer_code": scope.get("manufacturer_code", ""),
                    "name": "",
                    "brand_id": "",
                    "category_id": "",
                    "product_type_id": "",
                    "product_type_code": "",
                    "deleted_at": "",
                    "kb_facts": "",
                    "property_membership": "",
                    "prestate_source": "live_readonly_query",
                    "live_identity_drift": "|".join(flags),
                }
            )
            continue
        frozen_for_compare = {
            "manufacturer_code": scope.get("manufacturer_code", ""),
            "historical_name": scope.get("historical_name", ""),
            "product_type_code": scope.get("product_type_code", "")
            or routing.get("current_pt_code", ""),
            "brand_id": live.get("brand_id", ""),  # brand not in frozen scope — skip false BRAND_DRIFT
        }
        # Name drift vs phase3b1 snapshot historical_name
        flags = []
        if live.get("deleted_at"):
            flags.append("DELETED")
        hist = scope.get("historical_name", "")
        if hist and hist != live.get("name", ""):
            flags.append("NAME_DRIFT")
        if scope.get("manufacturer_code") != live.get("manufacturer_code", ""):
            flags.append("MANUFACTURER_CODE_DRIFT")
        if live.get("sku") != live.get("manufacturer_code") and live.get("sku") != scope.get(
            "manufacturer_code"
        ):
            # cohort uses sku≈mfr; flag only if unexpected
            if live.get("sku") != scope.get("manufacturer_code"):
                flags.append("SKU_DRIFT")
        expected_pt = scope.get("product_type_code") or routing.get("current_pt_code", "")
        if expected_pt and expected_pt != live.get("product_type_code", ""):
            flags.append("PRODUCT_TYPE_DRIFT")
        if not flags:
            flags = ["NO_DRIFT"]
        for f in flags:
            drift_counts[f] += 1
        kb = ";".join(dump.get("kb_facts_by_product", {}).get(pid, []))
        prestate_rows.append(
            {
                "product_id": pid,
                "sku": live.get("sku", ""),
                "manufacturer_code": live.get("manufacturer_code", ""),
                "name": live.get("name", ""),
                "brand_id": live.get("brand_id", ""),
                "category_id": live.get("category_id", ""),
                "product_type_id": live.get("product_type_id", ""),
                "product_type_code": live.get("product_type_code", ""),
                "deleted_at": live.get("deleted_at", ""),
                "kb_facts": kb,
                "property_membership": "",
                "prestate_source": "live_readonly_query",
                "live_identity_drift": "|".join(flags),
            }
        )

    # Routing precondition: for each reassignment, live PT == plan old_value
    mismatches = []
    for step in mutation_plan:
        if step["entity_type"] != "Product.product_type_id":
            continue
        pid = step["affected_product_id"]
        live = live_by_id.get(pid)
        if not live:
            mismatches.append({"product_id": pid, "reason": "missing_live"})
            continue
        if live.get("product_type_code") != step["old_value"]:
            mismatches.append(
                {
                    "product_id": pid,
                    "expected_old": step["old_value"],
                    "live_pt": live.get("product_type_code"),
                }
            )

    pt_collisions = list(dump.get("new_pt_code_collisions") or [])
    prop_probe = list(dump.get("property_probe_rows") or [])
    property_status = {
        "body_length": {
            "exact": "absent",
            "semantic_equivalent": "none_observed",
            "code_collision": "no",
            "status": "absent",
        },
        "plate_dimensions": {
            "exact": "absent",
            "semantic_equivalent": "none_observed",
            "code_collision": "no",
            "status": "absent",
        },
    }
    for row in prop_probe:
        key = row.split("|", 1)[0]
        if key in property_status:
            property_status[key] = {
                "exact": "existing",
                "semantic_equivalent": key,
                "code_collision": "yes",
                "status": "existing_exact",
                "raw": row,
            }

    unsafe_drift = (
        drift_counts.get("PRODUCT_TYPE_DRIFT", 0)
        + drift_counts.get("MANUFACTURER_CODE_DRIFT", 0)
        + drift_counts.get("DELETED", 0)
        + drift_counts.get("MISSING", 0)
    )
    # NAME_DRIFT alone is informational (Phase 3B2 does not mutate names)
    name_drift = drift_counts.get("NAME_DRIFT", 0)

    manifest = {
        "collected_at_utc": dump.get("collected_at_utc"),
        "host": dump.get("host"),
        "database": dump.get("database"),
        "APP_ENV": dump.get("APP_ENV"),
        "alembic_revision": dump.get("alembic_revision"),
        "postgres_version": dump.get("postgres_version"),
        "transaction_read_only": dump.get("transaction_read_only"),
        "rows_requested": 132,
        "rows_found": len(found_ids),
        "missing_ids": missing,
        "duplicate_ids": dupes,
        "NO_DRIFT": drift_counts.get("NO_DRIFT", 0),
        "NAME_DRIFT": name_drift,
        "SKU_DRIFT": drift_counts.get("SKU_DRIFT", 0),
        "MANUFACTURER_CODE_DRIFT": drift_counts.get("MANUFACTURER_CODE_DRIFT", 0),
        "PRODUCT_TYPE_DRIFT": drift_counts.get("PRODUCT_TYPE_DRIFT", 0),
        "BRAND_DRIFT": drift_counts.get("BRAND_DRIFT", 0),
        "DELETED": drift_counts.get("DELETED", 0),
        "mutation_sql_executed": dump.get("mutation_sql_executed", 0),
        "result": (
            "PASS"
            if len(found_ids) == 132
            and not missing
            and not dupes
            and dump.get("transaction_read_only") == "on"
            and dump.get("mutation_sql_executed", 0) == 0
            else "FAIL"
        ),
    }
    precondition = {
        "routing_precondition_mismatch": len(mismatches),
        "routing_mismatches": mismatches,
        "new_pt_code_collision": len(pt_collisions),
        "new_pt_code_collisions": pt_collisions,
        "property_status": property_status,
        "property_collision": sum(
            1 for v in property_status.values() if v.get("code_collision") == "yes"
        ),
        "unsafe_identity_drift_count": unsafe_drift,
        "name_drift_informational": name_drift,
        "plan_still_valid": len(mismatches) == 0
        and len(pt_collisions) == 0
        and unsafe_drift == 0
        and len(found_ids) == 132,
        "result": (
            "PASS"
            if len(mismatches) == 0
            and len(pt_collisions) == 0
            and unsafe_drift == 0
            and len(found_ids) == 132
            else "FAIL"
        ),
    }
    return {
        "prestate_rows": prestate_rows,
        "manifest": manifest,
        "precondition": precondition,
    }


async def _fingerprint_scope(conn: Any, product_ids: list[int]) -> str:
    pts = await conn.fetch("SELECT id, code, slug, name_fa, status FROM product_types ORDER BY id")
    props = await conn.fetch(
        "SELECT definition_id, key, status, data_type FROM knowledge_property_definitions ORDER BY key"
    )
    mem = await conn.fetch(
        """
        SELECT pt.code, kpd.key, m.requiredness
        FROM product_type_attribute_memberships m
        JOIN product_type_definitions d ON d.id = m.product_type_definition_id
        JOIN product_types pt ON pt.id = d.product_type_id
        JOIN knowledge_property_definitions kpd ON kpd.definition_id = m.property_definition_id
        ORDER BY 1,2
        """
    )
    prods = await conn.fetch(
        """
        SELECT id, sku, manufacturer_code, name, product_type_id
        FROM products WHERE id = ANY($1::int[]) ORDER BY id
        """,
        product_ids,
    )
    blob = json.dumps(
        {
            "pts": [dict(r) for r in pts],
            "props": [dict(r) for r in props],
            "mem": [dict(r) for r in mem],
            "prods": [dict(r) for r in prods],
        },
        sort_keys=True,
        default=str,
    )
    return sha256_text(blob)


async def seed_postgres_fixture(conn: Any, dump: dict[str, Any], routing_rows: list[dict[str, str]]) -> str:
    """Seed minimal real-schema fixture matching live mutation-sensitive fields."""
    # brands
    for b in dump.get("brands") or []:
        bid, name, slug = b[0], b[1], b[2]
        await conn.execute(
            """
            INSERT INTO brands (id, name, slug)
            VALUES ($1::int, $2, $3)
            ON CONFLICT (id) DO NOTHING
            """,
            int(bid),
            name,
            slug,
        )
    # categories
    for c in dump.get("categories") or []:
        cid, name, slug = c[0], c[1], c[2]
        await conn.execute(
            """
            INSERT INTO categories (id, name, slug)
            VALUES ($1::int, $2, $3)
            ON CONFLICT (id) DO NOTHING
            """,
            int(cid),
            name,
            slug,
        )
    # product types (existing)
    for pt in dump.get("product_types_seed") or []:
        # id|code|slug|name_fa|name_en|status
        pid, code, slug, name_fa, name_en, status = pt[0], pt[1], pt[2], pt[3], pt[4], pt[5]
        await conn.execute(
            """
            INSERT INTO product_types (id, code, slug, name_fa, name_en, status)
            VALUES ($1::int, $2, $3, $4, NULLIF($5,''), $6)
            ON CONFLICT (id) DO NOTHING
            """,
            int(pid),
            code,
            slug,
            name_fa,
            name_en,
            status,
        )
        # ensure active definition exists for membership targets
        await conn.execute(
            """
            INSERT INTO product_type_definitions (product_type_id, version, status, change_reason)
            SELECT $1::int, 1, 'active', 'phase3b2_fixture'
            WHERE NOT EXISTS (
              SELECT 1 FROM product_type_definitions d
              WHERE d.product_type_id = $1::int AND d.status = 'active'
            )
            """,
            int(pid),
        )

    # products
    for p in dump["products"]:
        await conn.execute(
            """
            INSERT INTO products (
              id, sku, slug, name, manufacturer_code, category_id, brand_id,
              product_type_id, stock_quantity, specifications, is_active, is_available
            ) VALUES (
              $1::int, $2, $3, $4, NULLIF($5,''), $6::int,
              NULLIF($7,'')::int, NULLIF($8,'')::int,
              0, '{}'::jsonb, true, true
            )
            ON CONFLICT (id) DO NOTHING
            """,
            int(p["product_id"]),
            p["sku"],
            f"fixture-{p['product_id']}-{p['sku']}",
            p["name"],
            p["manufacturer_code"],
            int(p["category_id"]),
            p["brand_id"] or None,
            p["product_type_id"] or None,
        )

    # reset sequences to avoid PK collisions on creates
    await conn.execute(
        "SELECT setval(pg_get_serial_sequence('product_types','id'), "
        "GREATEST((SELECT COALESCE(MAX(id),1) FROM product_types),1))"
    )
    await conn.execute(
        "SELECT setval(pg_get_serial_sequence('knowledge_property_definitions','id'), "
        "GREATEST((SELECT COALESCE(MAX(id),1) FROM knowledge_property_definitions),1))"
    )

    product_ids = [int(r["product_id"]) for r in routing_rows]
    return await _fingerprint_scope(conn, product_ids)


async def run_postgres_mutation_txn(
    conn: Any,
    *,
    mutation_plan: list[dict[str, str]],
    live_by_id: dict[str, dict[str, str]],
    fail_at: str | None = None,
) -> dict[str, Any]:
    """Execute exact plan under SERIALIZABLE; always ROLLBACK."""
    created_pts: list[str] = []
    props_created: list[str] = []
    memberships = 0
    reassigned = 0
    error: str | None = None
    status = "UNKNOWN"
    await conn.execute("SET LOCAL lock_timeout = '5s'")
    await conn.execute("SET LOCAL statement_timeout = '60s'")
    # Lock products that will be reassigned
    reassign_ids = [
        int(s["affected_product_id"])
        for s in mutation_plan
        if s["entity_type"] == "Product.product_type_id"
    ]
    if reassign_ids:
        await conn.fetch(
            "SELECT id FROM products WHERE id = ANY($1::int[]) ORDER BY id FOR UPDATE",
            reassign_ids,
        )
    try:
        for step in mutation_plan:
            et, action = step["entity_type"], step["action"]
            if et == "ProductType" and action == "CREATE":
                code = step["entity_id_or_key"]
                meta = NEW_PT_CATALOG[code]
                slug = code.lower().replace("_", "-")
                row = await conn.fetchrow(
                    """
                    INSERT INTO product_types (code, slug, name_fa, name_en, status, description)
                    VALUES ($1, $2, $3, $4, 'active', $5)
                    RETURNING id
                    """,
                    code,
                    slug,
                    meta.persian_title,
                    meta.english_concept,
                    meta.semantic_definition,
                )
                await conn.execute(
                    """
                    INSERT INTO product_type_definitions (product_type_id, version, status, change_reason)
                    VALUES ($1, 1, 'active', 'phase3b2_rehearsal')
                    """,
                    row["id"],
                )
                created_pts.append(code)
                if fail_at == "after_first_pt_create" and len(created_pts) == 1:
                    raise RuntimeError("injected:after_first_pt_create")
                if fail_at == "mid_pt_creation" and len(created_pts) == 4:
                    raise RuntimeError("injected:mid_pt_creation")
                if fail_at == "after_all_pt_creation" and len(created_pts) == 7:
                    raise RuntimeError("injected:after_all_pt_creation")
            elif et == "Property" and action == "CREATE":
                pcode = step["entity_id_or_key"]
                if fail_at == "after_first_property_create" and len(props_created) == 0:
                    # create then fail after first
                    pass
                data_type = "number" if pcode == "body_length" else "string"
                unit_dim = "length" if pcode == "body_length" else None
                def_id = f"prop.{pcode}.v1"
                await conn.execute(
                    """
                    INSERT INTO knowledge_property_definitions (
                      definition_id, key, data_type, unit_dimension, default_unit,
                      label_en, label_fa, validation, version, status
                    ) VALUES (
                      $1, $2, $3, $4, $5, $6, $7, '{}'::jsonb, '1', 'draft'
                    )
                    """,
                    def_id,
                    pcode,
                    data_type,
                    unit_dim,
                    "mm" if pcode == "body_length" else None,
                    pcode.replace("_", " ").title(),
                    pcode,
                )
                props_created.append(pcode)
                if fail_at == "after_first_property_create" and len(props_created) == 1:
                    raise RuntimeError("injected:after_first_property_create")
            elif et == "ProductTypePropertyMembership" and action == "CREATE":
                pt_code, pcode = step["entity_id_or_key"].split(":", 1)
                def_id = f"prop.{pcode}.v1"
                drow = await conn.fetchrow(
                    """
                    SELECT d.id FROM product_type_definitions d
                    JOIN product_types pt ON pt.id = d.product_type_id
                    WHERE pt.code = $1 AND d.status = 'active'
                    ORDER BY d.version DESC LIMIT 1
                    """,
                    pt_code,
                )
                if drow is None:
                    raise RuntimeError(f"missing active definition for {pt_code}")
                await conn.execute(
                    """
                    INSERT INTO product_type_attribute_memberships (
                      product_type_definition_id, property_definition_id, requiredness
                    ) VALUES ($1, $2, 'required')
                    """,
                    drow["id"],
                    def_id,
                )
                memberships += 1
                if fail_at == "after_memberships" and memberships == 5:
                    raise RuntimeError("injected:after_memberships")
            elif et == "Product.product_type_id" and action == "REASSIGN":
                pid = int(step["affected_product_id"])
                live_pt = live_by_id[str(pid)]["product_type_code"]
                # fail-closed: old PT must match live/fixture
                cur = await conn.fetchrow(
                    """
                    SELECT pt.code FROM products p
                    JOIN product_types pt ON pt.id = p.product_type_id
                    WHERE p.id = $1
                    """,
                    pid,
                )
                if cur is None or cur["code"] != step["old_value"]:
                    raise RuntimeError(
                        f"old_pt_mismatch product={pid} expected={step['old_value']} "
                        f"got={None if cur is None else cur['code']} live={live_pt}"
                    )
                target = await conn.fetchrow(
                    "SELECT id FROM product_types WHERE code = $1", step["new_value"]
                )
                if target is None:
                    raise RuntimeError(f"missing target PT {step['new_value']}")
                await conn.execute(
                    "UPDATE products SET product_type_id = $1 WHERE id = $2",
                    target["id"],
                    pid,
                )
                reassigned += 1
                total = sum(1 for s in mutation_plan if s["entity_type"] == "Product.product_type_id")
                mid = max(1, total // 2)
                if fail_at == "mid_reassignment" and reassigned == mid:
                    raise RuntimeError("injected:mid_reassignment")
                if fail_at == "after_all_reassignments" and reassigned == total:
                    raise RuntimeError("injected:after_all_reassignments")
            else:
                raise RuntimeError(f"unknown step {et}/{action}")

        # post-write validation
        if fail_at == "validation_failure":
            raise RuntimeError("injected:validation_failure")
        if len(created_pts) != 7:
            raise RuntimeError(f"pt_create_count={len(created_pts)}")
        if len(props_created) != 2:
            raise RuntimeError(f"prop_count={len(props_created)}")
        if memberships != 5:
            raise RuntimeError(f"membership_count={memberships}")
        if reassigned != 44:
            raise RuntimeError(f"reassign_count={reassigned}")
        # verify targets
        for step in mutation_plan:
            if step["entity_type"] != "Product.product_type_id":
                continue
            row = await conn.fetchrow(
                """
                SELECT pt.code FROM products p
                JOIN product_types pt ON pt.id = p.product_type_id
                WHERE p.id = $1
                """,
                int(step["affected_product_id"]),
            )
            if row["code"] != step["new_value"]:
                raise RuntimeError(
                    f"post_target_mismatch {step['affected_product_id']} "
                    f"{row['code']}!={step['new_value']}"
                )
        # Product.name unchanged vs fixture names from live
        status = "VALIDATED_READY_FOR_ROLLBACK"
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
        status = "FAILED"
    return {
        "status": status,
        "error": error,
        "created_pts": created_pts,
        "props_created": props_created,
        "memberships": memberships,
        "reassigned": reassigned,
    }


async def run_postgres_rehearsal(
    dsn: str,
    *,
    dump: dict[str, Any],
    routing_rows: list[dict[str, str]],
    mutation_plan: list[dict[str, str]],
    fail_at: str | None = None,
) -> dict[str, Any]:
    import asyncpg

    product_ids = [int(r["product_id"]) for r in routing_rows]
    live_by_id = {r["product_id"]: r for r in dump["products"]}

    # Seed connection (autocommit)
    seed_conn = await asyncpg.connect(dsn)
    try:
        await seed_conn.execute("TRUNCATE product_type_attribute_memberships, product_type_definitions, products, knowledge_property_definitions, product_types, brands, categories RESTART IDENTITY CASCADE")
        pre_fp = await seed_postgres_fixture(seed_conn, dump, routing_rows)
        pgver = await seed_conn.fetchval("SELECT version()")
        alem = await seed_conn.fetchval("SELECT version_num FROM alembic_version")
    finally:
        await seed_conn.close()

    # Mutation connection SERIALIZABLE + ROLLBACK
    conn = await asyncpg.connect(dsn)
    tx_result: dict[str, Any]
    try:
        tr = conn.transaction(isolation="serializable")
        await tr.start()
        try:
            tx_result = await run_postgres_mutation_txn(
                conn,
                mutation_plan=mutation_plan,
                live_by_id=live_by_id,
                fail_at=fail_at,
            )
        finally:
            await tr.rollback()
    finally:
        await conn.close()

    # Fresh connection drift check
    fresh = await asyncpg.connect(dsn)
    try:
        post_fp = await _fingerprint_scope(fresh, product_ids)
        pt_new = await fresh.fetchval(
            "SELECT count(*) FROM product_types WHERE code = ANY($1::text[])",
            list(NEW_PT_CODES),
        )
        prop_new = await fresh.fetchval(
            "SELECT count(*) FROM knowledge_property_definitions WHERE key = ANY($1::text[])",
            list(PROPERTY_CODES),
        )
        mem_new = await fresh.fetchval(
            """
            SELECT count(*) FROM product_type_attribute_memberships m
            JOIN knowledge_property_definitions kpd ON kpd.definition_id = m.property_definition_id
            WHERE kpd.key = ANY($1::text[])
            """,
            list(PROPERTY_CODES),
        )
        # ensure product PT codes still match live dump
        drift_rows = 0
        for p in dump["products"]:
            code = await fresh.fetchval(
                """
                SELECT pt.code FROM products pr
                JOIN product_types pt ON pt.id = pr.product_type_id
                WHERE pr.id = $1
                """,
                int(p["product_id"]),
            )
            if code != p["product_type_code"]:
                drift_rows += 1
        name_changed = await fresh.fetchval(
            """
            SELECT count(*) FROM products p
            JOIN (SELECT unnest($1::int[]) AS id) x ON x.id = p.id
            WHERE p.name NOT IN (SELECT name FROM products WHERE false)
            """,
            product_ids,
        )
        # compare names to dump
        name_mismatch = 0
        for p in dump["products"]:
            nm = await fresh.fetchval("SELECT name FROM products WHERE id=$1", int(p["product_id"]))
            if nm != p["name"]:
                name_mismatch += 1
    finally:
        await fresh.close()

    persistent = 0 if post_fp == pre_fp and pt_new == 0 and prop_new == 0 and mem_new == 0 and drift_rows == 0 and name_mismatch == 0 else 1
    ok = persistent == 0 and (
        (fail_at is None and tx_result["status"] == "VALIDATED_READY_FOR_ROLLBACK")
        or (fail_at is not None and tx_result["status"] == "FAILED")
    )
    return {
        "db_engine": "postgresql",
        "db_version": pgver,
        "alembic_revision": alem,
        "creation_method": "disposable_postgres_alembic_head_fixture",
        "schema_source": "alembic upgrade head (u4v5w6x7y8z9)",
        "production_data_used": False,
        "fixture_source": "live_readonly_dump_mutation_sensitive_fields",
        "isolation": "SERIALIZABLE + ROLLBACK",
        "prestate_fingerprint": pre_fp,
        "post_rollback_fingerprint": post_fp,
        "persistent_mutations": persistent,
        "fresh_connection_pt_creates": int(pt_new),
        "fresh_connection_property_creates": int(prop_new),
        "fresh_connection_memberships": int(mem_new),
        "fresh_connection_pt_reassign_drift": drift_rows,
        "product_name_actions": name_mismatch,
        "tx": tx_result,
        "fail_at": fail_at,
        "result": "PASS" if ok else "FAIL",
        "classification": "SCHEMA_FAITHFUL_POSTGRES_REHEARSAL",
    }


async def run_postgres_failure_injections(
    dsn: str,
    *,
    dump: dict[str, Any],
    routing_rows: list[dict[str, str]],
    mutation_plan: list[dict[str, str]],
) -> dict[str, Any]:
    points = [
        "after_first_pt_create",
        "mid_pt_creation",
        "after_all_pt_creation",
        "after_first_property_create",
        "after_memberships",
        "mid_reassignment",
        "after_all_reassignments",
        "validation_failure",
    ]
    out: dict[str, Any] = {}
    for p in points:
        r = await run_postgres_rehearsal(
            dsn,
            dump=dump,
            routing_rows=routing_rows,
            mutation_plan=mutation_plan,
            fail_at=p,
        )
        out[p] = {
            "status": r["tx"]["status"],
            "error": r["tx"]["error"],
            "persistent_mutations": r["persistent_mutations"],
            "rollback_ok": r["persistent_mutations"] == 0,
            "result": r["result"],
        }
    out["all_rollback_ok"] = all(v["rollback_ok"] for v in out.values() if isinstance(v, dict) and "rollback_ok" in v)
    out["result"] = "PASS" if out["all_rollback_ok"] else "FAIL"
    return out


def fixture_fingerprint(dump: dict[str, Any]) -> str:
    payload = {
        "products": dump["products"],
        "product_types_seed": dump.get("product_types_seed"),
        "brands": dump.get("brands"),
        "categories": dump.get("categories"),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
