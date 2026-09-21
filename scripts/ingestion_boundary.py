#!/usr/bin/env python3
"""ADR-012 / data-ingestion-policy fail-closed helpers for catalog scripts.

Category A (default): local API/asset bases only.
Category B (controlled production): requires BOTH
  KARZAR_ALLOW_PRODUCTION_WRITE=1
  KARZAR_INGESTION_CATEGORY=B
and an explicit production-host base (never a silent default).

Data-plane isolation (CATALOG_STAGING_ISOLATION):
  When ``KARZAR_DATA_PLANE=catalog_staging``, production API hosts are always
  refused (even with Category B). Direct DB writers should call
  ``assert_data_plane_destination`` / ``assert_catalog_mutate_destination``.

See docs/architecture/adr/ADR-012-ingestion-boundary-local-vs-production.md,
docs/architecture/data-ingestion-policy.md §6–§7, and
docs/CATALOG_STAGING_ISOLATION.md.
"""

from __future__ import annotations

import os
import sys
from urllib.parse import urlparse

PROD_HOST_MARKER = "karzartools.com"
ALLOW_ENV = "KARZAR_ALLOW_PRODUCTION_WRITE"
CATEGORY_ENV = "KARZAR_INGESTION_CATEGORY"
LOCAL_API_DEFAULT = "http://127.0.0.1:8000/api/v1"
LOCAL_ASSET_DEFAULT = "http://127.0.0.1:8000"


def is_production_base(url: str) -> bool:
    """True when the URL host is (or is under) the live karzartools.com domain."""
    host = (urlparse(url).hostname or "").lower()
    return PROD_HOST_MARKER in host


def assert_destination_allowed(url: str, *, label: str = "destination") -> None:
    """Abort if *url* targets production without Category B opt-in.

    Local / non-production hosts always pass. Production requires:
    - ``KARZAR_ALLOW_PRODUCTION_WRITE=1``
    - ``KARZAR_INGESTION_CATEGORY=B``

    Catalog-staging data plane never targets production hosts.
    """
    plane = os.getenv("KARZAR_DATA_PLANE", "").strip().lower()
    if plane == "catalog_staging" and is_production_base(url):
        print(
            f"FATAL (data-plane fail-closed): {label} targets production ({url}) "
            "while KARZAR_DATA_PLANE=catalog_staging. Use the isolated catalog-staging "
            "API base (e.g. http://127.0.0.1:8010/api/v1).",
            file=sys.stderr,
        )
        raise SystemExit(2)

    if not is_production_base(url):
        return

    allow = os.getenv(ALLOW_ENV, "").strip()
    category = os.getenv(CATEGORY_ENV, "").strip().upper()
    errors: list[str] = []
    if allow != "1":
        errors.append(f"set {ALLOW_ENV}=1")
    if category != "B":
        errors.append(f"set {CATEGORY_ENV}=B (controlled production import)")
    if not errors:
        return

    print(
        f"FATAL (ADR-012 fail-closed): {label} targets production ({url}) "
        f"but Category B controls are incomplete — {'; '.join(errors)}. "
        f"Category A work must use a local base (default {LOCAL_API_DEFAULT}). "
        f"See data-ingestion-policy.md §6 Category B.",
        file=sys.stderr,
    )
    raise SystemExit(2)


def assert_data_plane_destination() -> None:
    """Validate POSTGRES_* / KARZAR_DATA_PLANE consistency (fail closed)."""
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)
    from app.core.data_plane import identity_from_mapping

    try:
        identity_from_mapping(os.environ)
    except ValueError as exc:
        print(f"FATAL (data-plane): {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def assert_catalog_mutate_destination(*, allow_live: bool = False) -> None:
    """Fail closed for catalog APPLY unless plane is non-live (or allow_live)."""
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)
    from app.core.data_plane import assert_catalog_mutate_allowed, identity_from_mapping

    try:
        identity = identity_from_mapping(os.environ)
        assert_catalog_mutate_allowed(identity, allow_live_catalog_writes=allow_live)
    except ValueError as exc:
        print(f"FATAL (catalog mutate): {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def resolve_api_base(
    *,
    env_var: str = "KARZAR_API_BASE",
    default: str = LOCAL_API_DEFAULT,
    require_data_plane: bool | None = None,
) -> str:
    """Resolve ``KARZAR_API_BASE`` (local default) and enforce the production guard.

    When ``KARZAR_DATA_PLANE`` is set (or ``require_data_plane=True``), also
    validate PostgreSQL data-plane identity if ``POSTGRES_DB`` is present.
    """
    if require_data_plane is None:
        require_data_plane = bool(os.getenv("KARZAR_DATA_PLANE", "").strip()) or bool(
            os.getenv("POSTGRES_DB", "").strip()
            and os.getenv("KARZAR_REQUIRE_DATA_PLANE", "").strip() in {"1", "true", "yes"}
        )
    if require_data_plane and os.getenv("POSTGRES_DB", "").strip():
        assert_data_plane_destination()

    base = os.getenv(env_var, default).rstrip("/")
    assert_destination_allowed(base, label=env_var)
    return base


def resolve_asset_base(
    *,
    env_var: str = "PUBLIC_ASSET_BASE",
    default: str = LOCAL_ASSET_DEFAULT,
) -> str:
    """Resolve ``PUBLIC_ASSET_BASE`` (local default) and enforce the production guard."""
    base = os.getenv(env_var, default).rstrip("/")
    assert_destination_allowed(base, label=env_var)
    return base
