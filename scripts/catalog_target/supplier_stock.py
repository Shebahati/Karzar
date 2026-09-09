"""Supplier stock authority: validate + exact-map (read-only; never mutates catalog).

PRICE AUTHORITY and AVAILABILITY AUTHORITY are independent.
Never infer AVAILABLE from price, row existence, is_active, or prior is_available.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from catalog_target.core import canonicalize_brand, normalize_sku
from catalog_target.xlsx import iter_xlsx_rows

PARSER_VERSION = "supplier_stock/1.0.0"
NORMALIZATION_POLICY_VERSION = "supplier_stock_norm/1.0.0"

# Explicit stock freshness defaults (stricter than typical price aging).
DEFAULT_CURRENT_ENOUGH_DAYS = 14
DEFAULT_AGING_BUT_USABLE_DAYS = 45

AVAILABLE_STATUS_TOKENS = frozenset(
    {
        "موجود",
        "available",
        "in stock",
        "instock",
        "in-stock",
        "yes",
        "true",
        "1",
    }
)
UNAVAILABLE_STATUS_TOKENS = frozenset(
    {
        "ناموجود",
        "نا موجود",
        "ناموجودی",
        "unavailable",
        "out of stock",
        "outofstock",
        "out-of-stock",
        "no",
        "false",
        "0",
    }
)

# Header aliases (EN + FA) → canonical field
HEADER_ALIASES: dict[str, str] = {
    "brand": "brand",
    "برند": "brand",
    "supplier": "supplier",
    "تامین کننده": "supplier",
    "تأمین کننده": "supplier",
    "sku": "manufacturer_sku",
    "manufacturer_sku": "manufacturer_sku",
    "manufacturer sku": "manufacturer_sku",
    "کد کالا": "manufacturer_sku",
    "کدکالا": "manufacturer_sku",
    "supplier_sku": "supplier_sku",
    "supplier sku": "supplier_sku",
    "model": "model",
    "مدل": "model",
    "availability": "availability_status",
    "availability_status": "availability_status",
    "status": "availability_status",
    "وضعیت موجودی": "availability_status",
    "وضعیت": "availability_status",
    "quantity": "quantity",
    "qty": "quantity",
    "تعداد موجودی": "quantity",
    "تعداد": "quantity",
    "warehouse": "warehouse",
    "انبار": "warehouse",
    "last updated": "source_date",
    "last_updated": "source_date",
    "source_date": "source_date",
    "date": "source_date",
    "تاریخ بروزرسانی": "source_date",
    "تاریخ به‌روزرسانی": "source_date",
    "تاریخ": "source_date",
    "source_version": "source_version",
    "version": "source_version",
    "notes": "notes",
    "توضیحات": "notes",
}

# DASQUA reviewed pack suffix only: trailing -A (not -B / multi-segment).
_DASQUA_BASE_RE = re.compile(r"^(\d{3,5}-\d{3,5})$", re.I)
_DASQUA_PACK_A_RE = re.compile(r"^(\d{3,5}-\d{3,5})-A$", re.I)

TERMA_PRICE_EXCEPTION_SKUS = frozenset({"CDA100-300", "MA250H-200", "MD710-25"})

SALE_WAVE_PLAN_FIELDS = (
    "product_id",
    "brand",
    "sku",
    "current_base_price",
    "proposed_base_price",
    "price_source_id",
    "price_source_date",
    "price_source_value",
    "price_rule",
    "current_is_available",
    "proposed_is_available",
    "stock_source_id",
    "stock_source_date",
    "stock_source_status",
    "stock_source_quantity",
    "identity_match",
    "content_safety",
    "primary_image_present",
    "expected_current_hash",
)

ALLOWED_FUTURE_MUTATIONS = frozenset({"base_price", "is_available"})
FORBIDDEN_AUTO_MUTATIONS = frozenset(
    {"is_active", "content", "images", "slug", "category", "brand", "SKU", "sku", "name"}
)


@dataclass
class FreshnessPolicy:
    current_enough_days: int = DEFAULT_CURRENT_ENOUGH_DAYS
    aging_but_usable_days: int = DEFAULT_AGING_BUT_USABLE_DAYS

    def classify(self, age_days: int | None) -> str:
        if age_days is None:
            return "UNKNOWN"
        if age_days <= self.current_enough_days:
            return "CURRENT_ENOUGH"
        if age_days <= self.aging_but_usable_days:
            return "AGING_BUT_USABLE"
        return "STALE"


@dataclass
class SourceManifest:
    source_id: str
    brand: str
    supplier: str
    original_filename: str
    sha256: str
    received_at: str
    source_date: str | None
    authority_type: str
    parser_version: str = PARSER_VERSION
    normalization_policy_version: str = NORMALIZATION_POLICY_VERSION


@dataclass
class StockRow:
    source_row: int
    brand: str | None
    supplier: str | None
    manufacturer_sku: str
    supplier_sku: str
    model: str
    availability_status_raw: str
    quantity_raw: str
    quantity: int | None
    quantity_invalid: bool
    warehouse: str
    source_date_raw: str
    source_version: str
    notes: str
    normalized_status: str
    identity_key: str


@dataclass
class ValidationReport:
    source_authority_valid: bool
    input_rows: int
    unique_identifiers: int
    duplicate_identifiers: int
    conflicting_identifiers: int
    available: int
    unavailable: int
    unknown: int
    blank_status: int
    invalid_quantity: int
    unknown_status_values: list[str]
    source_date_present: bool
    source_date_age_days: int | None
    freshness: str
    deny_reasons: list[str] = field(default_factory=list)
    rows: list[StockRow] = field(default_factory=list)
    manifest: SourceManifest | None = None
    parser_version: str = PARSER_VERSION
    normalization_policy_version: str = NORMALIZATION_POLICY_VERSION

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["rows"] = [asdict(r) for r in self.rows]
        return d


@dataclass
class CatalogProduct:
    product_id: str
    brand: str
    sku: str
    model: str = ""
    is_active: bool = False
    deleted: bool = False


@dataclass
class MapResultRow:
    source_row: int
    brand: str
    manufacturer_sku: str
    model: str
    normalized_status: str
    quantity: int | None
    match_class: str
    product_id: str = ""
    catalog_sku: str = ""
    match_detail: str = ""
    price_exception_flag: bool = False


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _fold_header(value: str) -> str:
    s = str(value or "").strip().casefold()
    s = re.sub(r"\s+", " ", s)
    return s


def _canonical_header(name: str) -> str | None:
    return HEADER_ALIASES.get(_fold_header(name))


def _normalize_status_token(raw: str) -> str:
    s = str(raw or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s.casefold()


def normalize_availability_status(
    *,
    status_raw: str | None,
    quantity: int | None,
    quantity_invalid: bool,
    quantity_is_sellable_stock: bool,
) -> tuple[str, str | None]:
    """Return (normalized_status, unknown_token_if_any).

    Never uses price. Quantity drives status only when quantity_is_sellable_stock.
    """
    token = _normalize_status_token(status_raw or "")
    blank = not token

    if quantity_is_sellable_stock and not quantity_invalid and quantity is not None:
        if quantity > 0:
            return "AVAILABLE", None
        if quantity == 0:
            return "UNAVAILABLE", None

    if blank:
        return "UNKNOWN", None
    if token in AVAILABLE_STATUS_TOKENS:
        return "AVAILABLE", None
    if token in UNAVAILABLE_STATUS_TOKENS:
        return "UNAVAILABLE", None
    return "UNKNOWN", str(status_raw or "").strip()


def parse_quantity(raw: Any) -> tuple[int | None, bool]:
    """Return (quantity, invalid). Blank → (None, False)."""
    if raw is None:
        return None, False
    s = str(raw).strip()
    if not s:
        return None, False
    s = s.replace(",", "").replace("،", "")
    try:
        # Allow 5.0 style
        num = float(s)
    except ValueError:
        return None, True
    if not num.is_integer():
        return None, True
    ival = int(num)
    if ival < 0:
        return None, True
    return ival, False


def parse_source_date(raw: str | None, *, today: date | None = None) -> tuple[date | None, int | None]:
    """Parse common Gregorian / compact Jalali-looking ISO-ish dates. Returns (date, age_days)."""
    if raw is None:
        return None, None
    s = str(raw).strip()
    if not s:
        return None, None
    today = today or date.today()
    # Gregorian ISO
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            d = datetime.strptime(s[:10], fmt).date()
            return d, (today - d).days
        except ValueError:
            continue
    # Compact YYYYMMDD
    if re.fullmatch(r"\d{8}", s):
        try:
            d = datetime.strptime(s, "%Y%m%d").date()
            return d, (today - d).days
        except ValueError:
            return None, None
    return None, None


def dasqua_pack_a_base(sku: str) -> str | None:
    """If SKU is NNNN-NNNN-A, return base NNNN-NNNN; else None."""
    m = _DASQUA_PACK_A_RE.fullmatch(normalize_sku(sku))
    return m.group(1).upper() if m else None


def dasqua_is_base(sku: str) -> bool:
    return bool(_DASQUA_BASE_RE.fullmatch(normalize_sku(sku)))


def load_tabular(path: Path) -> list[dict[str, Any]]:
    path = Path(path)
    suf = path.suffix.lower()
    if suf == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows: list[dict[str, Any]] = []
            for i, raw in enumerate(reader, start=2):
                item = {k: (v if v is not None else "") for k, v in raw.items() if k is not None}
                item["__source_row"] = i
                rows.append(item)
            return rows
    if suf in {".xlsx", ".xlsm"}:
        return iter_xlsx_rows(path)
    raise ValueError(f"unsupported_format:{suf}")


def _row_get(row: Mapping[str, Any], canonical: str) -> str:
    for k, v in row.items():
        if str(k).startswith("__"):
            continue
        if _canonical_header(str(k)) == canonical:
            return "" if v is None else str(v).strip()
    return ""


def build_stock_rows(
    raw_rows: Sequence[Mapping[str, Any]],
    *,
    quantity_is_sellable_stock: bool,
    default_brand: str | None = None,
) -> tuple[list[StockRow], list[str]]:
    unknown_tokens: list[str] = []
    out: list[StockRow] = []
    for raw in raw_rows:
        brand_raw = _row_get(raw, "brand") or (default_brand or "")
        brand = canonicalize_brand(brand_raw) if brand_raw else None
        mfr = normalize_sku(_row_get(raw, "manufacturer_sku"))
        model = str(_row_get(raw, "model") or "").strip()
        model_key = normalize_sku(model) if model else ""
        identity = mfr or model_key
        status_raw = _row_get(raw, "availability_status")
        qty_raw = _row_get(raw, "quantity")
        qty, qty_invalid = parse_quantity(qty_raw)
        status, unk = normalize_availability_status(
            status_raw=status_raw,
            quantity=qty,
            quantity_invalid=qty_invalid,
            quantity_is_sellable_stock=quantity_is_sellable_stock,
        )
        if unk:
            unknown_tokens.append(unk)
        out.append(
            StockRow(
                source_row=int(raw.get("__source_row") or 0),
                brand=brand,
                supplier=_row_get(raw, "supplier") or None,
                manufacturer_sku=mfr,
                supplier_sku=normalize_sku(_row_get(raw, "supplier_sku")),
                model=model,
                availability_status_raw=status_raw,
                quantity_raw=qty_raw,
                quantity=qty,
                quantity_invalid=qty_invalid,
                warehouse=_row_get(raw, "warehouse"),
                source_date_raw=_row_get(raw, "source_date"),
                source_version=_row_get(raw, "source_version"),
                notes=_row_get(raw, "notes"),
                normalized_status=status,
                identity_key=identity,
            )
        )
    return out, sorted(set(unknown_tokens))


def validate_stock_source(
    path: Path,
    *,
    brand: str | None = None,
    supplier: str = "",
    authority_type: str = "AVAILABILITY",
    quantity_is_sellable_stock: bool = True,
    source_date_override: str | None = None,
    freshness: FreshnessPolicy | None = None,
    today: date | None = None,
) -> ValidationReport:
    """Read-only semantic validation. Default deny when authority is insufficient."""
    path = Path(path)
    freshness = freshness or FreshnessPolicy()
    today = today or date.today()
    deny: list[str] = []

    try:
        raw_rows = load_tabular(path)
    except Exception as exc:  # noqa: BLE001 — surface as deny
        return ValidationReport(
            source_authority_valid=False,
            input_rows=0,
            unique_identifiers=0,
            duplicate_identifiers=0,
            conflicting_identifiers=0,
            available=0,
            unavailable=0,
            unknown=0,
            blank_status=0,
            invalid_quantity=0,
            unknown_status_values=[],
            source_date_present=False,
            source_date_age_days=None,
            freshness="UNKNOWN",
            deny_reasons=[f"load_failed:{exc}"],
        )

    rows, unknown_tokens = build_stock_rows(
        raw_rows,
        quantity_is_sellable_stock=quantity_is_sellable_stock,
        default_brand=brand,
    )

    # Identity / brand checks
    missing_identity = sum(1 for r in rows if not r.identity_key)
    missing_brand = sum(1 for r in rows if not r.brand)
    missing_avail_signal = sum(
        1
        for r in rows
        if not r.availability_status_raw and r.quantity is None and not r.quantity_invalid
    )
    if missing_identity:
        deny.append(f"blank_identifiers:{missing_identity}")
    if missing_brand:
        deny.append(f"missing_brand:{missing_brand}")
    if missing_avail_signal:
        deny.append(f"rows_without_status_or_quantity:{missing_avail_signal}")
    if not quantity_is_sellable_stock:
        # status text must carry authority for all rows that lack known tokens
        weak = sum(
            1
            for r in rows
            if r.normalized_status == "UNKNOWN"
            and not r.availability_status_raw
        )
        if weak:
            deny.append("quantity_semantics_not_confirmed_and_status_weak")

    # Duplicates / conflicts by identity_key within brand
    by_key: dict[tuple[str, str], list[StockRow]] = {}
    for r in rows:
        if not r.identity_key or not r.brand:
            continue
        by_key.setdefault((r.brand, r.identity_key), []).append(r)

    duplicate_identifiers = sum(1 for g in by_key.values() if len(g) > 1)
    conflicting_identifiers = 0
    for group in by_key.values():
        statuses = {g.normalized_status for g in group}
        if len(group) > 1 and len(statuses) > 1:
            # annotate via notes field already present; conflict counted globally
            conflicting_identifiers += 1
    if conflicting_identifiers:
        deny.append(f"source_conflict_groups:{conflicting_identifiers}")

    # Source date
    date_candidates = [source_date_override] if source_date_override else []
    date_candidates.extend(r.source_date_raw for r in rows if r.source_date_raw)
    parsed_dates: list[tuple[date, int]] = []
    for cand in date_candidates:
        d, age = parse_source_date(cand, today=today)
        if d is not None and age is not None:
            parsed_dates.append((d, age))
    source_date_present = bool(parsed_dates) or bool(source_date_override)
    age_days = max((a for _, a in parsed_dates), default=None)
    # Prefer youngest (min age) when multiple
    if parsed_dates:
        age_days = min(a for _, a in parsed_dates)
    freshness_class = freshness.classify(age_days)
    if not source_date_present:
        deny.append("source_date_missing")
    if freshness_class == "STALE":
        deny.append("source_stale")
    if freshness_class == "UNKNOWN" and not source_date_present:
        deny.append("source_date_unknown")

    if brand:
        want = canonicalize_brand(brand)
        cross = sum(1 for r in rows if r.brand and r.brand != want)
        if cross:
            deny.append(f"cross_brand_rows:{cross}")

    available = sum(1 for r in rows if r.normalized_status == "AVAILABLE")
    unavailable = sum(1 for r in rows if r.normalized_status == "UNAVAILABLE")
    unknown = sum(1 for r in rows if r.normalized_status == "UNKNOWN")
    blank_status = sum(1 for r in rows if not r.availability_status_raw)
    invalid_quantity = sum(1 for r in rows if r.quantity_invalid)

    # Default deny: need at least one usable AVAILABLE/UNAVAILABLE signal overall
    if available + unavailable == 0:
        deny.append("no_explicit_available_or_unavailable_rows")

    valid = len(deny) == 0 and len(rows) > 0

    manifest = SourceManifest(
        source_id=str(uuid.uuid4()),
        brand=canonicalize_brand(brand) or (rows[0].brand if rows and rows[0].brand else ""),
        supplier=supplier or (rows[0].supplier or "" if rows else ""),
        original_filename=path.name,
        sha256=file_sha256(path),
        received_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        source_date=source_date_override
        or (parsed_dates[0][0].isoformat() if parsed_dates else None),
        authority_type=authority_type,
    )

    return ValidationReport(
        source_authority_valid=valid,
        input_rows=len(rows),
        unique_identifiers=len(by_key),
        duplicate_identifiers=duplicate_identifiers,
        conflicting_identifiers=conflicting_identifiers,
        available=available,
        unavailable=unavailable,
        unknown=unknown,
        blank_status=blank_status,
        invalid_quantity=invalid_quantity,
        unknown_status_values=unknown_tokens,
        source_date_present=source_date_present,
        source_date_age_days=age_days,
        freshness=freshness_class,
        deny_reasons=deny,
        rows=rows,
        manifest=manifest,
    )


def _catalog_indexes(
    catalog: Sequence[CatalogProduct],
) -> tuple[dict[tuple[str, str], list[CatalogProduct]], dict[tuple[str, str], list[CatalogProduct]]]:
    by_sku: dict[tuple[str, str], list[CatalogProduct]] = {}
    by_model: dict[tuple[str, str], list[CatalogProduct]] = {}
    for p in catalog:
        if p.deleted:
            continue
        b = canonicalize_brand(p.brand) or p.brand
        by_sku.setdefault((b, normalize_sku(p.sku)), []).append(p)
        if p.model:
            by_model.setdefault((b, normalize_sku(p.model)), []).append(p)
    return by_sku, by_model


def map_stock_to_catalog(
    report: ValidationReport,
    catalog: Sequence[CatalogProduct],
    *,
    brand: str,
    allow_exact_model: bool = False,
    allow_dasqua_pack_a: bool = True,
) -> list[MapResultRow]:
    """Exact-only mapper. Fuzzy/substring forbidden. Does not mutate catalog."""
    want = canonicalize_brand(brand)
    if not want:
        raise ValueError("brand_required")
    by_sku, by_model = _catalog_indexes(catalog)

    # Precompute DASQUA unique bases in catalog
    dasqua_bases: dict[str, list[CatalogProduct]] = {}
    if want == "DASQUA" and allow_dasqua_pack_a:
        for (b, sku), prods in by_sku.items():
            if b != "DASQUA":
                continue
            base = dasqua_pack_a_base(sku)
            if base:
                dasqua_bases.setdefault(base, []).extend(prods)
            elif dasqua_is_base(sku):
                dasqua_bases.setdefault(sku, []).extend(prods)

    # Detect duplicate source identities
    source_groups: dict[str, list[StockRow]] = {}
    for r in report.rows:
        if r.brand != want:
            continue
        if not r.identity_key:
            continue
        source_groups.setdefault(r.identity_key, []).append(r)

    results: list[MapResultRow] = []
    for r in report.rows:
        if r.brand and r.brand != want:
            results.append(
                MapResultRow(
                    source_row=r.source_row,
                    brand=r.brand or want,
                    manufacturer_sku=r.manufacturer_sku,
                    model=r.model,
                    normalized_status=r.normalized_status,
                    quantity=r.quantity,
                    match_class="NOT_FOUND",
                    match_detail="cross_brand_row_skipped",
                )
            )
            continue

        key = r.identity_key
        group = source_groups.get(key, [r])
        if len(group) > 1:
            statuses = {g.normalized_status for g in group}
            if len(statuses) > 1:
                results.append(
                    MapResultRow(
                        source_row=r.source_row,
                        brand=want,
                        manufacturer_sku=r.manufacturer_sku,
                        model=r.model,
                        normalized_status=r.normalized_status,
                        quantity=r.quantity,
                        match_class="SOURCE_CONFLICT",
                        match_detail="duplicate_identity_conflicting_status",
                        price_exception_flag=(normalize_sku(key) in TERMA_PRICE_EXCEPTION_SKUS),
                    )
                )
                continue
            if len(group) > 1:
                # duplicates same status
                pass

        match_class = "NOT_FOUND"
        detail = ""
        product_id = ""
        catalog_sku = ""

        # 1) Exact manufacturer SKU
        hits = by_sku.get((want, normalize_sku(r.manufacturer_sku)), []) if r.manufacturer_sku else []
        if len(hits) == 1:
            match_class = "EXACT_MATCH"
            detail = "EXACT_MANUFACTURER_SKU"
            product_id = hits[0].product_id
            catalog_sku = hits[0].sku
        elif len(hits) > 1:
            match_class = "AMBIGUOUS"
            detail = "multiple_catalog_sku_hits"

        # 2) DASQUA -A normalization (narrow)
        if match_class == "NOT_FOUND" and want == "DASQUA" and allow_dasqua_pack_a and r.manufacturer_sku:
            sku_n = normalize_sku(r.manufacturer_sku)
            base = dasqua_pack_a_base(sku_n)
            if base:
                # source is BASE-A → catalog BASE
                base_hits = by_sku.get(("DASQUA", base), [])
                if len(base_hits) == 1:
                    match_class = "EXACT_MATCH"
                    detail = "EXACT_NORMALIZED_SKU:dasqua_trailing_A"
                    product_id = base_hits[0].product_id
                    catalog_sku = base_hits[0].sku
                elif len(base_hits) > 1:
                    match_class = "AMBIGUOUS"
                    detail = "dasqua_base_ambiguous"
            elif dasqua_is_base(sku_n):
                # source BASE → catalog BASE-A unique
                pack = normalize_sku(f"{sku_n}-A")
                pack_hits = by_sku.get(("DASQUA", pack), [])
                if len(pack_hits) == 1:
                    match_class = "EXACT_MATCH"
                    detail = "EXACT_NORMALIZED_SKU:dasqua_trailing_A"
                    product_id = pack_hits[0].product_id
                    catalog_sku = pack_hits[0].sku

        # 3) Exact model (opt-in)
        if match_class == "NOT_FOUND" and allow_exact_model and r.model:
            mhits = by_model.get((want, normalize_sku(r.model)), [])
            if len(mhits) == 1:
                match_class = "EXACT_MATCH"
                detail = "EXACT_MODEL"
                product_id = mhits[0].product_id
                catalog_sku = mhits[0].sku
            elif len(mhits) > 1:
                match_class = "AMBIGUOUS"
                detail = "exact_model_ambiguous"

        if len(group) > 1 and match_class == "EXACT_MATCH":
            match_class = "DUPLICATE_SOURCE"
            detail = (detail + ";duplicate_source_same_status").strip(";")

        results.append(
            MapResultRow(
                source_row=r.source_row,
                brand=want,
                manufacturer_sku=r.manufacturer_sku,
                model=r.model,
                normalized_status=r.normalized_status,
                quantity=r.quantity,
                match_class=match_class,
                product_id=product_id,
                catalog_sku=catalog_sku,
                match_detail=detail,
                price_exception_flag=(
                    want == "TERMA"
                    and normalize_sku(r.manufacturer_sku or key) in TERMA_PRICE_EXCEPTION_SKUS
                ),
            )
        )
    return results


def activation_candidates_from_mapping(
    mapped: Sequence[MapResultRow],
    *,
    require_available: bool = True,
) -> list[MapResultRow]:
    """Future helper: stock-side candidates only. Does not merge price authority."""
    out: list[MapResultRow] = []
    for m in mapped:
        if m.match_class != "EXACT_MATCH":
            continue
        if require_available and m.normalized_status != "AVAILABLE":
            continue
        if m.price_exception_flag:
            # Stock does not repair price; still listable as stock-mapped but callers
            # must exclude from sale-wave until price authority exists.
            continue
        out.append(m)
    return out


def write_json(path: Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_mapping_csv(path: Path, rows: Sequence[MapResultRow]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(MapResultRow.__dataclass_fields__.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(asdict(r))
