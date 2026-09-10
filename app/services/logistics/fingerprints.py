"""Cart and destination fingerprints for quote binding."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence


def merge_line_quantities(items: Sequence[Mapping[str, int]]) -> dict[int, int]:
    """Sum quantities for the same product_id. Quote and checkout must share this."""
    merged: dict[int, int] = {}
    for item in items:
        product_id = int(item["product_id"])
        quantity = int(item["quantity"])
        merged[product_id] = merged.get(product_id, 0) + quantity
    return merged


def canonical_cart_items(items: Sequence[Mapping[str, int]]) -> list[dict[str, int]]:
    merged = merge_line_quantities(items)
    return [
        {"product_id": product_id, "quantity": quantity}
        for product_id, quantity in sorted(merged.items())
    ]


def cart_fingerprint(items: Sequence[Mapping[str, int]]) -> str:
    normalized = canonical_cart_items(items)
    payload = json.dumps(normalized, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def destination_fingerprint(*, location_code: int, postal_code: str | None = None) -> str:
    payload = json.dumps(
        {
            "location_code": int(location_code),
            "postal_code": (postal_code or "").strip(),
        },
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
