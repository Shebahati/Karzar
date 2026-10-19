"""Static safety checks for application-staging declarative primitives."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.app-staging.yml"
ENV_EXAMPLE = ROOT / ".env.app-staging.example"


def test_app_staging_compose_isolation_markers():
    text = COMPOSE.read_text(encoding="utf-8")
    assert "name: karzar_app_staging" in text
    assert "KARZAR_DATA_PLANE: staging" in text
    assert "KARZAR_MEDIA_PLANE: staging" in text
    assert "karzar_app_staging" in text
    assert "PAYMENT_PROVIDER: mock" in text
    assert "SMS_PROVIDER: console" in text
    assert 'PURCHASE_CHECKOUT_ENABLED: "false"' in text
    assert 'HESABFA_ENABLED: "false"' in text
    assert 'POSTEX_ENABLED: "false"' in text
    assert "karzar_app_staging_net" in text
    assert "karzar_app_staging_postgres_data" in text
    assert "127.0.0.1:" in text
    assert "lathe_api" not in text
    assert "lathe_postgres" not in text
    assert "lathe_redis" not in text
    assert "karzar_uploads" not in text
    assert "\n  postgres_data:" not in text
    assert "container_name:" not in text
    assert "POSTGRES_DB=karzar_staging" not in text.replace(" ", "")


def test_app_staging_env_example_identity():
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    assert "KARZAR_DATA_PLANE=staging" in text
    assert "KARZAR_MEDIA_PLANE=staging" in text
    assert "POSTGRES_DB=karzar_app_staging" in text
    assert "PAYMENT_PROVIDER=mock" in text
    assert "SMS_PROVIDER=console" in text
    assert "PURCHASE_CHECKOUT_ENABLED=false" in text
    assert "karzar_staging" not in text.split("POSTGRES_DB=")[-1].splitlines()[0]


def test_app_staging_compose_config_validates():
    import os
    import subprocess
    import tempfile

    env_src = ENV_EXAMPLE.read_text(encoding="utf-8")
    env_src = env_src.replace(
        "replace-with-strong-app-staging-password",
        "local-compose-config-only-password",
    )
    with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as tmp:
        tmp.write(env_src)
        tmp_path = tmp.name
    try:
        proc = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                str(COMPOSE),
                "--env-file",
                tmp_path,
                "config",
                "--quiet",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        os.unlink(tmp_path)
    assert proc.returncode == 0, proc.stderr
