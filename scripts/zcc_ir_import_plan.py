#!/usr/bin/env python3
"""READ-ONLY zcc.ir Phase 2 import planning (no APPLY).

Usage:
  python3 scripts/zcc_ir_import_plan.py plan --phase1-dir data/zcc_ir --output-dir data/zcc_ir_phase2 \\
    --karzar-snapshot /path/to/full_current_catalog.csv
  python3 scripts/zcc_ir_import_plan.py validate --manifest data/zcc_ir_phase2/import_manifest.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

FORBIDDEN = {"--apply", "--write", "--write-db", "--mutate", "--production-apply"}

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from zcc_ir_phase2 import FORBIDDEN_FLAGS  # noqa: E402
from zcc_ir_phase2.pipeline import run_phase2_plan  # noqa: E402
from zcc_ir_phase2.validate import validate_manifest_layers  # noqa: E402


def _reject_writes(argv: list[str]) -> int | None:
    hit = [flag for flag in FORBIDDEN if flag in argv]
    if hit:
        print(
            "FATAL: zcc.ir Phase 2 is READ-ONLY planning. Forbidden flag(s): "
            + ", ".join(hit)
            + ". No APPLY / catalog writer exists.",
            file=sys.stderr,
        )
        return 2
    return None


def cmd_plan(args: argparse.Namespace) -> int:
    if args.read_db:
        print(
            "FATAL: Phase 2 approval planning requires --karzar-snapshot (file-backed catalog CSV). "
            "--read-db is not supported for owner-bound import manifests. "
            "Use catalog_target snapshot tooling separately, then pass the CSV path.",
            file=sys.stderr,
        )
        return 2
    phase1_dir = Path(args.phase1_dir)
    output_dir = Path(args.output_dir)
    try:
        summary = run_phase2_plan(
            phase1_dir=phase1_dir,
            output_dir=output_dir,
            karzar_snapshot=args.karzar_snapshot,
            read_db=args.read_db,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"FATAL: {exc}", file=sys.stderr)
        return 2
    print(
        "PHASE2_PLAN_DONE "
        f"sources={summary['current_snapshot']['source_product_count']} "
        f"karzar={summary['current_snapshot']['karzar_product_count']} "
        f"sha256={summary['manifest_sha256']}"
    )
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.manifest)
    if not path.is_file():
        print(f"FATAL: manifest not found: {path}", file=sys.stderr)
        return 2
    layers = validate_manifest_layers(path)
    if layers.content_errors:
        for err in layers.content_errors:
            print(f"CONTENT_INVALID: {err}", file=sys.stderr)
    if layers.commerce_errors:
        for err in layers.commerce_errors:
            print(f"COMMERCE_INVALID: {err}", file=sys.stderr)
    print(
        f"CONTENT_PLAN_VALID={layers.CONTENT_PLAN_VALID} "
        f"COMMERCE_PLAN_VALID={layers.COMMERCE_PLAN_VALID} "
        f"CONTENT_BLOCKING_ERROR_COUNT={layers.CONTENT_BLOCKING_ERROR_COUNT} "
        f"CONTENT_DIAGNOSTIC_ROW_COUNT={layers.CONTENT_DIAGNOSTIC_ROW_COUNT} "
        f"CONTENT_COLLISION_AFFECTED_ROW_COUNT={layers.CONTENT_COLLISION_AFFECTED_ROW_COUNT} "
        f"LOGICAL_COLLISION_GROUP_COUNT={layers.LOGICAL_COLLISION_GROUP_COUNT} "
        f"MUTATION_BLOCKING_COLLISION_GROUPS={layers.MUTATION_BLOCKING_COLLISION_GROUPS} "
        f"CONTENT_MUTATION_PLAN_VALID={layers.CONTENT_MUTATION_PLAN_VALID}"
    )
    if layers.content_errors or layers.commerce_errors:
        return 1
    print("MANIFEST_VALID")
    return 0


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    blocked = _reject_writes(raw)
    if blocked is not None:
        return blocked
    for flag in FORBIDDEN_FLAGS:
        if flag in raw:
            print(f"FATAL: forbidden flag {flag}", file=sys.stderr)
            return 2

    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="READ-ONLY zcc.ir Phase 2 import plan")
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="Generate Phase-2 import plan artifacts")
    plan.add_argument("--phase1-dir", default=str(root / "data" / "zcc_ir"))
    plan.add_argument("--output-dir", default=str(root / "data" / "zcc_ir_phase2"))
    plan.add_argument("--karzar-snapshot", default=None, help="Full READ-ONLY current catalog CSV")
    plan.add_argument(
        "--read-db",
        action="store_true",
        help="Rejected for Phase 2 plan (file-backed --karzar-snapshot required for SHA binding)",
    )

    validate = sub.add_parser("validate", help="Validate import manifest (read-only)")
    validate.add_argument("--manifest", required=True)

    args = parser.parse_args(raw)
    if args.command == "plan":
        return cmd_plan(args)
    if args.command == "validate":
        return cmd_validate(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
