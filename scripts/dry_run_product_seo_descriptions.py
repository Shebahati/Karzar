#!/usr/bin/env python3
"""Dry-run report for product SEO description coverage (P1 skeleton).

Default: READ-ONLY against staging API. Never writes product fields.

Examples:
  # Staging dry-run (default API base)
  python scripts/dry_run_product_seo_descriptions.py --brand INSIZE

  # Local / custom
  KARZAR_API_BASE=https://api.karzartools.com/api/v1 \\
    python scripts/dry_run_product_seo_descriptions.py --limit 200 --json out/seo-dryrun.json

Do NOT pass --apply (reserved; currently rejected). Bulk apply is P2+ after review.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

# Allow `python scripts/...` without installing the package.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.utils.seo_descriptions import (  # noqa: E402
    is_stub_description,
    render_short_description_template,
)

API = os.getenv("KARZAR_API_BASE", "https://api.karzartools.com/api/v1")
UA = "KarzarSeoDescriptionDryRun/0.1"


def _get(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 — operator-controlled URL
        return json.loads(resp.read().decode("utf-8"))


def _list_products(*, brand: str | None, search: str | None, limit: int, skip: int) -> dict:
    params: dict[str, str] = {"limit": str(min(limit, 100)), "skip": str(skip)}
    if search:
        params["search"] = search
    # Public list may not filter by brand name; callers can pass search=brand.
    if brand and not search:
        params["search"] = brand
    query = urllib.parse.urlencode(params)
    return _get(f"{API.rstrip('/')}/products/?{query}")  # type: ignore[return-value]


def _classify_row(row: dict) -> str:
    short = row.get("short_description")
    long = row.get("description")
    name = row.get("name") or ""
    if short and not is_stub_description(short, product_name=name):
        return "short_ok"
    if short and is_stub_description(short, product_name=name):
        return "short_stub"
    if long and not is_stub_description(long, product_name=name):
        return "long_only"
    if long and is_stub_description(long, product_name=name):
        return "long_stub"
    return "empty"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brand", help="Brand name hint (uses search=)")
    parser.add_argument("--search", help="PLP search string")
    parser.add_argument("--limit", type=int, default=100, help="Max products to sample")
    parser.add_argument("--json", dest="json_out", help="Write full report JSON path")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="RESERVED — rejected. P2 bulk apply is out of scope for this skeleton.",
    )
    args = parser.parse_args()

    if args.apply:
        print("ERROR: --apply is not implemented. Run dry-run only; P2 needs human review.", file=sys.stderr)
        return 2

    print(f"API base: {API}")
    print("Mode: dry-run (read-only)")

    collected: list[dict] = []
    skip = 0
    remaining = args.limit
    while remaining > 0:
        batch_limit = min(100, remaining)
        try:
            page = _list_products(
                brand=args.brand,
                search=args.search,
                limit=batch_limit,
                skip=skip,
            )
        except urllib.error.HTTPError as exc:
            print(f"HTTP {exc.code}: {exc.reason}", file=sys.stderr)
            return 1
        except urllib.error.URLError as exc:
            print(f"URL error: {exc}", file=sys.stderr)
            return 1

        rows = page.get("data") if isinstance(page, dict) else page
        if not isinstance(rows, list) or not rows:
            break
        collected.extend(rows)
        skip += len(rows)
        remaining -= len(rows)
        meta = page.get("meta") if isinstance(page, dict) else {}
        total = int((meta or {}).get("total_count") or 0)
        if skip >= total or len(rows) < batch_limit:
            break

    counts: Counter[str] = Counter()
    samples: dict[str, list[dict]] = {k: [] for k in ("empty", "short_stub", "long_stub", "long_only", "short_ok")}
    template_previews: list[dict] = []

    for row in collected:
        # List payload may omit long description; mark unknown when absent.
        cls = _classify_row(row)
        if "description" not in row and "short_description" not in row:
            cls = "unknown_shape"
        counts[cls] += 1
        bucket = samples.setdefault(cls, [])
        if len(bucket) < 5:
            bucket.append(
                {
                    "id": row.get("id"),
                    "sku": row.get("sku"),
                    "name": row.get("name"),
                    "slug": row.get("slug"),
                    "short_description": row.get("short_description"),
                }
            )

        preview = render_short_description_template(
            name=str(row.get("name") or ""),
            brand_name=(row.get("brand") or {}).get("name") if isinstance(row.get("brand"), dict) else None,
            category_name=(row.get("category") or {}).get("name")
            if isinstance(row.get("category"), dict)
            else None,
            sku=row.get("sku"),
        )
        if preview and len(template_previews) < 10:
            template_previews.append({"id": row.get("id"), "sku": row.get("sku"), "preview": preview})

    report = {
        "api": API,
        "sampled": len(collected),
        "counts": dict(counts),
        "rates": {
            k: (round(v / len(collected), 4) if collected else 0.0) for k, v in counts.items()
        },
        "samples": samples,
        "template_previews": template_previews,
        "notes": [
            "Public list may omit description; use admin detail export for exact long-body rates.",
            "Stub rule: len<40 or ≈product name (see app.utils.seo_descriptions.is_stub_description).",
            "P2 brand order: INSIZE → Mitutoyo → Dasqua (rewrite stubs) → ASIMETO.",
            "Apply only on staging after reviewing this report; never commit secrets.",
        ],
    }

    print(json.dumps({"sampled": report["sampled"], "counts": report["counts"], "rates": report["rates"]}, ensure_ascii=False, indent=2))
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
