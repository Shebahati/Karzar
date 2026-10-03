from __future__ import annotations

import secrets

from mcp.server.auth.provider import AccessToken, TokenVerifier


class StaticBearerTokenVerifier:
    """Validates MCP client Bearer tokens (not Google OAuth)."""

    def __init__(self, expected_token: str | None) -> None:
        self._expected = expected_token

    async def verify_token(self, token: str) -> AccessToken | None:
        if not self._expected:
            return None
        if secrets.compare_digest(token, self._expected):
            return AccessToken(token=token, client_id="karzar-mcp-client", scopes=["mcp:tools"])
        return None


def build_token_verifier(expected_token: str | None) -> TokenVerifier:
    return StaticBearerTokenVerifier(expected_token)
