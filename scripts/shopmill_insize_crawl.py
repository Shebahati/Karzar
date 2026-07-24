#!/usr/bin/env python3
"""Crawl INSIZE products from shopmilltools.com and sync into Karzar.

- Names: exact shopmilltools product name
- SKUs: normalized to official INSIZE order (series-size), e.g. 200-1108 → 1108-200
- Only products whose name/slug clearly indicate INSIZE

Usage:
  python scripts/shopmill_insize_crawl.py --out data/shopmill_insize.jsonl
  python scripts/shopmill_insize_sync.py --jsonl data/shopmill_insize.jsonl --dry-run
  python scripts/shopmill_insize_sync.py --jsonl data/shopmill_insize.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://shopmilltools.com"
STORE = f"{BASE}/wp-json/wc/store/v1/products"
UA = "Mozilla/5.0 (compatible; KarzarCatalogImporter/1.0; +https://www.karzartools.com)"


def fetch(url: str, *, retries: int = 5, timeout: int = 90):
    last = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept": "application/json"}
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


def is_insize(name: str, slug: str) -> bool:
    blob = f"{name} {slug}".lower()
    return "insize" in blob or "اینسایز" in name


def extract_model_code(name: str) -> str | None:
    name = (name or "").replace("&#8211;", "–").replace("&#215;", "×").replace("&amp;", "&")
    for pat in [
        r"مدل\s*\(?\s*Insize\)?\s*([0-9A-Za-z][0-9A-Za-z\-./]*)",
        r"مدل\s*([0-9A-Za-z][0-9A-Za-z\-./]*)",
        r"کدل\s*([0-9A-Za-z][0-9A-Za-z\-./]*)",
        r"کد\s*([0-9A-Za-z][0-9A-Za-z\-./]*)",
        r"سری\s*(?:استاندارد\s*)?\(?\s*([0-9]{3,5}[A-Za-z0-9\-]*)\s*\)?",
    ]:
        m = re.search(pat, name, flags=re.I)
        if m:
            return m.group(1).strip().rstrip(").,]»\"'")
    return None

def to_official_sku(model: str | None) -> str | None:
    """Normalize shopmill 'مدل' code to official INSIZE SKU order.

    Shopmill often writes size-series (200-1108); official is series-size (1108-200).
    """
    if not model:
        return None
    code = model.strip().upper().replace(" ", "").replace("/", "-")
    code = code.replace("ـ", "-")
    # 1181-M25 / HDT-LP200 style — keep
    if re.match(r"^[A-Z]{2,}[A-Z0-9\-]*$", code):
        return code[:50]
    # N-N or N-N+letters
    m = re.match(r"^(\d+)([A-Z]*)-(\d+)([A-Z]*)$", code)
    if m:
        a, a_suf, b, b_suf = m.groups()
        # If second number is 4-digit series (typical INSIZE family) → reverse
        if len(b) == 4 and len(a) <= 4 and not b_suf:
            sku = f"{b}-{a}{a_suf}"
            return sku[:50]
        # already series-size (first is 4-digit)
        if len(a) == 4:
            return code[:50]
        # ambiguous: keep as-is
        return code[:50]
    # plain digits
    if re.match(r"^\d{3,6}[A-Z]*$", code):
        return code[:50]
    return code[:50] if code else None


def extract_specs(attrs: list) -> dict[str, str]:
    skip = {"گارانتی"}  # marketing-heavy; keep technical only
    specs: dict[str, str] = {}
    for attr in attrs or []:
        name = (attr.get("name") or "").strip()
        if not name or name in skip:
            continue
        terms = attr.get("terms") or []
        values = [str(t.get("name") or "").strip() for t in terms if t.get("name")]
        if values:
            specs[name] = "، ".join(values)
    return specs


def crawl(out_path: Path, *, per_page: int = 50, sleep_s: float = 0.7) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    page = 1
    written = 0
    skipped = 0
    total_pages = None

    with out_path.open("w", encoding="utf-8") as fh:
        while True:
            q = urllib.parse.urlencode(
                {
                    "per_page": per_page,
                    "page": page,
                    "search": "insize",
                    "orderby": "id",
                    "order": "asc",
                }
            )
            url = f"{STORE}?{q}"
            print(f"[crawl] page {page} …")
            headers, body = fetch(url)
            if total_pages is None:
                total_pages = int(headers.get("x-wp-totalpages") or "1")
                total = int(headers.get("x-wp-total") or "0")
                print(f"[crawl] search_hits≈{total} pages={total_pages}")
            data = json.loads(body.decode("utf-8"))
            if not data:
                break
            for item in data:
                name = (item.get("name") or "").strip()
                slug = item.get("slug") or ""
                if not is_insize(name, slug):
                    skipped += 1
                    continue
                # Exact shopmill name (decode common HTML entities only)
                name_exact = (
                    name.replace("&#8211;", "–")
                    .replace("&#8211", "–")
                    .replace("&amp;", "&")
                    .replace("&nbsp;", " ")
                )
                model = extract_model_code(name_exact)
                sku = to_official_sku(model)
                row = {
                    "source_id": item.get("id"),
                    "source_url": item.get("permalink"),
                    "name": name_exact[:255],
                    "model_raw": model,
                    "sku": sku,
                    "slug": slug,
                    "source_categories": [
                        {
                            "id": c.get("id"),
                            "name": c.get("name"),
                            "slug": c.get("slug"),
                        }
                        for c in (item.get("categories") or [])
                    ],
                    "specifications": extract_specs(item.get("attributes") or []),
                    "prices": item.get("prices"),
                }
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                written += 1
            print(f"[crawl] page {page} written={written} skipped_non_insize={skipped}")
            if page >= (total_pages or page):
                break
            page += 1
            time.sleep(sleep_s)

    print(f"[crawl] DONE written={written} → {out_path}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/shopmill_insize.jsonl")
    ap.add_argument("--per-page", type=int, default=50)
    ap.add_argument("--sleep", type=float, default=0.7)
    args = ap.parse_args()
    crawl(Path(args.out), per_page=args.per_page, sleep_s=args.sleep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
