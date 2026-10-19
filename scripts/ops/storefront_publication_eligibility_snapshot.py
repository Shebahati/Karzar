#!/usr/bin/env python3
"""Read-only storefront publication eligibility metrics (local DB only).

Compares legacy image-gated counts vs current policy (active + not deleted).
Uses asyncpg (see requirements.txt). Does not write to any database.
Credentials are read from env only (never printed).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED_DRIVER = "asyncpg==0.29.0"


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"Set {name} for a read-only local snapshot.", file=sys.stderr)
        raise SystemExit(2)
    return value


def normalize_database_url(url: str) -> str:
    """Strip SQLAlchemy driver suffixes for asyncpg.connect()."""
    for prefix in ("postgresql+asyncpg://", "postgres+asyncpg://", "postgresql+psycopg://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix) :]
    return url


def build_database_url_from_env() -> str:
    user = quote_plus(os.environ.get("POSTGRES_USER", "postgres"))
    password = quote_plus(_require_env("POSTGRES_PASSWORD"))
    host = os.environ.get("POSTGRES_SERVER", "127.0.0.1")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = quote_plus(os.environ.get("POSTGRES_DB", "karzar"))
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def _legacy_exists_subquery() -> str:
    from app.utils.public_catalog import legacy_public_image_gate_sql_conditions

    img = legacy_public_image_gate_sql_conditions("pi")
    return f"""
    EXISTS (
      SELECT 1 FROM product_images pi
      WHERE pi.product_id = p.id AND {img}
    )
"""


def snapshot_sql_queries() -> dict[str, str]:
    legacy_exists = _legacy_exists_subquery()
    return {
        "legacy": f"""
SELECT COUNT(*)::bigint FROM products p
WHERE p.deleted_at IS NULL AND p.is_active IS TRUE
  AND {legacy_exists};
""",
        "current": """
SELECT COUNT(*)::bigint FROM products p
WHERE p.deleted_at IS NULL AND p.is_active IS TRUE;
""",
        "imageless_active": f"""
SELECT COUNT(*)::bigint FROM products p
WHERE p.deleted_at IS NULL AND p.is_active IS TRUE
  AND NOT ({legacy_exists});
""",
        "inactive_imaged": """
SELECT COUNT(*)::bigint FROM products p
WHERE p.deleted_at IS NULL AND p.is_active IS FALSE
  AND EXISTS (
    SELECT 1 FROM product_images pi
    WHERE pi.product_id = p.id
      AND pi.image_url IS NOT NULL AND length(trim(pi.image_url)) > 0
  );
""",
    }


def evaluate_snapshot_identity(
    *,
    legacy: int,
    current: int,
    imageless_active: int,
) -> bool:
    """Active public set partitions into legacy-gated + imageless-active."""
    return current == legacy + imageless_active


def build_snapshot_payload(
    counts: dict[str, int],
    *,
    transaction_read_only: str,
) -> dict[str, object]:
    legacy = int(counts["legacy"])
    current = int(counts["current"])
    imageless_active = int(counts["imageless_active"])
    inactive_imaged = int(counts["inactive_imaged"])
    newly_visible = current - legacy
    identity_ok = evaluate_snapshot_identity(
        legacy=legacy,
        current=current,
        imageless_active=imageless_active,
    )
    return {
        "policy": "2026-10-19-no-mandatory-image",
        "driver": "asyncpg",
        "transaction_isolation": "repeatable_read",
        "transaction_read_only": transaction_read_only,
        "storefront_public_legacy_image_gate": legacy,
        "storefront_public_current_policy": current,
        "newly_visible_solely_due_to_image_policy": newly_visible,
        "active_without_valid_public_image": imageless_active,
        "still_hidden_inactive_despite_image": inactive_imaged,
        "identity_check_current_equals_legacy_plus_imageless_active": identity_ok,
        "note": (
            "Legacy gate uses PLACEHOLDER_ILIKE_TOKENS from public_catalog; "
            "current policy is active + not deleted only."
        ),
    }


async def collect_readonly_counts(database_url: str) -> tuple[dict[str, int], str]:
    """Open one REPEATABLE READ READ ONLY transaction and run all snapshot SELECTs."""
    try:
        import asyncpg
    except ImportError as exc:
        print(
            f"FATAL: asyncpg required ({REQUIRED_DRIVER}). Install requirements.txt.",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc

    queries = snapshot_sql_queries()
    conn = await asyncpg.connect(normalize_database_url(database_url))
    try:
        async with conn.transaction(isolation="repeatable_read", readonly=True):
            tro = await conn.fetchval("SHOW transaction_read_only")
            tro_norm = str(tro).strip().lower()
            if tro_norm != "on":
                raise RuntimeError(
                    f"transaction_read_only={tro!r} (expected on) — aborting snapshot"
                )
            counts = {
                key: int(await conn.fetchval(sql) or 0) for key, sql in queries.items()
            }
            return counts, tro_norm
    finally:
        await conn.close()


async def run_snapshot_async(database_url: str) -> dict[str, object]:
    counts, tro = await collect_readonly_counts(database_url)
    return build_snapshot_payload(counts, transaction_read_only=tro)


def main() -> int:
    try:
        database_url = build_database_url_from_env()
    except SystemExit as exc:
        return int(exc.code or 2)
    payload = asyncio.run(run_snapshot_async(database_url))
    print(json.dumps(payload, indent=2))
    identity_ok = bool(payload["identity_check_current_equals_legacy_plus_imageless_active"])
    return 0 if identity_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
