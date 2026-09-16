"""Static regression checks for the Phase 0 deployment and backup guards."""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_backup_cron_survives_github_artifact_mode_normalization():
    cron = _read("deploy/staging/scripts/install-backup-cron.sh")

    assert '/bin/bash "$DB_SCRIPT"' in cron
    assert '/bin/bash "$UPLOADS_SCRIPT"' in cron
    assert 'chmod +x "$DB_SCRIPT" "$UPLOADS_SCRIPT"' in cron


def test_deploy_workflows_restore_backup_script_modes_and_have_freeze_gate():
    for workflow in (
        ".github/workflows/deploy-staging.yml",
        ".github/workflows/deploy-production.yml",
    ):
        text = _read(workflow)
        assert "KARZAR_DEPLOY_FREEZE" in text
        assert "Deployment freeze gate" in text
        assert 'refs/heads/main' in text
        assert "needs: deploy-freeze" in text
        assert (
            "chmod +x scripts/backup_db.sh scripts/backup_uploads.sh "
            "scripts/backup_offsite_sync.sh"
        ) in text


def test_deploy_staging_does_not_publish_cms_as_a_side_effect():
    text = _read(".github/workflows/deploy-staging.yml")

    assert "publish_seo003_articles.py" not in text
    assert "KARZAR_ALLOW_PRODUCTION_WRITE" not in text
    assert "KARZAR_INGESTION_CATEGORY" not in text
    assert "run-smoke-staging.sh" in text


def test_smoke_staging_gates_on_readiness_before_functional_checks():
    smoke = _read("deploy/staging/scripts/smoke-staging.sh")
    assert "wait-staging-frontends.sh" in smoke
    assert "DEPLOY_FE_SMOKE_OK" in smoke
    wait_at = smoke.index("wait-staging-frontends.sh")
    checks_at = smoke.index('check "api_health"')
    assert wait_at < checks_at


def test_deploy_frontend_waits_for_http_readiness_after_container_start():
    script = _read("deploy/staging/scripts/deploy-frontend.sh")
    assert "wait-staging-frontends.sh" in script
    assert "docker run -d --name karzar_admin" in script
    admin_run = script.index("docker run -d --name karzar_admin")
    wait_at = script.index("wait-staging-frontends.sh")
    assert admin_run < wait_at


def test_deploy_production_workflow_still_invokes_smoke_staging_directly():
    text = _read(".github/workflows/deploy-production.yml")
    assert "bash deploy/staging/scripts/smoke-staging.sh" in text
    assert "run-smoke-staging.sh" not in text


def test_wait_staging_http_canonicalizes_curl_connection_failure_code(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_curl = fake_bin / "curl"
    fake_curl.write_text(
        "#!/usr/bin/env bash\n"
        "printf '000'\n"
        "exit 7\n",
        encoding="utf-8",
    )
    fake_curl.chmod(0o755)

    script = ROOT / "deploy/staging/scripts/wait-staging-http.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["READINESS_DEADLINE_SEC"] = "0"
    env["POLL_INTERVAL_SEC"] = "1"

    result = subprocess.run(
        ["bash", str(script), "testsvc", "http://127.0.0.1:9/nope", "200"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "testsvc_READINESS_FAILED: last HTTP code 000" in result.stderr
    assert "000000" not in result.stderr


def test_wait_staging_http_accepts_http_200_from_curl(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_curl = fake_bin / "curl"
    fake_curl.write_text(
        "#!/usr/bin/env bash\n"
        "printf '200'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_curl.chmod(0o755)

    script = ROOT / "deploy/staging/scripts/wait-staging-http.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"

    result = subprocess.run(
        ["bash", str(script), "testsvc", "http://127.0.0.1:1/ok", "200"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "READY testsvc (HTTP 200)" in result.stdout


def test_live_data_apply_workflows_honor_freeze():
    for workflow in (
        ".github/workflows/promote-measurement.yml",
        ".github/workflows/remove-omumi-padding.yml",
    ):
        text = _read(workflow)
        assert "if: inputs.mode == 'apply'" in text
        assert "KARZAR_DEPLOY_FREEZE" in text
        assert "Live data mutations are frozen" in text


def test_offsite_sync_defaults_to_repository_backup_directory():
    script = _read("scripts/backup_offsite_sync.sh")

    assert 'ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"' in script
    assert 'LOCAL_DIR="${BACKUP_LOCAL_DIR:-$ROOT_DIR/backups}"' in script
