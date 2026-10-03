from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest
import respx

from services.gsc_mcp.config import Settings
from services.gsc_mcp.errors import ErrorCode
from services.gsc_mcp.http_google import GoogleHttpClient, map_upstream_error
from services.gsc_mcp.oauth_google import GoogleOAuthTokenProvider


@pytest.fixture
def settings() -> Settings:
    return Settings(
        GOOGLE_GSC_CLIENT_ID="cid",
        GOOGLE_GSC_CLIENT_SECRET="TEST_CLIENT_SECRET_DO_NOT_LEAK",
        GOOGLE_GSC_REFRESH_TOKEN="TEST_REFRESH_TOKEN_DO_NOT_LEAK",
    )


@respx.mock
def test_oauth_refresh_success(settings: Settings) -> None:
    route = respx.post("https://oauth2.googleapis.com/token").mock(
        return_value=httpx.Response(200, json={"access_token": "short-lived", "expires_in": 3600})
    )
    http = GoogleHttpClient(30.0, 2, "test-agent", token_provider=None)
    provider = GoogleOAuthTokenProvider(settings=settings, http=http)
    token = provider.get_access_token()
    assert token == "short-lived"
    assert route.called


@respx.mock
def test_oauth_refresh_failure(settings: Settings) -> None:
    respx.post("https://oauth2.googleapis.com/token").mock(return_value=httpx.Response(400, text="bad"))
    http = GoogleHttpClient(30.0, 0, "test-agent", token_provider=None)
    provider = GoogleOAuthTokenProvider(settings=settings, http=http)
    from services.gsc_mcp.errors import GscMcpError

    with pytest.raises(GscMcpError) as exc:
        provider.get_access_token()
    assert exc.value.code == ErrorCode.AUTH_REFRESH_FAILED


@respx.mock
def test_retry_on_429(settings: Settings) -> None:
    respx.post("https://oauth2.googleapis.com/token").mock(
        side_effect=[
            httpx.Response(429, text="rate"),
            httpx.Response(200, json={"access_token": "ok", "expires_in": 60}),
        ]
    )
    http = GoogleHttpClient(30.0, 2, "test-agent", token_provider=None)
    provider = GoogleOAuthTokenProvider(settings=settings, http=http)
    assert provider.get_access_token() == "ok"


@respx.mock
def test_retry_on_5xx(settings: Settings) -> None:
    respx.get("https://www.googleapis.com/webmasters/v3/sites").mock(
        side_effect=[
            httpx.Response(503, text="down"),
            httpx.Response(200, json={"siteEntry": []}),
        ]
    )
    provider = MagicMock()
    provider.auth_headers.return_value = {"Authorization": "Bearer x"}
    http = GoogleHttpClient(30.0, 2, "test-agent", token_provider=provider)
    resp = http.request("GET", "https://www.googleapis.com/webmasters/v3/sites")
    assert resp.json() == {"siteEntry": []}


def test_403_permission_error() -> None:
    err = map_upstream_error(403, "denied")
    assert err.code == ErrorCode.UPSTREAM_PERMISSION_DENIED


def test_timeout_handling(settings: Settings) -> None:
    with respx.mock:
        respx.post("https://oauth2.googleapis.com/token").mock(side_effect=httpx.TimeoutException("t"))
        http = GoogleHttpClient(0.01, 0, "test-agent", token_provider=None)
        provider = GoogleOAuthTokenProvider(settings=settings, http=http)
        from services.gsc_mcp.errors import GscMcpError

        with pytest.raises(GscMcpError):
            provider.get_access_token()


def test_disallowed_host() -> None:
    http = GoogleHttpClient(5.0, 0, "ua", token_provider=None)
    with pytest.raises(Exception) as exc:
        http.request("GET", "https://evil.example.com/x")
    assert ErrorCode.INVALID_ARGUMENT.value in str(exc.value) or getattr(exc.value, "code", "") == ErrorCode.INVALID_ARGUMENT
