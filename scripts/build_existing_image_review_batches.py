#!/usr/bin/env python3
"""IMG-02A-02 — Build offline human-review batches / Pilot 001 (no DB, no network)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.image_review.contracts import (  # noqa: E402
    AUTHORITATIVE_CHECKSUMS_DIGEST,
    PILOT_BATCH_ID,
    ReviewError,
)
from scripts.image_review.pipeline import (  # noqa: E402
    build_pilot_package,
    semantic_compare_summaries,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Build deterministic offline human-review package for existing product images."
    )
    p.add_argument("--source-dir", required=True, type=Path, help="Verified IMG-02A-01 output dir")
    p.add_argument("--storage-root", required=True, type=Path, help="Read-only product uploads root")
    p.add_argument("--output-dir", required=True, type=Path, help="Empty absolute dir outside repo/storage")
    p.add_argument("--batch-id", default=PILOT_BATCH_ID)
    p.add_argument(
        "--expected-checksums-digest",
        default=AUTHORITATIVE_CHECKSUMS_DIGEST,
        help="SHA-256 of source checksums.sha256",
    )
    p.add_argument("--zip-path", type=Path, default=None, help="Optional absolute ZIP output path")
    p.add_argument(
        "--compare-with-summary",
        type=Path,
        default=None,
        help="Optional prior summary.json for semantic stability check",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = build_pilot_package(
            source_dir=args.source_dir,
            storage_root=args.storage_root,
            output_dir=args.output_dir,
            repository_root=REPO_ROOT,
            batch_id=args.batch_id,
            expected_checksums_digest=args.expected_checksums_digest,
            zip_path=args.zip_path,
        )
        if args.compare_with_summary is not None:
            prior = json.loads(args.compare_with_summary.read_text(encoding="utf-8"))
            semantic_compare_summaries(prior, result)
            result["semantic_second_run_stable"] = True
        print(json.dumps({k: result[k] for k in sorted(result) if k != "selected_asset_ids"}, ensure_ascii=False, indent=2))
        print(f"selected_unique_assets={result['selected_unique_assets']}")
        return 0
    except ReviewError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
