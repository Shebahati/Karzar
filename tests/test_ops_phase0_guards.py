"""Static regression checks for the Phase 0 deployment and backup guards."""

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
