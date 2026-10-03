from __future__ import annotations

from typing import Any
from urllib.parse import quote

from services.gsc_mcp.http_google import GoogleHttpClient


class SearchConsoleClient:
    BASE = "https://www.googleapis.com/webmasters/v3"

    def __init__(self, http: GoogleHttpClient) -> None:
        self._http = http

    def _site_path(self, site_url: str) -> str:
        return quote(site_url, safe="")

    def list_sites(self) -> dict[str, Any]:
        resp = self._http.request("GET", f"{self.BASE}/sites")
        return resp.json()

    def get_site(self, site_url: str) -> dict[str, Any]:
        resp = self._http.request("GET", f"{self.BASE}/sites/{self._site_path(site_url)}")
        return resp.json()

    def search_analytics_query(self, site_url: str, body: dict[str, Any]) -> dict[str, Any]:
        resp = self._http.request(
            "POST",
            f"{self.BASE}/sites/{self._site_path(site_url)}/searchAnalytics/query",
            json_body=body,
        )
        return resp.json()

    def list_sitemaps(self, site_url: str) -> dict[str, Any]:
        resp = self._http.request("GET", f"{self.BASE}/sites/{self._site_path(site_url)}/sitemaps")
        return resp.json()

    def get_sitemap(self, site_url: str, sitemap_url: str) -> dict[str, Any]:
        sm = quote(sitemap_url, safe="")
        resp = self._http.request(
            "GET",
            f"{self.BASE}/sites/{self._site_path(site_url)}/sitemaps/{sm}",
        )
        return resp.json()
