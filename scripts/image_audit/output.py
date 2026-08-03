"""Deterministic atomic CSV/JSON/checksum outputs for IMG-02A-01."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Callable, Iterable, Sequence
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

PublishWriter = Callable[[Path], None]


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


def _stream_checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def write_checksums(output_dir: Path, filenames: Sequence[str]) -> Path:
    """SHA-256 of every generated file except checksums.sha256 itself."""
    lines: list[str] = []
    for name in sorted(filenames):
        if name == "checksums.sha256":
            continue
        path = output_dir / name
        if not path.is_file():
            raise AuditError("output", f"missing output for checksum: {name}")
        digest = _stream_checksum(path)
        lines.append(f"{digest}  {name}")
    out = output_dir / "checksums.sha256"
    atomic_write_text(out, "\n".join(lines) + ("\n" if lines else ""))
    return out


def _clear_output_dir(output_dir: Path) -> None:
    if not output_dir.exists():
        return
    for child in output_dir.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def publish_inventory_outputs(
    output_dir: Path,
    *,
    writers: Sequence[PublishWriter],
    checksum_names: Sequence[str],
) -> None:
    """Stage all outputs outside output_dir; publish atomically or leave output empty."""
    staging_parent = output_dir.parent
    staging = Path(tempfile.mkdtemp(prefix=".img-audit-staging.", dir=str(staging_parent)))
    try:
        for writer in writers:
            writer(staging)
        checksum_path = write_checksums(staging, checksum_names)
        publish_names = sorted(set(checksum_names) | {checksum_path.name})
        for name in publish_names:
            src = staging / name
            if not src.is_file():
                raise AuditError("output", f"staging missing file: {name}")
            atomic_write_bytes(output_dir / name, src.read_bytes())
    except Exception:
        _clear_output_dir(output_dir)
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
