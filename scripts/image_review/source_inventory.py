"""Load and verify the immutable IMG-02A-01 inventory snapshot."""

from __future__ import annotations

import csv
import hashlib
import json
import stat as stat_mod
from pathlib import Path
from typing import Any

from scripts.image_audit.contracts import AuditError
from scripts.image_audit.storage import (
    assert_no_symlink_ancestors,
    assert_real_directory_no_symlink,
)

from .contracts import (
    AUTHORITATIVE_CHECKSUMS_DIGEST,
    EXPECTED_SOURCE_SUMMARY,
    REQUIRED_SOURCE_FILES,
    ReviewError,
)


def _audit_to_review(exc: AuditError) -> ReviewError:
    msg = str(exc)
    if ": " in msg:
        msg = msg.split(": ", 1)[1]
    return ReviewError(exc.code, msg)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def assert_source_dir(path: Path) -> Path:
    if not path.is_absolute():
        raise ReviewError("source", f"source-dir must be absolute: {path}")
    try:
        assert_no_symlink_ancestors(path, label="source-dir")
    except AuditError as e:
        raise _audit_to_review(e) from e
    try:
        st = path.lstat()
    except OSError as e:
        raise ReviewError("source", f"source-dir lstat failed: {path}") from e
    if stat_mod.S_ISLNK(st.st_mode):
        raise ReviewError("source", f"source-dir must not be a symlink: {path}")
    if not stat_mod.S_ISDIR(st.st_mode):
        raise ReviewError("source", f"source-dir must be a directory: {path}")
    return path


def verify_checksum_manifest(
    source_dir: Path,
    *,
    expected_checksums_digest: str = AUTHORITATIVE_CHECKSUMS_DIGEST,
) -> dict[str, str]:
    """Verify checksums.sha256 digest and every listed member hash."""
    assert_source_dir(source_dir)
    checksums_path = source_dir / "checksums.sha256"
    if not checksums_path.is_file() or checksums_path.is_symlink():
        raise ReviewError("source", "checksums.sha256 missing or is a symlink")
    digest = _sha256_file(checksums_path)
    if digest != expected_checksums_digest:
        raise ReviewError(
            "source",
            f"checksums.sha256 digest mismatch: got {digest}, expected {expected_checksums_digest}",
        )

    mapping: dict[str, str] = {}
    for line in checksums_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            raise ReviewError("source", f"malformed checksums line: {line!r}")
        expected, name = parts[0], parts[1].lstrip("*").strip()
        if "/" in name or name.startswith(".") or ".." in name.split("/"):
            raise ReviewError("source", f"unsafe checksum member name: {name!r}")
        mapping[name] = expected

    for required in REQUIRED_SOURCE_FILES:
        if required == "checksums.sha256":
            continue
        if required not in mapping:
            raise ReviewError("source", f"required file missing from checksum manifest: {required}")

    for name, expected in sorted(mapping.items()):
        member = source_dir / name
        if member.is_symlink():
            raise ReviewError("source", f"checksum member must not be symlink: {name}")
        if not member.is_file():
            raise ReviewError("source", f"checksum member missing: {name}")
        actual = _sha256_file(member)
        if actual != expected:
            raise ReviewError("source", f"checksum mismatch for {name}: {actual} != {expected}")
    return mapping


def load_verified_summary(
    source_dir: Path,
    *,
    expected: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary_path = source_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    expect = EXPECTED_SOURCE_SUMMARY if expected is None else expected
    for key, value in expect.items():
        if summary.get(key) != value:
            raise ReviewError(
                "source",
                f"summary.{key} mismatch: got {summary.get(key)!r}, expected {value!r}",
            )
    return summary


def _coerce_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in {"true", "1", "yes"}:
        return True
    if s in {"false", "0", "no"}:
        return False
    return None


def _coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def load_inventory_rows(source_dir: Path, *, allowed_names: set[str]) -> list[dict[str, Any]]:
    """Read inventory.csv only if listed in the verified checksum manifest."""
    if "inventory.csv" not in allowed_names:
        raise ReviewError("source", "inventory.csv not in verified manifest")
    path = source_dir / "inventory.csv"
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row = dict(raw)
            row["image_id"] = _coerce_int(row.get("image_id"))
            row["product_id"] = _coerce_int(row.get("product_id"))
            row["brand_id"] = _coerce_int(row.get("brand_id"))
            row["category_id"] = _coerce_int(row.get("category_id"))
            row["byte_size"] = _coerce_int(row.get("byte_size"))
            row["width"] = _coerce_int(row.get("width"))
            row["height"] = _coerce_int(row.get("height"))
            row["display_order"] = _coerce_int(row.get("display_order"))
            row["local_exists"] = _coerce_bool(row.get("local_exists"))
            row["is_primary"] = _coerce_bool(row.get("is_primary"))
            rows.append(row)
    return rows


def load_verified_source(
    source_dir: Path,
    *,
    expected_checksums_digest: str = AUTHORITATIVE_CHECKSUMS_DIGEST,
    expected_summary: dict[str, Any] | None = None,
) -> tuple[dict[str, str], dict[str, Any], list[dict[str, Any]]]:
    mapping = verify_checksum_manifest(
        source_dir, expected_checksums_digest=expected_checksums_digest
    )
    summary = load_verified_summary(source_dir, expected=expected_summary)
    rows = load_inventory_rows(source_dir, allowed_names=set(mapping))
    return mapping, summary, rows


def assert_storage_root(path: Path) -> Path:
    try:
        return assert_real_directory_no_symlink(path, label="storage-root")
    except AuditError as e:
        raise _audit_to_review(e) from e
