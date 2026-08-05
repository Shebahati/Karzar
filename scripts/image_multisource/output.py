"""External-only output helpers for IMG-02C."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from . import MultisourceError


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def assert_external_output(path: Path, repo_root: Path) -> Path:
    if not path.is_absolute():
        raise MultisourceError("output", f"output-dir must be absolute: {path}")
    if path.is_symlink():
        raise MultisourceError("output", f"output-dir must not be a symlink: {path}")
    try:
        path.resolve().relative_to(repo_root.resolve())
        raise MultisourceError("output", f"output-dir must be outside repository: {path}")
    except ValueError:
        pass
    return path


def ensure_absent_or_empty(path: Path) -> None:
    if path.exists():
        if path.is_symlink() or not path.is_dir():
            raise MultisourceError("output", f"invalid output path: {path}")
        if list(path.iterdir()):
            raise MultisourceError("output", f"output-dir is not empty: {path}")
        return
    path.mkdir(parents=True, exist_ok=False)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_checksums(output_dir: Path, members: list[str]) -> str:
    lines = [f"{sha256_file(output_dir / name)}  {name}" for name in members]
    (output_dir / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sha256_file(output_dir / "checksums.sha256")
