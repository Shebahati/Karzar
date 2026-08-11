"""Contracts for IMG-SHOPMILL-WATERMARK-CLEANUP."""

from __future__ import annotations

from dataclasses import dataclass

TASK_ID = "IMG-SHOPMILL-WATERMARK-CLEANUP"

# Storefront public list forces is_active=True for non-admin
# (app/api/endpoints/products_catalog.py). Soft-deleted products are excluded
# from normal catalog queries (app/crud/product.py). is_available is binary
# stock UX and does NOT hide a product from the catalog list by default.
ACTIVE_PUBLIC_SQL = (
    "product_is_active is true AND product_deleted is false"
)


@dataclass(frozen=True)
class ActivePublicSemantics:
    """Canonical active/public semantics used by this audit."""

    is_active: bool = True
    deleted: bool = False
    # Availability is recorded but not required for catalog visibility.
    require_available: bool = False


DEFAULT_INVENTORY_CSV = (
    "/var/tmp/karzar-image-audit/img02a01-20260803T121056Z/inventory.csv"
)
DEFAULT_HR_ASSET_REVIEWS = (
    "/var/tmp/karzar-image-review/human-review/img02a02-pilot-001/asset-review.csv",
    "/var/tmp/karzar-image-review/human-review/img02a02-batch-002/asset-review.csv",
    "/var/tmp/karzar-image-review/human-review/img02a02-remainder-all/asset-review.csv",
)
DEFAULT_PREVIEW_ROOTS = (
    "/var/tmp/karzar-image-review/prior-batches/img02a02-pilot-001/previews",
    "/var/tmp/karzar-image-review/prior-batches/img02a02-batch-002/previews",
    "/var/tmp/karzar-image-review/img02a02-remainder-all-pkg/previews",
)

HR_WATERMARK_POSITIVE = "distributor_or_retailer"
