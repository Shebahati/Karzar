"""Canonical Hesabfa item activation policy.

The website publication lifecycle and Hesabfa accounting item lifecycle are
intentionally independent. Storefront ``is_active`` / ``is_available`` and
commercial fields (price, stock) must not turn an accounting item off.
"""

from __future__ import annotations

# Accounting master-item lifecycle for every non-deleted Karzar catalog product.
# This constant is the single switch for Hesabfa ``active`` on item shells.
HESABFA_ITEM_ACTIVE = True


def hesabfa_item_should_be_active(product: object | None = None) -> bool:
    """Return the Hesabfa ``active`` flag for a catalog item shell.

    The website publication lifecycle and Hesabfa accounting item lifecycle
    are intentionally independent. ``product`` is accepted so call sites name
    the catalog row under consideration; ``is_active``, ``is_available``,
    ``base_price``, and ``stock_quantity`` are deliberately not read.
    """
    del product
    return HESABFA_ITEM_ACTIVE
