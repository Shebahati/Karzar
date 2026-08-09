#!/usr/bin/env python3
"""IMG-FAST-01A — Live public storefront Fast Coverage baseline CLI."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.fast_image_coverage_baseline.api_client import DEFAULT_API_BASE  # noqa: E402
from scripts.fast_image_coverage_baseline.contracts import BaselineError  # noqa: E402
from scripts.fast_image_coverage_baseline.output import (  # noqa: E402
    build_summary,
    verify_checksums,
    write_artifact_package,
    zip_package,
)
from scripts.fast_image_coverage_baseline.scan import run_scan  # noqa: E402
from scripts.fast_image_coverage_baseline.stability import compare_runs  # noqa: E402

DEFAULT_PACKAGE = Path("/home/moahmmad/Projects/Karzar-image-coverage/IMG-FAST-01A")
DEFAULT_ZIP = Path("/home/moahmmad/Projects/Karzar-image-coverage/IMG-FAST-01A.zip")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="IMG-FAST-01A live storefront image baseline")
    p.add_argument("--api-base", default=DEFAULT_API_BASE)
    p.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE)
    p.add_argument("--zip-path", type=Path, default=DEFAULT_ZIP)
    p.add_argument(
        "--work-root",
        type=Path,
        default=Path("/var/tmp/karzar-img-fast-01a"),
        help="Disposable run directories for cache + two-run comparison",
    )
    p.add_argument("--page-size", type=int, default=1000)
    p.add_argument("--api-concurrency", type=int, default=4)
    p.add_argument("--asset-concurrency", type=int, default=8)
    p.add_argument("--per-host-concurrency", type=int, default=6)
    p.add_argument("--timeout", type=float, default=20.0)
    p.add_argument("--retries", type=int, default=2)
    p.add_argument("--single-run", action="store_true", help="Skip second run (debug)")
    return p


async def _amain(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    work_root: Path = args.work_root
    work_root.mkdir(parents=True, exist_ok=True)
    # Unique sibling dirs so a killed mid-flight run can still be resumed separately.
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run1_dir = work_root / f"run1-{stamp}"
    run2_dir = work_root / f"run2-{stamp}"
    run1_dir.mkdir(parents=True, exist_ok=False)
    run2_dir.mkdir(parents=True, exist_ok=False)

    common = dict(
        api_base=args.api_base,
        page_size=args.page_size,
        api_concurrency=args.api_concurrency,
        asset_concurrency=args.asset_concurrency,
        per_host_concurrency=args.per_host_concurrency,
        timeout_s=args.timeout,
        retries=args.retries,
        resume=True,
    )

    print("=== RUN 1 ===", flush=True)
    scan1 = await run_scan(output_run_dir=run1_dir, **common)
    print(f"catalog_total={scan1.catalog_total}", flush=True)
    print(json.dumps(scan1.counters.to_dict()), flush=True)

    drift_rows: list[dict] = []
    stable: bool | None = None
    final_scan = scan1

    if not args.single_run:
        print("=== RUN 2 ===", flush=True)
        scan2 = await run_scan(output_run_dir=run2_dir, **common)
        stable, drift_rows = compare_runs(scan1, scan2)
        final_scan = scan2
        print(f"semantic_second_run_stable={stable}", flush=True)
        print(f"drift_rows={len(drift_rows)}", flush=True)

    summary = build_summary(
        final_scan,
        semantic_second_run_stable=stable if stable is not None else True,
        drift_rows=len(drift_rows),
        run_label="run2" if not args.single_run else "run1",
    )
    args.package_dir.parent.mkdir(parents=True, exist_ok=True)
    write_artifact_package(
        args.package_dir,
        final_scan,
        summary=summary,
        drift_rows=drift_rows,
    )
    checksums = verify_checksums(args.package_dir)
    zip_sha = zip_package(args.package_dir, args.zip_path)

    print(json.dumps({"summary": summary, "checksums": checksums, "zip_sha256": zip_sha}, indent=2))
    if checksums["checksum_failures"] or checksums["checksum_uncovered_files"]:
        raise BaselineError("checksum", f"checksum verification failed: {checksums}")
    if (
        checksums["checksum_entries"]
        != checksums["regular_payload_files_excluding_checksums_file"]
    ):
        raise BaselineError("checksum", f"checksum entry mismatch: {checksums}")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return asyncio.run(_amain(argv))
    except BaselineError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
