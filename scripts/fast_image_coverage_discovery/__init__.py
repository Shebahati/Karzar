"""IMG-FAST-01B — Catalog-wide one-image discovery (external outputs only)."""

from __future__ import annotations

TASK_ID = "IMG-FAST-01B"
SCHEMA_VERSION = "1.0.0"
ACCEPTED_SEED_ARTIFACT_SHA256 = (
    "abbed4a4890d136ee48f767cf5450c6389524042a22c0b9dd172c1a9d0995016"
)
BASELINE_SEED_TOTAL = 4708
ACCEPTED_CATALOG_TOTAL = 5901
ACCEPTED_USABLE_PRIMARY = 1193

FINAL_QUEUES = ("green_exact", "yellow_review", "unresolved")
LANE_ORDER = ("IR-1", "IR-2", "OFFICIAL", "DIST", "WIDE")

__all__ = [
    "TASK_ID",
    "SCHEMA_VERSION",
    "ACCEPTED_SEED_ARTIFACT_SHA256",
    "BASELINE_SEED_TOTAL",
    "FINAL_QUEUES",
    "LANE_ORDER",
]
