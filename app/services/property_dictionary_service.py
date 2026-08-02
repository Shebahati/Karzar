"""Property Dictionary import + validation (Prompt 11A / ADR-013).

Git seed is authoring SoT. Import is explicit, transactional, and idempotent.
Does not touch Products, Product Types, Facts, templates, or JSONB dual-write.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge import (
    DICTIONARY_STATUSES,
    PROPERTY_DATA_TYPES,
    UNIT_DIMENSIONS,
    KnowledgePropertyAlias,
    KnowledgePropertyDefinition,
    KnowledgeUnit,
)

DEFAULT_SEED_PATH = Path(
    "docs/architecture/specs/seeds/property-dictionary-v0-metrology.json"
)

_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class PropertyDictionaryImportError(ValueError):
    """Seed validation or import integrity failure (no partial commit)."""


def normalize_alias(text: str) -> str:
    """Deterministic alias identity: NFC + strip + casefold."""
    return unicodedata.normalize("NFC", text).strip().casefold()


def file_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_seed(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise PropertyDictionaryImportError(f"seed file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PropertyDictionaryImportError(f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise PropertyDictionaryImportError("seed root must be an object")
    return data


def validate_seed(data: dict[str, Any]) -> None:
    if data.get("dual_write") != "forbidden":
        raise PropertyDictionaryImportError("dual_write must be 'forbidden'")
    if data.get("scope") != "metrology":
        raise PropertyDictionaryImportError("scope must be 'metrology' for v0 seed")
    version = data.get("version")
    if not isinstance(version, str) or not version:
        raise PropertyDictionaryImportError("seed version required")

    units = data.get("units")
    definitions = data.get("definitions")
    if not isinstance(units, list) or not units:
        raise PropertyDictionaryImportError("units[] required")
    if not isinstance(definitions, list) or not definitions:
        raise PropertyDictionaryImportError("definitions[] required")

    unit_by_dim: dict[str, set[str]] = {}
    seen_unit_keys: set[tuple[str, str]] = set()
    for unit in units:
        if not isinstance(unit, dict):
            raise PropertyDictionaryImportError("unit must be object")
        dimension = unit.get("dimension")
        canonical = unit.get("canonical")
        aliases = unit.get("aliases", [])
        if dimension not in UNIT_DIMENSIONS:
            raise PropertyDictionaryImportError(f"unknown unit dimension: {dimension}")
        if not isinstance(canonical, str) or not canonical:
            raise PropertyDictionaryImportError("unit.canonical required")
        key = (dimension, canonical)
        if key in seen_unit_keys:
            raise PropertyDictionaryImportError(f"duplicate unit {key}")
        seen_unit_keys.add(key)
        unit_by_dim.setdefault(dimension, set()).add(canonical)
        if not isinstance(aliases, list) or not all(isinstance(a, str) for a in aliases):
            raise PropertyDictionaryImportError("unit.aliases must be string list")

    seen_def_ids: set[str] = set()
    seen_keys: set[str] = set()
    pending_aliases: list[tuple[str, str]] = []
    for defn in definitions:
        if not isinstance(defn, dict):
            raise PropertyDictionaryImportError("definition must be object")
        definition_id = defn.get("definition_id")
        key = defn.get("key")
        data_type = defn.get("data_type")
        status = defn.get("status")
        if not isinstance(definition_id, str) or not definition_id:
            raise PropertyDictionaryImportError("definition_id required")
        if definition_id in seen_def_ids:
            raise PropertyDictionaryImportError(f"duplicate definition_id: {definition_id}")
        seen_def_ids.add(definition_id)
        if not isinstance(key, str) or not _KEY_RE.match(key):
            raise PropertyDictionaryImportError(f"invalid property key: {key!r}")
        if key in seen_keys:
            raise PropertyDictionaryImportError(f"duplicate property key: {key}")
        seen_keys.add(key)
        if data_type not in PROPERTY_DATA_TYPES:
            raise PropertyDictionaryImportError(f"invalid data_type: {data_type}")
        if status not in DICTIONARY_STATUSES:
            raise PropertyDictionaryImportError(f"invalid definition status: {status}")
        for field in ("label_en", "label_fa", "validation", "version"):
            if field not in defn:
                raise PropertyDictionaryImportError(
                    f"definition {definition_id} missing {field}"
                )
        if not isinstance(defn["validation"], dict):
            raise PropertyDictionaryImportError(
                f"definition {definition_id} validation must be object"
            )
        for flag in ("comparable", "filterable", "customer_facing"):
            if flag not in defn or not isinstance(defn[flag], bool):
                raise PropertyDictionaryImportError(
                    f"definition {definition_id} {flag} must be bool"
                )

        unit_dimension = defn.get("unit_dimension")
        default_unit = defn.get("default_unit")
        if unit_dimension is not None:
            if unit_dimension not in UNIT_DIMENSIONS:
                raise PropertyDictionaryImportError(
                    f"unknown unit_dimension on {definition_id}: {unit_dimension}"
                )
            if unit_dimension not in unit_by_dim:
                raise PropertyDictionaryImportError(
                    f"no units registered for dimension {unit_dimension}"
                )
            if default_unit is not None and default_unit not in unit_by_dim[unit_dimension]:
                raise PropertyDictionaryImportError(
                    f"default_unit {default_unit!r} incompatible with {unit_dimension}"
                )
        elif default_unit is not None:
            raise PropertyDictionaryImportError(
                f"default_unit without unit_dimension on {definition_id}"
            )

        enum_values = defn.get("enum_values")
        if data_type == "enum":
            if not isinstance(enum_values, list) or not enum_values:
                raise PropertyDictionaryImportError(
                    f"enum definition {definition_id} requires enum_values"
                )
        elif enum_values is not None:
            raise PropertyDictionaryImportError(
                f"enum_values only allowed for enum datatype ({definition_id})"
            )

        validation = defn["validation"]
        numeric_markers = {"min", "max", "exclusive_min", "exclusive_max", "min_inclusive", "max_inclusive"}
        if data_type not in ("integer", "number", "quantity", "range") and any(
            k in validation for k in numeric_markers
        ):
            # allow_qualifier on quantity is fine; range keys on non-numeric are not
            if any(k in validation for k in ("min", "max", "exclusive_min", "exclusive_max")):
                raise PropertyDictionaryImportError(
                    f"numeric range rules invalid for data_type={data_type} ({definition_id})"
                )

        aliases = defn.get("aliases", [])
        if not isinstance(aliases, list) or not aliases:
            raise PropertyDictionaryImportError(
                f"definition {definition_id} requires non-empty aliases[]"
            )
        if not all(isinstance(a, str) and a.strip() for a in aliases):
            raise PropertyDictionaryImportError(
                f"definition {definition_id} aliases must be non-empty strings"
            )
        for alias in aliases:
            pending_aliases.append((normalize_alias(alias), definition_id))

    seen_norm: dict[str, str] = {}
    for norm, definition_id in pending_aliases:
        if norm in seen_norm and seen_norm[norm] != definition_id:
            raise PropertyDictionaryImportError(
                f"alias collision '{norm}' maps to both {seen_norm[norm]} and {definition_id}"
            )
        seen_norm[norm] = definition_id


def _empty_counters() -> dict[str, int]:
    return {
        "units_scanned": 0,
        "units_created": 0,
        "units_updated": 0,
        "units_unchanged": 0,
        "properties_scanned": 0,
        "properties_created": 0,
        "properties_updated": 0,
        "properties_unchanged": 0,
        "aliases_scanned": 0,
        "aliases_created": 0,
        "aliases_updated": 0,
        "aliases_unchanged": 0,
        "deprecated_or_missing": 0,
        "failed": 0,
    }


def _unit_payload(unit: dict[str, Any], *, seed_version: str, seed_checksum: str) -> dict[str, Any]:
    return {
        "dimension": unit["dimension"],
        "canonical_code": unit["canonical"],
        "aliases": list(unit.get("aliases") or []),
        "conversion_table_version": unit.get("conversion_table_version"),
        "label_en": unit.get("label_en"),
        "label_fa": unit.get("label_fa"),
        "status": unit.get("status") or "active",
        "seed_version": seed_version,
        "seed_checksum": seed_checksum,
    }


def _definition_payload(
    defn: dict[str, Any], *, seed_version: str, seed_checksum: str
) -> dict[str, Any]:
    return {
        "definition_id": defn["definition_id"],
        "key": defn["key"],
        "data_type": defn["data_type"],
        "unit_dimension": defn.get("unit_dimension"),
        "default_unit": defn.get("default_unit"),
        "label_en": defn["label_en"],
        "label_fa": defn["label_fa"],
        "description_en": defn.get("description_en"),
        "description_fa": defn.get("description_fa"),
        "validation": dict(defn["validation"]),
        "enum_values": defn.get("enum_values"),
        "comparable": bool(defn["comparable"]),
        "filterable": bool(defn["filterable"]),
        "customer_facing": bool(defn["customer_facing"]),
        "version": defn["version"],
        "status": defn["status"],
        "steward": defn.get("steward"),
        "supersedes_definition_id": defn.get("supersedes"),
        "seed_version": seed_version,
        "seed_checksum": seed_checksum,
    }


def _row_matches(row: Any, payload: dict[str, Any], fields: tuple[str, ...]) -> bool:
    for field in fields:
        current = getattr(row, field)
        expected = payload[field]
        if current != expected:
            return False
    return True


async def import_property_dictionary(
    db: AsyncSession,
    *,
    seed_path: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Validate + upsert dictionary tables. Caller commits unless dry_run."""
    counters = _empty_counters()
    path = seed_path.resolve()
    data = load_seed(path)
    validate_seed(data)
    checksum = file_checksum(path)
    seed_version = str(data["version"])

    if dry_run:
        counters["units_scanned"] = len(data["units"])
        counters["properties_scanned"] = len(data["definitions"])
        counters["aliases_scanned"] = sum(
            len(d.get("aliases") or []) for d in data["definitions"]
        )
        return {
            "dry_run": True,
            "seed_version": seed_version,
            "seed_checksum": checksum,
            "counters": counters,
        }

    unit_fields = (
        "dimension",
        "canonical_code",
        "aliases",
        "conversion_table_version",
        "label_en",
        "label_fa",
        "status",
        "seed_version",
        "seed_checksum",
    )
    def_fields = (
        "definition_id",
        "key",
        "data_type",
        "unit_dimension",
        "default_unit",
        "label_en",
        "label_fa",
        "description_en",
        "description_fa",
        "validation",
        "enum_values",
        "comparable",
        "filterable",
        "customer_facing",
        "version",
        "status",
        "steward",
        "supersedes_definition_id",
        "seed_version",
        "seed_checksum",
    )

    try:
        for unit in data["units"]:
            counters["units_scanned"] += 1
            payload = _unit_payload(unit, seed_version=seed_version, seed_checksum=checksum)
            unit_row = (
                await db.execute(
                    select(KnowledgeUnit).where(
                        KnowledgeUnit.dimension == payload["dimension"],
                        KnowledgeUnit.canonical_code == payload["canonical_code"],
                    )
                )
            ).scalar_one_or_none()
            if unit_row is None:
                db.add(KnowledgeUnit(**payload))
                counters["units_created"] += 1
            elif _row_matches(unit_row, payload, unit_fields):
                counters["units_unchanged"] += 1
            else:
                for field, value in payload.items():
                    setattr(unit_row, field, value)
                counters["units_updated"] += 1

        await db.flush()

        for defn in data["definitions"]:
            counters["properties_scanned"] += 1
            payload = _definition_payload(
                defn, seed_version=seed_version, seed_checksum=checksum
            )
            def_row = (
                await db.execute(
                    select(KnowledgePropertyDefinition).where(
                        KnowledgePropertyDefinition.definition_id
                        == payload["definition_id"]
                    )
                )
            ).scalar_one_or_none()
            if def_row is None:
                db.add(KnowledgePropertyDefinition(**payload))
                counters["properties_created"] += 1
            elif _row_matches(def_row, payload, def_fields):
                counters["properties_unchanged"] += 1
            else:
                # Never rename stable identity keys via display-driven update path.
                if def_row.key != payload["key"]:
                    raise PropertyDictionaryImportError(
                        f"refusing to rename key for {payload['definition_id']}"
                    )
                for field, value in payload.items():
                    if field == "key":
                        continue
                    setattr(def_row, field, value)
                counters["properties_updated"] += 1

        await db.flush()

        for defn in data["definitions"]:
            definition_id = defn["definition_id"]
            for alias in defn.get("aliases") or []:
                counters["aliases_scanned"] += 1
                norm = normalize_alias(alias)
                payload = {
                    "definition_id": definition_id,
                    "alias": alias,
                    "alias_normalized": norm,
                    "source_kind": "seed_inline",
                    "language": None,
                    "status": "active",
                }
                alias_row = (
                    await db.execute(
                        select(KnowledgePropertyAlias).where(
                            KnowledgePropertyAlias.alias_normalized == norm
                        )
                    )
                ).scalar_one_or_none()
                if alias_row is None:
                    db.add(KnowledgePropertyAlias(**payload))
                    counters["aliases_created"] += 1
                elif (
                    alias_row.definition_id == definition_id
                    and alias_row.alias == alias
                    and alias_row.source_kind == "seed_inline"
                    and alias_row.status == "active"
                ):
                    counters["aliases_unchanged"] += 1
                elif alias_row.definition_id != definition_id:
                    raise PropertyDictionaryImportError(
                        f"alias '{alias}' already bound to {alias_row.definition_id}"
                    )
                else:
                    alias_row.alias = alias
                    alias_row.source_kind = "seed_inline"
                    alias_row.status = "active"
                    counters["aliases_updated"] += 1

        # Missing seed rows: report only (no hard-delete / no auto-deprecate).
        seed_def_ids = {d["definition_id"] for d in data["definitions"]}
        db_defs = (
            await db.execute(select(KnowledgePropertyDefinition.definition_id))
        ).scalars().all()
        for definition_id in db_defs:
            if definition_id not in seed_def_ids:
                counters["deprecated_or_missing"] += 1

        await db.flush()
    except Exception:
        counters["failed"] += 1
        await db.rollback()
        raise

    return {
        "dry_run": False,
        "seed_version": seed_version,
        "seed_checksum": checksum,
        "counters": counters,
    }
