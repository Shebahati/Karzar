#!/usr/bin/env python3
"""Rebuild SOURCE_AUTHORITY_REGISTRY.csv from local OEM documents (read-only).

Does not mutate source PDFs, database, or catalog. Re-running on unchanged inputs
must yield an identical registry (sorted rows, stable columns).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.domain.phase2c_evidence import REGISTRY_FIELDNAMES  # noqa: E402
from scripts.phase2c_authority_extract import (  # noqa: E402
    DEFAULT_PRODUCT_DATA_ROOT,
    build_all_extractions,
    sha256_file,
)

DEFAULT_OUT = ROOT / "audit" / "product-naming-phase2c-discovery"
SOURCE_MANIFEST_NAME = "SOURCE_HASH_MANIFEST.json"


def _reject_apply(argv: list[str]) -> None:
    if any(a == "--apply" or a.startswith("--apply=") for a in argv):
        print("ERROR: --apply is rejected. Registry build is READ-ONLY.", file=sys.stderr)
        raise SystemExit(2)


def _canonical_row_sort_key(row: dict[str, str]) -> tuple[str, ...]:
    return (
        row.get("brand", ""),
        row.get("normalized_match_key", ""),
        row.get("source_id", ""),
        row.get("source_page_index", ""),
        row.get("source_row", ""),
        row.get("raw_source_code", ""),
    )


def write_registry(path: Path, rows: list[dict[str, str]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    sorted_rows = sorted(rows, key=_canonical_row_sort_key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=REGISTRY_FIELDNAMES, extrasaction="ignore")
        w.writeheader()
        for row in sorted_rows:
            w.writerow({k: row.get(k, "") for k in REGISTRY_FIELDNAMES})
    return sha256_file(path)


def build_source_hash_manifest(rows: list[dict[str, str]]) -> dict[str, str]:
    paths = sorted({r.get("source_path", "") for r in rows if r.get("source_path")})
    manifest: dict[str, str] = {}
    for p in paths:
        fp = Path(p)
        if fp.is_file():
            manifest[p] = sha256_file(fp)
    return manifest


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    _reject_apply(argv)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--product-data-root",
        type=Path,
        default=DEFAULT_PRODUCT_DATA_ROOT,
        help="Local Product and Data Complete root (hp-g2-450)",
    )
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = p.parse_args(argv)

    if not args.product_data_root.is_dir():
        print(f"ERROR: product data root missing: {args.product_data_root}", file=sys.stderr)
        return 2

    extracted = build_all_extractions(args.product_data_root)
    registry_path = args.out_dir / "SOURCE_AUTHORITY_REGISTRY.csv"
    digest = write_registry(registry_path, extracted)
    manifest = build_source_hash_manifest(extracted)
    manifest_path = args.out_dir / SOURCE_MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "source_files": manifest,
                "registry_sha256": digest,
                "registry_rows": len(extracted),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "registry_path": str(registry_path),
                "rows": len(extracted),
                "sha256": digest,
                "source_hash_manifest": str(manifest_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
