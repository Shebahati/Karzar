#!/usr/bin/env python3
"""Enrich Mitutoyo products from official EU leaflets (exact SKU match only).

Source of truth: PDFs under data/imports/mitutoyo/leaflets_eu/pdfs/
(official shop.mitutoyo.eu DO/base + mitutoyo.eu application/files mirrors).

HARD CONSTRAINT — never read or write commerce money / stock fields:
  Forbidden in any PATCH body or report payload used for writes:
    price, base_price, original_price, sale_price, list_price, discount,
    stock_quantity, is_available, availability
  Allowed only:
    short_description, description, meta_title, meta_description, specifications

Policy:
  - Very-high SKU match: exact order-No. token as on site (no prefix/suffix guessing)
  - No invented accuracy / range / ISO — only values adjacent to that SKU in PDF text
  - Separate short_description; fill meta_*; merge technical_specs carefully
    (fill empty keys; conflict → reject that key, never silent overwrite)
  - Persian factual copy from catalog facts only (Fact-check gate)
  - Staging writes; --dry-run default; --apply requires explicit flag + admin token

Usage:
  .venv/bin/python scripts/enrich_mitutoyo_from_leaflets.py --dry-run
  .venv/bin/python scripts/enrich_mitutoyo_from_leaflets.py --apply --token "$TOKEN"
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
from copy import deepcopy
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "data" / "imports" / "mitutoyo" / "leaflets_eu"
PDF_DIR = OUT_DIR / "pdfs"
REPORT_DIR = OUT_DIR / "reports"
SITE_EXPORT = PROJECT_ROOT / "data" / "imports" / "mitutoyo" / "site_mitutoyo_export_noprice.json"

API = os.getenv("KARZAR_API_BASE", "http://127.0.0.1:8000/api/v1").rstrip("/")
UA = "KarzarMitutoyoLeafletEnrich/1.0"
MITUTOYO_BRAND_ID = 2

# --- hard commerce forbid list (names + regex for PDF scrubbing) ---
FORBIDDEN_WRITE_KEYS = frozenset(
    {
        "price",
        "base_price",
        "original_price",
        "sale_price",
        "list_price",
        "discount",
        "discount_percent",
        "stock_quantity",
        "stock_unit",
        "is_available",
        "availability",
        "stock_status",
    }
)
ALLOWED_WRITE_KEYS = frozenset(
    {
        "short_description",
        "description",
        "meta_title",
        "meta_description",
        "specifications",
    }
)

PRICE_TOKEN_RE = re.compile(
    r"(?i)(?:list\s*price|promotion\s*price|price\s*€|€\s*[\d.,]+|[\d.,]+\s*€|"
    r"\bEUR\b|\bUSD\b|toman|ریال|تومان)"
)

# Exact Mitutoyo order / accessory tokens commonly used as SKUs on site
ORDER_TOKEN_RE = re.compile(
    r"\b("
    r"[0-9]{2,4}-[0-9]{2,4}(?:-[0-9]{1,2})?[A-Z]?"
    r"|[0-9]{6}"
    r"|[0-9]{2}[A-Z]{2,3}[0-9]{2,4}"
    r"|[0-9]{4,5}[A-Z]{1,2}"
    r"|[0-9]{5,7}[A-Z]?"
    r")\b"
)

RANGE_RE = re.compile(
    r"(?<![A-Za-z0-9])("
    r"\d+(?:[.,]\d+)?\s*[-–]\s*\d+(?:[.,]\d+)?\s*(?:mm|in|µm|um)"
    r"|\d+(?:[.,]\d+)?\s*(?:mm|in|µm|um)"
    r")(?![A-Za-z0-9])",
    re.I,
)
ACCURACY_RE = re.compile(
    r"(?<![A-Za-z0-9])("
    r"[±＋]\s*\d+(?:[.,]\d+)?\s*(?:µm|um|mm|μm)"
    r"|Class\s*[IVX0-9]+"
    r")(?![A-Za-z0-9])",
    re.I,
)
RESOLUTION_RE = re.compile(
    r"(?<![A-Za-z0-9])("
    r"0[,.]0+\d+\s*(?:mm|in|µm|um)"
    r"|\d+(?:[.,]\d+)?\s*µm"
    r")(?![A-Za-z0-9])",
    re.I,
)
IP_RE = re.compile(r"\bIP\s*([0-9]{2})\b", re.I)
STANDARD_RE = re.compile(r"\b((?:EN\s*)?ISO\s*\d+(?::\d+)?)\b", re.I)

# Prefer dimensional-metrology leaflets; skip OEM fluff when better sources exist
PDF_PRIORITY = [
    "PRE1563",
    "PRE1504",
    "PRE1569",
    "PRE1564",
    "PRE1582",
    "PRE1515",
    "PRE1441",
    "PRE1533",
    "PRE1278",
    "PRE1604",
    "PRE1502",
    "PRE1429",
]


def assert_no_forbidden(payload: dict[str, Any], *, context: str) -> None:
    bad = sorted(FORBIDDEN_WRITE_KEYS & set(payload.keys()))
    if bad:
        raise RuntimeError(f"{context}: forbidden keys in payload: {bad}")
    extra = sorted(set(payload.keys()) - ALLOWED_WRITE_KEYS)
    if extra:
        raise RuntimeError(f"{context}: non-allowlisted keys: {extra}")


def scrub_price_noise(text: str) -> str:
    """Remove commerce/price tokens from PDF text before fact extraction."""
    cleaned = PRICE_TOKEN_RE.sub(" ", text)
    cleaned = re.sub(r"\b\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?\b", " ", cleaned)
    return cleaned


def sku_token_pattern(sku: str) -> re.Pattern[str]:
    """Exact token: not a prefix of a longer order number."""
    esc = re.escape(sku.upper())
    return re.compile(rf"(?<![0-9A-Z-]){esc}(?![0-9A-Z-])", re.I)


def pdftotext(path: Path) -> str:
    return subprocess.check_output(
        ["pdftotext", "-layout", str(path), "-"],
        stderr=subprocess.DEVNULL,
        text=True,
        errors="ignore",
    )


def pdf_sort_key(path: Path) -> tuple[int, str]:
    name = path.name.upper()
    for idx, code in enumerate(PDF_PRIORITY):
        if code in name:
            return (idx, name)
    return (len(PDF_PRIORITY), name)


def load_site_catalog(path: Path) -> dict[str, dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for row in raw:
        sku = str(row.get("sku") or "").strip().upper()
        if not sku:
            continue
        # Drop any accidental commerce fields from export.
        clean = {
            "id": row.get("id"),
            "sku": sku,
            "name": row.get("name") or "",
            "slug": row.get("slug"),
            "short_description": row.get("short_description"),
            "category": row.get("category"),
            "category_id": row.get("category_id"),
            "brand": row.get("brand") or "Mitutoyo",
            "has_thumb": bool(row.get("has_thumb")),
        }
        for k in FORBIDDEN_WRITE_KEYS:
            clean.pop(k, None)
        out[sku] = clean
    return out


def export_site_if_needed(path: Path) -> None:
    """Read-only public catalog export (no price fields persisted)."""
    if path.exists() and path.stat().st_size > 100:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    skip = 0
    while True:
        q = urllib.parse.urlencode({"brand_id": MITUTOYO_BRAND_ID, "limit": 100, "skip": skip})
        req = urllib.request.Request(
            f"{API}/products/?{q}",
            headers={"User-Agent": UA, "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            page = json.loads(resp.read().decode())
        data = page.get("data") or []
        if not data:
            break
        for r in data:
            brand = r.get("brand") or {}
            if brand.get("id") != MITUTOYO_BRAND_ID and "mitutoyo" not in (
                brand.get("name") or ""
            ).lower():
                continue
            rows.append(
                {
                    "id": r.get("id"),
                    "sku": r.get("sku"),
                    "name": r.get("name"),
                    "slug": r.get("slug"),
                    "short_description": r.get("short_description"),
                    "category": (r.get("category") or {}).get("name"),
                    "category_id": (r.get("category") or {}).get("id"),
                    "brand": brand.get("name"),
                    "has_thumb": bool(r.get("thumbnail")),
                }
            )
        total = int((page.get("meta") or {}).get("total_count") or 0)
        skip += len(data)
        if skip >= total or len(data) < 100:
            break
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[export] wrote {len(rows)} Mitutoyo rows (no price fields) → {path}")


def index_pdfs(pdf_dir: Path) -> dict[str, dict[str, Any]]:
    """Map SKU → best leaflet hit {pdf, context, specs, leaflet_code}."""
    pdfs = sorted(pdf_dir.glob("*.pdf"), key=pdf_sort_key)
    # Deduplicate corp_ twin when same code already present as PRE*
    seen_codes: set[str] = set()
    filtered: list[Path] = []
    for pdf in pdfs:
        m = re.search(r"(PRE\d{4}|E\d{4,5})", pdf.name.upper())
        code = m.group(1) if m else pdf.name.upper()
        if pdf.name.lower().startswith("corp_") and code in seen_codes:
            continue
        seen_codes.add(code)
        filtered.append(pdf)

    # First pass: collect all tokens per pdf
    pdf_texts: list[tuple[Path, str, str]] = []
    for pdf in filtered:
        text = pdftotext(pdf)
        scrubbed = scrub_price_noise(text)
        pdf_texts.append((pdf, text, scrubbed))

    hits: dict[str, dict[str, Any]] = {}
    for pdf, text, scrubbed in pdf_texts:
        tokens = {m.group(1).upper() for m in ORDER_TOKEN_RE.finditer(text)}
        code_m = re.search(r"(PRE\s*\d{4}|E\d{4,5})", pdf.name.upper())
        leaflet = (code_m.group(1).replace(" ", "") if code_m else pdf.stem)[:32]
        for sku in tokens:
            if sku in hits:
                continue  # higher-priority PDF already claimed
            pat = sku_token_pattern(sku)
            m = pat.search(scrubbed)
            if not m:
                m = pat.search(text)
            if not m:
                continue
            start = max(0, m.start() - 220)
            end = min(len(scrubbed), m.end() + 320)
            ctx = scrubbed[start:end]
            specs = extract_specs_from_context(ctx, leaflet=leaflet, sku=sku)
            if not specs or set(specs.keys()) <= {"source_leaflet"}:
                # try raw (still scrubbed prices) wider window
                start = max(0, m.start() - 400)
                end = min(len(scrubbed), m.end() + 500)
                specs = extract_specs_from_context(
                    scrubbed[start:end], leaflet=leaflet, sku=sku
                )
            hits[sku] = {
                "sku": sku,
                "pdf": pdf.name,
                "leaflet": leaflet,
                "context": re.sub(r"\s+", " ", ctx).strip()[:500],
                "specs": specs,
            }
    return hits


def extract_specs_from_context(ctx: str, *, leaflet: str, sku: str | None = None) -> dict[str, str]:
    """Pull only factual metrology fields; never prices."""
    if PRICE_TOKEN_RE.search(ctx) and "€" in ctx:
        ctx = scrub_price_noise(ctx)
    specs: dict[str, str] = {}
    # Prefer explicit labeled fragments when present
    labeled = {
        "range": re.search(
            r"(?i)(?:measuring\s*)?range\s*[:\s]+([0-9.,\s\-–]+(?:mm|in|µm|um)?)", ctx
        ),
        "resolution": re.search(
            r"(?i)(?:digital\s*step|scale\s*graduation|resolution)\s*[:\s]+"
            r"([0-9.,]+\s*(?:mm|in|µm|um)?)",
            ctx,
        ),
        "accuracy": re.search(
            r"(?i)(?:accuracy|max\.?\s*perm(?:issible)?\.?\s*error|e\s*mpe)\s*[:\s]+"
            r"([±＋]?\s*[0-9.,]+\s*(?:µm|um|mm|μm)?|Class\s*\w+)",
            ctx,
        ),
        "standard": re.search(r"(?i)((?:EN\s*)?ISO\s*\d+(?::\d+)?)", ctx),
    }
    for key, match in labeled.items():
        if match:
            val = re.sub(r"\s+", " ", match.group(1)).strip(" :;,.|")
            if val and not PRICE_TOKEN_RE.search(val) and "€" not in val:
                specs[key] = val

    if "range" not in specs:
        m = RANGE_RE.search(ctx)
        if m:
            specs["range"] = re.sub(r"\s+", " ", m.group(1)).strip()
    if "accuracy" not in specs:
        m = ACCURACY_RE.search(ctx)
        if m:
            specs["accuracy"] = re.sub(r"\s+", " ", m.group(1)).strip()
    if "resolution" not in specs:
        # Scale graduation often appears as 0,01 mm near order rows
        m = RESOLUTION_RE.search(ctx)
        if m:
            specs["resolution"] = re.sub(r"\s+", " ", m.group(1)).strip()

    # Reject order-number false positives mistaken for ranges (e.g. "293-251 mm")
    rng = specs.get("range")
    if rng:
        core = re.sub(r"(?i)\s*(mm|in|µm|um|μm)\s*$", "", rng).strip()
        if sku and core.upper() == sku.upper():
            specs.pop("range", None)
        elif re.fullmatch(r"\d{2,4}-\d{2,4}(?:-\d{1,2})?[A-Z]?", core, re.I):
            # Mitutoyo order-No. shape without a clear measuring span → drop
            specs.pop("range", None)

    ip = IP_RE.search(ctx)
    if ip:
        specs["protection"] = f"IP{ip.group(1)}"
    std = STANDARD_RE.search(ctx)
    if std and "standard" not in specs:
        specs["standard"] = std.group(1).replace("  ", " ")

    # data output factual flag from wording (not commerce)
    if re.search(r"(?i)\bdata\s*output\b|\bdigimatic\b", ctx):
        if re.search(r"(?i)\b(?:yes|with)\b.*\bdata\s*output\b|\bdata\s*output\b.*\byes\b", ctx) or re.search(
            r"(?i)with measurement data output", ctx
        ):
            specs["data_output"] = "yes"
        elif re.search(r"(?i)without measurement data output|\bdata\s*output\b.*\bno\b", ctx):
            specs["data_output"] = "no"

    specs["source_leaflet"] = leaflet
    # Drop empty / price-tainted
    return {
        k: v
        for k, v in specs.items()
        if v and "€" not in v and not PRICE_TOKEN_RE.search(v) and "price" not in k.lower()
    }


def merge_technical_specs(
    existing: dict[str, Any] | None, incoming: dict[str, str]
) -> tuple[dict[str, Any], list[str]]:
    """Fill empty keys only; conflicts quarantined."""
    base = deepcopy(existing) if isinstance(existing, dict) else {}
    tech = base.get("technical_specs")
    if isinstance(tech, list):
        tech_map = {
            str(row.get("key")): row.get("value")
            for row in tech
            if isinstance(row, dict) and row.get("key")
        }
    elif isinstance(tech, dict):
        tech_map = {str(k): v for k, v in tech.items()}
    else:
        tech_map = {}

    features = base.get("features") if isinstance(base.get("features"), dict) else {}
    conflicts: list[str] = []
    skip_keys = {"source_leaflet", "data_output"}

    for key, value in incoming.items():
        if key in skip_keys:
            continue
        if key in FORBIDDEN_WRITE_KEYS or "price" in key.lower():
            continue
        old = tech_map.get(key)
        old_s = str(old).strip() if old is not None else ""
        if not old_s or old_s in {"", "0", "0.0", "None"}:
            tech_map[key] = value
        elif old_s.casefold() != value.casefold():
            conflicts.append(f"{key}: existing={old_s!r} leaflet={value!r}")
        # else equal — keep

    if incoming.get("data_output") == "yes":
        features["data_output"] = True
    elif incoming.get("data_output") == "no" and "data_output" not in features:
        features["data_output"] = False

    if incoming.get("protection", "").upper().startswith("IP"):
        features["waterproof"] = True

    base["technical_specs"] = tech_map
    base["features"] = features
    if "dimensions" not in base:
        base["dimensions"] = {}
    if "optional_accessories" not in base:
        base["optional_accessories"] = []
    # provenance (non-commerce)
    evidence = base.get("leaflet_evidence") if isinstance(base.get("leaflet_evidence"), dict) else {}
    evidence["leaflet"] = incoming.get("source_leaflet", "")
    evidence["matched_fields"] = sorted(k for k in incoming if k not in skip_keys)
    base["leaflet_evidence"] = evidence
    return base, conflicts


def fa_short(
    *,
    name: str,
    brand: str,
    category: str | None,
    sku: str,
    specs: dict[str, str],
) -> str | None:
    """Persian short blurb from SoT facts only — no invented claims."""
    parts: list[str] = []
    brand_s = (brand or "Mitutoyo").strip()
    if category:
        parts.append(f"{category} برند {brand_s}")
    else:
        parts.append(f"ابزار اندازه‌گیری برند {brand_s}")
    facts: list[str] = []
    if specs.get("range"):
        facts.append(f"محدوده {specs['range']}")
    if specs.get("resolution"):
        facts.append(f"تفکیک {specs['resolution']}")
    if specs.get("accuracy"):
        facts.append(f"دقت {specs['accuracy']}")
    if specs.get("protection"):
        facts.append(specs["protection"])
    if specs.get("standard"):
        facts.append(specs["standard"])
    if facts:
        parts.append("؛ ".join(facts[:4]))
    parts.append(f"کد سفارش {sku}")
    body = " — ".join(parts)
    if not factcheck_copy(body, specs, sku=sku):
        return None
    return body[:500]


def fa_long(
    *,
    name: str,
    brand: str,
    category: str | None,
    sku: str,
    specs: dict[str, str],
    leaflet: str,
) -> str | None:
    lines = [
        f"{name} محصول اصل برند {brand or 'Mitutoyo'} است.",
    ]
    if category:
        lines.append(f"دسته: {category}.")
    fact_bits = []
    if specs.get("range"):
        fact_bits.append(f"محدوده اندازه‌گیری {specs['range']}")
    if specs.get("resolution"):
        fact_bits.append(f"تفکیک/گام نمایش {specs['resolution']}")
    if specs.get("accuracy"):
        fact_bits.append(f"دقت اعلام‌شده در برگه رسمی {specs['accuracy']}")
    if specs.get("protection"):
        fact_bits.append(f"درجه حفاظت {specs['protection']}")
    if specs.get("standard"):
        fact_bits.append(f"مرجع استاندارد {specs['standard']}")
    if specs.get("data_output") == "yes":
        fact_bits.append("خروجی داده Digimatic طبق برگه فنی")
    if fact_bits:
        lines.append("طبق کاتالوگ/برگه رسمی Mitutoyo: " + "؛ ".join(fact_bits) + ".")
    lines.append(f"شماره سفارش Mitutoyo: {sku}.")
    lines.append(f"منبع مشخصات: برگه رسمی {leaflet} (Mitutoyo EU).")
    lines.append("هیچ مقدار دقت یا محدوده‌ای خارج از برگه رسمی اضافه نشده است.")
    body = "\n".join(lines)
    if not factcheck_copy(body, specs, sku=sku):
        return None
    return body


def fa_meta_title(*, name: str, sku: str) -> str:
    title = f"{name} | {sku} | Mitutoyo"
    return title[:255]


def fa_meta_description(*, short: str | None, specs: dict[str, str], sku: str, name: str) -> str:
    if short:
        return short[:500]
    bits = [name, f"کد {sku}"]
    for k in ("range", "accuracy", "resolution"):
        if specs.get(k):
            bits.append(f"{k}:{specs[k]}")
    return " — ".join(bits)[:500]


def factcheck_copy(text: str, specs: dict[str, str], *, sku: str) -> bool:
    """Reject copy that introduces numeric claims not present in specs/SKU."""
    if PRICE_TOKEN_RE.search(text) or "€" in text or "قیمت" in text:
        return False
    sku_u = sku.upper()
    if sku_u not in text.upper() and f"کد سفارش {sku}" not in text and f"کد {sku}" not in text:
        return False
    # Accuracy claims in copy must match extracted accuracy (if any claim present)
    for m in ACCURACY_RE.finditer(text):
        claimed = re.sub(r"\s+", "", m.group(1)).casefold()
        allowed = re.sub(r"\s+", "", specs.get("accuracy") or "").casefold()
        if not allowed or claimed not in allowed:
            return False
    for m in STANDARD_RE.finditer(text):
        std = re.sub(r"\s+", "", m.group(1)).casefold()
        allowed = re.sub(r"\s+", "", specs.get("standard") or "").casefold()
        if not allowed or std not in allowed:
            return False
    return True


def http_json(
    method: str,
    url: str,
    *,
    data: dict | None = None,
    headers: dict | None = None,
    timeout: float = 90,
    retries: int = 3,
) -> tuple[int, Any]:
    body = None
    hdrs = {"User-Agent": UA, "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    last_err: Exception | None = None
    for attempt in range(max(1, retries)):
        req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                return resp.status, json.loads(raw.decode()) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="ignore")
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {"raw": raw[:500]}
            return exc.code, payload
        except Exception as exc:  # noqa: BLE001 — retry transient network
            last_err = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"HTTP {method} {url} failed after retries: {last_err}")


def admin_get_product(product_id: int, token: str) -> dict:
    st, payload = http_json(
        "GET",
        f"{API}/products/{product_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if st != 200:
        raise RuntimeError(f"GET product {product_id} failed: {st} {payload}")
    # Strip commerce fields from local use
    for k in list(payload.keys()):
        if k in FORBIDDEN_WRITE_KEYS:
            payload.pop(k, None)
    return payload


def build_patch(
    *,
    site_row: dict[str, Any],
    hit: dict[str, Any],
    existing_specs: dict[str, Any] | None,
    existing_short: str | None,
    existing_desc: str | None,
    existing_meta_title: str | None,
    existing_meta_desc: str | None,
    overwrite_text: bool,
) -> tuple[dict[str, Any] | None, str, list[str]]:
    specs_in = dict(hit.get("specs") or {})
    merged, conflicts = merge_technical_specs(existing_specs, specs_in)
    short = fa_short(
        name=site_row["name"],
        brand=str(site_row.get("brand") or "Mitutoyo"),
        category=site_row.get("category"),
        sku=site_row["sku"],
        specs=specs_in,
    )
    long = fa_long(
        name=site_row["name"],
        brand=str(site_row.get("brand") or "Mitutoyo"),
        category=site_row.get("category"),
        sku=site_row["sku"],
        specs=specs_in,
        leaflet=str(hit.get("leaflet") or hit.get("pdf")),
    )
    if not short and not specs_in:
        return None, "no_extractable_facts", conflicts

    patch: dict[str, Any] = {"specifications": merged}
    if short and (overwrite_text or not (existing_short or "").strip()):
        patch["short_description"] = short
        patch["meta_description"] = fa_meta_description(
            short=short, specs=specs_in, sku=site_row["sku"], name=site_row["name"]
        )
        if overwrite_text or not (existing_meta_title or "").strip():
            patch["meta_title"] = fa_meta_title(name=site_row["name"], sku=site_row["sku"])
    if long and (overwrite_text or not (existing_desc or "").strip()):
        patch["description"] = long

    assert_no_forbidden(patch, context=f"build_patch {site_row['sku']}")
    reason = "ok"
    if conflicts:
        reason = "ok_with_spec_conflicts_quarantined"
    return patch, reason, conflicts


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def login_from_env() -> str:
    phone = os.getenv("INITIAL_SUPER_ADMIN_PHONE")
    password = os.getenv("INITIAL_SUPER_ADMIN_PASSWORD")
    secrets = PROJECT_ROOT / ".deploy-secrets"
    if secrets.exists():
        for line in secrets.read_text(encoding="utf-8").splitlines():
            if line.startswith("INITIAL_SUPER_ADMIN_PHONE=") and not phone:
                phone = line.split("=", 1)[1].strip()
            if line.startswith("INITIAL_SUPER_ADMIN_PASSWORD=") and not password:
                password = line.split("=", 1)[1].strip()
    if not phone or not password:
        raise RuntimeError("missing admin creds for --apply (or pass --token)")
    body = urllib.parse.urlencode({"username": phone, "password": password}).encode()
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
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    return data["access_token"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true", help="PATCH staging (allowlisted fields only)")
    parser.add_argument("--token", default="", help="Bearer JWT (else login from env/secrets)")
    parser.add_argument("--pdf-dir", type=Path, default=PDF_DIR)
    parser.add_argument("--site-export", type=Path, default=SITE_EXPORT)
    parser.add_argument("--limit", type=int, default=0, help="Max matched SKUs to process")
    parser.add_argument(
        "--overwrite-text",
        action="store_true",
        help="Replace existing short/long/meta when present (still no prices)",
    )
    parser.add_argument(
        "--fetch-detail",
        action="store_true",
        help="Admin GET before write to merge existing specs (may return commerce fields; they are stripped and never written)",
    )
    parser.add_argument("--sleep", type=float, default=0.08)
    args = parser.parse_args()
    if args.apply:
        args.dry_run = False

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    export_site_if_needed(args.site_export)
    site = load_site_catalog(args.site_export)
    print(f"[site] Mitutoyo SKUs={len(site)} (commerce fields stripped)")

    if not args.pdf_dir.exists():
        print(f"ERROR: missing PDF dir {args.pdf_dir}", file=sys.stderr)
        return 2

    index = index_pdfs(args.pdf_dir)
    print(f"[index] order tokens with contexts={len(index)}")

    matched_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []
    applied_rows: list[dict[str, Any]] = []

    # Reject: site SKUs not exactly in index
    for sku, row in sorted(site.items()):
        if sku not in index:
            rejected_rows.append(
                {
                    "sku": sku,
                    "id": row.get("id"),
                    "reason": "no_exact_sku_in_leaflets",
                    "name": row.get("name"),
                }
            )

    candidates = [(sku, site[sku], index[sku]) for sku in sorted(site) if sku in index]
    if args.limit:
        candidates = candidates[: args.limit]
    print(f"[match] exact SKU hits={len(candidates)}")

    token = ""
    if args.apply:
        token = args.token or login_from_env()

    price_write_attempts = 0  # must remain 0

    for sku, site_row, hit in candidates:
        existing_specs = None
        existing_short = site_row.get("short_description")
        existing_desc = None
        existing_meta_title = None
        existing_meta_desc = None
        # Default: do NOT admin-GET (avoids even reading price/stock fields).
        # Use list export emptiness + fill-empty merge. Opt-in --fetch-detail.
        if args.apply and args.fetch_detail:
            detail = admin_get_product(int(site_row["id"]), token)
            existing_specs = detail.get("specifications")
            existing_short = detail.get("short_description")
            existing_desc = detail.get("description")
            existing_meta_title = detail.get("meta_title")
            existing_meta_desc = detail.get("meta_description")

        patch, reason, conflicts = build_patch(
            site_row=site_row,
            hit=hit,
            existing_specs=existing_specs,
            existing_short=existing_short,
            existing_desc=existing_desc,
            existing_meta_title=existing_meta_title,
            existing_meta_desc=existing_meta_desc,
            overwrite_text=args.overwrite_text,
        )
        rec = {
            "sku": sku,
            "id": site_row.get("id"),
            "name": site_row.get("name"),
            "leaflet": hit.get("leaflet"),
            "pdf": hit.get("pdf"),
            "reason": reason,
            "conflicts": " | ".join(conflicts),
            "specs_json": json.dumps(hit.get("specs") or {}, ensure_ascii=False),
            "short_description": (patch or {}).get("short_description", ""),
            "meta_title": (patch or {}).get("meta_title", ""),
            "patch_keys": ",".join(sorted((patch or {}).keys())),
        }
        if not patch:
            rec["reason"] = reason
            rejected_rows.append(rec)
            continue

        # Final safety: patch keys
        try:
            assert_no_forbidden(patch, context=f"pre-write {sku}")
        except RuntimeError as exc:
            price_write_attempts += 1
            rec["reason"] = f"blocked_forbidden:{exc}"
            rejected_rows.append(rec)
            continue

        matched_rows.append(rec)

        if args.dry_run:
            continue

        # APPLY — allowlisted PATCH only
        st, resp = http_json(
            "PUT",
            f"{API}/products/{site_row['id']}",
            data=patch,
            headers={"Authorization": f"Bearer {token}"},
        )
        # Some deployments use PATCH; try PATCH on 405/422 method issues
        if st in {405, 404}:
            st, resp = http_json(
                "PATCH",
                f"{API}/products/{site_row['id']}",
                data=patch,
                headers={"Authorization": f"Bearer {token}"},
            )
        ok = st in {200, 201}
        applied_rows.append(
            {
                **rec,
                "http_status": st,
                "apply_ok": ok,
                "response_keys": ",".join(sorted(resp.keys())) if isinstance(resp, dict) else "",
            }
        )
        if not ok:
            rejected_rows.append({**rec, "reason": f"apply_failed_{st}", "error": str(resp)[:300]})
        time.sleep(args.sleep)

    # Reports
    matched_csv = REPORT_DIR / "matched.csv"
    rejected_csv = REPORT_DIR / "rejected.csv"
    applied_csv = REPORT_DIR / "applied.csv"
    fields = [
        "sku",
        "id",
        "name",
        "leaflet",
        "pdf",
        "reason",
        "conflicts",
        "specs_json",
        "short_description",
        "meta_title",
        "patch_keys",
        "http_status",
        "apply_ok",
    ]
    write_csv(matched_csv, matched_rows, fields)
    write_csv(rejected_csv, rejected_rows, fields + ["error"])
    write_csv(applied_csv, applied_rows, fields)

    summary = {
        "api": API,
        "mode": "apply" if args.apply else "dry-run",
        "site_skus": len(site),
        "exact_matched": len(matched_rows),
        "rejected": len(rejected_rows),
        "applied_ok": sum(1 for r in applied_rows if r.get("apply_ok")),
        "leaflets_used": sorted({r.get("leaflet") for r in matched_rows if r.get("leaflet")}),
        "pdfs_used": sorted({r.get("pdf") for r in matched_rows if r.get("pdf")}),
        "allowed_write_keys": sorted(ALLOWED_WRITE_KEYS),
        "forbidden_write_keys": sorted(FORBIDDEN_WRITE_KEYS),
        "price_or_stock_write_attempts": price_write_attempts,
        "price_or_stock_writes": 0,
        "reports": {
            "matched": str(matched_csv),
            "rejected": str(rejected_csv),
            "applied": str(applied_csv),
        },
        "notes": [
            "Exact SKU token match only — no 500-155 ↔ 500-155-30 guessing",
            "PDF price columns scrubbed before fact extraction",
            "PATCH/PUT body allowlisted to SEO/specs fields only",
        ],
    }
    summary_path = REPORT_DIR / ("summary_apply.json" if args.apply else "summary_dry_run.json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if price_write_attempts:
        print("ERROR: forbidden field attempts detected", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
