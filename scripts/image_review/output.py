"""Atomic pilot package publishing and ZIP creation."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import tempfile
import zipfile
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any

from scripts.image_audit.storage import (
    assert_disjoint_output_storage,
    assert_real_directory_no_symlink,
    prepare_output_dir,
)

from .contracts import ReviewError

PublishWriter = Callable[[Path], None]


def prepare_review_output_dir(
    path: Path, *, repository_root: Path, storage_root: Path
) -> Path:
    return prepare_output_dir(path, repository_root=repository_root, storage_root=storage_root)


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
    sio = io.StringIO()
    writer = csv.DictWriter(
        sio, fieldnames=list(fieldnames), extrasaction="ignore", lineterminator="\n"
    )
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


def write_checksums(output_dir: Path) -> Path:
    """Checksum all regular files under output_dir except checksums.sha256 itself."""
    lines: list[str] = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(output_dir).as_posix()
        if rel == "checksums.sha256":
            continue
        lines.append(f"{_stream_checksum(path)}  {rel}")
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


def publish_review_outputs(
    output_dir: Path,
    *,
    writers: Sequence[PublishWriter],
) -> None:
    staging_parent = output_dir.parent
    staging = Path(tempfile.mkdtemp(prefix=".img-review-staging.", dir=str(staging_parent)))
    try:
        for writer in writers:
            writer(staging)
        write_checksums(staging)
        _clear_output_dir(output_dir)
        for src in staging.rglob("*"):
            if src.is_dir():
                continue
            rel = src.relative_to(staging)
            dest = output_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_bytes(dest, src.read_bytes())
    except Exception:
        _clear_output_dir(output_dir)
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def create_pilot_zip(output_dir: Path, zip_path: Path) -> str:
    """ZIP pilot directory contents (no source originals). Returns SHA-256 of zip."""
    if zip_path.exists():
        raise ReviewError("output", f"zip already exists: {zip_path}")
    if not zip_path.is_absolute():
        raise ReviewError("output", "zip path must be absolute")
    assert_real_directory_no_symlink(output_dir, label="pilot-output")
    # zip must not land inside storage; caller validates placement
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(output_dir.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            rel = path.relative_to(output_dir).as_posix()
            # refuse accidental source tree names
            if rel.startswith("data/uploads/") or rel.endswith(".git"):
                raise ReviewError("output", f"refusing to zip suspicious path: {rel}")
            zf.write(path, arcname=f"{output_dir.name}/{rel}")
    return _stream_checksum(zip_path)


def assert_paths_safe(
    *,
    output_dir: Path,
    storage_root: Path,
    repository_root: Path,
    source_dir: Path,
) -> None:
    prepare_review_output_dir(
        output_dir, repository_root=repository_root, storage_root=storage_root
    )
    assert_disjoint_output_storage(output_dir, storage_root)
    # source inventory must not be the output
    try:
        output_dir.resolve().relative_to(source_dir.resolve())
        raise ReviewError("path", "output-dir must not be inside source-dir")
    except ValueError:
        pass
    try:
        source_dir.resolve().relative_to(output_dir.resolve())
        raise ReviewError("path", "source-dir must not be inside output-dir")
    except ValueError:
        pass
