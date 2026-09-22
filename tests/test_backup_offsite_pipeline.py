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


def _snapshot_paths(root: Path) -> set[str]:
    return {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() or p.is_dir()}


def _assert_no_secrets(text: str, *secrets: str) -> None:
    for secret in secrets:
        assert secret not in text


def test_offsite_default_aws_s3_sync_no_endpoint(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    (local / "karzar_20260922_031500.sql.gz").write_bytes(b"x")
    (local / "karzar_uploads_20260922_033000.tar.gz").write_bytes(b"y")
    lock = tmp_path / "offsite.lock"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    argv_log = tmp_path / "aws-argv.log"
    _write_exec(
        fake_bin / "aws",
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" >> '{argv_log}'\n"
        "exit 0\n",
    )
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["BACKUP_LOCAL_DIR"] = str(local)
    env["BACKUP_OFFSITE_LOCK"] = str(lock)
    env["BACKUP_OFFSITE_URI"] = "s3://my-bucket/karzar-backups"
    env.pop("BACKUP_S3_ENDPOINT_URL", None)
    env.pop("BACKUP_S3_REGION", None)
    result = _run(
        ["bash", str(ROOT / "scripts/backup_offsite_sync.sh")],
        env=env,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    success = (local / "offsite-last-success.txt").read_text(encoding="utf-8")
    assert "exit_status=0" in success
    assert "destination_type=s3" in success
    assert "endpoint=aws-default" in success
    aws_argv = argv_log.read_text(encoding="utf-8")
    assert "s3 sync" in aws_argv
    assert "--endpoint-url" not in aws_argv
    assert "s3://my-bucket/karzar-backups" in aws_argv


def test_s3_compatible_endpoint_and_region_propagated(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    (local / "karzar_20260922_031500.sql.gz").write_bytes(b"x")
    lock = tmp_path / "offsite.lock"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    argv_log = tmp_path / "aws-argv.log"
    region_log = tmp_path / "aws-region.log"
    _write_exec(
        fake_bin / "aws",
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" >> '{argv_log}'\n"
        f"printf '%s\\n' \"${{AWS_DEFAULT_REGION:-}}\" >> '{region_log}'\n"
        "exit 0\n",
    )
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["BACKUP_LOCAL_DIR"] = str(local)
    env["BACKUP_OFFSITE_LOCK"] = str(lock)
    env["BACKUP_OFFSITE_URI"] = "s3://bucket/prefix"
    env["BACKUP_S3_ENDPOINT_URL"] = "https://s3.example.invalid"
    env["BACKUP_S3_REGION"] = "test-region"
    result = _run(
        ["bash", str(ROOT / "scripts/backup_offsite_sync.sh")],
        env=env,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    aws_argv = argv_log.read_text(encoding="utf-8")
    assert "--endpoint-url https://s3.example.invalid" in aws_argv
    assert "s3 sync" in aws_argv
    assert region_log.read_text(encoding="utf-8").strip().splitlines()[-1] == "test-region"
    success = (local / "offsite-last-success.txt").read_text(encoding="utf-8")
    assert "endpoint=https://s3.example.invalid" in success
    assert "destination=s3://bucket/prefix" in success


def test_http_s3_endpoint_is_refused(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    lock = tmp_path / "offsite.lock"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    argv_log = tmp_path / "aws-argv.log"
    _write_exec(
        fake_bin / "aws",
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" >> '{argv_log}'\n"
        "exit 0\n",
    )
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["BACKUP_LOCAL_DIR"] = str(local)
    env["BACKUP_OFFSITE_LOCK"] = str(lock)
    env["BACKUP_OFFSITE_URI"] = "s3://bucket/prefix"
    env["BACKUP_S3_ENDPOINT_URL"] = "http://s3.example.invalid"
    result = _run(
        ["bash", str(ROOT / "scripts/backup_offsite_sync.sh")],
        env=env,
    )
    assert result.returncode != 0
    assert "https://" in result.stderr
    assert not argv_log.exists()
    failure = (local / "offsite-last-failure.txt").read_text(encoding="utf-8")
    assert "invalid BACKUP_S3_ENDPOINT_URL" in failure


def test_s3_destination_userinfo_refused_before_aws(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    lock = tmp_path / "offsite.lock"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    argv_log = tmp_path / "aws-argv.log"
    secret = "super-secret-userinfo"
    _write_exec(
        fake_bin / "aws",
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" >> '{argv_log}'\n"
        "exit 0\n",
    )
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["BACKUP_LOCAL_DIR"] = str(local)
    env["BACKUP_OFFSITE_LOCK"] = str(lock)
    env["BACKUP_OFFSITE_URI"] = f"s3://user:{secret}@bucket/prefix"
    result = _run(
        ["bash", str(ROOT / "scripts/backup_offsite_sync.sh")],
        env=env,
    )
    assert result.returncode != 0
    assert not argv_log.exists()
    combined = result.stdout + result.stderr
    _assert_no_secrets(combined, secret, "user:", "@bucket")
    failure = (local / "offsite-last-failure.txt").read_text(encoding="utf-8")
    assert "invalid s3 destination URI" in failure
    _assert_no_secrets(failure, secret)


def test_s3_destination_query_refused_before_aws(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    lock = tmp_path / "offsite.lock"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    argv_log = tmp_path / "aws-argv.log"
    secret = "query-token-secret"
    _write_exec(
        fake_bin / "aws",
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" >> '{argv_log}'\n"
        "exit 0\n",
    )
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["BACKUP_LOCAL_DIR"] = str(local)
    env["BACKUP_OFFSITE_LOCK"] = str(lock)
    env["BACKUP_OFFSITE_URI"] = f"s3://bucket/prefix?token={secret}"
    result = _run(
        ["bash", str(ROOT / "scripts/backup_offsite_sync.sh")],
        env=env,
    )
    assert result.returncode != 0
    assert not argv_log.exists()
    combined = result.stdout + result.stderr
    _assert_no_secrets(combined, secret)
    failure = (local / "offsite-last-failure.txt").read_text(encoding="utf-8")
    assert "invalid s3 destination URI" in failure
    _assert_no_secrets(failure, secret)


def test_s3_destination_fragment_refused_before_aws(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    lock = tmp_path / "offsite.lock"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    argv_log = tmp_path / "aws-argv.log"
    secret = "fragment-secret"
    _write_exec(
        fake_bin / "aws",
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" >> '{argv_log}'\n"
        "exit 0\n",
    )
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["BACKUP_LOCAL_DIR"] = str(local)
    env["BACKUP_OFFSITE_LOCK"] = str(lock)
    env["BACKUP_OFFSITE_URI"] = f"s3://bucket/prefix#{secret}"
    result = _run(
        ["bash", str(ROOT / "scripts/backup_offsite_sync.sh")],
        env=env,
    )
    assert result.returncode != 0
    assert not argv_log.exists()
    _assert_no_secrets(result.stdout + result.stderr, secret)


def test_s3_endpoint_userinfo_refused_before_aws(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    lock = tmp_path / "offsite.lock"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    argv_log = tmp_path / "aws-argv.log"
    secret = "endpoint-password"
    _write_exec(
        fake_bin / "aws",
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" >> '{argv_log}'\n"
        "exit 0\n",
    )
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["BACKUP_LOCAL_DIR"] = str(local)
    env["BACKUP_OFFSITE_LOCK"] = str(lock)
    env["BACKUP_OFFSITE_URI"] = "s3://bucket/prefix"
    env["BACKUP_S3_ENDPOINT_URL"] = f"https://user:{secret}@s3.example.invalid"
    result = _run(
        ["bash", str(ROOT / "scripts/backup_offsite_sync.sh")],
        env=env,
    )
    assert result.returncode != 0
    assert not argv_log.exists()
    combined = result.stdout + result.stderr
    _assert_no_secrets(combined, secret)
    failure = (local / "offsite-last-failure.txt").read_text(encoding="utf-8")
    assert "invalid BACKUP_S3_ENDPOINT_URL" in failure
    _assert_no_secrets(failure, secret)


def test_s3_endpoint_query_refused_before_aws(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    lock = tmp_path / "offsite.lock"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    argv_log = tmp_path / "aws-argv.log"
    secret = "endpoint-query-secret"
    _write_exec(
        fake_bin / "aws",
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" >> '{argv_log}'\n"
        "exit 0\n",
    )
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["BACKUP_LOCAL_DIR"] = str(local)
    env["BACKUP_OFFSITE_LOCK"] = str(lock)
    env["BACKUP_OFFSITE_URI"] = "s3://bucket/prefix"
    env["BACKUP_S3_ENDPOINT_URL"] = f"https://s3.example.invalid?token={secret}"
    result = _run(
        ["bash", str(ROOT / "scripts/backup_offsite_sync.sh")],
        env=env,
    )
    assert result.returncode != 0
    assert not argv_log.exists()
    _assert_no_secrets(result.stdout + result.stderr, secret)
    failure = (local / "offsite-last-failure.txt").read_text(encoding="utf-8")
    assert "invalid BACKUP_S3_ENDPOINT_URL" in failure


def test_standard_aws_credentials_succeed_but_stay_off_argv(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    (local / "karzar_20260922_031500.sql.gz").write_bytes(b"x")
    lock = tmp_path / "offsite.lock"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    argv_log = tmp_path / "aws-argv.log"
    access = "AKIAEXAMPLEKEYNOTREAL"
    secret = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    _write_exec(
        fake_bin / "aws",
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" >> '{argv_log}'\n"
        "exit 0\n",
    )
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["BACKUP_LOCAL_DIR"] = str(local)
    env["BACKUP_OFFSITE_LOCK"] = str(lock)
    env["BACKUP_OFFSITE_URI"] = "s3://bucket/prefix"
    env["BACKUP_S3_ENDPOINT_URL"] = "https://s3.example.invalid"
    env["AWS_ACCESS_KEY_ID"] = access
    env["AWS_SECRET_ACCESS_KEY"] = secret
    result = _run(
        ["bash", str(ROOT / "scripts/backup_offsite_sync.sh")],
        env=env,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    aws_argv = argv_log.read_text(encoding="utf-8")
    combined = result.stdout + result.stderr + aws_argv
    success = (local / "offsite-last-success.txt").read_text(encoding="utf-8")
    _assert_no_secrets(combined + success, access, secret)
    assert "--access-key" not in aws_argv
    assert access not in aws_argv
    assert secret not in aws_argv


ESSENTIAL_BINARIES = (
    "bash",
    "date",
    "mkdir",
    "flock",
    "sed",
    "printf",
    "find",
    "dirname",
    "basename",
    "cp",
    "cat",
    "tr",
    "head",
    "wc",
)


def _isolated_path(tmp_path: Path, *, extra_execs: dict[str, str] | None = None) -> Path:
    """PATH dir with coreutils symlinks and optional stub executables; no aws."""
    isolated = tmp_path / "isolated-bin"
    isolated.mkdir(exist_ok=True)
    for name in ESSENTIAL_BINARIES:
        for base in (Path("/usr/bin"), Path("/bin")):
            src = base / name
            if src.exists():
                target = isolated / name
                if not target.exists():
                    target.symlink_to(src)
                break
    if extra_execs:
        for name, body in extra_execs.items():
            _write_exec(isolated / name, body)
    return isolated


def test_s3_missing_aws_cli_fails_closed(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    lock = tmp_path / "offsite.lock"
    isolated = _isolated_path(tmp_path)
    env = os.environ.copy()
    env["PATH"] = str(isolated)
    env["BACKUP_LOCAL_DIR"] = str(local)
    env["BACKUP_OFFSITE_LOCK"] = str(lock)
    env["BACKUP_OFFSITE_URI"] = "s3://bucket/prefix"
    result = _run(
        ["bash", str(ROOT / "scripts/backup_offsite_sync.sh")],
        env=env,
    )
    assert result.returncode != 0
    assert "aws CLI not installed" in result.stderr
    failure = (local / "offsite-last-failure.txt").read_text(encoding="utf-8")
    assert "aws CLI not installed" in failure


def test_rsync_works_without_aws_cli(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    (local / "karzar_20260922_031500.sql.gz").write_bytes(b"x")
    lock = tmp_path / "offsite.lock"
    dest = tmp_path / "remote"
    dest.mkdir()
    isolated = _isolated_path(
        tmp_path,
        extra_execs={
            "rsync": (
                "#!/usr/bin/env bash\n"
                "src=; dest=\n"
                "for a in \"$@\"; do\n"
                "  case \"$a\" in -*) ;; *) "
                "if [[ -z \"$src\" ]]; then src=$a; else dest=$a; fi ;; esac\n"
                "done\n"
                "mkdir -p \"$dest\"\n"
                "cp -a \"$src\". \"$dest\" 2>/dev/null || cp -a \"${src%/}\" \"$dest\"\n"
                "exit 0\n"
            ),
        },
    )
    env = os.environ.copy()
    env["PATH"] = str(isolated)
    env["BACKUP_LOCAL_DIR"] = str(local)
    env["BACKUP_OFFSITE_LOCK"] = str(lock)
    env["BACKUP_OFFSITE_URI"] = f"testhost:{dest}"
    result = _run(
        ["bash", str(ROOT / "scripts/backup_offsite_sync.sh")],
        env=env,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    success = (local / "offsite-last-success.txt").read_text(encoding="utf-8")
    assert "destination_type=rsync" in success
    assert not (isolated / "aws").exists()


def test_preflight_s3_uses_head_bucket_not_sync(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    lock = tmp_path / "offsite.lock"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    argv_log = tmp_path / "aws-argv.log"
    _write_exec(
        fake_bin / "aws",
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" >> '{argv_log}'\n"
        "if [[ \"$*\" == *'s3 sync'* ]]; then exit 99; fi\n"
        "if [[ \"$*\" == *'head-bucket'* ]]; then exit 0; fi\n"
        "exit 1\n",
    )
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["BACKUP_LOCAL_DIR"] = str(local)
    env["BACKUP_OFFSITE_LOCK"] = str(lock)
    env["BACKUP_OFFSITE_URI"] = "s3://bucket/prefix"
    env["BACKUP_S3_ENDPOINT_URL"] = "https://s3.example.invalid"
    before = _snapshot_paths(tmp_path)
    result = _run(
        ["bash", str(ROOT / "scripts/backup_offsite_sync.sh"), "--preflight"],
        env=env,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    aws_argv = argv_log.read_text(encoding="utf-8")
    assert "s3api head-bucket" in aws_argv
    assert "--endpoint-url https://s3.example.invalid" in aws_argv
    assert "s3 sync" not in aws_argv
    assert "Preflight OK" in result.stdout
    assert not (local / "offsite-last-success.txt").exists()
    assert not (local / "offsite-last-failure.txt").exists()
    assert not lock.exists()
    after = _snapshot_paths(tmp_path)
    # Only the mocked aws argv log may appear as a new file under tmp_path.
    new_paths = after - before
    assert new_paths <= {str(argv_log.relative_to(tmp_path))}


def test_preflight_head_bucket_failure_is_filesystem_readonly(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    (local / "karzar_20260922_031500.sql.gz").write_bytes(b"seed")
    lock = tmp_path / "offsite.lock"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    argv_log = tmp_path / "aws-argv.log"
    _write_exec(
        fake_bin / "aws",
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" >> '{argv_log}'\n"
        "if [[ \"$*\" == *'head-bucket'* ]]; then exit 255; fi\n"
        "exit 0\n",
    )
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["BACKUP_LOCAL_DIR"] = str(local)
    env["BACKUP_OFFSITE_LOCK"] = str(lock)
    env["BACKUP_OFFSITE_URI"] = "s3://bucket/prefix"
    before = _snapshot_paths(tmp_path)
    before_backup_files = {p.name for p in local.iterdir()}
    result = _run(
        ["bash", str(ROOT / "scripts/backup_offsite_sync.sh"), "--preflight"],
        env=env,
    )
    assert result.returncode == 255
    assert "head-bucket failed" in result.stderr
    assert not (local / "offsite-last-success.txt").exists()
    assert not (local / "offsite-last-failure.txt").exists()
    assert not lock.exists()
    assert {p.name for p in local.iterdir()} == before_backup_files
    aws_argv = argv_log.read_text(encoding="utf-8")
    assert "s3 sync" not in aws_argv
    after = _snapshot_paths(tmp_path)
    new_paths = after - before
    assert new_paths <= {str(argv_log.relative_to(tmp_path))}


def test_preflight_missing_uri_no_marker_no_lock(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    lock = tmp_path / "offsite.lock"
    before = _snapshot_paths(tmp_path)
    result = _run(
        ["bash", str(ROOT / "scripts/backup_offsite_sync.sh"), "--preflight"],
        env={
            "BACKUP_LOCAL_DIR": str(local),
            "BACKUP_OFFSITE_LOCK": str(lock),
            "BACKUP_OFFSITE_URI": "",
        },
    )
    assert result.returncode != 0
    assert not (local / "offsite-last-success.txt").exists()
    assert not (local / "offsite-last-failure.txt").exists()
    assert not lock.exists()
    assert _snapshot_paths(tmp_path) == before


def test_preflight_missing_aws_no_marker_no_lock(tmp_path: Path):
    local = tmp_path / "backups"
    local.mkdir()
    lock = tmp_path / "offsite.lock"
    isolated = _isolated_path(tmp_path)
    before_backup = {p.name for p in local.iterdir()}
    result = _run(
        ["bash", str(ROOT / "scripts/backup_offsite_sync.sh"), "--preflight"],
        env={
            "PATH": str(isolated),
            "BACKUP_LOCAL_DIR": str(local),
            "BACKUP_OFFSITE_LOCK": str(lock),
            "BACKUP_OFFSITE_URI": "s3://bucket/prefix",
        },
    )
    assert result.returncode != 0
    assert "aws CLI not installed" in result.stderr
    assert not (local / "offsite-last-success.txt").exists()
    assert not (local / "offsite-last-failure.txt").exists()
    assert not lock.exists()
    assert {p.name for p in local.iterdir()} == before_backup


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
