"""CLI: import Property Dictionary Git seed into Postgres overlay (11A).

Usage:
  python scripts/seed_property_dictionary.py
  python scripts/seed_property_dictionary.py --seed PATH
  python scripts/seed_property_dictionary.py --dry-run

Local/Category A only. Does not touch Products, Facts, or JSONB dual-write.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.database import async_session_maker
from app.services.property_dictionary_service import (
    DEFAULT_SEED_PATH,
    PropertyDictionaryImportError,
    import_property_dictionary,
)


async def _run(seed: Path, dry_run: bool) -> int:
    async with async_session_maker() as session:
        try:
            result = await import_property_dictionary(
                session, seed_path=seed, dry_run=dry_run
            )
            if not dry_run:
                await session.commit()
        except PropertyDictionaryImportError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
            return 1
        except Exception as exc:  # noqa: BLE001 — surface unexpected failures to CLI
            print(json.dumps({"ok": False, "error": repr(exc)}, ensure_ascii=False))
            return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Property Dictionary v0 seed")
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
