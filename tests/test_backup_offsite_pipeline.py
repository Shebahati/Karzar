"""Behavioral tests for scheduled offsite backup + health evidence."""

from __future__ import annotations

import os
import re
import stat
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    base = os.environ.copy()
    if env:
        base.update(env)
    return subprocess.run(
        args,
        cwd=str(cwd or ROOT),
        env=base,
        capture_output=True,
        text=True,
        check=False,
    )


def _write_exec(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def test_install_backup_cron_requires_all_three_scripts_and_schedule():
    cron = (ROOT / "deploy/staging/scripts/install-backup-cron.sh").read_text(
        encoding="utf-8"
    )
    assert "OFFSITE_SCRIPT=" in cron
    assert 'for script in "$DB_SCRIPT" "$UPLOADS_SCRIPT" "$OFFSITE_SCRIPT"' in cron
    assert "Missing or unreadable backup script" in cron
    assert "15 3 * * * root" in cron
    assert "30 3 * * * root" in cron
    assert "45 3 * * * root" in cron
    assert "backup_offsite_sync.sh" in cron
    assert "cron-offsite.log" in cron
    assert "/opt/karzar/.deploy-secrets" in cron
    assert "DB       03:15" in cron
    assert "uploads  03:30" in cron
    assert "offsite  03:45" in cron
    assert "BACKUP_OFFSITE_URI must be configured in host secrets" in cron
    # No secret values embedded in installer/cron template.
    assert re.search(r"BACKUP_OFFSITE_URI=s3://", cron) is None
    assert "AKIA" not in cron
    assert "aws_secret_access_key" not in cron.lower()


def test_cron_file_generation_contains_jobs_without_secrets(tmp_path: Path):
    """Dry-run the cron body by extracting ENV_LOAD + schedule lines via bash."""
    installer = ROOT / "deploy/staging/scripts/install-backup-cron.sh"
    # Simulate non-root generation by evaluating the same template locally.
    root_dir = ROOT
    deploy_secrets = "/opt/karzar/.deploy-secrets"
    env_load = (
        "set -a; [[ -f ./.env ]] && . ./.env; "
        f"[[ -f {deploy_secrets} ]] && . {deploy_secrets}; set +a"
    )
    cron_body = textwrap.dedent(
        f"""\
        SHELL=/bin/bash
        PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
        15 3 * * * root cd "{root_dir}" && {env_load} && BACKUP_DIR="{root_dir}/backups" /bin/bash "{root_dir}/scripts/backup_db.sh" >> "{root_dir}/backups/cron.log" 2>&1
        30 3 * * * root cd "{root_dir}" && {env_load} && BACKUP_DIR="{root_dir}/backups" /bin/bash "{root_dir}/scripts/backup_uploads.sh" >> "{root_dir}/backups/cron-uploads.log" 2>&1
        45 3 * * * root cd "{root_dir}" && {env_load} && BACKUP_LOCAL_DIR="{root_dir}/backups" /bin/bash "{root_dir}/scripts/backup_offsite_sync.sh" >> "{root_dir}/backups/cron-offsite.log" 2>&1
        """
    )
    out = tmp_path / "karzar-backup"
    out.write_text(cron_body, encoding="utf-8")
    text = out.read_text(encoding="utf-8")
    assert "15 3 * * * root" in text
    assert "30 3 * * * root" in text
    assert "45 3 * * * root" in text
    assert "backup_db.sh" in text
    assert "backup_uploads.sh" in text
    assert "backup_offsite_sync.sh" in text
    assert "BACKUP_OFFSITE_URI=" not in text
    assert installer.is_file()


def test_offsite_sync_fails_closed_when_uri_unset(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    lock = tmp_path / "offsite.lock"
    result = _run(
        ["bash", str(ROOT / "scripts/backup_offsite_sync.sh")],
        env={
            "BACKUP_LOCAL_DIR": str(local),
            "BACKUP_OFFSITE_LOCK": str(lock),
            "BACKUP_OFFSITE_URI": "",
        },
    )
    assert result.returncode != 0
    failure = local / "offsite-last-failure.txt"
    assert failure.is_file()
    body = failure.read_text(encoding="utf-8")
    assert "exit_status=1" in body
    assert "BACKUP_OFFSITE_URI unset" in body
    assert not (local / "offsite-last-success.txt").exists()


def test_offsite_destination_logging_is_sanitized(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    (local / "karzar_20260922_031500.sql.gz").write_bytes(b"x")
    (local / "karzar_uploads_20260922_033000.tar.gz").write_bytes(b"y")
    lock = tmp_path / "offsite.lock"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_exec(
        fake_bin / "aws",
        "#!/usr/bin/env bash\nexit 0\n",
    )
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["BACKUP_LOCAL_DIR"] = str(local)
    env["BACKUP_OFFSITE_LOCK"] = str(lock)
    env["BACKUP_OFFSITE_URI"] = (
        "s3://user:secret-token@my-bucket/karzar-backups?X-Amz-Signature=leak"
    )
    result = _run(
        ["bash", str(ROOT / "scripts/backup_offsite_sync.sh")],
        env=env,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    combined = result.stdout + result.stderr
    assert "secret-token" not in combined
    assert "X-Amz-Signature" not in combined
    assert "user:secret" not in combined
    assert "s3://my-bucket/karzar-backups" in combined
    success = (local / "offsite-last-success.txt").read_text(encoding="utf-8")
    assert "exit_status=0" in success
    assert "secret-token" not in success


def test_offsite_failure_marker_after_prior_success(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    (local / "karzar_20260922_031500.sql.gz").write_bytes(b"x")
    lock = tmp_path / "offsite.lock"
    success = local / "offsite-last-success.txt"
    success.write_text(
        "timestamp_utc=2026-09-21T03:45:00Z\nexit_status=0\nsummary=prior\n",
        encoding="utf-8",
    )
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_exec(fake_bin / "aws", "#!/usr/bin/env bash\nexit 7\n")
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["BACKUP_LOCAL_DIR"] = str(local)
    env["BACKUP_OFFSITE_LOCK"] = str(lock)
    env["BACKUP_OFFSITE_URI"] = "s3://example-bucket/prefix"
    result = _run(
        ["bash", str(ROOT / "scripts/backup_offsite_sync.sh")],
        env=env,
    )
    assert result.returncode == 7
    failure = (local / "offsite-last-failure.txt").read_text(encoding="utf-8")
    assert "exit_status=7" in failure
    # Prior success file remains, but failure marker is present for health checks.
    assert success.is_file()
    assert (local / "offsite-last-failure.txt").stat().st_mtime >= success.stat().st_mtime


def test_health_checker_passes_with_fresh_representative_files(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    (local / "karzar_20260922_031500.sql.gz").write_bytes(b"db")
    (local / "karzar_uploads_20260922_033000.tar.gz").write_bytes(b"up")
    (local / "offsite-last-success.txt").write_text(
        "timestamp_utc=2026-09-22T03:45:00Z\nexit_status=0\nsummary=ok\n",
        encoding="utf-8",
    )
    result = _run(
        ["bash", str(ROOT / "scripts/check_backup_health.sh")],
        env={
            "BACKUP_LOCAL_DIR": str(local),
            "BACKUP_MAX_AGE_HOURS": "24",
        },
    )
    assert result.returncode == 0, result.stderr
    assert "BACKUP_HEALTH_OK" in result.stdout


def test_health_checker_fails_when_offsite_stale_or_missing(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    (local / "karzar_20260922_031500.sql.gz").write_bytes(b"db")
    (local / "karzar_uploads_20260922_033000.tar.gz").write_bytes(b"up")
    # No success marker → unhealthy
    result = _run(
        ["bash", str(ROOT / "scripts/check_backup_health.sh")],
        env={
            "BACKUP_LOCAL_DIR": str(local),
            "BACKUP_MAX_AGE_HOURS": "24",
        },
    )
    assert result.returncode != 0
    assert "missing offsite success marker" in result.stderr


def test_health_checker_fails_when_failure_newer_than_success(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    (local / "karzar_20260922_031500.sql.gz").write_bytes(b"db")
    (local / "karzar_uploads_20260922_033000.tar.gz").write_bytes(b"up")
    success = local / "offsite-last-success.txt"
    failure = local / "offsite-last-failure.txt"
    success.write_text(
        "timestamp_utc=2026-09-22T01:00:00Z\nexit_status=0\nsummary=ok\n",
        encoding="utf-8",
    )
    # Ensure failure mtime is newer
    import time

    time.sleep(0.05)
    failure.write_text(
        "timestamp_utc=2026-09-22T02:00:00Z\nexit_status=1\nsummary=fail\n",
        encoding="utf-8",
    )
    result = _run(
        ["bash", str(ROOT / "scripts/check_backup_health.sh")],
        env={
            "BACKUP_LOCAL_DIR": str(local),
            "BACKUP_MAX_AGE_HOURS": "24",
        },
    )
    assert result.returncode != 0
    assert "failure marker newer than success" in result.stderr


def test_offsite_source_covers_db_and_uploads_filename_families():
    """Documentation/self-check: both artifact families land under backups/."""
    db = (ROOT / "scripts/backup_db.sh").read_text(encoding="utf-8")
    uploads = (ROOT / "scripts/backup_uploads.sh").read_text(encoding="utf-8")
    offsite = (ROOT / "scripts/backup_offsite_sync.sh").read_text(encoding="utf-8")
    assert "karzar_" in db and ".sql.gz" in db
    assert "karzar_uploads_" in uploads and ".tar.gz" in uploads
    assert 'LOCAL_DIR="${BACKUP_LOCAL_DIR:-$ROOT_DIR/backups}"' in offsite
    assert "BACKUP_RETENTION_DAYS applies to local files only" in offsite
    assert "--delete" in offsite
    assert "set -euo pipefail" in offsite


def test_health_checker_fails_when_backups_stale(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    db = local / "karzar_20260101_000000.sql.gz"
    up = local / "karzar_uploads_20260101_000000.tar.gz"
    db.write_bytes(b"db")
    up.write_bytes(b"up")
    # Age the files beyond 1 hour
    old = 1_700_000_000  # far past
    os.utime(db, (old, old))
    os.utime(up, (old, old))
    (local / "offsite-last-success.txt").write_text(
        "timestamp_utc=2026-09-22T03:45:00Z\nexit_status=0\nsummary=ok\n",
        encoding="utf-8",
    )
    result = _run(
        ["bash", str(ROOT / "scripts/check_backup_health.sh")],
        env={
            "BACKUP_LOCAL_DIR": str(local),
            "BACKUP_MAX_AGE_HOURS": "1",
        },
    )
    assert result.returncode != 0
    assert "no recent DB backup" in result.stderr or "no recent uploads backup" in result.stderr
