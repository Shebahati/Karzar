from __future__ import annotations

from typing import Any

from services.gsc_mcp.errors import ErrorCode, GscMcpError
from services.gsc_mcp.http_google import GoogleHttpClient


class CruxClient:
    QUERY_URL = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"

    def __init__(self, http: GoogleHttpClient, api_key: str | None) -> None:
        self._http = http
        self._api_key = api_key

    def configured(self) -> bool:
        return bool(self._api_key)

    def query_record(self, body: dict[str, Any]) -> dict[str, Any]:
        if not self._api_key:
            raise GscMcpError(ErrorCode.CRUX_NOT_CONFIGURED, "CRUX_API_KEY is not configured")
        url = f"{self.QUERY_URL}?key={self._api_key}"
        resp = self._http.request("POST", url, json_body=body)
        data = resp.json()
        if not data.get("record"):
            return {"status": "NO_DATA", "record": None, "raw": data}
        return {"status": "OK", "record": data.get("record"), "raw": data}
