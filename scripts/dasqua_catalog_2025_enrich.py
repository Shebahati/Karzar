#!/usr/bin/env python3
"""High-accuracy Dasqua catalog enrichment from official 2025 PDF.

Policy (PIM / SEO / AI-pipeline):
  - Very-high SKU/code match only (exact catalog SKU ↔ PDF Code).
  - Never invent specs; only extract fields present on the matched PDF row.
  - Merge into specifications (fill empty / missing; never overwrite non-empty
    conflicting values — report conflicts instead).
  - Separate ``short_description`` (not a name-echo stub).
  - Optional factual long ``description`` from confirmed SoT only.
  - Staging writes via admin API; dry-run by default.
  - HARD: never read/write commerce money or stock fields (price, discount,
    stock qty, availability). PUT payloads are allowlisted enrichment keys only.

Examples:
  # Full dry-run (export + index + match + payloads)
  python scripts/dasqua_catalog_2025_enrich.py \\
    --pdf "/path/to/DASQUA 2025 EDITION.pdf"

  # Apply after reviewing reports
  python scripts/dasqua_catalog_2025_enrich.py --pdf ... --apply --limit 50

Reports land under data/imports/dasqua/catalog_2025/.
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
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Allow `python scripts/...` without installing the package.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.utils.seo_descriptions import (  # noqa: E402
    is_stub_description,
    render_short_description_template,
)

API = os.getenv("KARZAR_API_BASE", "https://api.karzartools.com/api/v1")
UA = "KarzarDasquaCatalog2025Enrich/1.0"
BRAND_ID_DEFAULT = 4  # Dasqua | داسکوا
OUT_DIR = _ROOT / "data" / "imports" / "dasqua" / "catalog_2025"

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
# Only these keys may appear on an apply PUT body.
ALLOWED_PUT_KEYS = frozenset(
    {
        "short_description",
        "description",
        "meta_title",
        "meta_description",
        "specifications",
    }
)
# Fields kept from product detail for enrichment (no commerce).
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


def strip_commerce_fields(obj: Any) -> Any:
    """Recursively drop forbidden commerce/stock keys from API payloads."""
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
    """Keep enrichment-relevant fields only; strip all commerce/stock."""
    cleaned = strip_commerce_fields(detail)
    return {k: v for k, v in cleaned.items() if k in EXPORT_KEEP_KEYS}


def assert_payload_safe(payload: dict[str, Any]) -> None:
    """Raise if PUT body contains anything outside enrichment allowlist."""
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

CODE_RE = re.compile(r"(?<![\d.])(\d{3,5}-\d{3,5}(?:-[A-Za-z0-9]+)?)(?![\d])")
CODE_FULL_RE = re.compile(r"^\d{3,5}-\d{3,5}(?:-[A-Za-z0-9]+)?$")
RANGE_RE = re.compile(
    r"^(?:±)?\d+(?:\.\d+)?(?:mm)?\s*-\s*\d+(?:\.\d+)?(?:mm)?"
    r'(?:/[0-9.\-/"\'inmm]+)?$',
    re.IGNORECASE,
)
# Resolution / graduation: 0.01, 0.01mm, 0.01/0.0005", 0.001/0.00005"
RES_RE = re.compile(r"^(?:0\.\d+)(?:mm)?(?:/[0-9.]+(?:[\"'])?)?(?:/\d+/\d+[\"']?)?$", re.I)
# Accuracy: ±0.003 or 0.02/0.001" (slash form). Bare integers / single dims are NOT accuracy.
ACC_RE = re.compile(r"^(?:±\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?[\"']?)?|\d+\.\d+/\d+(?:\.\d+)?[\"']?)$")
GARBAGE_ACC = {"±", "+", "-", "—", "."}


@dataclass
class PdfSpecRow:
    code: str
    range: str | None = None
    resolution: str | None = None
    accuracy: str | None = None
    line_no: int = 0
    raw_tail: str = ""


@dataclass
class MatchResult:
    product_id: int
    sku: str
    name: str
    status: str  # matched | unmatched | conflict | weak_row
    pdf_code: str | None = None
    pdf_specs: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def _load_admin_creds() -> tuple[str, str]:
    phone = os.getenv("INITIAL_SUPER_ADMIN_PHONE")
    password = os.getenv("INITIAL_SUPER_ADMIN_PASSWORD")
    secrets = _ROOT / ".deploy-secrets"
    # Prefer sibling backend secrets if this worktree has none.
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
    last_err: Exception | None = None
    for attempt in range(5):
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
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:  # noqa: S310
                return json.loads(resp.read().decode())["access_token"]
        except (TimeoutError, urllib.error.URLError) as exc:
            last_err = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"admin login failed after retries: {last_err}")


def base_code(code: str) -> str:
    m = re.match(r"^(\d{3,5}-\d{3,5})", code.strip())
    return m.group(1) if m else code.strip()


def normalize_token(tok: str) -> str:
    return (
        tok.replace("\x00", "")
        .replace("\x01", " ")
        .replace("\xa0", " ")
        .strip()
        .strip(",")
    )


def is_code_token(tok: str) -> bool:
    return bool(CODE_FULL_RE.fullmatch(tok))


def is_range_token(tok: str) -> bool:
    if is_code_token(tok):
        return False
    # Reject if another product code is embedded (OCR bleed).
    if CODE_RE.search(tok) and not RANGE_RE.match(tok):
        return False
    return bool(RANGE_RE.match(tok))


def is_resolution_token(tok: str) -> bool:
    if tok in GARBAGE_ACC or is_code_token(tok):
        return False
    return bool(RES_RE.match(tok))


def is_accuracy_token(tok: str) -> bool:
    if tok in GARBAGE_ACC or is_code_token(tok):
        return False
    if not ACC_RE.match(tok):
        return False
    # Lone "±0" style noise
    if re.fullmatch(r"±0+(?:\.0+)?", tok):
        return False
    return True


def extract_pdf_text(pdf_path: Path, cache_path: Path) -> str:
    """Extract text via pdftotext -layout; cache for resume."""
    if cache_path.exists() and cache_path.stat().st_mtime >= pdf_path.stat().st_mtime:
        return cache_path.read_text(encoding="utf-8", errors="ignore")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["pdftotext", "-layout", str(pdf_path), str(cache_path)]
    subprocess.run(cmd, check=True, capture_output=True)
    return cache_path.read_text(encoding="utf-8", errors="ignore")


def parse_pdf_rows(text: str, catalog_skus: set[str]) -> dict[str, list[PdfSpecRow]]:
    """Index PDF rows for catalog SKUs only (very-high confidence gate)."""
    cat_bases = {base_code(s) for s in catalog_skus}
    lines = text.splitlines()
    by_sku: dict[str, list[PdfSpecRow]] = defaultdict(list)

    for i, line in enumerate(lines):
        for m in CODE_RE.finditer(line):
            code = m.group(1)
            b = base_code(code)
            # Exact catalog match preferred; base match only when base itself is a catalog SKU.
            if code in catalog_skus:
                sku_key = code
            elif b in catalog_skus:
                sku_key = b
            elif b in cat_bases:
                # Catalog has a more specific SKU (e.g. with suffix) — skip ambiguous base.
                continue
            else:
                continue

            rest = line[m.end() :]
            toks = [normalize_token(t) for t in re.split(r"\s+", rest.strip()) if t]
            if len(toks) < 2 and i + 1 < len(lines):
                toks += [
                    normalize_token(t)
                    for t in re.split(r"\s+", lines[i + 1].strip())
                    if t
                ][:14]

            range_v: str | None = None
            res_v: str | None = None
            acc_v: str | None = None
            for tok in toks[:20]:
                if not tok or "\x00" in tok:
                    continue
                # Stop if another product code appears mid-tail (bleed).
                if range_v and is_code_token(tok):
                    break
                if range_v is None and is_range_token(tok):
                    range_v = tok
                    continue
                if range_v is not None and res_v is None and is_resolution_token(tok):
                    res_v = tok
                    continue
                if range_v is not None and is_accuracy_token(tok):
                    # Skip if this token is identical to resolution (same cell misread).
                    if res_v and tok == res_v:
                        continue
                    acc_v = tok

            if not (range_v or res_v or acc_v):
                continue
            # Reject obviously broken ranges (embedded codes / titles).
            if range_v and (CODE_RE.search(range_v) and not is_range_token(range_v)):
                continue
            if any(ord(ch) < 32 for ch in (range_v or "") + (res_v or "") + (acc_v or "")):
                continue

            by_sku[sku_key].append(
                PdfSpecRow(
                    code=code,
                    range=range_v,
                    resolution=res_v,
                    accuracy=acc_v,
                    line_no=i + 1,
                    raw_tail=" ".join(toks[:12]),
                )
            )
    return by_sku


def consensus_specs(rows: list[PdfSpecRow]) -> tuple[dict[str, str] | None, list[str]]:
    """Return specs only when non-conflicting across PDF hits."""
    notes: list[str] = []
    if not rows:
        return None, ["no_pdf_row"]

    # Prefer rows with more filled fields; drop incomplete ±-only noise.
    cleaned: list[PdfSpecRow] = []
    for r in rows:
        if r.accuracy in GARBAGE_ACC:
            r = PdfSpecRow(
                code=r.code,
                range=r.range,
                resolution=r.resolution,
                accuracy=None,
                line_no=r.line_no,
                raw_tail=r.raw_tail,
            )
        if r.range or r.resolution or r.accuracy:
            cleaned.append(r)
    if not cleaned:
        return None, ["rows_cleaned_empty"]

    # Group by (range, resolution, accuracy)
    groups: dict[tuple, list[PdfSpecRow]] = defaultdict(list)
    for r in cleaned:
        groups[(r.range, r.resolution, r.accuracy)].append(r)

    if len(groups) == 1:
        r = cleaned[0]
        out = {}
        if r.range:
            out["range"] = r.range
        if r.resolution:
            out["resolution"] = r.resolution
        if r.accuracy:
            out["accuracy"] = r.accuracy
        return (out or None), notes

    # Soft consensus: if all agree on range, take union of fields where unanimous.
    ranges = {r.range for r in cleaned if r.range}
    if len(ranges) != 1:
        notes.append(f"conflict_ranges:{sorted(ranges)[:4]}")
        return None, notes

    range_v = next(iter(ranges))
    res_vals = {r.resolution for r in cleaned if r.resolution}
    acc_vals = {r.accuracy for r in cleaned if r.accuracy}
    out: dict[str, str] = {"range": range_v}
    if len(res_vals) == 1:
        out["resolution"] = next(iter(res_vals))
    elif len(res_vals) > 1:
        notes.append(f"conflict_resolution:{sorted(res_vals)[:3]}")
    if len(acc_vals) == 1:
        out["accuracy"] = next(iter(acc_vals))
    elif len(acc_vals) > 1:
        notes.append(f"conflict_accuracy:{sorted(acc_vals)[:3]}")

    # If we only have range after conflicts on other fields, still OK (factual).
    if notes and len(out) == 1 and "range" in out:
        notes.append("partial_consensus_range_only")
    if any(n.startswith("conflict_") for n in notes) and len(out) == 1:
        # Range-only after field conflicts is still high-confidence for range.
        return out, notes
    if any(n.startswith("conflict_") for n in notes) and ("resolution" not in out and "accuracy" not in out):
        return out, notes
    return out, notes


def specs_to_dict(specs: Any) -> dict[str, str]:
    """Normalize storefront/admin technical_specs to flat non-empty dict."""
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


# Map PDF English keys ↔ common Persian keys already in catalog.
SPEC_ALIASES = {
    "range": ["range", "بازه اندازه‌گیری", "بازه اندازه گیری", "اندازه", "محدوده"],
    "accuracy": ["accuracy", "دقت"],
    "resolution": ["resolution", "وضوح", "تفکیک", "درجه‌بندی", "درجه بندی", "graduation"],
}


def existing_has_key(existing: dict[str, str], canon: str) -> str | None:
    for alias in SPEC_ALIASES.get(canon, [canon]):
        if alias in existing and existing[alias].strip():
            return alias
    # case-insensitive
    lower = {k.casefold(): k for k in existing}
    for alias in SPEC_ALIASES.get(canon, [canon]):
        if alias.casefold() in lower:
            return lower[alias.casefold()]
    return None


def merge_technical_specs(
    existing_specs: dict[str, Any] | None,
    pdf_specs: dict[str, str],
) -> tuple[dict[str, Any], list[str], dict[str, str]]:
    """Merge PDF facts into specifications without weakening good data.

    Returns (new_specifications_for_storage, notes, filled_fields).
    Storage shape: nested dict technical_specs.
    """
    notes: list[str] = []
    filled: dict[str, str] = {}
    existing_flat = specs_to_dict(existing_specs)
    tech: dict[str, str] = dict(existing_flat)

    # Preserve non-technical sections from existing.
    base: dict[str, Any] = {}
    if isinstance(existing_specs, dict):
        base = {
            "features": existing_specs.get("features") or {},
            "dimensions": existing_specs.get("dimensions") or {},
            "optional_accessories": existing_specs.get("optional_accessories") or [],
        }
    else:
        base = {"features": {}, "dimensions": {}, "optional_accessories": []}

    for canon, value in pdf_specs.items():
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
        # Write canonical English key (PIM-friendly); keep Persian aliases if present empty.
        tech[canon] = value
        filled[canon] = value

    result = {
        "technical_specs": tech,
        "features": base["features"] if isinstance(base["features"], dict) else {},
        "dimensions": base["dimensions"] if isinstance(base["dimensions"], dict) else {},
        "optional_accessories": base.get("optional_accessories") or [],
    }
    return result, notes, filled


def _norm_spec_val(v: str) -> str:
    s = v.casefold().replace(" ", "").replace("٫", ".")
    s = s.replace("۰", "0").replace("۱", "1").replace("۲", "2").replace("۳", "3")
    s = s.replace("۴", "4").replace("۵", "5").replace("۶", "6").replace("۷", "7")
    s = s.replace("۸", "8").replace("۹", "9")
    return s


def persian_short_description(
    *,
    name: str,
    brand_name: str | None,
    category_name: str | None,
    sku: str,
    tech: dict[str, str],
) -> str | None:
    """Factual Persian short blurb from SoT only (no invented claims)."""
    rng = tech.get("range") or tech.get("بازه اندازه‌گیری") or tech.get("بازه اندازه گیری")
    acc = tech.get("accuracy") or tech.get("دقت")
    res = tech.get("resolution") or tech.get("وضوح")

    parts: list[str] = []
    if category_name:
        parts.append(f"{category_name} برند داسکوا")
    elif brand_name:
        parts.append("محصول برند داسکوا")
    else:
        parts.append("محصول برند داسکوا")

    facts: list[str] = []
    if rng:
        facts.append(f"بازه: {rng}")
    if acc:
        facts.append(f"دقت: {acc}")
    if res:
        facts.append(f"وضوح: {res}")
    if facts:
        parts.append("؛ ".join(facts))
    if sku:
        parts.append(f"کد {sku}")

    body = " — ".join(parts)
    if is_stub_description(body, product_name=name):
        # Last resort: template helper (may omit accuracy — still SoT-only).
        preview = render_short_description_template(
            name=name,
            brand_name=brand_name or "Dasqua | داسکوا",
            category_name=category_name,
            sku=sku,
            technical_specs={"range": rng, "resolution": res},
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
) -> str | None:
    """Optional longer factual copy — specs only, no marketing fluff."""
    lines = [
        f"{category_name or 'ابزار اندازه‌گیری'} داسکوا با کد {sku}.",
    ]
    facts = []
    if tech.get("range") or tech.get("بازه اندازه‌گیری"):
        facts.append(f"بازه اندازه‌گیری: {tech.get('range') or tech.get('بازه اندازه‌گیری')}")
    if tech.get("resolution") or tech.get("وضوح"):
        facts.append(f"وضوح/درجه‌بندی: {tech.get('resolution') or tech.get('وضوح')}")
    if tech.get("accuracy") or tech.get("دقت"):
        facts.append(f"دقت: {tech.get('accuracy') or tech.get('دقت')}")
    if not facts:
        return None
    lines.append("مشخصات طبق کاتالوگ رسمی Dasqua 2025:")
    lines.extend(f"- {f}" for f in facts)
    lines.append("مقادیر فقط از ردیف هم‌کد کاتالوگ استخراج شده‌اند.")
    return "\n".join(lines)[:4000]


def meta_title_for(name: str, sku: str) -> str:
    base = name.strip() or f"داسکوا {sku}"
    if sku not in base:
        base = f"{base} | {sku}"
    return base[:255]


def meta_description_for(short: str | None, name: str, sku: str) -> str:
    if short and not is_stub_description(short, product_name=name):
        return short[:500]
    return f"{name} | داسکوا کد {sku}"[:500]


def fetch_dasqua_products(auth: dict, *, brand_id: int, limit: int | None) -> list[dict]:
    """Export active Dasqua products (list + detail for specs/descriptions)."""
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
            # Never retain commerce fields from list cards.
            row = strip_commerce_fields(row)
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


def build_payload(product: dict, pdf_specs: dict[str, str]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build PUT payload + audit record."""
    name = product.get("name") or ""
    sku = product.get("sku") or ""
    brand = product.get("brand") if isinstance(product.get("brand"), dict) else {}
    cat = product.get("category") if isinstance(product.get("category"), dict) else {}
    brand_name = brand.get("name")
    category_name = cat.get("name")

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
            category_name=category_name, sku=sku, tech=tech_flat
        )

    new_meta_title = None
    if not (meta_title or "").strip():
        new_meta_title = meta_title_for(name, sku)

    new_meta_desc = None
    if not (meta_desc or "").strip():
        new_meta_desc = meta_description_for(new_short or short, name, sku)

    payload: dict[str, Any] = {}
    if filled or merge_notes:
        # Only send specifications when we actually fill something new.
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
        "price_keys_in_payload": 0,
    }
    return payload, audit


def run(args: argparse.Namespace) -> int:
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        return 2

    print(f"API: {API}")
    print(f"PDF: {pdf_path}")
    print(f"Out: {out}")
    print(f"Mode: {'APPLY' if args.apply else 'dry-run'}")

    # Public catalog read is enough for dry-run/export. Admin login only for --apply.
    auth: dict[str, str] = {}
    if args.apply:
        token = login()
        auth = {"Authorization": f"Bearer {token}"}

    # 1) Export
    export_path = out / "site_export.jsonl"
    export_csv = out / "site_export.csv"
    if args.reuse_export and export_path.exists():
        products = [
            sanitize_product_export(json.loads(line))
            for line in export_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        print(f"[export] reused {len(products)} from {export_path} (commerce-stripped)")
    else:
        products = fetch_dasqua_products(auth, brand_id=args.brand_id, limit=args.limit)
        with export_path.open("w", encoding="utf-8") as f:
            for p in products:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
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

    catalog_skus = {str(p.get("sku") or "").strip() for p in products if p.get("sku")}
    catalog_skus.discard("")

    # 2) Index PDF
    text_cache = out / "pdf_text_layout.txt"
    text = extract_pdf_text(pdf_path, text_cache)
    by_sku = parse_pdf_rows(text, catalog_skus)
    index_path = out / "pdf_index.jsonl"
    with index_path.open("w", encoding="utf-8") as f:
        for sku, rows in sorted(by_sku.items()):
            f.write(
                json.dumps(
                    {"sku": sku, "rows": [asdict(r) for r in rows]},
                    ensure_ascii=False,
                )
                + "\n"
            )
    print(f"[pdf] indexed SKUs with rows: {len(by_sku)}")

    # 3) Match
    matches: list[MatchResult] = []
    payloads: list[dict[str, Any]] = []
    for p in products:
        sku = str(p.get("sku") or "").strip()
        rows = by_sku.get(sku) or []
        # Also try base if exact missing and base is this sku (already keyed).
        if not rows and base_code(sku) != sku:
            rows = by_sku.get(base_code(sku)) or []

        if not rows:
            # Mention-only?
            if sku in text or base_code(sku) in text:
                matches.append(
                    MatchResult(
                        product_id=int(p["id"]),
                        sku=sku,
                        name=p.get("name") or "",
                        status="unmatched_no_spec_row",
                        notes=["sku_mentioned_but_no_parseable_spec_row"],
                    )
                )
            else:
                matches.append(
                    MatchResult(
                        product_id=int(p["id"]),
                        sku=sku,
                        name=p.get("name") or "",
                        status="unmatched",
                        notes=["sku_not_in_pdf"],
                    )
                )
            continue

        specs, notes = consensus_specs(rows)
        if not specs:
            matches.append(
                MatchResult(
                    product_id=int(p["id"]),
                    sku=sku,
                    name=p.get("name") or "",
                    status="conflict",
                    pdf_code=rows[0].code,
                    notes=notes,
                )
            )
            continue

        mr = MatchResult(
            product_id=int(p["id"]),
            sku=sku,
            name=p.get("name") or "",
            status="matched",
            pdf_code=rows[0].code,
            pdf_specs=specs,
            notes=notes,
        )
        matches.append(mr)
        payload, audit = build_payload(p, specs)
        if payload:
            payloads.append(
                {
                    "id": p["id"],
                    "sku": sku,
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
                "pdf_code": m.pdf_code or "",
                "range": m.pdf_specs.get("range", ""),
                "resolution": m.pdf_specs.get("resolution", ""),
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
            "pdf_code",
            "range",
            "resolution",
            "accuracy",
            "notes",
        ],
    )

    dry_path = out / "dry_run_payloads.jsonl"
    with dry_path.open("w", encoding="utf-8") as f:
        for row in payloads:
            assert_payload_safe(row["payload"])
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    export_forbidden = count_forbidden_in_obj(products)
    payload_forbidden = count_forbidden_in_obj([r["payload"] for r in payloads])

    summary = {
        "api": API,
        "pdf": str(pdf_path),
        "brand_id": args.brand_id,
        "exported": len(products),
        "match_counts": dict(status_counts),
        "payloads": len(payloads),
        "apply": bool(args.apply),
        "applied": 0,
        "apply_errors": 0,
        "commerce_policy": {
            "forbidden_keys": sorted(FORBIDDEN_COMMERCE_KEYS),
            "allowed_put_keys": sorted(ALLOWED_PUT_KEYS),
            "export_forbidden_hits": export_forbidden[:20],
            "export_forbidden_count": len(export_forbidden),
            "payload_forbidden_hits": payload_forbidden[:20],
            "payload_forbidden_count": len(payload_forbidden),
            "zero_price_writes": len(payload_forbidden) == 0,
            "zero_price_reads_persisted": len(export_forbidden) == 0,
        },
        "paths": {
            "site_export": str(export_path),
            "site_export_csv": str(export_csv),
            "pdf_index": str(index_path),
            "match_report": str(match_csv),
            "dry_run_payloads": str(dry_path),
        },
    }
    if export_forbidden or payload_forbidden:
        print(
            f"ERROR: commerce field leak export={len(export_forbidden)} "
            f"payload={len(payload_forbidden)}",
            file=sys.stderr,
        )
        (out / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return 3

    # 4) Apply
    apply_rows: list[dict] = []
    if args.apply:
        if args.apply_limit:
            to_apply = payloads[: args.apply_limit]
        else:
            to_apply = payloads
        print(f"[apply] writing {len(to_apply)} products…")
        for row in to_apply:
            pid = row["id"]
            payload = row["payload"]
            assert_payload_safe(payload)
            try:
                st, resp = http_json(
                    "PUT",
                    f"{API.rstrip('/')}/products/{pid}",
                    data=payload,
                    headers=auth,
                    timeout=90,
                )
            except Exception as exc:  # noqa: BLE001 — continue batch; record failure
                st, resp = 0, {"error": str(exc)[:300]}
            ok = st in (200, 201)
            apply_rows.append(
                {
                    "id": pid,
                    "sku": row["sku"],
                    "http_status": st,
                    "ok": ok,
                    "payload_keys": "|".join(sorted(payload.keys())),
                    "error": "" if ok else json.dumps(resp, ensure_ascii=False)[:300],
                }
            )
            if ok:
                summary["applied"] += 1
            else:
                summary["apply_errors"] += 1
                print(f"[apply] FAIL {row['sku']} {st} {resp}")
            time.sleep(0.12)
        apply_csv = out / "apply_report.csv"
        write_csv(
            apply_csv,
            apply_rows,
            ["id", "sku", "http_status", "ok", "payload_keys", "error"],
        )
        summary["paths"]["apply_report"] = str(apply_csv)

    summary_path = out / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary.get("apply_errors", 0) == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pdf",
        required=True,
        help="Path to official DASQUA 2025 catalog PDF",
    )
    parser.add_argument(
        "--out-dir",
        default=str(OUT_DIR),
        help="Report directory (default: data/imports/dasqua/catalog_2025)",
    )
    parser.add_argument("--brand-id", type=int, default=BRAND_ID_DEFAULT)
    parser.add_argument("--limit", type=int, default=None, help="Limit export size (debug)")
    parser.add_argument(
        "--reuse-export",
        action="store_true",
        help="Reuse site_export.jsonl if present",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write updates to staging API (default: dry-run only)",
    )
    parser.add_argument(
        "--apply-limit",
        type=int,
        default=None,
        help="Max products to apply (safety cap)",
    )
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
