from __future__ import annotations

from typing import Any

from services.gsc_mcp.http_google import GoogleHttpClient


class UrlInspectionClient:
    INSPECT_URL = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"

    def __init__(self, http: GoogleHttpClient) -> None:
        self._http = http

    def inspect(self, site_url: str, inspection_url: str, language_code: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "inspectionUrl": inspection_url,
            "siteUrl": site_url,
        }
        if language_code:
            body["languageCode"] = language_code
        resp = self._http.request("POST", self.INSPECT_URL, json_body=body)
        return resp.json()
