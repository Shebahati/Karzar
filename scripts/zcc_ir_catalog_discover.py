#!/usr/bin/env python3
"""READ-ONLY zcc.ir catalog discovery and Karzar reconciliation (Phase 1).

Does not create, update, or delete Karzar products. There is no APPLY path.

Usage:
  KARZAR_API_BASE=<http(s) origin or /api/v1 base> python3 scripts/zcc_ir_catalog_discover.py
  python3 scripts/zcc_ir_catalog_discover.py --output-dir data/zcc_ir --sleep 0.8
  python3 scripts/zcc_ir_catalog_discover.py --skip-karzar-public --karzar-products-json snapshot.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

FORBIDDEN = {"--apply", "--write", "--write-db", "--mutate", "--production-apply"}

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from zcc_ir_catalog.karzar_snapshot import (  # noqa: E402
    KarzarApiBaseError,
    resolve_karzar_public_origin,
)
from zcc_ir_catalog.pipeline import run_phase1  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    hit = [flag for flag in FORBIDDEN if flag in raw]
    if hit:
        print(
            "FATAL: zcc.ir Phase 1 is READ-ONLY. Forbidden flag(s): "
            + ", ".join(hit)
            + ". No APPLY / catalog writer exists in this tool.",
            file=sys.stderr,
        )
        return 2

    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="READ-ONLY zcc.ir catalog discovery (Phase 1). No production writes."
    )
    parser.add_argument(
        "--output-dir",
        default=str(root / "data" / "zcc_ir"),
        help="Artifact directory (default data/zcc_ir, gitignored via /data/)",
    )
    parser.add_argument(
        "--cache-dir",
        default=None,
        help="HTTP cache directory (default: <output-dir>/http_cache)",
    )
    parser.add_argument("--sleep", type=float, default=0.8, help="Seconds between live requests")
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--limit", type=int, default=None, help="Max product pages (debug)")
    parser.add_argument(
        "--skip-listings",
        action="store_true",
        help="Use product sitemap only; skip tag/category listing pagination",
    )
    parser.add_argument(
        "--skip-karzar-public",
        action="store_true",
        help="Do not GET the public Karzar HTTP API; reconcile only if a snapshot is provided",
    )
    parser.add_argument(
        "--karzar-api-base",
        default=None,
        help=(
            "Public Karzar API origin or /api/v1 base for GET-only snapshot. "
            "Overrides KARZAR_API_BASE. Required only when fetching the public catalog."
        ),
    )
    parser.add_argument("--snapshot", default=None, help="READ-ONLY current-catalog CSV")
    parser.add_argument(
        "--karzar-products-json",
        default=None,
        help="READ-ONLY public product list JSON (array or {data: []})",
    )
    parser.add_argument(
        "--read-db",
        action="store_true",
        help="Local READ-ONLY DB snapshot via catalog_target (production hosts refused)",
    )
    args = parser.parse_args(raw)

    need_public = (not args.skip_karzar_public) and not (
        args.snapshot or args.karzar_products_json or args.read_db
    )
    if need_public:
        try:
            resolve_karzar_public_origin(args.karzar_api_base)
        except KarzarApiBaseError as exc:
            print(f"FATAL: {exc}", file=sys.stderr)
            return 2

    output_dir = Path(args.output_dir)
    cache_dir = Path(args.cache_dir) if args.cache_dir else output_dir / "http_cache"
    result = run_phase1(
        output_dir=output_dir,
        cache_dir=cache_dir,
        sleep_s=args.sleep,
        timeout_s=args.timeout,
        retries=args.retries,
        limit=args.limit,
        include_listings=not args.skip_listings,
        fetch_karzar_public=not args.skip_karzar_public,
        snapshot_csv=args.snapshot,
        products_json=args.karzar_products_json,
        read_db=args.read_db,
        karzar_api_base=args.karzar_api_base,
    )
    summary = result["summary"]
    print(
        "PHASE1_DONE "
        f"products={summary.get('total_products')} "
        f"failures={summary.get('crawl_failures')} "
        f"create={summary.get('create_candidates')} "
        f"mutation={summary.get('production_db_mutation')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
