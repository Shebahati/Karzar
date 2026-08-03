#!/usr/bin/env python3
"""IMG-02A-01 — Canonical existing Product / ProductImage inventory (read-only)."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.image_audit.contracts import DEFAULT_STORAGE_REL, AuditError  # noqa: E402
from scripts.image_audit.database import open_readonly_session  # noqa: E402
from scripts.image_audit.inventory import run_inventory  # noqa: E402
from scripts.image_audit.storage import (  # noqa: E402
    assert_real_directory_no_symlink,
    prepare_output_dir,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Read-only inventory of ProductImage rows and local product upload storage."
    )
    p.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Absolute empty directory outside the repository",
    )
    p.add_argument(
        "--storage-root",
        type=Path,
        default=None,
        help="Absolute real directory (default: <repo>/data/uploads/products)",
    )
    p.add_argument(
        "--database-url",
        default=None,
        help="Async SQLAlchemy URL (default: DATABASE_URL or ASYNC_DATABASE_URI env)",
    )
    p.add_argument(
        "--include-deleted-products",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include soft-deleted products (default: true)",
    )
    p.add_argument(
        "--no-storage-scan",
        action="store_true",
        help="Emergency mode: skip recursive storage scan",
    )
    return p


def _resolve_database_url(cli_value: str | None) -> str:
    if cli_value:
        return cli_value.strip()
    for key in ("DATABASE_URL", "ASYNC_DATABASE_URI"):
        val = os.environ.get(key)
        if val:
            return val.strip()
    # Compose from POSTGRES_* if present (without printing secrets)
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    host = os.environ.get("POSTGRES_SERVER")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB")
    if user and password and host and db:
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
    raise AuditError(
        "database",
        "Provide --database-url or DATABASE_URL / POSTGRES_* environment",
    )


async def _amain(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    storage_root = args.storage_root or (REPO_ROOT.joinpath(*DEFAULT_STORAGE_REL))
    if not storage_root.is_absolute():
        raise AuditError("path", "storage-root must be absolute")
    assert_real_directory_no_symlink(storage_root, label="storage-root")
    output_dir = prepare_output_dir(args.output_dir, repository_root=REPO_ROOT)

    database_url = _resolve_database_url(args.database_url)
    async with open_readonly_session(database_url) as db:
        # Safe identity print (no DSN/password)
        print(f"database_name={db.database_name}")
        print(f"database_user={db.database_user}")
        print(f"transaction_read_only={db.transaction_read_only}")
        print(f"storage_root={storage_root}")
        print(f"output_dir={output_dir}")
        if db.dialect == "postgresql" and db.transaction_read_only != "on":
            raise AuditError("database", "refusing to continue without transaction_read_only=on")

        summary = await run_inventory(
            db=db,
            storage_root=storage_root,
            output_dir=output_dir,
            include_deleted_products=bool(args.include_deleted_products),
            storage_scan=not bool(args.no_storage_scan),
            repository_root=REPO_ROOT,
        )

    print(f"total_products={summary['total_products']}")
    print(f"total_product_images={summary['total_product_images']}")
    print(f"network_requests_performed={summary['network_requests_performed']}")
    print(f"database_modified={summary['database_modified']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return asyncio.run(_amain(argv))
    except AuditError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
