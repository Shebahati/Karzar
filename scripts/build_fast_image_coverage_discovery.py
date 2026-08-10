#!/usr/bin/env python3
"""IMG-FAST-01B — Catalog-wide one-image discovery CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.fast_image_coverage_baseline.api_client import require_api_base  # noqa: E402
from scripts.fast_image_coverage_discovery.contracts import DiscoveryError  # noqa: E402
from scripts.fast_image_coverage_discovery.drift import reconcile_storefront_sync  # noqa: E402
from scripts.fast_image_coverage_discovery.orchestrator import run_discovery  # noqa: E402
from scripts.fast_image_coverage_discovery.output import write_package, zip_package  # noqa: E402
from scripts.fast_image_coverage_discovery.seed import (  # noqa: E402
    extract_seed_from_zip,
    load_seed_products,
    write_accepted_seed_manifest,
)

DEFAULT_SEED_ZIP = Path("/home/moahmmad/Projects/Karzar-image-coverage/IMG-FAST-01A.zip")
DEFAULT_PACKAGE = Path("/home/moahmmad/Projects/Karzar-image-coverage/IMG-FAST-01B")
DEFAULT_ZIP = Path("/home/moahmmad/Projects/Karzar-image-coverage/IMG-FAST-01B.zip")


def normalize_storefront_api_base(api_base: str) -> str:
    """Accept host root or .../api/v1; canonical paths include /api/v1/."""
    base = require_api_base(api_base).rstrip("/")
    if base.endswith("/api/v1"):
        base = base[: -len("/api/v1")]
    return base


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="IMG-FAST-01B catalog-wide one-image discovery")
    p.add_argument("--api-base", required=True, help="Explicit storefront API base (required)")
    p.add_argument("--seed-zip", type=Path, default=DEFAULT_SEED_ZIP)
    p.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE)
    p.add_argument("--zip-path", type=Path, default=DEFAULT_ZIP)
    p.add_argument("--seed-work-dir", type=Path, default=None, help="Temp extract dir for seed artifact")
    p.add_argument("--no-resume", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    api_base = normalize_storefront_api_base(args.api_base)
    work_dir = args.seed_work_dir or (args.package_dir / "_seed_extract")
    try:
        seed_csv = extract_seed_from_zip(args.seed_zip, work_dir)
        seed_products = load_seed_products(seed_csv)
        write_accepted_seed_manifest(args.package_dir, zip_path=args.seed_zip, seed_products=seed_products)
        drift_rows, run_universe, counters = reconcile_storefront_sync(
            api_base=api_base,
            seed_products=seed_products,
        )
        state = run_discovery(
            api_base=api_base,
            package_dir=args.package_dir,
            run_universe=run_universe,
            seed_manifest_sha256=args.seed_zip.name,
            drift_counters=counters,
            resume=not args.no_resume,
        )
        meta = write_package(
            args.package_dir,
            state=state,
            drift_rows=drift_rows,
            run_universe=run_universe,
            seed_zip=args.seed_zip,
        )
        zip_sha = zip_package(args.package_dir, args.zip_path)
        print(f"summary: {meta['summary']}")
        print(f"zip_sha256: {zip_sha}")
        return 0
    except DiscoveryError as exc:
        print(f"HALT {exc.code}: {exc.detail}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
