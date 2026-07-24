#!/usr/bin/env python3
"""Catalog remediation batch:
1) Clean names (HTML entities, Arabic presentation forms, marketing phrases, broken dups)
2) Strip AZS- SKU prefix (keep uniqueness)
3) Assign brands to unbranded via name/SKU/crawl heuristics
4) Rename «— عمومی» category leaves to unique «استاندارد» names
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

API = os.getenv("KARZAR_API_BASE", "https://api.karzartools.com/api/v1")
UA = "KarzarCatalogRemediation/1.0"

# Remove marketing fluff but keep «مدل CODE»
MARKETING_PATTERNS = [
    r"\s*با گارانتی شرکتی",
    r"\s*\+\s*ضمانت اصالت کالا و کالیبراسیون",
    r"\s*\+\s*تحویل 2 ساعته در تهران",
    r"\s*\+\s*ارسال سریع به سراسر ایران",
    r"\s*تحویل 2 ساعته در تهران",
    r"\s*ارسال سریع به سراسر ایران",
    r"\s*ضمانت اصالت کالا و کالیبراسیون",
]

BRAND_RULES: list[tuple[str, str | None, list[str]]] = [
    ("ASTPOWER", "تایوان", [
        "astpower", "ast-power", "ast power", "ای اس تی پاور", "ای.اس.تی",
        "آست پاور", "توربوکات", "turbocut", "tu-dr", "tu-d13",
        "ast-gt", "ast-80", "ast-230", "ast-dm", "ast-pro", "ast-turbo",
    ]),
    ("CHUMPOWER", "تایوان", ["chumpower", "چام پاور", "چامپاور", "چام‌پاور"]),
    ("WINSTAR", "تایوان", ["وینستار", "winstar", "g-star", "h-star", "m-star", "al-star"]),
    ("GROZ", "هند", ["گروز", "groz"]),
    ("CHAGAN", "هند", ["چاگان", "جاگان", "chagan"]),
    ("VERTEX", "تایوان", ["ورتکس", "vertex"]),
    ("KEEGO", "تایوان", ["کیگو", "keego", "kegoo", "3keego", "تری کیگو"]),
    ("MPA", "ایتالیا", ["ام پی ای", "ام‌پی‌ای", " mpa", "mpa "]),
    ("OMG", "ایتالیا", [" omg", "omg ", "omgایتالیا"]),
    ("TRANSMEX", "هند", ["ترنمکس", "transmex"]),
    ("NAREX", "چک", ["نارکس", "narex"]),
    ("ZPS", "چک", ["zps", "زد پی اس"]),
    ("LI_HSUN", "تایوان", ["li_hsun", "li-hsun", "li hsun", "لی‌سان"]),
    ("ROHM", "آلمان", ["rohm", "röhm", "رهم"]),
    ("VOGEL", "آلمان", ["وگل", "vogel"]),
    ("VIYER", None, ["viyer"]),
    ("PROMAX", None, ["پرومکس", "promax"]),
    ("CP-GRAT", None, ["cp-grat", "cp grat"]),
    ("ACROBAT", "ترکیه", ["آکروبات", "acrobat"]),
    ("JAGUAR", None, ["jaguar", "jaquar", "جگوار"]),
    ("SAHAND", "ایران", ["سهند"]),
    ("DENIZ", "هند", ["دنیز", "deniz"]),
    ("UTEX", "چین", ["یوتکس", "utex"]),
    ("EMKAY", "هند", ["امکای", "emkay"]),
    ("ASIMETO", "تایوان", ["آسیمتو", "asimeto"]),
    ("INSIZE", "چین", ["اینسایز", "insize"]),
    ("MITUTOYO", "ژاپن", ["میتوتویو", "mitutoyo"]),
    ("DASQUA", "ایتالیا", ["داسکوا", "dasqua"]),
]

BRAND_DISPLAY = {
    "ASTPOWER": ("ASTPOWER | ای اس تی پاور", "تایوان"),
    "KEEGO": ("3Keego | کیگو", "تایوان"),
    "LI_HSUN": ("LI-HSUN | لی‌سان", "تایوان"),
    "ROHM": ("RÖHM | رهم", "آلمان"),
    "CP-GRAT": ("CP-GRAT | سی‌پی‌گرات", None),
    "EMKAY": ("Emkay | امکای", "هند"),
    "CHUMPOWER": ("Chumpower | چام‌پاور", "تایوان"),
    "WINSTAR": ("Winstar | وینستار", "تایوان"),
    "GROZ": ("Groz | گروز", "هند"),
    "CHAGAN": ("Chagan | چاگان", "هند"),
    "VERTEX": ("Vertex | ورتکس", "تایوان"),
    "MPA": ("MPA | ام پی ای", "ایتالیا"),
    "OMG": ("OMG | او ام جی", "ایتالیا"),
    "TRANSMEX": ("Transmex | ترنمکس", "هند"),
    "NAREX": ("Narex | نارکس", "چک"),
    "ZPS": ("ZPS | زد پی‌اس", "چک"),
    "VOGEL": ("Vogel | وگل", "آلمان"),
    "VIYER": ("Viyer | ویر", None),
    "PROMAX": ("Promax | پرومکس", None),
    "ACROBAT": ("Acrobat | آکروبات", "ترکیه"),
    "JAGUAR": ("Jaguar | جگوار", None),
    "SAHAND": ("Sahand | سهند", "ایران"),
    "DENIZ": ("Deniz | دنیز", "هند"),
    "UTEX": ("Utex | یوتکس", "چین"),
    "ASIMETO": ("Asimeto | آسیمتو", "تایوان"),
}

GARBAGE_NAME_RE = re.compile(
    r"(ی ي سنج|الکی$|رس پيچ|گوشتي کاربايد|1,\d{3},\d{3},\d{3}|مرکزیاب 1$)"
)


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
        return json.loads(resp.read().decode())["access_token"]


def fetch_all_products(auth: dict) -> list[dict]:
    products: list[dict] = []
    skip = 0
    while True:
        st, resp = http_json(
            "GET",
            f"{API}/products/?limit=100&skip={skip}",
            headers=auth,
            timeout=120,
        )
        if st != 200:
            raise RuntimeError(f"products fetch {st} {resp}")
        batch = resp.get("data") or []
        if not batch:
            break
        for p in batch:
            brand_obj = p.get("brand") if isinstance(p.get("brand"), dict) else None
            brand_name = (
                (brand_obj or {}).get("name")
                if brand_obj
                else p.get("brand_name")
            )
            brand_id = p.get("brand_id") or (brand_obj or {}).get("id")
            products.append(
                {
                    "id": p["id"],
                    "sku": p.get("sku"),
                    "name": p.get("name"),
                    "brand_id": brand_id,
                    "brand_name": brand_name,
                    "category_id": p.get("category_id"),
                    "price": p.get("price"),
                }
            )
        skip += len(batch)
        if len(batch) < 100:
            break
        print(f"[rem] fetched {len(products)}…")
    return products


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


def clean_name(name: str) -> str:
    if not name:
        return name
    s = html.unescape(name)
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\xa0", " ")
    model_m = re.search(r"مدل\s*[0-9A-Za-z][0-9A-Za-z\-./]*", s)
    model = model_m.group(0) if model_m else None
    for pat in MARKETING_PATTERNS:
        s = re.sub(pat, "", s, flags=re.I)
    s = re.sub(r"[ \t]+", " ", s).strip()
    s = re.sub(r"[\s\-–|/]+$", "", s).strip()
    if model and model not in s:
        s = f"{s} {model}".strip()
    return s[:255]


def looks_garbage(name: str) -> bool:
    if not name:
        return True
    if len(name.strip()) < 5:
        return True
    if GARBAGE_NAME_RE.search(name):
        return True
    if re.search(r"\d,\d{3},\d{3}", name):
        return True
    return False


def fix_garbage_name(sku: str, old: str) -> str:
    """Map known garbled Dasqua families to readable Persian names."""
    s = (sku or "").strip()
    prefix = s.split("-")[0] if "-" in s else s[:4]

    if prefix == "8500":
        size = ""
        m = re.search(r"8500-(\d{4})$", s)
        if m:
            dig = m.group(1)
            a, b = int(dig[:2]) * 10, int(dig[2:]) * 10
            if a and b:
                size = f" {a}×{b}mm"
        return f"صفحه گرانیتی داسکوا{size} کد {s}"

    if prefix == "5333":
        return f"نوک پراب ساعت اندیکاتور داسکوا کد {s}"

    if prefix == "1803":
        return f"ساعت مرکزیاب داسکوا کد {s}"

    if prefix == "1804":
        return f"ضخامت‌سنج پوشش داسکوا کد {s}"

    if prefix == "9211":
        return f"گیج ضخامت صفحه‌ای داسکوا کد {s}"

    if prefix in {"1122", "8101", "8203", "8561", "8802"}:
        # OCR garbage «ی ي سنج شور» → Shore hardness tester
        range_bit = ""
        rm = re.search(r"(0-\d+\s*mm)", old or "", re.I)
        if rm:
            range_bit = f" {rm.group(1)}"
        return f"سختی‌سنج شور داسکوا{range_bit} کد {s}"

    return f"ابزار اندازه‌گیری داسکوا کد {s}" if s else clean_name(old)


def detect_brand(name: str, sku: str = "") -> str | None:
    blob = f"{name} {sku}".lower().replace("\u200c", "")
    raw = f"{name} {sku}"
    for key, _country, needles in BRAND_RULES:
        for n in needles:
            if n.lower() in blob or n in raw:
                if key == "VIYER" and not (
                    "viyer" in blob
                    or "روغن" in (name or "")
                    or re.search(r"(^|[\s\-])ویر($|[\s\-])", name or "")
                ):
                    continue
                if key == "MPA" and "omg" in blob:
                    continue
                return key
    # ASTPOWER from SKU patterns (AZS-AST-…, AST-PRO, …)
    if re.search(r"(^|[-_/])AST([-_/]|$)", sku or "", re.I):
        return "ASTPOWER"
    if re.search(r"\bAST[-_ ]?[A-Z0-9]", raw, re.I) or re.search(r"AST-\w+", raw, re.I):
        return "ASTPOWER"
    if "ای اس تی" in (name or ""):
        return "ASTPOWER"
    return None


def new_sku_from_azs(sku: str, name: str, seen: Counter) -> str:
    raw = sku.strip()
    if not raw.upper().startswith("AZS-"):
        base = raw
    else:
        rest = raw[4:]
        # Prefer AST-* style already in AZS suffix
        if re.match(r"(?i)AST[-_/]", rest):
            base = rest.replace("/", "-").upper()[:50]
        else:
            m = re.search(r"(?:مدل|کد)\s*([0-9A-Za-z][0-9A-Za-z\-./]{2,})", name or "")
            if m:
                base = m.group(1).upper().replace("/", "-")[:50]
            else:
                m2 = re.search(r"\b([A-Z]{2,6}[-_]?\d{2,}[A-Z0-9\-]*)\b", name or "", re.I)
                if m2 and not m2.group(1).upper().startswith("HSS"):
                    base = m2.group(1).upper()[:50]
                else:
                    base = rest.replace("/", "-")[:50]
    base = re.sub(r"\s+", "-", base).strip("-") or raw[4:50]
    base = base[:50]
    key = base.upper()
    # collision with an already-claimed SKU
    if seen[key] == 0:
        seen[key] = 1
        return base
    seen[key] += 1
    suf = f"-{seen[key]}"
    return (base[: 50 - len(suf)] + suf)


def resolve_brand_ids(brands: list[dict]) -> dict[str, int]:
    brand_ids: dict[str, int] = {}
    mapping = {
        "ASTPOWER": "ASTPOWER",
        "ASIMETO": "ASIMETO",
        "CHUMPOWER": "CHUMPOWER",
        "WINSTAR": "WINSTAR",
        "GROZ": "GROZ",
        "CHAGAN": "CHAGAN",
        "VERTEX": "VERTEX",
        "3KEEGO": "KEEGO",
        "MPA": "MPA",
        "OMG": "OMG",
        "TRANSMEX": "TRANSMEX",
        "NAREX": "NAREX",
        "ZPS": "ZPS",
        "LI-HSUN": "LI_HSUN",
        "RÖHM": "ROHM",
        "ROHM": "ROHM",
        "VOGEL": "VOGEL",
        "VIYER": "VIYER",
        "PROMAX": "PROMAX",
        "CP-GRAT": "CP-GRAT",
        "ACROBAT": "ACROBAT",
        "JAGUAR": "JAGUAR",
        "SAHAND": "SAHAND",
        "DENIZ": "DENIZ",
        "UTEX": "UTEX",
        "EMKAY": "EMKAY",
        "INSIZE": "INSIZE",
        "MITUTOYO": "MITUTOYO",
        "DASQUA": "DASQUA",
    }
    for b in brands:
        eng = b["name"].split("|")[0].strip().upper()
        brand_ids[eng] = b["id"]
        for k, v in mapping.items():
            if eng == k or eng.startswith(k):
                brand_ids[v] = b["id"]
    return brand_ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.06)
    ap.add_argument("--skip-brands", action="store_true")
    ap.add_argument("--skip-cats", action="store_true")
    ap.add_argument("--skip-skus", action="store_true")
    ap.add_argument("--refresh", action="store_true", help="re-fetch products from API")
    args = ap.parse_args()

    token = login()
    auth = {"Authorization": f"Bearer {token}"}

    slim_path = Path("data/catalog_slim.json")
    if args.refresh or not slim_path.exists():
        slim = fetch_all_products(auth)
        slim_path.write_text(json.dumps(slim, ensure_ascii=False), encoding="utf-8")
        print(f"[rem] refreshed catalog_slim n={len(slim)}")
    else:
        slim = json.loads(slim_path.read_text(encoding="utf-8"))
        print(f"[rem] products={len(slim)}")

    crawl = load_crawl()
    print(f"[rem] crawl entries={len(crawl)}")

    st, brands_resp = http_json("GET", f"{API}/brands/", headers=auth)
    brand_ids = resolve_brand_ids(brands_resp.get("data") or [])

    # ---------- 1) name cleans ----------
    cleanable: list[tuple[dict, str]] = []
    garbage_fixes: list[tuple[dict, str]] = []
    for p in slim:
        old = p.get("name") or ""
        new = clean_name(old)
        if new != old:
            cleanable.append((p, new))
        elif looks_garbage(old):
            garbage_fixes.append((p, fix_garbage_name(str(p.get("sku") or ""), old)))
    print(f"[rem] name_cleanable={len(cleanable)} garbage_auto_rename={len(garbage_fixes)}")

    name_by_id = {p["id"]: n for p, n in cleanable}
    for p, n in garbage_fixes:
        name_by_id[p["id"]] = n

    # ---------- 2) SKU strip AZS ----------
    sku_seen: Counter = Counter()
    for p in slim:
        s = str(p.get("sku") or "")
        if s and not s.upper().startswith("AZS-"):
            sku_seen[s.upper()] = 1

    sku_updates: list[tuple[dict, str]] = []
    if not args.skip_skus:
        for p in slim:
            s = str(p.get("sku") or "")
            if not s.upper().startswith("AZS-"):
                continue
            name_for = name_by_id.get(p["id"], p.get("name") or "")
            new = new_sku_from_azs(s, name_for, sku_seen)
            if new != s:
                sku_updates.append((p, new))
    print(f"[rem] sku_updates={len(sku_updates)}")

    # ---------- 3) brands for unbranded ----------
    brand_updates: list[tuple[dict, int, str]] = []
    if not args.skip_brands:
        for p in slim:
            # list API often omits brand_id; treat brand_name as already branded
            if p.get("brand_id") or p.get("brand_name"):
                continue
            sku = str(p.get("sku") or "")
            name_for = name_by_id.get(p["id"], p.get("name") or "")
            crawl_name = ""
            m = re.match(r"(?i)AZS-(\d+)$", sku)
            if m:
                crow = crawl.get(int(m.group(1)))
                if crow:
                    crawl_name = crow.get("name") or ""
            key = detect_brand(f"{name_for} {crawl_name}", sku)
            if not key:
                continue
            if key not in brand_ids:
                bname, country = BRAND_DISPLAY.get(
                    key, (f"{key.replace('_', '-')} | {key}", next((c for k, c, _ in BRAND_RULES if k == key), None))
                )
                if args.dry_run:
                    brand_ids[key] = -1
                else:
                    st, created = http_json(
                        "POST",
                        f"{API}/brands/",
                        data={"name": bname, "country": country},
                        headers=auth,
                    )
                    if st in (200, 201):
                        brand_ids[key] = created["id"]
                        print(f"[brand] created {bname} id={created['id']}")
                    else:
                        print(f"[brand] FAIL create {bname}: {st} {created}")
                        continue
            brand_updates.append((p, brand_ids[key], key))
    print(f"[rem] brand_updates={len(brand_updates)} keys={Counter(k for _,_,k in brand_updates)}")

    # ---------- 4) categories rename عمومی → استاندارد ----------
    cat_renames: list[tuple[dict, str]] = []
    if not args.skip_cats:
        st, cats_resp = http_json("GET", f"{API}/categories/", headers=auth)
        cats = cats_resp.get("data") or []
        by_id = {c["id"]: c for c in cats}
        used_names: set[str] = {((c.get("name") or "").strip()) for c in cats}
        for c in cats:
            name = c.get("name") or ""
            if "— عمومی" not in name:
                continue
            parent = by_id.get(c.get("parent_id"))
            parent_name = (parent.get("name") if parent else "") or ""
            # Prefer unique leaf under parent: «استاندارد»
            candidates = [
                "استاندارد",
                f"استاندارد — {parent_name}".strip(" —")[:80],
                f"استاندارد ({c['id']})",
            ]
            new_name = None
            for cand in candidates:
                if cand and cand not in used_names:
                    new_name = cand
                    break
            if not new_name:
                new_name = f"استاندارد ({c['id']})"
            used_names.add(new_name)
            cat_renames.append((c, new_name))
    print(f"[rem] cat_renames={len(cat_renames)}")

    plan = {
        "name_clean": len(cleanable),
        "garbage_rename": len(garbage_fixes),
        "sku_updates": len(sku_updates),
        "brand_updates": len(brand_updates),
        "cat_renames": len(cat_renames),
        "sku_samples": [(p["sku"], n) for p, n in sku_updates[:20]],
        "name_samples": [(p["sku"], p["name"], n) for p, n in cleanable[:15]],
        "garbage_samples": [(p["sku"], p["name"], n) for p, n in garbage_fixes[:15]],
        "brand_samples": [(p["sku"], k) for p, _, k in brand_updates[:30]],
        "cat_samples": [(c["id"], c["name"], n) for c, n in cat_renames[:15]],
    }
    Path("data/remediation_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if args.dry_run:
        print("[rem] dry-run → data/remediation_plan.json")
        return 0

    ok = fail = 0
    failures: list[str] = []

    def put_product(pid: int, payload: dict, label: str) -> bool:
        nonlocal ok, fail
        st, resp = http_json("PUT", f"{API}/products/{pid}", data=payload, headers=auth)
        if st in (200, 201):
            ok += 1
            return True
        fail += 1
        failures.append(f"{label}: {st} {resp}")
        return False

    for i, (p, new) in enumerate(cleanable, 1):
        put_product(p["id"], {"name": new}, f"name {p.get('sku')}")
        if i % 50 == 0:
            print(f"[rem] names {i}/{len(cleanable)}")
        time.sleep(args.sleep)
    for i, (p, new) in enumerate(garbage_fixes, 1):
        put_product(p["id"], {"name": new}, f"garbage {p.get('sku')}")
        if i % 25 == 0:
            print(f"[rem] garbage {i}/{len(garbage_fixes)}")
        time.sleep(args.sleep)
    print(f"[rem] names done ok={ok} fail={fail}")

    sku_ok = sku_fail = 0
    for i, (p, new) in enumerate(sku_updates, 1):
        st, resp = http_json(
            "PUT", f"{API}/products/{p['id']}", data={"sku": new}, headers=auth
        )
        if st in (200, 201):
            sku_ok += 1
        else:
            sku_fail += 1
            failures.append(f"sku {p.get('sku')}->{new}: {st} {resp}")
            if sku_fail <= 20:
                print(f"[rem] SKU FAIL {p.get('sku')} -> {new}: {st} {resp}")
        if i % 50 == 0:
            print(f"[rem] skus {i}/{len(sku_updates)} ok={sku_ok} fail={sku_fail}")
        time.sleep(args.sleep)
    print(f"[rem] skus done ok={sku_ok} fail={sku_fail}")

    b_ok = b_fail = 0
    for i, (p, bid, key) in enumerate(brand_updates, 1):
        if bid < 0:
            continue
        st, resp = http_json(
            "PUT", f"{API}/products/{p['id']}", data={"brand_id": bid}, headers=auth
        )
        if st in (200, 201):
            b_ok += 1
        else:
            b_fail += 1
            failures.append(f"brand {p.get('sku')}: {st} {resp}")
        if i % 40 == 0:
            print(f"[rem] brands {i}/{len(brand_updates)}")
        time.sleep(args.sleep)
    print(f"[rem] brands done ok={b_ok} fail={b_fail}")

    c_ok = c_fail = 0
    for c, new_name in cat_renames:
        st, resp = http_json(
            "PUT", f"{API}/categories/{c['id']}", data={"name": new_name}, headers=auth
        )
        if st in (200, 201):
            c_ok += 1
            print(f"[cat] {c['id']} {c['name']} → {new_name}")
        else:
            alt = f"استاندارد ({c['id']})"
            st2, resp2 = http_json(
                "PUT", f"{API}/categories/{c['id']}", data={"name": alt}, headers=auth
            )
            if st2 in (200, 201):
                c_ok += 1
                print(f"[cat] {c['id']} → {alt}")
            else:
                c_fail += 1
                failures.append(f"cat {c['id']}: {st} {resp}")
                print(f"[cat] FAIL {c['id']}: {st} {resp}")
        time.sleep(0.05)
    print(f"[rem] cats done ok={c_ok} fail={c_fail}")

    report = {
        "name_clean": len(cleanable),
        "garbage_rename": len(garbage_fixes),
        "sku_ok": sku_ok,
        "sku_fail": sku_fail,
        "brand_ok": b_ok,
        "brand_fail": b_fail,
        "cat_ok": c_ok,
        "cat_fail": c_fail,
        "failures": failures[:100],
    }
    Path("data/remediation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("[rem] DONE", {k: v for k, v in report.items() if k != "failures"})
    if failures:
        print(f"[rem] failures={len(failures)} (see report)")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
