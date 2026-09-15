"""Three-level readiness model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from zcc_ir_catalog.models import SourceProduct

from zcc_ir_phase2.category_plan import CategoryDecisionRow
from zcc_ir_phase2.reconcile import Phase2ReconcileRow


@dataclass
class ReadinessRow:
    source_url: str
    identity_readiness: str
    content_readiness: str
    commerce_readiness: str
    import_content_ready: bool
    blocking_flags: list[str]

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["blocking_flags"] = list(self.blocking_flags)
        return data


def build_readiness(
    products: list[SourceProduct],
    reconcile: list[Phase2ReconcileRow],
    categories: dict[str, CategoryDecisionRow],
) -> list[ReadinessRow]:
    by_url = {p.source_url: p for p in products}
    rows: list[ReadinessRow] = []
    for rec in reconcile:
        product = by_url[rec.source_url]
        flags = list(rec.blocking_flags)
        identity = "IDENTITY_HOLD" if rec.primary_state.startswith("HOLD_") else "IDENTITY_READY"
        if rec.primary_state in {"HOLD_IDENTITY_REVIEW", "HOLD_DUPLICATE", "HOLD_SOURCE_CONFLICT"}:
            identity = "IDENTITY_HOLD"
        cat = categories.get(rec.source_url)
        content = "CONTENT_HOLD"
        if cat and cat.decision == "MAPPED_EXISTING" and product.main_image_url:
            content = "CONTENT_READY"
        elif rec.primary_state in {"NOOP_EXISTING_EXACT", "UPDATE_CONTENT_CANDIDATE"}:
            content = "CONTENT_READY"
        if "missing_image" in product.parse_flags:
            content = "CONTENT_HOLD"
            flags.append("missing_image")
        commerce = "COMMERCE_NOT_AUTHORIZED"
        if rec.price_state == "PRICE_SOURCE_INVALID":
            commerce = "COMMERCE_INVALID"
        brand_ok = product.brand_normalized in {"ZCC.CT", "SAN OU"} or (
            product.brand_normalized == "STC" and False
        )
        import_ready = (
            identity == "IDENTITY_READY"
            and content == "CONTENT_READY"
            and brand_ok
            and cat is not None
            and cat.decision == "MAPPED_EXISTING"
            and rec.primary_state not in {"HOLD_DUPLICATE", "HOLD_SOURCE_CONFLICT"}
        )
        rows.append(
            ReadinessRow(
                source_url=rec.source_url,
                identity_readiness=identity,
                content_readiness=content,
                commerce_readiness=commerce,
                import_content_ready=import_ready,
                blocking_flags=flags,
            )
        )
    rows.sort(key=lambda r: r.source_url)
    return rows
