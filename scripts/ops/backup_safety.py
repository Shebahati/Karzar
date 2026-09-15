#!/usr/bin/env python3
"""Backup safety gate helpers (filename-authoritative timestamps)."""

from __future__ import annotations

import gzip
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

CANONICAL_DB_RE = re.compile(r"^karzar_(\d{8})_(\d{6})\.sql\.gz$")

# Allow modest clock skew between backup filename (UTC) and host clock.
MAX_FUTURE_SKEW = timedelta(minutes=15)


@dataclass(frozen=True)
class CanonicalDbBackup:
    path: Path
    stamp: datetime


def parse_canonical_db_stamp(name: str) -> datetime | None:
    m = CANONICAL_DB_RE.match(name)
    if not m:
        return None
    try:
        return datetime.strptime(f"{m.group(1)}_{m.group(2)}", "%Y%m%d_%H%M%S").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


def list_canonical_db_backups(backup_dir: Path) -> list[CanonicalDbBackup]:
    out: list[CanonicalDbBackup] = []
    if not backup_dir.is_dir():
        return out
    for entry in backup_dir.iterdir():
        if entry.is_symlink():
            continue
        if not entry.is_file():
            continue
        stamp = parse_canonical_db_stamp(entry.name)
        if stamp is None:
            continue
        out.append(CanonicalDbBackup(entry.resolve(), stamp))
    return out


def evaluate_backup_safety_gate(
    backup_dir: Path,
    now: datetime | None = None,
    max_age: timedelta = timedelta(hours=36),
) -> tuple[bool, str]:
    """Return (pass, reason). Filename UTC timestamp is authoritative for freshness."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    try:
        root = backup_dir.resolve()
    except OSError as exc:
        return False, f"backup_dir_resolve_failed:{exc}"

    if not root.is_dir():
        return False, "backup_dir_missing"

    canonical = list_canonical_db_backups(root)
    if len(canonical) < 2:
        return False, "fewer_than_two_canonical_db_backups"

    latest = max(canonical, key=lambda b: b.stamp)
    latest_path = latest.path

    if latest_path.is_symlink():
        return False, "latest_is_symlink"
    if not latest_path.is_file():
        return False, "latest_not_regular_file"

    if latest.stamp > now + MAX_FUTURE_SKEW:
        return False, "latest_filename_timestamp_in_future"

    age = now - latest.stamp
    if age > max_age:
        return False, f"latest_backup_older_than_{int(max_age.total_seconds())}s"

    try:
        size = latest_path.stat().st_size
    except OSError as exc:
        return False, f"stat_failed:{exc}"
    if size <= 0:
        return False, "latest_zero_bytes"

    try:
        with gzip.open(latest_path, "rb") as fh:
            fh.read(1)
    except (OSError, gzip.BadGzipFile):
        return False, "gzip_integrity_failed"

    return True, "ok"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: backup_safety.py <backup_dir>", file=sys.stderr)
        return 2
    ok, reason = evaluate_backup_safety_gate(Path(sys.argv[1]))
    print(f"BACKUP_SAFETY_GATE={'PASS' if ok else 'FAIL'}")
    print(f"REASON={reason}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
