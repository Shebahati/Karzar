"""Source calibration records."""

from __future__ import annotations

from .sources.base import SourceAdapter


def calibration_rows(adapters: dict[str, SourceAdapter]) -> list[dict]:
    rows = []
    for sid, adapter in adapters.items():
        cal = adapter.calibration
        rows.append(
            {
                "source_id": sid,
                "domain": adapter.domain,
                "adapter_type": adapter.adapter_type,
                "calibration_checked": cal.checked if cal else 0,
                "calibration_passed": cal.passed if cal else False,
                "bulk_enabled": adapter.bulk_enabled,
                "indexed_skus": len(adapter._index),
                "last_error": adapter.last_error,
            }
        )
    return rows
