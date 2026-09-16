"""Canonical import-plan hashing (approval identity), separate from volatile metadata."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

# Top-level manifest keys excluded from owner approval identity (non-semantic metadata).
VOLATILE_MANIFEST_KEYS = frozenset(
    {
        "git_sha",
        "karzar_snapshot_timestamp",
        "generated_at",
        "IMPORT_MANIFEST_SHA256",
        "CANONICAL_IMPORT_PLAN_SHA256",
    }
)

# Per-entry `source_timestamp` is excluded: crawl provenance is bound at manifest level via
# `source_crawl_timestamp` (semantic). Row timestamps are run metadata only.
VOLATILE_ENTRY_KEYS = frozenset({"source_timestamp"})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


def write_manifest_sidecar_sha256(manifest_path: Path) -> str:
    """Write import_manifest.json.sha256 for the final on-disk bytes. Returns digest."""
    digest = sha256_file(manifest_path)
    sidecar = manifest_path.with_name(manifest_path.name + ".sha256")
    sidecar.write_text(digest + "\n", encoding="utf-8")
    return digest
