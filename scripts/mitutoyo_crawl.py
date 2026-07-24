#!/usr/bin/env python3
"""Crawl Mitutoyo Iran products via WooCommerce Store API (no images, no marketing copy).

Outputs JSONL ready for Karzar import:
  name, sku, base_price, category_hint, specifications

Usage:
  python scripts/mitutoyo_crawl.py --out data/mitutoyo_crawl.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://www.mitutoyoiran.com"
STORE = f"{BASE}/wp-json/wc/store/v1/products"
UA = "Mozilla/5.0 (compatible; KarzarCatalogImporter/1.0; +https://www.karzartools.com)"

# Map source category slug/name keywords → Karzar leaf category id (اندازه گیری دقیق subtree)
CATEGORY_MAP: list[tuple[tuple[str, ...], int]] = [
    (("digital-caliper", "vernier-caliper", "dial-caliper", "کولیس"), 57),  # انواع کولیس
    (("micrometer", "میکرومتر", "میکرومتر"), 58),  # انواع میکرومتر
    (("dial-indicator-accessories", "indicator-accessories"), 80),  # قطعات یدکی
    (("dial-indicator", "ساعت-اندیکاتور", "اندیکاتور"), 59),  # ساعت اندیکاتور
    (("dial-test", "test-indicator", "شیطانک", "شیطونک"), 60),  # ساعت شیطانکی
    (("depth", "عمق"), 62),  # عمق سنج
    (("bore", "cylinder", "بورگیج", "سیلندر"), 63),  # گیج داخل سیلندر
    (("height", "ارتفاع", "کولیس-پایه"), 69),  # ارتفاع سنج
    (("angle", "زاویه"), 68),  # زاویه سنج
    (("gage-block", "gauge-block", "راپورتر", "بلوک"), 66),  # راپورتر
    (("filler", "thickness", "فیلر", "ضخامت", "شابلون"), 73),  # فیلر (شابلون نزدیک)
    (("radius", "شعاع"), 70),  # شعاع سنج
    (("stand", "holder", "پایه-ساعت", "پایه-میکرو"), 64),  # پایه ساعت (fallback)
    (("level", "تراز"), 71),  # تراز صنعتی
    (("square", "گونیا"), 75),
    (("scale", "خط-کش", "متر"), 76),
]

DEFAULT_CATEGORY_ID = 56  # اندازه گیری دقیق (parent) — better than wrong leaf; prefer leaf when mapped


def fetch(url: str, *, retries: int = 5, timeout: int = 90) -> tuple[dict[str, str], bytes]:
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": UA,
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                headers = {k.lower(): v for k, v in resp.headers.items()}
                return headers, resp.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            wait = min(30, 2**attempt)
            print(f"  retry {attempt}/{retries} after {wait}s: {exc}")
            time.sleep(wait)
    raise RuntimeError(f"Failed {url}: {last}")


def map_category(categories: list[dict]) -> tuple[int, str]:
    names = " ".join(
        f"{c.get('slug') or ''} {c.get('name') or ''}" for c in categories
    ).lower()
    for keys, cat_id in CATEGORY_MAP:
        if any(k.lower() in names for k in keys):
            return cat_id, keys[0]
    return DEFAULT_CATEGORY_ID, "fallback-اندازه-گیری-دقیق"


def extract_specs(attrs: list[dict]) -> dict:
    specs: dict[str, str] = {}
    for attr in attrs or []:
        name = (attr.get("name") or "").strip()
        if not name:
            continue
        # Skip marketing-ish fields if any; keep technical attributes only
        terms = attr.get("terms") or []
        values = [str(t.get("name") or "").strip() for t in terms if t.get("name")]
        if not values:
            continue
        specs[name] = "، ".join(values)
    return specs


def normalize_sku(sku: str | None, name: str) -> str | None:
    sku = (sku or "").strip()
    if sku:
        return sku[:50]
    # Fallback: model code in name like 505-742J / 06AFM380 / 938882
    m = re.search(r"([0-9]{2,}[A-Za-z0-9\-]{0,20})", name)
    if m:
        return m.group(1)[:50]
    return None


def parse_price(prices: dict | None) -> int | None:
    if not prices:
        return None
    raw = prices.get("price") or prices.get("regular_price") or ""
    if raw in ("", "0", None):
        return None
    try:
        return int(str(raw).replace(",", "").strip())
    except ValueError:
        return None


def crawl(out_path: Path, *, per_page: int = 50, sleep_s: float = 1.2) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    page = 1
    total_pages = None
    written = 0
    skipped = 0

    with out_path.open("w", encoding="utf-8") as fh:
        while True:
            url = f"{STORE}?per_page={per_page}&page={page}&orderby=id&order=asc"
            print(f"[crawl] page {page} …")
            headers, body = fetch(url)
            if total_pages is None:
                total_pages = int(headers.get("x-wp-totalpages") or "1")
                total = int(headers.get("x-wp-total") or "0")
                print(f"[crawl] total_products≈{total} total_pages={total_pages}")
            data = json.loads(body.decode("utf-8"))
            if not isinstance(data, list) or not data:
                print("[crawl] empty page — stop")
                break
            for item in data:
                name = (item.get("name") or "").strip()
                # Prefer Mitutoyo brand products; Store API may expose brands differently
                brands = item.get("brands") or []
                brand_text = " ".join(
                    f"{b.get('slug','')} {b.get('name','')}" for b in brands
                ).lower()
                class_list = " ".join(item.get("categories", []) and [])  # unused
                # Filter: name/brand contains mitutoyo OR sku present with Japanese brand attrs
                attrs = item.get("attributes") or []
                specs = extract_specs(attrs)
                made = (specs.get("ساخت") or "").lower()
                is_mitu = (
                    "mitutoyo" in brand_text
                    or "میتوتویو" in brand_text
                    or "میتوتویو" in name
                    or "mitutoyo" in name.lower()
                    or "ژاپن" in made
                )
                # Site is Mitutoyo specialty shop — keep all published catalog items
                is_mitu = True

                sku = normalize_sku(item.get("sku"), name)
                if not sku or not name:
                    skipped += 1
                    continue
                price = parse_price(item.get("prices"))
                cat_id, cat_hint = map_category(item.get("categories") or [])
                # Specs only — no description/content/images
                specs_out = {
                    k: v
                    for k, v in specs.items()
                    if k
                    not in {
                        # keep گارانتی/ساخت/کد فنی as product specs (not marketing paragraphs)
                    }
                }
                row = {
                    "source_id": item.get("id"),
                    "source_url": item.get("permalink") or item.get("url"),
                    "name": name,
                    "sku": sku,
                    "base_price": price,  # toman integer or null
                    "karzar_category_id": cat_id,
                    "category_map_hint": cat_hint,
                    "source_categories": [
                        {"id": c.get("id"), "name": c.get("name"), "slug": c.get("slug")}
                        for c in (item.get("categories") or [])
                    ],
                    "specifications": specs_out,
                    "is_in_stock": bool(item.get("is_in_stock", True)),
                }
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                written += 1
            print(f"[crawl] page {page} done — written={written} skipped={skipped}")
            if page >= (total_pages or page):
                break
            page += 1
            time.sleep(sleep_s)

    print(f"[crawl] FINISHED written={written} skipped={skipped} → {out_path}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/mitutoyo_crawl.jsonl")
    ap.add_argument("--per-page", type=int, default=50)
    ap.add_argument("--sleep", type=float, default=1.2)
    args = ap.parse_args()
    crawl(Path(args.out), per_page=args.per_page, sleep_s=args.sleep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
