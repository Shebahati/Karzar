#!/usr/bin/env python3
"""Generate Phase 1B Route B target taxonomy design package (design-only)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.taxonomy_route_b_target_design import generate_route_b_package  # noqa: E402

DEFAULT_OUT = ROOT / "audit/taxonomy-phase1b-route-b-target-design-2026-10-18"


def git_sha(ref: str = "HEAD") -> str:
    return subprocess.check_output(["git", "rev-parse", ref], cwd=ROOT, text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-sha", default="0d04e794712206e1421a596e28993002d05e338c")
    args = parser.parse_args()
    head = git_sha("HEAD")
    payload = generate_route_b_package(args.out_dir, base_git_sha=args.base_sha, head_git_sha=head)
    print(json.dumps({"status": "READY_FOR_OWNER_REVIEW", "head": head, "out": str(args.out_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
