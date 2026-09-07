"""READ-ONLY Target Catalog reconciliation (no production mutation)."""

from .core import (  # noqa: F401
    STATES,
    canonicalize_brand,
    convert_price,
    normalize_sku,
    suffix_near_miss,
)
