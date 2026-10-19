#!/usr/bin/env python3
"""Read-only storefront publication eligibility metrics (local DB only).

Compares legacy image-gated counts vs current policy (active + not deleted).
Does not write to any database.
"""

from __future__ import annotations

import json
import os
import sys

from sqlalchemy import create_engine, text


def _engine():
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ["POSTGRES_PASSWORD"]
    host = os.environ.get("POSTGRES_SERVER", "127.0.0.1")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "karzar")
    url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
    return create_engine(url)


LEGACY_IMAGE_GATE_SQL = """
SELECT COUNT(*) FROM products p
WHERE p.deleted_at IS NULL AND p.is_active IS TRUE
  AND EXISTS (
    SELECT 1 FROM product_images pi
    WHERE pi.product_id = p.id
      AND pi.image_url IS NOT NULL AND length(trim(pi.image_url)) > 0
      AND pi.image_url NOT ILIKE '%placeholder%'
      AND pi.image_url NOT ILIKE '%woocommerce-placeholder%'
      AND pi.image_url NOT ILIKE '%no-image%'
      AND pi.image_url NOT ILIKE '%no_image%'
      AND pi.image_url NOT ILIKE '%karzar-editorial%'
      AND pi.image_url NOT ILIKE '%/images/placeholders/%'
  );
"""

CURRENT_POLICY_SQL = """
SELECT COUNT(*) FROM products p
WHERE p.deleted_at IS NULL AND p.is_active IS TRUE;
"""

IMAGELESS_ACTIVE_SQL = """
SELECT COUNT(*) FROM products p
WHERE p.deleted_at IS NULL AND p.is_active IS TRUE
  AND NOT EXISTS (
    SELECT 1 FROM product_images pi
    WHERE pi.product_id = p.id
      AND pi.image_url IS NOT NULL AND length(trim(pi.image_url)) > 0
      AND pi.image_url NOT ILIKE '%placeholder%'
      AND pi.image_url NOT ILIKE '%woocommerce-placeholder%'
      AND pi.image_url NOT ILIKE '%no-image%'
      AND pi.image_url NOT ILIKE '%no_image%'
      AND pi.image_url NOT ILIKE '%karzar-editorial%'
      AND pi.image_url NOT ILIKE '%/images/placeholders/%'
  );
"""

INACTIVE_WITH_IMAGE_SQL = """
SELECT COUNT(*) FROM products p
WHERE p.deleted_at IS NULL AND p.is_active IS FALSE
  AND EXISTS (
    SELECT 1 FROM product_images pi
    WHERE pi.product_id = p.id
      AND pi.image_url IS NOT NULL AND length(trim(pi.image_url)) > 0
  );
"""


def main() -> int:
    if "POSTGRES_PASSWORD" not in os.environ:
        print("Set POSTGRES_* env vars for a read-only local snapshot.", file=sys.stderr)
        return 2
    eng = _engine()
    with eng.connect() as conn:
        legacy = int(conn.execute(text(LEGACY_IMAGE_GATE_SQL)).scalar() or 0)
        current = int(conn.execute(text(CURRENT_POLICY_SQL)).scalar() or 0)
        imageless_active = int(conn.execute(text(IMAGELESS_ACTIVE_SQL)).scalar() or 0)
        inactive_imaged = int(conn.execute(text(INACTIVE_WITH_IMAGE_SQL)).scalar() or 0)
    newly_visible = max(0, current - legacy)
    payload = {
        "policy": "2026-10-19-no-mandatory-image",
        "storefront_public_legacy_image_gate": legacy,
        "storefront_public_current_policy": current,
        "newly_visible_solely_due_to_image_policy": newly_visible,
        "active_without_valid_public_image": imageless_active,
        "still_hidden_inactive_despite_image": inactive_imaged,
        "note": (
            "newly_visible is active products that legacy image gate excluded; "
            "inactive_imaged remain blocked by is_active."
        ),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
