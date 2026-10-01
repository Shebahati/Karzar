from __future__ import annotations

from typing import Any


def normalize_search_analytics(data: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for row in data.get("rows") or []:
        rows.append(
            {
                "keys": row.get("keys"),
                "clicks": row.get("clicks"),
                "impressions": row.get("impressions"),
                "ctr": row.get("ctr"),
                "position": row.get("position"),
            }
        )
    return {
        "status": "OK",
        "rows": rows,
        "responseAggregationType": data.get("responseAggregationType"),
        "metadata": {
            "data_limitation": (
                "Search Analytics does not guarantee all query rows; privacy and API limits "
                "mean sum(query rows) may not equal site totals."
            ),
        },
    }


def normalize_sitemap_list(data: dict[str, Any]) -> dict[str, Any]:
    sitemaps = []
    for sm in data.get("sitemap") or []:
        sitemaps.append(
            {
                "path": sm.get("path"),
                "lastSubmitted": sm.get("lastSubmitted"),
                "lastDownloaded": sm.get("lastDownloaded"),
                "isPending": sm.get("isPending"),
                "isSitemapsIndex": sm.get("isSitemapsIndex"),
                "type": sm.get("type"),
                "warnings": sm.get("warnings"),
                "errors": sm.get("errors"),
                "contents": sm.get("contents"),
            }
        )
    return {"status": "OK", "sitemaps": sitemaps}


def normalize_sitemap_get(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "OK",
        "path": data.get("path"),
        "lastSubmitted": data.get("lastSubmitted"),
        "lastDownloaded": data.get("lastDownloaded"),
        "isPending": data.get("isPending"),
        "isSitemapsIndex": data.get("isSitemapsIndex"),
        "type": data.get("type"),
        "warnings": data.get("warnings"),
        "errors": data.get("errors"),
        "contents": data.get("contents"),
    }


def normalize_inspection(data: dict[str, Any]) -> dict[str, Any]:
    result = data.get("inspectionResult") or {}
    index_status = result.get("indexStatusResult") or {}
    return {
        "status": "OK",
        "inspectionResult": {
            "verdict": index_status.get("verdict"),
            "coverageState": index_status.get("coverageState"),
            "robotsTxtState": index_status.get("robotsTxtState"),
            "indexingState": index_status.get("indexingState"),
            "lastCrawlTime": index_status.get("lastCrawlTime"),
            "pageFetchState": index_status.get("pageFetchState"),
            "googleCanonical": index_status.get("googleCanonical"),
            "userCanonical": index_status.get("userCanonical"),
            "crawledAs": index_status.get("crawledAs"),
            "referringUrls": index_status.get("referringUrls"),
            "sitemap": index_status.get("sitemap"),
        },
        "note": (
            "This inspects the version known to the Google index. "
            "It is not Google's live URL test."
        ),
    }


def normalize_crux_record(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("status") == "NO_DATA":
        return {"status": "NO_DATA", "metrics": None}
    record = result.get("record") or {}
    metrics = record.get("metrics") or {}
    out_metrics: dict[str, Any] = {}
    for key in ("largest_contentful_paint", "interaction_to_next_paint", "cumulative_layout_shift", "first_contentful_paint", "experimental_time_to_first_byte"):
        if key in metrics:
            out_metrics[key] = metrics[key]
    labels = {
        "largest_contentful_paint": "LCP",
        "interaction_to_next_paint": "INP",
        "cumulative_layout_shift": "CLS",
        "first_contentful_paint": "FCP",
        "experimental_time_to_first_byte": "TTFB",
    }
    friendly: dict[str, Any] = {}
    for k, v in out_metrics.items():
        friendly[labels.get(k, k)] = v
    return {
        "status": "OK",
        "metrics": friendly,
        "collectionPeriod": record.get("collectionPeriod"),
    }
