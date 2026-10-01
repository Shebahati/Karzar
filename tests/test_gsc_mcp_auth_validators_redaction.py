from __future__ import annotations

import logging

import pytest
from services.gsc_mcp.errors import ErrorCode, GscMcpError
from services.gsc_mcp.mcp_auth import StaticBearerTokenVerifier
from services.gsc_mcp.redaction import redact_text
from services.gsc_mcp.validators import (
    validate_date_range,
    validate_dimensions,
    validate_inspection_url,
    validate_property,
    validate_search_type,
)


@pytest.mark.asyncio
async def test_bearer_auth_valid() -> None:
    verifier = StaticBearerTokenVerifier("TEST_MCP_TOKEN_DO_NOT_LEAK")
    token = await verifier.verify_token("TEST_MCP_TOKEN_DO_NOT_LEAK")
    assert token is not None


@pytest.mark.asyncio
async def test_bearer_auth_invalid() -> None:
    verifier = StaticBearerTokenVerifier("TEST_MCP_TOKEN_DO_NOT_LEAK")
    assert await verifier.verify_token("wrong") is None


@pytest.mark.asyncio
async def test_bearer_auth_missing_config() -> None:
    verifier = StaticBearerTokenVerifier(None)
    assert await verifier.verify_token("anything") is None


def test_property_allowlist() -> None:
    validate_property("sc-domain:karzartools.com", "sc-domain:karzartools.com", False)
    with pytest.raises(GscMcpError) as exc:
        validate_property("sc-domain:evil.com", "sc-domain:karzartools.com", False)
    assert exc.value.code == ErrorCode.PROPERTY_FORBIDDEN


def test_url_allowlist_and_rejections() -> None:
    origins = ("https://www.karzartools.com", "https://karzartools.com")
    validate_inspection_url("https://www.karzartools.com/product/foo", origins)
    with pytest.raises(GscMcpError):
        validate_inspection_url("https://evil.com/x", origins)
    with pytest.raises(GscMcpError):
        validate_inspection_url("http://127.0.0.1/", origins)
    with pytest.raises(GscMcpError):
        validate_inspection_url("javascript:alert(1)", origins)
    with pytest.raises(GscMcpError):
        validate_inspection_url("https://user:pass@www.karzartools.com/", origins)


def test_date_validation() -> None:
    validate_date_range("2025-01-01", "2025-01-28", 480)
    with pytest.raises(GscMcpError):
        validate_date_range("2025-02-01", "2025-01-01", 480)
    with pytest.raises(GscMcpError):
        validate_date_range("2020-01-01", "2026-01-01", 30)


def test_dimension_and_search_type_validation() -> None:
    validate_dimensions(["query", "page"])
    with pytest.raises(GscMcpError):
        validate_dimensions(["not_a_dim"])
    validate_search_type("web")
    with pytest.raises(GscMcpError):
        validate_search_type("invalid")


def test_secret_redaction(caplog: pytest.LogCaptureFixture) -> None:
    raw = (
        "refresh_token=TEST_REFRESH_TOKEN_DO_NOT_LEAK "
        "client_secret=TEST_CLIENT_SECRET_DO_NOT_LEAK "
        "Authorization: Bearer TEST_MCP_TOKEN_DO_NOT_LEAK"
    )
    redacted = redact_text(raw)
    assert "TEST_REFRESH_TOKEN_DO_NOT_LEAK" not in redacted
    assert "TEST_CLIENT_SECRET_DO_NOT_LEAK" not in redacted
    assert "TEST_MCP_TOKEN_DO_NOT_LEAK" not in redacted
    caplog.set_level(logging.INFO)
    logging.getLogger("test").info(redact_text(raw))
    assert "TEST_REFRESH_TOKEN_DO_NOT_LEAK" not in caplog.text


def test_security_sentinel_not_in_redacted_output() -> None:
    msg = "CRUX key CRUX_API_KEY=TEST_CRUX_KEY_DO_NOT_LEAK"
    assert "TEST_CRUX_KEY_DO_NOT_LEAK" not in redact_text(msg)
