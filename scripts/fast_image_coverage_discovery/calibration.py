"""Source calibration records."""

from __future__ import annotations

from .sources.wc_store import SourceIndex


def calibration_rows(indexes: dict[str, SourceIndex]) -> list[dict]:
    rows = []
    for sid, idx in indexes.items():
        rows.append(
            {
                "source_id": sid,
                "domain": idx.domain,
                "calibration_checked": idx.calibration_checked,
                "calibration_passed": idx.calibration_passed,
                "bulk_enabled": idx.bulk_enabled,
                "indexed_skus": len(idx.by_sku),
                "last_error": idx.last_error,
            }
        )
    return rows
