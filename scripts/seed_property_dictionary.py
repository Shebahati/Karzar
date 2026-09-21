"""CLI: import Property Dictionary Git seed into Postgres overlay (11A).

Usage:
  python scripts/seed_property_dictionary.py --dry-run
  python scripts/seed_property_dictionary.py
  python scripts/seed_property_dictionary.py --seed PATH

Non-dry-run mutations are allowed only on:
  - KARZAR_DATA_PLANE=development
  - KARZAR_DATA_PLANE=catalog_staging with matching environment_identity sentinel

Live (including historic APP_ENV=staging + POSTGRES_DB=karzar_staging) is refused.
Does not touch Products, Facts, or JSONB dual-write. No --force-production switch.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.data_plane import (
    assert_dictionary_seed_import_allowed,
    format_identity_report,
    identity_from_mapping,
)
from app.db.database import async_session_maker
from app.services.property_dictionary_service import (
    DEFAULT_SEED_PATH,
    PropertyDictionaryImportError,
    file_checksum,
    import_property_dictionary,
    load_seed,
    validate_seed,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def _read_environment_identity_plane(session: AsyncSession) -> str | None:
    """Return environment_identity.plane for id=1, or None if absent/unmigrated."""
    try:
        row = (
            await session.execute(
                text("SELECT plane FROM environment_identity WHERE id = 1")
            )
        ).first()
    except Exception:  # noqa: BLE001 — missing table/pre-migration → absent sentinel
        return None
    if row is None:
        return None
    return str(row[0]) if row[0] is not None else None


def _dry_run_report(seed: Path, identity_block: str | None) -> dict:
    data = load_seed(seed)
    validate_seed(data)
    report: dict = {
        "dry_run": True,
        "seed_path": str(seed),
        "seed_version": data.get("version"),
        "checksum": file_checksum(seed),
        "units_scanned": len(data.get("units") or []),
        "properties_scanned": len(data.get("definitions") or []),
        "aliases_scanned": sum(
            len(d.get("aliases") or [])
            for d in (data.get("definitions") or [])
            if isinstance(d, dict)
        ),
    }
    if identity_block is not None:
        report["data_plane_identity"] = identity_block
    return report


async def _run(seed: Path, dry_run: bool) -> int:
    identity = None
    identity_error: str | None = None
    try:
        identity = identity_from_mapping(os.environ)
    except ValueError as exc:
        identity_error = str(exc)

    if dry_run:
        # Zero-write seed validation — no mutate permit / sentinel required.
        if identity is not None:
            block = format_identity_report(identity)
        else:
            block = f"(unresolved: {identity_error})" if identity_error else None
        # Still open a session only if we will call import dry-run path that
        # compares against DB; keep existing import_property_dictionary dry-run.
        async with async_session_maker() as session:
            try:
                result = await import_property_dictionary(
                    session, seed_path=seed, dry_run=True
                )
            except PropertyDictionaryImportError as exc:
                print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
                return 1
            except Exception as exc:  # noqa: BLE001
                print(json.dumps({"ok": False, "error": repr(exc)}, ensure_ascii=False))
                return 1
        report = _dry_run_report(seed, block)
        report.update(result)
        print(json.dumps({"ok": True, **report}, ensure_ascii=False, indent=2))
        return 0

    # Non-dry-run: fail closed before first write.
    if identity is None:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": (
                        f"data-plane identity unresolved: {identity_error}. "
                        "Set POSTGRES_DB and KARZAR_DATA_PLANE "
                        "(development|catalog_staging)."
                    ),
                },
                ensure_ascii=False,
            )
        )
        return 2

    async with async_session_maker() as session:
        try:
            sentinel = await _read_environment_identity_plane(session)
            assert_dictionary_seed_import_allowed(
                identity, sentinel_plane=sentinel
            )
            result = await import_property_dictionary(
                session, seed_path=seed, dry_run=False
            )
            await session.commit()
        except (PropertyDictionaryImportError, ValueError) as exc:
            await session.rollback()
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
            return 1
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            print(json.dumps({"ok": False, "error": repr(exc)}, ensure_ascii=False))
            return 1

    print(
        json.dumps(
            {
                "ok": True,
                "data_plane": identity.data_plane,
                "postgres_db": identity.postgres_db,
                **result,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Import Property Dictionary v0 seed "
            "(development / catalog_staging only; live refused)"
        )
    )
    parser.add_argument(
        "--seed",
        type=Path,
        default=DEFAULT_SEED_PATH,
        help="Path to property-dictionary JSON seed",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate seed only; no database writes",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args.seed, args.dry_run)))


if __name__ == "__main__":
    main()
