#!/usr/bin/env python3
"""IMG-02C multisource discovery CLI (external outputs only; no DB)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from image_multisource import MultisourceError  # noqa: E402
from image_multisource.pipeline import run_foundation_and_calibration  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    cal = sub.add_parser(
        "calibrate-batch-001",
        help="Eligibility + registry snapshot + ≤20 per-source calibration (no bulk download)",
    )
    cal.add_argument("--worklist-csv", type=Path, required=True)
    cal.add_argument("--r2-seed", type=Path, required=True, help="IMG-02B-R2.zip or extracted dir")
    cal.add_argument("--output-dir", type=Path, required=True)
    cal.add_argument("--registry-json", type=Path, default=None)
    cal.add_argument("--limit", type=int, default=20)
    cal.add_argument(
        "--live-calibration",
        action="store_true",
        help="Run ≤20 live probes against known allowed hosts (ops only; CI must not)",
    )

    r1 = sub.add_parser(
        "discover-batch-001-r1",
        help="R1 real-source onboarding + bulk discovery (ops only; external outputs)",
    )
    r1.add_argument("--worklist-csv", type=Path, required=True)
    r1.add_argument("--r2-seed", type=Path, required=True)
    r1.add_argument("--output-dir", type=Path, required=True)
    r1.add_argument("--work-root", type=Path, required=True, help="External cache/work root")
    r1.add_argument("--zip-path", type=Path, default=None)
    r1.add_argument("--delay", type=float, default=0.8)
    r1.add_argument("--relation-cap", type=int, default=400)
    r1.add_argument("--calibration-limit", type=int, default=20)

    r2 = sub.add_parser(
        "remediate-batch-001-r2",
        help="R2 offline semantic remediation from immutable R1 Artifact (no live network)",
    )
    r2.add_argument("--r1-root", type=Path, required=True)
    r2.add_argument("--r1-zip", type=Path, default=None)
    r2.add_argument("--output-dir", type=Path, required=True)
    r2.add_argument("--zip-path", type=Path, default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "calibrate-batch-001":
        probes = None
        robots_txt_by_source = None
        if args.live_calibration:
            from image_multisource.live_probes import build_live_probe_map
            from image_multisource.registry import (
                builtin_known_host_registry,
                load_registry,
            )

            sources = (
                load_registry(args.registry_json)
                if args.registry_json is not None
                else builtin_known_host_registry()
            )
            live = build_live_probe_map(sources, delay=0.8)
            robots_txt_by_source = live.pop("_robots_txt")
            probes = live
        try:
            result = run_foundation_and_calibration(
                worklist_csv=args.worklist_csv,
                r2_seed=args.r2_seed,
                output_dir=args.output_dir,
                repo_root=REPO_ROOT,
                registry_path=args.registry_json,
                calibration_limit=args.limit,
                probes=probes,
                robots_txt_by_source=robots_txt_by_source,
            )
        except MultisourceError as exc:
            print(
                json.dumps(
                    {"ok": False, "stage": exc.stage, "error": exc.message},
                    ensure_ascii=False,
                ),
                file=sys.stderr,
            )
            return 2
        print(
            json.dumps(
                {
                    "ok": True,
                    "output_dir": result["output_dir"],
                    "checksums_digest": result["checksums_digest"],
                    "remaining_eligible": result["eligibility"]["totals"][
                        "remaining_eligible"
                    ],
                    "enabled_source_count": result["calibration"]["enabled_source_count"],
                    "disabled_sources": result["calibration"]["disabled_sources"],
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "discover-batch-001-r1":
        from image_multisource.r1_ops import package_review_zip, run_r1_bulk

        try:
            result = run_r1_bulk(
                worklist_csv=args.worklist_csv,
                r2_seed=args.r2_seed,
                output_dir=args.output_dir,
                repo_root=REPO_ROOT,
                work_root=args.work_root,
                delay=args.delay,
                relation_cap=args.relation_cap,
                calibration_limit=args.calibration_limit,
            )
            zip_info = None
            if args.zip_path is not None:
                sha = package_review_zip(Path(result["output_dir"]), args.zip_path)
                zip_info = {
                    "zip_path": str(args.zip_path),
                    "sha256": sha,
                    "size_bytes": args.zip_path.stat().st_size,
                }
        except MultisourceError as exc:
            print(
                json.dumps(
                    {"ok": False, "stage": exc.stage, "error": exc.message},
                    ensure_ascii=False,
                ),
                file=sys.stderr,
            )
            return 2
        print(
            json.dumps(
                {
                    "ok": True,
                    "output_dir": result["output_dir"],
                    "checksums_digest": result["checksums_digest"],
                    "enabled_sources": result["enabled_sources"],
                    "summary": result["summary"],
                    "zip": zip_info,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "remediate-batch-001-r2":
        from image_multisource.r2_remediate import package_review_zip, run_r2_remediation

        try:
            result = run_r2_remediation(
                r1_root=args.r1_root,
                output_dir=args.output_dir,
                repo_root=REPO_ROOT,
                r1_zip=args.r1_zip,
            )
            zip_info = None
            if args.zip_path is not None:
                sha = package_review_zip(Path(result["output_dir"]), args.zip_path)
                zip_info = {
                    "zip_path": str(args.zip_path),
                    "sha256": sha,
                    "size_bytes": args.zip_path.stat().st_size,
                }
        except MultisourceError as exc:
            print(
                json.dumps(
                    {"ok": False, "stage": exc.stage, "error": exc.message},
                    ensure_ascii=False,
                ),
                file=sys.stderr,
            )
            return 2
        print(
            json.dumps(
                {
                    "ok": True,
                    "output_dir": result["output_dir"],
                    "summary": result["summary"],
                    "checksum": result["checksum"],
                    "zip": zip_info,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
