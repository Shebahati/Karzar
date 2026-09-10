"""Cart and destination fingerprints for quote binding."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence


def cart_fingerprint(items: Sequence[Mapping[str, int]]) -> str:
    normalized = sorted(
        (
            {
                "product_id": int(item["product_id"]),
                "quantity": int(item["quantity"]),
            }
            for item in items
        ),
        key=lambda row: row["product_id"],
    )
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
