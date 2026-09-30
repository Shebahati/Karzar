#!/usr/bin/env python3
"""Read-only public API / storefront / Emalls sample verify after INSIZE 10% discount APPLY."""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

API = "https://api.karzartools.com/api/v1"
SITE = "https://karzartools.com"
UA = "KarzarInsizeDiscount10Verify/1.0"


def get_json(url: str, timeout: int = 45):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw[:500]}
        return e.code, payload


def get_text(url: str, timeout: int = 45):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="ignore")


def digits_only(s: str) -> str:
    return re.sub(r"[^0-9]", "", s or "")


def expected_api_price(s: str) -> str:
    d = Decimal(s)
    text = format(d, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def load_manifest(out: Path):
    paths = sorted(out.glob("INSIZE_DISCOUNT_10_MANIFEST_*.json"))
    if not paths:
        raise SystemExit("manifest json missing")
    data = json.loads(paths[-1].read_text(encoding="utf-8"))
    return data["rows"]


def pick_samples(rows):
    priced = sorted(rows, key=lambda r: Decimal(r["pre_base_price"]))
    samples: list[dict] = []

    def add(label, row):
        if row is None:
            return
        pid = int(row["product_id"])
        if any(int(s["product_id"]) == pid for s in samples):
            return
        samples.append({"label": label, **row})

    add("lowest_price", priced[0] if priced else None)
    add("highest_price", priced[-1] if priced else None)
    add(
        "active_available",
        next((r for r in rows if r["is_active"] and r["is_available"]), None),
    )
    add(
        "active_unavailable",
        next((r for r in rows if r["is_active"] and not r["is_available"]), None),
    )
    add(
        "visible_imaged",
        next((r for r in rows if r["is_active"] and r.get("has_image")), None),
    )
    add(
        "previously_discounted",
        next((r for r in rows if r.get("pre_original_price") is not None), None),
    )
    mids = [r for r in rows if r["is_active"] and r["is_available"]]
    if len(mids) >= 3:
        mid_i = len(mids) // 2
        add("mid_range_1", mids[mid_i])
        add("mid_range_2", mids[max(0, mid_i - 5)])
        add("mid_range_3", mids[min(len(mids) - 1, mid_i + 5)])
    return samples


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: insize_discount_10_site_verify.py OUT_DIR", file=sys.stderr)
        return 2
    out = Path(sys.argv[1])
    rows = load_manifest(out)
    samples = pick_samples(rows)
    results = []

    deals_probe: dict = {"ok": False}
    status, brand_list = get_json(
        f"{API}/products/?brand_id=3&is_active=true&limit=100&sort=discount_desc"
    )
    deals_probe["brand_list_status"] = status
    if status == 200:
        items = brand_list.get("data") or []
        disc = [p for p in items if (p.get("discount_percent") or 0) > 0]
        deals_probe["ok"] = True
        deals_probe["sample_page_discounted"] = len(disc)
        deals_probe["sample_page_total"] = len(items)
        deals_probe["note"] = (
            "Home deals section filters discount_percent>0 client-side; "
            "INSIZE 10% products become eligible when publicly listed."
        )

    # Emalls feed probe for a few visible SKUs (first page + match by page_unique)
    emalls_index: dict[int, dict] = {}
    try:
        est, efeed = get_json(f"{API}/integrations/emalls/products?page=1&limit=50")
        if est == 200:
            for item in efeed.get("products") or efeed.get("data") or []:
                pid = item.get("page_unique") or item.get("id")
                if pid is not None:
                    emalls_index[int(pid)] = item
            deals_probe["emalls_page1_count"] = len(emalls_index)
    except Exception as exc:  # noqa: BLE001
        deals_probe["emalls_probe_error"] = str(exc)

    for s in samples:
        expected_base = expected_api_price(s["computed_post_base_price"])
        expected_orig = expected_api_price(s["computed_post_original_price"])
        pid = int(s["product_id"])
        slug = s.get("slug") or s["sku"]
        api_url = f"{API}/products/{pid}"
        st, payload = get_json(api_url)
        api = {
            "url": api_url,
            "status": st,
            "base_price": None,
            "original_price": None,
            "discount_percent": None,
            "base_matches": False,
            "original_matches": False,
            "discount_matches": False,
        }
        if st == 200:
            api["sku"] = payload.get("sku")
            api["is_active"] = payload.get("is_active")
            api["is_available"] = payload.get("is_available")
            api["slug"] = payload.get("slug")
            api["base_price"] = payload.get("base_price")
            api["original_price"] = payload.get("original_price")
            api["discount_percent"] = payload.get("discount_percent")
            api["base_matches"] = str(payload.get("base_price")) == expected_base
            api["original_matches"] = str(payload.get("original_price")) == expected_orig
            api["discount_matches"] = payload.get("discount_percent") == 10

        store_url = f"{SITE}/product/{slug}"
        sst, html = get_text(store_url)
        store = {
            "url": store_url,
            "status": sst,
            "price_digits_found_base": False,
            "price_digits_found_original": False,
            "discount_badge_hint": False,
            "strike_hint": False,
            "json_ld_offer_hint": False,
        }
        if sst == 200:
            base_d = digits_only(expected_base)
            orig_d = digits_only(expected_orig)
            html_digits = digits_only(html)
            store["price_digits_found_base"] = base_d in html_digits
            store["price_digits_found_original"] = orig_d in html_digits
            store["discount_badge_hint"] = (
                ("٪10" in html)
                or ("تخفیف" in html and "10" in html)
                or ('"discount_percent":10' in html)
                or ("٪۱۰" in html)
            )
            store["strike_hint"] = "line-through" in html
            store["json_ld_offer_hint"] = (
                '"@type":"Offer"' in html.replace(" ", "") or '"@type": "Offer"' in html
            )
            m = re.search(r'"price"\s*:\s*"?([0-9]+(?:\.[0-9]+)?)"?', html)
            if m:
                store["json_ld_price"] = m.group(1)
                store["json_ld_price_matches_base"] = (
                    digits_only(m.group(1)) == base_d or m.group(1) == expected_base
                )

        emalls = {"probed": False}
        if st == 200:
            emalls = {
                "probed": True,
                "mapping": "current_price=base_price; old_price=original_price",
                "current_price_expected": expected_base,
                "old_price_expected": expected_orig,
                "matches_api_fields": api["base_matches"] and api["original_matches"],
            }
            hit = emalls_index.get(pid)
            if hit:
                emalls["feed_hit"] = True
                emalls["feed_current_price"] = hit.get("current_price")
                emalls["feed_old_price"] = hit.get("old_price")
                emalls["feed_current_matches"] = str(hit.get("current_price")) == expected_base
                emalls["feed_old_matches"] = str(hit.get("old_price")) == expected_orig
            else:
                emalls["feed_hit"] = False
                emalls["note"] = "not on Emalls page=1 sample; mapping proven via API fields"

        results.append(
            {
                "label": s["label"],
                "sku": s["sku"],
                "product_id": pid,
                "expected_base": expected_base,
                "expected_original": expected_orig,
                "expected_discount_percent": 10,
                "pre_original_price": s.get("pre_original_price"),
                "is_active": s["is_active"],
                "is_available": s["is_available"],
                "api": api,
                "storefront": store,
                "emalls": emalls,
            }
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "samples": results,
        "deals_homepage_effect": deals_probe,
        "hesabfa": {
            "catalog_mutation": "NONE_AUTHORIZED",
            "invoice_semantics": (
                "OrderItem.unit_price = discounted base_price; "
                "Hesabfa unitPrice=gross paid; tax=0 under current approved policy"
            ),
        },
        "summary": {
            "api_base_ok": sum(1 for r in results if r["api"].get("base_matches")),
            "api_original_ok": sum(1 for r in results if r["api"].get("original_matches")),
            "api_discount_ok": sum(1 for r in results if r["api"].get("discount_matches")),
            "store_status_200": sum(1 for r in results if r["storefront"]["status"] == 200),
            "sample_count": len(results),
        },
    }
    (out / "SITE_VERIFY.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["summary"], indent=2))
    visible = [r for r in results if r["api"]["status"] == 200]
    hard_fail = [
        r
        for r in visible
        if not (
            r["api"]["base_matches"]
            and r["api"]["original_matches"]
            and r["api"]["discount_matches"]
        )
    ]
    if hard_fail:
        print("SITE_VERIFY_API_MISMATCH", [r["sku"] for r in hard_fail], file=sys.stderr)
        return 2
    print("SITE_VERIFY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
