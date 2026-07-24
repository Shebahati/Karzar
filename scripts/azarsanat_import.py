#!/usr/bin/env python3
"""Import crawled azarsanat.net products into Karzar.

Rules:
- default base_price = 10_000_000 (placeholder until price list arrives)
- no images, no marketing description
- specs from WooCommerce attributes only
- create missing brands (Emkay, UTEX, Azarsanat, …)
- ensure depth-3 selectable leaves under existing depth-2 tool/machine categories
- skip duplicates vs existing catalog (SKU / model / Mitutoyo|INSIZE|Dasqua source brands)

Usage:
  python scripts/azarsanat_import.py --jsonl data/azarsanat_crawl.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

API = os.getenv("KARZAR_API_BASE", "https://api.karzartools.com/api/v1")
STOCK_QTY = "10"
DEFAULT_PRICE = "10000000"
UA = "KarzarAzarsanatImporter/1.0"

# Existing brand ids (staging)
EXISTING_BRANDS = {
    "ASIMETO": 6,
    "ASTPOWER": 13,
    "INSIZE": 3,
    "DASQUA": 4,
    "MITUTOYO": 2,
}

# Brands that must never be re-imported from azarsanat (already in catalog)
SKIP_SOURCE_BRANDS = {"MITUTOYO", "INSIZE", "DASQUA"}

# Depth-2 non-selectable parents → create a depth-3 leaf named "عمومی" under each
DEPTH2_PARENTS_NEEDING_LEAF = [
    33, 34, 35, 36, 37, 38, 39, 40,
    41, 42, 43, 44, 45, 46, 47,
    48, 49, 50, 51, 52, 53, 54, 55,
    121, 122, 123, 124, 125,
]

# Extra category trees to create when missing: (root_name, mid_name, leaf_name)
EXTRA_TREES = [
    ("لوازم جانبی صنعتی", "روغن و روانکار", "روغن صنعتی"),
    ("لوازم جانبی صنعتی", "ابزار دستی", "ابزار دستی عمومی"),
    ("لوازم جانبی صنعتی", "ابزار چوبی", "ابزار آلات چوبی"),
    ("دستگاه‌های صنعتی", "مولتی اسپیندل", "مولتی اسپیندل"),
    ("دستگاه‌های صنعتی", "لوازم جانبی دستگاه", "لوازم جانبی قلاویز زن"),
]

# Source category slug/name keywords → Karzar depth-2 parent id (leaf resolved later)
# More specific rules first.
CATEGORY_RULES: list[tuple[tuple[str, ...], str]] = [
    # machines
    (("drill-magnet", "دریل مگنت"), "machine:magnet"),
    (("tool-sharpener-machine", "دستگاه ابزار تیز", "toolsharpen", "مته تیز کن", "فرز تیز کن", "قلاویز تیز کن", "drill-sharpener", "endmill-sharpener", "tap-sharpener"), "machine:sharpener"),
    (("tapping-machine", "قلاویز زن", "دستگاه قلاویز"), "machine:tapping"),
    (("coredrill", "کُرگیری", "کرگیری", "کر دریل"), "machine:core"),
    (("اسپارک", "spark"), "machine:spark"),
    (("multi-spindle", "مولتی اسپیندل", "multispindel"), "extra:multi"),
    (("tapping-machine-accessories", "لوازم جانبی دستگاه قلاویز"), "extra:tap-acc"),
    # measurement
    (("calipers", "کولیس"), "meas:57"),
    (("micrometer", "میکرومتر"), "meas:58"),
    (("dial-measuring", "ساعت اندازه"), "meas:59"),
    (("measurement-dial-base", "پایه ساعت"), "meas:64"),
    (("pine-gage", "پین گیج"), "meas:67"),
    (("protractor", "زوایه", "زاویه"), "meas:68"),
    (("compass", "پرگار"), "meas:72"),
    (("bevel", "گونیا"), "meas:75"),
    (("ruler", "خط کش"), "meas:76"),
    (("threaded-template", "شابلون", "دنده سنج", "رزوه سنج"), "meas:65"),
    (("ring-gauge", "گیج توپی", "گیج رینگی", "ball-gauge"), "meas:67"),
    (("v-block", "وی بلوک"), "work:113"),
    (("hardness", "سختی سنج"), "meas:89"),
    (("زبری", "roughness"), "meas:93"),
    (("صفحه صافی", "surface-plate"), "meas:79"),
    (("فیلر", "filler", "شیارسنج"), "meas:73"),
    (("تراز صنعتی", "level"), "meas:71"),
    (("گیج داخل سیلندر", "bore", "cylinder"), "meas:63"),
    (("عمق سنج", "depth"), "meas:62"),
    (("راپورتر", "گیج بلوک", "gage-block"), "meas:66"),
    (("accessories-for-measuring", "لوازم جانبی تجهیزات اندازه"), "meas:80"),
    (("quality-measurement", "اندازه گیری و کنترل"), "meas:57"),  # fallback leaf later refined by name
    # toolholding / workholding
    (("pull-stud", "پول استاد", "pull stud"), "hold:17"),
    (("bt-er-collet", "کلت فشنگی", "spring-collet", "فشنگی"), "hold:13"),
    (("collet-drill-chuck", "کلت سه نظام"), "hold:13"),
    (("کلت", "collet"), "hold:13"),
    (("بیس هلدر", "بیس هولدر", "base-holder"), "hold:19"),
    (("holding-lathe", "هلدر تراشکاری", "cutting-insert-holder", "هلدر رو تراش"), "insert:27"),
    (("vise", "گیره"), "work:99"),
    (("صفحه گردان", "تایکوپ", "rotary"), "work:102"),
    (("روبند", "clamp"), "work:106"),
    (("زیرکاری", "زیر سری"), "work:112"),
    (("lathe-centres", "مرغک"), "work:119"),
    (("سه نظام", "chuck"), "work:116"),
    (("milling-lathe-and-drill", "تجهیزات دستگاه فرز"), "hold:13"),
    # cutting tools
    (("machine-screw-thread", "قلاویز ماشینی"), "tap:49"),
    (("handmade-qalawiz", "قلاویز دستی"), "tap:50"),
    (("قلاویز چپ", "left"), "tap:52"),
    (("قلاویز گیر", "tap-holder"), "hold:13"),
    (("hadida", "حدیده"), "tap:54"),
    (("هلی کویل", "helicoil", "هلی‌کویل"), "tap:55"),
    (("برقو", "reamer"), "drill:47"),
    (("endmill", "فرز انگشتی"), "endmill:35"),
    (("carbideburrs", "فرز فرم"), "endmill:40"),
    (("drill", "مته خزینه", "مته مرغک", "مته"), "drill:43"),
    (("گردبر", "dusters"), "drill:43"),
    (("screw-thread-reamer", "قلاویز کاری و برقو"), "tap:49"),
    # oils / hand / wood
    (("industrial-oils", "روغن", "cutting-oil", "روانکاوی", "آنتی باکتریال", "نانو روغن", "ژل پاک"), "extra:oil"),
    (("woodtools", "ابزار آلات چوبی", "رنده"), "extra:wood"),
    (("hand-tool", "ابزار دستی", "چکش", "سوهان", "مغار", "سنبه", "تیشه", "شابر", "کمان اره", "جک", "پلیسه"), "extra:hand"),
]


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


def http_json(method: str, url: str, *, data=None, headers=None, timeout=90):
    body = None
    hdrs = {"User-Agent": UA, "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
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
    body = urllib.parse.urlencode({"username": phone, "password": password}).encode()
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


def normalize_text(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"&#\d+;", " ", s)
    s = re.sub(r"&[a-z]+;", " ", s)
    s = re.sub(r"[^\w\u0600-\u06ff]+", "", s, flags=re.UNICODE)
    return s


def extract_model_tokens(name: str) -> set[str]:
    tokens = set()
    for m in re.finditer(r"[A-Za-z]{0,6}\d{2,}[A-Za-z0-9\-]{0,20}", name or ""):
        t = m.group(0).upper().strip("-")
        if len(t) >= 3:
            tokens.add(t)
    return tokens


def detect_brand_key(row: dict) -> str:
    brand_tax = " ".join(
        f"{b.get('name', '')} {b.get('slug', '')}" for b in (row.get("source_brands") or [])
    )
    blob = f"{row.get('name', '')} {brand_tax}"
    rules = [
        ("MITUTOYO", ("mitutoyo", "میتوتویو")),
        ("INSIZE", ("insize", "اینسایز")),
        ("DASQUA", ("dasqua", "داسکوا")),
        ("ASIMETO", ("asimeto", "آسیمتو")),
        ("ASTPOWER", ("astpower", "ast-turbocut", "ast ", "ای اس تی", "آست پاور")),
        ("EMKAY", ("emkay", "امکای", " et ")),
        ("UTEX", ("utex", "یوتکس")),
    ]
    low = blob.lower()
    for key, needles in rules:
        if any(n in low or n in blob for n in needles):
            return key
    return "AZARSANAT"


def ensure_brands(auth: dict) -> dict[str, int]:
    status, resp = http_json("GET", f"{API}/brands/", headers=auth)
    if status != 200:
        raise RuntimeError(f"brands list failed: {status} {resp}")
    items = resp.get("data") or []
    by_name = {b["name"]: b["id"] for b in items}
    wanted = {
        "ASIMETO": ("ASIMETO | آسیمتو", None),
        "ASTPOWER": ("ASTPOWER | ای اس تی پاور", None),
        "EMKAY": ("Emkay | امکای", "India"),
        "UTEX": ("UTEX | یوتکس", None),
        "AZARSANAT": ("Azarsanat | آذرصنعت", "Iran"),
    }
    out: dict[str, int] = {}
    for key, (fullname, country) in wanted.items():
        if key in EXISTING_BRANDS and any(
            b["id"] == EXISTING_BRANDS[key] for b in items
        ):
            out[key] = EXISTING_BRANDS[key]
            continue
        if fullname in by_name:
            out[key] = by_name[fullname]
            continue
        # fuzzy match startswith english part
        eng = fullname.split("|")[0].strip().lower()
        found = next((b for b in items if b["name"].lower().startswith(eng)), None)
        if found:
            out[key] = found["id"]
            continue
        st, created = http_json(
            "POST",
            f"{API}/brands/",
            data={"name": fullname, "country": country},
            headers=auth,
        )
        if st in (200, 201):
            out[key] = created["id"]
            print(f"[brand] created {fullname} id={out[key]}")
        else:
            raise RuntimeError(f"create brand {fullname}: {st} {created}")
    return out


def ensure_depth3_leaves(auth: dict) -> dict[int, int]:
    """Map depth-2 parent id → selectable depth-3 child id."""
    status, resp = http_json("GET", f"{API}/categories/", headers=auth)
    cats = resp.get("data") or []
    by_id = {c["id"]: c for c in cats}
    children: dict[int, list[dict]] = {}
    for c in cats:
        if c.get("parent_id") is not None:
            children.setdefault(c["parent_id"], []).append(c)

    mapping: dict[int, int] = {}
    for pid in DEPTH2_PARENTS_NEEDING_LEAF:
        parent = by_id.get(pid)
        if not parent:
            print(f"[cat] missing parent {pid}")
            continue
        kids = children.get(pid) or []
        selectable = [k for k in kids if k.get("is_selectable")]
        if selectable:
            mapping[pid] = selectable[0]["id"]
            continue
        # create leaf
        leaf_name = f"{parent['name']} — عمومی"
        if len(leaf_name) > 100:
            leaf_name = "عمومی"
        st, created = http_json(
            "POST",
            f"{API}/categories/",
            data={"name": leaf_name, "parent_id": pid},
            headers=auth,
        )
        if st in (200, 201):
            mapping[pid] = created["id"]
            print(f"[cat] leaf under {pid} → {created['id']} {leaf_name}")
        else:
            raise RuntimeError(f"create leaf under {pid}: {st} {created}")
    return mapping


def ensure_extra_trees(auth: dict) -> dict[str, int]:
    """Return keys like extra:oil → leaf id."""
    status, resp = http_json("GET", f"{API}/categories/", headers=auth)
    cats = resp.get("data") or []
    by_name_parent: dict[tuple[str | None, str], int] = {
        (c.get("parent_id"), c["name"]): c["id"] for c in cats
    }
    roots = {c["name"]: c["id"] for c in cats if c.get("parent_id") is None}

    key_map = {
        ("لوازم جانبی صنعتی", "روغن و روانکار", "روغن صنعتی"): "extra:oil",
        ("لوازم جانبی صنعتی", "ابزار دستی", "ابزار دستی عمومی"): "extra:hand",
        ("لوازم جانبی صنعتی", "ابزار چوبی", "ابزار آلات چوبی"): "extra:wood",
        ("دستگاه‌های صنعتی", "مولتی اسپیندل", "مولتی اسپیندل"): "extra:multi",
        ("دستگاه‌های صنعتی", "لوازم جانبی دستگاه", "لوازم جانبی قلاویز زن"): "extra:tap-acc",
    }
    out: dict[str, int] = {}

    for root_name, mid_name, leaf_name in EXTRA_TREES:
        # root
        if root_name in roots:
            root_id = roots[root_name]
        else:
            st, created = http_json(
                "POST",
                f"{API}/categories/",
                data={"name": root_name, "parent_id": None},
                headers=auth,
            )
            if st not in (200, 201):
                raise RuntimeError(f"create root {root_name}: {st} {created}")
            root_id = created["id"]
            roots[root_name] = root_id
            print(f"[cat] root {root_name} id={root_id}")

        # mid
        mid_key = (root_id, mid_name)
        if mid_key in by_name_parent:
            mid_id = by_name_parent[mid_key]
        else:
            # also match by name only under this root via refresh
            st, created = http_json(
                "POST",
                f"{API}/categories/",
                data={"name": mid_name, "parent_id": root_id},
                headers=auth,
            )
            if st in (200, 201):
                mid_id = created["id"]
                by_name_parent[mid_key] = mid_id
                print(f"[cat] mid {mid_name} id={mid_id}")
            elif st == 409:
                # refetch
                status, resp = http_json("GET", f"{API}/categories/", headers=auth)
                cats = resp.get("data") or []
                mid_id = next(
                    c["id"]
                    for c in cats
                    if c.get("parent_id") == root_id and c["name"] == mid_name
                )
            else:
                raise RuntimeError(f"create mid {mid_name}: {st} {created}")

        # leaf
        leaf_key = (mid_id, leaf_name)
        if leaf_key in by_name_parent:
            leaf_id = by_name_parent[leaf_key]
        else:
            st, created = http_json(
                "POST",
                f"{API}/categories/",
                data={"name": leaf_name, "parent_id": mid_id},
                headers=auth,
            )
            if st in (200, 201):
                leaf_id = created["id"]
                by_name_parent[leaf_key] = leaf_id
                print(f"[cat] leaf {leaf_name} id={leaf_id}")
            elif st == 409:
                status, resp = http_json("GET", f"{API}/categories/", headers=auth)
                cats = resp.get("data") or []
                leaf_id = next(
                    c["id"]
                    for c in cats
                    if c.get("parent_id") == mid_id and c["name"] == leaf_name
                )
            else:
                raise RuntimeError(f"create leaf {leaf_name}: {st} {created}")

        out[key_map[(root_name, mid_name, leaf_name)]] = leaf_id

    return out


def resolve_category(
    row: dict,
    *,
    depth2_leaves: dict[int, int],
    extras: dict[str, int],
) -> int:
    blob = " ".join(
        f"{c.get('slug') or ''} {c.get('name') or ''}"
        for c in (row.get("source_categories") or [])
    )
    name = row.get("name") or ""
    search = f"{blob} {name}".lower()

    token = None
    for keys, tok in CATEGORY_RULES:
        if any(k.lower() in search for k in keys):
            token = tok
            break
    if token is None:
        token = "meas:57"  # last resort — better than failing; refined below by name

    # name-based refinements for measurement fallback
    if "کولیس" in name:
        token = "meas:57"
    elif "میکرومتر" in name or "میکرو متر" in name:
        token = "meas:58"
    elif "اندیکاتور" in name or "ساعت اندازه" in name:
        token = "meas:59"
    elif "شیطانک" in name or "شیطونک" in name:
        token = "meas:60"

    if token.startswith("meas:") or token.startswith("hold:") or token.startswith("work:") or token.startswith("insert:"):
        return int(token.split(":")[1])
    if token.startswith("extra:"):
        key = "extra:" + token.split(":", 1)[1]
        # map short keys
        alias = {
            "extra:oil": "extra:oil",
            "extra:hand": "extra:hand",
            "extra:wood": "extra:wood",
            "extra:multi": "extra:multi",
            "extra:tap-acc": "extra:tap-acc",
        }
        return extras[alias[key]]
    if token.startswith("machine:"):
        m = {
            "magnet": 123,
            "sharpener": 121,
            "tapping": 122,
            "core": 125,
            "spark": 124,
        }[token.split(":")[1]]
        return depth2_leaves[m]
    if token.startswith("tap:"):
        return depth2_leaves[int(token.split(":")[1])]
    if token.startswith("drill:"):
        return depth2_leaves[int(token.split(":")[1])]
    if token.startswith("endmill:"):
        return depth2_leaves[int(token.split(":")[1])]
    return 57


def build_specifications(raw: dict) -> dict:
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
        "مدل": "standard",
    }
    for k, v in (raw or {}).items():
        key = str(k).strip()
        val = str(v).strip()
        if not val:
            continue
        if key in mapping:
            tech[mapping[key]] = val
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


def make_sku(row: dict, seen: Counter) -> str:
    raw = (row.get("sku") or "").strip()
    if raw:
        base = re.sub(r"\s+", "-", raw)[:40]
        sku = f"AZS-{base}"
    else:
        sku = f"AZS-{row['source_id']}"
    sku = sku[:50]
    seen[sku] += 1
    if seen[sku] == 1:
        return sku
    suffix = f"-{seen[sku]}"
    return (sku[: 50 - len(suffix)] + suffix)


def load_existing_catalog(auth: dict) -> tuple[set[str], set[str], set[str]]:
    """Return (skus_lower, normalized_names, model_tokens)."""
    skus: set[str] = set()
    names: set[str] = set()
    models: set[str] = set()
    skip = 0
    limit = 1000
    total = None
    while True:
        status, resp = http_json(
            "GET",
            f"{API}/products/?skip={skip}&limit={limit}",
            headers=auth,
        )
        if status != 200:
            raise RuntimeError(f"products list failed: {status} {resp}")
        items = resp.get("data") or resp.get("items") or []
        meta = resp.get("meta") or {}
        if total is None:
            total = meta.get("total_count") or meta.get("total") or resp.get("total")
        if not items:
            break
        for p in items:
            sku = (p.get("sku") or "").strip().lower()
            name = p.get("name") or ""
            if sku:
                skus.add(sku)
                if sku.startswith("azs-"):
                    skus.add(sku[4:])
            names.add(normalize_text(name))
            models |= extract_model_tokens(name)
        skip += len(items)
        if total is not None and skip >= int(total):
            break
        if len(items) < limit:
            break
        if skip > 20000:
            break
    print(
        f"[dedup] loaded existing skus={len(skus)} names={len(names)} "
        f"models={len(models)} total_meta={total}"
    )
    return skus, names, models

def is_duplicate(row: dict, skus: set[str], names: set[str], models: set[str]) -> str | None:
    brand = detect_brand_key(row)
    if brand in SKIP_SOURCE_BRANDS:
        return f"skip-brand:{brand}"
    src_sku = (row.get("sku") or "").strip().lower()
    if src_sku and src_sku in skus:
        return f"sku:{src_sku}"
    n = normalize_text(row.get("name") or "")
    if n and n in names:
        return "name-exact"
    # model overlap with same brand family products — only if model looks specific
    tokens = extract_model_tokens(row.get("name") or "")
    strong = {t for t in tokens if len(t) >= 5}
    if strong and strong & models:
        return f"model:{','.join(sorted(strong & models)[:3])}"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", default="data/azarsanat_crawl.jsonl")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.12)
    args = ap.parse_args()

    rows = [
        json.loads(line)
        for line in Path(args.jsonl).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if args.limit:
        rows = rows[: args.limit]

    print("[import] rows", len(rows))
    print("[import] admin login…")
    token = login()
    auth = {"Authorization": f"Bearer {token}"}

    brands = ensure_brands(auth)
    print("[import] brands", brands)
    depth2_leaves = ensure_depth3_leaves(auth)
    extras = ensure_extra_trees(auth)
    print("[import] extras", extras)

    skus, names, models = load_existing_catalog(auth)

    # pre-map
    brand_counts: Counter = Counter()
    cat_counts: Counter = Counter()
    skip_counts: Counter = Counter()
    prepared = []
    for row in rows:
        reason = is_duplicate(row, skus, names, models)
        if reason:
            skip_counts[reason.split(":")[0]] += 1
            continue
        bkey = detect_brand_key(row)
        brand_counts[bkey] += 1
        cid = resolve_category(row, depth2_leaves=depth2_leaves, extras=extras)
        cat_counts[cid] += 1
        prepared.append((row, bkey, cid))

    print("[import] will_import", len(prepared))
    print("[import] skip", dict(skip_counts))
    print("[import] brands_dist", dict(brand_counts))
    print("[import] top_cats", cat_counts.most_common(15))

    if args.dry_run:
        print("[import] dry-run only")
        return 0

    seen_sku: Counter = Counter()
    ok = fail = 0
    failures: list[str] = []

    for i, (row, bkey, cid) in enumerate(prepared, 1):
        sku = make_sku(row, seen_sku)
        payload = {
            "sku": sku,
            "name": row["name"][:255].replace("&#8211;", "–"),
            "category_id": int(cid),
            "brand_id": brands[bkey],
            "base_price": DEFAULT_PRICE,
            "stock_quantity": STOCK_QTY,
            "stock_unit": "piece",
            "is_original": True,
            "is_active": True,
            "description": None,
            "pdf_catalog_url": None,
            "specifications": build_specifications(row.get("specifications") or {}),
            "warranty_text": (row.get("specifications") or {}).get("گارانتی"),
        }
        status, resp = http_json("POST", f"{API}/products/", data=payload, headers=auth)
        if status in (200, 201):
            ok += 1
            # prevent intra-batch name dupes against later items
            names.add(normalize_text(row["name"]))
            skus.add(sku.lower())
            if ok % 50 == 0 or i == len(prepared):
                print(f"[import] progress {i}/{len(prepared)} ok={ok} fail={fail}")
        else:
            msg = resp.get("message") or resp.get("error_code") or str(resp)[:200]
            if status in (409, 400) and "sku" in str(resp).lower():
                skip_counts["api-sku"] += 1
            else:
                fail += 1
                failures.append(f"{sku}: {status} {msg}")
                if fail <= 12:
                    print(f"[import] FAIL {sku}: {status} {msg}")
        time.sleep(args.sleep)

    print(f"[import] DONE ok={ok} fail={fail} skipped_pre={sum(skip_counts.values())}")
    out = Path("data/azarsanat_import_failures.txt")
    if failures:
        out.write_text("\n".join(failures), encoding="utf-8")
        print("[import] failures →", out)
    summary = {
        "ok": ok,
        "fail": fail,
        "skipped": dict(skip_counts),
        "brands": dict(brand_counts),
    }
    Path("data/azarsanat_import_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
