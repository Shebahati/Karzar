#!/usr/bin/env python3
"""Enrich INSIZE products from official catalogue 108A (2025–2027) — CONTENT ONLY.

HARD CONSTRAINT: never read or write price / stock / availability / commerce money fields.
Allowed writes: short_description, description, meta_title, meta_description, specifications.

Matching is very-high-confidence only (exact catalog Code No., or unambiguous single
letter-suffix variant such as site 1111-100 → catalog 1111-100A).

v2 rules (locked JSON schema / measurement template):
  - Never invent numeric specs; unknown → omit / false / []
  - Accuracy ≠ Resolution
  - Long description is editorial only — NEVER bullet-list specs
  - Rewrite prior specs-echo long descriptions on rematch
  - Measurement technical keys only (EN canonical); omit unknown / zero dimensions
  - Never write base_price / is_available

Usage (from backend root):
  python scripts/enrich_insize_from_catalog_108A.py index
  python scripts/enrich_insize_from_catalog_108A.py match --refresh-site
  python scripts/enrich_insize_from_catalog_108A.py dry-run
  python scripts/enrich_insize_from_catalog_108A.py apply --apply-confirm --force --rebuild

PDF (must exist):
  /home/moahmmad/Downloads/Telegram Desktop/INSIZE-Dimensional-Metrology-108A-2025-2027.pdf
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any

API = os.getenv("KARZAR_API_BASE", "https://api.karzartools.com/api/v1")
INSIZE_BRAND_ID = 3
UA = "KarzarInsizeCatalog108AEnrich/1.0"
CATALOG_EDITION = "108A-2025-2027"
DEFAULT_PDF = Path(
    "/home/moahmmad/Downloads/Telegram Desktop/"
    "INSIZE-Dimensional-Metrology-108A-2025-2027.pdf"
)
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "imports" / "insize" / "catalog_108A"
PDF_TEXT = OUT / "pdf_text_full.txt"
CATALOG_INDEX = OUT / "catalog_index.json"
SITE_LIST = OUT / "site_list.json"
SITE_INVENTORY = OUT / "site_inventory.json"
MATCHED_CSV = OUT / "matched.csv"
REJECTED_CSV = OUT / "rejected.csv"
APPLIED_CSV = OUT / "applied.csv"
DRY_RUN_JSON = OUT / "dry_run_payloads.json"

# --- Content-only contract (never include commerce fields) ---
CONTENT_FIELDS = frozenset(
    {
        "short_description",
        "description",
        "meta_title",
        "meta_description",
        "specifications",
    }
)
FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "base_price",
        "original_price",
        "price",
        "sale_price",
        "list_price",
        "discount",
        "discount_percent",
        "tax_percent",
        "stock_quantity",
        "stock_unit",
        "is_available",
        "availability",
        "stock_status",
        "currency",
    }
)

# Locked measurement template technical_specs keys (English canonical only).
MEASUREMENT_TECH_KEYS = (
    "range",
    "accuracy",
    "resolution",
    "material",
    "standard",
    "battery_type",
)

# Persian labels sometimes present in legacy rows — map back to EN canonical.
FA_TO_EN = {
    "بازه اندازه‌گیری": "range",
    "بازه": "range",
    "دقت": "accuracy",
    "تفکیک‌پذیری": "resolution",
    "رزولوشن": "resolution",
    "درجه بندی": "resolution",
    "جنس": "material",
    "متریال": "material",
    "استاندارد": "standard",
    "باتری": "battery_type",
    "نوع باتری": "battery_type",
    "استاندارد باتری": "battery_type",
}

COUNTRY_LIKE_MATERIAL = re.compile(
    r"^(چین|china|japan|ژاپن|germany|آلمان|taiwan|تایوان|usa|آمریکا)$",
    re.I,
)

SERIES_FA = {
    "DIGITAL CALIPER": "کولیس دیجیتال",
    "DIGITAL CALIPERS": "کولیس دیجیتال",
    "VERNIER CALIPER": "کولیس ورنیه",
    "VERNIER CALIPERS": "کولیس ورنیه",
    "OUTSIDE MICROMETER": "میکرومتر خارجی",
    "OUTSIDE MICROMETERS": "میکرومتر خارجی",
    "INSIDE MICROMETER": "میکرومتر داخلی",
    "DEPTH MICROMETER": "میکرومتر عمق",
    "DIAL INDICATOR": "ساعت اندیکاتور",
    "HEIGHT GAUGE": "ارتفاع‌سنج",
    "DEPTH GAUGE": "عمق‌سنج",
    "DIGITAL HEIGHT GAUGE": "ارتفاع‌سنج دیجیتال",
    "FEELER GAUGE": "فیلر",
    "FLEXIBLE RULER": "خط‌کش انعطاف‌پذیر",
    "CHAMFER GAUGE": "گیج پخ",
}

SPECS_ECHO_MARKERS = (
    "مشخصات طبق کاتالوگ",
    "مشخصات طبق کاتالوگ رسمی",
)



def _clean(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip(" .;,\t*")


def _norm_sku(sku: str | None) -> str:
    return _clean(sku).upper().replace(" ", "").replace("_", "-")


def assert_content_only(payload: dict[str, Any]) -> None:
    bad = sorted(set(payload) & FORBIDDEN_PAYLOAD_KEYS)
    if bad:
        raise RuntimeError(f"Refusing payload with forbidden commerce keys: {bad}")
    extra = sorted(set(payload) - CONTENT_FIELDS)
    if extra:
        raise RuntimeError(f"Refusing non-content keys in update payload: {extra}")


def http_json(method: str, url: str, *, data=None, headers=None, timeout=90, retries: int = 4):
    body = None
    hdrs = {"User-Agent": UA, "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    last_err: Exception | None = None
    for attempt in range(retries):
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
        except Exception as e:  # noqa: BLE001 — retry transient network failures
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"HTTP {method} {url} failed after {retries} tries: {last_err}")


def _load_admin_creds() -> tuple[str, str]:
    phone = os.getenv("INITIAL_SUPER_ADMIN_PHONE")
    password = os.getenv("INITIAL_SUPER_ADMIN_PASSWORD")
    secrets = ROOT / ".deploy-secrets"
    if secrets.exists():
        for line in secrets.read_text(encoding="utf-8").splitlines():
            if line.startswith("INITIAL_SUPER_ADMIN_PHONE=") and not phone:
                phone = line.split("=", 1)[1].strip()
            if line.startswith("INITIAL_SUPER_ADMIN_PASSWORD=") and not password:
                password = line.split("=", 1)[1].strip()
    if not phone or not password:
        raise RuntimeError("Set INITIAL_SUPER_ADMIN_PHONE/PASSWORD or use .deploy-secrets")
    return phone, password


def login(*, retries: int = 8) -> str:
    phone, password = _load_admin_creds()
    body = urllib.parse.urlencode({"username": phone, "password": password}).encode()
    last_err: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(
            f"{API}/auth/login",
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "User-Agent": UA,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
            token = data.get("access_token")
            if not token:
                raise RuntimeError("login failed: no access_token")
            return token
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"login failed after {retries} tries: {last_err}")


# ---------------------------------------------------------------------------
# PDF extract + index
# ---------------------------------------------------------------------------


def cmd_extract_pdf(pdf: Path) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not pdf.exists():
        raise SystemExit(f"PDF not found: {pdf}")
    info = subprocess.check_output(["pdfinfo", str(pdf)], text=True)
    pages = int([ln for ln in info.splitlines() if ln.startswith("Pages:")][0].split(":")[1])
    print(f"[extract] pages={pages} → {PDF_TEXT}")
    with PDF_TEXT.open("w", encoding="utf-8") as f:
        chunk = 25
        for start in range(1, pages + 1, chunk):
            end = min(start + chunk - 1, pages)
            text = subprocess.check_output(
                ["pdftotext", "-f", str(start), "-l", str(end), "-layout", str(pdf), "-"],
                text=True,
                errors="replace",
            )
            parts = text.split("\f")
            for i, part in enumerate(parts):
                pdf_page = min(start + i, end)
                f.write(f"\n\n=====PDF_PAGE_{pdf_page}=====\n")
                f.write(part)
            print(f"[extract] {start}-{end}", flush=True)
    print(f"[extract] done size={PDF_TEXT.stat().st_size}")


def _page_map(text: str) -> dict[int, str]:
    page_re = re.compile(r"=====PDF_PAGE_(\d+)=====")
    parts = page_re.split(text)
    pages: dict[int, str] = {}
    for i in range(1, len(parts), 2):
        try:
            n = int(parts[i])
        except ValueError:
            continue
        pages[n] = parts[i + 1] if i + 1 < len(parts) else ""
    return pages


def _parse_rows_from_text(content: str) -> list[tuple[str, str, str, str]]:
    """Return list of (code, range, accuracy, raw)."""
    rows: list[tuple[str, str, str, str]] = []
    # Primary: Code [*] Range Accuracy  (allow unicode mu / micro)
    code = r"(\d{3,5}-\d{1,5}[A-Za-z]{0,4})"
    rng = (
        r"((?:Ø|ф|Ф)?\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?"
        r"(?:mm|µm|μm|um|\"|in|MPa|N|HRC|°)?"
        r"(?:\s*/\s*(?:Ø|ф|Ф)?[\d\.\-]+(?:mm|µm|μm|um|\"|in)?)?)"
    )
    acc = r"([±+\-]\s*\d+(?:\.\d+)?\s*(?:mm|µm|μm|um|\"|in)?)"
    primary = re.compile(rf"(?<![A-Za-z0-9]){code}\s*\*?\s+{rng}\s+{acc}", re.I)
    for m in primary.finditer(content):
        rows.append((_norm_sku(m.group(1)), _clean(m.group(2)), _clean(m.group(3)), _clean(m.group(0))[:140]))

    # Circumference-style: Code range Ørange ±acc ±acc
    circ = re.compile(
        rf"(?<![A-Za-z0-9]){code}\s+(\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?mm)\s+"
        rf"((?:Ø|ф|Ф)\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?mm)\s+"
        rf"([±+\-]\s*\d+(?:\.\d+)?mm)\s+([±+\-]\s*\d+(?:\.\d+)?mm)",
        re.I,
    )
    for m in circ.finditer(content):
        rows.append(
            (
                _norm_sku(m.group(1)),
                f"{_clean(m.group(2))} / {_clean(m.group(3))}",
                f"circumference {_clean(m.group(4))}; diameter {_clean(m.group(5))}",
                _clean(m.group(0))[:140],
            )
        )
    return rows


def _page_meta(content: str) -> dict[str, Any]:
    series = ""
    for line in content.splitlines()[:30]:
        ls = line.strip()
        if len(ls) >= 10 and ls.isupper() and any(c.isalpha() for c in ls):
            if "PAGE" in ls or ls.startswith("====="):
                continue
            series = _clean(ls)
            # drop trailing DATA/OUTPUT noise
            series = re.sub(r"\s+(DATA|OUTPUT|VIDEO|ATTENTION:?)\s*$", "", series, flags=re.I)
            series = re.sub(r"\s{2,}.*$", "", series)
            break

    def _looks_like_measure(val: str) -> bool:
        v = val.casefold()
        if not re.search(r"\d", v):
            return False
        # Reject column headers / noise words accidentally captured
        if re.fullmatch(r"(range|accuracy|code|type|remark|page|unit)", v):
            return False
        return bool(re.search(r"(mm|µm|μm|um|\"|in|°)", v, re.I)) or bool(
            re.search(r"\d+\.\d+", v)
        )

    resolution = ""
    graduation = ""
    for m in re.finditer(r"(Resolution|Graduation)\s*[:：]?\s*([^\n]{3,50})", content, re.I):
        val = _clean(m.group(2))
        val = re.split(r"\s{2,}", val)[0]
        if not _looks_like_measure(val):
            continue
        if m.group(1).lower().startswith("grad"):
            graduation = val
            if not resolution:
                resolution = val
        else:
            resolution = val

    battery = ""
    bm = re.search(r"Battery\s+(CR\d+|LR\d+|SR\d+|AAA|AA)\b", content, re.I)
    if bm:
        battery = bm.group(1).upper()

    standard = ""
    sm = re.search(r"(?:Meet|According to|Conforms to)\s+(DIN\s*\d+[A-Za-z0-9\-]*|ISO\s*[\d\-]+)", content, re.I)
    if sm:
        standard = _clean(sm.group(1))

    material = ""
    mm = re.search(r"Made of\s+([^\n]{5,50})", content, re.I)
    if mm:
        material = _clean(re.split(r"\s{2,}", mm.group(1))[0])

    force = ""
    fm = re.search(r"Measuring\s+force\s*[:：]?\s*([^\n]{3,40})", content, re.I)
    if fm:
        force = _clean(re.split(r"\s{2,}", fm.group(1))[0])

    features: list[str] = []
    for line in content.splitlines():
        ls = line.strip()
        if re.match(
            r"^(Non waterproof|Waterproof|Absolute system|Buttons:|Automatic power|Data output|"
            r"IP\d+|Ratchet|Friction|Carbide|Digital readout|Satin chrome)",
            ls,
            re.I,
        ):
            features.append(_clean(re.split(r"\s{2,}", ls)[0]))
    features = list(dict.fromkeys(features))[:10]

    return {
        "series": series,
        "resolution": resolution,
        "graduation": graduation,
        "battery": battery,
        "standard": standard,
        "material": material,
        "measuring_force": force,
        "features": features,
    }


def build_catalog_index() -> dict[str, Any]:
    if not PDF_TEXT.exists():
        raise SystemExit(f"Missing {PDF_TEXT}; run: extract")
    text = PDF_TEXT.read_text(encoding="utf-8", errors="replace")
    pages = _page_map(text)
    entries: dict[str, dict[str, Any]] = {}
    ambiguous: dict[str, int] = {}

    # Whole-document row pass (more complete than per-page alone)
    for code, rng, acc, raw in _parse_rows_from_text(text):
        rec = {
            "code": code,
            "range": rng,
            "accuracy": acc,
            "resolution": "",
            "graduation": "",
            "battery": "",
            "measuring_force": "",
            "standard": "",
            "material": "",
            "series": "",
            "features": [],
            "pdf_page": None,
            "raw_row": raw,
            "catalog_edition": CATALOG_EDITION,
        }
        if code in entries:
            prev = entries[code]
            if prev.get("range") and rng and prev["range"] != rng and prev.get("accuracy") != acc:
                ambiguous[code] = ambiguous.get(code, 0) + 1
                continue
            for k, v in rec.items():
                if v and not prev.get(k):
                    prev[k] = v
        else:
            entries[code] = rec

    # Attach page-level meta by scanning pages
    for page_no, content in pages.items():
        meta = _page_meta(content)
        for code, rng, acc, raw in _parse_rows_from_text(content):
            if code not in entries:
                entries[code] = {
                    "code": code,
                    "range": rng,
                    "accuracy": acc,
                    "resolution": "",
                    "graduation": "",
                    "battery": "",
                    "measuring_force": "",
                    "standard": "",
                    "material": "",
                    "series": "",
                    "features": [],
                    "pdf_page": page_no,
                    "raw_row": raw,
                    "catalog_edition": CATALOG_EDITION,
                }
            ent = entries[code]
            if ent.get("pdf_page") is None:
                ent["pdf_page"] = page_no
            for k in ("series", "resolution", "graduation", "battery", "standard", "material", "measuring_force"):
                if meta.get(k) and not ent.get(k):
                    ent[k] = meta[k]
            if meta.get("features"):
                ent["features"] = list(dict.fromkeys((ent.get("features") or []) + meta["features"]))[:10]

    payload = {
        "edition": CATALOG_EDITION,
        "count": len(entries),
        "ambiguous_conflict_count": len(ambiguous),
        "entries": entries,
        "ambiguous": ambiguous,
    }
    CATALOG_INDEX.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[index] entries={len(entries)} ambiguous={len(ambiguous)} → {CATALOG_INDEX}")
    return payload


# ---------------------------------------------------------------------------
# Site inventory (public API — no commerce fields stored for enrichment logic)
# ---------------------------------------------------------------------------


def fetch_site_list() -> list[dict[str, Any]]:
    OUT.mkdir(parents=True, exist_ok=True)
    products: list[dict[str, Any]] = []
    skip = 0
    while True:
        st, page = http_json("GET", f"{API}/products/?brand_id={INSIZE_BRAND_ID}&skip={skip}&limit=100")
        if st != 200:
            raise RuntimeError(f"list failed {st} {page}")
        batch = page.get("data") or []
        # Drop commerce fields immediately — we do not use them
        for p in batch:
            products.append(
                {
                    "id": p.get("id"),
                    "sku": _norm_sku(p.get("sku")),
                    "name": p.get("name"),
                    "slug": p.get("slug"),
                    "short_description": p.get("short_description"),
                    "category_name": (p.get("category") or {}).get("name")
                    if isinstance(p.get("category"), dict)
                    else None,
                }
            )
        total = (page.get("meta") or {}).get("total_count")
        skip += len(batch)
        print(f"[site] listed {skip}/{total}", flush=True)
        if not batch or (total is not None and skip >= int(total)):
            break
    SITE_LIST.write_text(
        json.dumps({"total": len(products), "products": products}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return products


def fetch_product_detail(product_id: int, auth: dict | None = None) -> dict[str, Any]:
    headers = dict(auth or {})
    st, raw = http_json("GET", f"{API}/products/{product_id}", headers=headers)
    if st != 200:
        raise RuntimeError(f"detail {product_id} failed {st}")
    body = raw
    if isinstance(raw.get("data"), dict) and "sku" in raw["data"]:
        body = raw["data"]
    # Strip commerce fields from in-memory detail used for merge decisions
    return {
        "id": body.get("id"),
        "sku": _norm_sku(body.get("sku")),
        "name": body.get("name"),
        "slug": body.get("slug"),
        "short_description": body.get("short_description"),
        "description": body.get("description"),
        "meta_title": body.get("meta_title"),
        "meta_description": body.get("meta_description"),
        "specifications": body.get("specifications") or {},
        "category_name": (body.get("category") or {}).get("name")
        if isinstance(body.get("category"), dict)
        else None,
    }


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------


def _sku_base(sku: str) -> str:
    return re.sub(r"[A-Z]+$", "", sku)


def match_site_to_catalog(
    site_products: list[dict[str, Any]],
    catalog: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_base: dict[str, list[str]] = defaultdict(list)
    for code in catalog:
        by_base[_sku_base(code)].append(code)

    matched: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for p in site_products:
        sku = _norm_sku(p.get("sku"))
        if not sku:
            rejected.append({**p, "reason": "empty_sku", "confidence": "none"})
            continue

        if sku in catalog:
            matched.append(
                {
                    **p,
                    "catalog_code": sku,
                    "confidence": "very_high",
                    "match_rule": "exact_code",
                    "catalog": catalog[sku],
                }
            )
            continue

        # Site bare code → exactly one catalog lettered variant (e.g. 1111-100 → 1111-100A)
        cands = [c for c in by_base.get(sku, []) if c != sku]
        if len(cands) == 1:
            matched.append(
                {
                    **p,
                    "catalog_code": cands[0],
                    "confidence": "very_high",
                    "match_rule": "unique_letter_suffix",
                    "catalog": catalog[cands[0]],
                }
            )
            continue
        if len(cands) > 1:
            rejected.append(
                {
                    **p,
                    "reason": "ambiguous_letter_suffixes",
                    "candidates": ",".join(sorted(cands)[:12]),
                    "confidence": "low",
                }
            )
            continue

        # Site has letter suffix but catalog only has exact? already handled.
        # Site lettered, catalog missing that letter → reject (do not fall back to base)
        base = _sku_base(sku)
        if base != sku and base in catalog:
            rejected.append(
                {
                    **p,
                    "reason": "site_suffix_catalog_base_only_refuse",
                    "candidates": base,
                    "confidence": "low",
                }
            )
            continue

        # Presence-only (code mentioned but no table row) — still reject for enrichment
        # unless we have a catalog entry (we don't).
        rejected.append({**p, "reason": "not_in_catalog_index", "confidence": "none"})

    return matched, rejected


def write_match_csvs(matched: list[dict], rejected: list[dict]) -> None:
    with MATCHED_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "sku",
                "catalog_code",
                "confidence",
                "match_rule",
                "name",
                "range",
                "accuracy",
                "resolution",
                "series",
                "pdf_page",
            ],
        )
        w.writeheader()
        for m in matched:
            cat = m.get("catalog") or {}
            w.writerow(
                {
                    "id": m.get("id"),
                    "sku": m.get("sku"),
                    "catalog_code": m.get("catalog_code"),
                    "confidence": m.get("confidence"),
                    "match_rule": m.get("match_rule"),
                    "name": m.get("name"),
                    "range": cat.get("range"),
                    "accuracy": cat.get("accuracy"),
                    "resolution": cat.get("resolution"),
                    "series": cat.get("series"),
                    "pdf_page": cat.get("pdf_page"),
                }
            )
    with REJECTED_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["id", "sku", "name", "reason", "candidates", "confidence"],
        )
        w.writeheader()
        for r in rejected:
            w.writerow(
                {
                    "id": r.get("id"),
                    "sku": r.get("sku"),
                    "name": r.get("name"),
                    "reason": r.get("reason"),
                    "candidates": r.get("candidates", ""),
                    "confidence": r.get("confidence"),
                }
            )
    print(f"[match] matched={len(matched)} rejected={len(rejected)}")
    print(f"[match] → {MATCHED_CSV}")
    print(f"[match] → {REJECTED_CSV}")


# ---------------------------------------------------------------------------
# Content builders (facts only — locked measurement schema)
# ---------------------------------------------------------------------------


def _tech_as_dict(specs: Any) -> dict[str, str]:
    if not isinstance(specs, dict):
        return {}
    tech = specs.get("technical_specs")
    out: dict[str, str] = {}
    if isinstance(tech, dict):
        for k, v in tech.items():
            if v is None or v is False or v == "":
                continue
            out[str(k)] = _clean(str(v))
    elif isinstance(tech, list):
        for row in tech:
            if not isinstance(row, dict):
                continue
            k = _clean(str(row.get("key") or ""))
            v = _clean(str(row.get("value") or ""))
            if k and v:
                out[k] = v
    return out


def _is_stub(text: str | None, name: str | None = None) -> bool:
    body = _clean(text)
    if not body or len(body) < 40:
        return True
    n = _clean(name)
    if n and body.casefold() == n.casefold():
        return True
    if n and body.casefold().startswith(n.casefold()) and len(body) <= len(n) + 8:
        return True
    return False


def is_specs_echo_description(text: str | None) -> bool:
    """True when long description is a bullet dump of specs (v1 anti-pattern)."""
    body = text or ""
    if not body.strip():
        return False
    for marker in SPECS_ECHO_MARKERS:
        if marker in body:
            return True
    bullet_lines = re.findall(r"(?m)^-\s+.+$", body)
    if len(bullet_lines) >= 3:
        joined = "\n".join(bullet_lines)
        if any(
            token in joined
            for token in (
                "بازه",
                "دقت",
                "تفکیک",
                "رزولوشن",
                "جنس",
                "باتری",
                "استاندارد",
                "Range",
                "Accuracy",
                "Resolution",
            )
        ):
            return True
    return False


def _series_fa(series: str) -> str:
    s = _clean(series).upper()
    for en, fa in SERIES_FA.items():
        if en in s:
            return fa
    if s:
        return series.title() if series == series.upper() else series
    return ""


def _looks_like_accuracy(val: str) -> bool:
    return "±" in val or "+-" in val or val.strip().startswith("+")


def _sanitize_material(val: str | None) -> str:
    v = _clean(val)
    if not v:
        return ""
    if COUNTRY_LIKE_MATERIAL.match(v):
        return ""
    return v[:120]


def build_short_description(name: str, cat: dict[str, Any], category_name: str | None) -> str | None:
    """1–3 factual Persian sentences; numbers only from catalog facts."""
    parts: list[str] = []
    series_fa = _series_fa(cat.get("series") or "")
    if series_fa:
        parts.append(f"{series_fa} برند INSIZE")
    elif category_name:
        parts.append(f"{category_name} برند INSIZE")
    else:
        parts.append("ابزار اندازه‌گیری برند INSIZE")

    facts: list[str] = []
    if cat.get("range"):
        facts.append(f"بازه {_clean(cat['range'])}")
    if cat.get("resolution"):
        facts.append(f"تفکیک‌پذیری {_clean(cat['resolution'])}")
    elif cat.get("graduation"):
        facts.append(f"درجه بندی {_clean(cat['graduation'])}")
    if cat.get("accuracy"):
        facts.append(f"دقت {_clean(cat['accuracy'])}")
    if facts:
        parts.append("؛ ".join(facts[:3]))

    code = cat.get("code")
    if code:
        parts.append(f"کد {code}")
    parts.append(f"بر اساس کاتالوگ INSIZE {CATALOG_EDITION}")

    body = ". ".join(parts) + "."
    if _is_stub(body, name):
        return None
    return body[:500]


def build_long_description(
    name: str,
    cat: dict[str, Any],
    category_name: str | None = None,
) -> str | None:
    """Editorial identity only — NEVER duplicate the specs table as bullets."""
    _ = name
    series_fa = _series_fa(cat.get("series") or "")
    identity = series_fa or (category_name or "").strip() or "ابزار اندازه‌گیری"
    code = _clean(cat.get("code"))
    sentences = [
        f"{identity} برند INSIZE"
        + (f" با کد کاتالوگ {code}" if code else "")
        + ".",
        "مشخصات عددی و ویژگی‌های فنی این مدل فقط در بخش مشخصات فنی همین صفحه آمده است.",
        f"مرجع کاتالوگ رسمی INSIZE {CATALOG_EDITION}؛ برای استعلام موجودی و قیمت با کارزار تولز تماس بگیرید.",
    ]
    return " ".join(sentences)[:4000]


def build_meta_title(name: str, sku: str) -> str:
    base = _clean(name) or f"INSIZE {sku}"
    if "insize" not in base.casefold() and "اینسایز" not in base:
        base = f"{base} | INSIZE"
    return base[:255]


def build_meta_description(short: str | None, name: str, sku: str) -> str:
    if short and not _is_stub(short, name):
        return short[:500]
    return f"{_clean(name) or sku} | مشخصات طبق کاتالوگ INSIZE {CATALOG_EDITION}"[:500]


def _parse_buttons_list(features: list[str]) -> list[str]:
    for feat in features:
        m = re.match(r"^Buttons?\s*:\s*(.+)$", feat, re.I)
        if not m:
            continue
        raw = m.group(1)
        parts = [p.strip(" .") for p in re.split(r"[,;/]| and ", raw) if p.strip(" .")]
        return [p for p in parts if 1 < len(p) < 40][:12]
    return []


def build_measurement_features(cat: dict[str, Any], existing_features: Any) -> dict[str, Any]:
    """Map catalog feature lines → locked measurement feature keys only."""
    base = dict(existing_features) if isinstance(existing_features, dict) else {}
    feat_lines = [str(f) for f in (cat.get("features") or [])]
    joined = " | ".join(feat_lines).lower()

    waterproof = False
    if re.search(r"\bwaterproof\b", joined) and not re.search(r"\bnon\s*waterproof\b", joined):
        waterproof = True
    elif re.search(r"\bip\s*\d+", joined):
        waterproof = True
    elif isinstance(base.get("waterproof"), bool) and "non waterproof" not in joined:
        waterproof = bool(base["waterproof"])
    if "non waterproof" in joined:
        waterproof = False

    data_output = bool(re.search(r"data\s*output", joined))
    if not data_output and isinstance(base.get("data_output"), bool):
        data_output = bool(base["data_output"])

    auto_power_off = bool(re.search(r"automatic\s+power\s*off|auto\s*power\s*off", joined))
    if not auto_power_off and isinstance(base.get("auto_power_off"), bool):
        auto_power_off = bool(base["auto_power_off"])

    buttons_list = _parse_buttons_list(feat_lines)
    if not buttons_list:
        prior = base.get("buttons_list") or base.get("buttons")
        if isinstance(prior, list):
            buttons_list = [str(x).strip() for x in prior if str(x).strip()][:12]
        elif isinstance(prior, str) and prior.strip():
            buttons_list = [p.strip() for p in prior.split(",") if p.strip()][:12]
    has_buttons = bool(buttons_list) or bool(
        re.search(r"^buttons?\s*:", "\n".join(feat_lines), re.I | re.M)
    )

    cert_text = ""
    has_cert = False
    for feat in feat_lines:
        if re.search(
            r"inspection\s+certificate|manufacturer.*certificate|supplied with.*certificate",
            feat,
            re.I,
        ):
            has_cert = True
            cert_text = _clean(feat)[:200]
            break
    if not has_cert:
        prior_cert = base.get("certification_text") or base.get("certification") or ""
        if isinstance(prior_cert, str) and prior_cert.strip():
            has_cert = True
            cert_text = prior_cert.strip()[:200]
        elif base.get("has_certification") is True:
            has_cert = True

    return {
        "waterproof": waterproof,
        "data_output": data_output,
        "auto_power_off": auto_power_off,
        "has_buttons": has_buttons,
        "buttons_list": buttons_list,
        "has_certification": has_cert,
        "certification_text": cert_text if has_cert else "",
    }


def _normalize_dimensions(existing: Any) -> dict[str, Any]:
    """Keep only known non-zero dimension keys; never invent zeros."""
    raw: dict[str, Any] = {}
    if isinstance(existing, dict):
        raw = existing
    elif isinstance(existing, list):
        for row in existing:
            if isinstance(row, dict) and row.get("key") is not None:
                raw[str(row["key"])] = row.get("value")

    allowed = {"L", "a", "b", "c", "d", "L_mm", "a_mm", "b_mm", "c_mm", "d_mm"}
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if k not in allowed:
            continue
        if v is None or v == "" or v is False:
            continue
        try:
            num = float(v)
        except (TypeError, ValueError):
            s = _clean(str(v))
            if s:
                out[k] = s
            continue
        if num == 0.0:
            continue
        out[k] = num
    return out


def merge_specifications(existing: Any, cat: dict[str, Any]) -> dict[str, Any]:
    """Build measurement-template specs from catalog; never invent values."""
    base = deepcopy(existing) if isinstance(existing, dict) else {}
    prior = _tech_as_dict(base)

    prior_en: dict[str, str] = {}
    for k, v in prior.items():
        en = FA_TO_EN.get(k, k)
        if en in MEASUREMENT_TECH_KEYS and v and not COUNTRY_LIKE_MATERIAL.match(v):
            if en == "accuracy" and not _looks_like_accuracy(v) and en in prior_en:
                continue
            if en == "resolution" and _looks_like_accuracy(v):
                continue
            if en not in prior_en:
                prior_en[en] = v
            elif en == "material" and COUNTRY_LIKE_MATERIAL.match(prior_en[en]):
                prior_en[en] = v

    resolution = _clean(cat.get("resolution") or "")
    if not resolution:
        resolution = _clean(cat.get("graduation") or "")

    incoming: dict[str, str] = {}
    if cat.get("range"):
        incoming["range"] = _clean(cat["range"])
    if cat.get("accuracy"):
        incoming["accuracy"] = _clean(cat["accuracy"])
    if resolution:
        incoming["resolution"] = resolution
    mat = _sanitize_material(cat.get("material"))
    if mat:
        incoming["material"] = mat
    if cat.get("standard"):
        incoming["standard"] = _clean(cat["standard"])
    if cat.get("battery"):
        incoming["battery_type"] = _clean(cat["battery"])

    merged: dict[str, str] = {}
    for key in MEASUREMENT_TECH_KEYS:
        if key in incoming:
            merged[key] = incoming[key]
        elif key in prior_en and prior_en[key]:
            if key == "material" and not _sanitize_material(prior_en[key]):
                continue
            if key == "accuracy" and not _looks_like_accuracy(prior_en[key]):
                continue
            if key == "resolution" and _looks_like_accuracy(prior_en[key]):
                continue
            merged[key] = prior_en[key]

    features = build_measurement_features(cat, base.get("features"))
    dimensions = _normalize_dimensions(base.get("dimensions"))

    out: dict[str, Any] = {
        "technical_specs": merged,
        "features": features,
        "dimensions": dimensions,
        "optional_accessories": base.get("optional_accessories") or [],
    }
    for k, v in base.items():
        if k in out or k in FORBIDDEN_PAYLOAD_KEYS or "price" in str(k).lower():
            continue
        out[k] = v
    return out


def build_content_payload(detail: dict[str, Any], cat: dict[str, Any]) -> dict[str, Any] | None:
    name = detail.get("name") or ""
    sku = detail.get("sku") or cat.get("code") or ""
    category_name = detail.get("category_name")

    short = detail.get("short_description")
    long = detail.get("description")
    meta_title = detail.get("meta_title")
    meta_desc = detail.get("meta_description")

    new_short = build_short_description(name, cat, category_name)
    new_long = build_long_description(name, cat, category_name)
    new_meta_title = build_meta_title(name, sku)
    new_meta_desc = build_meta_description(new_short or short, name, sku)
    new_specs = merge_specifications(detail.get("specifications"), cat)

    payload: dict[str, Any] = {}

    if new_short and (_is_stub(short, name) or not short):
        payload["short_description"] = new_short

    if new_long and (is_specs_echo_description(long) or _is_stub(long, name) or not long):
        payload["description"] = new_long

    if not meta_title:
        payload["meta_title"] = new_meta_title
    if not meta_desc or _is_stub(meta_desc, name) or is_specs_echo_description(meta_desc):
        payload["meta_description"] = new_meta_desc

    old_specs = detail.get("specifications") or {}
    old_collapsed: dict[str, str] = {}
    for k, v in _tech_as_dict(old_specs).items():
        en = FA_TO_EN.get(k, k)
        if en in MEASUREMENT_TECH_KEYS and en not in old_collapsed:
            old_collapsed[en] = v
    new_tech = dict(new_specs.get("technical_specs") or {})

    old_feats = old_specs.get("features") if isinstance(old_specs, dict) else {}
    new_feats = new_specs.get("features") or {}
    old_dims = _normalize_dimensions(
        old_specs.get("dimensions") if isinstance(old_specs, dict) else {}
    )
    new_dims = new_specs.get("dimensions") or {}

    has_fa_dupes = any(k in FA_TO_EN for k in _tech_as_dict(old_specs))
    specs_changed = (
        new_tech != old_collapsed
        or new_feats != (old_feats if isinstance(old_feats, dict) else {})
        or new_dims != old_dims
        or is_specs_echo_description(long)
        or has_fa_dupes
    )
    if specs_changed:
        payload["specifications"] = new_specs

    if not payload:
        return None
    assert_content_only(payload)
    return payload


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_index(args: argparse.Namespace) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if args.extract or not PDF_TEXT.exists():
        cmd_extract_pdf(Path(args.pdf))
    build_catalog_index()
    return 0


def cmd_site(args: argparse.Namespace) -> int:
    products = fetch_site_list()
    print(f"[site] total={len(products)} (commerce fields discarded)")
    return 0


def cmd_match(args: argparse.Namespace) -> int:
    if not CATALOG_INDEX.exists():
        build_catalog_index()
    catalog = json.loads(CATALOG_INDEX.read_text(encoding="utf-8"))["entries"]
    if not SITE_LIST.exists() or args.refresh_site:
        products = fetch_site_list()
    else:
        products = json.loads(SITE_LIST.read_text(encoding="utf-8"))["products"]
    matched, rejected = match_site_to_catalog(products, catalog)
    write_match_csvs(matched, rejected)
    (OUT / "matched.json").write_text(
        json.dumps(
            [
                {
                    "id": m["id"],
                    "sku": m["sku"],
                    "catalog_code": m["catalog_code"],
                    "match_rule": m["match_rule"],
                    "catalog": m["catalog"],
                    "name": m.get("name"),
                    "category_name": m.get("category_name"),
                }
                for m in matched
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


def _iter_matched(limit: int | None) -> list[dict[str, Any]]:
    path = OUT / "matched.json"
    if not path.exists():
        raise SystemExit("Run match first")
    rows = json.loads(path.read_text(encoding="utf-8"))
    if limit is not None:
        rows = rows[:limit]
    return rows


def cmd_dry_run(args: argparse.Namespace) -> int:
    rows = _iter_matched(args.limit)
    payloads = []
    skipped = 0
    for i, row in enumerate(rows):
        detail = fetch_product_detail(int(row["id"]))
        payload = build_content_payload(detail, row["catalog"])
        if not payload:
            skipped += 1
            continue
        assert_content_only(payload)
        desc = payload.get("description") or ""
        if is_specs_echo_description(desc) or re.search(r"(?m)^-\s*(بازه|دقت|تفکیک)", desc):
            raise RuntimeError(f"Refusing specs-echo description for {row['sku']}")
        specs = payload.get("specifications") or {}
        dims = specs.get("dimensions") if isinstance(specs, dict) else {}
        if isinstance(dims, dict):
            for dk, dv in dims.items():
                try:
                    if float(dv) == 0.0:
                        raise RuntimeError(f"Refusing zero dimension {dk} for {row['sku']}")
                except (TypeError, ValueError):
                    pass
        payloads.append(
            {
                "id": row["id"],
                "sku": row["sku"],
                "catalog_code": row["catalog_code"],
                "fields": sorted(payload.keys()),
                "payload": payload,
            }
        )
        if (i + 1) % 25 == 0:
            print(f"[dry-run] prepared {i+1}/{len(rows)}", flush=True)
        time.sleep(args.sleep)

    DRY_RUN_JSON.write_text(
        json.dumps(
            {
                "api": API,
                "edition": CATALOG_EDITION,
                "matched_considered": len(rows),
                "would_update": len(payloads),
                "skipped_no_delta": skipped,
                "content_fields_only": sorted(CONTENT_FIELDS),
                "forbidden_keys_never_sent": sorted(FORBIDDEN_PAYLOAD_KEYS),
                "items": payloads,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"[dry-run] would_update={len(payloads)} skipped={skipped} → {DRY_RUN_JSON}",
    )
    field_counts: dict[str, int] = defaultdict(int)
    for item in payloads:
        for f in item["fields"]:
            field_counts[f] += 1
    print("[dry-run] field counts:", dict(field_counts))
    return 0


APPLIED_FIELDS = [
    "id",
    "sku",
    "catalog_code",
    "fields",
    "status",
    "price_fields_written",
    "error",
]


def _write_applied_csv(rows: list[dict[str, Any]]) -> None:
    with APPLIED_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=APPLIED_FIELDS)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in APPLIED_FIELDS})


def _load_already_ok_ids() -> set[int]:
    if not APPLIED_CSV.exists():
        return set()
    ok_ids: set[int] = set()
    with APPLIED_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if str(row.get("status")) in ("200", "201"):
                try:
                    ok_ids.add(int(row["id"]))
                except (TypeError, ValueError):
                    continue
    return ok_ids


def cmd_apply(args: argparse.Namespace) -> int:
    """Content-only PUT via admin API. Payload keys asserted before every write."""
    if not args.apply_confirm:
        print("Refusing apply without --apply-confirm (safety).", file=sys.stderr)
        return 2

    # Prefer dry-run payloads if present and limit matches intent
    if DRY_RUN_JSON.exists() and not args.rebuild:
        dry = json.loads(DRY_RUN_JSON.read_text(encoding="utf-8"))
        items = dry.get("items") or []
        if args.limit is not None:
            items = items[: args.limit]
    else:
        # Build from match + live details
        rows = _iter_matched(args.limit)
        items = []
        for row in rows:
            detail = fetch_product_detail(int(row["id"]))
            payload = build_content_payload(detail, row["catalog"])
            if payload:
                items.append(
                    {
                        "id": row["id"],
                        "sku": row["sku"],
                        "catalog_code": row["catalog_code"],
                        "fields": sorted(payload.keys()),
                        "payload": payload,
                    }
                )

    already_ok = set() if args.force else _load_already_ok_ids()
    if already_ok:
        before = len(items)
        items = [it for it in items if int(it["id"]) not in already_ok]
        print(f"[apply] resume: skipping {before - len(items)} already-ok ids")
    elif args.force:
        print("[apply] --force: re-applying all planned items (ignore prior applied.csv)")

    print(f"[apply] content-only updates planned={len(items)} api={API}")
    token = login()
    auth = {"Authorization": f"Bearer {token}"}

    applied_rows: list[dict[str, Any]] = []
    if APPLIED_CSV.exists() and not args.force:
        with APPLIED_CSV.open(encoding="utf-8") as f:
            applied_rows = [dict(r) for r in csv.DictReader(f) if str(r.get("status")) in ("200", "201")]

    ok = len(applied_rows)
    fail = 0
    for i, item in enumerate(items):
        payload = item["payload"]
        assert_content_only(payload)
        # Belt-and-suspenders: drop anything forbidden if sneaks in
        payload = {k: v for k, v in payload.items() if k in CONTENT_FIELDS}
        assert_content_only(payload)

        try:
            st, resp = http_json(
                "PUT",
                f"{API}/products/{item['id']}",
                data=payload,
                headers=auth,
                retries=6,
                timeout=120,
            )
        except Exception as exc:  # noqa: BLE001 — continue batch on transient network errors
            fail += 1
            applied_rows.append(
                {
                    "id": item["id"],
                    "sku": item["sku"],
                    "catalog_code": item["catalog_code"],
                    "fields": ",".join(item["fields"]),
                    "status": "error",
                    "price_fields_written": "none",
                    "error": str(exc)[:300],
                }
            )
            print(f"[apply] ERROR {item['sku']}: {exc}", flush=True)
            _write_applied_csv(applied_rows)
            time.sleep(max(args.sleep, 1.5))
            # refresh token periodically after errors
            if fail % 5 == 0:
                token = login()
                auth = {"Authorization": f"Bearer {token}"}
            continue

        if st in (200, 201):
            ok += 1
            applied_rows.append(
                {
                    "id": item["id"],
                    "sku": item["sku"],
                    "catalog_code": item["catalog_code"],
                    "fields": ",".join(item["fields"]),
                    "status": st,
                    "price_fields_written": "none",
                }
            )
        else:
            fail += 1
            applied_rows.append(
                {
                    "id": item["id"],
                    "sku": item["sku"],
                    "catalog_code": item["catalog_code"],
                    "fields": ",".join(item["fields"]),
                    "status": st,
                    "price_fields_written": "none",
                    "error": str(resp)[:300],
                }
            )
            if fail <= 15:
                print(f"[apply] FAIL {item['sku']}: {st}", flush=True)
            if st in (401, 403):
                token = login()
                auth = {"Authorization": f"Bearer {token}"}
        if (i + 1) % 20 == 0:
            print(f"[apply] progress {i+1}/{len(items)} ok={ok} fail={fail}", flush=True)
            _write_applied_csv(applied_rows)
        time.sleep(args.sleep)

    _write_applied_csv(applied_rows)

    summary = {
        "ok": ok,
        "fail": fail,
        "planned": len(items) + len(already_ok),
        "resumed_skipped": len(already_ok),
        "price_fields_written": 0,
        "content_fields_only": True,
        "applied_csv": str(APPLIED_CSV),
    }
    (OUT / "apply_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[apply] DONE {summary}")
    return 0 if fail == 0 else 1


def cmd_qa(args: argparse.Namespace) -> int:
    """Sample ≥N applied/matched products via public API (content fields only)."""
    sample_n = args.limit or 20
    if APPLIED_CSV.exists():
        with APPLIED_CSV.open(encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if str(r.get("status")) in ("200", "201")]
    else:
        rows = [
            {"id": str(r["id"]), "sku": r["sku"]}
            for r in json.loads((OUT / "matched.json").read_text(encoding="utf-8"))
        ]
    rows = rows[:sample_n]
    report = []
    echo_count = 0
    zero_dim_count = 0
    for r in rows:
        d = fetch_product_detail(int(r["id"]))
        desc = d.get("description") or ""
        echo = is_specs_echo_description(desc)
        if echo:
            echo_count += 1
        dims = _normalize_dimensions(
            (d.get("specifications") or {}).get("dimensions")
            if isinstance(d.get("specifications"), dict)
            else {}
        )
        raw_dims = (
            (d.get("specifications") or {}).get("dimensions")
            if isinstance(d.get("specifications"), dict)
            else []
        )
        has_zero = False
        if isinstance(raw_dims, list):
            for row in raw_dims:
                if isinstance(row, dict):
                    try:
                        if float(row.get("value")) == 0.0:
                            has_zero = True
                    except (TypeError, ValueError):
                        pass
        if has_zero:
            zero_dim_count += 1
        tech = _tech_as_dict(d.get("specifications"))
        report.append(
            {
                "id": d["id"],
                "sku": d["sku"],
                "short_len": len(d.get("short_description") or ""),
                "long_len": len(desc),
                "specs_echo_description": echo,
                "zero_dimensions_present": has_zero,
                "has_meta_title": bool(d.get("meta_title")),
                "has_meta_description": bool(d.get("meta_description")),
                "tech_keys": sorted(tech.keys()),
                "short_preview": (d.get("short_description") or "")[:120],
                "long_preview": desc[:160],
                "kept_dimensions": dims,
            }
        )
        time.sleep(args.sleep)
    out = OUT / "qa_sample.json"
    summary = {
        "sampled": len(report),
        "specs_echo_descriptions": echo_count,
        "zero_dimensions_present": zero_dim_count,
        "sample": report,
    }
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"[qa] sampled={len(report)} specs_echo={echo_count} zero_dims={zero_dim_count} → {out}",
    )
    for row in report[:5]:
        print(
            f"  {row['sku']}: short={row['short_len']} long={row['long_len']} "
            f"echo={row['specs_echo_description']} meta_t={row['has_meta_title']}"
        )
    return 0 if echo_count == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "command",
        choices=["extract", "index", "site", "match", "dry-run", "apply", "qa", "all-dry"],
    )
    ap.add_argument("--pdf", default=str(DEFAULT_PDF))
    ap.add_argument("--extract", action="store_true", help="Force PDF re-extract before index")
    ap.add_argument("--refresh-site", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--sleep", type=float, default=0.05)
    ap.add_argument(
        "--apply-confirm",
        action="store_true",
        help="Required for apply; content-only PUTs, zero price fields",
    )
    ap.add_argument("--rebuild", action="store_true", help="Rebuild payloads on apply")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Re-apply even if id already succeeded in applied.csv (v2 rewrite)",
    )
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    if args.command == "extract":
        cmd_extract_pdf(Path(args.pdf))
        return 0
    if args.command == "index":
        return cmd_index(args)
    if args.command == "site":
        return cmd_site(args)
    if args.command == "match":
        return cmd_match(args)
    if args.command == "dry-run":
        return cmd_dry_run(args)
    if args.command == "apply":
        return cmd_apply(args)
    if args.command == "qa":
        return cmd_qa(args)
    if args.command == "all-dry":
        args.extract = args.extract or not PDF_TEXT.exists()
        cmd_index(args)
        cmd_site(args)
        cmd_match(args)
        return cmd_dry_run(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
