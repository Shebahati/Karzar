#!/usr/bin/env python3
"""Category B APPLY for AST manifests (dry-run default). Does not run without explicit gates."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from catalog_target.ast_price_catalog_apply import (  # noqa: E402
    assert_apply_gates,
    load_create_plan,
    load_update_plan,
    manifest_identity,
)
from catalog_target.ast_price_catalog_constants import SOURCE_ARCHIVE_SHA256  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-dir", type=Path, default=ROOT / "audit/ast-price-and-catalog-20261024")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--confirm-production-write", action="store_true")
    parser.add_argument("--owner-authorization", default="")
    parser.add_argument("--confirm-source-sha256", default="")
    parser.add_argument("--confirm-update-manifest-sha256", default="")
    parser.add_argument("--confirm-create-manifest-sha256", default="")
    args = parser.parse_args()

    update_path = args.audit_dir / "UPDATE_PRODUCTS.csv"
    create_path = args.audit_dir / "CREATE_PRODUCTS.csv"
    ids = manifest_identity(update_path, create_path)
    updates = load_update_plan(update_path)
    creates = load_create_plan(create_path)

    dry_run = not args.apply
    if not args.apply:
        print(
            {
                "status": "dry_run",
                "updates": len(updates),
                "creates": len(creates),
                "manifest": ids,
                "note": "Pass --apply with full Category B gates to mutate production.",
            }
        )
        return 0
    try:
        assert_apply_gates(
            apply=args.apply,
            rollback=False,
            owner_authorization=args.owner_authorization,
            confirm_production_write=args.confirm_production_write,
            confirm_source_sha256=args.confirm_source_sha256,
            confirm_update_manifest_sha256=args.confirm_update_manifest_sha256,
            confirm_create_manifest_sha256=args.confirm_create_manifest_sha256,
            update_manifest_sha256=ids["update_manifest_sha256"],
            create_manifest_sha256=ids["create_manifest_sha256"],
            confirm_update_count=len(updates),
            confirm_create_count=len(creates),
            update_count=len(updates),
            create_count=len(creates),
        )
    except Exception as exc:
        print({"status": "blocked", "reason": str(exc)})
        return 2

    print(
        {
            "status": "dry_run_ready" if dry_run else "apply_ready",
            "updates": len(updates),
            "creates": len(creates),
            "manifest": ids,
            "source_sha256": SOURCE_ARCHIVE_SHA256,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
