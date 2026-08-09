"""Two-run semantic stability comparison."""

from __future__ import annotations

from .contracts import ProductClassification, ScanResult


def compare_runs(run1: ScanResult, run2: ScanResult) -> tuple[bool, list[dict[str, str | int]]]:
    """Semantic stability: same product ID universe and same state per product."""
    ids1 = set(run1.unique_product_ids)
    ids2 = set(run2.unique_product_ids)
    map1 = {c.product_id: c for c in run1.classifications}
    map2 = {c.product_id: c for c in run2.classifications}
    drift: list[dict[str, str | int]] = []

    only1 = ids1 - ids2
    only2 = ids2 - ids1
    for pid in sorted(only1):
        c = map1[pid]
        drift.append(
            {
                "product_id": pid,
                "run1_state": c.image_state,
                "run2_state": "",
                "run1_thumbnail": c.primary_image_reference or "",
                "run2_thumbnail": "",
                "change_reason": "missing_in_run2",
            }
        )
    for pid in sorted(only2):
        c = map2[pid]
        drift.append(
            {
                "product_id": pid,
                "run1_state": "",
                "run2_state": c.image_state,
                "run1_thumbnail": "",
                "run2_thumbnail": c.primary_image_reference or "",
                "change_reason": "missing_in_run1",
            }
        )

    for pid in sorted(ids1 & ids2):
        a: ProductClassification = map1[pid]
        b: ProductClassification = map2[pid]
        if a.image_state != b.image_state:
            drift.append(
                {
                    "product_id": pid,
                    "run1_state": a.image_state,
                    "run2_state": b.image_state,
                    "run1_thumbnail": a.primary_image_reference or "",
                    "run2_thumbnail": b.primary_image_reference or "",
                    "change_reason": "state_changed",
                }
            )
        elif (a.primary_image_reference or "") != (b.primary_image_reference or ""):
            # Reported for operators; does not fail semantic state stability.
            drift.append(
                {
                    "product_id": pid,
                    "run1_state": a.image_state,
                    "run2_state": b.image_state,
                    "run1_thumbnail": a.primary_image_reference or "",
                    "run2_thumbnail": b.primary_image_reference or "",
                    "change_reason": "thumbnail_changed_same_state",
                }
            )

    blocking = [
        d
        for d in drift
        if d["change_reason"]
        in {"missing_in_run1", "missing_in_run2", "state_changed"}
    ]
    stable = (
        len(blocking) == 0
        and ids1 == ids2
        and len(ids1) == run1.catalog_total
        and run1.catalog_total == run2.catalog_total
    )
    return stable, drift
