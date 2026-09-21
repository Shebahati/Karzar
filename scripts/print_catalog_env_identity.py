#!/usr/bin/env python3
"""Print non-secret catalog / data-plane identity for operators.

Usage:
  python scripts/print_catalog_env_identity.py

Does not print passwords, tokens, or full connection URLs with credentials.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.data_plane import (  # noqa: E402
    format_identity_report,
    identity_from_mapping,
)


def main() -> int:
    try:
        identity = identity_from_mapping(os.environ)
    except ValueError as exc:
        print(f"FATAL: data-plane identity invalid — {exc}", file=sys.stderr)
        return 2
    print(format_identity_report(identity))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
