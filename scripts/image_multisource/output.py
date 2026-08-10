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


def list_packaged_payload_files(output_dir: Path) -> list[str]:
    """Relative paths of every regular file under output_dir except checksums.sha256."""
    out: list[str] = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(output_dir).as_posix()
        if rel == "checksums.sha256":
            continue
        out.append(rel)
    return out


def write_full_checksums(output_dir: Path) -> dict[str, Any]:
    members = list_packaged_payload_files(output_dir)
    digest = write_checksums(output_dir, members)
    regular = len(members) + 1  # include checksums.sha256
    return {
        "checksums_digest": digest,
        "checksum_entries": len(members),
        "regular_file_count": regular,
        "checksum_uncovered_files": 0,
        "members": members,
    }


def verify_checksums(output_dir: Path) -> dict[str, Any]:
    chk = output_dir / "checksums.sha256"
    if not chk.is_file():
        raise MultisourceError("output", "checksums.sha256 missing")
    failures = 0
    entries = 0
    listed: set[str] = set()
    for line in chk.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        sha, name = line.split("  ", 1)
        entries += 1
        listed.add(name)
        path = output_dir / name
        if not path.is_file() or sha256_file(path) != sha:
            failures += 1
    expected = set(list_packaged_payload_files(output_dir))
    uncovered = sorted(expected - listed)
    return {
        "checksum_entries": entries,
        "checksum_failures": failures,
        "checksum_uncovered_files": len(uncovered),
        "uncovered": uncovered,
        "regular_file_count": len(expected) + 1,
    }
