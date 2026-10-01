from __future__ import annotations

from dataclasses import dataclass

from services.gsc_mcp.clients import CruxClient, SearchConsoleClient, UrlInspectionClient
from services.gsc_mcp.config import Settings
from services.gsc_mcp.http_google import GoogleHttpClient
from services.gsc_mcp.limits import InMemoryRateLimiter, InspectionRateLimiter
from services.gsc_mcp.oauth_google import GoogleOAuthTokenProvider


@dataclass
class ServiceContext:
    settings: Settings
    http: GoogleHttpClient
    oauth: GoogleOAuthTokenProvider
    gsc: SearchConsoleClient
    inspection: UrlInspectionClient
    crux: CruxClient
    inspection_limiter: InspectionRateLimiter
    analytics_limiter: InMemoryRateLimiter


def build_service_context(settings: Settings) -> ServiceContext:
    oauth = GoogleOAuthTokenProvider(settings=settings)
    http = GoogleHttpClient(
        timeout_seconds=settings.gsc_http_timeout_seconds,
        max_retries=settings.gsc_max_retries,
        user_agent=settings.user_agent,
        token_provider=oauth,
        max_response_bytes=settings.gsc_max_response_bytes,
    )
    oauth.http = http
    return ServiceContext(
        settings=settings,
        http=http,
        oauth=oauth,
        gsc=SearchConsoleClient(http),
        inspection=UrlInspectionClient(http),
        crux=CruxClient(http, settings.crux_api_key),
        inspection_limiter=InspectionRateLimiter(settings.gsc_inspection_daily_soft_limit),
        analytics_limiter=InMemoryRateLimiter(max_per_minute=30),
    )
