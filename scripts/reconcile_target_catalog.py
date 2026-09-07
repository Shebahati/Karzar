#!/usr/bin/env python3
"""READ-ONLY Target Catalog reconciliation.

Does not mutate production, local databases, or product rows.
There is no APPLY path.

Usage:
  KARZAR_TARGET_SOURCE_DIR=/path/to/ProductsAndData \\
    python3 scripts/reconcile_target_catalog.py

  python3 scripts/reconcile_target_catalog.py \\
    --source-dir /path/to/ProductsAndData \\
    --snapshot /path/to/current_catalog.csv \\
    --output-dir data/catalog-target
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

FORBIDDEN = {"--apply", "--write", "--write-db", "--mutate", "--production-apply"}

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from catalog_target.reconcile import run_reconciliation  # noqa: E402
from catalog_target.sources import describe_source_root, resolve_source_root  # noqa: E402


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(Path(__file__).resolve().parents[1]),
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    hit = [flag for flag in FORBIDDEN if flag in raw]
    if hit:
        print(
            "FATAL: this tool is READ-ONLY. Forbidden flag(s): "
            + ", ".join(hit)
            + ". No APPLY phase exists.",
            file=sys.stderr,
        )
        return 2

    parser = argparse.ArgumentParser(description="READ-ONLY Target Catalog reconciliation")
    parser.add_argument(
        "--source-dir",
        default=None,
        help="Approved Products and Data root (else KARZAR_TARGET_SOURCE_DIR)",
    )
    parser.add_argument(
        "--snapshot",
        default=None,
        help="Optional READ-ONLY current-catalog CSV. Not a live production count.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parents[1] / "data" / "catalog-target"),
    )
    parser.add_argument(
        "--read-db",
        action="store_true",
        help="Attempt local READ-ONLY DB snapshot. Production hosts are refused.",
    )
    args = parser.parse_args(raw)

    info = describe_source_root(args.source_dir)
    print(f"KARZAR_TARGET_SOURCE_DIR raw={info['raw'] or '(unset)'}")
    print(f"KARZAR_TARGET_SOURCE_DIR resolved={info['resolved'] or '(none)'}")
    print(f"KARZAR_TARGET_SOURCE_DIR exists={info['exists']}")

    root = resolve_source_root(args.source_dir)
    if root is None:
        print("REAL_SOURCE_VALIDATION = BLOCKED_SOURCE_NOT_MOUNTED")
        print("TARGET_MANIFEST_READY = FALSE")
        print("CURRENT_SITE_RECONCILIATION_READY = FALSE")
        print("APPLY_READY = FALSE")
        print("Did not regenerate a zero-row manifest.")
        print("PRODUCTION MUTATION: ZERO")
        return 3

    result = run_reconciliation(
        source_root=root,
        output_dir=Path(args.output_dir),
        baseline_sha=_git_sha(),
        snapshot_path=args.snapshot,
        read_db=args.read_db,
        real_source_validation="ok",
    )
    print("REAL_SOURCE_VALIDATION = ok")
    print(f"SOURCE_TREE_VALID = {str(result.source_tree_valid).upper()}")
    print(f"PARTIAL_TARGET_MANIFEST_VALID = {str(result.partial_target_manifest_valid).upper()}")
    print(f"TARGET_MANIFEST_READY = {str(result.target_manifest_ready).upper()}")
    print(
        "CURRENT_SITE_RECONCILIATION_READY = "
        f"{str(result.current_site_reconciliation_ready).upper()}"
    )
    print("APPLY_READY = FALSE")
    print("PRODUCTION MUTATION: ZERO")
    print(f"baseline_sha={result.baseline_sha}")
    print(f"db_evidence={result.evidence_kind} ({result.evidence_note})")
    print(f"current_products={len(result.current_products)}")
    print(f"target_skus={len(result.target_skus)}")
    print(f"output_dir={args.output_dir}")
    print("apply_phase=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
