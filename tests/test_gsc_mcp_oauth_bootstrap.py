from __future__ import annotations

import json
import stat
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx

from services.gsc_mcp.bootstrap_oauth import run_bootstrap, write_credentials_file
from services.gsc_mcp.config import GOOGLE_OAUTH_SCOPE, Settings
from services.gsc_mcp.errors import ErrorCode, GscMcpError
from services.gsc_mcp.http_google import GoogleHttpClient
from services.gsc_mcp.oauth_google import exchange_authorization_code
from services.gsc_mcp.oauth_loopback import LoopbackOAuthServer, constant_time_equal
from services.gsc_mcp.pkce import code_challenge_s256, generate_code_verifier

RFC7636_VERIFIER = "dBjftJeZ4CVP-mB92KpfuZscxYj8Gb0LgwXHa2zYlA"
RFC7636_CHALLENGE = "ALgNT5GtvVAoBeNhKYZuCeRXtG9UGwzvFMXJB8uH6KU"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        GOOGLE_GSC_CLIENT_ID="cid",
        GOOGLE_GSC_CLIENT_SECRET="TEST_CLIENT_SECRET_DO_NOT_LEAK",
        GOOGLE_GSC_REFRESH_TOKEN="TEST_REFRESH_TOKEN_DO_NOT_LEAK",
    )


def test_pkce_s256_rfc7636_example() -> None:
    assert code_challenge_s256(RFC7636_VERIFIER) == RFC7636_CHALLENGE


def test_pkce_verifier_length_and_charset() -> None:
    verifier = generate_code_verifier(64)
    assert 43 <= len(verifier) <= 128
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~")
    assert set(verifier).issubset(allowed)


def test_constant_time_state_compare() -> None:
    assert constant_time_equal("abc", "abc") is True
    assert constant_time_equal("abc", "abd") is False


def test_json_and_form_body_mutually_exclusive() -> None:
    client = GoogleHttpClient(5.0, 0, "ua", token_provider=None)
    with pytest.raises(GscMcpError) as exc:
        client.request(
            "POST",
            "https://oauth2.googleapis.com/token",
            json_body={"a": "1"},
            form_body={"b": "2"},
            skip_auth=True,
        )
    assert exc.value.code == ErrorCode.INVALID_ARGUMENT


@respx.mock
def test_refresh_token_uses_form_encoding(settings) -> None:
    def assert_form(request: httpx.Request) -> httpx.Response:
        assert request.headers["content-type"].startswith("application/x-www-form-urlencoded")
        body = request.content.decode()
        assert "grant_type=refresh_token" in body
        assert "refresh_token=" in body
        assert request.url.host == "oauth2.googleapis.com"
        return httpx.Response(200, json={"access_token": "short-lived", "expires_in": 3600})

    respx.post("https://oauth2.googleapis.com/token").mock(side_effect=assert_form)
    from services.gsc_mcp.oauth_google import GoogleOAuthTokenProvider

    http = GoogleHttpClient(30.0, 0, "test-agent", token_provider=None)
    provider = GoogleOAuthTokenProvider(settings=settings, http=http)
    assert provider.get_access_token() == "short-lived"


@respx.mock
def test_authorization_code_exchange_uses_form_encoding() -> None:
    captured: dict[str, str] = {}

    def assert_form(request: httpx.Request) -> httpx.Response:
        assert request.headers["content-type"].startswith("application/x-www-form-urlencoded")
        captured["body"] = request.content.decode()
        return httpx.Response(200, json={"refresh_token": "rt", "access_token": "at"})

    respx.post("https://oauth2.googleapis.com/token").mock(side_effect=assert_form)
    exchange_authorization_code(
        client_id="cid",
        client_secret="sec",
        code="auth-code",
        redirect_uri="http://127.0.0.1:8765/oauth/callback",
        code_verifier="verifier-value",
    )
    body = captured["body"]
    assert "grant_type=authorization_code" in body
    assert "code_verifier=verifier-value" in body
    assert "code=auth-code" in body


def test_loopback_binds_localhost_only() -> None:
    server = LoopbackOAuthServer.start(expected_state="expected-state-value")
    try:
        assert server.host == "127.0.0.1"
        assert server.port > 0
    finally:
        server.shutdown()


def test_loopback_callback_success_and_shutdown() -> None:
    state = "test-state-12345"
    server = LoopbackOAuthServer.start(expected_state=state)
    try:
        url = f"{server.redirect_uri}?state={state}&code=authcode123"
        with urllib.request.urlopen(url, timeout=5) as resp:
            assert resp.status == 200
        result = server.wait_for_result(timeout_seconds=5.0)
        assert result.code == "authcode123"
        assert result.error is None
    finally:
        server.shutdown()


def test_loopback_state_mismatch() -> None:
    server = LoopbackOAuthServer.start(expected_state="good-state")
    try:
        url = f"{server.redirect_uri}?state=bad-state&code=authcode123"
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(url, timeout=5)
        assert exc.value.code == 400
        result = server.wait_for_result(timeout_seconds=5.0)
        assert result.error == "invalid_state"
        assert result.code is None
    finally:
        server.shutdown()


def test_loopback_missing_code() -> None:
    server = LoopbackOAuthServer.start(expected_state="only-state")
    try:
        url = f"{server.redirect_uri}?state=only-state"
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(url, timeout=5)
        result = server.wait_for_result(timeout_seconds=5.0)
        assert result.error == "missing_code"
    finally:
        server.shutdown()


def test_loopback_oauth_error_param() -> None:
    server = LoopbackOAuthServer.start(expected_state="st")
    try:
        url = f"{server.redirect_uri}?state=st&error=access_denied"
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(url, timeout=5)
        result = server.wait_for_result(timeout_seconds=5.0)
        assert result.error == "access_denied"
    finally:
        server.shutdown()


def test_credentials_file_mode_and_fields(tmp_path: Path) -> None:
    out = tmp_path / "credentials.json"
    write_credentials_file(
        out,
        client_id="cid",
        client_secret="TEST_CLIENT_SECRET_DO_NOT_LEAK",
        refresh_token="TEST_REFRESH_TOKEN_DO_NOT_LEAK",
    )
    mode = stat.S_IMODE(out.stat().st_mode)
    assert mode == 0o600
    data = json.loads(out.read_text())
    assert data["scope"] == GOOGLE_OAUTH_SCOPE
    assert "code_verifier" not in data
    assert "state" not in data
    assert "access_token" not in data
    assert data["refresh_token"] == "TEST_REFRESH_TOKEN_DO_NOT_LEAK"


@respx.mock
def test_run_bootstrap_persists_refresh_token_only(tmp_path: Path) -> None:
    out = tmp_path / "creds.json"

    def token_response(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"refresh_token": "TEST_REFRESH_TOKEN_DO_NOT_LEAK", "access_token": "x"})

    respx.post("https://oauth2.googleapis.com/token").mock(side_effect=token_response)

    state_holder: dict[str, str] = {}
    real_start = LoopbackOAuthServer.start

    def fake_start(*, expected_state: str, callback_path: str = "/oauth/callback") -> LoopbackOAuthServer:
        state_holder["state"] = expected_state
        srv = real_start(expected_state=expected_state, callback_path=callback_path)
        url = f"{srv.redirect_uri}?state={expected_state}&code=the-code"
        urllib.request.urlopen(url, timeout=5)
        return srv

    with patch.object(LoopbackOAuthServer, "start", side_effect=fake_start):
        with patch("services.gsc_mcp.bootstrap_oauth.webbrowser.open"):
            run_bootstrap(
                client_id="cid",
                client_secret="sec",
                output=out,
                open_browser=False,
            )

    saved = json.loads(out.read_text())
    assert "TEST_REFRESH_TOKEN_DO_NOT_LEAK" in saved["refresh_token"]
    assert "the-code" not in json.dumps(saved)
    assert "code_verifier" not in saved
    assert state_holder["state"] not in json.dumps(saved)


def test_authorization_url_includes_pkce_and_readonly_scope() -> None:
    from services.gsc_mcp.oauth_google import build_authorization_url

    url = build_authorization_url(
        client_id="cid",
        redirect_uri="http://127.0.0.1:1/oauth/callback",
        state="state",
        code_challenge="challenge",
    )
    assert "code_challenge=challenge" in url
    assert "code_challenge_method=S256" in url
    assert GOOGLE_OAUTH_SCOPE in url
    assert "webmasters.readonly" in url
    assert "https://www.googleapis.com/auth/webmasters&" not in url
