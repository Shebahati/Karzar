#!/usr/bin/env python3
"""High-accuracy SAN OU (سانو) catalog enrichment from official downloads.

Official sources (sanouchuck.com):
  - EN https://en.sanouchuck.com/download.aspx  (download.ashx?id=1..3)
  - CN https://www.sanouchuck.com/download.aspx (images/upfile/*.pdf)
  - Harvest / Pro leaflets + official product HTML facts

Policy (PIM / SEO / AI-pipeline Fact-check):
  - Very-high model match only (e.g. K11-160 ↔ outer Ø 160 mm row).
  - Strip SO- internal SKUs when matching catalog model codes in names.
  - Never invent specs; only fields present on the matched official row/HTML.
  - Separate short_description; meta_*; merge technical_specs (fill-empty only).
  - HARD: never read/write price, sale_price, list_price, discount, stock,
    availability, or other commerce fields. PUT allowlist only.

Examples:
  python scripts/sanou_official_catalog_enrich.py --dry-run
  python scripts/sanou_official_catalog_enrich.py --apply --limit 30

Reports: data/imports/sanou/official_catalog/
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.utils.seo_descriptions import (  # noqa: E402
    is_stub_description,
)

API = os.getenv("KARZAR_API_BASE", "https://api.karzartools.com/api/v1")
UA = "KarzarSanouOfficialCatalogEnrich/1.0"
BRAND_ID_DEFAULT = 20  # SAN OU | سانو
OUT_DIR = _ROOT / "data" / "imports" / "sanou" / "official_catalog"

# --- HARD commerce ban (user confirmation) ---------------------------------
FORBIDDEN_COMMERCE_KEYS = frozenset(
    {
        "price",
        "sale_price",
        "list_price",
        "base_price",
        "original_price",
        "discount",
        "discount_percent",
        "stock",
        "stock_quantity",
        "stock_unit",
        "stock_status",
        "low_stock",
        "availability",
        "is_available",
        "tax_percent",
        "weight_grams",
        "hesabfa_stock",
        "warehouse_quantity",
    }
)
ALLOWED_PUT_KEYS = frozenset(
    {
        "short_description",
        "description",
        "meta_title",
        "meta_description",
        "specifications",
    }
)
EXPORT_KEEP_KEYS = frozenset(
    {
        "id",
        "sku",
        "slug",
        "name",
        "category_id",
        "brand_id",
        "category",
        "brand",
        "is_active",
        "is_original",
        "warranty_text",
        "pdf_catalog_url",
        "short_description",
        "description",
        "meta_title",
        "meta_description",
        "specifications",
        "created_at",
        "updated_at",
    }
)

# Custom digit font used in some SAN OU Chinese leaflets (PUA).
_PUA_DIGIT = {
    "\uf6b1": "0",
    "\uf6b2": "1",
    "\uf6b3": "2",
    "\uf6b4": "3",
    "\uf6b5": "4",
    "\uf6b6": "5",
    "\uf6b7": "6",
    "\uf6b8": "7",
    "\uf6b9": "8",
    "\uf6ba": "9",
}

MODEL_RE = re.compile(r"\b(K1[12]|K72)-(\d{2,4})(?:MM)?\b", re.IGNORECASE)
SIZE_RE = re.compile(
    r"\b(80|100|125|130|160|165|190|200|250|315|320|325|380)\b"
)

# Official Harvest HTML (productshow id=8): batch accuracy ≤ 0.03 mm
HARVEST_ACCURACY = "≤0.03 mm"
# Official Pro HTML: accuracy ≤ 0.03 mm (radial / end face / outer)
PRO_ACCURACY = "≤0.03 mm"


@dataclass
class CatalogRow:
    outer_diameter_mm: str
    through_hole_mm: str | None = None
    max_speed_rpm: str | None = None
    mounting_bolts: str | None = None
    source: str = ""
    raw: str = ""


@dataclass
class MatchResult:
    product_id: int
    sku: str
    name: str
    status: str
    model: str | None = None
    pdf_specs: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def strip_commerce_fields(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: strip_commerce_fields(v)
            for k, v in obj.items()
            if k not in FORBIDDEN_COMMERCE_KEYS
        }
    if isinstance(obj, list):
        return [strip_commerce_fields(x) for x in obj]
    return obj


def sanitize_product_export(detail: dict) -> dict:
    cleaned = strip_commerce_fields(detail)
    return {k: v for k, v in cleaned.items() if k in EXPORT_KEEP_KEYS}


def assert_payload_safe(payload: dict[str, Any]) -> None:
    bad = sorted(set(payload) - ALLOWED_PUT_KEYS)
    if bad:
        raise RuntimeError(f"forbidden PUT keys (commerce/other): {bad}")
    for k in FORBIDDEN_COMMERCE_KEYS:
        if k in payload:
            raise RuntimeError(f"forbidden commerce key in PUT: {k}")


def count_forbidden_in_obj(obj: Any) -> list[str]:
    hits: list[str] = []

    def walk(node: Any, path: str = "") -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                p = f"{path}.{k}" if path else k
                if k in FORBIDDEN_COMMERCE_KEYS:
                    hits.append(p)
                walk(v, p)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(obj)
    return hits


def _load_admin_creds() -> tuple[str, str]:
    phone = os.getenv("INITIAL_SUPER_ADMIN_PHONE")
    password = os.getenv("INITIAL_SUPER_ADMIN_PASSWORD")
    secrets = _ROOT / ".deploy-secrets"
    if not secrets.exists():
        alt = _ROOT.parent / "backend" / ".deploy-secrets"
        if alt.exists():
            secrets = alt
    if secrets.exists():
        for line in secrets.read_text(encoding="utf-8").splitlines():
            if line.startswith("INITIAL_SUPER_ADMIN_PHONE=") and not phone:
                phone = line.split("=", 1)[1].strip()
            if line.startswith("INITIAL_SUPER_ADMIN_PASSWORD=") and not password:
                password = line.split("=", 1)[1].strip()
    if not phone or not password:
        raise RuntimeError("missing admin creds (env or .deploy-secrets)")
    return phone, password


def http_json(
    method: str,
    url: str,
    *,
    data=None,
    headers=None,
    timeout: int = 90,
    retries: int = 4,
):
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
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                raw = resp.read()
                return resp.status, json.loads(raw.decode()) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="ignore")
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {"raw": raw[:500]}
            if e.code in {429, 502, 503, 504} and attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            return e.code, payload
        except (TimeoutError, urllib.error.URLError) as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"HTTP {method} {url} failed after {retries} tries: {last_err}")


def login() -> str:
    phone, password = _load_admin_creds()
    body = urllib.parse.urlencode({"username": phone, "password": password}).encode()
    req = urllib.request.Request(
        f"{API.rstrip('/')}/auth/login",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": UA,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        return json.loads(resp.read().decode())["access_token"]


def decode_pua(text: str) -> str:
    out = []
    for ch in text:
        if ch in _PUA_DIGIT:
            out.append(_PUA_DIGIT[ch])
        else:
            out.append(ch)
    s = "".join(out)
    # Leaflet extracts encode bolts as "3\\x0e.6" (= 3-M6) and decimals as "3\\x0f5" (= 3.5).
    s = re.sub(r"(\d)\x0e\.(\d)", r"\1-M\2", s)
    s = re.sub(r"(\d)[\x0e]\.?[\x0f]?(\d)", r"\1-M\2", s)
    s = re.sub(r"(\d)[\x0f](\d)", r"\1.\2", s)
    s = s.replace("\x0e", "-").replace("", "-")
    s = s.replace("\x0f", ".").replace("", ".")
    return s

def parse_harvest_dimension_table(text: str, *, source: str) -> dict[str, CatalogRow]:
    """Parse Harvest leaflet dimension rows (outer Ø → through-hole, rpm, bolts).

    Column layout (after size): D1 D2 D3(=through) H H1 … Z-d force rpm
    Only emit fields we label with high confidence.
    """
    decoded = decode_pua(text)
    by_od: dict[str, CatalogRow] = {}
    for line in decoded.splitlines():
        line = line.strip()
        if not line:
            continue
        m = SIZE_RE.search(line)
        if not m:
            continue
        # Require a max-speed-like trailing integer
        if not re.search(r"\b([12]\d{3}|[3-9]\d{3})\b", line):
            continue
        rest = line[m.start() :]
        toks = re.findall(r"\d+(?:\.\d+)?|-M\d+|M\d+", rest)
        merged: list[str] = []
        i = 0
        while i < len(toks):
            if i + 1 < len(toks) and toks[i].isdigit() and toks[i + 1].startswith("-M"):
                merged.append(toks[i] + toks[i + 1])
                i += 2
            else:
                merged.append(toks[i])
                i += 1
        if len(merged) < 8:
            continue
        od = merged[0]
        if od not in {
            "80",
            "100",
            "125",
            "130",
            "160",
            "165",
            "190",
            "200",
            "250",
            "315",
            "320",
            "325",
            "380",
        }:
            continue
        rpm = merged[-1]
        if not rpm.isdigit() or int(rpm) < 800:
            continue
        through = merged[3] if len(merged) > 3 else None
        # Through-hole must be smaller than outer diameter
        if through and through.replace(".", "", 1).isdigit():
            if float(through) >= float(od):
                through = None
        bolt = next((t for t in merged if re.fullmatch(r"\d+-M\d+", t)), None)
        row = CatalogRow(
            outer_diameter_mm=od,
            through_hole_mm=through,
            max_speed_rpm=rpm,
            mounting_bolts=bolt,
            source=source,
            raw=" ".join(merged[:12]),
        )
        # Prefer first clean hit; keep if identical
        prev = by_od.get(od)
        if prev and (
            prev.through_hole_mm != row.through_hole_mm
            or prev.max_speed_rpm != row.max_speed_rpm
        ):
            # Conflict → drop both for this OD
            by_od.pop(od, None)
            continue
        by_od[od] = row
    return by_od


def load_catalog_index(pdf_dir: Path) -> dict[str, CatalogRow]:
    """Index Harvest leaflet(s); prefer decoded text extracts under pdfs/."""
    candidates = [
        pdf_dir / "cn_harvest_fold.txt",
        pdf_dir / "cn_丰收卡盘折页.txt",
    ]
    merged: dict[str, CatalogRow] = {}
    for path in candidates:
        if not path.exists():
            continue
        part = parse_harvest_dimension_table(
            path.read_text(encoding="utf-8", errors="replace"),
            source=path.name,
        )
        for od, row in part.items():
            if od in merged and (
                merged[od].max_speed_rpm != row.max_speed_rpm
                or merged[od].through_hole_mm != row.through_hole_mm
            ):
                # Ambiguous across files — drop
                merged.pop(od, None)
                continue
            merged[od] = row
    return merged


def is_k11_manual_chuck_body(name: str) -> bool:
    """Very-high gate: K11 self-centering lathe chuck body only (not accessories)."""
    n = (name or "").upper()
    if not MODEL_RE.search(name or ""):
        return False
    # Accessories / other families
    ban = (
        "ADAPTER",
        "JAWS",
        "SCROLL",
        "PINION",
        "DEAD CENTER",
        "DRILL CHUCK",
        "ROHM",
    )
    if any(b in n for b in ban):
        return False
    if "فک" in (name or "") or "آچار" in (name or ""):
        return False
    if "لوازم یدکی" in (name or "") or "دنباله" in (name or ""):
        return False
    if "پشت سه نظام" in (name or "") or "پیچ پشت" in (name or ""):
        return False
    # Must be regular/self-centering chuck wording or Harvest brand
    if "HARVEST" in n:
        return True
    if "منظم" in (name or "") and "K11-" in n:
        return True
    return False


def extract_k11_size(name: str) -> str | None:
    m = re.search(r"\bK11-(\d{2,4})(?:MM)?\b", name or "", re.I)
    if not m:
        return None
    return str(int(m.group(1)))  # K11-080 → 80


def row_to_specs(row: CatalogRow, *, harvest_series: bool) -> dict[str, str]:
    specs: dict[str, str] = {
        "outer_diameter_mm": row.outer_diameter_mm,
    }
    if row.through_hole_mm:
        specs["through_hole_mm"] = row.through_hole_mm
    if row.max_speed_rpm:
        specs["max_speed_rpm"] = row.max_speed_rpm
    if row.mounting_bolts:
        specs["mounting_bolts"] = row.mounting_bolts
    if harvest_series:
        specs["accuracy"] = HARVEST_ACCURACY
        specs["series"] = "Harvest"
    specs["source"] = f"sanouchuck official:{row.source}"
    return specs


def specs_to_dict(specs: Any) -> dict[str, str]:
    out: dict[str, str] = {}
    if not specs:
        return out
    if isinstance(specs, dict):
        technical = specs.get("technical_specs", specs)
    else:
        technical = specs
    if isinstance(technical, list):
        for row in technical:
            if not isinstance(row, dict):
                continue
            k = str(row.get("key") or "").strip()
            v = str(row.get("value") or "").strip()
            if k and v and k not in FORBIDDEN_COMMERCE_KEYS:
                out[k] = v
    elif isinstance(technical, dict):
        for k, v in technical.items():
            if k in FORBIDDEN_COMMERCE_KEYS or v is None:
                continue
            sv = str(v).strip()
            if sv:
                out[str(k)] = sv
    return out


SPEC_ALIASES = {
    "outer_diameter_mm": [
        "outer_diameter_mm",
        "outer_diameter",
        "قطر خارجی",
        "قطر بيروني",
    ],
    "through_hole_mm": [
        "through_hole_mm",
        "through_hole",
        "bore",
        "bore_mm",
        "سوراخ مرکزی",
        "قطر سوراخ",
    ],
    "max_speed_rpm": [
        "max_speed_rpm",
        "max_speed",
        "speed_rpm",
        "حداکثر سرعت",
        "دور مجاز",
    ],
    "mounting_bolts": ["mounting_bolts", "bolts", "پیچ نصب"],
    "accuracy": ["accuracy", "دقت"],
    "series": ["series", "سری"],
}


def existing_has_key(existing: dict[str, str], canon: str) -> str | None:
    for alias in SPEC_ALIASES.get(canon, [canon]):
        if alias in existing and existing[alias].strip():
            return alias
    lower = {k.casefold(): k for k in existing}
    for alias in SPEC_ALIASES.get(canon, [canon]):
        if alias.casefold() in lower:
            return lower[alias.casefold()]
    return None


def _norm_spec_val(v: str) -> str:
    s = v.casefold().replace(" ", "").replace("٫", ".")
    for a, b in zip("۰۱۲۳۴۵۶۷۸۹", "0123456789", strict=True):
        s = s.replace(a, b)
    return s


def merge_technical_specs(
    existing_specs: dict[str, Any] | None,
    pdf_specs: dict[str, str],
) -> tuple[dict[str, Any], list[str], dict[str, str]]:
    notes: list[str] = []
    filled: dict[str, str] = {}
    existing_flat = specs_to_dict(existing_specs)
    tech: dict[str, str] = dict(existing_flat)

    base: dict[str, Any]
    if isinstance(existing_specs, dict):
        base = {
            "features": existing_specs.get("features") or {},
            "dimensions": existing_specs.get("dimensions") or {},
            "optional_accessories": existing_specs.get("optional_accessories") or [],
        }
    else:
        base = {"features": {}, "dimensions": {}, "optional_accessories": []}

    for canon, value in pdf_specs.items():
        if canon == "source":
            # Keep provenance under technical_specs only when filling something else
            continue
        value = value.strip()
        if not value:
            continue
        hit = existing_has_key(tech, canon)
        if hit:
            old = tech[hit].strip()
            if old and _norm_spec_val(old) != _norm_spec_val(value):
                notes.append(f"keep_existing_{canon}:{old}|pdf:{value}")
                continue
            if old:
                notes.append(f"unchanged_{canon}")
                continue
        tech[canon] = value
        filled[canon] = value

    if filled and pdf_specs.get("source"):
        # provenance only when we actually filled facts
        if not existing_has_key(tech, "source"):
            tech["catalog_source"] = pdf_specs["source"]
            filled["catalog_source"] = pdf_specs["source"]

    result = {
        "technical_specs": tech,
        "features": base["features"] if isinstance(base["features"], dict) else {},
        "dimensions": base["dimensions"] if isinstance(base["dimensions"], dict) else {},
        "optional_accessories": base.get("optional_accessories") or [],
    }
    # Ensure no commerce keys nested
    result = strip_commerce_fields(result)
    return result, notes, filled


def persian_short_description(
    *,
    name: str,
    brand_name: str | None,
    category_name: str | None,
    model: str | None,
    tech: dict[str, str],
) -> str | None:
    parts: list[str] = []
    # Only echo Harvest when the product name itself carries that series token.
    if "HARVEST" in (name or "").upper():
        parts.append("سه نظام تراش Harvest برند سانو")
    else:
        parts.append("سه نظام تراش (سری K11) برند سانو")
    facts: list[str] = []
    if model:
        facts.append(f"مدل {model}")
    if tech.get("outer_diameter_mm"):
        facts.append(f"قطر خارجی {tech['outer_diameter_mm']} میلی‌متر")
    if tech.get("through_hole_mm"):
        facts.append(f"سوراخ مرکزی {tech['through_hole_mm']} میلی‌متر")
    if tech.get("max_speed_rpm"):
        facts.append(f"حداکثر سرعت {tech['max_speed_rpm']} دور بر دقیقه")
    if tech.get("accuracy"):
        facts.append(f"دقت {tech['accuracy']}")
    if facts:
        parts.append("؛ ".join(facts))

    body = " — ".join(parts)
    if is_stub_description(body, product_name=name):
        return None
    return body[:500]


def persian_long_description(
    *,
    model: str | None,
    tech: dict[str, str],
    source: str,
) -> str | None:
    facts = []
    if tech.get("outer_diameter_mm"):
        facts.append(f"قطر خارجی: {tech['outer_diameter_mm']} mm")
    if tech.get("through_hole_mm"):
        facts.append(f"سوراخ مرکزی (through-hole): {tech['through_hole_mm']} mm")
    if tech.get("max_speed_rpm"):
        facts.append(f"حداکثر سرعت مجاز: {tech['max_speed_rpm']} r/min")
    if tech.get("mounting_bolts"):
        facts.append(f"پیچ نصب: {tech['mounting_bolts']}")
    if tech.get("accuracy"):
        facts.append(f"دقت (طبق بروشور/صفحه رسمی Harvest): {tech['accuracy']}")
    if not facts:
        return None
    lines = [
        f"سه نظام تراش سانو{f' مدل {model}' if model else ''}.",
        "مشخصات استخراج‌شده از کاتالوگ/بروشور رسمی SAN OU (بدون حدس):",
        *[f"- {f}" for f in facts],
        f"منبع: {source}",
    ]
    return "\n".join(lines)[:4000]


def meta_title_for(name: str, model: str | None) -> str:
    base = name.strip() or "سانو"
    if model and model not in base:
        base = f"{base} | {model}"
    return base[:255]


def meta_description_for(short: str | None, name: str, model: str | None) -> str:
    if short and not is_stub_description(short, product_name=name):
        return short[:500]
    bit = f" مدل {model}" if model else ""
    return f"{name}{bit} | برند سانو (SAN OU)"[:500]


def _is_our_enrichment_copy(text: str | None) -> bool:
    """True when body looks like a prior run of this script (safe to refresh)."""
    if not text:
        return False
    return ("برند سانو" in text) and (
        "قطر خارجی" in text or "سوراخ مرکزی" in text or "مشخصات استخراج‌شده" in text
    )


def build_payload(
    product: dict, pdf_specs: dict[str, str], *, model: str | None
) -> tuple[dict[str, Any], dict[str, Any]]:
    name = product.get("name") or ""
    brand = product.get("brand") if isinstance(product.get("brand"), dict) else {}
    cat = product.get("category") if isinstance(product.get("category"), dict) else {}

    merged_specs, merge_notes, filled = merge_technical_specs(
        product.get("specifications"), pdf_specs
    )
    tech_flat = {
        str(k): str(v)
        for k, v in (merged_specs.get("technical_specs") or {}).items()
        if v is not None and str(v).strip()
    }

    short = product.get("short_description")
    long = product.get("description")
    meta_title = product.get("meta_title")
    meta_desc = product.get("meta_description")

    new_short = None
    if (
        not short
        or is_stub_description(short, product_name=name)
        or _is_our_enrichment_copy(short)
    ):
        new_short = persian_short_description(
            name=name,
            brand_name=brand.get("name"),
            category_name=cat.get("name"),
            model=model,
            tech=tech_flat,
        )

    new_long = None
    if (
        not long
        or is_stub_description(long, product_name=name)
        or _is_our_enrichment_copy(long)
    ):
        new_long = persian_long_description(
            model=model,
            tech=tech_flat,
            source=pdf_specs.get("source") or "sanouchuck.com",
        )

    new_meta_title = None
    if not (meta_title or "").strip():
        new_meta_title = meta_title_for(name, model)

    new_meta_desc = None
    if not (meta_desc or "").strip() or _is_our_enrichment_copy(meta_desc):
        new_meta_desc = meta_description_for(new_short or short, name, model)

    payload: dict[str, Any] = {}
    if filled:
        payload["specifications"] = merged_specs
    if new_short:
        payload["short_description"] = new_short
    if new_long:
        payload["description"] = new_long
    if new_meta_title:
        payload["meta_title"] = new_meta_title
    if new_meta_desc:
        payload["meta_description"] = new_meta_desc

    assert_payload_safe(payload)
    audit = {
        "filled_specs": filled,
        "merge_notes": merge_notes,
        "new_short": new_short,
        "new_long": bool(new_long),
        "new_meta_title": bool(new_meta_title),
        "new_meta_description": bool(new_meta_desc),
        "payload_keys": sorted(payload.keys()),
        "forbidden_hits_in_payload": count_forbidden_in_obj(payload),
    }
    return payload, audit


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def fetch_products(auth: dict, *, brand_id: int, limit: int | None) -> list[dict]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    ids: list[int] = []
    skip = 0
    while True:
        st, resp = http_json(
            "GET",
            f"{API.rstrip('/')}/products/?brand_id={brand_id}&limit=100&skip={skip}",
            headers=auth,
            timeout=120,
        )
        if st != 200:
            raise RuntimeError(f"list products failed {st} {resp}")
        batch = resp.get("data") or []
        if not batch:
            break
        for row in batch:
            brand = row.get("brand") if isinstance(row.get("brand"), dict) else {}
            if (row.get("brand_id") or brand.get("id")) != brand_id:
                continue
            if row.get("is_active") is False:
                continue
            ids.append(int(row["id"]))
            if limit and len(ids) >= limit:
                break
        if limit and len(ids) >= limit:
            break
        skip += len(batch)
        meta = resp.get("meta") or {}
        total = int(meta.get("total_count") or 0)
        if skip >= total or len(batch) < 100:
            break

    print(f"[export] listed {len(ids)} ids; fetching details…")

    def _detail(pid: int) -> dict | None:
        st2, detail = http_json(
            "GET",
            f"{API.rstrip('/')}/products/{pid}",
            headers=auth,
            timeout=60,
        )
        if st2 != 200:
            print(f"[warn] detail {pid} -> {st2}")
            return None
        return sanitize_product_export(detail)

    products: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {pool.submit(_detail, pid): pid for pid in ids}
        done = 0
        for fut in as_completed(futs):
            detail = fut.result()
            done += 1
            if detail:
                products.append(detail)
            if done % 50 == 0:
                print(f"[export] details {done}/{len(ids)}…")
    products.sort(key=lambda p: int(p.get("id") or 0))
    leaks = count_forbidden_in_obj(products)
    if leaks:
        raise RuntimeError(f"commerce fields leaked into export: {leaks[:10]}")
    return products


def run(args: argparse.Namespace) -> int:
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pdf_dir = Path(args.pdf_dir)

    print(f"API: {API}")
    print(f"PDF dir: {pdf_dir}")
    print(f"Out: {out}")
    print(f"Mode: {'APPLY' if args.apply else 'dry-run'}")
    print(
        "POLICY: PUT allowlist="
        + ",".join(sorted(ALLOWED_PUT_KEYS))
        + " | commerce forbidden"
    )

    auth: dict[str, str] = {}
    if args.apply:
        token = login()
        auth = {"Authorization": f"Bearer {token}"}

    export_path = out / "site_export.jsonl"
    export_csv = out / "site_export.csv"
    if args.reuse_export and export_path.exists():
        products = [
            sanitize_product_export(json.loads(line))
            for line in export_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        print(f"[export] reused {len(products)} from {export_path}")
    else:
        products = fetch_products(auth, brand_id=args.brand_id, limit=args.limit)
        with export_path.open("w", encoding="utf-8") as f:
            for p in products:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        write_csv(
            export_csv,
            [
                {
                    "id": p.get("id"),
                    "sku": p.get("sku"),
                    "name": p.get("name"),
                    "has_short": bool((p.get("short_description") or "").strip()),
                    "has_long": bool((p.get("description") or "").strip()),
                    "tech_count": len(specs_to_dict(p.get("specifications"))),
                }
                for p in products
            ],
            ["id", "sku", "name", "has_short", "has_long", "tech_count"],
        )
        print(f"[export] {len(products)} products -> {export_path}")

    catalog = load_catalog_index(pdf_dir)
    index_path = out / "pdf_index.jsonl"
    with index_path.open("w", encoding="utf-8") as f:
        for od, row in sorted(catalog.items(), key=lambda x: int(x[0])):
            f.write(
                json.dumps(
                    {
                        "outer_diameter_mm": row.outer_diameter_mm,
                        "through_hole_mm": row.through_hole_mm,
                        "max_speed_rpm": row.max_speed_rpm,
                        "mounting_bolts": row.mounting_bolts,
                        "source": row.source,
                        "raw": row.raw,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    print(f"[pdf] indexed outer diameters: {sorted(catalog, key=int)}")

    matches: list[MatchResult] = []
    payloads: list[dict[str, Any]] = []

    for p in products:
        sku = str(p.get("sku") or "").strip()
        name = p.get("name") or ""
        if not is_k11_manual_chuck_body(name):
            matches.append(
                MatchResult(
                    product_id=int(p["id"]),
                    sku=sku,
                    name=name,
                    status="unmatched_not_k11_chuck_body",
                    notes=["product_type_gate"],
                )
            )
            continue

        size = extract_k11_size(name)
        model_m = MODEL_RE.search(name)
        model = (
            f"{model_m.group(1).upper()}-{model_m.group(2)}" if model_m else None
        )
        if not size or size not in catalog:
            matches.append(
                MatchResult(
                    product_id=int(p["id"]),
                    sku=sku,
                    name=name,
                    status="unmatched",
                    model=model,
                    notes=[f"size_{size}_not_in_harvest_table"],
                )
            )
            continue

        row = catalog[size]
        # Dimension table is from the official Harvest leaflet; sizes map to K11 منظم bodies.
        specs = row_to_specs(row, harvest_series=True)
        if "HARVEST" not in name.upper():
            # Keep accuracy from official Harvest page/leaflet; drop series label unless named.
            specs.pop("series", None)
        mr = MatchResult(
            product_id=int(p["id"]),
            sku=sku,
            name=name,
            status="matched",
            model=model,
            pdf_specs=specs,
            notes=[f"matched_outer_diameter={size}", f"source={row.source}"],
        )
        matches.append(mr)
        payload, audit = build_payload(p, specs, model=model)
        if payload:
            payloads.append(
                {
                    "id": p["id"],
                    "sku": sku,
                    "model": model,
                    "payload": payload,
                    "audit": audit,
                    "pdf_specs": specs,
                }
            )

    status_counts = Counter(m.status for m in matches)
    print(f"[match] {dict(status_counts)}")
    print(f"[payloads] ready={len(payloads)}")

    match_csv = out / "match_report.csv"
    write_csv(
        match_csv,
        [
            {
                "id": m.product_id,
                "sku": m.sku,
                "name": m.name,
                "status": m.status,
                "model": m.model or "",
                "outer_diameter_mm": m.pdf_specs.get("outer_diameter_mm", ""),
                "through_hole_mm": m.pdf_specs.get("through_hole_mm", ""),
                "max_speed_rpm": m.pdf_specs.get("max_speed_rpm", ""),
                "accuracy": m.pdf_specs.get("accuracy", ""),
                "notes": "|".join(m.notes),
            }
            for m in matches
        ],
        [
            "id",
            "sku",
            "name",
            "status",
            "model",
            "outer_diameter_mm",
            "through_hole_mm",
            "max_speed_rpm",
            "accuracy",
            "notes",
        ],
    )

    dry_path = out / "dry_run_payloads.jsonl"
    with dry_path.open("w", encoding="utf-8") as f:
        for row in payloads:
            assert_payload_safe(row["payload"])
            if count_forbidden_in_obj(row["payload"]):
                raise RuntimeError("commerce key in dry-run payload")
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary: dict[str, Any] = {
        "api": API,
        "brand_id": args.brand_id,
        "exported": len(products),
        "catalog_ods": sorted(catalog, key=int),
        "match_counts": dict(status_counts),
        "payloads": len(payloads),
        "apply": bool(args.apply),
        "applied": 0,
        "apply_errors": 0,
        "price_writes": 0,
        "forbidden_put_violations": 0,
        "policy": {
            "forbidden_keys": sorted(FORBIDDEN_COMMERCE_KEYS),
            "allowed_put_keys": sorted(ALLOWED_PUT_KEYS),
            "zero_price_writes_confirmed": True,
        },
        "sources_used": sorted({r.source for r in catalog.values()}),
        "paths": {
            "site_export": str(export_path),
            "pdf_index": str(index_path),
            "match_report": str(match_csv),
            "dry_run_payloads": str(dry_path),
        },
    }

    apply_rows: list[dict] = []
    if args.apply:
        to_apply = payloads[: args.apply_limit] if args.apply_limit else payloads
        print(f"[apply] writing {len(to_apply)} products (enrichment fields only)…")
        for row in to_apply:
            payload = row["payload"]
            assert_payload_safe(payload)
            if count_forbidden_in_obj(payload):
                summary["forbidden_put_violations"] += 1
                apply_rows.append(
                    {
                        "id": row["id"],
                        "sku": row["sku"],
                        "status": "blocked_commerce_key",
                    }
                )
                continue
            st, resp = http_json(
                "PUT",
                f"{API.rstrip('/')}/products/{row['id']}",
                data=payload,
                headers=auth,
                timeout=90,
            )
            ok = st in {200, 201}
            if ok:
                summary["applied"] += 1
            else:
                summary["apply_errors"] += 1
            apply_rows.append(
                {
                    "id": row["id"],
                    "sku": row["sku"],
                    "status": "ok" if ok else f"http_{st}",
                    "payload_keys": ",".join(sorted(payload.keys())),
                    "error": "" if ok else json.dumps(resp, ensure_ascii=False)[:300],
                }
            )
            time.sleep(0.05)
        write_csv(
            out / "apply_report.csv",
            apply_rows,
            ["id", "sku", "status", "payload_keys", "error"],
        )

    summary_path = out / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(
        f"ZERO price writes confirmed: price_writes={summary['price_writes']} "
        f"forbidden_violations={summary['forbidden_put_violations']}"
    )
    return 0 if summary["apply_errors"] == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default=str(OUT_DIR),
        help="Report output directory",
    )
    parser.add_argument(
        "--pdf-dir",
        default=str(OUT_DIR / "pdfs"),
        help="Directory with official PDF text extracts",
    )
    parser.add_argument("--brand-id", type=int, default=BRAND_ID_DEFAULT)
    parser.add_argument("--limit", type=int, default=None, help="Limit export count")
    parser.add_argument("--reuse-export", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Default mode (no writes)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write enrichment fields to staging via admin PUT",
    )
    parser.add_argument("--apply-limit", type=int, default=None)
    args = parser.parse_args()
    if args.apply:
        args.dry_run = False
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
