"""Verify prior human-review batch packages used as exclusion inputs."""

from __future__ import annotations

import hashlib
import json
import re
import stat as stat_mod
from pathlib import Path
from typing import Any

from scripts.image_audit.contracts import AuditError
from scripts.image_audit.storage import assert_no_symlink_ancestors

from .contracts import REVIEW_SCHEMA_VERSION, ReviewError

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_PRIOR_FILES = (
    "batch-metadata.json",
    "summary.json",
    "asset-manifest.json",
    "checksums.sha256",
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _assert_absolute_real_dir(path: Path, *, label: str) -> Path:
    if not path.is_absolute():
        raise ReviewError("prior_batch", f"{label} must be absolute: {path}")
    try:
        assert_no_symlink_ancestors(path, label=label)
    except AuditError as e:
        msg = str(e)
        if ": " in msg:
            msg = msg.split(": ", 1)[1]
        raise ReviewError(e.code, msg) from e
    try:
        st = path.lstat()
    except OSError as e:
        raise ReviewError("prior_batch", f"{label} lstat failed: {path}") from e
    if stat_mod.S_ISLNK(st.st_mode):
        raise ReviewError("prior_batch", f"{label} must not be a symlink: {path}")
    if not stat_mod.S_ISDIR(st.st_mode):
        raise ReviewError("prior_batch", f"{label} must be a directory: {path}")
    return path


def _assert_disjoint(path: Path, other: Path, *, label: str, other_label: str) -> None:
    try:
        path.resolve().relative_to(other.resolve())
        raise ReviewError(
            "prior_batch",
            f"{label} must not overlap {other_label}: {path} vs {other}",
        )
    except ValueError:
        pass
    try:
        other.resolve().relative_to(path.resolve())
        raise ReviewError(
            "prior_batch",
            f"{other_label} must not overlap {label}: {other} vs {path}",
        )
    except ValueError:
        pass


def verify_prior_batch_checksums(batch_dir: Path) -> dict[str, str]:
    """Verify every listed checksums.sha256 member (no trust of directory name)."""
    checksums_path = batch_dir / "checksums.sha256"
    if not checksums_path.is_file() or checksums_path.is_symlink():
        raise ReviewError("prior_batch", "checksums.sha256 missing or is a symlink")

    mapping: dict[str, str] = {}
    for line in checksums_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            raise ReviewError("prior_batch", f"malformed checksums line: {line!r}")
        expected, name = parts[0], parts[1].lstrip("*").strip()
        if name.startswith("/") or name.startswith("..") or "/../" in f"/{name}/":
            raise ReviewError("prior_batch", f"unsafe checksum member name: {name!r}")
        if ".." in Path(name).parts:
            raise ReviewError("prior_batch", f"unsafe checksum member name: {name!r}")
        mapping[name] = expected

    for required in REQUIRED_PRIOR_FILES:
        if required == "checksums.sha256":
            continue
        if required not in mapping:
            raise ReviewError(
                "prior_batch",
                f"required file missing from checksum manifest: {required}",
            )

    for name, expected in sorted(mapping.items()):
        member = batch_dir / name
        if member.is_symlink():
            raise ReviewError("prior_batch", f"checksum member must not be symlink: {name}")
        if not member.is_file():
            raise ReviewError("prior_batch", f"checksum member missing: {name}")
        actual = _sha256_file(member)
        if actual != expected:
            raise ReviewError(
                "prior_batch",
                f"checksum mismatch for {name}: {actual} != {expected}",
            )
    return mapping


def _load_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise ReviewError("prior_batch", f"required JSON missing or symlink: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_asset_id(value: Any, *, context: str) -> str:
    text = str(value or "").strip().lower()
    if not _SHA256_RE.fullmatch(text):
        raise ReviewError("prior_batch", f"malformed prior Asset SHA in {context}: {value!r}")
    return text


def load_prior_batch_asset_ids(
    batch_dir: Path,
    *,
    repository_root: Path,
    storage_root: Path,
    output_dir: Path | None = None,
    known_source_asset_ids: set[str] | None = None,
) -> dict[str, Any]:
    """
    Verify one prior batch package and return exclusion metadata.

    Identity comes from batch-metadata.json / summary.json — never the directory name.
    """
    label = "prior-batch-dir"
    _assert_absolute_real_dir(batch_dir, label=label)
    _assert_disjoint(batch_dir, repository_root, label=label, other_label="repository")
    _assert_disjoint(batch_dir, storage_root, label=label, other_label="storage-root")
    if output_dir is not None:
        _assert_disjoint(batch_dir, output_dir, label=label, other_label="output-dir")

    verify_prior_batch_checksums(batch_dir)

    metadata = _load_json(batch_dir / "batch-metadata.json")
    summary = _load_json(batch_dir / "summary.json")
    manifest = _load_json(batch_dir / "asset-manifest.json")
    if not isinstance(manifest, list):
        raise ReviewError("prior_batch", "asset-manifest.json must be a list")

    schema_v = metadata.get("review_schema_version", summary.get("review_schema_version"))
    if schema_v != REVIEW_SCHEMA_VERSION:
        raise ReviewError(
            "prior_batch",
            f"review_schema_version must be {REVIEW_SCHEMA_VERSION}, got {schema_v!r}",
        )

    batch_id = str(metadata.get("batch_id") or summary.get("batch_id") or "").strip()
    if not batch_id:
        raise ReviewError("prior_batch", "prior batch_id missing from metadata/summary")

    manifest_ids: list[str] = []
    seen: set[str] = set()
    for row in manifest:
        if not isinstance(row, dict):
            raise ReviewError("prior_batch", "asset-manifest.json rows must be objects")
        aid = _normalize_asset_id(row.get("asset_id") or row.get("sha256"), context="manifest")
        if aid in seen:
            raise ReviewError("prior_batch", f"duplicate Asset ID inside prior batch {batch_id}: {aid}")
        seen.add(aid)
        manifest_ids.append(aid)

    summary_ids_raw = summary.get("selected_asset_ids")
    if not isinstance(summary_ids_raw, list):
        raise ReviewError("prior_batch", "summary.selected_asset_ids must be a list")
    summary_ids = [
        _normalize_asset_id(x, context="summary.selected_asset_ids") for x in summary_ids_raw
    ]
    if len(summary_ids) != len(set(summary_ids)):
        raise ReviewError("prior_batch", f"duplicate Asset ID in summary for prior batch {batch_id}")
    if sorted(summary_ids) != sorted(manifest_ids):
        raise ReviewError(
            "prior_batch",
            f"summary/manifest Asset ID mismatch for prior batch {batch_id}",
        )
    if set(summary_ids) != set(manifest_ids):
        raise ReviewError(
            "prior_batch",
            f"summary/manifest Asset ID set mismatch for prior batch {batch_id}",
        )

    if known_source_asset_ids is not None:
        unknown = sorted(set(manifest_ids) - known_source_asset_ids)
        if unknown:
            raise ReviewError(
                "prior_batch",
                f"unknown prior Asset ID absent from source inventory: {unknown[0]}",
            )

    return {
        "batch_id": batch_id,
        "task_id": metadata.get("task_id") or summary.get("task_id"),
        "review_schema_version": REVIEW_SCHEMA_VERSION,
        "selected_unique_assets": len(manifest_ids),
        "asset_ids": list(manifest_ids),
        "batch_dir": batch_dir.name,
    }


def load_prior_batch_exclusions(
    prior_batch_dirs: list[Path],
    *,
    repository_root: Path,
    storage_root: Path,
    output_dir: Path | None = None,
    known_source_asset_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Verify one or more prior batches; reject cross-batch Asset ID duplicates."""
    records: list[dict[str, Any]] = []
    excluded: list[str] = []
    seen: set[str] = set()
    batch_ids: list[str] = []

    for directory in prior_batch_dirs:
        record = load_prior_batch_asset_ids(
            directory,
            repository_root=repository_root,
            storage_root=storage_root,
            output_dir=output_dir,
            known_source_asset_ids=known_source_asset_ids,
        )
        for aid in record["asset_ids"]:
            if aid in seen:
                raise ReviewError(
                    "prior_batch",
                    f"duplicate Asset ID across prior batches: {aid}",
                )
            seen.add(aid)
            excluded.append(aid)
        batch_ids.append(record["batch_id"])
        records.append(record)

    return {
        "prior_batch_ids": batch_ids,
        "prior_batch_count": len(records),
        "excluded_prior_asset_count": len(excluded),
        "excluded_asset_ids": excluded,
        "prior_batches": records,
    }
