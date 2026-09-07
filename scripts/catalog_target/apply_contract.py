"""Future APPLY contract (READ-ONLY design). No writer is implemented here.

Any future production mutation PR must implement this guard before writing.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


APPLY_REQUIRED_LIVE_FIELDS = (
    "id",
    "sku",
    "base_price",
    "is_active",
    "is_available",
)


@dataclass(frozen=True)
class StaleSnapshotGuard:
    """Abort-before-mutation contract for a future APPLY PR.

    Before any production write, re-read each allowlisted row live and compare
    against the reviewed snapshot values. If any field differs, abort the entire
    APPLY. No partial blind apply.
    """

    name: str = "stale_snapshot_preflight"
    mode: str = "abort_entire_apply_on_any_drift"
    required_live_fields: tuple[str, ...] = APPLY_REQUIRED_LIVE_FIELDS
    compare_against: str = "reviewed_snapshot_row"
    on_mismatch: str = "ABORT_BEFORE_MUTATION"
    partial_apply_allowed: bool = False
    writer_implemented: bool = False
    notes: tuple[str, ...] = (
        "Re-SELECT targeted production rows immediately before mutation.",
        "Compare id, sku, base_price, is_active, is_available to the reviewed plan.",
        "Also refuse if snapshot checksum/timestamp no longer matches operator-approved evidence.",
        "REVIEW / CREATE / DEACTIVATE are out of scope for INSIZE Sales Wave 1.",
    )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["required_live_fields"] = list(self.required_live_fields)
        payload["notes"] = list(self.notes)
        return payload


@dataclass
class FutureApplyReadiness:
    insize_sales_wave_1_ready: bool = False
    create_apply_ready: bool = False
    deactivate_apply_ready: bool = False
    global_apply_ready: bool = False
    stale_snapshot_guard: dict[str, Any] = field(default_factory=lambda: StaleSnapshotGuard().as_dict())
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "INSIZE_SALES_WAVE_1_READY": self.insize_sales_wave_1_ready,
            "CREATE_APPLY_READY": self.create_apply_ready,
            "DEACTIVATE_APPLY_READY": self.deactivate_apply_ready,
            "GLOBAL_APPLY_READY": self.global_apply_ready,
            "stale_snapshot_guard": self.stale_snapshot_guard,
            "reasons": self.reasons,
        }
