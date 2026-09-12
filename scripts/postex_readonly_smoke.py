#!/usr/bin/env python3
"""Read-only Postex smoke. Never creates/edits/cancels parcels or mutates wallet.

Requires:
  POSTEX_LIVE_READONLY_TESTS=1
  POSTEX_API_KEY from the environment (never printed)
"""

from __future__ import annotations

import asyncio
import os
import sys


def _die(message: str, code: int = 2) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


async def main() -> None:
    if os.environ.get("POSTEX_LIVE_READONLY_TESTS", "").strip() != "1":
        _die("Refusing to run: set POSTEX_LIVE_READONLY_TESTS=1")
    key = os.environ.get("POSTEX_API_KEY", "").strip()
    if not key:
        _die("POSTEX_API_KEY is required")

    # Import after opt-in so a missing app env does not run accidentally.
    from app.core.config import settings
    from app.services.logistics.postex.client import PostexClient

    client = PostexClient(
        base_url=settings.POSTEX_BASE_URL,
        api_key=key,
        timeout_seconds=settings.POSTEX_TIMEOUT_SECONDS,
    )
    print("whoami…")
    await client.whoami()
    print("ok")
    print("cities…")
    await client.get_json("/locality/cities/all", operation="cities_all")
    print("ok")
    print("shipping-methods…")
    await client.get_json("/shipping-methods", operation="shipping_methods")
    print("ok")
    print("boxes…")
    await client.get_json("/common/boxes", operation="boxes")
    print("ok")
    print("quotes are non-mutating per official summary; skipping unless origin+dest env set.")
    from_city = os.environ.get("POSTEX_ORIGIN_CITY_CODE")
    to_city = os.environ.get("POSTEX_SMOKE_TO_CITY_CODE")
    if from_city and to_city:
        print("quote…")
        await client.post_json(
            "/shipping/quotes",
            {
                "collection_type": settings.POSTEX_COLLECTION_TYPE,
                "from_city_code": int(from_city),
                "parcels": [
                    {
                        "to_city_code": int(to_city),
                        "payment_type": "SENDER",
                        "parcel_properties": {
                            "length": 20,
                            "width": 15,
                            "height": 10,
                            "total_weight": 500,
                            "box_type_id": int(os.environ.get("POSTEX_SMOKE_BOX_TYPE_ID", "1")),
                            "total_value": 100000,
                            "total_value_currency": "IRR",
                        },
                    }
                ],
            },
            operation="quotes",
            mutating=False,
        )
        print("ok")
    print("read-only smoke complete (no mutating calls).")


if __name__ == "__main__":
    asyncio.run(main())
