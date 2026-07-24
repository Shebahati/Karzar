#!/usr/bin/env python3
"""Discover mitutoyoiran.com product listing endpoints."""
from __future__ import annotations

import json
import re
import sys
import urllib.request

UA = "Mozilla/5.0 (compatible; KarzarCatalogImporter/1.0)"


def fetch(url: str, timeout: int = 45) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {url}: {exc}")
        return 0, b""


def main() -> int:
    code, body = fetch("https://www.mitutoyoiran.com/")
    print(f"home status={code} size={len(body)}")
    if not body:
        return 1
    html = body.decode("utf-8", errors="ignore")
    print("woocommerce", "woocommerce" in html.lower())
    cats = sorted(set(re.findall(r'href=["\']([^"\']*product-category[^"\']*)["\']', html)))
    print("cat_links", len(cats))
    for c in cats[:50]:
        print("CAT", c)
    prods = sorted(set(re.findall(r'href=["\']([^"\']*/product/[^"\']*)["\']', html)))
    print("home_products", len(prods))
    for p in prods[:10]:
        print("P", p)

    probes = [
        "https://www.mitutoyoiran.com/wp-json/wc/store/v1/products?per_page=2",
        "https://www.mitutoyoiran.com/wp-json/wp/v2/product?per_page=2",
        "https://www.mitutoyoiran.com/wp-json/wc/store/v1/products/categories?per_page=50",
        "https://www.mitutoyoiran.com/product-sitemap.xml",
        "https://www.mitutoyoiran.com/sitemap_index.xml",
        "https://www.mitutoyoiran.com/sitemap.xml",
    ]
    for url in probes:
        c, b = fetch(url, timeout=30)
        print(f"probe {c} {url} size={len(b)}")
        print(b[:220].decode("utf-8", errors="ignore").replace("\n", " "))
    Path = __import__("pathlib").Path
    Path("/tmp/mitu_home.html").write_bytes(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
