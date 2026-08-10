"""IMG-FAST-01A — live storefront Fast Coverage catalog baseline (read-only)."""

from __future__ import annotations

__all__ = [
    "STATES",
    "IMAGE_STATES",
]

STATES = IMAGE_STATES = (
    "usable_primary",
    "promotable_existing_image",
    "missing_all_images",
    "broken_only",
    "known_placeholder_only",
    "ambiguous_current_state",
)
