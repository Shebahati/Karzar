from __future__ import annotations

import httpx
import pytest
import respx

from services.gsc_mcp.clients import CruxClient, SearchConsoleClient, UrlInspectionClient
from services.gsc_mcp.errors import ErrorCode
from services.gsc_mcp.http_google import GoogleHttpClient
from services.gsc_mcp.normalize import (
    normalize_inspection,
    normalize_search_analytics,
    normalize_sitemap_get,
    normalize_sitemap_list,
)


def _http() -> GoogleHttpClient:
    provider = type("P", (), {"auth_headers": lambda self: {"Authorization": "Bearer t"}})()
    return GoogleHttpClient(10.0, 0, "ua", token_provider=provider)


@respx.mock
def test_search_analytics_normalization() -> None:
    respx.post("https://www.googleapis.com/webmasters/v3/sites/sc-domain%3Akarzartools.com/searchAnalytics/query").mock(
        return_value=httpx.Response(
            200,
            json={
                "rows": [{"keys": ["q"], "clicks": 1, "impressions": 2, "ctr": 0.5, "position": 3.0}],
                "responseAggregationType": "byProperty",
            },
        )
    )
    client = SearchConsoleClient(_http())
    raw = client.search_analytics_query(
        "sc-domain:karzartools.com",
        {"startDate": "2025-01-01", "endDate": "2025-01-07", "dimensions": ["query"]},
    )
    norm = normalize_search_analytics(raw)
    assert norm["rows"][0]["clicks"] == 1
    assert "data_limitation" in norm["metadata"]


@respx.mock
def test_sitemap_list_and_get_normalization() -> None:
    respx.get("https://www.googleapis.com/webmasters/v3/sites/sc-domain%3Akarzartools.com/sitemaps").mock(
        return_value=httpx.Response(200, json={"sitemap": [{"path": "https://www.karzartools.com/sitemap.xml"}]})
    )
    respx.get(
        "https://www.googleapis.com/webmasters/v3/sites/sc-domain%3Akarzartools.com/sitemaps/https%3A%2F%2Fwww.karzartools.com%2Fsitemap.xml"
    ).mock(return_value=httpx.Response(200, json={"path": "https://www.karzartools.com/sitemap.xml"}))
    gsc = SearchConsoleClient(_http())
    listed = normalize_sitemap_list(gsc.list_sitemaps("sc-domain:karzartools.com"))
    assert listed["sitemaps"][0]["path"].endswith("sitemap.xml")
    got = normalize_sitemap_get(
        gsc.get_sitemap("sc-domain:karzartools.com", "https://www.karzartools.com/sitemap.xml")
    )
    assert got["status"] == "OK"


@respx.mock
def test_url_inspection_normalization() -> None:
    respx.post("https://searchconsole.googleapis.com/v1/urlInspection/index:inspect").mock(
        return_value=httpx.Response(
            200,
            json={
                "inspectionResult": {
                    "indexStatusResult": {
                        "verdict": "PASS",
                        "coverageState": "Submitted and indexed",
                    }
                }
            },
        )
    )
    client = UrlInspectionClient(_http())
    raw = client.inspect("sc-domain:karzartools.com", "https://www.karzartools.com/")
    norm = normalize_inspection(raw)
    assert norm["inspectionResult"]["verdict"] == "PASS"
    assert "not Google's live URL test" in norm["note"]


@respx.mock
def test_crux_success_and_no_data_and_missing_key() -> None:
    http = _http()
    with pytest.raises(Exception) as exc:
        CruxClient(http, None).query_record({"origin": "https://www.karzartools.com"})
    assert getattr(exc.value, "code", None) == ErrorCode.CRUX_NOT_CONFIGURED

    respx.post(url__regex=r"https://chromeuxreport\.googleapis\.com/v1/records:queryRecord.*").mock(
        return_value=httpx.Response(200, json={"record": {"metrics": {}}})
    )
    client = CruxClient(http, "TEST_CRUX_KEY_DO_NOT_LEAK")
    ok = client.query_record({"origin": "https://www.karzartools.com"})
    assert ok["status"] == "OK"

    respx.post(url__regex=r"https://chromeuxreport\.googleapis\.com/v1/records:queryRecord.*").mock(
        return_value=httpx.Response(200, json={})
    )
    no_data = client.query_record({"origin": "https://www.karzartools.com"})
    assert no_data["status"] == "NO_DATA"
