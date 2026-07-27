#!/usr/bin/env python3
"""High-accuracy Dohre (دوهره) catalog enrichment from official dohrecnc.com.

Policy (PIM / SEO / AI-pipeline Fact-check):
  - Very-high SKU/model match only (exact catalog SKU ↔ official model code).
  - Never invent specs; only extract fields present on the matched official page/PDF.
  - Merge into specifications.technical_specs (fill empty; never overwrite conflicts).
  - Separate ``short_description``; optional factual long ``description``; ``meta_*``.
  - Staging writes via admin API; dry-run by default.
  - HARD: never read/write commerce money or stock fields (price, sale_price,
    list_price, discount, stock qty, availability). PUT bodies are allowlisted
    enrichment keys only.

Examples:
  python scripts/dohre_official_catalog_enrich.py --dry-run
  python scripts/dohre_official_catalog_enrich.py --apply --limit 25

Reports: data/imports/dohre/official_catalog/
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
    render_short_description_template,
)

API = os.getenv("KARZAR_API_BASE", "https://api.karzartools.com/api/v1")
UA = "KarzarDohreOfficialCatalogEnrich/1.0"
BRAND_ID_DEFAULT = 9  # DOHRE | دوهره
OFFICIAL_BASE = "https://www.dohrecnc.com"
OUT_DIR = _ROOT / "data" / "imports" / "dohre" / "official_catalog"

# Commerce / inventory — never persist from API reads, never send on PUT.
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

# Official Dohre series model codes (PEX/TEX/…); exact alphanumeric tokens only.
MODEL_RE = re.compile(
    r"\b((?:[PTUHDMAC]EX|CBN|PCD)[-_]?\d{2,8}[A-Za-z0-9-]*)\b",
    re.IGNORECASE,
)


@dataclass
class OfficialSpec:
    model: str
    source_url: str
    specs: dict[str, str] = field(default_factory=dict)
    title: str = ""
    notes: list[str] = field(default_factory=list)


@dataclass
class MatchResult:
    product_id: int
    sku: str
    name: str
    status: str
    official_model: str | None = None
    official_specs: dict[str, str] = field(default_factory=dict)
    source_url: str | None = None
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


def normalize_model(code: str) -> str:
    return re.sub(r"[\s_]+", "-", code.strip().upper())


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
            if k and v:
                out[k] = v
    elif isinstance(technical, dict):
        for k, v in technical.items():
            if v is None:
                continue
            sv = str(v).strip()
            if sv:
                out[str(k)] = sv
    return out


SPEC_ALIASES = {
    "flutes": ["flutes", "تعداد شیار", "تعداد لبه"],
    "coating": ["coating", "پوشش"],
    "shank_diameter": ["shank_diameter", "قطر دنباله", "قطر شنک"],
    "cutting_diameter": ["cutting_diameter", "قطر برش", "قطر"],
    "overall_length": ["overall_length", "طول کلی", "طول کل"],
    "workpiece_material": ["workpiece_material", "ماده کار", "کاربرد"],
    "helix_angle": ["helix_angle", "زاویه هلیکس"],
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
    for fa, en in zip("۰۱۲۳۴۵۶۷۸۹", "0123456789", strict=True):
        s = s.replace(fa, en)
    return s


def merge_technical_specs(
    existing_specs: dict[str, Any] | None,
    official_specs: dict[str, str],
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

    for canon, value in official_specs.items():
        value = value.strip()
        if not value:
            continue
        hit = existing_has_key(tech, canon)
        if hit:
            old = tech[hit].strip()
            if old and _norm_spec_val(old) != _norm_spec_val(value):
                notes.append(f"keep_existing_{canon}:{old}|official:{value}")
                continue
            if old:
                notes.append(f"unchanged_{canon}")
                continue
        tech[canon] = value
        filled[canon] = value

    result = {
        "technical_specs": tech,
        "features": base["features"] if isinstance(base["features"], dict) else {},
        "dimensions": base["dimensions"] if isinstance(base["dimensions"], dict) else {},
        "optional_accessories": base.get("optional_accessories") or [],
    }
    return result, notes, filled


def persian_short_description(
    *,
    name: str,
    brand_name: str | None,
    category_name: str | None,
    sku: str,
    tech: dict[str, str],
) -> str | None:
    parts: list[str] = []
    if category_name:
        parts.append(f"{category_name} برند دوهره")
    else:
        parts.append("ابزار CNC برند دوهره")

    facts: list[str] = []
    if tech.get("series"):
        facts.append(f"سری {tech['series']}")
    if tech.get("cutting_diameter") or tech.get("قطر برش"):
        facts.append(f"قطر برش: {tech.get('cutting_diameter') or tech.get('قطر برش')}")
    if tech.get("flutes") or tech.get("تعداد شیار"):
        facts.append(f"تعداد شیار: {tech.get('flutes') or tech.get('تعداد شیار')}")
    if tech.get("coating") or tech.get("پوشش"):
        facts.append(f"پوشش: {tech.get('coating') or tech.get('پوشش')}")
    if tech.get("workpiece_material") or tech.get("ماده کار"):
        facts.append(f"کاربرد: {tech.get('workpiece_material') or tech.get('ماده کار')}")
    if facts:
        parts.append("؛ ".join(facts))
    if sku:
        parts.append(f"کد {sku}")

    body = " — ".join(parts)
    if is_stub_description(body, product_name=name):
        preview = render_short_description_template(
            name=name,
            brand_name=brand_name or "DOHRE | دوهره",
            category_name=category_name,
            sku=sku,
            technical_specs=tech,
        )
        if preview and not is_stub_description(preview, product_name=name):
            return preview[:500]
        return None
    return body[:500]


def persian_long_description(
    *,
    category_name: str | None,
    sku: str,
    tech: dict[str, str],
    source_url: str | None,
) -> str | None:
    if not tech:
        return None
    lines = [f"{category_name or 'ابزار فرزکاری CNC'} دوهره با کد {sku}."]
    lines.append("مشخصات طبق منبع رسمی Dohre CNC:")
    label_fa = {
        "series": "سری",
        "cutting_diameter": "قطر برش",
        "shank_diameter": "قطر دنباله",
        "overall_length": "طول کلی",
        "flutes": "تعداد شیار",
        "coating": "پوشش",
        "helix_angle": "زاویه هلیکس",
        "workpiece_material": "ماده کار",
    }
    for key, label in label_fa.items():
        if tech.get(key):
            lines.append(f"- {label}: {tech[key]}")
    if source_url:
        lines.append(f"منبع: {source_url}")
    lines.append("مقادیر فقط از تطبیق خیلی‌بالای مدل رسمی استخراج شده‌اند؛ بدون حدس.")
    return "\n".join(lines)[:4000]


def meta_title_for(name: str, sku: str) -> str:
    base = name.strip() or f"دوهره {sku}"
    if sku and sku not in base:
        base = f"{base} | {sku}"
    return base[:255]


def meta_description_for(short: str | None, name: str, sku: str) -> str:
    if short and not is_stub_description(short, product_name=name):
        return short[:500]
    return f"{name} | دوهره کد {sku}"[:500]


def fetch_dohre_products(auth: dict, *, brand_id: int, limit: int | None) -> list[dict]:
    """Export active Dohre products; strip commerce fields before return."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    ids: list[int] = []
    skip = 0
    while True:
        batch_limit = 100
        st, resp = http_json(
            "GET",
            f"{API.rstrip('/')}/products/?brand_id={brand_id}&limit={batch_limit}&skip={skip}",
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
        if skip >= total or len(batch) < batch_limit:
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
    return products


def load_official_index(out: Path) -> dict[str, OfficialSpec]:
    """Build model→OfficialSpec from crawled product_pages / source_index."""
    by_model: dict[str, OfficialSpec] = {}

    product_pages = out / "product_pages.json"
    series_index = out / "series_index.json"
    source_index = out / "source_index.json"

    records: list[dict] = []
    if product_pages.exists():
        records.extend(json.loads(product_pages.read_text(encoding="utf-8")))
    if series_index.exists():
        records.extend(json.loads(series_index.read_text(encoding="utf-8")))

    for rec in records:
        if not isinstance(rec, dict) or rec.get("error"):
            continue
        url = str(rec.get("url") or "")
        title = str(rec.get("title") or "")
        facts = rec.get("facts") if isinstance(rec.get("facts"), dict) else {}
        models = rec.get("models") or []
        # Infer series from URL / title when no SKU-level model.
        series = None
        m = re.search(
            r"(pex|tex|uex|hex|dex|mex|aex|cbn|pcd)(?:-series)?",
            url + " " + title,
            re.I,
        )
        if m:
            series = m.group(1).upper()

        clean_facts = {
            str(k): str(v).strip()
            for k, v in facts.items()
            if v and str(v).strip() and str(k) not in FORBIDDEN_COMMERCE_KEYS
        }
        if series and "series" not in clean_facts:
            clean_facts["series"] = series

        for raw in models:
            model = normalize_model(str(raw))
            if not MODEL_RE.fullmatch(model) and not MODEL_RE.match(model):
                continue
            if model in by_model and by_model[model].specs and not clean_facts:
                continue
            by_model[model] = OfficialSpec(
                model=model,
                source_url=url,
                specs=dict(clean_facts),
                title=title,
            )

    # Also scan saved HTML pages for model tokens (high-confidence codes only).
    pages_dir = out / "pages"
    if pages_dir.exists():
        for html_path in pages_dir.glob("*.html"):
            text = html_path.read_text(encoding="utf-8", errors="ignore")
            for m in MODEL_RE.finditer(text):
                model = normalize_model(m.group(1))
                if model not in by_model:
                    by_model[model] = OfficialSpec(
                        model=model,
                        source_url=f"local:{html_path.name}",
                        specs={},
                        title="",
                        notes=["model_token_from_html_only"],
                    )

    if source_index.exists():
        # Touch file for audit trail; models already covered above.
        _ = json.loads(source_index.read_text(encoding="utf-8"))

    return by_model


def match_sku_to_official(
    sku: str, name: str, by_model: dict[str, OfficialSpec]
) -> tuple[OfficialSpec | None, list[str]]:
    """Very-high confidence only: exact SKU == model, or SKU contained as whole model token."""
    notes: list[str] = []
    if not sku:
        return None, ["empty_sku"]

    candidates = {
        normalize_model(sku),
        normalize_model(sku.replace(" ", "")),
    }
    # Strip common internal prefixes if present (SO- style not used; keep conservative).
    for c in list(candidates):
        candidates.add(c.replace("_", "-"))

    for c in candidates:
        if c in by_model:
            return by_model[c], notes

    # Exact model token inside name (word boundary).
    for model, spec in by_model.items():
        if re.search(rf"(?<![A-Z0-9-]){re.escape(model)}(?![A-Z0-9-])", normalize_model(name)):
            notes.append("matched_via_name_token")
            return spec, notes
        if re.search(rf"(?<![A-Z0-9-]){re.escape(model)}(?![A-Z0-9-])", normalize_model(sku)):
            notes.append("matched_via_sku_token")
            return spec, notes

    return None, ["no_exact_model_match"]


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def coverage_flags(p: dict) -> dict[str, Any]:
    name = p.get("name") or ""
    short = p.get("short_description")
    long = p.get("description")
    tech = specs_to_dict(p.get("specifications"))
    return {
        "has_short": bool(short and not is_stub_description(short, product_name=name)),
        "has_long_stub": bool(long and is_stub_description(long, product_name=name)),
        "has_long_ok": bool(long and not is_stub_description(long, product_name=name)),
        "has_meta_title": bool((p.get("meta_title") or "").strip()),
        "has_meta_description": bool((p.get("meta_description") or "").strip()),
        "tech_keys": "|".join(sorted(tech.keys())),
        "tech_count": len(tech),
    }


def build_payload(
    product: dict, official: OfficialSpec
) -> tuple[dict[str, Any], dict[str, Any]]:
    name = product.get("name") or ""
    sku = product.get("sku") or ""
    brand = product.get("brand") if isinstance(product.get("brand"), dict) else {}
    cat = product.get("category") if isinstance(product.get("category"), dict) else {}
    brand_name = brand.get("name")
    category_name = cat.get("name")

    merged_specs, merge_notes, filled = merge_technical_specs(
        product.get("specifications"), official.specs
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
    if not short or is_stub_description(short, product_name=name):
        new_short = persian_short_description(
            name=name,
            brand_name=brand_name,
            category_name=category_name,
            sku=sku,
            tech=tech_flat,
        )

    new_long = None
    if not long or is_stub_description(long, product_name=name):
        new_long = persian_long_description(
            category_name=category_name,
            sku=sku,
            tech=tech_flat,
            source_url=official.source_url,
        )

    new_meta_title = None
    if not (meta_title or "").strip():
        new_meta_title = meta_title_for(name, sku)

    new_meta_desc = None
    if not (meta_desc or "").strip():
        new_meta_desc = meta_description_for(new_short or short, name, sku)

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
        "source_url": official.source_url,
        "forbidden_hits_in_payload": count_forbidden_in_obj(payload),
    }
    return payload, audit


def run(args: argparse.Namespace) -> int:
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"API: {API}")
    print(f"Official: {OFFICIAL_BASE}")
    print(f"Out: {out}")
    print(f"Mode: {'APPLY' if args.apply else 'dry-run'}")
    print(
        "HARD: PUT allowlist = short_description,description,meta_*,specifications; "
        "zero price/stock reads persisted or written."
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
        products = fetch_dohre_products(auth, brand_id=args.brand_id, limit=args.limit)
        with export_path.open("w", encoding="utf-8") as f:
            for p in products:
                # Defense-in-depth: never persist commerce fields to disk.
                safe = sanitize_product_export(p)
                hits = count_forbidden_in_obj(safe)
                if hits:
                    raise RuntimeError(f"commerce leak in export: {hits}")
                f.write(json.dumps(safe, ensure_ascii=False) + "\n")
        csv_rows = []
        for p in products:
            flags = coverage_flags(p)
            csv_rows.append(
                {
                    "id": p.get("id"),
                    "sku": p.get("sku"),
                    "name": p.get("name"),
                    "is_active": p.get("is_active"),
                    "short_description": (p.get("short_description") or "")[:120],
                    "description": (p.get("description") or "")[:120],
                    "meta_title": p.get("meta_title") or "",
                    "meta_description": (p.get("meta_description") or "")[:120],
                    **flags,
                }
            )
        write_csv(
            export_csv,
            csv_rows,
            [
                "id",
                "sku",
                "name",
                "is_active",
                "short_description",
                "description",
                "meta_title",
                "meta_description",
                "has_short",
                "has_long_stub",
                "has_long_ok",
                "has_meta_title",
                "has_meta_description",
                "tech_keys",
                "tech_count",
            ],
        )
        print(f"[export] {len(products)} products -> {export_path}")

    by_model = load_official_index(out)
    index_path = out / "official_model_index.jsonl"
    with index_path.open("w", encoding="utf-8") as f:
        for model, spec in sorted(by_model.items()):
            f.write(
                json.dumps(
                    {
                        "model": model,
                        "source_url": spec.source_url,
                        "title": spec.title,
                        "specs": spec.specs,
                        "notes": spec.notes,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    print(f"[official] indexed models: {len(by_model)}")

    matches: list[MatchResult] = []
    payloads: list[dict[str, Any]] = []

    if not products:
        print("[blocker] brand present but 0 active SKUs — nothing to enrich")
    for p in products:
        sku = str(p.get("sku") or "").strip()
        name = p.get("name") or ""
        official, notes = match_sku_to_official(sku, name, by_model)
        if not official:
            matches.append(
                MatchResult(
                    product_id=int(p["id"]),
                    sku=sku,
                    name=name,
                    status="unmatched",
                    notes=notes,
                )
            )
            continue
        if not official.specs and "model_token_from_html_only" in official.notes:
            matches.append(
                MatchResult(
                    product_id=int(p["id"]),
                    sku=sku,
                    name=name,
                    status="matched_no_specs",
                    official_model=official.model,
                    source_url=official.source_url,
                    notes=notes + official.notes,
                )
            )
            # Still allow meta/short from series-only if series present — else skip payload.
            if not official.specs.get("series"):
                continue

        mr = MatchResult(
            product_id=int(p["id"]),
            sku=sku,
            name=name,
            status="matched",
            official_model=official.model,
            official_specs=official.specs,
            source_url=official.source_url,
            notes=notes,
        )
        matches.append(mr)
        payload, audit = build_payload(p, official)
        if payload:
            payloads.append(
                {
                    "id": p["id"],
                    "sku": sku,
                    "payload": payload,
                    "audit": audit,
                    "official_specs": official.specs,
                    "source_url": official.source_url,
                }
            )

    status_counts = Counter(m.status for m in matches)
    print(f"[match] {dict(status_counts)}")
    print(f"[payloads] ready={len(payloads)}")

    # Verify zero commerce keys across all payloads.
    commerce_violations = []
    for row in payloads:
        hits = count_forbidden_in_obj(row["payload"])
        if hits:
            commerce_violations.append({"id": row["id"], "sku": row["sku"], "hits": hits})
        assert_payload_safe(row["payload"])

    match_csv = out / "match_report.csv"
    write_csv(
        match_csv,
        [
            {
                "id": m.product_id,
                "sku": m.sku,
                "name": m.name,
                "status": m.status,
                "official_model": m.official_model or "",
                "source_url": m.source_url or "",
                "specs": json.dumps(m.official_specs, ensure_ascii=False),
                "notes": "|".join(m.notes),
            }
            for m in matches
        ],
        [
            "id",
            "sku",
            "name",
            "status",
            "official_model",
            "source_url",
            "specs",
            "notes",
        ],
    )

    dry_path = out / "dry_run_payloads.jsonl"
    with dry_path.open("w", encoding="utf-8") as f:
        for row in payloads:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary: dict[str, Any] = {
        "api": API,
        "official_source": OFFICIAL_BASE,
        "brand_id": args.brand_id,
        "exported": len(products),
        "official_models_indexed": len(by_model),
        "match_counts": dict(status_counts),
        "payloads": len(payloads),
        "apply": bool(args.apply),
        "applied": 0,
        "apply_errors": 0,
        "commerce_policy": {
            "forbidden_keys": sorted(FORBIDDEN_COMMERCE_KEYS),
            "allowed_put_keys": sorted(ALLOWED_PUT_KEYS),
            "price_writes": 0,
            "stock_writes": 0,
            "payload_commerce_violations": commerce_violations,
            "zero_price_writes_confirmed": len(commerce_violations) == 0,
        },
        "blocker": None,
        "paths": {
            "site_export": str(export_path),
            "site_export_csv": str(export_csv),
            "official_model_index": str(index_path),
            "match_report": str(match_csv),
            "dry_run_payloads": str(dry_path),
        },
    }

    if len(products) == 0:
        summary["blocker"] = {
            "code": "zero_skus",
            "message": (
                "Brand DOHRE | دوهره (id=9) exists on api.karzartools.com with "
                "product_count=0. Enrichment payloads cannot be applied until "
                "active SKUs are imported and linked to brand_id=9."
            ),
        }

    apply_rows: list[dict] = []
    if args.apply:
        if not products:
            print("[apply] skipped — 0 SKUs")
        else:
            to_apply = payloads[: args.apply_limit] if args.apply_limit else payloads
            print(f"[apply] writing {len(to_apply)} products (enrichment keys only)…")
            for row in to_apply:
                assert_payload_safe(row["payload"])
                pid = row["id"]
                st, resp = http_json(
                    "PUT",
                    f"{API.rstrip('/')}/products/{pid}",
                    data=row["payload"],
                    headers=auth,
                    timeout=90,
                )
                ok = st in (200, 201)
                apply_rows.append(
                    {
                        "id": pid,
                        "sku": row["sku"],
                        "http_status": st,
                        "ok": ok,
                        "payload_keys": "|".join(sorted(row["payload"].keys())),
                        "error": "" if ok else json.dumps(resp, ensure_ascii=False)[:300],
                    }
                )
                if ok:
                    summary["applied"] += 1
                else:
                    summary["apply_errors"] += 1
                    print(f"[apply] FAIL {row['sku']} {st} {resp}")
                time.sleep(0.08)
            apply_csv = out / "apply_report.csv"
            write_csv(
                apply_csv,
                apply_rows,
                ["id", "sku", "http_status", "ok", "payload_keys", "error"],
            )
            summary["paths"]["apply_report"] = str(apply_csv)

    # Final commerce audit on apply report keys.
    summary["commerce_policy"]["apply_payload_keys_union"] = sorted(
        {k for row in payloads for k in row["payload"]}
    )
    summary["commerce_policy"]["price_writes"] = 0
    summary["commerce_policy"]["stock_writes"] = 0

    summary_path = out / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary.get("apply_errors", 0) == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default=str(OUT_DIR),
        help="Report directory (default: data/imports/dohre/official_catalog)",
    )
    parser.add_argument("--brand-id", type=int, default=BRAND_ID_DEFAULT)
    parser.add_argument("--limit", type=int, default=None, help="Limit export size (debug)")
    parser.add_argument(
        "--reuse-export",
        action="store_true",
        help="Reuse site_export.jsonl if present",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Default mode — build payloads, no writes",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write allowlisted enrichment fields to staging API",
    )
    parser.add_argument(
        "--apply-limit",
        type=int,
        default=None,
        help="Cap number of PUTs when --apply",
    )
    args = parser.parse_args()
    if args.apply:
        args.dry_run = False
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
