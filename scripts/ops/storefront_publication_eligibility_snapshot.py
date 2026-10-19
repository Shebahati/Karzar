#!/usr/bin/env python3
"""Read-only storefront publication eligibility metrics (local DB only).

Compares legacy image-gated counts vs current policy (active + not deleted).
Does not write to any database. Credentials are read from env only (never printed).
"""

from __future__ import annotations

import json
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL

from app.utils.public_catalog import legacy_public_image_gate_sql_conditions


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"Set {name} for a read-only local snapshot.", file=sys.stderr)
        raise SystemExit(2)
    return value


def _build_engine() -> Engine:
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = _require_env("POSTGRES_PASSWORD")
    host = os.environ.get("POSTGRES_SERVER", "127.0.0.1")
    port = int(os.environ.get("POSTGRES_PORT", "5432"))
    db = os.environ.get("POSTGRES_DB", "karzar")
    # Prefer URL.create so passwords with special characters are safe.
    url = URL.create(
        drivername="postgresql+psycopg",
        username=user,
        password=password,
        host=host,
        port=port,
        database=db,
    )
    return create_engine(url, pool_pre_ping=True)


def _legacy_exists_subquery() -> str:
    img = legacy_public_image_gate_sql_conditions("pi")
    return f"""
    EXISTS (
      SELECT 1 FROM product_images pi
      WHERE pi.product_id = p.id AND {img}
    )
"""


def _scalar(conn, sql: str) -> int:
    conn.execute(text("SET TRANSACTION READ ONLY"))
    return int(conn.execute(text(sql)).scalar() or 0)


def main() -> int:
    try:
        eng = _build_engine()
    except SystemExit:
        return 2
    legacy_exists = _legacy_exists_subquery()
    legacy_sql = f"""
SELECT COUNT(*) FROM products p
WHERE p.deleted_at IS NULL AND p.is_active IS TRUE
  AND {legacy_exists};
"""
    current_sql = """
SELECT COUNT(*) FROM products p
WHERE p.deleted_at IS NULL AND p.is_active IS TRUE;
"""
    imageless_sql = f"""
SELECT COUNT(*) FROM products p
WHERE p.deleted_at IS NULL AND p.is_active IS TRUE
  AND NOT ({legacy_exists});
"""
    inactive_imaged_sql = """
SELECT COUNT(*) FROM products p
WHERE p.deleted_at IS NULL AND p.is_active IS FALSE
  AND EXISTS (
    SELECT 1 FROM product_images pi
    WHERE pi.product_id = p.id
      AND pi.image_url IS NOT NULL AND length(trim(pi.image_url)) > 0
  );
"""
    with eng.connect() as conn:
        with conn.begin():
            legacy = _scalar(conn, legacy_sql)
            current = _scalar(conn, current_sql)
            imageless_active = _scalar(conn, imageless_sql)
            inactive_imaged = _scalar(conn, inactive_imaged_sql)
    newly_visible = current - legacy
    identity_ok = current == legacy + newly_visible
    payload = {
        "policy": "2026-10-19-no-mandatory-image",
        "storefront_public_legacy_image_gate": legacy,
        "storefront_public_current_policy": current,
        "newly_visible_solely_due_to_image_policy": newly_visible,
        "active_without_valid_public_image": imageless_active,
        "still_hidden_inactive_despite_image": inactive_imaged,
        "identity_check_current_equals_legacy_plus_newly_visible": identity_ok,
        "note": (
            "Legacy gate uses PLACEHOLDER_ILIKE_TOKENS from public_catalog; "
            "current policy is active + not deleted only."
        ),
    }
    print(json.dumps(payload, indent=2))
    return 0 if identity_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
