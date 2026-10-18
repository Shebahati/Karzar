#!/usr/bin/env python3
"""Generate Phase 1B Route B2 architecture review package."""

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

from catalog_target.taxonomy_route_b2_architecture_review import (  # noqa: E402
    B2_DIR_NAME,
    PR533_MERGE_SHA,
    generate_b2_package,
)


def git_sha(ref: str = "HEAD") -> str:
    return subprocess.check_output(["git", "rev-parse", ref], cwd=ROOT, text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=ROOT / B2_DIR_NAME)
    parser.add_argument("--base-sha", default=PR533_MERGE_SHA)
    args = parser.parse_args()
    head = git_sha("HEAD")
    generate_b2_package(args.out_dir, base_git_sha=args.base_sha, generator_run_git_sha=head)
    print(json.dumps({"status": "READY_FOR_OWNER_REVIEW", "head": head, "base": args.base_sha}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
