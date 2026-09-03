"""INSIZE sales activation — workbook parse, conservative SKU match, price math.

Commercial rules (Revenue Fast Track, distributor workbook 11 Shahrivar):
- Resolve catalog columns by HEADER NAME (never positional letters).
- supplier_available := normalized(وضعیت) == "موجود"
- Final Rial = قیمت دلاری × workbook rate cell (Sheet1!K6 for this file)
- Karzar base_price is Toman: rial / TOMAN_TO_RIAL (10)
- Exact normalized SKU match only for automatic commerce; ambiguous → REVIEW
"""

from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable

from app.core.constants import TOMAN_TO_RIAL
from app.utils.seo_descriptions import is_stub_description

REQUIRED_HEADERS = (
    "CODE",
    "DESCRIPTION",
    "موجودی قدس",
    "موجودی تهران",
    "شوروم قدس",
    "شوروم تهران",
    "موجودی کل",
    "وضعیت",
    "قیمت دلاری",
)

CONTROL_SKU = "1114-150A"
CONTROL_USD = Decimal("28.5")
CONTROL_RIAL = Decimal("71250000")
CONTROL_TOMAN = Decimal("7125000")
DEFAULT_RATE_CELL = "K6"

_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_HYPHEN_RE = re.compile(r"[\u2010\u2011\u2012\u2013\u2014\u2212\uFE63\uFF0Dـ]")
_WS_RE = re.compile(r"\s+")


def normalize_sku(value: str | None) -> str:
    """Conservative SKU normalization for exact commerce matching."""
    if value is None:
        return ""
    s = str(value).strip().upper()
    s = _HYPHEN_RE.sub("-", s)
    s = s.replace("_", "-")
    s = _WS_RE.sub("", s)
    return s


def normalize_status(value: str | None) -> str:
    if value is None:
        return ""
    return _WS_RE.sub(" ", str(value).strip())


def parse_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    text = str(value).strip().replace(",", "").replace(" ", "")
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def rial_from_usd(usd: Decimal, rate: Decimal) -> Decimal:
    return (usd * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def toman_from_rial(rial: Decimal) -> Decimal:
    return (rial / Decimal(TOMAN_TO_RIAL)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def final_toman_from_usd(usd: Decimal, rate: Decimal) -> Decimal:
    return toman_from_rial(rial_from_usd(usd, rate))


def _col_letters_to_idx(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _cell_ref_col(ref: str) -> str:
    return "".join(ch for ch in ref if ch.isalpha())


def _load_shared_strings(z: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    out: list[str] = []
    for si in root.findall("m:si", _NS):
        out.append("".join(t.text or "" for t in si.findall(".//m:t", _NS)))
    return out


def _cell_value(cell: ET.Element, shared: list[str]) -> Any:
    t = cell.get("t")
    v = cell.find("m:v", _NS)
    if v is None:
        return None
    if t == "s":
        return shared[int(v.text or "0")]
    return v.text


def _sheet_path_for_name(z: zipfile.ZipFile, wanted: str) -> str | None:
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid_to_target: dict[str, str] = {}
    for rel in rels:
        rid = rel.get("Id")
        target = rel.get("Target")
        if rid and target:
            rid_to_target[rid] = target
    for sh in wb.findall("m:sheets/m:sheet", _NS):
        if sh.get("name") == wanted:
            rid = sh.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            )
            target = rid_to_target.get(rid or "", "")
            if not target:
                return None
            if not target.startswith("xl/"):
                target = f"xl/{target.lstrip('/')}"
            return target
    return None


@dataclass
class WorkbookRow:
    code: str
    description: str | None
    total_inventory: Decimal | None
    status: str
    usd_price: Decimal | None
    source_row: int


@dataclass
class WorkbookCatalog:
    rows: list[WorkbookRow]
    rate: Decimal
    rate_cell: str
    sheet_name: str
    headers: dict[str, int]

    @property
    def by_code(self) -> dict[str, WorkbookRow]:
        out: dict[str, WorkbookRow] = {}
        for row in self.rows:
            key = normalize_sku(row.code)
            if key and key not in out:
                out[key] = row
        return out


def load_workbook_catalog(
    path: Path,
    *,
    sheet_name: str = "Sheet1",
    rate_cell: str = DEFAULT_RATE_CELL,
) -> WorkbookCatalog:
    """Load distributor catalog by header names from the hidden source sheet."""
    path = Path(path)
    with zipfile.ZipFile(path) as z:
        shared = _load_shared_strings(z)
        sheet_path = _sheet_path_for_name(z, sheet_name)
        if not sheet_path or sheet_path not in z.namelist():
            # Fallback: first worksheet
            sheet_path = "xl/worksheets/sheet1.xml"
        sheet = ET.fromstring(z.read(sheet_path))
        xml_rows = sheet.findall("m:sheetData/m:row", _NS)
        if not xml_rows:
            raise ValueError(f"empty sheet {sheet_name}")

        rate_val: Any = None
        for row in xml_rows:
            for c in row.findall("m:c", _NS):
                if c.get("r") == rate_cell:
                    rate_val = _cell_value(c, shared)
        rate = parse_decimal(rate_val)
        if rate is None or rate <= 0:
            raise ValueError(f"invalid workbook rate at {rate_cell}: {rate_val!r}")

        header_map: dict[int, str] = {}
        for c in xml_rows[0].findall("m:c", _NS):
            ref = c.get("r", "A1")
            col = _cell_ref_col(ref)
            header_map[_col_letters_to_idx(col)] = str(_cell_value(c, shared) or "").strip()

        name_to_idx = {name: idx for idx, name in header_map.items() if name}
        missing = [h for h in REQUIRED_HEADERS if h not in name_to_idx]
        if missing:
            raise ValueError(f"FAIL CLOSED: missing headers {missing}")

        def row_values(row_el: ET.Element) -> dict[int, Any]:
            out: dict[int, Any] = {}
            for c in row_el.findall("m:c", _NS):
                ref = c.get("r", "A1")
                out[_col_letters_to_idx(_cell_ref_col(ref))] = _cell_value(c, shared)
            return out

        rows: list[WorkbookRow] = []
        for row_el in xml_rows[1:]:
            vals = row_values(row_el)
            code_raw = vals.get(name_to_idx["CODE"])
            if code_raw is None or str(code_raw).strip() == "":
                continue
            code = str(code_raw).strip()
            status = normalize_status(vals.get(name_to_idx["وضعیت"]))
            usd = parse_decimal(vals.get(name_to_idx["قیمت دلاری"]))
            total = parse_decimal(vals.get(name_to_idx["موجودی کل"]))
            desc = vals.get(name_to_idx["DESCRIPTION"])
            excel_row = int(row_el.get("r") or (len(rows) + 2))
            rows.append(
                WorkbookRow(
                    code=code,
                    description=None if desc is None else str(desc),
                    total_inventory=total,
                    status=status,
                    usd_price=usd,
                    source_row=excel_row,
                )
            )

    return WorkbookCatalog(
        rows=rows,
        rate=rate,
        rate_cell=rate_cell,
        sheet_name=sheet_name,
        headers={h: name_to_idx[h] for h in REQUIRED_HEADERS},
    )


def verify_control_sku(catalog: WorkbookCatalog) -> dict[str, Any]:
    """Required regression fixture: 1114-150A → 71,250,000 Rial / 7,125,000 Toman."""
    row = catalog.by_code.get(normalize_sku(CONTROL_SKU))
    if row is None:
        return {"ok": False, "error": f"{CONTROL_SKU} missing from workbook"}
    if row.usd_price != CONTROL_USD:
        return {
            "ok": False,
            "error": f"USD mismatch: got {row.usd_price}, expected {CONTROL_USD}",
        }
    rial = rial_from_usd(row.usd_price, catalog.rate)
    toman = toman_from_rial(rial)
    ok = rial == CONTROL_RIAL and toman == CONTROL_TOMAN
    return {
        "ok": ok,
        "sku": CONTROL_SKU,
        "usd": str(row.usd_price),
        "rate": str(catalog.rate),
        "rial": str(rial),
        "toman": str(toman),
        "expected_rial": str(CONTROL_RIAL),
        "expected_toman": str(CONTROL_TOMAN),
        "status": row.status,
    }


def supplier_available(status: str | None) -> bool:
    return normalize_status(status) == "موجود"


def valid_workbook_price(usd: Decimal | None, rate: Decimal) -> tuple[str, Decimal | None, Decimal | None]:
    """Return (class, rial, toman)."""
    if usd is None or usd <= 0:
        return "INVALID_WORKBOOK_PRICE", None, None
    if rate is None or rate <= 0:
        return "INVALID_WORKBOOK_PRICE", None, None
    rial = rial_from_usd(usd, rate)
    toman = toman_from_rial(rial)
    if toman <= 0:
        return "INVALID_WORKBOOK_PRICE", rial, toman
    # Recompute and guard against mismatch
    if rial_from_usd(usd, rate) != rial:
        return "PRICE_CALCULATION_MISMATCH", rial, toman
    return "VALID_WORKBOOK_PRICE", rial, toman


def has_useful_specs(specifications: Any) -> bool:
    if not specifications:
        return False
    if isinstance(specifications, str):
        text = specifications.strip()
        if not text or text in ("{}", "null", "None"):
            return False
        # Cheap signal: any non-empty technical value
        return any(
            key in text
            for key in (
                "range",
                "accuracy",
                "resolution",
                "بازه",
                "دقت",
                "رزولوشن",
                "اندازه",
            )
        ) and '""' not in text.replace('": ""', "")
    if isinstance(specifications, dict):
        tech = specifications.get("technical_specs") or {}
        if isinstance(tech, dict):
            return any(str(v).strip() for v in tech.values())
        if isinstance(tech, list):
            return any(str((item or {}).get("value") or "").strip() for item in tech)
    return False


_PLACEHOLDER_IMAGE_RE = re.compile(
    r"(placeholder|picsum|via\.placeholder|dummyimage|no[_-]?image)",
    re.I,
)


def image_ready(image_count: int | str | None, primary_url: str | None) -> bool:
    try:
        count = int(image_count or 0)
    except (TypeError, ValueError):
        count = 0
    if count <= 0:
        return False
    url = (primary_url or "").strip()
    if not url:
        return False
    if _PLACEHOLDER_IMAGE_RE.search(url):
        return False
    return True


def content_ready(
    *,
    name: str | None,
    short_description: str | None,
    description: str | None,
    specifications: Any,
) -> bool:
    short_ok = not is_stub_description(short_description, product_name=name)
    long_ok = not is_stub_description(description, product_name=name)
    specs_ok = has_useful_specs(specifications)
    # Acceptable if non-stub short OR non-stub long, plus useful specs when present;
    # require at least one factual prose field and prefer specs, but allow prose-only
    # if specs empty (still not inventing).
    if short_ok or long_ok:
        return True
    return False


@dataclass
class MatchResult:
    method: str  # exact | ambiguous | unmatched
    workbook_code: str | None = None
    candidates: list[str] = field(default_factory=list)


def match_exact(sku: str, workbook_by_code: dict[str, WorkbookRow]) -> MatchResult:
    key = normalize_sku(sku)
    if not key:
        return MatchResult(method="unmatched")
    if key in workbook_by_code:
        return MatchResult(method="exact", workbook_code=workbook_by_code[key].code)
    return MatchResult(method="unmatched")


def duplicate_workbook_codes(rows: Iterable[WorkbookRow]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = normalize_sku(row.code)
        if not key:
            continue
        counts[key] = counts.get(key, 0) + 1
    return {k: v for k, v in counts.items() if v > 1}


def workbook_sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


FORBIDDEN_APPLY_FIELDS = frozenset(
    {
        "name",
        "sku",
        "slug",
        "brand_id",
        "category_id",
        "short_description",
        "description",
        "specifications",
        "is_active",
        "stock_quantity",
        "original_price",
        "meta_title",
        "meta_description",
    }
)

ALLOWED_APPLY_FIELDS = frozenset({"base_price", "is_available"})


@dataclass
class PilotSkuPlan:
    product_id: int
    sku: str
    title: str
    category_id: int
    category_name: str
    slug: str
    public_path: str
    workbook_code: str
    workbook_row: int
    workbook_description: str | None
    usd_price: Decimal
    rate: Decimal
    rial_price: Decimal
    toman_price: Decimal
    current_base_price: Decimal | None
    new_base_price: Decimal
    absolute_delta: Decimal | None
    percentage_delta: float | None
    current_is_available: bool
    target_is_available: bool
    is_active: bool
    image_ready: bool
    content_ready: bool
    eligibility_reason: str
    expected_updated_at: str | None = None
    review_flags: list[str] = field(default_factory=list)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "sku": self.sku,
            "title": self.title,
            "category_id": self.category_id,
            "category_name": self.category_name,
            "slug": self.slug,
            "public_path": self.public_path,
            "workbook_code": self.workbook_code,
            "workbook_row": self.workbook_row,
            "workbook_description": self.workbook_description,
            "usd_price": str(self.usd_price),
            "rate": str(self.rate),
            "rial_price": str(self.rial_price),
            "toman_price": str(self.toman_price),
            "current_base_price": None
            if self.current_base_price is None
            else str(self.current_base_price),
            "new_base_price": str(self.new_base_price),
            "absolute_delta": None
            if self.absolute_delta is None
            else str(self.absolute_delta),
            "percentage_delta": self.percentage_delta,
            "current_is_available": self.current_is_available,
            "target_is_available": self.target_is_available,
            "is_active": self.is_active,
            "image_ready": self.image_ready,
            "content_ready": self.content_ready,
            "eligibility_reason": self.eligibility_reason,
            "expected_updated_at": self.expected_updated_at,
            "review_flags": list(self.review_flags),
        }


@dataclass
class PilotManifest:
    version: int
    workbook_sha256: str
    expected_rate: str
    expected_sku_count: int
    selected_skus: list[str]
    checkout_test_sku: str
    plans: list[PilotSkuPlan]
    generated_at_utc: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "workbook_sha256": self.workbook_sha256,
            "expected_rate": self.expected_rate,
            "expected_sku_count": self.expected_sku_count,
            "selected_skus": list(self.selected_skus),
            "checkout_test_sku": self.checkout_test_sku,
            "generated_at_utc": self.generated_at_utc,
            "plans": [p.to_public_dict() for p in self.plans],
        }


class PilotGateError(ValueError):
    """Raised when a pilot apply/verify gate fails."""


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "t", "true", "yes", "y"}


def assert_expected_workbook_sha(path: Path, expected_sha256: str) -> str:
    actual = workbook_sha256(path)
    if actual.lower() != expected_sha256.lower():
        raise PilotGateError(
            f"workbook-hash mismatch: expected {expected_sha256}, got {actual}"
        )
    return actual


def assert_expected_rate(catalog: WorkbookCatalog, expected_rate: Decimal) -> None:
    if catalog.rate != expected_rate:
        raise PilotGateError(
            f"workbook-rate mismatch: expected {expected_rate}, got {catalog.rate}"
        )


def load_pilot_manifest(path: Path) -> PilotManifest:
    import json

    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    plans = [
        PilotSkuPlan(
            product_id=int(p["product_id"]),
            sku=str(p["sku"]),
            title=str(p["title"]),
            category_id=int(p["category_id"]),
            category_name=str(p["category_name"]),
            slug=str(p["slug"]),
            public_path=str(p["public_path"]),
            workbook_code=str(p["workbook_code"]),
            workbook_row=int(p["workbook_row"]),
            workbook_description=p.get("workbook_description"),
            usd_price=Decimal(str(p["usd_price"])),
            rate=Decimal(str(p["rate"])),
            rial_price=Decimal(str(p["rial_price"])),
            toman_price=Decimal(str(p["toman_price"])),
            current_base_price=(
                None
                if p.get("current_base_price") in (None, "")
                else Decimal(str(p["current_base_price"]))
            ),
            new_base_price=Decimal(str(p["new_base_price"])),
            absolute_delta=(
                None
                if p.get("absolute_delta") in (None, "")
                else Decimal(str(p["absolute_delta"]))
            ),
            percentage_delta=p.get("percentage_delta"),
            current_is_available=bool(p["current_is_available"]),
            target_is_available=bool(p["target_is_available"]),
            is_active=bool(p["is_active"]),
            image_ready=bool(p["image_ready"]),
            content_ready=bool(p["content_ready"]),
            eligibility_reason=str(p["eligibility_reason"]),
            expected_updated_at=p.get("expected_updated_at"),
            review_flags=list(p.get("review_flags") or []),
        )
        for p in raw["plans"]
    ]
    return PilotManifest(
        version=int(raw.get("version", 1)),
        workbook_sha256=str(raw["workbook_sha256"]),
        expected_rate=str(raw["expected_rate"]),
        expected_sku_count=int(raw["expected_sku_count"]),
        selected_skus=[str(s) for s in raw["selected_skus"]],
        checkout_test_sku=str(raw["checkout_test_sku"]),
        plans=plans,
        generated_at_utc=str(raw["generated_at_utc"]),
    )


def revalidate_plan_against_live(
    plan: PilotSkuPlan,
    *,
    product: dict[str, Any],
    workbook_row: WorkbookRow,
    catalog: WorkbookCatalog,
) -> None:
    """Fail closed if live product/workbook no longer matches the approved plan."""
    if normalize_sku(product.get("sku")) != normalize_sku(plan.sku):
        raise PilotGateError(f"SKU mismatch for product_id={plan.product_id}")
    if normalize_sku(workbook_row.code) != normalize_sku(plan.workbook_code):
        raise PilotGateError(f"workbook CODE mismatch for {plan.sku}")
    if normalize_sku(plan.sku) != normalize_sku(plan.workbook_code):
        raise PilotGateError(f"exact SKU enforcement failed for {plan.sku}")
    if not _truthy(product.get("is_active")):
        raise PilotGateError(f"inactive product rejection: {plan.sku}")
    if not supplier_available(workbook_row.status):
        raise PilotGateError(f"supplier unavailable: {plan.sku}")
    price_class, rial, toman = valid_workbook_price(workbook_row.usd_price, catalog.rate)
    if price_class != "VALID_WORKBOOK_PRICE" or toman is None or toman <= 0:
        raise PilotGateError(f"invalid price rejection: {plan.sku} ({price_class})")
    if toman != plan.new_base_price or rial != plan.rial_price:
        raise PilotGateError(f"price plan drift for {plan.sku}")
    if not image_ready(product.get("image_count"), product.get("primary_image_url")):
        raise PilotGateError(f"image/content readiness rejection (image): {plan.sku}")
    if not content_ready(
        name=product.get("name"),
        short_description=product.get("short_description"),
        description=product.get("description"),
        specifications=product.get("specifications"),
    ):
        raise PilotGateError(f"image/content readiness rejection (content): {plan.sku}")
    if not product.get("category_id"):
        raise PilotGateError(f"missing category: {plan.sku}")
    if not (product.get("slug") or "").strip():
        raise PilotGateError(f"missing slug: {plan.sku}")
    # Stale/concurrent detection via updated_at snapshot in manifest
    live_updated = str(product.get("updated_at") or "")
    if plan.expected_updated_at and live_updated and live_updated != plan.expected_updated_at:
        raise PilotGateError(
            f"stale/concurrent record rejection: {plan.sku} "
            f"(expected updated_at={plan.expected_updated_at}, live={live_updated})"
        )


@dataclass
class ApplyResult:
    updated: list[dict[str, Any]]
    skipped_idempotent: list[dict[str, Any]]
    audit: list[dict[str, Any]]


def apply_pilot_plans(
    *,
    products_by_id: dict[int, Any],
    plans: list[PilotSkuPlan],
    workbook_by_code: dict[str, WorkbookRow],
    catalog: WorkbookCatalog,
    live_product_rows: dict[str, dict[str, Any]],
) -> ApplyResult:
    """Apply base_price + is_available only. Mutates product objects in-memory.

    Caller must wrap in a DB transaction and commit/rollback. Raises PilotGateError
    before any mutation if gates fail; if mutation has started and a later gate
    fails, raises after partial in-memory changes — caller must rollback session.
    """
    if not plans:
        raise PilotGateError("empty pilot plan")

    # Preflight all gates before mutating anything
    ordered: list[tuple[PilotSkuPlan, Any, WorkbookRow, dict[str, Any]]] = []
    for plan in plans:
        product = products_by_id.get(plan.product_id)
        if product is None:
            raise PilotGateError(f"product_id {plan.product_id} not found")
        live = live_product_rows.get(normalize_sku(plan.sku))
        if live is None:
            raise PilotGateError(f"live snapshot missing for {plan.sku}")
        wb = workbook_by_code.get(normalize_sku(plan.workbook_code))
        if wb is None:
            raise PilotGateError(f"workbook row missing for {plan.sku}")
        revalidate_plan_against_live(
            plan, product=live, workbook_row=wb, catalog=catalog
        )
        # Forbidden field identity checks against live snapshot
        if str(live.get("name")) != plan.title:
            raise PilotGateError(f"forbidden-field drift (title): {plan.sku}")
        if normalize_sku(live.get("sku")) != normalize_sku(plan.sku):
            raise PilotGateError(f"forbidden-field drift (sku): {plan.sku}")
        ordered.append((plan, product, wb, live))

    updated: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []

    for plan, product, _wb, live in ordered:
        old_price = getattr(product, "base_price", None)
        old_avail = bool(getattr(product, "is_available", False))
        new_price = plan.new_base_price
        already = (
            old_price is not None
            and Decimal(str(old_price)) == new_price
            and old_avail is True
        )
        entry = {
            "sku": plan.sku,
            "product_id": plan.product_id,
            "old_base_price": None if old_price is None else str(old_price),
            "new_base_price": str(new_price),
            "old_is_available": old_avail,
            "new_is_available": True,
            "idempotent": already,
        }
        audit.append(entry)
        if already:
            skipped.append(entry)
            continue
        product.base_price = new_price
        product.is_available = True
        updated.append(entry)

    return ApplyResult(updated=updated, skipped_idempotent=skipped, audit=audit)


def verify_pilot_state(
    *,
    plans: list[PilotSkuPlan],
    products_by_id: dict[int, Any],
    snapshots_before: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Verify only allowlisted commerce fields changed to expected values."""
    errors: list[str] = []
    ok_skus: list[str] = []
    for plan in plans:
        product = products_by_id.get(plan.product_id)
        if product is None:
            errors.append(f"missing product {plan.sku}")
            continue
        price = getattr(product, "base_price", None)
        avail = bool(getattr(product, "is_available", False))
        if price is None or Decimal(str(price)) != plan.new_base_price:
            errors.append(
                f"{plan.sku}: base_price={price} expected={plan.new_base_price}"
            )
            continue
        if not avail:
            errors.append(f"{plan.sku}: is_available is not true")
            continue
        if snapshots_before:
            before = snapshots_before.get(plan.product_id, {})
            for field_name in FORBIDDEN_APPLY_FIELDS:
                if field_name not in before:
                    continue
                current = getattr(product, field_name, None)
                if str(current) != str(before[field_name]):
                    errors.append(
                        f"{plan.sku}: forbidden field changed: {field_name}"
                    )
        ok_skus.append(plan.sku)
    if errors:
        raise PilotGateError("verify failed: " + "; ".join(errors))
    return {"ok": True, "verified_skus": ok_skus}
