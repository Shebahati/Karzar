#!/usr/bin/env python3
"""Generate / validate Owner Architecture Decision Journal (documentation-only)."""

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

from catalog_target.taxonomy_owner_architecture_decision_journal import (  # noqa: E402
    JOURNAL_DIR_NAME,
    PR534_MERGE_SHA,
    JournalPaths,
    validate_journal_package,
    write_journal_package,
)


def git_sha(ref: str = "HEAD") -> str:
    return subprocess.check_output(["git", "rev-parse", ref], cwd=ROOT, text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=ROOT / JOURNAL_DIR_NAME)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    head = git_sha("HEAD")

    if args.validate_only:
        result = validate_journal_package(JournalPaths(args.out_dir))
        print(json.dumps({"status": result["status"], "head": head, "base": PR534_MERGE_SHA}, indent=2))
        return 0 if result["status"] == "PASS" else 1

    payload = write_journal_package(args.out_dir, generator_git_sha=head)
    print(
        json.dumps(
            {
                "status": "READY_FOR_OWNER_REVIEW",
                "head": head,
                "base": PR534_MERGE_SHA,
                "validation": payload["validation"]["status"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
