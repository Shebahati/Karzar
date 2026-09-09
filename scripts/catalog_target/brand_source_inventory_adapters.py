"""Owner-confirmed brand/source inventory adapters (exceptions only).

Generic supplier-stock rule remains: price does NOT imply stock.
These adapters MUST NOT be applied to other brands or other price lists.

Provenance: Owner business-semantics correction 2026-09-09.
See docs/catalog/SUPPLIER_STOCK_AUTHORITY.md §10.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

ADAPTERS_VERSION = "brand_source_inventory_adapters/1.0.0"


@dataclass(frozen=True)
class BrandSourceInventoryAdapter:
    adapter_id: str
    brand: str
    source_path: str
    rule: str
    provenance: str
    unresolved_exclusions: tuple[str, ...] = ()


# Exact source paths Owner authorized as operational supplier inventory lists.
DASQUA_GOOGLE_DRIVE_INVENTORY_LIST = BrandSourceInventoryAdapter(
    adapter_id="DASQUA_GOOGLE_DRIVE_INVENTORY_LIST",
    brand="DASQUA",
    source_path=(
        "/home/shebahati/KaZar/Product and Data Complete/"
        "اندازه گیری/داسکوا/لیست قیمت داسکوا +10 درصد.pdf"
    ),
    rule=(
        "valid positive supplier price row = AVAILABLE; "
        "zero / blank / invalid price = NOT AVAILABLE FOR ACTIVATION"
    ),
    provenance="Owner correction 2026-09-09; not inferred from a PDF stock column",
)

TERMA_GOOGLE_DRIVE_INVENTORY_LIST = BrandSourceInventoryAdapter(
    adapter_id="TERMA_GOOGLE_DRIVE_INVENTORY_LIST",
    brand="TERMA",
    source_path=(
        "/home/shebahati/KaZar/Product and Data Complete/"
        "اندازه گیری/ترما/لیست قیمت ترما +25درصد.pdf"
    ),
    rule=(
        "valid positive supplier price row = AVAILABLE; "
        "zero / blank / invalid / unresolved = NOT AVAILABLE FOR ACTIVATION"
    ),
    provenance="Owner correction 2026-09-09; not inferred from a PDF stock column",
    unresolved_exclusions=("CDA100-300", "MA250H-200", "MD710-25"),
)

ADAPTERS_BY_ID: Mapping[str, BrandSourceInventoryAdapter] = {
    DASQUA_GOOGLE_DRIVE_INVENTORY_LIST.adapter_id: DASQUA_GOOGLE_DRIVE_INVENTORY_LIST,
    TERMA_GOOGLE_DRIVE_INVENTORY_LIST.adapter_id: TERMA_GOOGLE_DRIVE_INVENTORY_LIST,
}


def inventory_status_from_positive_price(
    *,
    adapter_id: str,
    source_path: str,
    sku: str,
    price: float | None,
) -> str:
    """Return AVAILABLE / UNAVAILABLE for an authorized adapter only.

    Raises ValueError if adapter_id/source_path do not match an Owner adapter.
    Does not repair unresolved TERMA exceptions via inventory semantics.
    """
    adapter = ADAPTERS_BY_ID.get(adapter_id)
    if adapter is None:
        raise ValueError(f"unknown_inventory_adapter:{adapter_id}")
    if source_path != adapter.source_path:
        raise ValueError(
            f"source_path_mismatch_for_adapter:{adapter_id}"
        )
    if sku in adapter.unresolved_exclusions:
        return "UNAVAILABLE"
    if price is None:
        return "UNAVAILABLE"
    try:
        value = float(price)
    except (TypeError, ValueError):
        return "UNAVAILABLE"
    if value > 0:
        return "AVAILABLE"
    return "UNAVAILABLE"
