#!/usr/bin/env python3
"""Dry-run / local-only apply of remediated ShopMill assets into product storage.

Does NOT talk to production. Requires an explicit --storage-root under a local
checkout (typically <repo>/data/uploads/products) and writes files only.

DB ProductImage URL updates are intentionally out of scope here (ADR-012 /
HC-09). When storage already serves /static/uploads/products/{relpath},
replacing the file bytes at the mapped relative path is sufficient if the URL
path is unchanged.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="remediation-manifest.csv from IMG-SHOPMILL-WATERMARK-CLEANUP",
    )
    p.add_argument(
        "--storage-root",
        type=Path,
        required=True,
        help="Local product uploads root (e.g. data/uploads/products)",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Actually copy files (default: dry-run)",
    )
    args = p.parse_args(argv)

    storage = args.storage_root.resolve()
    if not storage.is_dir():
        print(f"storage-root missing: {storage}", file=sys.stderr)
        return 2

    rows = list(csv.DictReader(args.manifest.open(encoding="utf-8")))
    # unique by mapped path
    plans = {}
    for row in rows:
        if str(row.get("remediation_ok")).lower() not in {"1", "true"}:
            continue
        rel = (row.get("mapped_local_relative_path") or "").strip()
        src = Path(row.get("output_path") or "")
        if not rel or not src.is_file():
            continue
        plans[rel] = src

    print(f"planned_unique_paths={len(plans)} apply={args.apply}")
    for rel, src in sorted(plans.items()):
        dest = storage / rel
        print(f"{'COPY' if args.apply else 'DRY'} {src} -> {dest}")
        if args.apply:
            dest.parent.mkdir(parents=True, exist_ok=True)
            # backup original if present
            if dest.is_file():
                bak = dest.with_suffix(dest.suffix + ".shopmill-bak")
                if not bak.exists():
                    shutil.copy2(dest, bak)
            shutil.copy2(src, dest)
            print(f"  sha256={_sha256(dest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
