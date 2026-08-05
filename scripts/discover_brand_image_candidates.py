#!/usr/bin/env python3
"""CLI for governed brand image candidate discovery (IMG-02B-02..04).

Reads IMG-02B worklists, discovers official/authorized image candidates, and
writes CSV/JSON artifacts to an operator-supplied absolute directory **outside**
the Git repository.

Hard boundaries:
- Does not import SQLAlchemy, app.db, Product, ProductImage, or CRUD modules.
- Does not claim commercial image rights (rights_status=review_required).
- Host allowlists are lane-scoped; redirects elsewhere fail closed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from image_candidate_discovery import (  # noqa: E402
    ALLOWED_HOSTS,
    LANE_SPECS,
    CandidateDiscoveryError,
)
from image_candidate_discovery.consolidate import consolidate_lane_outputs  # noqa: E402
from image_candidate_discovery.core import run_lane_candidate_discovery  # noqa: E402
from image_candidate_discovery.reconcile_insize import (  # noqa: E402
    apply_insize_reconciliation,
    reconcile_insize_candidate_runs,
    write_insize_reconcile_report,
)
from image_candidate_discovery.sanou_calibrate import calibrate_sanou_site_shape  # noqa: E402
from image_candidate_discovery.transport import HostThrottledFetcher  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Governed brand image candidate discovery (IMG-02B lanes)."
    )
    sub = p.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Discover candidates for one brand lane")
    run_p.add_argument(
        "--lane",
        required=True,
        choices=sorted(LANE_SPECS.keys()),
        help="Discovery lane: dasqua | insize | san_ou",
    )
    run_p.add_argument(
        "--worklist-root",
        required=True,
        type=Path,
        help="Absolute IMG-02B-01 worklist directory (with checksums.sha256)",
    )
    run_p.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Absolute empty external output directory (outside the repo)",
    )
    run_p.add_argument("--concurrency", type=int, default=3)
    run_p.add_argument("--delay", type=float, default=0.75)
    run_p.add_argument("--timeout", type=float, default=60.0)
    run_p.add_argument("--max-transient-retries", type=int, default=2)
    run_p.add_argument("--limit", type=int, default=None)

    cons = sub.add_parser("consolidate", help="Merge per-lane external outputs")
    cons.add_argument(
        "--lane-dir",
        action="append",
        required=True,
        metavar="BRAND=PATH",
        help="Brand key and lane output dir, e.g. dasqua=/var/tmp/.../img02b-dasqua",
    )
    cons.add_argument(
        "--download-dir",
        action="append",
        default=[],
        metavar="BRAND=PATH",
        help="Optional brand=download-dir from discover_product_images",
    )
    cons.add_argument(
        "--accepted-manifest",
        action="append",
        default=[],
        metavar="BRAND=PATH",
        help="Optional brand=stable-materialized-manifest.csv override",
    )
    cons.add_argument(
        "--drift-review-csv",
        action="append",
        default=[],
        type=Path,
        help="Optional source-drift-review.csv to fold into governed manual queue",
    )
    cons.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Absolute empty external consolidation directory",
    )

    cal = sub.add_parser(
        "calibrate-sanou",
        help="Bounded SAN OU official site-shape calibration (≤25 models)",
    )
    cal.add_argument("--output-json", required=True, type=Path)
    cal.add_argument("--delay", type=float, default=0.75)
    cal.add_argument("--timeout", type=float, default=60.0)
    cal.add_argument(
        "--model-sample-csv",
        type=Path,
        default=None,
        help="Optional CSV with product_id,sku,product_name,model columns (≤25 used)",
    )

    rec = sub.add_parser(
        "reconcile-insize",
        help="Reconcile INSIZE first/second candidate runs + materialization",
    )
    rec.add_argument("--first-run-dir", required=True, type=Path)
    rec.add_argument("--second-run-dir", required=True, type=Path)
    rec.add_argument("--materialization-dir", type=Path, default=None)
    rec.add_argument("--requested", type=int, default=263)
    rec.add_argument("--output-json", required=True, type=Path)

    apply = sub.add_parser(
        "apply-insize-reconciliation",
        help="Apply effective INSIZE drift quarantine outputs (no network)",
    )
    apply.add_argument("--first-run-dir", required=True, type=Path)
    apply.add_argument("--second-run-dir", required=True, type=Path)
    apply.add_argument("--materialization-dir", required=True, type=Path)
    apply.add_argument("--output-dir", required=True, type=Path)
    apply.add_argument("--requested", type=int, default=263)
    return p


def _parse_brand_paths(items: list[str]) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"expected BRAND=PATH, got: {item}")
        brand, path = item.split("=", 1)
        brand = brand.strip()
        if not brand:
            raise SystemExit(f"empty brand in: {item}")
        out[brand] = Path(path)
    return out


def _cmd_run(args: argparse.Namespace) -> int:
    print(
        json.dumps(
            {
                "phase": "start",
                "lane": args.lane,
                "output_dir": str(args.output_dir),
                "worklist_root": str(args.worklist_root),
                "concurrency": args.concurrency,
                "delay": args.delay,
                "limit": args.limit,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    try:
        result = run_lane_candidate_discovery(
            lane=args.lane,
            worklist_root=args.worklist_root,
            output_dir=args.output_dir,
            repo_root=REPO_ROOT,
            concurrency=args.concurrency,
            delay=args.delay,
            timeout=args.timeout,
            max_transient_retries=args.max_transient_retries,
            limit=args.limit,
        )
    except CandidateDiscoveryError as exc:
        print(
            json.dumps(
                {"ok": False, "stage": exc.stage, "error": exc.message},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2

    payload = {
        "ok": True,
        "lane_id": result.get("lane_id"),
        "brand_key": result.get("brand_key"),
        "output_dir": result.get("output_dir"),
        "candidate_count": result.get("candidate_count"),
        "rejected_count": result.get("rejected_count"),
        "manual_count": result.get("manual_count"),
        "checksums_digest": result.get("checksums_digest"),
        "stats": result.get("stats"),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _cmd_consolidate(args: argparse.Namespace) -> int:
    lane_dirs = _parse_brand_paths(args.lane_dir)
    download_dirs = _parse_brand_paths(args.download_dir) if args.download_dir else None
    accepted_manifest_by_brand = (
        _parse_brand_paths(args.accepted_manifest) if args.accepted_manifest else None
    )
    print(
        json.dumps(
            {
                "phase": "start",
                "command": "consolidate",
                "lane_dirs": {k: str(v) for k, v in sorted(lane_dirs.items())},
                "download_dirs": (
                    {k: str(v) for k, v in sorted(download_dirs.items())}
                    if download_dirs
                    else None
                ),
                "accepted_manifest_by_brand": (
                    {k: str(v) for k, v in sorted(accepted_manifest_by_brand.items())}
                    if accepted_manifest_by_brand
                    else None
                ),
                "drift_review_csvs": [str(p) for p in (args.drift_review_csv or [])],
                "output_dir": str(args.output_dir),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    try:
        result = consolidate_lane_outputs(
            lane_dirs=lane_dirs,
            download_dirs=download_dirs,
            output_dir=args.output_dir,
            repo_root=REPO_ROOT,
            accepted_manifest_by_brand=accepted_manifest_by_brand,
            drift_review_csvs=list(args.drift_review_csv or []),
        )
    except (CandidateDiscoveryError, ValueError) as exc:
        stage = getattr(exc, "stage", "consolidate")
        message = getattr(exc, "message", str(exc))
        print(
            json.dumps(
                {"ok": False, "stage": stage, "error": message},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2
    print(
        json.dumps(
            {"ok": True, **{k: result[k] for k in ("output_dir", "checksums_digest")}},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _cmd_calibrate_sanou(args: argparse.Namespace) -> int:
    import csv

    samples: list[dict[str, str]] = []
    if args.model_sample_csv is not None:
        with args.model_sample_csv.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                samples.append(dict(row))
                if len(samples) >= 25:
                    break
    fetcher = HostThrottledFetcher(
        allowed_hosts=ALLOWED_HOSTS["san_ou"],
        delay=args.delay,
        timeout=args.timeout,
    )
    report = calibrate_sanou_site_shape(
        fetcher=fetcher,
        model_samples=samples,
        max_model_samples=25,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "governed_outcome": report.get("governed_outcome"),
                "proven_product_detail_shape": report.get("proven_product_detail_shape"),
                "calibration_row_count": len(report.get("calibration_rows") or []),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _cmd_reconcile_insize(args: argparse.Namespace) -> int:
    report = reconcile_insize_candidate_runs(
        first_run_dir=args.first_run_dir,
        second_run_dir=args.second_run_dir,
        materialization_dir=args.materialization_dir,
        requested=args.requested,
    )
    write_insize_reconcile_report(report, args.output_json)
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "first_run_candidates": report.get("first_run_candidates"),
                "second_run_candidates": report.get("second_run_candidates"),
                "stable_intersection": report.get("stable_intersection"),
                "source_drift_count": report.get("source_drift_count"),
                "coverage": report.get("coverage"),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _cmd_apply_insize_reconciliation(args: argparse.Namespace) -> int:
    try:
        result = apply_insize_reconciliation(
            first_run_dir=args.first_run_dir,
            second_run_dir=args.second_run_dir,
            materialization_dir=args.materialization_dir,
            output_dir=args.output_dir,
            repo_root=REPO_ROOT,
            requested=args.requested,
        )
    except CandidateDiscoveryError as exc:
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
                "stable_candidates": result["stable_candidates"],
                "source_drift_rows": result["source_drift_rows"],
                "stable_materialized_rows": result["stable_materialized_rows"],
                "materialized_source_drift_rows": result[
                    "materialized_source_drift_rows"
                ],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    known = {
        "run",
        "consolidate",
        "calibrate-sanou",
        "reconcile-insize",
        "apply-insize-reconciliation",
        "-h",
        "--help",
    }
    if argv and argv[0] not in known:
        argv = ["run", *argv]
    args = _build_parser().parse_args(argv)
    if args.command == "consolidate":
        return _cmd_consolidate(args)
    if args.command == "run":
        return _cmd_run(args)
    if args.command == "calibrate-sanou":
        return _cmd_calibrate_sanou(args)
    if args.command == "reconcile-insize":
        return _cmd_reconcile_insize(args)
    if args.command == "apply-insize-reconciliation":
        return _cmd_apply_insize_reconciliation(args)
    _build_parser().print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
