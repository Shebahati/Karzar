#!/usr/bin/env python3
"""ADR-012 / data-ingestion-policy fail-closed helpers for catalog scripts.

Category A (default): local API/asset bases only.
Category B (controlled production): requires BOTH
  KARZAR_ALLOW_PRODUCTION_WRITE=1
  KARZAR_INGESTION_CATEGORY=B
and an explicit production-host base (never a silent default).

See docs/architecture/adr/ADR-012-ingestion-boundary-local-vs-production.md
and docs/architecture/data-ingestion-policy.md §6–§7.
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
    """
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


def resolve_api_base(
    *,
    env_var: str = "KARZAR_API_BASE",
    default: str = LOCAL_API_DEFAULT,
) -> str:
    """Resolve ``KARZAR_API_BASE`` (local default) and enforce the production guard."""
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
