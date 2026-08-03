#!/usr/bin/env python3
"""CLI for governed multi-brand product image discovery (IMG-01B)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from image_discovery.consolidation import consolidate_batches  # noqa: E402
from image_discovery.core import run_discovery  # noqa: E402
from image_discovery.sources import get_adapter  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def _validate_run_args(args: argparse.Namespace) -> None:
    if args.max_images_per_product <= 0:
        raise SystemExit("ERROR: --max-images-per-product must be > 0 (invalid values are not coerced)")
    if args.concurrency <= 0:
        raise SystemExit("ERROR: --concurrency must be > 0")
    if args.delay < 0:
        raise SystemExit("ERROR: --delay must be >= 0")
    if args.limit is not None and args.limit < 0:
        raise SystemExit("ERROR: --limit must be >= 0")
    if args.offset < 0:
        raise SystemExit("ERROR: --offset must be >= 0")
    if args.force_refetch and not args.resume:
        # force-refetch alone: refetch network; comparison without previous is fine
        pass


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0].startswith("-"):
        argv = ["run", *argv]
    elif not argv:
        argv = ["run", "--help"]

    p = argparse.ArgumentParser(description="Governed product image discovery (generic engine)")
    sub = p.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Validate candidates and materialize assets")
    run_p.add_argument("--source", required=True, help="Adapter name, e.g. insize_tosag")
    run_p.add_argument("--products-csv", type=Path, default=None)
    run_p.add_argument("--candidates-csv", type=Path, default=None)
    run_p.add_argument("--output-dir", type=Path, required=True)
    run_p.add_argument("--sku", action="append", default=None)
    run_p.add_argument("--limit", type=int, default=None)
    run_p.add_argument("--offset", type=int, default=0)
    run_p.add_argument("--concurrency", type=int, default=2)
    run_p.add_argument("--delay", type=float, default=0.5)
    run_p.add_argument("--resume", action="store_true", help="Reuse governed previous Manifest/state")
    run_p.add_argument(
        "--force-refetch",
        action="store_true",
        help="Refetch network assets; with --resume may still compare to previous immutable state",
    )
    run_p.add_argument("--max-images-per-product", type=int, default=1)

    cons = sub.add_parser("consolidate", help="Globally reclassify batch outputs")
    cons.add_argument("--input-dir", type=Path, required=True)
    cons.add_argument("--output-dir", type=Path, required=True)
    cons.add_argument(
        "--allow-replace",
        action="store_true",
        help="Explicitly allow writing into a non-empty consolidate output",
    )

    args = p.parse_args(argv)

    if args.command == "consolidate":
        summary = consolidate_batches(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            repo_root=REPO_ROOT,
            allow_replace=args.allow_replace,
        )
    else:
        _validate_run_args(args)
        adapter = get_adapter(args.source)
        summary = run_discovery(
            adapter=adapter,
            products_csv=args.products_csv,
            candidates_csv=args.candidates_csv,
            output_dir=args.output_dir,
            repo_root=REPO_ROOT,
            sku_filters=args.sku,
            limit=args.limit,
            offset=args.offset,
            concurrency=args.concurrency,
            delay=args.delay,
            resume=args.resume,
            force_refetch=args.force_refetch,
            max_images_per_product=args.max_images_per_product,
        )

    keys = [
        "requested_rows",
        "accepted_rows",
        "rejected_rows",
        "downloaded_unique_assets",
        "reused_existing_assets",
        "unique_assets",
        "family_rows",
        "singleton_unverified_rows",
        "cross_brand_duplicate_rows",
        "manifest_semantic_sha256",
        "semantic_manifest_stable",
        "asset_set_stable",
        "stale_unreferenced_files",
        "missing_referenced_files",
        "unexpected_symlinks",
        "duplicate_physical_asset_groups",
        "duplicate_physical_asset_files",
    ]
    print(json.dumps({k: summary[k] for k in keys if k in summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
