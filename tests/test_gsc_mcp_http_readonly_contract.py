from __future__ import annotations

import re
from typing import Any
from urllib.parse import unquote, urlparse

import httpx
import respx

from services.gsc_mcp.clients import SearchConsoleClient, UrlInspectionClient
from services.gsc_mcp.http_google import GoogleHttpResponse

SITE = "sc-domain:karzartools.com"
SITEMAP = "https://www.karzartools.com/sitemap.xml"
INSPECT_URL = "https://www.karzartools.com/"


class RecordingGoogleHttp:
    """Captures outbound Google HTTP calls for read-only contract assertions."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def request(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        skip_auth: bool = False,
        extra_headers: dict[str, str] | None = None,
    ) -> GoogleHttpResponse:
        self.calls.append((method.upper(), url))
        return GoogleHttpResponse(status_code=200, headers={}, content=b"{}")

    def auth_headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer test"}


def _normalize_gsc_path(url: str) -> str:
    parsed = urlparse(url)
    path = unquote(parsed.path)
    path = re.sub(r"^/sites/[^/]+", "/sites/{site}", path)
    if "/sitemaps/" in path:
        path = re.sub(r"/sitemaps/.*", "/sitemaps/{sitemap}", path)
    return f"{parsed.scheme}://{parsed.netloc}{path}"


ALLOWED_GSC_CALLS = frozenset(
    {
        ("GET", "https://www.googleapis.com/webmasters/v3/sites"),
        ("GET", "https://www.googleapis.com/webmasters/v3/sites/{site}"),
        (
            "POST",
            "https://www.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query",
        ),
        ("GET", "https://www.googleapis.com/webmasters/v3/sites/{site}/sitemaps"),
        ("GET", "https://www.googleapis.com/webmasters/v3/sites/{site}/sitemaps/{sitemap}"),
    }
)

ALLOWED_INSPECTION_CALLS = frozenset(
    {
        ("POST", "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"),
    }
)

FORBIDDEN_METHODS = frozenset({"PUT", "PATCH", "DELETE"})


def test_search_console_client_http_read_only_surface() -> None:
    http = RecordingGoogleHttp()
    gsc = SearchConsoleClient(http)

    gsc.list_sites()
    gsc.get_site(SITE)
    gsc.search_analytics_query(
        SITE,
        {"startDate": "2025-01-01", "endDate": "2025-01-07", "dimensions": ["query"]},
    )
    gsc.list_sitemaps(SITE)
    gsc.get_sitemap(SITE, SITEMAP)

    for method, url in http.calls:
        assert method not in FORBIDDEN_METHODS
        key = (method, _normalize_gsc_path(url))
        assert key in ALLOWED_GSC_CALLS, f"Unexpected GSC call: {method} {url}"

    assert len(http.calls) == 5


def test_url_inspection_client_http_read_only_post() -> None:
    http = RecordingGoogleHttp()
    inspection = UrlInspectionClient(http)
    inspection.inspect(SITE, INSPECT_URL)

    assert len(http.calls) == 1
    method, url = http.calls[0]
    assert method == "POST"
    assert (method, url) in ALLOWED_INSPECTION_CALLS
    assert method not in FORBIDDEN_METHODS


@respx.mock
def test_no_sitemap_submit_or_indexing_routes_hit() -> None:
    """Prove client methods never call write-style Search Console routes."""
    routes = {
        "submit": respx.put("https://www.googleapis.com/webmasters/v3/sites/sc-domain%3Akarzartools.com/sitemaps/submit"),
        "delete": respx.delete(
            "https://www.googleapis.com/webmasters/v3/sites/sc-domain%3Akarzartools.com/sitemaps/x"
        ),
        "add_site": respx.put("https://www.googleapis.com/webmasters/v3/sites/sc-domain%3Akarzartools.com"),
        "indexing": respx.post("https://indexing.googleapis.com/v3/urlNotifications:publish"),
    }
    for route in routes.values():
        route.mock(return_value=httpx.Response(200, json={}))

    http = RecordingGoogleHttp()
    gsc = SearchConsoleClient(http)
    gsc.list_sitemaps(SITE)

    for name, route in routes.items():
        assert not route.called, f"Write route {name} must not be called"
