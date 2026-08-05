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

from image_candidate_discovery import LANE_SPECS, CandidateDiscoveryError  # noqa: E402
from image_candidate_discovery.consolidate import consolidate_lane_outputs  # noqa: E402
from image_candidate_discovery.core import run_lane_candidate_discovery  # noqa: E402

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
        "--output-dir",
        required=True,
        type=Path,
        help="Absolute empty external consolidation directory",
    )
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
    print(json.dumps({"ok": True, **{k: result[k] for k in ("output_dir", "checksums_digest")}}, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Backward-compatible flat flags: treat missing subcommand as "run".
    if argv and argv[0] not in {"run", "consolidate", "-h", "--help"} and not argv[0].startswith("-"):
        pass
    if argv and argv[0] not in {"run", "consolidate", "-h", "--help"}:
        argv = ["run", *argv]
    args = _build_parser().parse_args(argv)
    if args.command == "consolidate":
        return _cmd_consolidate(args)
    if args.command == "run":
        return _cmd_run(args)
    _build_parser().print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
