"""Canonical import-plan hashing (approval identity), separate from volatile metadata."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

# Top-level manifest keys excluded from owner approval identity.
VOLATILE_MANIFEST_KEYS = frozenset(
    {
        "git_sha",
        "karzar_snapshot_timestamp",
        "generated_at",
        "IMPORT_MANIFEST_SHA256",
        "CANONICAL_IMPORT_PLAN_SHA256",
        "RAW_MANIFEST_FILE_SHA256",
    }
)

# Per-entry keys that may vary between runs without changing execution semantics.
VOLATILE_ENTRY_KEYS = frozenset({"source_timestamp"})


def canonical_operation_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return entries with volatile per-row fields stripped."""
    cleaned: list[dict[str, Any]] = []
    for entry in entries:
        row = deepcopy(entry)
        for key in VOLATILE_ENTRY_KEYS:
            row.pop(key, None)
        cleaned.append(row)
    return cleaned


def canonical_import_plan_body(manifest: dict[str, Any]) -> dict[str, Any]:
    """Semantic payload used for owner approval hashing."""
    body = {k: v for k, v in manifest.items() if k not in VOLATILE_MANIFEST_KEYS}
    entries = body.get("entries")
    if isinstance(entries, list):
        body["entries"] = canonical_operation_entries(entries)
    return body


def canonical_import_plan_sha256(manifest: dict[str, Any]) -> str:
    payload = json.dumps(
        canonical_import_plan_body(manifest),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def raw_manifest_file_sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def attach_manifest_hashes(manifest: dict[str, Any], *, raw_file_bytes: bytes | None = None) -> dict[str, Any]:
    """Add CANONICAL_IMPORT_PLAN_SHA256 and optional RAW_MANIFEST_FILE_SHA256 in-place."""
    manifest["CANONICAL_IMPORT_PLAN_SHA256"] = canonical_import_plan_sha256(manifest)
    if raw_file_bytes is not None:
        manifest["RAW_MANIFEST_FILE_SHA256"] = raw_manifest_file_sha256(raw_file_bytes)
    return manifest
