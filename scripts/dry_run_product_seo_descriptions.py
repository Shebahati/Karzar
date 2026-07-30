#!/usr/bin/env python3
"""Dry-run report for product SEO description coverage (P1).

Default: READ-ONLY against staging API. Never writes product fields.

Examples:
  # Staging dry-run by brand name (resolves brand_id when possible)
  python scripts/dry_run_product_seo_descriptions.py --brand INSIZE --limit 500

  # Exact brand filter
  python scripts/dry_run_product_seo_descriptions.py --brand-id 3 --limit 500 \\
    --json out/seo-insize.json --hydrate-detail 25

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
    template_apply_ready,
)

_scripts_dir = Path(__file__).resolve().parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))
from ingestion_boundary import resolve_api_base  # noqa: E402

API = resolve_api_base()
UA = "KarzarSeoDescriptionDryRun/0.2"

# Locked P2 brand order → known staging brand IDs (fallback if brands list is slow).
_BRAND_ID_HINTS: dict[str, int] = {
    "INSIZE": 3,
    "Mitutoyo": 2,
    "Dasqua": 4,
    "ASIMETO": 6,
}


def _get(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 — operator-controlled URL
        return json.loads(resp.read().decode("utf-8"))


def _resolve_brand_id(brand: str | None) -> int | None:
    if not brand:
        return None
    hint = _BRAND_ID_HINTS.get(brand) or _BRAND_ID_HINTS.get(brand.strip())
    # Prefer exact known mapping for the locked P2 brands.
    for key, bid in _BRAND_ID_HINTS.items():
        if brand.casefold() == key.casefold() or brand.casefold() in key.casefold():
            return bid
    if hint:
        return hint
    try:
        page = _get(f"{API.rstrip('/')}/brands/?limit=100")
    except (urllib.error.HTTPError, urllib.error.URLError):
        return None
    rows = page.get("data") if isinstance(page, dict) else page
    if not isinstance(rows, list):
        return None
    needle = brand.casefold()
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "")
        if needle in name.casefold():
            try:
                return int(row["id"])
            except (KeyError, TypeError, ValueError):
                continue
    return None


def _list_products(
    *,
    brand_id: int | None,
    brand: str | None,
    search: str | None,
    limit: int,
    skip: int,
) -> dict:
    params: dict[str, str] = {"limit": str(min(limit, 100)), "skip": str(skip)}
    if brand_id is not None:
        params["brand_id"] = str(brand_id)
    elif search:
        params["search"] = search
    elif brand:
        params["search"] = brand
    query = urllib.parse.urlencode(params)
    return _get(f"{API.rstrip('/')}/products/?{query}")  # type: ignore[return-value]


def _get_detail(product_id: int | str) -> dict | None:
    try:
        payload = _get(f"{API.rstrip('/')}/products/{product_id}")
    except (urllib.error.HTTPError, urllib.error.URLError):
        return None
    if isinstance(payload, dict) and "id" in payload:
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload["data"]
    return None


def _classify_row(row: dict) -> str:
    short = row.get("short_description")
    long = row.get("description")
    name = row.get("name") or ""
    if short and not is_stub_description(short, product_name=name):
        return "short_ok"
    if short and is_stub_description(short, product_name=name):
        return "short_stub"
    if "description" in row:
        if long and not is_stub_description(long, product_name=name):
            return "long_only"
        if long and is_stub_description(long, product_name=name):
            return "long_stub"
        return "empty"
    # List payload often omits long description — treat missing short as empty_short.
    if short is None and "short_description" in row:
        return "empty"
    if "short_description" not in row and "description" not in row:
        return "unknown_shape"
    return "empty"


def _row_context(row: dict) -> dict:
    specs = row.get("specifications") or row.get("technical_specs")
    return {
        "name": str(row.get("name") or ""),
        "brand_name": (row.get("brand") or {}).get("name") if isinstance(row.get("brand"), dict) else None,
        "category_name": (row.get("category") or {}).get("name")
        if isinstance(row.get("category"), dict)
        else None,
        "sku": row.get("sku"),
        "technical_specs": specs if isinstance(specs, (dict, list)) else None,
    }


def _template_for_row(row: dict) -> str | None:
    return render_short_description_template(**_row_context(row))


def _apply_ready_for_row(row: dict) -> bool:
    return template_apply_ready(**_row_context(row))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brand", help="Brand name hint (resolves to brand_id when possible)")
    parser.add_argument("--brand-id", type=int, help="Exact brand_id filter")
    parser.add_argument("--search", help="PLP search string")
    parser.add_argument("--limit", type=int, default=100, help="Max products to sample")
    parser.add_argument(
        "--hydrate-detail",
        type=int,
        default=20,
        help="Fetch N product details for long-body + spec-aware template samples (0=off)",
    )
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

    brand_id = args.brand_id
    if brand_id is None and args.brand:
        brand_id = _resolve_brand_id(args.brand)

    print(f"API base: {API}")
    print("Mode: dry-run (read-only)")
    if brand_id is not None:
        print(f"brand_id: {brand_id}" + (f" ({args.brand})" if args.brand else ""))
    elif args.brand:
        print(f"brand filter: search={args.brand!r} (brand_id unresolved)")

    collected: list[dict] = []
    skip = 0
    remaining = args.limit
    while remaining > 0:
        batch_limit = min(100, remaining)
        try:
            page = _list_products(
                brand_id=brand_id,
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
    samples: dict[str, list[dict]] = {
        k: [] for k in ("empty", "short_stub", "long_stub", "long_only", "short_ok", "unknown_shape")
    }
    template_previews: list[dict] = []
    template_ok = 0
    template_none = 0
    apply_ready = 0

    for row in collected:
        cls = _classify_row(row)
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

        preview = _template_for_row(row)
        if preview:
            template_ok += 1
            if _apply_ready_for_row(row):
                apply_ready += 1
            if len(template_previews) < 10:
                template_previews.append(
                    {"id": row.get("id"), "sku": row.get("sku"), "preview": preview, "source": "list"}
                )
        else:
            template_none += 1

    hydrate_samples: list[dict] = []
    hydrate_counts: Counter[str] = Counter()
    hydrate_apply_ready = 0
    if args.hydrate_detail > 0 and collected:
        for row in collected[: args.hydrate_detail]:
            detail = _get_detail(row.get("id"))
            if not detail:
                hydrate_counts["detail_error"] += 1
                continue
            cls = _classify_row(detail)
            hydrate_counts[cls] += 1
            preview = _template_for_row(detail)
            ready = bool(preview and _apply_ready_for_row(detail))
            if ready:
                hydrate_apply_ready += 1
            entry = {
                "id": detail.get("id"),
                "sku": detail.get("sku"),
                "name": detail.get("name"),
                "class": cls,
                "short_description": detail.get("short_description"),
                "description": (detail.get("description") or "")[:160] or None,
                "preview": preview,
                "apply_ready": ready,
            }
            if len(hydrate_samples) < 15:
                hydrate_samples.append(entry)
            if preview and len(template_previews) < 15:
                template_previews.append(
                    {
                        "id": detail.get("id"),
                        "sku": detail.get("sku"),
                        "preview": preview,
                        "apply_ready": ready,
                        "source": "detail",
                    }
                )

    n = len(collected) or 1
    report = {
        "api": API,
        "brand": args.brand,
        "brand_id": brand_id,
        "sampled": len(collected),
        "counts": dict(counts),
        "rates": {k: round(v / len(collected), 4) if collected else 0.0 for k, v in counts.items()},
        "template_coverage": {
            "renderable": template_ok,
            "none": template_none,
            "renderable_rate": round(template_ok / n, 4) if collected else 0.0,
            "apply_ready": apply_ready,
            "apply_ready_rate": round(apply_ready / n, 4) if collected else 0.0,
        },
        "hydrate_detail": {
            "requested": args.hydrate_detail,
            "counts": dict(hydrate_counts),
            "apply_ready": hydrate_apply_ready,
            "samples": hydrate_samples,
        },
        "samples": samples,
        "template_previews": template_previews,
        "notes": [
            "Public list includes short_description but usually omits long description.",
            "Use --hydrate-detail N to sample long-body stub rates + spec-aware templates.",
            "Stub rule: len<40 or ≈product name (see app.utils.seo_descriptions.is_stub_description).",
            "apply_ready requires at least one safe measurement SoT field (range/resolution/…).",
            "P2 brand order: INSIZE → Mitutoyo → Dasqua (rewrite stubs) → ASIMETO.",
            "Apply only on staging after reviewing this report; never commit secrets.",
            "Do not bulk-apply category+SKU-only blurbs — taxonomy leaves are often wrong for kits.",
        ],
    }

    print(
        json.dumps(
            {
                "sampled": report["sampled"],
                "brand_id": brand_id,
                "counts": report["counts"],
                "rates": report["rates"],
                "template_coverage": report["template_coverage"],
                "hydrate_counts": report["hydrate_detail"]["counts"],
                "hydrate_apply_ready": report["hydrate_detail"]["apply_ready"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
