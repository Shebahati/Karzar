from __future__ import annotations

import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient
from services.gsc_mcp.config import Settings
from services.gsc_mcp.server import build_mcp_server
from services.gsc_mcp.service_context import build_service_context

REQUIRED_TOOLS = {
    "gsc_list_properties",
    "gsc_get_property",
    "gsc_search_analytics",
    "gsc_list_sitemaps",
    "gsc_get_sitemap",
    "gsc_inspect_url",
    "crux_get_origin_field_data",
    "crux_get_url_field_data",
    "gsc_capabilities",
}

FORBIDDEN_TOOLS = {
    "gsc_submit_sitemap",
    "gsc_request_indexing",
    "google_api_proxy",
}


@pytest.fixture
def settings() -> Settings:
    return Settings(
        KARZAR_MCP_ACCESS_TOKEN="TEST_MCP_TOKEN_DO_NOT_LEAK",
        GOOGLE_GSC_CLIENT_ID="id",
        GOOGLE_GSC_CLIENT_SECRET="sec",
        GOOGLE_GSC_REFRESH_TOKEN="refresh",
        CRUX_API_KEY="TEST_CRUX_KEY_DO_NOT_LEAK",
    )


@pytest.mark.asyncio
async def test_tool_discovery(settings: Settings) -> None:
    server = build_mcp_server(settings)
    tools = await server.list_tools()
    names = {t.name for t in tools}
    assert REQUIRED_TOOLS.issubset(names)
    assert names.isdisjoint(FORBIDDEN_TOOLS)


@pytest.mark.asyncio
async def test_authenticated_tool_call_mocked(settings: Settings) -> None:
    ctx = build_service_context(settings)
    with respx.mock:
        respx.post("https://oauth2.googleapis.com/token").mock(
            return_value=httpx.Response(200, json={"access_token": "at", "expires_in": 3600})
        )
        respx.get("https://www.googleapis.com/webmasters/v3/sites").mock(
            return_value=httpx.Response(200, json={"siteEntry": []})
        )
        server = build_mcp_server(settings, ctx)
        result = await server.call_tool("gsc_auth_probe", {})
        assert result.is_error is False


@pytest.mark.asyncio
async def test_mcp_http_unauthenticated_rejected(settings: Settings) -> None:
    server = build_mcp_server(settings)
    app = server.streamable_http_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        assert response.status_code in {401, 403, 406}


@pytest.mark.asyncio
async def test_health_without_google_call(settings: Settings) -> None:
    server = build_mcp_server(settings)
    app = server.streamable_http_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
