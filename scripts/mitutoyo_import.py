#!/usr/bin/env python3
"""Import crawled Mitutoyo products into Karzar via admin API.

- brand_id = Mitutoyo (2)
- no images, no marketing description
- specs only (mapped into technical_specs + extra source attrs)
- stock_quantity > 0, is_active=True
- prices as crawled (toman)

Usage:
  python scripts/mitutoyo_import.py --jsonl data/mitutoyo_crawl.jsonl
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

import os

API = os.getenv("KARZAR_API_BASE", "https://api.karzartools.com/api/v1")
BRAND_ID = 2  # Mitutoyo | میتوتویو
STOCK_QTY = "10"


def _load_admin_creds() -> tuple[str, str]:
    phone = os.getenv("INITIAL_SUPER_ADMIN_PHONE")
    password = os.getenv("INITIAL_SUPER_ADMIN_PASSWORD")
    secrets = Path(__file__).resolve().parents[1] / ".deploy-secrets"
    if secrets.exists():
        for line in secrets.read_text(encoding="utf-8").splitlines():
            if line.startswith("INITIAL_SUPER_ADMIN_PHONE=") and not phone:
                phone = line.split("=", 1)[1].strip()
            if line.startswith("INITIAL_SUPER_ADMIN_PASSWORD=") and not password:
                password = line.split("=", 1)[1].strip()
    if not phone or not password:
        raise RuntimeError("Set INITIAL_SUPER_ADMIN_PHONE/PASSWORD or use .deploy-secrets")
    return phone, password

# More specific rules first
CATEGORY_RULES: list[tuple[tuple[str, ...], int]] = [
    (("dial-indicator-accessories", "لوازم جانبی ساعت"), 80),
    (("ارتفاع سنج و کولیس پایه", "ارتفاع-سنج", "height"), 69),
    (("پایه ساعت", "پایه میکرومتر", "پایه-ها", "stand"), 64),
    (("شابلون",), 65),
    (("فیلر", "thickness", "ضخامت"), 73),
    (("شیطانک", "شیطونک", "dial-test", "test-indicator"), 60),
    (("اندیکاتور", "dial-indicator"), 59),
    (("بورگیج", "سیلندر", "bore", "cylinder"), 63),
    (("عمق", "depth"), 62),
    (("راپورتر", "گیج بلوک", "gage-block", "gauge-block"), 66),
    (("زاویه", "angle"), 68),
    (("میکرومتر", "micrometer"), 58),
    (("کولیس", "caliper"), 57),
]


def remap_category(row: dict) -> int:
    blob = " ".join(
        f"{c.get('slug') or ''} {c.get('name') or ''}"
        for c in (row.get("source_categories") or [])
    ).lower()
    for keys, cid in CATEGORY_RULES:
        if any(k.lower() in blob for k in keys):
            return cid
    return int(row.get("karzar_category_id") or 57)


def build_specifications(raw: dict) -> dict:
    """Map Persian attribute names into Karzar nested specs; keep extras under notes."""
    tech = {
        "range": "",
        "accuracy": "",
        "resolution": "",
        "material": "",
        "standard": "",
        "battery_type": "",
    }
    extras: dict[str, str] = {}
    mapping = {
        "سایز (رنج)": "range",
        "سایز": "range",
        "رنج": "range",
        "دقت": "accuracy",
        "رزولوشن": "resolution",
        "قدرت تفکیک": "resolution",
        "ساخت": "material",
        "کد فنی": "standard",
    }
    for k, v in (raw or {}).items():
        key = str(k).strip()
        val = str(v).strip()
        if not val:
            continue
        if key in mapping:
            tech[mapping[key]] = val
        elif key in {"گارانتی"}:
            extras[key] = val
        else:
            extras[key] = val
    return {
        "technical_specs": tech,
        "features": {
            "waterproof": False,
            "data_output": False,
            "auto_power_off": False,
            "buttons": [],
            "certification": extras.get("گارانتی", ""),
        },
        "dimensions": {"L_mm": 0.0, "a_mm": 0.0, "b_mm": 0.0, "c_mm": 0.0, "d_mm": 0.0},
        "optional_accessories": [],
        "source_attributes": extras,
    }


def http_json(method: str, url: str, *, data=None, headers=None, timeout=60):
    body = None
    hdrs = {"User-Agent": "KarzarMitutoyoImporter/1.0", "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw.decode()) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw[:500]}
        return e.code, payload


def login() -> str:
    phone, password = _load_admin_creds()
    body = urllib.parse.urlencode(
        {"username": phone, "password": password}
    ).encode()
    req = urllib.request.Request(
        f"{API}/auth/login",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"login failed: {data}")
    return token


def unique_sku(sku: str, seen: Counter) -> str:
    seen[sku] += 1
    if seen[sku] == 1:
        return sku[:50]
    suffix = f"-{seen[sku]}"
    return (sku[: 50 - len(suffix)] + suffix)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default="data/mitutoyo_crawl.jsonl")
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.15)
    args = ap.parse_args()

    rows = [
        json.loads(line)
        for line in Path(args.jsonl).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if args.limit:
        rows = rows[: args.limit]

    # Remap categories with improved rules
    for r in rows:
        r["karzar_category_id"] = remap_category(r)

    print("[import] rows", len(rows))
    print("[import] category distribution", Counter(r["karzar_category_id"] for r in rows))
    print("[import] priced", sum(1 for r in rows if r.get("base_price") is not None))

    if args.dry_run:
        print("[import] dry-run only")
        return 0

    print("[import] admin login…")
    token = login()
    auth = {"Authorization": f"Bearer {token}"}

    seen_sku: Counter = Counter()
    ok = fail = skip = 0
    failures: list[str] = []

    for i, row in enumerate(rows, 1):
        sku = unique_sku(str(row["sku"]), seen_sku)
        price = row.get("base_price")
        payload = {
            "sku": sku,
            "name": row["name"][:255],
            "category_id": int(row["karzar_category_id"]),
            "brand_id": BRAND_ID,
            "base_price": str(price) if price is not None else None,
            "stock_quantity": STOCK_QTY,
            "stock_unit": "piece",
            "is_original": True,
            "is_active": True,
            "description": None,  # no marketing copy
            "pdf_catalog_url": None,
            "specifications": build_specifications(row.get("specifications") or {}),
            "warranty_text": (row.get("specifications") or {}).get("گارانتی"),
        }
        status, resp = http_json(
            "POST", f"{API}/products/", data=payload, headers=auth
        )
        if status in (200, 201):
            ok += 1
            if ok % 25 == 0 or i == len(rows):
                print(f"[import] progress {i}/{len(rows)} ok={ok} fail={fail}")
        else:
            msg = resp.get("message") or resp.get("error_code") or str(resp)[:200]
            # skip duplicates already in catalog
            if status in (409, 400) and "sku" in str(resp).lower():
                skip += 1
            else:
                fail += 1
                failures.append(f"{sku}: {status} {msg}")
                if fail <= 8:
                    print(f"[import] FAIL {sku}: {status} {msg}")
        time.sleep(args.sleep)

    print(f"[import] DONE ok={ok} fail={fail} skip_dupish={skip}")
    if failures:
        Path("data/mitutoyo_import_failures.txt").write_text(
            "\n".join(failures), encoding="utf-8"
        )
        print("[import] failures written to data/mitutoyo_import_failures.txt")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
