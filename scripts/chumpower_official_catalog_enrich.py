#!/usr/bin/env python3
"""High-accuracy Chumpower catalog enrichment from official chuck site.

Official SoT (machine-tool / chucks — NOT PET blow-molding):
  https://www.chumpowerchuck.com/  (catalog PDFs linked from Download;
  assets may be hosted under chumpower.com/UserFiles/down/ — same corp CDN)

HARD CONSTRAINT — commerce fields are forbidden:
  Never read, log, or write: price, base_price, original_price, sale_price,
  list_price, discount, tax_percent, stock_quantity, stock_unit, stock_status,
  availability, is_available, low_stock, or any money/qty commerce field.
  PUT payloads may ONLY contain:
    short_description, description, meta_title, meta_description, specifications

Policy (PIM / SEO / AI-pipeline Fact-check):
  - Very-high model match only: exact Code No. (BA…/BF…) or unique Type/SPEC.
  - Never invent specs; only fields present on the matched official row.
  - Merge technical_specs (fill empty/missing; never overwrite conflicting values).
  - Persian factual copy from confirmed SoT only.
  - Staging writes; dry-run by default; --apply after review.

Examples:
  python scripts/chumpower_official_catalog_enrich.py --dry-run
  python scripts/chumpower_official_catalog_enrich.py --reuse-export --apply --apply-limit 25

Reports: data/imports/chumpower/official_catalog/
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
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
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
UA = "KarzarChumpowerOfficialCatalogEnrich/1.0"
BRAND_ID_DEFAULT = 33  # Chumpower | چام‌پاور
OUT_DIR = _ROOT / "data" / "imports" / "chumpower" / "official_catalog"
OFFICIAL_BASE = "https://www.chumpowerchuck.com/en/"

# --- Commerce / stock: absolute deny-list (read + write) ---
FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "price",
        "base_price",
        "original_price",
        "sale_price",
        "list_price",
        "discount",
        "tax_percent",
        "stock_quantity",
        "stock_unit",
        "stock_status",
        "availability",
        "is_available",
        "low_stock",
    }
)
FORBIDDEN_KEY_SUBSTR = (
    "price",
    "stock",
    "avail",
    "discount",
    "tax_percent",
)
ALLOWED_PAYLOAD_KEYS = frozenset(
    {
        "short_description",
        "description",
        "meta_title",
        "meta_description",
        "specifications",
    }
)

CODE_RE = re.compile(r"^(BA[0-9A-Z]{8,}|BF[0-9A-Z]{8,})$", re.I)
BA_LINE_RE = re.compile(r"^\s*(BA[0-9A-Z]{8,}|BF[0-9A-Z]{8,})\b(.*)$", re.I)


@dataclass
class OfficialRow:
    code: str
    type: str = ""
    url: str = ""
    page: str = ""
    title: str = ""
    fields: dict[str, str] = field(default_factory=dict)
    source: str = ""


@dataclass
class MatchResult:
    product_id: int
    sku: str
    name: str
    status: str  # matched | unmatched | ambiguous
    official_code: str | None = None
    match_via: str | None = None
    official_specs: dict[str, str] = field(default_factory=dict)
    source_url: str | None = None
    notes: list[str] = field(default_factory=list)


def _is_forbidden_key(key: str) -> bool:
    k = key.casefold()
    if k in FORBIDDEN_PAYLOAD_KEYS:
        return True
    return any(s in k for s in FORBIDDEN_KEY_SUBSTR)


def strip_commerce_fields(obj: Any) -> Any:
    """Recursively drop price/stock/availability keys from API objects (export only)."""
    if isinstance(obj, dict):
        return {
            k: strip_commerce_fields(v)
            for k, v in obj.items()
            if not _is_forbidden_key(str(k))
        }
    if isinstance(obj, list):
        return [strip_commerce_fields(x) for x in obj]
    return obj


def assert_payload_commerce_free(payload: dict[str, Any], *, context: str) -> None:
    bad = sorted(k for k in payload if k not in ALLOWED_PAYLOAD_KEYS or _is_forbidden_key(k))
    if bad:
        raise RuntimeError(f"FORBIDDEN commerce/non-SEO keys in {context}: {bad}")


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


def normalize_type(tok: str) -> str:
    return re.sub(r"\s+", "", tok.strip().upper().replace("×", "X").replace("−", "-"))


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
            if k and v and not _is_forbidden_key(k):
                out[k] = v
    elif isinstance(technical, dict):
        for k, v in technical.items():
            if v is None or _is_forbidden_key(str(k)):
                continue
            sv = str(v).strip()
            if sv:
                out[str(k)] = sv
    return out


SPEC_ALIASES = {
    "capacity": ["capacity", "ظرفیت", "سایز مته", "بازه", "range", "Capacity mm"],
    "tap_size": ["tap_size", "سایز قلاویز", "Tap", "TC JIS Tap", "DIN371 Tap", "DIN376 Tap"],
    "shank_diameter": ["shank_diameter", "قطر دنباله", "Tap Shank ØD", "ΦD", "ØD"],
    "shank_square": ["shank_square", "مربع دنباله", "Tap Shank□", "□", "四方孔"],
    "mount": ["mount", "دنباله", "arbor", "Type", "taper", "B", "JT", "MT"],
    "series": ["series", "سری", "TC312", "collet_series"],
    "standard": ["standard", "استاندارد", "DIN", "ISO", "JIS"],
    "length_mm": ["length_mm", "طول", "L", "L1", "L (mm)", "L1 (mm)"],
    "model": ["model", "مدل", "Code No.", "type"],
}


def existing_has_key(existing: dict[str, str], canon: str) -> str | None:
    for alias in SPEC_ALIASES.get(canon, [canon]):
        if alias in existing and existing[alias].strip():
            return alias
    lower = {k.casefold(): k for k in existing}
    for alias in SPEC_ALIASES.get(canon, [canon]):
        if alias.casefold() in lower and existing[lower[alias.casefold()]].strip():
            return lower[alias.casefold()]
    return None


def _norm_spec_val(v: str) -> str:
    s = v.casefold().replace(" ", "").replace("٫", ".").replace("〜", "~").replace("～", "~")
    s = s.replace("×", "x").replace("*", "x").replace("−", "-")
    trans = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
    return s.translate(trans)


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
        if not value or _is_forbidden_key(canon):
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


def _clean_html_noise(val: str) -> str:
    s = val.replace("&nbsp;", " ").replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def fields_to_official_specs(row: OfficialRow) -> dict[str, str]:
    """Map official labeled fields → canonical technical_specs (SoT only)."""
    f = {
        k.strip(): _clean_html_noise(str(v))
        for k, v in row.fields.items()
        if str(v).strip()
    }
    out: dict[str, str] = {}

    if row.code:
        out["model"] = row.code
    if row.type:
        out["type"] = _clean_html_noise(row.type)

    # Prefer explicit labeled fields from HTML speclist.
    mapping = [
        ("capacity", ["Capacity", "Capacity mm", "Capacity inch", "Working Scope", "Tapping Capacity"]),
        ("tap_size", ["Tap", "TC JIS Tap", "DIN371 Tap", "DIN376 Tap", "ISO529 Tap", "ISO529/2283"]),
        ("shank_diameter", ["Tap Shank ØD", "Tap Shank D", "ΦD", "ØD", "Shank ØD"]),
        ("shank_square", ["Tap Shank□", "Tap Shank □", "□", "Tap Shank"]),
        ("length_mm", ["L1 (mm)", "L (mm)", "L1", "L", "Length"]),
        ("mount", ["Mount", "Taper", "Arbor"]),
        ("series", ["Series"]),
        ("standard", ["Standard"]),
    ]
    for canon, keys in mapping:
        for k in keys:
            if k in f and f[k]:
                out[canon] = f[k]
                break

    # Infer series/standard from type / title crumbs when present as tokens.
    blob = " ".join([row.type, row.title, " ".join(f.values())])
    for series in ("TC1433", "TC820", "TC312", "TC308"):
        if series in blob.replace(" ", "").upper() or series in blob.upper():
            out.setdefault("series", series)
            break
    for std in ("DIN371", "DIN 371", "DIN376", "DIN 376", "ISO529", "ISO 529", "JIS", "2283"):
        if std.replace(" ", "").upper() in blob.replace(" ", "").upper():
            out.setdefault("standard", std.replace(" ", ""))
            break

    # PDF raw_tail: keep only when we have little else — extract capacity-like M#~M#
    raw = f.get("raw_tail") or ""
    if raw and "capacity" not in out:
        m = re.search(r"\b(M\d+\s*[~\-〜～]\s*M\d+)\b", raw, re.I)
        if m:
            out["capacity"] = re.sub(r"\s+", "", m.group(1)).replace("〜", "~").replace("～", "~")
    if raw and "length_mm" not in out:
        # Prefer a standalone length token after type (heuristic, only if unique-looking)
        nums = re.findall(r"(?<![\d.])(\d{2,4})(?![\d])", raw)
        # Do not guess — skip numeric-only PDF tails without labels.
        _ = nums

    # Drop empty / forbidden
    return {k: v for k, v in out.items() if v and not _is_forbidden_key(k)}


def persian_short_description(
    *,
    name: str,
    brand_name: str | None,
    category_name: str | None,
    sku: str,
    tech: dict[str, str],
) -> str | None:
    brand_fa = "چام‌پاور"
    if brand_name and "چام" in brand_name:
        brand_fa = "چام‌پاور"
    parts: list[str] = []
    if category_name:
        parts.append(f"{category_name} برند {brand_fa}")
    else:
        parts.append(f"محصول برند {brand_fa}")

    facts: list[str] = []
    if tech.get("type"):
        facts.append(f"تیپ {tech['type']}")
    if tech.get("capacity"):
        facts.append(f"ظرفیت: {tech['capacity']}")
    if tech.get("tap_size"):
        facts.append(f"قلاویز: {tech['tap_size']}")
    if tech.get("shank_diameter"):
        facts.append(f"قطر دنباله: {tech['shank_diameter']}")
    if tech.get("shank_square"):
        facts.append(f"مربع: {tech['shank_square']}")
    if tech.get("series"):
        facts.append(f"سری {tech['series']}")
    if tech.get("standard"):
        facts.append(f"استاندارد {tech['standard']}")
    if tech.get("mount"):
        facts.append(f"دنباله: {tech['mount']}")
    if facts:
        parts.append("؛ ".join(facts))
    if sku:
        parts.append(f"کد {sku}")

    body = " — ".join(parts)
    if is_stub_description(body, product_name=name):
        preview = render_short_description_template(
            name=name,
            brand_name=brand_name or "Chumpower | چام‌پاور",
            category_name=category_name,
            sku=sku,
            technical_specs={
                "range": tech.get("capacity"),
                "اندازه": tech.get("tap_size") or tech.get("type"),
            },
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
    lines = [
        f"{category_name or 'ابزار ماشین‌کاری'} چام‌پاور با کد {sku}.",
    ]
    facts = []
    label_map = [
        ("model", "کد سازنده"),
        ("type", "تیپ"),
        ("capacity", "ظرفیت"),
        ("tap_size", "سایز قلاویز"),
        ("shank_diameter", "قطر دنباله قلاویز"),
        ("shank_square", "مقطع مربع دنباله"),
        ("series", "سری فشنگی"),
        ("standard", "استاندارد"),
        ("mount", "دنباله/نصب"),
        ("length_mm", "طول (mm)"),
    ]
    for key, label in label_map:
        if tech.get(key):
            facts.append(f"{label}: {tech[key]}")
    if not facts:
        return None
    lines.append("مشخصات طبق کاتالوگ رسمی برند Chumpower Machinery:")
    lines.extend(f"- {f}" for f in facts)
    if source_url:
        lines.append(f"منبع: {source_url}")
    lines.append("مقادیر فقط از ردیف هم‌کد/تیپ یکتای رسمی استخراج شده‌اند؛ هیچ قیمت یا موجودی‌ای ثبت نشده است.")
    return "\n".join(lines)[:4000]


def meta_title_for(name: str, sku: str) -> str:
    base = name.strip() or f"چام‌پاور {sku}"
    if sku and sku not in base:
        base = f"{base} | {sku}"
    return base[:255]


def meta_description_for(short: str | None, name: str, sku: str) -> str:
    if short and not is_stub_description(short, product_name=name):
        return short[:500]
    return f"{name} | چام‌پاور کد {sku}"[:500]


def load_official_index(out: Path) -> tuple[dict[str, OfficialRow], dict[str, str]]:
    """Load code→row and unique type→code maps from prior crawl artifacts."""
    lookup_path = out / "official_model_lookup.json"
    type_path = out / "official_unique_type_map.json"
    by_code: dict[str, OfficialRow] = {}
    type_map: dict[str, str] = {}

    if lookup_path.exists():
        raw = json.loads(lookup_path.read_text(encoding="utf-8"))
        for code, r in raw.items():
            by_code[code.upper()] = OfficialRow(
                code=str(r.get("code") or code).upper(),
                type=str(r.get("type") or ""),
                url=str(r.get("url") or ""),
                page=str(r.get("page") or ""),
                title=str(r.get("title") or ""),
                fields={str(k): str(v) for k, v in (r.get("fields") or {}).items()},
                source=str(r.get("source") or ""),
            )

    if type_path.exists():
        raw_t = json.loads(type_path.read_text(encoding="utf-8"))
        for t, codes in raw_t.items():
            if isinstance(codes, list) and len(codes) == 1:
                type_map[normalize_type(t)] = str(codes[0]).upper()
            elif isinstance(codes, str):
                type_map[normalize_type(t)] = codes.upper()

    # Rebuild unique type map from by_code if needed
    if by_code and not type_map:
        buckets: dict[str, set[str]] = defaultdict(set)
        for code, row in by_code.items():
            if row.type:
                buckets[normalize_type(row.type)].add(code)
            # Also index Type field
            for k in ("Type", "SPEC", "SPEC."):
                if row.fields.get(k):
                    buckets[normalize_type(row.fields[k])].add(code)
        type_map = {t: next(iter(codes)) for t, codes in buckets.items() if len(codes) == 1}

    return by_code, type_map


def rebuild_official_index_from_disk(out: Path) -> tuple[dict[str, OfficialRow], dict[str, str]]:
    """Parse cached HTML details + PDF texts into lookup files."""
    detail_dir = Path("/tmp/chumpower_crawl/details")
    pdf_dir = out / "pdf_text"
    rows: list[OfficialRow] = []
    by_code: dict[str, OfficialRow] = {}
    type_buckets: dict[str, set[str]] = defaultdict(set)

    if detail_dir.exists():
        for p in sorted(detail_dir.glob("products_i_*.html")):
            html = p.read_text(encoding="utf-8", errors="ignore")
            title_m = re.search(r"<title>([^<]+)</title>", html, re.I)
            title = title_m.group(1).strip() if title_m else p.stem
            blocks = re.findall(r"<div class=['\"]speclist_i['\"]>([\s\S]*?)</div>", html)
            for b in blocks:
                hm = re.search(r"<h6>([^<]+)</h6>", b)
                if not hm:
                    continue
                code = hm.group(1).strip().upper()
                fields: dict[str, str] = {}
                for km in re.finditer(r"([A-Za-zØΦ□ /()\-]{1,40}):\s*([^<\n]+)", b):
                    k = km.group(1).strip()
                    v = re.sub(r"\s+", " ", km.group(2)).strip()
                    if v and not _is_forbidden_key(k):
                        fields[k] = v
                typ = fields.get("Type") or fields.get("SPEC") or fields.get("SPEC.") or ""
                row = OfficialRow(
                    code=code,
                    type=typ,
                    url=OFFICIAL_BASE + p.name,
                    page=p.name,
                    title=title,
                    fields=fields,
                    source="html_speclist",
                )
                rows.append(row)
                by_code[code] = row
                if typ:
                    type_buckets[normalize_type(typ)].add(code)

    if pdf_dir.exists():
        for p in sorted(pdf_dir.glob("*.txt")):
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                m = BA_LINE_RE.match(line)
                if not m:
                    continue
                code = m.group(1).upper()
                rest = m.group(2).strip()
                toks = [t for t in re.split(r"\s{2,}|\t+", rest) if t.strip()]
                if not toks:
                    toks = [t for t in rest.split() if t]
                typ = toks[0] if toks else ""
                # Prefer HTML row when present; else add PDF.
                if code not in by_code:
                    row = OfficialRow(
                        code=code,
                        type=typ,
                        url=f"pdf:{p.name}#{i}",
                        page=p.name,
                        title="",
                        fields={"raw_tail": rest[:400]},
                        source="pdf",
                    )
                    rows.append(row)
                    by_code[code] = row
                if typ:
                    type_buckets[normalize_type(typ)].add(code)

    type_map = {t: next(iter(codes)) for t, codes in type_buckets.items() if len(codes) == 1}

    lookup = {
        code: {
            "code": r.code,
            "type": r.type,
            "url": r.url,
            "page": r.page,
            "title": r.title,
            "fields": r.fields,
            "source": r.source,
        }
        for code, r in by_code.items()
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "official_model_lookup.json").write_text(
        json.dumps(lookup, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "official_unique_type_map.json").write_text(
        json.dumps({t: [c] for t, c in type_map.items()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (out / "official_model_index.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
    print(f"[index] codes={len(by_code)} unique_types={len(type_map)}")
    return by_code, type_map


def fetch_chumpower_products(auth: dict, *, brand_id: int, limit: int | None) -> list[dict]:
    """Export active Chumpower products with commerce fields stripped."""
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

    print(f"[export] listed {len(ids)} ids; fetching details (commerce-stripped)…")

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
        return strip_commerce_fields(detail)

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


def resolve_match(
    sku: str,
    by_code: dict[str, OfficialRow],
    type_map: dict[str, str],
) -> tuple[OfficialRow | None, str | None, list[str]]:
    """Very-high confidence only."""
    notes: list[str] = []
    sku_u = sku.strip().upper()
    if not sku_u:
        return None, None, ["empty_sku"]

    if sku_u in by_code:
        return by_code[sku_u], "exact_code", notes

    # Type / SPEC unique match (including length-suffixed types like JT2S-SF12-61L)
    nt = normalize_type(sku_u)
    if nt in type_map and type_map[nt] in by_code:
        return by_code[type_map[nt]], "exact_unique_type", notes

    # Strip trailing -NNL length suffix and retry type if unique
    m = re.match(r"^(.+)-(\d{2,4})L?$", sku_u)
    if m:
        base_t = normalize_type(m.group(1))
        if base_t in type_map and type_map[base_t] in by_code:
            row = by_code[type_map[base_t]]
            # Confirm length appears in official fields/raw if present
            length = m.group(2)
            blob = json.dumps(row.fields, ensure_ascii=False) + " " + row.type
            if length in blob or not row.fields:
                notes.append(f"type_base_with_length:{length}")
                return row, "unique_type_plus_length", notes
            notes.append("length_not_confirmed_on_official_row")

    return None, None, notes


def build_payload(
    product: dict, row: OfficialRow
) -> tuple[dict[str, Any], dict[str, Any]]:
    name = product.get("name") or ""
    sku = product.get("sku") or ""
    brand = product.get("brand") if isinstance(product.get("brand"), dict) else {}
    cat = product.get("category") if isinstance(product.get("category"), dict) else {}
    brand_name = brand.get("name")
    category_name = cat.get("name")

    official_specs = fields_to_official_specs(row)
    merged_specs, merge_notes, filled = merge_technical_specs(
        product.get("specifications"), official_specs
    )
    tech_flat = {
        str(k): str(v)
        for k, v in (merged_specs.get("technical_specs") or {}).items()
        if v is not None and str(v).strip() and not _is_forbidden_key(str(k))
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
            source_url=row.url or None,
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

    assert_payload_commerce_free(payload, context=f"sku={sku}")

    audit = {
        "filled_specs": filled,
        "merge_notes": merge_notes,
        "official_specs": official_specs,
        "new_short": new_short,
        "new_long": bool(new_long),
        "new_meta_title": bool(new_meta_title),
        "new_meta_description": bool(new_meta_desc),
        "payload_keys": sorted(payload.keys()),
        "commerce_keys_written": [],  # explicit zero
        "source_url": row.url,
        "official_code": row.code,
    }
    return payload, audit


def run(args: argparse.Namespace) -> int:
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"API: {API}")
    print(f"Out: {out}")
    print(f"Mode: {'APPLY' if args.apply else 'dry-run'}")
    print("Commerce fields: FORBIDDEN (zero price/stock writes)")

    auth: dict[str, str] = {}
    if args.apply:
        token = login()
        auth = {"Authorization": f"Bearer {token}"}

    # 1) Export (commerce-stripped)
    export_path = out / "site_export.jsonl"
    export_csv = out / "site_export.csv"
    if args.reuse_export and export_path.exists():
        products = [
            strip_commerce_fields(json.loads(line))
            for line in export_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        print(f"[export] reused {len(products)} from {export_path}")
    else:
        products = fetch_chumpower_products(auth, brand_id=args.brand_id, limit=args.limit)
        with export_path.open("w", encoding="utf-8") as f:
            for p in products:
                # Defense in depth: never persist commerce fields
                f.write(json.dumps(strip_commerce_fields(p), ensure_ascii=False) + "\n")
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

    # 2) Official index
    if args.rebuild_index or not (out / "official_model_lookup.json").exists():
        by_code, type_map = rebuild_official_index_from_disk(out)
    else:
        by_code, type_map = load_official_index(out)
        print(f"[index] loaded codes={len(by_code)} unique_types={len(type_map)}")

    # 3) Match
    matches: list[MatchResult] = []
    payloads: list[dict[str, Any]] = []
    for p in products:
        sku = str(p.get("sku") or "").strip()
        row, via, notes = resolve_match(sku, by_code, type_map)
        if not row:
            matches.append(
                MatchResult(
                    product_id=int(p["id"]),
                    sku=sku,
                    name=p.get("name") or "",
                    status="unmatched",
                    notes=notes or ["no_exact_code_or_unique_type"],
                )
            )
            continue

        specs = fields_to_official_specs(row)
        if not specs:
            matches.append(
                MatchResult(
                    product_id=int(p["id"]),
                    sku=sku,
                    name=p.get("name") or "",
                    status="matched_no_specs",
                    official_code=row.code,
                    match_via=via,
                    source_url=row.url,
                    notes=notes + ["official_row_empty_specs"],
                )
            )
            # Still allow SEO text from model/type alone if present
            if not (row.code or row.type):
                continue

        mr = MatchResult(
            product_id=int(p["id"]),
            sku=sku,
            name=p.get("name") or "",
            status="matched",
            official_code=row.code,
            match_via=via,
            official_specs=specs,
            source_url=row.url,
            notes=notes,
        )
        matches.append(mr)
        payload, audit = build_payload(p, row)
        if payload:
            payloads.append(
                {
                    "id": p["id"],
                    "sku": sku,
                    "payload": payload,
                    "audit": audit,
                    "match_via": via,
                    "official_code": row.code,
                }
            )

    status_counts = Counter(m.status for m in matches)
    print(f"[match] {dict(status_counts)}")
    print(f"[payloads] ready={len(payloads)}")

    # Fact-check: every payload commerce-free
    for row in payloads:
        assert_payload_commerce_free(row["payload"], context=f"batch sku={row['sku']}")

    match_csv = out / "match_report.csv"
    write_csv(
        match_csv,
        [
            {
                "id": m.product_id,
                "sku": m.sku,
                "name": m.name,
                "status": m.status,
                "official_code": m.official_code or "",
                "match_via": m.match_via or "",
                "specs": json.dumps(m.official_specs, ensure_ascii=False),
                "source_url": m.source_url or "",
                "notes": "|".join(m.notes),
            }
            for m in matches
        ],
        [
            "id",
            "sku",
            "name",
            "status",
            "official_code",
            "match_via",
            "specs",
            "source_url",
            "notes",
        ],
    )

    dry_path = out / "dry_run_payloads.jsonl"
    with dry_path.open("w", encoding="utf-8") as f:
        for row in payloads:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # QA sample file (first 20 matched with payloads)
    qa_path = out / "qa_sample.json"
    qa_path.write_text(
        json.dumps(payloads[:20], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary: dict[str, Any] = {
        "api": API,
        "brand_id": args.brand_id,
        "official_sources": {
            "site": "https://www.chumpowerchuck.com/en/index.html",
            "note": (
                "chumpower.com English index is PET blow-molding — NOT used for SKU SoT. "
                "Catalog PDFs are linked from chuck Download page (CDN under chumpower.com/UserFiles)."
            ),
            "codes_indexed": len(by_code),
            "unique_types": len(type_map),
        },
        "exported": len(products),
        "match_counts": dict(status_counts),
        "payloads": len(payloads),
        "apply": bool(args.apply),
        "applied": 0,
        "apply_errors": 0,
        "commerce_policy": {
            "forbidden_keys": sorted(FORBIDDEN_PAYLOAD_KEYS),
            "allowed_payload_keys": sorted(ALLOWED_PAYLOAD_KEYS),
            "price_writes": 0,
            "stock_writes": 0,
            "verified_payloads_commerce_free": True,
        },
        "paths": {
            "site_export": str(export_path),
            "site_export_csv": str(export_csv),
            "match_report": str(match_csv),
            "dry_run_payloads": str(dry_path),
            "qa_sample": str(qa_path),
        },
    }

    # 4) Apply — SEO/specs only
    apply_rows: list[dict] = []
    if args.apply:
        to_apply = payloads[: args.apply_limit] if args.apply_limit else payloads
        print(f"[apply] writing {len(to_apply)} products (SEO/specs only)…")
        for row in to_apply:
            assert_payload_commerce_free(row["payload"], context=f"apply sku={row['sku']}")
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
                    "commerce_keys": "",  # always empty by construction
                    "error": "" if ok else json.dumps(strip_commerce_fields(resp), ensure_ascii=False)[:300],
                }
            )
            if ok:
                summary["applied"] += 1
            else:
                summary["apply_errors"] += 1
                print(f"[apply] FAIL {row['sku']} {st}")
            time.sleep(0.08)
        apply_csv = out / "apply_report.csv"
        write_csv(
            apply_csv,
            apply_rows,
            ["id", "sku", "http_status", "ok", "payload_keys", "commerce_keys", "error"],
        )
        summary["paths"]["apply_report"] = str(apply_csv)
        summary["commerce_policy"]["price_writes"] = 0
        summary["commerce_policy"]["stock_writes"] = 0

    summary_path = out / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary.get("apply_errors", 0) == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--brand-id", type=int, default=BRAND_ID_DEFAULT)
    parser.add_argument("--limit", type=int, default=None, help="Limit export size (debug)")
    parser.add_argument("--reuse-export", action="store_true")
    parser.add_argument("--rebuild-index", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Dry-run (default). Kept for CLI clarity.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write SEO/specs updates to staging API (never price/stock)",
    )
    parser.add_argument("--apply-limit", type=int, default=None)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
