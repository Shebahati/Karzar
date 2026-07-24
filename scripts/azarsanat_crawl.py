#!/usr/bin/env python3
"""Crawl azarsanat.net products via WooCommerce Store API.

Outputs JSONL with catalog fields only (no images, no marketing HTML).

Usage:
  python scripts/azarsanat_crawl.py --out data/azarsanat_crawl.jsonl
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

BASE = "https://azarsanat.net"
STORE = f"{BASE}/wp-json/wc/store/v1/products"
UA = "Mozilla/5.0 (compatible; KarzarCatalogImporter/1.0; +https://www.karzartools.com)"


def fetch(url: str, *, retries: int = 5, timeout: int = 90) -> tuple[dict[str, str], bytes]:
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": UA, "Accept": "application/json"},
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


def extract_specs(attrs: list[dict]) -> dict[str, str]:
    specs: dict[str, str] = {}
    for attr in attrs or []:
        name = (attr.get("name") or "").strip()
        if not name:
            continue
        terms = attr.get("terms") or []
        values = [str(t.get("name") or "").strip() for t in terms if t.get("name")]
        if values:
            specs[name] = "، ".join(values)
    return specs


def crawl(out_path: Path, *, per_page: int = 100, sleep_s: float = 0.8) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    page = 1
    total_pages = None
    written = 0

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
                if not name:
                    continue
                brands = item.get("brands") or []
                sku = (item.get("sku") or "").strip() or None
                row = {
                    "source_id": item.get("id"),
                    "source_url": item.get("permalink") or item.get("url"),
                    "name": name,
                    "sku": sku,
                    "prices": item.get("prices"),
                    "source_brands": [
                        {
                            "id": b.get("id"),
                            "name": b.get("name"),
                            "slug": b.get("slug"),
                        }
                        for b in brands
                    ],
                    "source_categories": [
                        {
                            "id": c.get("id"),
                            "name": c.get("name"),
                            "slug": c.get("slug"),
                        }
                        for c in (item.get("categories") or [])
                    ],
                    "specifications": extract_specs(item.get("attributes") or []),
                    "is_in_stock": bool(item.get("is_in_stock", True)),
                }
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                written += 1
            print(f"[crawl] page {page} done — written={written}")
            if page >= (total_pages or page):
                break
            page += 1
            time.sleep(sleep_s)

    print(f"[crawl] FINISHED written={written} → {out_path}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/azarsanat_crawl.jsonl")
    ap.add_argument("--per-page", type=int, default=100)
    ap.add_argument("--sleep", type=float, default=0.8)
    args = ap.parse_args()
    crawl(Path(args.out), per_page=args.per_page, sleep_s=args.sleep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
