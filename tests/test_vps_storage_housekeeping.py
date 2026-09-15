"""Tests for VPS storage housekeeping (retention + shell safety)."""

from __future__ import annotations

import gzip
import os
import subprocess
import textwrap
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from scripts.ops.backup_retention import (
    RetentionDeleteError,
    apply_retention_deletes,
    classify_file,
    plan_directory,
    plan_upload_retention,
)
from scripts.ops.backup_safety import evaluate_backup_safety_gate, parse_canonical_db_stamp

REPO_ROOT = Path(__file__).resolve().parents[1]
HOUSEKEEPING_SH = REPO_ROOT / "scripts/ops/vps_storage_housekeeping.sh"
LIB_SH = REPO_ROOT / "scripts/ops/vps_storage_housekeeping_lib.sh"
RETENTION_PY = REPO_ROOT / "scripts/ops/backup_retention.py"
BACKUP_SAFETY_PY = REPO_ROOT / "scripts/ops/backup_safety.py"


def _touch_db(path: Path, day: datetime) -> Path:
    name = f"karzar_{day.strftime('%Y%m%d_%H%M%S')}.sql.gz"
    data = b"-- test\n"
    with gzip.open(path / name, "wb") as fh:
        fh.write(data)
    return path / name


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
        base = datetime(2026, 9, 15, 3, 15, 0, tzinfo=UTC)
        for i in range(20):
            _touch_db(tmp_path, base - timedelta(days=i))
        payload = plan_directory(tmp_path)
        deletes = [r for r in payload["rows"] if r["decision"] == "DELETE_CANDIDATE"]
        keeps = [r for r in payload["rows"] if r["decision"] != "DELETE_CANDIDATE"]
        assert len(keeps) >= 14
        assert len(deletes) == 20 - len(keeps)

    def test_upload_weekly_monthly_only(self, tmp_path: Path):
        base = datetime(2026, 9, 15, 3, 30, 0, tzinfo=UTC)
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
        now = datetime(2026, 9, 15, 3, 15, 0, tzinfo=UTC)
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
        now = datetime.now(UTC)
        _touch_db(backups, now)
        _touch_db(backups, now - timedelta(days=1))
        proc = self._run_gate(tmp_path)
        assert "BACKUP_SAFETY_GATE=PASS" in proc.stdout

    def test_fail_stale_latest_by_filename_not_mtime(self, tmp_path: Path):
        backups = tmp_path / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        old = datetime(2026, 9, 1, 3, 0, 0, tzinfo=UTC)
        p1 = _touch_db(backups, old)
        p2 = _touch_db(backups, old - timedelta(days=1))
        now_ts = time.time()
        os.utime(p1, (now_ts, now_ts))
        os.utime(p2, (now_ts, now_ts))
        proc = self._run_gate(tmp_path)
        assert "BACKUP_SAFETY_GATE=FAIL" in proc.stdout

    def test_fail_zero_byte(self, tmp_path: Path):
        backups = tmp_path / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        name = "karzar_20260915_031501.sql.gz"
        (backups / name).write_bytes(b"")
        with gzip.open(backups / "karzar_20260914_031501.sql.gz", "wb") as fh:
            fh.write(b"x")
        proc = self._run_gate(tmp_path)
        assert "BACKUP_SAFETY_GATE=FAIL" in proc.stdout

    def test_fail_broken_gzip_on_latest_canonical(self, tmp_path: Path):
        backups = tmp_path / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        (backups / "karzar_20260915_031501.sql.gz").write_bytes(b"not-gzip")
        with gzip.open(backups / "karzar_20260914_031501.sql.gz", "wb") as fh:
            fh.write(b"x")
        proc = self._run_gate(tmp_path)
        assert "BACKUP_SAFETY_GATE=FAIL" in proc.stdout

    def test_fail_too_few_backups(self, tmp_path: Path):
        backups = tmp_path / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        now = datetime.now(UTC)
        _touch_db(backups, now)
        proc = self._run_gate(tmp_path)
        assert "BACKUP_SAFETY_GATE=FAIL" in proc.stdout

    def test_fail_future_filename_timestamp(self, tmp_path: Path):
        backups = tmp_path / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        future = datetime.now(UTC) + timedelta(days=2)
        _touch_db(backups, future)
        _touch_db(backups, future - timedelta(days=1))
        ok, reason = evaluate_backup_safety_gate(backups)
        assert not ok
        assert "future" in reason

    def test_malformed_filename_ignored_for_canonical_count(self, tmp_path: Path):
        backups = tmp_path / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        (backups / "karzar_bad_000000.sql.gz").write_bytes(b"x")
        now = datetime.now(UTC)
        _touch_db(backups, now)
        ok, _ = evaluate_backup_safety_gate(backups)
        assert not ok


class TestBackupSafetyPython:
    def test_parse_canonical(self):
        dt = parse_canonical_db_stamp("karzar_20260915_031501.sql.gz")
        assert dt == datetime(2026, 9, 15, 3, 15, 1, tzinfo=UTC)
        assert parse_canonical_db_stamp("karzar_prod_baseline_20260728_151651.sql.gz") is None


class TestPathContainmentDeletes:
    def _payload_delete(self, path: Path) -> dict:
        return {
            "rows": [
                {
                    "type": "db",
                    "decision": "DELETE_CANDIDATE",
                    "path": str(path),
                    "size": 10,
                }
            ]
        }

    def test_normal_direct_child_allowed(self, tmp_path: Path):
        f = _touch_db(tmp_path, datetime(2026, 1, 1, tzinfo=UTC))
        apply_retention_deletes(self._payload_delete(f), tmp_path)
        assert not f.exists()

    def test_symlink_refused(self, tmp_path: Path):
        real = _touch_db(tmp_path, datetime(2026, 1, 2, tzinfo=UTC))
        link = tmp_path / "karzar_20260102_030000.sql.gz"
        link.symlink_to(real.name)
        with pytest.raises(RetentionDeleteError):
            apply_retention_deletes(self._payload_delete(link), tmp_path)

    def test_symlink_outside_root_refused(self, tmp_path: Path):
        outside = tmp_path.parent / "outside.sql.gz"
        outside.write_bytes(b"x")
        link = tmp_path / "karzar_20260102_030000.sql.gz"
        link.symlink_to(outside)
        with pytest.raises(RetentionDeleteError):
            apply_retention_deletes(self._payload_delete(link), tmp_path)

    def test_traversal_refused(self, tmp_path: Path):
        evil = tmp_path / ".." / "evil.sql.gz"
        with pytest.raises(RetentionDeleteError):
            apply_retention_deletes(self._payload_delete(evil), tmp_path)

    def test_prefix_confusion_refused(self, tmp_path: Path):
        evil_root = tmp_path.parent / f"{tmp_path.name}-evil"
        evil_root.mkdir()
        evil = evil_root / "karzar_20260102_030000.sql.gz"
        with gzip.open(evil, "wb") as fh:
            fh.write(b"x")
        with pytest.raises(RetentionDeleteError):
            apply_retention_deletes(self._payload_delete(evil), tmp_path)

    def test_nested_subdirectory_refused(self, tmp_path: Path):
        nested = tmp_path / "nested"
        nested.mkdir()
        f = nested / "karzar_20260102_030000.sql.gz"
        with gzip.open(f, "wb") as fh:
            fh.write(b"x")
        with pytest.raises(RetentionDeleteError):
            apply_retention_deletes(self._payload_delete(f), tmp_path)


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

    def test_host_gate_pass_with_mocks(self, tmp_path: Path):
        root = tmp_path / "Karzar"
        root.mkdir(parents=True)
        script = textwrap.dedent(
            r"""
            source "${LIB}"
            vsh_verify_host_identity && echo HOST_IDENTITY_GATE=PASS || echo HOST_IDENTITY_GATE=FAIL
            """
        )
        proc = subprocess.run(
            ["bash", "-c", script],
            env={
                **os.environ,
                "LIB": str(LIB_SH),
                "KARZAR_EXPECTED_HOSTNAME": "srv5944957438",
                "KARZAR_HOUSEKEEPING_MOCK_HOSTNAME": "srv5944957438",
                "KARZAR_ROOT": str(root),
                "KARZAR_HOUSEKEEPING_MOCK_DOCKER_PS": "lathe_api,lathe_postgres",
            },
            capture_output=True,
            text=True,
            check=True,
        )
        assert "HOST_IDENTITY_GATE=PASS" in proc.stdout

    def _detect_active(self, process_lines: str) -> str:
        script = textwrap.dedent(
            r"""
            source "${LIB}"
            if vsh_active_build_or_deploy; then echo YES; else echo NO; fi
            """
        )
        env = {
            **os.environ,
            "LIB": str(LIB_SH),
            "KARZAR_HOUSEKEEPING_TEST_PROCESS_LINES": process_lines,
        }
        return subprocess.run(
            ["bash", "-c", script],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    def test_idle_listener_not_active(self):
        assert self._detect_active("4242|/opt/actions-runner/bin/Runner.Listener run") == "NO"

    def test_runner_worker_active(self):
        assert self._detect_active("5151|/opt/actions-runner/bin/Runner.Worker spawn") == "YES"

    def test_deploy_backend_active(self):
        assert self._detect_active("9001|bash deploy-backend.sh") == "YES"

    def test_deploy_frontend_active(self):
        assert self._detect_active("9002|bash deploy-frontend.sh") == "YES"

    def test_deploy_staging_active(self):
        assert self._detect_active("9003|bash deploy-staging workflow") == "YES"

    def test_docker_build_active(self):
        assert self._detect_active("9004|docker build -t karzar-app:staging .") == "YES"


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


class TestDryRunDestructive:
    def _harness_env(self, tmp_path: Path) -> dict[str, str]:
        root = tmp_path / "opt/karzar/Karzar"
        backups = root / "backups"
        backups.mkdir(parents=True)
        now = datetime.now(UTC)
        _touch_db(backups, now)
        _touch_db(backups, now - timedelta(days=1))

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        audit = tmp_path / "audit.log"
        docker_stub = bin_dir / "docker"
        docker_stub.write_text(
            textwrap.dedent(
                f"""#!/usr/bin/env bash
set -euo pipefail
echo "$@" >> "{audit}"
if [[ "$1" == "builder" && "$2" == "prune" ]]; then
  if [[ "${{3:-}}" == "--help" ]]; then
    echo "--filter until=168h"
    exit 0
  fi
  echo "DESTRUCTIVE_BUILDER_PRUNE" >> "{audit}"
  exit 99
fi
if [[ "$1" == "ps" ]]; then
  echo lathe_api
  echo lathe_postgres
  exit 0
fi
if [[ "$1" == "system" && "$2" == "df" ]]; then
  echo "Build Cache     10        10        1MB     0B"
  exit 0
fi
if [[ "$1" == "builder" && "$2" == "du" ]]; then
  echo "Total: 1MB"
  exit 0
fi
exit 0
"""
            )
        )
        docker_stub.chmod(0o755)

        rm_stub = bin_dir / "rm"
        rm_stub.write_text(
            f"""#!/usr/bin/env bash
echo "DESTRUCTIVE_RM" >> "{audit}"
exit 99
"""
        )
        rm_stub.chmod(0o755)

        return {
            "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
            "KARZAR_ROOT": str(root),
            "KARZAR_BACKUP_DIR": str(backups),
            "KARZAR_EXPECTED_HOSTNAME": "srv5944957438",
            "KARZAR_HOUSEKEEPING_MOCK_HOSTNAME": "srv5944957438",
            "KARZAR_HOUSEKEEPING_MOCK_DOCKER_PS": "lathe_api,lathe_postgres",
            "KARZAR_HOUSEKEEPING_MOCK_ACTIVE_BUILD": "0",
            "KARZAR_HOUSEKEEPING_LOCK_FILE": str(tmp_path / "housekeeping.lock"),
            "AUDIT_LOG": str(audit),
        }

    def test_dry_run_no_destructive_commands(self, tmp_path: Path):
        env = self._harness_env(tmp_path)
        audit = Path(env["AUDIT_LOG"])
        for args in ([], ["--dry-run"]):
            subprocess.run(
                [str(HOUSEKEEPING_SH), *args],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            log = audit.read_text()
            assert "DESTRUCTIVE_BUILDER_PRUNE" not in log
            assert "DESTRUCTIVE_RM" not in log
            assert "--apply-deletes" not in log

    def test_default_invocation_is_dry_run(self, tmp_path: Path):
        env = self._harness_env(tmp_path)
        proc = subprocess.run(
            [str(HOUSEKEEPING_SH)],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert "MODE=dry-run" in proc.stdout
        assert "docker builder prune" in proc.stdout
        assert "DESTRUCTIVE_BUILDER_PRUNE" not in Path(env["AUDIT_LOG"]).read_text()


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
        day = datetime(2026, 9, 10, 3, 30, 0, tzinfo=UTC)
        _touch_upload(tmp_path, day)
        _touch_upload(tmp_path, day + timedelta(hours=1))
        files = [classify_file(p) for p in tmp_path.iterdir()]
        dec = plan_upload_retention(files)
        kept = [p for p, (d, _) in dec.items() if d != "DELETE_CANDIDATE"]
        assert len(kept) == 1
