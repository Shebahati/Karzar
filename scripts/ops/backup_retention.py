#!/usr/bin/env python3
"""Deterministic local backup retention planning (no deletions)."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable, Literal

Decision = Literal[
    "KEEP_DAILY",
    "KEEP_WEEKLY",
    "KEEP_MONTHLY",
    "KEEP_UNKNOWN",
    "DELETE_CANDIDATE",
]

DB_NAME_RE = re.compile(r"^karzar_(\d{8})_(\d{6})\.sql\.gz$")
UPLOAD_NAME_RE = re.compile(r"^karzar_uploads_(\d{8})_(\d{6})\.tar\.gz$")

# Baseline filenames observed on production VPS (2026-09-15 audit).
DB_BASELINE_RE = re.compile(r"^karzar_prod_baseline_\d{8}_\d{6}\.sql\.gz$")


@dataclass(frozen=True)
class BackupFile:
    path: Path
    name: str
    size: int
    parsed_at: datetime | None
    kind: Literal["db", "upload", "unknown"]


@dataclass(frozen=True)
class Row:
    type: str
    timestamp: str
    size: int
    decision: Decision
    reason: str
    path: str


def _parse_stamp(day: str, time_part: str) -> datetime | None:
    try:
        return datetime.strptime(f"{day}_{time_part}", "%Y%m%d_%H%M%S").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


def classify_file(path: Path) -> BackupFile:
    name = path.name
    size = path.stat().st_size if path.exists() else 0
    if DB_NAME_RE.match(name) or DB_BASELINE_RE.match(name):
        m = DB_NAME_RE.match(name)
        parsed = _parse_stamp(m.group(1), m.group(2)) if m else None
        return BackupFile(path, name, size, parsed, "db")
    if UPLOAD_NAME_RE.match(name):
        m = UPLOAD_NAME_RE.match(name)
        assert m is not None
        parsed = _parse_stamp(m.group(1), m.group(2))
        return BackupFile(path, name, size, parsed, "upload")
    return BackupFile(path, name, size, None, "unknown")


def _newest_per_day(files: Iterable[BackupFile]) -> dict[date, BackupFile]:
    out: dict[date, BackupFile] = {}
    for f in files:
        if f.parsed_at is None:
            continue
        d = f.parsed_at.date()
        if d not in out or (f.parsed_at or datetime.min.replace(tzinfo=timezone.utc)) > (
            out[d].parsed_at or datetime.min.replace(tzinfo=timezone.utc)
        ):
            out[d] = f
    return out


def _newest_per_iso_week(files: Iterable[BackupFile]) -> dict[tuple[int, int], BackupFile]:
    out: dict[tuple[int, int], BackupFile] = {}
    for f in files:
        if f.parsed_at is None:
            continue
        iso = f.parsed_at.isocalendar()
        key = (iso.year, iso.week)
        if key not in out or (f.parsed_at or datetime.min.replace(tzinfo=timezone.utc)) > (
            out[key].parsed_at or datetime.min.replace(tzinfo=timezone.utc)
        ):
            out[key] = f
    return out


def _newest_per_month(files: Iterable[BackupFile]) -> dict[tuple[int, int], BackupFile]:
    out: dict[tuple[int, int], BackupFile] = {}
    for f in files:
        if f.parsed_at is None:
            continue
        key = (f.parsed_at.year, f.parsed_at.month)
        if key not in out or (f.parsed_at or datetime.min.replace(tzinfo=timezone.utc)) > (
            out[key].parsed_at or datetime.min.replace(tzinfo=timezone.utc)
        ):
            out[key] = f
    return out


def _sorted_days(days: list[date]) -> list[date]:
    return sorted(days, reverse=True)


def _sorted_weeks(weeks: list[tuple[int, int]]) -> list[tuple[int, int]]:
    return sorted(weeks, reverse=True)


def _sorted_months(months: list[tuple[int, int]]) -> list[tuple[int, int]]:
    return sorted(months, reverse=True)


def plan_db_retention(
    files: list[BackupFile],
    daily_count: int = 14,
    weekly_count: int = 8,
    monthly_count: int = 12,
) -> dict[Path, tuple[Decision, str]]:
    valid = [f for f in files if f.kind == "db" and f.parsed_at is not None]
    unknown = [f for f in files if f.kind == "db" and f.parsed_at is None]
    decisions: dict[Path, tuple[Decision, str]] = {}

    for f in unknown:
        decisions[f.path] = ("KEEP_UNKNOWN", "unparseable_or_noncanonical_db_name")

    per_day = _newest_per_day(valid)
    keep_days = set(_sorted_days(list(per_day.keys()))[:daily_count])
    for d in keep_days:
        decisions[per_day[d].path] = ("KEEP_DAILY", f"daily_slot:{d.isoformat()}")

    per_week = _newest_per_iso_week(valid)
    keep_weeks = set(_sorted_weeks(list(per_week.keys()))[:weekly_count])
    for w in keep_weeks:
        f = per_week[w]
        if f.path not in decisions:
            decisions[f.path] = ("KEEP_WEEKLY", f"weekly_slot:{w[0]}-W{w[1]:02d}")

    per_month = _newest_per_month(valid)
    keep_months = set(_sorted_months(list(per_month.keys()))[:monthly_count])
    for m in keep_months:
        f = per_month[m]
        if f.path not in decisions:
            decisions[f.path] = ("KEEP_MONTHLY", f"monthly_slot:{m[0]}-{m[1]:02d}")

    for f in valid:
        if f.path not in decisions:
            decisions[f.path] = ("DELETE_CANDIDATE", "outside_retention_union")

    return decisions


def plan_upload_retention(
    files: list[BackupFile],
    weekly_count: int = 8,
    monthly_count: int = 12,
) -> dict[Path, tuple[Decision, str]]:
    valid = [f for f in files if f.kind == "upload" and f.parsed_at is not None]
    unknown = [f for f in files if f.kind == "upload" and f.parsed_at is None]
    decisions: dict[Path, tuple[Decision, str]] = {}

    for f in unknown:
        decisions[f.path] = ("KEEP_UNKNOWN", "unparseable_upload_name")

    per_week = _newest_per_iso_week(valid)
    keep_weeks = set(_sorted_weeks(list(per_week.keys()))[:weekly_count])
    for w in keep_weeks:
        decisions[per_week[w].path] = ("KEEP_WEEKLY", f"weekly_slot:{w[0]}-W{w[1]:02d}")

    per_month = _newest_per_month(valid)
    keep_months = set(_sorted_months(list(per_month.keys()))[:monthly_count])
    for m in keep_months:
        f = per_month[m]
        if f.path not in decisions:
            decisions[f.path] = ("KEEP_MONTHLY", f"monthly_slot:{m[0]}-{m[1]:02d}")

    for f in valid:
        if f.path not in decisions:
            decisions[f.path] = ("DELETE_CANDIDATE", "outside_retention_union")

    return decisions


def build_rows(files: list[BackupFile], decisions: dict[Path, tuple[Decision, str]]) -> list[Row]:
    rows: list[Row] = []
    for f in sorted(files, key=lambda x: x.name):
        dec, reason = decisions.get(f.path, ("KEEP_UNKNOWN", "not_classified"))
        ts = f.parsed_at.isoformat() if f.parsed_at else "invalid"
        rows.append(
            Row(
                type=f.kind,
                timestamp=ts,
                size=f.size,
                decision=dec,
                reason=reason,
                path=str(f.path),
            )
        )
    return rows


def summarize(rows: list[Row]) -> dict[str, int]:
    def count(kind: str, decision: Decision) -> int:
        return sum(1 for r in rows if r.type == kind and r.decision == decision)

    def bytes_delete(kind: str) -> int:
        return sum(r.size for r in rows if r.type == kind and r.decision == "DELETE_CANDIDATE")

    return {
        "DB_BACKUPS_TOTAL": sum(1 for r in rows if r.type == "db"),
        "DB_BACKUPS_KEEP": sum(
            1 for r in rows if r.type == "db" and r.decision != "DELETE_CANDIDATE"
        ),
        "DB_BACKUPS_DELETE_CANDIDATES": count("db", "DELETE_CANDIDATE"),
        "DB_BACKUP_BYTES_RECLAIMABLE": bytes_delete("db"),
        "UPLOAD_BACKUPS_TOTAL": sum(1 for r in rows if r.type == "upload"),
        "UPLOAD_BACKUPS_KEEP": sum(
            1 for r in rows if r.type == "upload" and r.decision != "DELETE_CANDIDATE"
        ),
        "UPLOAD_BACKUPS_DELETE_CANDIDATES": count("upload", "DELETE_CANDIDATE"),
        "UPLOAD_BACKUP_BYTES_RECLAIMABLE": bytes_delete("upload"),
    }


class RetentionDeleteError(Exception):
    """Unsafe or invalid retention delete."""


def _validate_delete_candidate(candidate: Path, backup_root: Path) -> Path:
    """Fail closed unless candidate is a direct regular file child of backup_root."""
    if ".." in candidate.parts:
        raise RetentionDeleteError("path_traversal")

    try:
        lst = candidate.lstat()
    except OSError as exc:
        raise RetentionDeleteError(f"lstat_failed:{exc}") from exc

    if stat.S_ISLNK(lst.st_mode):
        raise RetentionDeleteError("symlink_refused")

    if not stat.S_ISREG(lst.st_mode):
        raise RetentionDeleteError("not_regular_file")

    try:
        root = backup_root.resolve(strict=True)
        parent = candidate.parent.resolve()
        resolved = candidate.resolve()
    except OSError as exc:
        raise RetentionDeleteError(f"resolve_failed:{exc}") from exc

    if parent != root:
        raise RetentionDeleteError("not_direct_child_of_backup_root")

    try:
        common = os.path.commonpath([str(resolved), str(root)])
    except ValueError:
        raise RetentionDeleteError("outside_backup_root")

    if common != str(root):
        raise RetentionDeleteError("outside_backup_root")

    # Prefix-confusion guard (e.g. .../backups-evil/file).
    if not str(resolved).startswith(str(root) + os.sep):
        raise RetentionDeleteError("prefix_confusion")

    return resolved


def apply_retention_deletes(payload: dict, backup_dir: Path) -> dict[str, int]:
    root = backup_dir.resolve()
    db_deleted = 0
    upload_deleted = 0
    bytes_reclaimed = 0
    for row in payload["rows"]:
        if row["decision"] != "DELETE_CANDIDATE":
            continue
        original = Path(row["path"])
        target = _validate_delete_candidate(original, root)
        size = target.stat().st_size
        os.remove(target)
        bytes_reclaimed += size
        if row["type"] == "db":
            db_deleted += 1
        elif row["type"] == "upload":
            upload_deleted += 1
    return {
        "DB_BACKUPS_DELETED": db_deleted,
        "UPLOAD_BACKUPS_DELETED": upload_deleted,
        "BACKUP_BYTES_RECLAIMED": bytes_reclaimed,
    }


def plan_directory(backup_dir: Path) -> dict:
    if not backup_dir.is_dir():
        raise FileNotFoundError(f"backup directory missing: {backup_dir}")

    all_files = [classify_file(p) for p in backup_dir.iterdir() if p.is_file() and not p.is_symlink()]
    db_files = [f for f in all_files if f.kind == "db"]
    upload_files = [f for f in all_files if f.kind == "upload"]
    other = [f for f in all_files if f.kind == "unknown"]

    db_dec = plan_db_retention(db_files)
    up_dec = plan_upload_retention(upload_files)
    other_dec = {f.path: ("KEEP_UNKNOWN", "non_backup_filename") for f in other}

    decisions = {**db_dec, **up_dec, **other_dec}
    rows = build_rows(all_files, decisions)
    summary = summarize(rows)
    return {"rows": [r.__dict__ for r in rows], "summary": summary}


def main() -> int:
    parser = argparse.ArgumentParser(description="Karzar backup retention plan (no deletes).")
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--json", action="store_true", help="Emit JSON only on stdout")
    parser.add_argument(
        "--apply-deletes",
        action="store_true",
        help="Apply DELETE_CANDIDATE rows (internal; requires JSON plan on stdin).",
    )
    args = parser.parse_args()
    backup_dir = args.backup_dir.resolve()
    if args.apply_deletes:
        payload = json.load(sys.stdin)
        try:
            result = apply_retention_deletes(payload, backup_dir)
        except (RetentionDeleteError, OSError) as exc:
            print(json.dumps({"error": str(exc)}), file=sys.stderr)
            return 1
        for key, value in result.items():
            print(f"{key}={value}")
        return 0
    try:
        payload = plan_directory(backup_dir)
    except OSError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
