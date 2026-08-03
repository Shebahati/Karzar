#!/usr/bin/env python3
"""Deprecated shim — use scripts/discover_product_images.py run --source insize_tosag."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))

from discover_product_images import main as _main  # noqa: E402


def main() -> int:
    print(
        "WARNING: discover_insize_product_images.py is a shim; "
        "prefer: discover_product_images.py run --source insize_tosag ...",
        file=sys.stderr,
    )
    argv = list(sys.argv[1:])
    # Map legacy flags to new CLI
    if "--source" not in argv:
        argv = ["run", "--source", "insize_tosag", *argv]
    elif argv and not argv[0].startswith("-") and argv[0] != "run":
        pass
    elif argv and argv[0].startswith("-"):
        argv = ["run", *argv]
    return _main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
