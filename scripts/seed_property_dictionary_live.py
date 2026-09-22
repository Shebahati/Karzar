"""Governed LIVE-only Property Dictionary import (Category B).

Usage (seed-only dry-run — zero DB writes):
  python scripts/seed_property_dictionary_live.py --dry-run

Usage (authorized live mutation — Owner Category B only):
  python scripts/seed_property_dictionary_live.py \\
    --expected-sha256 <FULL_SHA256> \\
    --confirm-seed-sha256 <FULL_SHA256> \\
    --backup-reference karzar_YYYYMMDD_HHMMSS.sql.gz \\
    --restore-drill-reference <operator-assertion-id>

This is the ONLY governed live Dictionary import path.

It does NOT weaken scripts/seed_property_dictionary.py (development /
catalog_staging only; live refused).

Non-dry-run requires:
  - explicit KARZAR_DATA_PLANE=live
  - POSTGRES_DB ∈ live denylist (e.g. karzar_staging / KARZAR_LIVE_DB_DENYLIST)
  - KARZAR_INGESTION_CATEGORY=B
  - KARZAR_ALLOW_PRODUCTION_WRITE=1
  - environment_identity.plane=live
  - matching --expected-sha256 and --confirm-seed-sha256
  - non-empty --backup-reference and --restore-drill-reference

Does not touch Products, Product Types, Facts, or JSONB.
Does not close GitHub #247; backup/restore refs are operator audit gates only.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.data_plane import (
    assert_category_b_production_write,
    assert_live_db_sentinel,
    assert_live_dictionary_seed_import_allowed,
    format_identity_report,
    identity_from_mapping,
    live_db_denylist,
)
from app.services.property_dictionary_service import (
    DEFAULT_SEED_PATH,
    PropertyDictionaryImportError,
    file_checksum,
    load_seed,
    validate_seed,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

REQUIRED_ACTIVE_DEFINITIONS = (
    "def.measurement_range",
    "def.resolution",
    "def.accuracy",
)


def assert_seed_sha_authorization(
    *,
    actual_sha256: str,
    expected_sha256: str | None,
    confirm_seed_sha256: str | None,
) -> None:
    """Require expected + confirmation SHAs to equal the actual seed digest."""
    actual = (actual_sha256 or "").strip().lower()
    expected = (expected_sha256 or "").strip().lower()
    confirm = (confirm_seed_sha256 or "").strip().lower()
    if not expected:
        raise ValueError("Live Property Dictionary import refused: --expected-sha256 is required.")
    if not confirm:
        raise ValueError(
            "Live Property Dictionary import refused: --confirm-seed-sha256 is required."
        )
    if actual != expected:
        raise ValueError(
            "Live Property Dictionary import refused: seed SHA256 mismatch "
            f"(actual={actual} expected={expected})."
        )
    if actual != confirm:
        raise ValueError(
            "Live Property Dictionary import refused: confirmation SHA256 mismatch "
            f"(actual={actual} confirm={confirm})."
        )


def assert_operator_references(
    *,
    backup_reference: str | None,
    restore_drill_reference: str | None,
) -> None:
    """Require non-empty operator audit references (not restore-proof)."""
    backup = (backup_reference or "").strip()
    drill = (restore_drill_reference or "").strip()
    if not backup:
        raise ValueError("Live Property Dictionary import refused: --backup-reference is required.")
    if not drill:
        raise ValueError(
            "Live Property Dictionary import refused: --restore-drill-reference is required."
        )


def _seed_only_dry_run_report(seed: Path) -> dict[str, Any]:
    data = load_seed(seed)
    validate_seed(data)
    definitions = data.get("definitions") or []
    return {
        "ok": True,
        "dry_run": True,
        "seed_path": str(seed),
        "seed_version": data.get("version"),
        "actual_sha256": file_checksum(seed),
        "units_scanned": len(data.get("units") or []),
        "properties_scanned": len(definitions),
        "aliases_scanned": sum(
            len(d.get("aliases") or []) for d in definitions if isinstance(d, dict)
        ),
        "writes": 0,
        "note": "seed-only dry-run; Category B / sentinel / backup gates not required",
    }


async def _read_environment_identity_plane(session: AsyncSession) -> str | None:
    """Return environment_identity.plane for id=1, or None if absent/unmigrated."""
    from sqlalchemy import text

    try:
        row = (
            await session.execute(text("SELECT plane FROM environment_identity WHERE id = 1"))
        ).first()
    except Exception:  # noqa: BLE001 — missing table/pre-migration → absent
        return None
    if row is None:
        return None
    return str(row[0]) if row[0] is not None else None


async def _post_write_verify(
    session: AsyncSession,
    *,
    expected_sha256: str,
    expected_units: int,
    expected_definitions: int,
    expected_aliases: int,
) -> dict[str, Any]:
    from app.db.models.knowledge import (
        KnowledgePropertyAlias,
        KnowledgePropertyDefinition,
        KnowledgeUnit,
    )
    from sqlalchemy import func, select

    units = int(
        (await session.execute(select(func.count()).select_from(KnowledgeUnit))).scalar_one()
    )
    defs = int(
        (
            await session.execute(select(func.count()).select_from(KnowledgePropertyDefinition))
        ).scalar_one()
    )
    aliases = int(
        (
            await session.execute(select(func.count()).select_from(KnowledgePropertyAlias))
        ).scalar_one()
    )
    if units != expected_units or defs != expected_definitions or aliases != expected_aliases:
        raise ValueError(
            "Live Property Dictionary post-write verification failed: "
            f"counts units={units} defs={defs} aliases={aliases}; "
            f"expected units={expected_units} defs={expected_definitions} "
            f"aliases={expected_aliases}."
        )

    active_ids = {
        row[0]
        for row in (
            await session.execute(
                select(KnowledgePropertyDefinition.definition_id).where(
                    KnowledgePropertyDefinition.definition_id.in_(REQUIRED_ACTIVE_DEFINITIONS),
                    KnowledgePropertyDefinition.status == "active",
                )
            )
        ).all()
    }
    missing = [d for d in REQUIRED_ACTIVE_DEFINITIONS if d not in active_ids]
    if missing:
        raise ValueError(
            "Live Property Dictionary post-write verification failed: "
            f"missing active definitions {missing}."
        )

    checksum_rows = (
        await session.execute(
            select(KnowledgePropertyDefinition.seed_checksum).where(
                KnowledgePropertyDefinition.definition_id.in_(REQUIRED_ACTIVE_DEFINITIONS)
            )
        )
    ).all()
    bad = [r[0] for r in checksum_rows if (r[0] or "").lower() != expected_sha256.lower()]
    if bad:
        raise ValueError(
            "Live Property Dictionary post-write verification failed: "
            "seed_checksum on imported definitions does not match actual seed SHA."
        )

    return {
        "knowledge_units": units,
        "knowledge_property_definitions": defs,
        "knowledge_property_aliases": aliases,
        "required_active_definitions": list(REQUIRED_ACTIVE_DEFINITIONS),
        "seed_checksum_verified": True,
    }


async def _run_live_import(
    *,
    seed: Path,
    expected_sha256: str,
    confirm_seed_sha256: str,
    backup_reference: str,
    restore_drill_reference: str,
) -> dict[str, Any]:
    """Execute the full non-dry-run guard order then transactional import."""
    # 1–2: load + validate + compute SHA (before any identity/DB mutation)
    data = load_seed(seed)
    validate_seed(data)
    actual_sha = file_checksum(seed)
    expected_units = len(data.get("units") or [])
    expected_definitions = len(data.get("definitions") or [])
    expected_aliases = sum(
        len(d.get("aliases") or []) for d in (data.get("definitions") or []) if isinstance(d, dict)
    )

    # 3–4: checksum authorization
    assert_seed_sha_authorization(
        actual_sha256=actual_sha,
        expected_sha256=expected_sha256,
        confirm_seed_sha256=confirm_seed_sha256,
    )

    # 5–9: identity + Category B (before any DB session)
    try:
        identity = identity_from_mapping(os.environ)
    except ValueError as exc:
        raise ValueError(f"data-plane identity unresolved: {exc}") from exc

    if identity.inferred_data_plane:
        raise ValueError(
            "Live Property Dictionary import refused: KARZAR_DATA_PLANE must be "
            "set explicitly to 'live' (inferred plane is not accepted)."
        )
    if identity.data_plane != "live":
        raise ValueError(
            "Live Property Dictionary import refused: KARZAR_DATA_PLANE must be "
            f"'live' (got {identity.data_plane!r}). Use "
            "scripts/seed_property_dictionary.py for development/catalog_staging."
        )
    extra = os.environ.get("KARZAR_LIVE_DB_DENYLIST")
    deny = live_db_denylist(extra=extra)
    db_lower = (identity.postgres_db or "").strip().lower()
    if db_lower not in deny:
        raise ValueError(
            "Live Property Dictionary import refused: POSTGRES_DB="
            f"{identity.postgres_db!r} is not a recognized LIVE database. "
            f"Approved live names: {', '.join(sorted(deny))}."
        )
    assert_category_b_production_write(
        allow_production_write=os.environ.get("KARZAR_ALLOW_PRODUCTION_WRITE"),
        ingestion_category=os.environ.get("KARZAR_INGESTION_CATEGORY"),
    )

    # 13–14: operator refs (before DB open; audit gates only)
    assert_operator_references(
        backup_reference=backup_reference,
        restore_drill_reference=restore_drill_reference,
    )

    # Lazy DB imports — keep seed-only dry-run free of Settings/DB bootstrap.
    from app.db.database import async_session_maker
    from app.services.property_dictionary_service import import_property_dictionary

    async with async_session_maker() as session:
        try:
            # 10–12: session + live sentinel (require_match)
            sentinel = await _read_environment_identity_plane(session)
            assert_live_dictionary_seed_import_allowed(
                identity,
                sentinel_plane=sentinel,
                allow_production_write=os.environ.get("KARZAR_ALLOW_PRODUCTION_WRITE"),
                ingestion_category=os.environ.get("KARZAR_INGESTION_CATEGORY"),
                extra_live_db_names=extra,
            )
            # Defensive re-check of sentinel helper (same rule, explicit name).
            assert_live_db_sentinel(sentinel_plane=sentinel)
            # 15–16: transactional import + commit
            result = await import_property_dictionary(session, seed_path=seed, dry_run=False)
            await session.commit()
            # 17: post-write verification
            verification = await _post_write_verify(
                session,
                expected_sha256=actual_sha,
                expected_units=expected_units,
                expected_definitions=expected_definitions,
                expected_aliases=expected_aliases,
            )
        except Exception:
            await session.rollback()
            raise

    return {
        "ok": True,
        "dry_run": False,
        "data_plane": identity.data_plane,
        "postgres_db": identity.postgres_db,
        "identity": format_identity_report(identity),
        "actual_sha256": actual_sha,
        "expected_sha256": expected_sha256.strip().lower(),
        "backup_reference": backup_reference.strip(),
        "restore_drill_reference": restore_drill_reference.strip(),
        "verification": verification,
        **result,
    }


async def _run(
    *,
    seed: Path,
    dry_run: bool,
    expected_sha256: str | None,
    confirm_seed_sha256: str | None,
    backup_reference: str | None,
    restore_drill_reference: str | None,
) -> int:
    if dry_run:
        try:
            report = _seed_only_dry_run_report(seed)
        except (PropertyDictionaryImportError, ValueError, OSError) as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
            return 1
        # Optional non-secret identity when resolvable (no mutate / no Category B).
        try:
            identity = identity_from_mapping(os.environ)
            report["data_plane_identity"] = format_identity_report(identity)
        except ValueError as exc:
            report["data_plane_identity"] = f"(unresolved: {exc})"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    try:
        if not expected_sha256 or not confirm_seed_sha256:
            raise ValueError(
                "Live Property Dictionary import refused: "
                "--expected-sha256 and --confirm-seed-sha256 are required."
            )
        if not backup_reference or not restore_drill_reference:
            raise ValueError(
                "Live Property Dictionary import refused: "
                "--backup-reference and --restore-drill-reference are required."
            )
        report = await _run_live_import(
            seed=seed,
            expected_sha256=expected_sha256,
            confirm_seed_sha256=confirm_seed_sha256,
            backup_reference=backup_reference,
            restore_drill_reference=restore_drill_reference,
        )
    except (PropertyDictionaryImportError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": repr(exc)}, ensure_ascii=False))
        return 1

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "LIVE-only Property Dictionary import "
            "(Category B + checksum + sentinel; ordinary importer unchanged)"
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
        help="Seed-only validation; zero database writes",
    )
    parser.add_argument(
        "--expected-sha256",
        default=None,
        help="Owner-approved seed SHA256 (required for non-dry-run)",
    )
    parser.add_argument(
        "--confirm-seed-sha256",
        default=None,
        help="Operator confirmation SHA256; must equal actual seed digest",
    )
    parser.add_argument(
        "--backup-reference",
        default=None,
        help="Non-secret backup artifact/drill id (audit gate; not restore proof)",
    )
    parser.add_argument(
        "--restore-drill-reference",
        default=None,
        help="Operator assertion that a restore drill was completed and reviewed",
    )
    args = parser.parse_args()
    raise SystemExit(
        asyncio.run(
            _run(
                seed=args.seed,
                dry_run=args.dry_run,
                expected_sha256=args.expected_sha256,
                confirm_seed_sha256=args.confirm_seed_sha256,
                backup_reference=args.backup_reference,
                restore_drill_reference=args.restore_drill_reference,
            )
        )
    )


if __name__ == "__main__":
    main()
