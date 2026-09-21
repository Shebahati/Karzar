#!/usr/bin/env python3
"""Fail closed unless the process env matches the expected data plane.

Usage:
  python scripts/assert_catalog_data_plane.py --expect catalog_staging
  python scripts/assert_catalog_data_plane.py --expect catalog_staging --allow-mutate

Exit codes:
  0 — identity matches expectation
  2 — fail-closed (wrong plane / live DB contradiction / mutate refused)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.data_plane import (  # noqa: E402
    assert_catalog_mutate_allowed,
    format_identity_report,
    identity_from_mapping,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expect",
        required=True,
        choices=("live", "catalog_staging", "development"),
        help="Required KARZAR_DATA_PLANE (after inference)",
    )
    parser.add_argument(
        "--allow-mutate",
        action="store_true",
        help="Also enforce catalog-mutate eligibility for the resolved plane",
    )
    parser.add_argument(
        "--allow-live-catalog-writes",
        action="store_true",
        help="Permit mutate when plane is live (still subject to ADR-012 for API hosts)",
    )
    args = parser.parse_args(argv)

    try:
        identity = identity_from_mapping(os.environ)
    except ValueError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 2

    print(format_identity_report(identity))

    if identity.data_plane != args.expect:
        print(
            f"FATAL: expected data plane {args.expect!r}, got {identity.data_plane!r} "
            f"(DB={identity.postgres_db!r}).",
            file=sys.stderr,
        )
        return 2

    if args.allow_mutate:
        try:
            assert_catalog_mutate_allowed(
                identity,
                allow_live_catalog_writes=args.allow_live_catalog_writes,
            )
        except ValueError as exc:
            print(f"FATAL: {exc}", file=sys.stderr)
            return 2

    print(f"OK: data plane is {identity.data_plane!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
