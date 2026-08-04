#!/usr/bin/env python3
"""IMG-02B-01 — Build deterministic source-discovery worklists (no network/DB/storage)."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.image_source_worklists.builder import build_worklists  # noqa: E402
from scripts.image_source_worklists.contracts import (  # noqa: E402
    AUTHORITATIVE_CHECKSUMS_DIGEST,
    WorklistError,
)
from scripts.image_source_worklists.inputs import (  # noqa: E402
    load_inventory,
    load_review_bundles,
)
from scripts.image_source_worklists.output import (  # noqa: E402
    semantic_fingerprint,
    write_worklist_outputs,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Build governed IMG-02B source-discovery worklists (read-only)."
    )
    p.add_argument(
        "--source-dir",
        required=True,
        type=Path,
        help="Verified IMG-02A-01 inventory directory",
    )
    p.add_argument(
        "--review-root",
        required=True,
        type=Path,
        help="External directory containing the three human-review ZIP bundles",
    )
    p.add_argument(
        "--extract-root",
        required=True,
        type=Path,
        help="Absolute external directory for temporary review ZIP extraction",
    )
    p.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Absolute empty external output directory",
    )
    p.add_argument(
        "--expected-checksums-digest",
        default=AUTHORITATIVE_CHECKSUMS_DIGEST,
    )
    p.add_argument(
        "--compare-with",
        type=Path,
        default=None,
        help="Optional prior output dir for semantic second-run comparison",
    )
    p.add_argument(
        "--copy-final-to",
        type=Path,
        default=None,
        help="Optional absolute external directory to copy final outputs into",
    )
    p.add_argument(
        "--allow-nonempty-output",
        action="store_true",
        help="Permit writing into a non-empty output directory (governed reuse only)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        inventory = load_inventory(
            args.source_dir,
            expected_checksums_digest=args.expected_checksums_digest,
        )
        review_data = load_review_bundles(
            args.review_root,
            extract_root=args.extract_root,
        )
        built = build_worklists(inventory, review_data)
        result = write_worklist_outputs(
            args.output_dir,
            repo_root=REPO_ROOT,
            inventory=inventory,
            review_data=review_data,
            built=built,
            allow_nonempty=args.allow_nonempty_output,
        )
        payload = {
            "ok": True,
            "output_dir": result["output_dir"],
            "checksums_digest": result["checksums_digest"],
            "work_item_total": result["work_item_total"],
            "counts": built["counts"],
            "safety": result["summary"]["safety"],
        }
        if args.compare_with is not None:
            left = semantic_fingerprint(args.compare_with)
            right = semantic_fingerprint(args.output_dir)
            stable = left == right
            payload["semantic_second_run_stable"] = stable
            if not stable:
                raise WorklistError("determinism", "semantic second-run mismatch")
        if args.copy_final_to is not None:
            dest = args.copy_final_to
            if not dest.is_absolute():
                raise WorklistError("output", "copy-final-to must be absolute")
            if dest.resolve() == REPO_ROOT.resolve() or str(dest).startswith(str(REPO_ROOT)):
                raise WorklistError("output", "copy-final-to must be outside repository")
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(args.output_dir, dest)
            payload["final_copy"] = str(dest)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except WorklistError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
