from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer
from starlette.requests import Request
from starlette.responses import JSONResponse

from services.gsc_mcp.config import DEFAULT_GSC_SITE_URL, Settings
from services.gsc_mcp.errors import ErrorCode, GscMcpError
from services.gsc_mcp.mcp_auth import build_token_verifier
from services.gsc_mcp.normalize import (
    normalize_crux_record,
    normalize_inspection,
    normalize_search_analytics,
    normalize_sitemap_get,
    normalize_sitemap_list,
)
from services.gsc_mcp.service_context import ServiceContext, build_service_context
from services.gsc_mcp.validators import (
    validate_date_range,
    validate_dimensions,
    validate_inspection_url,
    validate_property,
    validate_row_limit,
    validate_search_analytics_filters,
    validate_search_type,
)

logger = logging.getLogger(__name__)

CAPABILITIES: dict[str, str] = {
    "search_analytics": "supported",
    "sites": "read_only",
    "sitemaps": "read_only",
    "url_inspection_indexed_version": "supported",
    "live_url_test": "NOT_SUPPORTED_BY_API",
    "page_indexing_aggregate_report": "NOT_SUPPORTED_BY_PUBLIC_GSC_API",
    "core_web_vitals_search_console_report": "NOT_DIRECTLY_SUPPORTED",
    "crux_field_data": "supported_if_api_key_and_data_available",
    "sitemap_submission": "intentionally_disabled",
    "request_indexing": "intentionally_disabled",
}


def _log_tool_result(tool_name: str, request_id: str, started: float, result: dict[str, Any]) -> None:
    duration_ms = int((time.time() - started) * 1000)
    error_code = result.get("error_code")
    count = None
    if "rows" in result:
        count = len(result.get("rows") or [])
    elif "sitemaps" in result:
        count = len(result.get("sitemaps") or [])
    logger.info(
        "tool=%s request_id=%s duration_ms=%s result_count=%s error_code=%s",
        tool_name,
        request_id,
        duration_ms,
        count,
        error_code,
    )


def _ok(data: dict[str, Any]) -> dict[str, Any]:
    return data


def _handle_tool_error(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, GscMcpError):
        return exc.as_dict()
    return GscMcpError(ErrorCode.INTERNAL_ERROR, str(exc)).as_dict()


def build_mcp_server(settings: Settings | None = None, ctx: ServiceContext | None = None) -> MCPServer:
    settings = settings or Settings()
    ctx = ctx or build_service_context(settings)

    auth_settings = AuthSettings(
        issuer_url=settings.mcp_public_base_url,
        resource_server_url=settings.mcp_public_base_url,
        validate_token_resource=False,
    )
    token_verifier = build_token_verifier(settings.karzar_mcp_access_token)

    server = MCPServer(
        name="karzar-gsc-mcp",
        title="Karzar GSC Read-Only MCP",
        description="Read-only Google Search Console and CrUX data access for Karzar.",
        version="0.1.0",
        auth=auth_settings,
        token_verifier=token_verifier,
    )

    @server.custom_route("/health", methods=["GET"])
    async def health(_: Request) -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "google_oauth_configured": ctx.oauth.configured(),
                "crux_configured": ctx.crux.configured(),
                "mcp_auth_configured": settings.mcp_auth_configured,
            }
        )

    def _site(site_url: str | None) -> str:
        return site_url or ctx.settings.gsc_site_url

    @server.tool(
        description=(
            "READ-ONLY: List Search Console properties visible to the configured Google account "
            "(Sites.list). No write side effects."
        )
    )
    async def gsc_list_properties() -> dict[str, Any]:
        request_id = str(uuid.uuid4())
        started = time.time()
        try:
            if not ctx.oauth.configured():
                raise GscMcpError(ErrorCode.AUTH_NOT_CONFIGURED, "Google OAuth is not configured")
            data = ctx.gsc.list_sites()
            entries = []
            for entry in data.get("siteEntry") or []:
                entries.append(
                    {"site_url": entry.get("siteUrl"), "permission_level": entry.get("permissionLevel")}
                )
            result = _ok({"status": "OK", "properties": entries})
            _log_tool_result("gsc_list_properties", request_id, started, result)
            return result
        except Exception as exc:
            result = _handle_tool_error(exc)
            _log_tool_result("gsc_list_properties", request_id, started, result)
            return result

    @server.tool(
        description=(
            "READ-ONLY: Get one Search Console property permission record (Sites.get). "
            f"Default property: {DEFAULT_GSC_SITE_URL}. "
            "Foreign properties are rejected unless GSC_ALLOW_FOREIGN_PROPERTIES is enabled."
        )
    )
    async def gsc_get_property(site_url: str | None = None) -> dict[str, Any]:
        request_id = str(uuid.uuid4())
        started = time.time()
        try:
            prop = _site(site_url)
            validate_property(prop, ctx.settings.gsc_site_url, ctx.settings.gsc_allow_foreign_properties)
            data = ctx.gsc.get_site(prop)
            result = _ok(
                {
                    "status": "OK",
                    "site_url": data.get("siteUrl"),
                    "permission_level": data.get("permissionLevel"),
                }
            )
            _log_tool_result("gsc_get_property", request_id, started, result)
            return result
        except Exception as exc:
            result = _handle_tool_error(exc)
            _log_tool_result("gsc_get_property", request_id, started, result)
            return result

    @server.tool(
        description=(
            "READ-ONLY: Query Search Console Search Analytics (searchAnalytics.query). "
            "Data may be incomplete: privacy/anonymization and API limits mean sum(query rows) "
            "does not necessarily equal site totals. No write side effects."
        )
    )
    async def gsc_search_analytics(
        start_date: str,
        end_date: str,
        dimensions: list[str] | None = None,
        search_type: str | None = "web",
        row_limit: int | None = 1000,
        start_row: int | None = 0,
        filters: list[dict[str, Any]] | None = None,
        data_state: str | None = None,
        site_url: str | None = None,
    ) -> dict[str, Any]:
        request_id = str(uuid.uuid4())
        started = time.time()
        try:
            ctx.analytics_limiter.acquire("search_analytics")
            prop = _site(site_url)
            validate_property(prop, ctx.settings.gsc_site_url, ctx.settings.gsc_allow_foreign_properties)
            validate_date_range(start_date, end_date, ctx.settings.gsc_max_date_span_days)
            dims = validate_dimensions(dimensions)
            st = validate_search_type(search_type)
            limit = validate_row_limit(row_limit, ctx.settings.gsc_max_row_limit)
            start = start_row or 0
            if start < 0:
                raise GscMcpError(ErrorCode.INVALID_ARGUMENT, "start_row must be >= 0")
            validated_filters = validate_search_analytics_filters(filters)
            body: dict[str, Any] = {
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": dims,
                "type": st,
                "rowLimit": limit,
                "startRow": start,
            }
            if validated_filters:
                body["dimensionFilterGroups"] = [{"filters": validated_filters}]
            if data_state:
                body["dataState"] = data_state
            raw = ctx.gsc.search_analytics_query(prop, body)
            result = normalize_search_analytics(raw)
            if len(result.get("rows") or []) >= limit:
                result["truncated"] = True
            _log_tool_result("gsc_search_analytics", request_id, started, result)
            return result
        except Exception as exc:
            result = _handle_tool_error(exc)
            _log_tool_result("gsc_search_analytics", request_id, started, result)
            return result

    @server.tool(description="READ-ONLY: List sitemaps for the configured property (Sitemaps.list).")
    async def gsc_list_sitemaps(site_url: str | None = None) -> dict[str, Any]:
        request_id = str(uuid.uuid4())
        started = time.time()
        try:
            prop = _site(site_url)
            validate_property(prop, ctx.settings.gsc_site_url, ctx.settings.gsc_allow_foreign_properties)
            raw = ctx.gsc.list_sitemaps(prop)
            result = normalize_sitemap_list(raw)
            _log_tool_result("gsc_list_sitemaps", request_id, started, result)
            return result
        except Exception as exc:
            result = _handle_tool_error(exc)
            _log_tool_result("gsc_list_sitemaps", request_id, started, result)
            return result

    @server.tool(description="READ-ONLY: Get one sitemap record (Sitemaps.get). No submit/delete.")
    async def gsc_get_sitemap(sitemap_url: str, site_url: str | None = None) -> dict[str, Any]:
        request_id = str(uuid.uuid4())
        started = time.time()
        try:
            prop = _site(site_url)
            validate_property(prop, ctx.settings.gsc_site_url, ctx.settings.gsc_allow_foreign_properties)
            validate_inspection_url(sitemap_url, ctx.settings.allowed_origins)
            raw = ctx.gsc.get_sitemap(prop, sitemap_url)
            result = normalize_sitemap_get(raw)
            _log_tool_result("gsc_get_sitemap", request_id, started, result)
            return result
        except Exception as exc:
            result = _handle_tool_error(exc)
            _log_tool_result("gsc_get_sitemap", request_id, started, result)
            return result

    @server.tool(
        description=(
            "READ-ONLY: URL Inspection API (index.inspect) for the configured property. "
            "This inspects the version known to the Google index. "
            "It is not Google's live URL test. Only Karzar storefront origins are allowed."
        )
    )
    async def gsc_inspect_url(
        inspection_url: str,
        language_code: str | None = None,
        site_url: str | None = None,
    ) -> dict[str, Any]:
        request_id = str(uuid.uuid4())
        started = time.time()
        try:
            ctx.inspection_limiter.acquire()
            prop = _site(site_url)
            validate_property(prop, ctx.settings.gsc_site_url, ctx.settings.gsc_allow_foreign_properties)
            url = validate_inspection_url(inspection_url, ctx.settings.allowed_origins)
            raw = ctx.inspection.inspect(prop, url, language_code=language_code)
            result = normalize_inspection(raw)
            _log_tool_result("gsc_inspect_url", request_id, started, result)
            return result
        except Exception as exc:
            result = _handle_tool_error(exc)
            _log_tool_result("gsc_inspect_url", request_id, started, result)
            return result

    @server.tool(
        description=(
            "READ-ONLY: Chrome UX Report field data for the default origin "
            "(https://www.karzartools.com). Requires CRUX_API_KEY. No write side effects."
        )
    )
    async def crux_get_origin_field_data(
        origin: str | None = None,
        form_factor: str | None = None,
    ) -> dict[str, Any]:
        request_id = str(uuid.uuid4())
        started = time.time()
        try:
            if not ctx.crux.configured():
                raise GscMcpError(ErrorCode.CRUX_NOT_CONFIGURED, "CRUX_API_KEY is not configured")
            o = origin or "https://www.karzartools.com"
            validate_inspection_url(o, ctx.settings.allowed_origins)
            body: dict[str, Any] = {"origin": o}
            if form_factor:
                body["formFactor"] = form_factor
            raw = ctx.crux.query_record(body)
            result = normalize_crux_record(raw)
            _log_tool_result("crux_get_origin_field_data", request_id, started, result)
            return result
        except Exception as exc:
            result = _handle_tool_error(exc)
            _log_tool_result("crux_get_origin_field_data", request_id, started, result)
            return result

    @server.tool(
        description=(
            "READ-ONLY: Chrome UX Report page-level field data. Karzar URL allowlist applies. "
            "Does not silently substitute origin-level data when page data is unavailable."
        )
    )
    async def crux_get_url_field_data(
        url: str,
        form_factor: str | None = None,
    ) -> dict[str, Any]:
        request_id = str(uuid.uuid4())
        started = time.time()
        try:
            if not ctx.crux.configured():
                raise GscMcpError(ErrorCode.CRUX_NOT_CONFIGURED, "CRUX_API_KEY is not configured")
            validated = validate_inspection_url(url, ctx.settings.allowed_origins)
            body: dict[str, Any] = {"url": validated}
            if form_factor:
                body["formFactor"] = form_factor
            raw = ctx.crux.query_record(body)
            result = normalize_crux_record(raw)
            if result.get("status") == "NO_DATA":
                result["origin_fallback_available"] = True
            _log_tool_result("crux_get_url_field_data", request_id, started, result)
            return result
        except Exception as exc:
            result = _handle_tool_error(exc)
            _log_tool_result("crux_get_url_field_data", request_id, started, result)
            return result

    @server.tool(
        description="Return static capability map so clients do not hallucinate unsupported GSC features."
    )
    async def gsc_capabilities() -> dict[str, Any]:
        return {
            "status": "OK",
            "capabilities": CAPABILITIES,
            "readonly_scope": "https://www.googleapis.com/auth/webmasters.readonly",
        }

    @server.tool(
        description="READ-ONLY diagnostic: calls Sites.list to verify Google OAuth (optional)."
    )
    async def gsc_auth_probe() -> dict[str, Any]:
        request_id = str(uuid.uuid4())
        started = time.time()
        try:
            if not ctx.oauth.configured():
                raise GscMcpError(ErrorCode.AUTH_NOT_CONFIGURED, "Google OAuth is not configured")
            data = ctx.gsc.list_sites()
            count = len(data.get("siteEntry") or [])
            result = _ok({"status": "OK", "property_count": count})
            _log_tool_result("gsc_auth_probe", request_id, started, result)
            return result
        except Exception as exc:
            result = _handle_tool_error(exc)
            _log_tool_result("gsc_auth_probe", request_id, started, result)
            return result

    return server


def run_streamable_http(settings: Settings | None = None) -> None:
    settings = settings or Settings()
    server = build_mcp_server(settings)
    server.run(
        transport="streamable-http",
        host=settings.mcp_host,
        port=settings.mcp_port,
        streamable_http_path="/mcp",
    )
