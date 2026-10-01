from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any

from services.gsc_mcp.config import GOOGLE_OAUTH_SCOPE, Settings
from services.gsc_mcp.errors import ErrorCode, GscMcpError
from services.gsc_mcp.http_google import GoogleHttpClient
from services.gsc_mcp.redaction import redact_text

logger = logging.getLogger(__name__)

TOKEN_URL = "https://oauth2.googleapis.com/token"


@dataclass
class GoogleOAuthTokenProvider:
    settings: Settings
    http: GoogleHttpClient | None = None
    _access_token: str | None = None
    _expires_at: float = 0.0
    _lock: Lock = Lock()

    def configured(self) -> bool:
        return self.settings.google_oauth_configured

    def _refresh(self) -> None:
        if not self.configured():
            raise GscMcpError(ErrorCode.AUTH_NOT_CONFIGURED, "Google OAuth is not configured")
        body = {
            "client_id": self.settings.google_gsc_client_id,
            "client_secret": self.settings.google_gsc_client_secret,
            "refresh_token": self.settings.google_gsc_refresh_token,
            "grant_type": "refresh_token",
        }
        if not self.http:
            raise GscMcpError(ErrorCode.INTERNAL_ERROR, "HTTP client not initialized")
        try:
            response = self.http.request(
                "POST",
                TOKEN_URL,
                json_body=body,
                skip_auth=True,
            )
        except GscMcpError:
            raise
        except Exception as exc:
            logger.exception("OAuth refresh failed")
            raise GscMcpError(ErrorCode.AUTH_REFRESH_FAILED, "Failed to refresh Google access token") from exc

        data: dict[str, Any] = response.json()
        token = data.get("access_token")
        if not token:
            raise GscMcpError(ErrorCode.AUTH_REFRESH_FAILED, "OAuth response missing access_token")
        expires_in = int(data.get("expires_in", 3600))
        self._access_token = str(token)
        self._expires_at = time.time() + max(expires_in - 60, 30)
        logger.info("Google access token refreshed (expires_in=%s)", expires_in)

    def get_access_token(self) -> str:
        with self._lock:
            if self._access_token and time.time() < self._expires_at:
                return self._access_token
            self._refresh()
            if not self._access_token:
                raise GscMcpError(ErrorCode.AUTH_REFRESH_FAILED, "No access token after refresh")
            return self._access_token

    def auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.get_access_token()}"}


def exchange_authorization_code(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    http: GoogleHttpClient | None = None,
) -> dict[str, Any]:
    client = http or GoogleHttpClient(
        timeout_seconds=30.0,
        max_retries=2,
        user_agent="Karzar-GSC-MCP-bootstrap/0.1",
        token_provider=None,
    )
    response = client.request(
        "POST",
        TOKEN_URL,
        json_body={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        skip_auth=True,
    )
    return response.json()


def build_authorization_url(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
) -> str:
    from urllib.parse import urlencode

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_OAUTH_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


def safe_log_oauth_failure(message: str) -> str:
    return redact_text(message)
