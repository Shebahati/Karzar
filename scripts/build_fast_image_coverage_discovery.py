#!/usr/bin/env python3
"""IMG-FAST-01B R2 — Catalog-wide one-image discovery CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.fast_image_coverage_baseline.api_client import require_api_base  # noqa: E402
from scripts.fast_image_coverage_discovery.contracts import DiscoveryError  # noqa: E402
from scripts.fast_image_coverage_discovery.drift import reconcile_storefront_sync  # noqa: E402
from scripts.fast_image_coverage_discovery.orchestrator import run_discovery_r2  # noqa: E402
from scripts.fast_image_coverage_discovery.output import write_package, zip_package  # noqa: E402
from scripts.fast_image_coverage_discovery.seed import (  # noqa: E402
    extract_seed_from_zip,
    load_seed_products,
    write_accepted_seed_manifest,
)

DEFAULT_SEED_ZIP = Path("/home/moahmmad/Projects/Karzar-image-coverage/IMG-FAST-01A.zip")
DEFAULT_PACKAGE = Path("/home/moahmmad/Projects/Karzar-image-coverage/IMG-FAST-01B-R2")
DEFAULT_ZIP = Path("/home/moahmmad/Projects/Karzar-image-coverage/IMG-FAST-01B-R2.zip")
R1_CHECKPOINT = Path("/home/moahmmad/Projects/Karzar-image-coverage/IMG-FAST-01B/checkpoint.json")


def normalize_storefront_api_base(api_base: str) -> str:
    base = require_api_base(api_base).rstrip("/")
    if base.endswith("/api/v1"):
        base = base[: -len("/api/v1")]
    return base


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="IMG-FAST-01B R2 multi-adapter discovery")
    p.add_argument("--api-base", required=True, help="Explicit storefront API base (required)")
    p.add_argument("--seed-zip", type=Path, default=DEFAULT_SEED_ZIP)
    p.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE)
    p.add_argument("--zip-path", type=Path, default=DEFAULT_ZIP)
    p.add_argument("--seed-work-dir", type=Path, default=None)
    p.add_argument("--r1-checkpoint", type=Path, default=R1_CHECKPOINT)
    p.add_argument("--pilot", action="store_true", help="Run operational pilot before full bulk")
    p.add_argument("--pilot-limit", type=int, default=100)
    p.add_argument("--no-resume", action="store_true")
    p.add_argument(
        "--skip-drift",
        action="store_true",
        help="Reuse R1 drift/run-universe CSVs (no live storefront re-scan)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    api_base = normalize_storefront_api_base(args.api_base)
    work_dir = args.seed_work_dir or (args.package_dir / "_seed_extract")
    try:
        seed_csv = extract_seed_from_zip(args.seed_zip, work_dir)
        seed_products = load_seed_products(seed_csv)
        write_accepted_seed_manifest(args.package_dir, zip_path=args.seed_zip, seed_products=seed_products)

        if args.skip_drift:
            # Load from R1 artifact CSVs
            import csv

            from scripts.fast_image_coverage_discovery.contracts import DriftRow, RunProduct

            r1 = Path("/home/moahmmad/Projects/Karzar-image-coverage/IMG-FAST-01B")
            drift_rows = []
            with (r1 / "baseline-to-run-drift.csv").open(encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    drift_rows.append(
                        DriftRow(
                            int(row["product_id"]),
                            row["sku"],
                            row["brand_key"],
                            row["drift_status"],  # type: ignore[arg-type]
                            row.get("notes", ""),
                        )
                    )
            run_universe = []
            with (r1 / "run-universe.csv").open(encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    run_universe.append(
                        RunProduct(
                            int(row["product_id"]),
                            row["sku"],
                            row["brand_key"],
                            row["category_slug"],
                            row["product_name"],
                            row["origin"],
                            row.get("brand_sort_key") or row["brand_key"] or "(none)",
                        )
                    )
            counters = {
                "active_seed_missing": sum(1 for d in drift_rows if d.drift_status == "active_seed_missing"),
                "resolved_since_baseline": sum(1 for d in drift_rows if d.drift_status == "resolved_since_baseline"),
                "removed_since_baseline": sum(1 for d in drift_rows if d.drift_status == "removed_since_baseline"),
                "new_missing_since_baseline": sum(1 for d in drift_rows if d.drift_status == "new_missing_since_baseline"),
            }
        else:
            drift_rows, run_universe, counters = reconcile_storefront_sync(
                api_base=api_base,
                seed_products=seed_products,
            )

        state, metrics = run_discovery_r2(
            api_base=api_base,
            package_dir=args.package_dir,
            run_universe=run_universe,
            seed_manifest_sha256=args.seed_zip.name,
            drift_counters=counters,
            r1_checkpoint=args.r1_checkpoint,
            pilot=args.pilot,
            pilot_limit=args.pilot_limit,
            resume=not args.no_resume,
        )

        if metrics.get("pilot_abort"):
            meta = write_package(
                args.package_dir,
                state=state,
                drift_rows=drift_rows if not args.pilot else [
                    d for d in drift_rows if d.product_id in state.products
                ],
                run_universe=run_universe if not args.pilot else [
                    p for p in run_universe if p.product_id in state.products
                ],
                seed_zip=args.seed_zip,
            )
            (args.package_dir / "r2-metrics.json").write_text(
                json.dumps(metrics, indent=2, default=str), encoding="utf-8"
            )
            zip_sha = zip_package(args.package_dir, args.zip_path)
            print("HALT: pilot abort —", metrics.get("pilot_abort_reason") or "gate failed", file=sys.stderr)
            print(f"metrics: {json.dumps(metrics, default=str)}")
            print(f"zip_sha256: {zip_sha}")
            return 3

        meta = write_package(
            args.package_dir,
            state=state,
            drift_rows=drift_rows,
            run_universe=run_universe if not args.pilot else [p for p in run_universe if p.product_id in state.products],
            seed_zip=args.seed_zip,
        )
        (args.package_dir / "r2-metrics.json").write_text(
            json.dumps({**metrics, **meta.get("summary", {})}, indent=2, default=str),
            encoding="utf-8",
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
