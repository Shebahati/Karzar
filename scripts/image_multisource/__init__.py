"""IMG-02C multisource image discovery (external outputs only; no DB)."""

from __future__ import annotations

TASK_ID = "IMG-02C"
NODE_ID = "IMG-02C-01-MULTISOURCE-BATCH-001"
BATCH_ID = "IMG-02C-01-BATCH-001"

SOURCE_CLASS_ORDER = ("S1", "S2", "S3", "S4", "S5")

AUTHORIZATION_STATES = frozenset(
    {
        "official",
        "authorized_confirmed",
        "authorized_candidate",
        "specialist_retailer",
        "iranian_supplier",
        "unknown",
    }
)

AUTOMATIC_MATCH_BASES = frozenset(
    {
        "exact_sku_product_page",
        "exact_model_product_page",
        "exact_sku_official_catalog",
        "exact_model_official_catalog",
        "exact_sku_authorized_distributor",
    }
)

RETAILER_SOURCE_CLASSES = frozenset({"S4", "S5"})


class MultisourceError(Exception):
    def __init__(self, stage: str, message: str) -> None:
        self.stage = stage
        self.message = message
        super().__init__(f"{stage}: {message}")
