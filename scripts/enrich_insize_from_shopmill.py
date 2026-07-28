#!/usr/bin/env python3
"""Enrich INSIZE products from shopmilltools.com — CONTENT ONLY.

Source of truth: WooCommerce Store API crawl of shopmilltools.com INSIZE PDPs
(Persian attribute tables). Reuses ``scripts/shopmill_insize_crawl.py`` helpers.

HARD CONSTRAINT — never read/persist or write commerce fields:
  Forbidden: price, base_price, original_price, sale_price, list_price, discount,
    stock_quantity, stock_unit, is_available, availability, stock_status, …
  Allowed PUT keys only:
    short_description, description, meta_title, meta_description, specifications

Matching (very-high confidence only):
  - Exact normalized INSIZE SKU (official series-size order from crawl)
  - Unambiguous letter-suffix base (site 1111-100 ↔ shopmill 1111-100A) when unique
  - Skip ambiguous / no-SKU / empty-spec rows

Specs policy:
  - Locked measurement technical_specs keys (EN canonical): range, accuracy,
    resolution, material, standard, battery_type
  - ALL other factual shopmill attributes preserved under source_attributes
  - Merge fill-empty; conflict → keep existing (never silent overwrite)
  - Never invent values; never treat country-of-origin as material

Usage:
  python scripts/enrich_insize_from_shopmill.py --crawl
  python scripts/enrich_insize_from_shopmill.py --dry-run
  python scripts/enrich_insize_from_shopmill.py --apply --apply-confirm
  python scripts/enrich_insize_from_shopmill.py --reuse-export --reuse-crawl --dry-run

Reports: data/imports/insize/shopmill/
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.utils.seo_descriptions import (  # noqa: E402
    display_brand_name,
    display_category_name,
    is_stub_description,
)

API = os.getenv("KARZAR_API_BASE", "https://api.karzartools.com/api/v1").rstrip("/")
UA = "KarzarInsizeShopmillEnrich/1.0"
INSIZE_BRAND_ID = 3
OUT_DIR = _ROOT / "data" / "imports" / "insize" / "shopmill"
SOURCE_LABEL = "shopmilltools.com"
CUSTOMER_SOURCE_LABEL = "مشخصات رسمی برند"

FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "price",
        "base_price",
        "original_price",
        "sale_price",
        "list_price",
        "discount",
        "discount_percent",
        "tax_percent",
        "stock",
        "stock_quantity",
        "stock_unit",
        "stock_status",
        "low_stock",
        "availability",
        "is_available",
        "hesabfa_stock",
        "warehouse_quantity",
        "currency",
        "weight_grams",
    }
)
FORBIDDEN_KEY_SUBSTR = ("price", "stock", "avail", "discount", "tax_percent")
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
        "category_name",
        "brand_name",
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

# Locked measurement template (EN canonical) — same contract as 108A tooling.
MEASUREMENT_TECH_KEYS = (
    "range",
    "accuracy",
    "resolution",
    "material",
    "standard",
    "battery_type",
)

# shopmill Persian attribute → canonical EN key
SHOPMILL_TO_CANON = {
    "دامنه اندازه گیری": "range",
    "دامنه اندازه‌گیری": "range",
    "سایز": "range",
    "دقت اندازه گیری": "accuracy",
    "دقت اندازه‌گیری": "accuracy",
    "دقت": "accuracy",
    "تفکیک پذیری": "resolution",
    "تفکیک‌پذیری": "resolution",
    "رزولوشن": "resolution",
    "تقسیم بندی اندازه": "resolution",
    "متریال": "material",
    "جنس فک": "material",
    "جنس": "material",
    "استاندارد ساخت": "standard",
    "استاندارد": "standard",
    "استاندار باتری": "battery_type",  # shopmill typo
    "استاندارد باتری": "battery_type",
    "نوع باتری": "battery_type",
    "باتری": "battery_type",
}

# Marketing / non-technical shopmill attrs — skip entirely
SKIP_ATTRS = frozenset(
    {
        "گارانتی",
        "قیمت",
        "موجودی",
        "برند",
        "brand",
        "warranty",
        "price",
        "stock",
    }
)

COUNTRY_LIKE = re.compile(
    r"^(چین|china|ژاپن|japan|آلمان|germany|تایوان|taiwan|کره|korea|"
    r"آمریکا|usa|us|ایران|iran|ایتالیا|italy|سوئیس|switzerland)$",
    re.I,
)
TRUTHY_FA = re.compile(r"^(بله|آری|دارد|yes|true|1|ip\s*\d+)$", re.I)
FALSY_FA = re.compile(r"^(خیر|ندارد|نه|no|false|0|non)$", re.I)


@dataclass
class MatchResult:
    product_id: int
    sku: str
    name: str
    status: str  # matched | unmatched | ambiguous | skipped_no_specs | already_complete
    shopmill_sku: str | None = None
    source_url: str | None = None
    shopmill_specs: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def _clean(s: Any) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip(" .;,\t*")


def _norm_sku(sku: str | None) -> str:
    return _clean(sku).upper().replace(" ", "").replace("_", "-").replace("ـ", "-")


def _is_forbidden_key(key: str) -> bool:
    k = key.casefold()
    if k in FORBIDDEN_PAYLOAD_KEYS:
        return True
    return any(s in k for s in FORBIDDEN_KEY_SUBSTR)


def strip_commerce_fields(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: strip_commerce_fields(v)
            for k, v in obj.items()
            if not _is_forbidden_key(str(k))
        }
    if isinstance(obj, list):
        return [strip_commerce_fields(x) for x in obj]
    return obj


def sanitize_product_export(detail: dict[str, Any]) -> dict[str, Any]:
    cleaned = strip_commerce_fields(detail)
    return {k: v for k, v in cleaned.items() if k in EXPORT_KEEP_KEYS}


def assert_payload_safe(payload: dict[str, Any], *, context: str = "payload") -> None:
    bad = sorted(k for k in payload if k not in ALLOWED_PUT_KEYS or _is_forbidden_key(k))
    if bad:
        raise RuntimeError(f"{context}: forbidden/non-allowlisted keys: {bad}")
    for k in FORBIDDEN_PAYLOAD_KEYS:
        if k in payload:
            raise RuntimeError(f"{context}: forbidden commerce key: {k}")


def count_forbidden_in_obj(obj: Any) -> list[str]:
    hits: list[str] = []

    def walk(node: Any, path: str = "") -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                p = f"{path}.{k}" if path else str(k)
                if _is_forbidden_key(str(k)):
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
            with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
                data = json.loads(resp.read().decode())
            token = data.get("access_token")
            if not token:
                raise RuntimeError("login failed: no access_token")
            return token
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"login failed after {retries} tries: {last_err}")


def _load_crawl_module():
    path = _ROOT / "scripts" / "shopmill_insize_crawl.py"
    spec = importlib.util.spec_from_file_location("shopmill_insize_crawl", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_crawl(out_path: Path, *, sleep_s: float = 0.7) -> int:
    """Crawl shopmill; strip prices from every row before write."""
    mod = _load_crawl_module()
    tmp = out_path.with_suffix(".raw.jsonl")
    mod.crawl(tmp, sleep_s=sleep_s)
    written = 0
    with tmp.open(encoding="utf-8") as src, out_path.open("w", encoding="utf-8") as dst:
        for line in src:
            if not line.strip():
                continue
            row = json.loads(line)
            row.pop("prices", None)
            # Belt-and-suspenders: drop any commerce-looking keys
            row = {
                k: v
                for k, v in row.items()
                if not _is_forbidden_key(str(k)) and k != "prices"
            }
            dst.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    tmp.unlink(missing_ok=True)
    print(f"[crawl] commerce-stripped rows={written} → {out_path}")
    return written


def load_crawl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        row.pop("prices", None)
        sku = _norm_sku(row.get("sku"))
        if sku:
            row["sku"] = sku
        rows.append(row)
    return rows


def sku_base(sku: str) -> str:
    """Strip trailing letter suffix: 1111-100A → 1111-100."""
    s = _norm_sku(sku)
    m = re.match(r"^(\d+-\d+)([A-Z]+)$", s)
    return m.group(1) if m else s


def looks_like_accuracy(val: str) -> bool:
    v = _clean(val)
    if not v:
        return False
    if "±" in v or "+-" in v or v.startswith("±") or v.startswith("+"):
        return True
    # shopmill often uses ±0.03mm already; bare 0.03mm alone is ambiguous — accept if
    # labeled as accuracy upstream (caller decides). Here: require ± or slash form.
    if "/" in v and re.search(r"\d", v):
        return True
    return False


def sanitize_material(val: str | None) -> str:
    v = _clean(val)
    if not v or COUNTRY_LIKE.match(v):
        return ""
    return v[:120]


def map_shopmill_attributes(raw: dict[str, Any] | None) -> tuple[dict[str, str], dict[str, str], dict[str, Any]]:
    """Map shopmill attrs → (canonical tech, source_attributes, feature hints).

    Returns ALL factual attributes; invents nothing.
    """
    tech: dict[str, str] = {}
    extras: dict[str, str] = {}
    feature_hints: dict[str, Any] = {}

    for k, v in (raw or {}).items():
        key = _clean(k)
        val = _clean(v)
        if not key or not val:
            continue
        if key in SKIP_ATTRS or key.casefold() in {s.casefold() for s in SKIP_ATTRS}:
            continue
        if _is_forbidden_key(key):
            continue

        if key in ("گواهی ضد آب", "ضد آب"):
            if TRUTHY_FA.match(val) or re.search(r"\bip\s*\d+", val, re.I):
                feature_hints["waterproof"] = True
            elif FALSY_FA.match(val):
                feature_hints["waterproof"] = False
            extras[key] = val
            continue

        if key in ("عملکرد دکمه ها", "عملکرد دکمه‌ها", "دکمه ها"):
            buttons = [p.strip() for p in re.split(r"[،,;/|]", val) if p.strip()]
            feature_hints["buttons_list"] = buttons[:12]
            feature_hints["has_buttons"] = bool(buttons)
            extras[key] = val
            continue

        canon = SHOPMILL_TO_CANON.get(key)
        if canon:
            if canon == "material":
                mat = sanitize_material(val)
                if not mat:
                    extras[key] = val  # keep country/noise under extras, not material
                    continue
                val = mat
            if canon == "accuracy" and not looks_like_accuracy(val):
                # Still keep as accuracy when shopmill labeled it دقت — values like 0.02mm
                # without ± are common on shopmill; accept with note via extras duplicate.
                if not re.search(r"\d", val):
                    extras[key] = val
                    continue
            if canon == "resolution" and looks_like_accuracy(val) and "±" in val:
                # Mis-labeled accuracy as resolution — park in extras, don't poison resolution
                extras[key] = val
                continue
            # Prefer first non-empty; later conflicting keys go to extras
            if canon not in tech:
                tech[canon] = val
            elif _norm_spec_val(tech[canon]) != _norm_spec_val(val):
                extras[key] = val
            continue

        # Country of origin → extras only (never material)
        if key in ("کشور سازنده", "کشور"):
            extras[key] = val
            continue

        extras[key] = val

    return tech, extras, feature_hints


def _norm_spec_val(v: str) -> str:
    s = v.casefold().replace(" ", "").replace("٫", ".")
    trans = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
    return s.translate(trans)


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
            k = _clean(row.get("key"))
            v = _clean(row.get("value"))
            if k and v:
                out[k] = v
    elif isinstance(technical, dict):
        for k, v in technical.items():
            sv = _clean(v)
            if sv:
                out[str(k)] = sv
    return out


FA_TO_EN = {
    "بازه اندازه‌گیری": "range",
    "بازه اندازه گیری": "range",
    "بازه": "range",
    "دقت": "accuracy",
    "تفکیک‌پذیری": "resolution",
    "تفکیک پذیری": "resolution",
    "رزولوشن": "resolution",
    "درجه بندی": "resolution",
    "جنس": "material",
    "متریال": "material",
    "استاندارد": "standard",
    "باتری": "battery_type",
    "نوع باتری": "battery_type",
    "استاندارد باتری": "battery_type",
}


def existing_canon_tech(existing_specs: Any) -> dict[str, str]:
    flat = specs_to_dict(existing_specs)
    out: dict[str, str] = {}
    for k, v in flat.items():
        en = FA_TO_EN.get(k, k)
        if en not in MEASUREMENT_TECH_KEYS:
            continue
        if en == "material" and not sanitize_material(v):
            continue
        if en not in out:
            out[en] = v
    return out


def merge_specifications(
    existing_specs: Any,
    shop_tech: dict[str, str],
    shop_extras: dict[str, str],
    feature_hints: dict[str, Any],
) -> tuple[dict[str, Any], list[str], dict[str, str]]:
    """Fill-empty merge into locked measurement schema + source_attributes."""
    notes: list[str] = []
    filled: dict[str, str] = {}

    base: dict[str, Any] = {}
    if isinstance(existing_specs, dict):
        base = deepcopy(existing_specs)
    prior_tech = existing_canon_tech(existing_specs)

    merged_tech: dict[str, str] = {}
    for key in MEASUREMENT_TECH_KEYS:
        incoming = _clean(shop_tech.get(key))
        prior = _clean(prior_tech.get(key))
        if incoming:
            if prior and _norm_spec_val(prior) != _norm_spec_val(incoming):
                notes.append(f"keep_existing_{key}:{prior}|shopmill:{incoming}")
                merged_tech[key] = prior
            else:
                merged_tech[key] = incoming
                if not prior or _norm_spec_val(prior) != _norm_spec_val(incoming):
                    filled[key] = incoming
                else:
                    notes.append(f"unchanged_{key}")
        elif prior:
            merged_tech[key] = prior

    # Features
    prior_feats = base.get("features") if isinstance(base.get("features"), dict) else {}
    feats = dict(prior_feats) if isinstance(prior_feats, dict) else {}
    if "waterproof" in feature_hints:
        if feats.get("waterproof") in (None, "") or feats.get("waterproof") is False:
            if feature_hints["waterproof"] is True or feats.get("waterproof") is False:
                if feats.get("waterproof") != feature_hints["waterproof"]:
                    feats["waterproof"] = feature_hints["waterproof"]
                    filled["features.waterproof"] = str(feature_hints["waterproof"])
        elif feats.get("waterproof") != feature_hints["waterproof"]:
            notes.append(
                f"keep_existing_waterproof:{feats.get('waterproof')}|shop:{feature_hints['waterproof']}"
            )
    if feature_hints.get("buttons_list") and not feats.get("buttons_list") and not feats.get("buttons"):
        feats["buttons_list"] = feature_hints["buttons_list"]
        feats["has_buttons"] = True
        filled["features.buttons_list"] = ",".join(feature_hints["buttons_list"][:4])
    # Normalize locked-ish feature keys without inventing True
    feats.setdefault("waterproof", bool(feats.get("waterproof", False)))
    feats.setdefault("data_output", bool(feats.get("data_output", False)))
    feats.setdefault("auto_power_off", bool(feats.get("auto_power_off", False)))
    if "buttons_list" not in feats:
        prior_btns = feats.get("buttons")
        if isinstance(prior_btns, list):
            feats["buttons_list"] = [str(x) for x in prior_btns if str(x).strip()][:12]
        else:
            feats["buttons_list"] = []
    feats.setdefault("has_buttons", bool(feats.get("buttons_list")))
    feats.setdefault("has_certification", bool(feats.get("has_certification", False)))
    if not isinstance(feats.get("certification_text"), str):
        feats["certification_text"] = _clean(feats.get("certification") or "")

    # Dimensions — keep existing non-zero only
    dims_raw = base.get("dimensions") if isinstance(base.get("dimensions"), dict) else {}
    dims: dict[str, Any] = {}
    for k, v in (dims_raw or {}).items():
        if v in (None, "", 0, 0.0):
            continue
        try:
            num = float(v)
            if num == 0.0:
                continue
            dims[k] = num
        except (TypeError, ValueError):
            s = _clean(v)
            if s:
                dims[k] = s

    # source_attributes: merge fill-empty
    prior_src = base.get("source_attributes") if isinstance(base.get("source_attributes"), dict) else {}
    src = dict(prior_src) if isinstance(prior_src, dict) else {}
    for k, v in shop_extras.items():
        if not v:
            continue
        if k in src and _clean(src[k]) and _norm_spec_val(str(src[k])) != _norm_spec_val(v):
            notes.append(f"keep_existing_attr:{k}")
            continue
        if k not in src or not _clean(src.get(k)):
            src[k] = v
            filled[f"attr:{k}"] = v

    # Provenance (non-commerce)
    src.setdefault("source", SOURCE_LABEL)
    if shop_tech or shop_extras:
        src["source_kind"] = "shopmilltools_wc_attributes"

    result = {
        "technical_specs": merged_tech,
        "features": feats,
        "dimensions": dims,
        "optional_accessories": base.get("optional_accessories") or [],
        "source_attributes": src,
    }
    # Preserve other non-commerce sections already on product
    for k, v in base.items():
        if k in result or _is_forbidden_key(str(k)):
            continue
        result[k] = v
    return result, notes, filled


def persian_short_description(
    *,
    name: str,
    brand_name: str | None,
    category_name: str | None,
    sku: str,
    tech: dict[str, str],
) -> str | None:
    brand = display_brand_name(brand_name) or "اینسایز"
    cat = display_category_name(category_name)
    lead = cat or "ابزار اندازه‌گیری"
    parts = [f"{lead} برند {brand}"]
    facts: list[str] = []
    if tech.get("range"):
        facts.append(f"بازه {tech['range']}")
    if tech.get("resolution"):
        facts.append(f"تفکیک‌پذیری {tech['resolution']}")
    if tech.get("accuracy"):
        facts.append(f"دقت {tech['accuracy']}")
    if facts:
        parts.append("؛ ".join(facts[:3]))
    if sku:
        parts.append(f"کد {sku}")
    parts.append(CUSTOMER_SOURCE_LABEL)
    body = ". ".join(parts) + "."
    if is_stub_description(body, product_name=name):
        return None
    return body[:500]


def persian_long_description(
    *,
    category_name: str | None,
    sku: str,
) -> str:
    cat = display_category_name(category_name) or "ابزار اندازه‌گیری"
    code = f" با کد {sku}" if sku else ""
    return (
        f"{cat} برند اینسایز (INSIZE){code}. "
        "مشخصات عددی و ویژگی‌های فنی این مدل فقط در بخش مشخصات فنی همین صفحه آمده است. "
        f"مرجع مشخصات: {CUSTOMER_SOURCE_LABEL}."
    )[:4000]


def meta_title_for(name: str, sku: str) -> str:
    base = _clean(name) or f"INSIZE {sku}"
    if "insize" not in base.casefold() and "اینسایز" not in base:
        base = f"{base} | INSIZE"
    return base[:255]


def meta_description_for(short: str | None, name: str, sku: str) -> str:
    if short and not is_stub_description(short, product_name=name):
        return short[:500]
    return f"{_clean(name) or sku} | {CUSTOMER_SOURCE_LABEL}"[:500]


def _product_brand_name(product: dict[str, Any]) -> str | None:
    brand = product.get("brand")
    if isinstance(brand, dict):
        return brand.get("name")
    return product.get("brand_name") or "INSIZE | اینسایز"


def _product_category_name(product: dict[str, Any]) -> str | None:
    cat = product.get("category")
    if isinstance(cat, dict):
        return cat.get("name")
    return product.get("category_name")


def _has_customer_facing_external_domain(text: str | None) -> bool:
    if not text:
        return False
    return "shopmilltools.com" in text.lower()


def build_payload(
    product: dict[str, Any],
    shop_row: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    name = product.get("name") or ""
    sku = _norm_sku(product.get("sku"))
    brand_name = _product_brand_name(product)
    category_name = _product_category_name(product)

    shop_tech, shop_extras, feature_hints = map_shopmill_attributes(
        shop_row.get("specifications")
    )
    merged_specs, merge_notes, filled = merge_specifications(
        product.get("specifications"),
        shop_tech,
        shop_extras,
        feature_hints,
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
        or _has_customer_facing_external_domain(short)
    ):
        new_short = persian_short_description(
            name=name,
            brand_name=brand_name,
            category_name=category_name,
            sku=sku,
            tech=tech_flat,
        )

    new_long = None
    if (
        not long
        or is_stub_description(long, product_name=name)
        or _has_customer_facing_external_domain(long)
    ):
        new_long = persian_long_description(category_name=category_name, sku=sku)

    new_meta_title = None
    if not (meta_title or "").strip():
        new_meta_title = meta_title_for(name, sku)

    new_meta_desc = None
    if (
        not (meta_desc or "").strip()
        or is_stub_description(meta_desc, product_name=name)
        or _has_customer_facing_external_domain(meta_desc)
    ):
        new_meta_desc = meta_description_for(new_short or short, name, sku)

    payload: dict[str, Any] = {}
    # Only send specifications when we fill something new
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

    assert_payload_safe(payload, context=f"sku={sku}")

    audit = {
        "filled": filled,
        "merge_notes": merge_notes,
        "shopmill_canon": shop_tech,
        "shopmill_extra_keys": sorted(shop_extras.keys()),
        "new_short": bool(new_short),
        "new_long": bool(new_long),
        "new_meta_title": bool(new_meta_title),
        "new_meta_description": bool(new_meta_desc),
        "payload_keys": sorted(payload.keys()),
        "source_url": shop_row.get("source_url"),
    }
    return payload, audit


def load_site_inventory(path: Path) -> list[dict]:
    """Load commerce-stripped inventory JSON (list or {products:[…]})."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        products = raw
    elif isinstance(raw, dict):
        products = raw.get("products") or raw.get("data") or []
    else:
        raise RuntimeError(f"unsupported site inventory shape: {path}")
    out: list[dict] = []
    for p in products:
        if not isinstance(p, dict):
            continue
        cleaned = sanitize_product_export(
            {
                **p,
                # Flatten inventory fields into export shape when brand/category objects absent
                "brand": p.get("brand")
                or {"id": p.get("brand_id") or INSIZE_BRAND_ID, "name": p.get("brand_name") or "INSIZE | اینسایز"},
                "category": p.get("category")
                or (
                    {"id": p.get("category_id"), "name": p.get("category_name")}
                    if p.get("category_id") or p.get("category_name")
                    else None
                ),
            }
        )
        # Keep flat category_name for payload helper
        if p.get("category_name") and "category_name" not in cleaned:
            cleaned["category_name"] = p["category_name"]
        out.append(cleaned)
    return out


def fetch_insize_products(
    auth: dict[str, str],
    *,
    brand_id: int,
    limit: int | None,
    workers: int = 12,
) -> list[dict]:
    ids: list[int] = []
    skip = 0
    batch_limit = 100
    while True:
        st, resp = http_json(
            "GET",
            f"{API}/products/?brand_id={brand_id}&skip={skip}&limit={batch_limit}",
            headers=auth,
            timeout=60,
        )
        if st != 200:
            raise RuntimeError(f"list INSIZE failed {st} {resp}")
        batch = resp.get("data") or []
        for p in batch:
            if p.get("id") is not None:
                ids.append(int(p["id"]))
        if not batch:
            break
        skip += len(batch)
        meta = resp.get("meta") or {}
        total = int(meta.get("total_count") or 0)
        if limit and len(ids) >= limit:
            ids = ids[:limit]
            break
        if skip >= total or len(batch) < batch_limit:
            break

    print(f"[export] listed {len(ids)} ids; fetching details (workers={workers})…")

    def _detail(pid: int) -> dict | None:
        st2, detail = http_json(
            "GET",
            f"{API}/products/{pid}",
            headers=auth,
            timeout=60,
            retries=6,
        )
        if st2 != 200:
            print(f"[warn] detail {pid} -> {st2}")
            return None
        return sanitize_product_export(detail)

    products: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_detail, pid): pid for pid in ids}
        done = 0
        for fut in as_completed(futs):
            detail = fut.result()
            done += 1
            if detail:
                products.append(detail)
            if done % 50 == 0:
                print(f"[export] details {done}/{len(ids)}…", flush=True)
    products.sort(key=lambda p: int(p.get("id") or 0))
    return products


def index_shopmill(rows: list[dict[str, Any]]) -> tuple[dict[str, dict], dict[str, list[str]]]:
    """exact sku → row; base sku → list of full skus."""
    by_sku: dict[str, dict] = {}
    by_base: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        sku = _norm_sku(row.get("sku"))
        if not sku:
            continue
        if sku in by_sku:
            # Should not happen with current crawl; mark later as ambiguous
            by_sku[sku] = row  # last wins but flagged via by_base length
        else:
            by_sku[sku] = row
        by_base[sku_base(sku)].append(sku)
    return by_sku, dict(by_base)


def resolve_shopmill_match(
    site_sku: str,
    by_sku: dict[str, dict],
    by_base: dict[str, list[str]],
) -> tuple[dict | None, str, list[str]]:
    """Return (row, via, notes). None row ⇒ unmatched/ambiguous."""
    notes: list[str] = []
    sku = _norm_sku(site_sku)
    if not sku:
        return None, "no_sku", ["empty_site_sku"]

    if sku in by_sku:
        return by_sku[sku], "exact", notes

    base = sku_base(sku)
    candidates = list(dict.fromkeys(by_base.get(base) or []))
    # Also: site has suffix, shopmill is base
    if base != sku and base in by_sku:
        candidates = list(dict.fromkeys([base] + candidates))
    # Site is base, shopmill has unique suffix
    if not candidates and base in by_base:
        candidates = list(dict.fromkeys(by_base[base]))

    candidates = [c for c in candidates if c in by_sku]
    if len(candidates) == 1:
        notes.append(f"suffix_variant:{sku}->{candidates[0]}")
        return by_sku[candidates[0]], "suffix_unique", notes
    if len(candidates) > 1:
        notes.append(f"ambiguous_candidates:{','.join(candidates[:8])}")
        return None, "ambiguous", notes
    return None, "unmatched", ["sku_not_in_shopmill"]


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def run(args: argparse.Namespace) -> int:
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    crawl_path = Path(args.crawl_jsonl)
    print(f"API: {API}")
    print(f"Out: {out}")
    print(f"Mode: {'APPLY' if args.apply else 'dry-run'}")

    # 1) Crawl
    if args.crawl or (not crawl_path.exists() and not args.reuse_crawl):
        run_crawl(crawl_path, sleep_s=args.crawl_sleep)
    elif args.reuse_crawl and crawl_path.exists():
        print(f"[crawl] reusing {crawl_path}")
    elif not crawl_path.exists():
        # Try sibling backend crawl artifact
        alt = _ROOT.parent / "backend" / "data" / "shopmill_insize.jsonl"
        if alt.exists():
            print(f"[crawl] copying from {alt}")
            rows_alt = load_crawl_rows(alt)
            crawl_path.parent.mkdir(parents=True, exist_ok=True)
            with crawl_path.open("w", encoding="utf-8") as f:
                for r in rows_alt:
                    r = {k: v for k, v in r.items() if k != "prices" and not _is_forbidden_key(str(k))}
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
        else:
            print("[crawl] no crawl file — running fresh crawl")
            run_crawl(crawl_path, sleep_s=args.crawl_sleep)

    shop_rows = load_crawl_rows(crawl_path)
    # Drop price if any leaked
    for r in shop_rows:
        r.pop("prices", None)
    print(f"[crawl] loaded={len(shop_rows)} with_specs={sum(1 for r in shop_rows if r.get('specifications'))}")

    by_sku, by_base = index_shopmill(shop_rows)

    # 2) Export site
    auth: dict[str, str] = {}
    if args.apply:
        token = login()
        auth = {"Authorization": f"Bearer {token}"}

    export_path = out / "site_export.jsonl"
    export_csv = out / "site_export.csv"
    if args.site_inventory:
        inv = Path(args.site_inventory)
        products = load_site_inventory(inv)
        if args.limit:
            products = products[: args.limit]
        print(f"[export] loaded inventory {len(products)} from {inv}")
        with export_path.open("w", encoding="utf-8") as f:
            for p in products:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
    elif args.reuse_export and export_path.exists():
        products = [
            sanitize_product_export(json.loads(line))
            for line in export_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        print(f"[export] reused {len(products)} from {export_path}")
    else:
        products = fetch_insize_products(
            auth, brand_id=args.brand_id, limit=args.limit, workers=args.workers
        )
        with export_path.open("w", encoding="utf-8") as f:
            for p in products:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        print(f"[export] {len(products)} products → {export_path}")

    write_csv(
        export_csv,
        [
            {
                "id": p.get("id"),
                "sku": p.get("sku"),
                "name": p.get("name"),
                "is_active": p.get("is_active"),
                "has_short": bool(p.get("short_description")),
                "has_long": bool(p.get("description")),
                "tech_count": len(existing_canon_tech(p.get("specifications"))),
            }
            for p in products
        ],
        ["id", "sku", "name", "is_active", "has_short", "has_long", "tech_count"],
    )

    export_forbidden = count_forbidden_in_obj(products)
    if export_forbidden:
        print(f"ERROR: commerce leak in export: {export_forbidden[:20]}", file=sys.stderr)
        return 3

    # 3) Match + payloads
    matches: list[MatchResult] = []
    payloads: list[dict[str, Any]] = []

    for p in products:
        sku = _norm_sku(p.get("sku"))
        shop, via, notes = resolve_shopmill_match(sku, by_sku, by_base)
        if shop is None:
            status = "ambiguous" if via == "ambiguous" else "unmatched"
            matches.append(
                MatchResult(
                    product_id=int(p["id"]),
                    sku=sku,
                    name=p.get("name") or "",
                    status=status,
                    notes=notes,
                )
            )
            continue

        raw_specs = shop.get("specifications") or {}
        if not raw_specs:
            matches.append(
                MatchResult(
                    product_id=int(p["id"]),
                    sku=sku,
                    name=p.get("name") or "",
                    status="skipped_no_specs",
                    shopmill_sku=_norm_sku(shop.get("sku")),
                    source_url=shop.get("source_url"),
                    notes=notes + ["shopmill_empty_attributes"],
                )
            )
            continue

        shop_tech, shop_extras, _hints = map_shopmill_attributes(raw_specs)
        payload, audit = build_payload(p, shop)
        mr = MatchResult(
            product_id=int(p["id"]),
            sku=sku,
            name=p.get("name") or "",
            status="matched",
            shopmill_sku=_norm_sku(shop.get("sku")),
            source_url=shop.get("source_url"),
            shopmill_specs={**shop_tech, **{f"attr:{k}": v for k, v in list(shop_extras.items())[:8]}},
            notes=notes + [f"via:{via}"],
        )
        if not payload:
            mr.status = "already_complete"
            mr.notes.append("no_content_changes")
            matches.append(mr)
            continue
        matches.append(mr)
        payloads.append(
            {
                "id": p["id"],
                "sku": sku,
                "shopmill_sku": mr.shopmill_sku,
                "source_url": mr.source_url,
                "match_via": via,
                "payload": payload,
                "audit": audit,
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
                "shopmill_sku": m.shopmill_sku or "",
                "source_url": m.source_url or "",
                "range": m.shopmill_specs.get("range", ""),
                "accuracy": m.shopmill_specs.get("accuracy", ""),
                "resolution": m.shopmill_specs.get("resolution", ""),
                "notes": "|".join(m.notes),
            }
            for m in matches
        ],
        [
            "id",
            "sku",
            "name",
            "status",
            "shopmill_sku",
            "source_url",
            "range",
            "accuracy",
            "resolution",
            "notes",
        ],
    )

    dry_path = out / "dry_run_payloads.jsonl"
    with dry_path.open("w", encoding="utf-8") as f:
        for row in payloads:
            assert_payload_safe(row["payload"], context=f"dry sku={row['sku']}")
            # Ensure nested payload also commerce-free
            nested_hits = count_forbidden_in_obj(row["payload"])
            if nested_hits:
                raise RuntimeError(f"commerce in payload {row['sku']}: {nested_hits}")
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    payload_forbidden = count_forbidden_in_obj([r["payload"] for r in payloads])

    # Sample before/after for report
    samples = []
    for row in payloads[:5]:
        samples.append(
            {
                "sku": row["sku"],
                "payload_keys": row["audit"]["payload_keys"],
                "filled": row["audit"]["filled"],
                "source_url": row.get("source_url"),
            }
        )

    summary: dict[str, Any] = {
        "api": API,
        "source": SOURCE_LABEL,
        "brand_id": args.brand_id,
        "shopmill_rows": len(shop_rows),
        "catalog_insize": len(products),
        "match_counts": dict(status_counts),
        "matched": status_counts.get("matched", 0) + status_counts.get("already_complete", 0),
        "payloads": len(payloads),
        "enriched_would_write": len(payloads),
        "skipped": {
            "unmatched": status_counts.get("unmatched", 0),
            "ambiguous": status_counts.get("ambiguous", 0),
            "skipped_no_specs": status_counts.get("skipped_no_specs", 0),
            "already_complete": status_counts.get("already_complete", 0),
        },
        "apply": bool(args.apply),
        "applied": 0,
        "apply_errors": 0,
        "fields_written": sorted(ALLOWED_PUT_KEYS),
        "commerce_policy": {
            "forbidden_keys": sorted(FORBIDDEN_PAYLOAD_KEYS),
            "allowed_put_keys": sorted(ALLOWED_PUT_KEYS),
            "export_forbidden_count": len(export_forbidden),
            "payload_forbidden_count": len(payload_forbidden),
            "zero_price_writes": len(payload_forbidden) == 0,
        },
        "samples": samples,
        "paths": {
            "crawl_jsonl": str(crawl_path),
            "site_export": str(export_path),
            "match_report": str(match_csv),
            "dry_run_payloads": str(dry_path),
        },
    }

    if payload_forbidden:
        print(f"ERROR: commerce in payloads: {payload_forbidden[:20]}", file=sys.stderr)
        (out / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return 3

    # 4) Apply
    apply_rows: list[dict] = []
    if args.apply:
        if not args.apply_confirm:
            print("ERROR: --apply requires --apply-confirm", file=sys.stderr)
            return 2
        to_apply = payloads[: args.apply_limit] if args.apply_limit else payloads
        # Resume: skip ids already ok in applied.csv
        applied_path = out / "applied.csv"
        done_ids: set[int] = set()
        if applied_path.exists() and not args.force:
            with applied_path.open(encoding="utf-8-sig", newline="") as fh:
                for prev in csv.DictReader(fh):
                    if str(prev.get("ok") or "").strip().lower() in {"true", "1", "yes"}:
                        try:
                            done_ids.add(int(prev["id"]))
                        except (TypeError, ValueError, KeyError):
                            pass
            if done_ids:
                before = len(to_apply)
                to_apply = [r for r in to_apply if int(r["id"]) not in done_ids]
                print(f"[apply] resume skip_done={before - len(to_apply)} remaining={len(to_apply)}")

        print(f"[apply] writing {len(to_apply)} products…")
        for i, row in enumerate(to_apply, 1):
            pid = row["id"]
            payload = row["payload"]
            assert_payload_safe(payload, context=f"apply sku={row['sku']}")
            st, resp = 0, {}
            for attempt in range(3):
                try:
                    st, resp = http_json(
                        "PUT",
                        f"{API}/products/{pid}",
                        data=payload,
                        headers=auth,
                        timeout=90,
                    )
                except Exception as exc:  # noqa: BLE001
                    st, resp = 0, {"error": str(exc)[:300]}
                if st == 401:
                    print(f"[apply] token expired at {row['sku']} — re-login…", flush=True)
                    auth = {"Authorization": f"Bearer {login()}"}
                    continue
                if st in (0, 429, 502, 503, 504) and attempt + 1 < 3:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                break
            ok = st in (200, 201)
            apply_rows.append(
                {
                    "id": pid,
                    "sku": row["sku"],
                    "http_status": st,
                    "ok": ok,
                    "payload_keys": "|".join(sorted(payload.keys())),
                    "price_fields_written": "none",
                    "error": "" if ok else json.dumps(resp, ensure_ascii=False)[:300],
                }
            )
            if ok:
                summary["applied"] += 1
            else:
                summary["apply_errors"] += 1
                print(f"[apply] FAIL {row['sku']} {st} {resp}", flush=True)
            if i % 25 == 0 or i == len(to_apply):
                print(
                    f"[apply] progress {i}/{len(to_apply)} ok={summary['applied']} err={summary['apply_errors']}",
                    flush=True,
                )
                # Checkpoint applied.csv so resume survives mid-run kills
                checkpoint = apply_rows
                if applied_path.exists() and not args.force:
                    prev = list(csv.DictReader(applied_path.open(encoding="utf-8-sig")))
                    by_id = {str(r.get("id")): r for r in prev}
                    for r in apply_rows:
                        by_id[str(r["id"])] = r
                    checkpoint = list(by_id.values())
                write_csv(
                    applied_path,
                    checkpoint,
                    [
                        "id",
                        "sku",
                        "http_status",
                        "ok",
                        "payload_keys",
                        "price_fields_written",
                        "error",
                    ],
                )
            time.sleep(args.sleep)

        # Append or write apply report
        apply_csv = out / "apply_report.csv"
        write_csv(
            apply_csv,
            apply_rows,
            ["id", "sku", "http_status", "ok", "payload_keys", "price_fields_written", "error"],
        )
        # Merge into applied.csv for resume
        all_applied = apply_rows
        if applied_path.exists() and not args.force:
            # rewrite combined
            prev = list(csv.DictReader(applied_path.open(encoding="utf-8-sig")))
            by_id = {str(r.get("id")): r for r in prev}
            for r in apply_rows:
                by_id[str(r["id"])] = r
            all_applied = list(by_id.values())
        write_csv(
            applied_path,
            all_applied,
            ["id", "sku", "http_status", "ok", "payload_keys", "price_fields_written", "error"],
        )
        summary["paths"]["apply_report"] = str(apply_csv)
        summary["paths"]["applied"] = str(applied_path)

    summary_path = out / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    # Also dump match details
    (out / "matches.jsonl").write_text(
        "\n".join(json.dumps(asdict(m), ensure_ascii=False) for m in matches) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary.get("apply_errors", 0) == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default=str(OUT_DIR),
        help="Report directory",
    )
    parser.add_argument(
        "--crawl-jsonl",
        default=str(OUT_DIR / "shopmill_insize.jsonl"),
        help="Path to commerce-stripped shopmill crawl JSONL",
    )
    parser.add_argument("--crawl", action="store_true", help="Force fresh shopmill crawl")
    parser.add_argument("--reuse-crawl", action="store_true", help="Reuse existing crawl JSONL")
    parser.add_argument("--crawl-sleep", type=float, default=0.7)
    parser.add_argument("--brand-id", type=int, default=INSIZE_BRAND_ID)
    parser.add_argument("--limit", type=int, default=None, help="Limit site export (debug)")
    parser.add_argument("--reuse-export", action="store_true")
    parser.add_argument(
        "--site-inventory",
        default=None,
        help="Path to commerce-stripped site inventory JSON (skips live detail fetch)",
    )
    parser.add_argument("--workers", type=int, default=12, help="Detail fetch workers")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Default mode")
    parser.add_argument("--apply", action="store_true", help="Write content-only PUTs")
    parser.add_argument(
        "--apply-confirm",
        action="store_true",
        help="Required together with --apply",
    )
    parser.add_argument("--apply-limit", type=int, default=None)
    parser.add_argument("--force", action="store_true", help="Ignore applied.csv resume")
    parser.add_argument("--sleep", type=float, default=0.25, help="Delay between PUTs")
    args = parser.parse_args()
    if args.apply:
        args.dry_run = False
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
