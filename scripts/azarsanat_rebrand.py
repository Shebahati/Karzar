#!/usr/bin/env python3
"""Assign brands to unbranded AZS (ex-Azarsanat) products with careful name matching.

- Only assign when brand evidence is clear in product name (or crawl name).
- Create missing brands with country when needed.
- Leave truly unknown products unbranded.

Usage:
  python scripts/azarsanat_rebrand.py --dry-run
  python scripts/azarsanat_rebrand.py
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
from collections import Counter, defaultdict
from pathlib import Path

API = os.getenv("KARZAR_API_BASE", "https://api.karzartools.com/api/v1")
UA = "KarzarRebrand/1.0"

# brand_key -> (display_name, country)
NEW_BRANDS = {
    "WINSTAR": ("Winstar | وینستار", "تایوان"),
    "CHUMPOWER": ("Chumpower | چام‌پاور", "تایوان"),
    "PROMAX": ("Promax | پرومکس", None),
    "OMG": ("OMG | او ام جی", "ایتالیا"),
    "MPA": ("MPA | ام پی ای", "ایتالیا"),
    "ROHM": ("RÖHM | رهم", "آلمان"),
    "KEEGO": ("3Keego | کیگو", "تایوان"),
    "VIYER": ("Viyer | ویر", None),
    "ZPS": ("ZPS | زد پی‌اس", "چک"),
    "LI_HSUN": ("LI-HSUN | لی‌سان", "تایوان"),
    "ACROBAT": ("Acrobat | آکروبات", "ترکیه"),
    "CP-GRAT": ("CP-GRAT | سی‌پی‌گرات", None),
    "GROZ": ("Groz | گروز", "هند"),
    "NAREX": ("Narex | نارکس", "چک"),
    "VERTEX": ("Vertex | ورتکس", "تایوان"),
    "TRANSMEX": ("Transmex | ترنمکس", "هند"),
    "VOGEL": ("Vogel | وگل", "آلمان"),
    "JAGUAR": ("Jaguar | جگوار", None),
    "CHAGAN": ("Chagan | چاگان", "هند"),
    "SAHAND": ("Sahand | سهند", "ایران"),
    "DENIZ": ("Deniz | دنیز", "هند"),
}

EXISTING_KEYS = {
    "ASTPOWER": None,  # resolve by name startswith
    "ASIMETO": None,
    "UTEX": None,
    "EMKAY": None,
}


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
        raise RuntimeError("missing admin creds")
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
    return data["access_token"]


def normalize_name(name: str) -> str:
    return (
        (name or "")
        .replace("&#8211;", "–")
        .replace("&amp;", "&")
        .replace("\u200c", "")
    )


def detect_brand(name: str) -> str | None:
    n = normalize_name(name)
    low = n.lower()

    checks: list[tuple[str, list[str]]] = [
        ("WINSTAR", ["وینستار", "winstar", "g-star", "h-star", "m-star", "al-star"]),
        ("CHUMPOWER", ["chumpower", "چام پاور", "چامپاور", "چام‌پاور"]),
        ("PROMAX", ["پرومکس", "promax"]),
        ("OMG", ["omg ایتالیا", " omg", "omg ", "omgایتالیا"]),
        (
            "MPA",
            [
                " mpa",
                "mpa ",
                "mpa ایتالیا",
                "mpaایتالیا",
                "ام پی ای ایتالیا",
                "ام‌پی‌ای",
                "ام پی ای",
            ],
        ),
        ("ROHM", ["röhm", "rohm", "رهم"]),
        (
            "KEEGO",
            [
                "keego",
                "kegoo",
                "3keego",
                "3kegoo",
                "کیگو",
                "تری کیگو",
                "۳کیگو",
            ],
        ),
        ("ZPS", ["zps", "زد پی اس", "زدپی‌اس"]),
        ("LI_HSUN", ["li_hsun", "li-hsun", "li hsun", "hsun"]),
        ("ACROBAT", ["آکروبات", "acrobat"]),
        ("CP-GRAT", ["cp-grat", "cp grat"]),
        ("GROZ", ["گروز", "groz"]),
        ("NAREX", ["نارکس", "narex"]),
        ("VERTEX", ["ورتکس", "vertex"]),
        ("TRANSMEX", ["ترنمکس", "transmex"]),
        ("VOGEL", ["وگل", "vogel"]),
        ("JAGUAR", ["jaquar", "jaguar", "جگوار"]),
        ("CHAGAN", ["چاگان", "جاگان", "chagan"]),
        ("SAHAND", ["سهند"]),
        ("DENIZ", ["دنیز", "deniz"]),
        (
            "ASTPOWER",
            [
                "astpower",
                "ast-power",
                "ast power",
                "ای اس تی پاور",
                "ای.اس.تی. پاور",
                "ای.اس.تی پاور",
                "ای.اس.تی.پاور",
                "آست پاور",
                "توربوکات",
                "turbocut",
                "tu-dr",
                "tu-d13",
                "ast-gt",
                "ast-80",
                "ast-230",
                "ast-dm",
                "ast-pro",
                "ast-turbo",
            ],
        ),
        ("UTEX", ["utex", "یوتکس"]),
        ("EMKAY", ["emkay", "امکای"]),
        ("ASIMETO", ["asimeto", "آسیمتو"]),
    ]

    for brand, needles in checks:
        for needle in needles:
            if needle.lower() in low or needle in n:
                if brand == "MPA" and ("omg" in low):
                    continue  # OMG multi-spindle must not become MPA
                return brand

    # Viyer oils: require clear marker
    if "viyer" in low or re.search(r"(?:^|[\s\-])ویر(?:$|[\s\-])", n):
        if any(x in n for x in ("روغن", "VIYER", "viyer", "ویر")):
            return "VIYER"

    if re.search(r"\bAST[-_ ]?[A-Z0-9]", n, re.I) or re.search(r"AST-\w+", n, re.I):
        return "ASTPOWER"
    if "ای اس تی" in n:
        return "ASTPOWER"
    return None


def load_crawl() -> dict[int, dict]:
    path = Path("data/azarsanat_crawl.jsonl")
    out: dict[int, dict] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        out[int(row["source_id"])] = row
    return out


def load_unbranded(auth: dict) -> list[dict]:
    products: list[dict] = []
    skip = 0
    while True:
        st, resp = http_json(
            "GET", f"{API}/products/?skip={skip}&limit=1000", headers=auth
        )
        if st != 200:
            raise RuntimeError(f"list failed {st} {resp}")
        items = resp.get("data") or []
        for p in items:
            if not (p.get("brand") or {}).get("id"):
                products.append(p)
        total = (resp.get("meta") or {}).get("total_count")
        skip += len(items)
        if not items:
            break
        if total is not None and skip >= int(total):
            break
        if len(items) < 1000:
            break
    return products


def ensure_brands(auth: dict, needed: set[str]) -> dict[str, int]:
    st, resp = http_json("GET", f"{API}/brands/", headers=auth)
    items = resp.get("data") or []
    by_eng: dict[str, int] = {}
    for b in items:
        eng = (b["name"].split("|")[0]).strip().upper()
        by_eng[eng] = b["id"]
        # aliases
        if "ASTPOWER" in eng:
            by_eng["ASTPOWER"] = b["id"]
        if "ASIMETO" in eng:
            by_eng["ASIMETO"] = b["id"]
        if "UTEX" in eng:
            by_eng["UTEX"] = b["id"]
        if "EMKAY" in eng:
            by_eng["EMKAY"] = b["id"]
        if "WINSTAR" in eng or "وینستار" in b["name"]:
            by_eng["WINSTAR"] = b["id"]
        if "CHUMPOWER" in eng or "چام" in b["name"]:
            by_eng["CHUMPOWER"] = b["id"]
        if "PROMAX" in eng or "پرومکس" in b["name"]:
            by_eng["PROMAX"] = b["id"]
        if eng == "OMG" or b["name"].startswith("OMG"):
            by_eng["OMG"] = b["id"]
        if eng == "MPA" or b["name"].startswith("MPA"):
            by_eng["MPA"] = b["id"]
        if "RÖHM" in b["name"].upper() or "ROHM" in eng or "رهم" in b["name"]:
            by_eng["ROHM"] = b["id"]
        if "KEEGO" in eng or "کیگو" in b["name"]:
            by_eng["KEEGO"] = b["id"]
        if "VIYER" in eng or "ویر" in b["name"]:
            by_eng["VIYER"] = b["id"]
        if eng.startswith("ZPS") or "زد پی" in b["name"]:
            by_eng["ZPS"] = b["id"]
        if "HSUN" in eng or "LI-HSUN" in eng or "لی‌سان" in b["name"] or "لی سان" in b["name"]:
            by_eng["LI_HSUN"] = b["id"]
        if "ACROBAT" in eng or "آکروبات" in b["name"]:
            by_eng["ACROBAT"] = b["id"]
        if "CP-GRAT" in eng or "CP GRAT" in eng:
            by_eng["CP-GRAT"] = b["id"]
        if "GROZ" in eng or "گروز" in b["name"]:
            by_eng["GROZ"] = b["id"]
        if "NAREX" in eng or "نارکس" in b["name"]:
            by_eng["NAREX"] = b["id"]
        if "VERTEX" in eng or "ورتکس" in b["name"]:
            by_eng["VERTEX"] = b["id"]
        if "TRANSMEX" in eng or "ترنمکس" in b["name"]:
            by_eng["TRANSMEX"] = b["id"]
        if "VOGEL" in eng or "وگل" in b["name"]:
            by_eng["VOGEL"] = b["id"]
        if "JAGUAR" in eng or "JAQUAR" in eng or "جگوار" in b["name"]:
            by_eng["JAGUAR"] = b["id"]
        if "CHAGAN" in eng or "چاگان" in b["name"] or "جاگان" in b["name"]:
            by_eng["CHAGAN"] = b["id"]
        if "SAHAND" in eng or "سهند" in b["name"]:
            by_eng["SAHAND"] = b["id"]
        if "DENIZ" in eng or "دنیز" in b["name"]:
            by_eng["DENIZ"] = b["id"]

    out: dict[str, int] = {}
    for key in needed:
        if key in by_eng:
            out[key] = by_eng[key]
            continue
        if key not in NEW_BRANDS:
            raise RuntimeError(f"no create recipe for brand {key}")
        name, country = NEW_BRANDS[key]
        st, created = http_json(
            "POST",
            f"{API}/brands/",
            data={"name": name, "country": country},
            headers=auth,
        )
        if st not in (200, 201):
            raise RuntimeError(f"create brand {name}: {st} {created}")
        out[key] = created["id"]
        print(f"[brand] created {name} id={out[key]} country={country}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.08)
    args = ap.parse_args()

    token = login()
    auth = {"Authorization": f"Bearer {token}"}
    crawl = load_crawl()
    products = load_unbranded(auth)
    print(f"[rebrand] unbranded={len(products)}")

    assignments: list[tuple[dict, str, str]] = []
    unknown: list[str] = []
    for p in products:
        sku = str(p.get("sku") or "")
        name = p.get("name") or ""
        m = re.match(r"AZS-(\d+)$", sku)
        if m:
            sid = int(m.group(1))
            if sid in crawl:
                name = crawl[sid].get("name") or name
        brand = detect_brand(name)
        if brand:
            assignments.append((p, brand, name))
        else:
            unknown.append(name)

    dist = Counter(b for _, b, _ in assignments)
    print("[rebrand] identified", len(assignments), dict(dist))
    print("[rebrand] unknown", len(unknown))
    for b, n in dist.most_common():
        print(f"  {n:4} {b}")

    samples = defaultdict(list)
    for p, b, name in assignments:
        if len(samples[b]) < 3:
            samples[b].append(f"{p.get('sku')}: {normalize_name(name)[:80]}")
    print("[rebrand] samples:")
    for b, rows in samples.items():
        print(f"  {b}:")
        for r in rows:
            print(f"    {r}")

    if args.dry_run:
        Path("data/azarsanat_rebrand_unknown.txt").write_text(
            "\n".join(unknown), encoding="utf-8"
        )
        print("[rebrand] dry-run; unknowns → data/azarsanat_rebrand_unknown.txt")
        return 0

    needed = set(dist.keys())
    brands = ensure_brands(auth, needed)
    print("[rebrand] brand ids", brands)

    ok = fail = 0
    failures = []
    for i, (p, bkey, _name) in enumerate(assignments, 1):
        bid = brands[bkey]
        st, resp = http_json(
            "PUT",
            f"{API}/products/{p['id']}",
            data={"brand_id": bid},
            headers=auth,
        )
        if st in (200, 201):
            ok += 1
            if ok % 40 == 0 or i == len(assignments):
                print(f"[rebrand] progress {i}/{len(assignments)} ok={ok} fail={fail}")
        else:
            fail += 1
            failures.append(f"{p.get('sku')}: {st} {resp}")
            if fail <= 8:
                print(f"[rebrand] FAIL {p.get('sku')}: {st} {resp}")
        time.sleep(args.sleep)

    report = {
        "identified": len(assignments),
        "unknown": len(unknown),
        "ok": ok,
        "fail": fail,
        "distribution": dict(dist),
        "failures": failures[:50],
    }
    Path("data/azarsanat_rebrand_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    Path("data/azarsanat_rebrand_unknown.txt").write_text(
        "\n".join(unknown), encoding="utf-8"
    )
    print(f"[rebrand] DONE ok={ok} fail={fail} unknown_left={len(unknown)}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
