"""Deterministic atomic CSV/JSON/checksum outputs for IMG-02A-01."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from .contracts import AuditError

OUTPUT_FILES = (
    "inventory.csv",
    "inventory.json",
    "product-coverage.csv",
    "product-coverage.json",
    "summary.json",
    "run-metadata.json",
    "broken-or-unavailable.csv",
    "remote-unverified.csv",
    "database-anomalies.csv",
    "duplicate-exact-sha.csv",
    "products-without-valid-image.csv",
    "products-with-multiple-images.csv",
    "unreferenced-storage-assets.csv",
    "rejected-storage-entries.csv",
    "checksums.sha256",
)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def atomic_write_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))


def write_json(path: Path, payload: Any) -> None:
    atomic_write_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[dict[str, Any]]) -> None:
    # Build in memory then atomic write for fail-closed completeness
    from io import StringIO

    sio = StringIO()
    writer = csv.DictWriter(sio, fieldnames=list(fieldnames), extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: _csv_cell(row.get(k)) for k in fieldnames})
    atomic_write_text(path, sio.getvalue())


def _csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list | tuple):
        return "|".join(str(x) for x in value)
    return str(value)


def write_checksums(output_dir: Path, filenames: Sequence[str]) -> Path:
    """SHA-256 of every generated file except checksums.sha256 itself."""
    lines: list[str] = []
    for name in sorted(filenames):
        if name == "checksums.sha256":
            continue
        path = output_dir / name
        if not path.is_file():
            raise AuditError("output", f"missing output for checksum: {name}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    out = output_dir / "checksums.sha256"
    atomic_write_text(out, "\n".join(lines) + ("\n" if lines else ""))
    return out
