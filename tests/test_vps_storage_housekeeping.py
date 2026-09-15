"""Tests for VPS storage housekeeping (retention + shell safety)."""

from __future__ import annotations

import gzip
import json
import os
import re
import subprocess
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.ops.backup_retention import (
    classify_file,
    plan_db_retention,
    plan_directory,
    plan_upload_retention,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
HOUSEKEEPING_SH = REPO_ROOT / "scripts/ops/vps_storage_housekeeping.sh"
LIB_SH = REPO_ROOT / "scripts/ops/vps_storage_housekeeping_lib.sh"
RETENTION_PY = REPO_ROOT / "scripts/ops/backup_retention.py"


def _touch_db(path: Path, day: datetime) -> None:
    name = f"karzar_{day.strftime('%Y%m%d_%H%M%S')}.sql.gz"
    data = b"-- test\n"
    with gzip.open(path / name, "wb") as fh:
        fh.write(data)


def _touch_upload(path: Path, day: datetime) -> None:
    name = f"karzar_uploads_{day.strftime('%Y%m%d_%H%M%S')}.tar.gz"
    (path / name).write_bytes(b"upload")


class TestDiskClassification:
    def test_disk_state_thresholds(self):
        env = os.environ.copy()
        env["KARZAR_DISK_WARNING_PERCENT"] = "65"
        env["KARZAR_DISK_CRITICAL_PERCENT"] = "80"
        script = textwrap.dedent(
            r"""
            source "${LIB}"
            for pct in 49 65 80; do
              echo "${pct}=$(vsh_disk_state ${pct})"
            done
            """
        )
        out = subprocess.run(
            ["bash", "-c", script],
            env={**env, "LIB": str(LIB_SH)},
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert "49=NORMAL" in out
        assert "65=WARNING" in out
        assert "80=CRITICAL" in out


class TestBackupRetention:
    def test_daily_weekly_monthly_union(self, tmp_path: Path):
        base = datetime(2026, 9, 15, 3, 15, 0, tzinfo=timezone.utc)
        for i in range(20):
            _touch_db(tmp_path, base - timedelta(days=i))
        payload = plan_directory(tmp_path)
        deletes = [r for r in payload["rows"] if r["decision"] == "DELETE_CANDIDATE"]
        keeps = [r for r in payload["rows"] if r["decision"] != "DELETE_CANDIDATE"]
        assert len(keeps) >= 14
        assert len(deletes) == 20 - len(keeps)

    def test_upload_weekly_monthly_only(self, tmp_path: Path):
        base = datetime(2026, 9, 15, 3, 30, 0, tzinfo=timezone.utc)
        for i in range(100):
            _touch_upload(tmp_path, base - timedelta(days=i))
        payload = plan_directory(tmp_path)
        upload_rows = [r for r in payload["rows"] if r["type"] == "upload"]
        assert len(upload_rows) == 100
        assert payload["summary"]["UPLOAD_BACKUPS_DELETE_CANDIDATES"] > 0

    def test_unknown_filename_preserved(self, tmp_path: Path):
        (tmp_path / "karzar_prod_baseline_20260728_151651.sql.gz").write_bytes(b"x")
        (tmp_path / "random.sql.gz").write_bytes(b"x")
        payload = plan_directory(tmp_path)
        for row in payload["rows"]:
            assert row["decision"] != "DELETE_CANDIDATE"

    def test_malformed_timestamp_preserved(self, tmp_path: Path):
        (tmp_path / "karzar_notadate_000000.sql.gz").write_bytes(b"x")
        payload = plan_directory(tmp_path)
        row = next(r for r in payload["rows"] if "notadate" in r["path"])
        assert row["decision"] in ("KEEP_UNKNOWN",)

    def test_newest_never_deleted_when_in_window(self, tmp_path: Path):
        now = datetime(2026, 9, 15, 3, 15, 0, tzinfo=timezone.utc)
        _touch_db(tmp_path, now)
        _touch_db(tmp_path, now - timedelta(days=1))
        payload = plan_directory(tmp_path)
        newest = max(
            (r for r in payload["rows"] if r["type"] == "db"),
            key=lambda r: r["timestamp"],
        )
        assert newest["decision"] != "DELETE_CANDIDATE"


class TestBackupSafetyGate:
    def _run_gate(self, tmp_path: Path, extra_env: dict | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(
            {
                "KARZAR_ROOT": str(tmp_path),
                "KARZAR_BACKUP_DIR": str(tmp_path / "backups"),
            }
        )
        if extra_env:
            env.update(extra_env)
        backups = tmp_path / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        script = textwrap.dedent(
            r"""
            source "${LIB}"
            vsh_backup_safety_gate
            echo BACKUP_SAFETY_GATE=${BACKUP_SAFETY_GATE}
            """
        )
        return subprocess.run(
            ["bash", "-c", script],
            env={**env, "LIB": str(LIB_SH)},
            capture_output=True,
            text=True,
        )

    def test_pass_with_two_valid_backups(self, tmp_path: Path):
        backups = tmp_path / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        _touch_db(backups, now)
        _touch_db(backups, now - timedelta(days=1))
        proc = self._run_gate(tmp_path)
        assert "BACKUP_SAFETY_GATE=PASS" in proc.stdout

    def test_fail_stale_latest(self, tmp_path: Path):
        backups = tmp_path / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        old = datetime(2026, 9, 1, 3, 0, 0, tzinfo=timezone.utc)
        _touch_db(backups, old)
        _touch_db(backups, old - timedelta(days=1))
        for p in backups.glob("karzar_*.sql.gz"):
            os.utime(p, (old.timestamp(), old.timestamp()))
        proc = self._run_gate(tmp_path)
        assert "BACKUP_SAFETY_GATE=FAIL" in proc.stdout

    def test_fail_zero_byte(self, tmp_path: Path):
        backups = tmp_path / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        name = "karzar_20260915_031501.sql.gz"
        (backups / name).write_bytes(b"")
        (backups / "karzar_20260914_031501.sql.gz").write_bytes(b"x")
        proc = self._run_gate(tmp_path)
        assert "BACKUP_SAFETY_GATE=FAIL" in proc.stdout

    def test_fail_broken_gzip(self, tmp_path: Path):
        backups = tmp_path / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        (backups / "karzar_20260915_031501.sql.gz").write_bytes(b"not-gzip")
        (backups / "karzar_20260914_031501.sql.gz").write_bytes(b"x")
        proc = self._run_gate(tmp_path)
        assert "BACKUP_SAFETY_GATE=FAIL" in proc.stdout

    def test_fail_too_few_backups(self, tmp_path: Path):
        backups = tmp_path / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        _touch_db(backups, now)
        proc = self._run_gate(tmp_path)
        assert "BACKUP_SAFETY_GATE=FAIL" in proc.stdout


class TestHostAndBuildGates:
    def test_host_gate_fail_wrong_hostname(self):
        script = textwrap.dedent(
            r"""
            source "${LIB}"
            vsh_verify_host_identity && echo OK || echo FAIL
            """
        )
        proc = subprocess.run(
            ["bash", "-c", script],
            env={
                **os.environ,
                "LIB": str(LIB_SH),
                "KARZAR_EXPECTED_HOSTNAME": "expected-host",
                "KARZAR_HOUSEKEEPING_MOCK_HOSTNAME": "wrong-host",
            },
            capture_output=True,
            text=True,
        )
        assert "FAIL" in proc.stdout

    def test_active_build_runner_worker(self):
        script = textwrap.dedent(
            r"""
            source "${LIB}"
            KARZAR_HOUSEKEEPING_MOCK_ACTIVE_BUILD=1
            if vsh_active_build_or_deploy; then echo YES; else echo NO; fi
            """
        )
        out = subprocess.run(
            ["bash", "-c", script],
            env={**os.environ, "LIB": str(LIB_SH)},
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert "YES" in out

    def test_idle_listener_not_active(self):
        script = textwrap.dedent(
            r"""
            source "${LIB}"
            KARZAR_HOUSEKEEPING_MOCK_ACTIVE_BUILD=0
            if vsh_active_build_or_deploy; then echo YES; else echo NO; fi
            """
        )
        out = subprocess.run(
            ["bash", "-c", script],
            env={**os.environ, "LIB": str(LIB_SH)},
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert "NO" in out


class TestDockerSafety:
    FORBIDDEN = (
        "docker system prune",
        "docker image prune",
        "docker volume prune",
        "docker container prune",
    )

    def test_no_forbidden_docker_commands_in_executable_paths(self):
        for path in (
            HOUSEKEEPING_SH,
            LIB_SH,
        ):
            text = path.read_text()
            lines = []
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                lines.append(line)
            body = "\n".join(lines)
            for cmd in self.FORBIDDEN:
                assert cmd not in body, f"{cmd} found in {path}"


class TestDryRunDefault:
    def test_default_mode_is_dry_run_help(self):
        proc = subprocess.run(
            [str(HOUSEKEEPING_SH), "--help"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "dry-run" in proc.stdout.lower()

    def test_script_requires_explicit_apply_for_destructive_env(self):
        text = HOUSEKEEPING_SH.read_text()
        assert 'MODE="dry-run"' in text or "MODE=dry-run" in text
        assert "--apply" in text


class TestRetentionUploadPlan:
    def test_overlapping_slots_no_duplicate_delete(self, tmp_path: Path):
        day = datetime(2026, 9, 10, 3, 30, 0, tzinfo=timezone.utc)
        _touch_upload(tmp_path, day)
        _touch_upload(tmp_path, day + timedelta(hours=1))
        files = [classify_file(p) for p in tmp_path.iterdir()]
        dec = plan_upload_retention(files)
        kept = [p for p, (d, _) in dec.items() if d != "DELETE_CANDIDATE"]
        assert len(kept) == 1
