#!/usr/bin/env python3
"""Offline logistics package validator. No DB, Postex, or catalog mutation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.logistics import (  # noqa: E402
    read_csv_rows,
    summarize,
    validate_file_rows,
    write_json,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="CSV logistics intake file")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    suffix = args.path.suffix.lower()
    if suffix not in {".csv"}:
        print(
            json.dumps(
                {
                    "error": "unsupported_format",
                    "detail": "Use CSV for validate_logistics_package.py; XLSX via logistics_backfill.py",
                }
            ),
            file=sys.stderr,
        )
        return 2

    rows = read_csv_rows(args.path)
    results = validate_file_rows(rows)
    payload = {
        "path": str(args.path),
        "summary": summarize(results),
        "rows": [r.to_dict() for r in results],
        "mutations": 0,
        "postex_calls": 0,
    }
    summary = {k: v for k, v in payload.items() if k != "rows"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.json_out:
        write_json(args.json_out, payload)
    # Exit 0 even when rows are incomplete — this is a report tool, not an apply gate.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
