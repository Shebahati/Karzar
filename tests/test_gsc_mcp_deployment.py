from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = REPO_ROOT / "docker-compose.gsc-mcp.yml"
NGINX_BOOTSTRAP_TEMPLATE = REPO_ROOT / "deploy/staging/nginx/mcp.karzartools.com.bootstrap.conf.template"
NGINX_TEMPLATE = REPO_ROOT / "deploy/staging/nginx/mcp.karzartools.com.conf.template"
DOCKERFILE = REPO_ROOT / "services/gsc_mcp/Dockerfile"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"

PLACEHOLDER_ENV = {
    "GOOGLE_GSC_CLIENT_ID": "ci-placeholder-client-id",
    "GOOGLE_GSC_CLIENT_SECRET": "ci-placeholder-client-secret",
    "GOOGLE_GSC_REFRESH_TOKEN": "ci-placeholder-refresh-token",
    "KARZAR_MCP_ACCESS_TOKEN": "ci-placeholder-mcp-token",
}


def _docker_daemon_available() -> bool:
    return shutil.which("docker") is not None and Path("/var/run/docker.sock").exists()


def test_compose_publishes_loopback_only() -> None:
    text = COMPOSE_FILE.read_text(encoding="utf-8")
    assert "127.0.0.1:8010:8010" in text
    assert re.search(r'(?m)^\s*-\s*["\']?8010:8010', text) is None
    assert re.search(r'0\.0\.0\.0:8010', text) is None


def test_compose_service_isolated() -> None:
    text = COMPOSE_FILE.read_text(encoding="utf-8")
    assert "container_name: karzar_gsc_mcp" in text
    assert "depends_on" not in text
    assert "gsc_mcp:" in text
    assert 'MCP_HOST: "0.0.0.0"' in text
    assert "MCP_PUBLIC_BASE_URL: https://mcp.karzartools.com" in text
    assert "dockerfile: services/gsc_mcp/Dockerfile" in text


def test_compose_config_resolves_with_placeholder_env() -> None:
    if not _docker_daemon_available():
        pytest.skip("docker daemon not available")
    env = {**os.environ, **PLACEHOLDER_ENV}
    proc = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(COMPOSE_FILE),
            "config",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "host_ip: 127.0.0.1" in proc.stdout or "127.0.0.1:8010:8010" in proc.stdout
    assert "published: \"8010\"" in proc.stdout or "published: '8010'" in proc.stdout


def test_nginx_bootstrap_http_only_acme() -> None:
    text = NGINX_BOOTSTRAP_TEMPLATE.read_text(encoding="utf-8")
    assert "listen 80" in text
    assert "server_name mcp.karzartools.com" in text
    assert "/.well-known/acme-challenge/" in text
    assert "/var/www/certbot" in text
    assert re.search(r"listen\s+443", text) is None
    assert "proxy_pass" not in text
    assert re.search(r"^\s*ssl_certificate\b", text, re.M) is None


def test_nginx_final_tls_and_mcp_proxy_directives() -> None:
    text = NGINX_TEMPLATE.read_text(encoding="utf-8")
    assert "server_name mcp.karzartools.com" in text
    assert "ssl_certificate     /etc/letsencrypt/live/mcp.karzartools.com/fullchain.pem;" in text
    assert "ssl_certificate_key /etc/letsencrypt/live/mcp.karzartools.com/privkey.pem;" in text
    assert "# ssl_certificate" not in text
    assert "location /mcp" in text
    assert "proxy_buffering off" in text
    assert "proxy_cache off" in text
    assert "proxy_read_timeout 300s" in text
    assert "proxy_send_timeout 300s" in text
    assert "proxy_set_header Authorization $http_authorization" in text
    assert "location = /health" in text
    assert "return 404" in text
    assert "/.well-known/acme-challenge/" in text


def test_dockerfile_non_root_and_healthcheck() -> None:
    text = DOCKERFILE.read_text(encoding="utf-8")
    assert "USER appuser" in text
    assert "python:3.12" in text
    assert "HEALTHCHECK" in text
    assert "127.0.0.1:8010/health" in text
    assert "MCP_HOST=127.0.0.1" not in text


def test_dockerignore_blocks_secret_patterns() -> None:
    text = DOCKERIGNORE.read_text(encoding="utf-8")
    for needle in (
        "credentials.json",
        "client_secret",
        ".gsc-credentials",
    ):
        assert needle in text


@pytest.mark.skipif(not _docker_daemon_available(), reason="docker daemon not available")
def test_gsc_mcp_image_builds() -> None:
    proc = subprocess.run(
        [
            "docker",
            "build",
            "-f",
            "services/gsc_mcp/Dockerfile",
            "-t",
            "karzar-gsc-mcp-ci:test",
            ".",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stderr[-4000:]


@pytest.mark.skipif(not _docker_daemon_available(), reason="docker daemon not available")
def test_gsc_mcp_container_health_and_non_root() -> None:
    image = "karzar-gsc-mcp-ci:test"
    subprocess.run(
        ["docker", "build", "-f", "services/gsc_mcp/Dockerfile", "-t", image, "."],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        timeout=600,
    )
    env = {
        **PLACEHOLDER_ENV,
        "MCP_HOST": "0.0.0.0",
        "KARZAR_MCP_ACCESS_TOKEN": PLACEHOLDER_ENV["KARZAR_MCP_ACCESS_TOKEN"],
    }
    run = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-d",
            "--name",
            "karzar_gsc_mcp_ci",
            "-e",
            f"MCP_HOST={env['MCP_HOST']}",
            "-e",
            f"KARZAR_MCP_ACCESS_TOKEN={env['KARZAR_MCP_ACCESS_TOKEN']}",
            "-e",
            f"GOOGLE_GSC_CLIENT_ID={env['GOOGLE_GSC_CLIENT_ID']}",
            "-e",
            f"GOOGLE_GSC_CLIENT_SECRET={env['GOOGLE_GSC_CLIENT_SECRET']}",
            "-e",
            f"GOOGLE_GSC_REFRESH_TOKEN={env['GOOGLE_GSC_REFRESH_TOKEN']}",
            "-p",
            "127.0.0.1:18010:8010",
            image,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    container_id = run.stdout.strip()
    try:
        user_proc = subprocess.run(
            ["docker", "exec", container_id, "id", "-u"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert user_proc.stdout.strip() != "0"
        for _ in range(30):
            health = subprocess.run(
                [
                    "curl",
                    "-fsS",
                    "http://127.0.0.1:18010/health",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if health.returncode == 0:
                break
            subprocess.run(["sleep", "1"], check=True)
        else:
            logs = subprocess.run(
                ["docker", "logs", container_id],
                capture_output=True,
                text=True,
            )
            pytest.fail(f"health never ready: {logs.stdout}\n{logs.stderr}")
        assert "refresh_token" not in health.stdout.lower()
        subprocess.run(
            ["docker", "run", "--rm", image, "sh", "-c", "test ! -f /app/.env && test ! -f /app/credentials.json"],
            capture_output=True,
            text=True,
            check=True,
        )
    finally:
        subprocess.run(["docker", "rm", "-f", container_id], capture_output=True)
