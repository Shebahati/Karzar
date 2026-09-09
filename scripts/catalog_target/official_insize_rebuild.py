"""Guarded official INSIZE Wave 1 content+identity rebuild (dry-run default).

Mutates ONLY: name, short_description, description, specifications,
meta_title, meta_description.

Never mutates commerce, SKU, slug, brand, category, or media.
Shopmill is forbidden as authority and as string content.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from catalog_target.sales_wave_apply import (
    ALLOW_ENV,
    CATEGORY_ENV,
    PROD_HOST_MARKER,
    ApplyAbort,
    assert_production_apply_authorized,
    connect_runtime_db,
    normalize_database_url,
    sha256_file,
)

MUTABLE_COLUMNS = (
    "name",
    "short_description",
    "description",
    "specifications",
    "meta_title",
    "meta_description",
)

FORBIDDEN_PAYLOAD_FIELDS = (
    "base_price",
    "original_price",
    "tax_percent",
    "is_available",
    "is_active",
    "stock_quantity",
    "sku",
    "slug",
    "brand_id",
    "category_id",
)

FORBIDDEN_MUTATION_COLUMNS = (
    "sku",
    "slug",
    "brand_id",
    "category_id",
    "base_price",
    "original_price",
    "tax_percent",
    "is_available",
    "is_active",
    "stock_quantity",
    "deleted_at",
)

ALLOWED_COMPLETENESS = "OFFICIAL_REBUILD_READY"
ALLOWED_MATCH_CLASSES = frozenset({"EXACT_SKU", "EXACT_MODEL", "EXACT_SKU_AND_MODEL"})
EXCLUDED_COMPLETENESS = frozenset({"OFFICIAL_PARTIAL", "MANUAL_OFFICIAL_REVIEW", "SOURCE_CONFLICT"})

SHOPMILL_RE = re.compile(r"shopmill|shopmilltools", re.I)
HTML_RE = re.compile(
    r"</?(?:html|body|div|span|p|br|ul|ol|li|table|tr|td|th|a|img|script|style|font|b|i|em|strong)\b[^>]*>",
    re.I,
)
PLACEHOLDER_RE = re.compile(r"\b(TODO|TBD|FIXME|PLACEHOLDER|lorem ipsum)\b", re.I)
MODEL_TOKEN_RE = re.compile(
    r"(?:مدل|کد|کدل)\s*([0-9A-Za-z]+(?:-[0-9A-Za-z]+)*)",
    re.I,
)

WAVE1_ALLOWLIST_COUNT = 158
DEFAULT_EVIDENCE_DIR = Path(".local-scratch/insize-wave1-official-rebuild")
DEFAULT_PLAN_CSV_RELATIVE = "data/catalog-target/insize_official_rebuild_plan.csv"
DEFAULT_PLAN_JSON_RELATIVE = "data/catalog-target/insize_official_rebuild_plan.json"

# Filled after first reviewed plan generation; tests may override via load path.
REVIEWED_PLAN_CSV_SHA256 = ""

REQUIRED_PLAN_FIELDS = (
    "product_id",
    "site_sku",
    "current_name",
    "proposed_name",
    "current_short_description_hash",
    "proposed_short_description",
    "current_description_hash",
    "proposed_description",
    "current_specifications_hash",
    "proposed_specifications",
    "current_meta_title",
    "proposed_meta_title",
    "current_meta_description_hash",
    "proposed_meta_description",
    "official_model",
    "official_product_name",
    "official_source_id",
    "official_source_page",
    "official_fact_count",
    "mapping_class",
    "title_class",
    "completeness",
)


class DbConnection(Protocol):
    def cursor(self, *args: Any, **kwargs: Any) -> Any: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


@dataclass(frozen=True)
class PlanRow:
    product_id: int
    site_sku: str
    current_name: str
    proposed_name: str
    current_short_description_hash: str
    proposed_short_description: str
    current_description_hash: str
    proposed_description: str
    current_specifications_hash: str
    proposed_specifications: str
    current_meta_title: str
    proposed_meta_title: str
    current_meta_description_hash: str
    proposed_meta_description: str
    official_model: str
    official_product_name: str
    official_source_id: str
    official_source_page: str
    official_fact_count: int
    mapping_class: str
    title_class: str
    completeness: str
    current_short_description: str = ""
    current_description: str = ""
    current_specifications: str = ""
    current_meta_description: str = ""
    priority_class: str = ""
    expected_updated_at: str = ""


@dataclass(frozen=True)
class LiveContentProduct:
    id: int
    sku: str
    name: str
    slug: str
    brand_id: int | None
    category_id: int | None
    short_description: str
    description: str
    specifications: str
    meta_title: str
    meta_description: str
    updated_at: str
    base_price: str = ""
    is_active: bool | None = None
    is_available: bool | None = None
    deleted_at: str | None = None


@dataclass
class StaleGuardResult:
    ok: bool
    expected_count: int
    observed_count: int
    drifts: list[dict[str, Any]] = field(default_factory=list)
    missing_ids: list[int] = field(default_factory=list)
    extra_ids: list[int] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ApplyRunResult:
    mode: str
    production_apply_executed: bool
    aborted: bool
    abort_reason: str = ""
    plan_rows: int = 0
    stale_guard: dict[str, Any] = field(default_factory=dict)
    backup_path: str = ""
    backup_sha256: str = ""
    rollback_sql_path: str = ""
    updated_count: int = 0
    transaction_safeguards: dict[str, Any] = field(default_factory=dict)
    dry_run_lines: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def content_hash(value: str | None) -> str:
    raw = (value or "").encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def norm_code(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    trans = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    text = text.translate(trans)
    text = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", text)
    text = re.sub(r"\s+", "", text)
    return text.upper()


def assert_no_shopmill(text: str, *, context: str) -> None:
    if SHOPMILL_RE.search(text or ""):
        raise ApplyAbort(f"shopmill_string_forbidden:{context}")


def assert_payload_content_only(payload: dict[str, Any]) -> None:
    forbidden = [key for key in FORBIDDEN_PAYLOAD_FIELDS if key in payload]
    if forbidden:
        raise ApplyAbort(f"forbidden_payload_fields:{','.join(sorted(forbidden))}")


def customer_facing_specifications(raw: Any) -> dict[str, Any]:
    """Whole-field official specs without Shopmill or source URLs."""
    if isinstance(raw, str):
        if not raw.strip():
            return {"technical_specs": {}, "features": [], "authority": "official_insize"}
        raw = json.loads(raw)
    if not isinstance(raw, dict):
        raise ApplyAbort("specifications_not_object")
    assert_no_shopmill(json.dumps(raw, ensure_ascii=False), context="specifications")

    tech_in = raw.get("technical_specs") or {}
    if not isinstance(tech_in, dict):
        raise ApplyAbort("technical_specs_not_object")
    tech_out: dict[str, str] = {}
    for key, val in tech_in.items():
        if str(key).startswith("_"):
            continue
        if isinstance(val, dict):
            value = str(val.get("value") or val.get("normalized_value") or "").strip()
        else:
            value = str(val).strip()
        if not value:
            continue
        assert_no_shopmill(value, context=f"spec:{key}")
        if re.search(r"https?://|shopmill", value, re.I):
            raise ApplyAbort(f"spec_value_has_url_or_reseller:{key}")
        tech_out[str(key)] = value

    features_in = raw.get("features") or []
    features_out: list[str] = []
    if isinstance(features_in, list):
        for item in features_in:
            text = str(item).strip()
            if not text:
                continue
            assert_no_shopmill(text, context="feature")
            features_out.append(text)

    out = {
        "technical_specs": tech_out,
        "features": features_out,
        "authority": "official_insize",
    }
    assert_no_shopmill(json.dumps(out, ensure_ascii=False), context="customer_specs")
    return out


def extract_model_from_title(name: str) -> str | None:
    match = MODEL_TOKEN_RE.search(name or "")
    if not match:
        return None
    return match.group(1).strip()


def extract_persian_type(current_name: str, official_product_name: str) -> str:
    official = (official_product_name or "").strip()
    official = re.sub(r"\s+", " ", official)
    if official and re.search(r"[\u0600-\u06FF]", official):
        # Prefer short official Persian name from product list.
        cleaned = re.sub(r"\s+\d[\d./~\-]*$", "", official).strip()
        if 2 <= len(cleaned) <= 60:
            return cleaned

    text = current_name or ""
    text = re.sub(r"\(Insize\)", "", text, flags=re.I)
    text = re.sub(r"\bInsize\b", "", text, flags=re.I)
    text = re.sub(r"اینسایز", "", text)
    text = MODEL_TOKEN_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" -–—|")
    if not text or not re.search(r"[\u0600-\u06FF]", text):
        raise ApplyAbort("persian_product_type_unavailable")
    return text


def _reversed_model(model: str) -> str | None:
    parts = (model or "").split("-")
    if len(parts) != 2:
        return None
    return f"{parts[1]}-{parts[0]}"


def build_proposed_title(
    *,
    site_sku: str,
    official_model: str,
    official_product_name: str,
    current_name: str,
) -> tuple[str, str]:
    """Return (proposed_name, title_class)."""
    if norm_code(site_sku) != norm_code(official_model):
        raise ApplyAbort(f"sku_model_mismatch:{site_sku}:{official_model}")

    persian_type = extract_persian_type(current_name, official_product_name)
    proposed = f"{persian_type} اینسایز مدل {official_model}"
    proposed = re.sub(r"\s+", " ", proposed).strip()
    assert_no_shopmill(proposed, context="proposed_name")

    current_model = extract_model_from_title(current_name)
    current_type = extract_persian_type(current_name, "")
    official_type = (official_product_name or "").strip()
    reversed_model = _reversed_model(official_model)
    current_compact = re.sub(r"\s+", "", current_name or "")

    # Material meaning change: official Persian name conflicts with current type.
    if (
        official_type
        and re.search(r"[\u0600-\u06FF]", official_type)
        and current_type
        and not _persian_type_overlap(current_type, official_type)
        and not _persian_type_overlap(current_type, persian_type)
    ):
        return proposed, "MATERIAL_IDENTITY_CHANGE"

    if current_model and norm_code(current_model) == norm_code(official_model):
        return proposed, "SAFE_IDENTITY_CORRECTION"

    if current_model and norm_code(current_model) != norm_code(official_model):
        if _persian_type_overlap(current_type, persian_type):
            return proposed, "SAFE_IDENTITY_CORRECTION"
        return proposed, "MATERIAL_IDENTITY_CHANGE"

    # Model token missing, but reversed official order is present in the title.
    if reversed_model and (
        reversed_model in current_name
        or norm_code(reversed_model) in norm_code(current_compact)
    ):
        if _persian_type_overlap(current_type, persian_type):
            return proposed, "SAFE_IDENTITY_CORRECTION"

    # Official model already present with formatting differences only.
    if official_model in current_name or norm_code(official_model) in norm_code(current_compact):
        return proposed, "SAFE_IDENTITY_CORRECTION"

    return proposed, "MANUAL_TITLE_REVIEW"


def _normalize_title_compare(value: str) -> str:
    text = value or ""
    text = re.sub(r"\(Insize\)", "", text, flags=re.I)
    text = re.sub(r"\s+", "", text)
    return text.casefold()


def _persian_tokens(text: str) -> set[str]:
    return {tok for tok in re.findall(r"[\u0600-\u06FF]{2,}", text or "") if tok not in {"مدل", "کد"}}


def _persian_type_overlap(a: str, b: str) -> bool:
    ta, tb = _persian_tokens(a), _persian_tokens(b)
    if not ta or not tb:
        return False
    return bool(ta & tb)


def validate_proposed_content(row: PlanRow) -> None:
    blob = "\n".join(
        [
            row.proposed_name,
            row.proposed_short_description,
            row.proposed_description,
            row.proposed_specifications,
            row.proposed_meta_title,
            row.proposed_meta_description,
        ]
    )
    assert_no_shopmill(blob, context=f"product:{row.site_sku}")
    if HTML_RE.search(blob):
        raise ApplyAbort(f"unexpected_html:{row.site_sku}")
    if PLACEHOLDER_RE.search(blob):
        raise ApplyAbort(f"placeholder_string:{row.site_sku}")
    if row.site_sku not in row.proposed_name:
        raise ApplyAbort(f"title_missing_official_model:{row.site_sku}")
    if row.site_sku not in row.proposed_short_description and row.site_sku not in row.proposed_description:
        raise ApplyAbort(f"content_missing_official_model:{row.site_sku}")
    if norm_code(row.site_sku) != norm_code(row.official_model):
        raise ApplyAbort(f"plan_sku_model_mismatch:{row.site_sku}")
    if row.completeness != ALLOWED_COMPLETENESS:
        raise ApplyAbort(f"completeness_not_ready:{row.site_sku}:{row.completeness}")
    if row.mapping_class not in ALLOWED_MATCH_CLASSES:
        raise ApplyAbort(f"mapping_not_exact:{row.site_sku}:{row.mapping_class}")
    if row.title_class == "MATERIAL_IDENTITY_CHANGE":
        raise ApplyAbort(f"material_identity_in_plan:{row.site_sku}")
    if row.title_class == "MANUAL_TITLE_REVIEW":
        raise ApplyAbort(f"manual_title_in_plan:{row.site_sku}")
    specs = customer_facing_specifications(row.proposed_specifications)
    if not specs.get("technical_specs") and not specs.get("features"):
        raise ApplyAbort(f"empty_official_specs:{row.site_sku}")


def load_allowlist_ids(path: Path) -> set[int]:
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    ids = {int(r.get("product_id") or r.get("id")) for r in rows}
    if len(ids) != WAVE1_ALLOWLIST_COUNT:
        raise ApplyAbort(f"allowlist_count_mismatch:expected={WAVE1_ALLOWLIST_COUNT}:got={len(ids)}")
    return ids


def load_and_validate_plan(path: Path, *, allowlist_ids: set[int] | None = None) -> list[PlanRow]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(REQUIRED_PLAN_FIELDS) - set(reader.fieldnames or [])
        if missing:
            raise ApplyAbort(f"plan_missing_fields:{','.join(sorted(missing))}")
        rows: list[PlanRow] = []
        seen: set[int] = set()
        for raw in reader:
            pid = int(str(raw["product_id"]).strip())
            if pid in seen:
                raise ApplyAbort(f"duplicate_plan_product_id:{pid}")
            seen.add(pid)
            row = PlanRow(
                product_id=pid,
                site_sku=str(raw["site_sku"]).strip(),
                current_name=raw.get("current_name") or "",
                proposed_name=raw.get("proposed_name") or "",
                current_short_description_hash=raw.get("current_short_description_hash") or "",
                proposed_short_description=raw.get("proposed_short_description") or "",
                current_description_hash=raw.get("current_description_hash") or "",
                proposed_description=raw.get("proposed_description") or "",
                current_specifications_hash=raw.get("current_specifications_hash") or "",
                proposed_specifications=raw.get("proposed_specifications") or "",
                current_meta_title=raw.get("current_meta_title") or "",
                proposed_meta_title=raw.get("proposed_meta_title") or "",
                current_meta_description_hash=raw.get("current_meta_description_hash") or "",
                proposed_meta_description=raw.get("proposed_meta_description") or "",
                official_model=raw.get("official_model") or "",
                official_product_name=raw.get("official_product_name") or "",
                official_source_id=raw.get("official_source_id") or "",
                official_source_page=raw.get("official_source_page") or "",
                official_fact_count=int(str(raw.get("official_fact_count") or "0")),
                mapping_class=raw.get("mapping_class") or "",
                title_class=raw.get("title_class") or "",
                completeness=raw.get("completeness") or "",
                priority_class=raw.get("priority_class") or "",
                expected_updated_at=raw.get("expected_updated_at") or "",
            )
            validate_proposed_content(row)
            payload = plan_row_to_update_payload(row)
            assert_payload_content_only(payload)
            rows.append(row)
    if allowlist_ids is not None:
        outside = [r.product_id for r in rows if r.product_id not in allowlist_ids]
        if outside:
            raise ApplyAbort(f"plan_outside_allowlist:{outside[:5]}")
    return rows


def plan_row_to_update_payload(row: PlanRow) -> dict[str, Any]:
    specs = customer_facing_specifications(row.proposed_specifications)
    payload = {
        "name": row.proposed_name,
        "short_description": row.proposed_short_description,
        "description": row.proposed_description,
        "specifications": specs,
        "meta_title": row.proposed_meta_title,
        "meta_description": row.proposed_meta_description,
    }
    assert_payload_content_only(payload)
    return payload


def stale_guard(plan_rows: list[PlanRow], live_rows: list[LiveContentProduct]) -> StaleGuardResult:
    by_id = {row.id: row for row in live_rows}
    expected_ids = [row.product_id for row in plan_rows]
    missing = [pid for pid in expected_ids if pid not in by_id]
    extra = [pid for pid in by_id if pid not in set(expected_ids)]
    drifts: list[dict[str, Any]] = []
    for plan in plan_rows:
        live = by_id.get(plan.product_id)
        if live is None:
            continue
        if live.sku != plan.site_sku:
            drifts.append({"id": plan.product_id, "field": "sku", "expected": plan.site_sku, "observed": live.sku})
        if live.name != plan.current_name:
            drifts.append({"id": plan.product_id, "field": "name", "expected": plan.current_name, "observed": live.name})
        if content_hash(live.short_description) != plan.current_short_description_hash:
            drifts.append({"id": plan.product_id, "field": "short_description_hash"})
        if content_hash(live.description) != plan.current_description_hash:
            drifts.append({"id": plan.product_id, "field": "description_hash"})
        if content_hash(live.specifications) != plan.current_specifications_hash:
            drifts.append({"id": plan.product_id, "field": "specifications_hash"})
        if (live.meta_title or "") != (plan.current_meta_title or ""):
            drifts.append({"id": plan.product_id, "field": "meta_title"})
        if content_hash(live.meta_description) != plan.current_meta_description_hash:
            drifts.append({"id": plan.product_id, "field": "meta_description_hash"})
        if plan.expected_updated_at and live.updated_at and live.updated_at != plan.expected_updated_at:
            drifts.append(
                {
                    "id": plan.product_id,
                    "field": "updated_at",
                    "expected": plan.expected_updated_at,
                    "observed": live.updated_at,
                }
            )
    ok = not drifts and not missing and not extra and len(live_rows) == len(plan_rows)
    return StaleGuardResult(
        ok=ok,
        expected_count=len(plan_rows),
        observed_count=len(live_rows),
        drifts=drifts,
        missing_ids=missing,
        extra_ids=extra,
    )


SELECT_CONTENT_SQL = """
SELECT p.id,
       p.sku,
       p.name,
       p.slug,
       p.brand_id,
       p.category_id,
       COALESCE(p.short_description, '') AS short_description,
       COALESCE(p.description, '') AS description,
       COALESCE(p.specifications::text, '') AS specifications,
       COALESCE(p.meta_title, '') AS meta_title,
       COALESCE(p.meta_description, '') AS meta_description,
       COALESCE(p.updated_at::text, '') AS updated_at,
       COALESCE(p.base_price::text, '') AS base_price,
       p.is_active,
       p.is_available,
       COALESCE(p.deleted_at::text, '') AS deleted_at
FROM products p
WHERE p.id = ANY(%s)
ORDER BY p.id
"""

SELECT_CONTENT_SQL_FOR_UPDATE = SELECT_CONTENT_SQL + "\nFOR UPDATE"

UPDATE_CONTENT_SQL = """
UPDATE products
SET name = %s,
    short_description = %s,
    description = %s,
    specifications = %s::jsonb,
    meta_title = %s,
    meta_description = %s,
    updated_at = NOW()
WHERE id = %s AND sku = %s AND deleted_at IS NULL
  AND name IS NOT DISTINCT FROM %s
  AND COALESCE(short_description, '') IS NOT DISTINCT FROM %s
  AND COALESCE(description, '') IS NOT DISTINCT FROM %s
  AND COALESCE(specifications::text, '') IS NOT DISTINCT FROM %s
  AND COALESCE(meta_title, '') IS NOT DISTINCT FROM %s
  AND COALESCE(meta_description, '') IS NOT DISTINCT FROM %s
"""


def rows_from_db(cursor: Any, product_ids: list[int], *, for_update: bool = False) -> list[LiveContentProduct]:
    sql = SELECT_CONTENT_SQL_FOR_UPDATE if for_update else SELECT_CONTENT_SQL
    cursor.execute(sql, (product_ids,))
    out: list[LiveContentProduct] = []
    for row in cursor.fetchall():
        out.append(
            LiveContentProduct(
                id=int(row[0]),
                sku=str(row[1]),
                name=str(row[2] or ""),
                slug=str(row[3] or ""),
                brand_id=int(row[4]) if row[4] is not None else None,
                category_id=int(row[5]) if row[5] is not None else None,
                short_description=str(row[6] or ""),
                description=str(row[7] or ""),
                specifications=str(row[8] or ""),
                meta_title=str(row[9] or ""),
                meta_description=str(row[10] or ""),
                updated_at=str(row[11] or ""),
                base_price=str(row[12] or ""),
                is_active=row[13],
                is_available=row[14],
                deleted_at=(str(row[15]) if row[15] else None),
            )
        )
    return out


def write_pre_apply_backup(
    live_rows: list[LiveContentProduct],
    *,
    output_dir: Path,
    stamp: str | None = None,
) -> tuple[Path, str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = stamp or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = output_dir / f"insize_official_rebuild_pre_apply_{stamp}.csv"
    rollback_path = output_dir / f"insize_official_rebuild_rollback_{stamp}.sql"
    fields = [
        "id",
        "sku",
        "name",
        "slug",
        "short_description",
        "description",
        "specifications",
        "meta_title",
        "meta_description",
        "updated_at",
    ]
    with backup_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in sorted(live_rows, key=lambda item: item.id):
            writer.writerow(
                {
                    "id": row.id,
                    "sku": row.sku,
                    "name": row.name,
                    "slug": row.slug,
                    "short_description": row.short_description,
                    "description": row.description,
                    "specifications": row.specifications,
                    "meta_title": row.meta_title,
                    "meta_description": row.meta_description,
                    "updated_at": row.updated_at,
                }
            )
    lines = [
        "-- Rollback for official INSIZE content/identity rebuild.",
        "-- Restores ONLY mutable content fields; never touches commerce/SKU/slug.",
        "BEGIN;",
    ]
    for row in sorted(live_rows, key=lambda item: item.id):
        def esc(value: str) -> str:
            return value.replace("'", "''")

        specs_sql = "NULL" if not row.specifications else f"'{esc(row.specifications)}'::jsonb"
        lines.append(
            "UPDATE products SET "
            f"name = '{esc(row.name)}', "
            f"short_description = '{esc(row.short_description)}', "
            f"description = '{esc(row.description)}', "
            f"specifications = {specs_sql}, "
            f"meta_title = '{esc(row.meta_title)}', "
            f"meta_description = '{esc(row.meta_description)}' "
            f"WHERE id = {row.id} AND sku = '{esc(row.sku)}';"
        )
    lines.append(f"-- expected_row_count={len(live_rows)}")
    lines.append("COMMIT;")
    rollback_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return backup_path, sha256_file(backup_path), rollback_path


def apply_plan(
    conn: DbConnection,
    plan_rows: list[PlanRow],
    *,
    dry_run: bool = True,
    backup_dir: Path | None = None,
) -> ApplyRunResult:
    if not plan_rows:
        raise ApplyAbort("empty_plan")
    for row in plan_rows:
        validate_proposed_content(row)

    product_ids = [row.product_id for row in plan_rows]
    cursor = conn.cursor()
    try:
        live = rows_from_db(cursor, product_ids, for_update=not dry_run)
        guard = stale_guard(plan_rows, live)
        dry_lines = [
            {
                "product_id": row.product_id,
                "sku": row.site_sku,
                "fields": list(MUTABLE_COLUMNS),
                "title_class": row.title_class,
            }
            for row in plan_rows
        ]
        if not guard.ok:
            conn.rollback()
            return ApplyRunResult(
                mode="dry_run" if dry_run else "apply_aborted",
                production_apply_executed=False,
                aborted=True,
                abort_reason="stale_snapshot_guard_failed",
                plan_rows=len(plan_rows),
                stale_guard=guard.as_dict(),
                dry_run_lines=dry_lines,
                transaction_safeguards={
                    "single_transaction": True,
                    "abort_before_first_write": True,
                    "partial_commit_allowed": False,
                    "mutable_columns": list(MUTABLE_COLUMNS),
                    "forbidden_columns": list(FORBIDDEN_MUTATION_COLUMNS),
                },
            )

        backup_path = ""
        backup_sha = ""
        rollback_path = ""
        if backup_dir is not None:
            bpath, bsha, rpath = write_pre_apply_backup(live, output_dir=backup_dir)
            backup_path = str(bpath)
            backup_sha = bsha
            rollback_path = str(rpath)

        if dry_run:
            conn.rollback()
            return ApplyRunResult(
                mode="dry_run",
                production_apply_executed=False,
                aborted=False,
                plan_rows=len(plan_rows),
                stale_guard=guard.as_dict(),
                backup_path=backup_path,
                backup_sha256=backup_sha,
                rollback_sql_path=rollback_path,
                dry_run_lines=dry_lines,
                transaction_safeguards={
                    "single_transaction": True,
                    "mutable_columns": list(MUTABLE_COLUMNS),
                    "forbidden_columns": list(FORBIDDEN_MUTATION_COLUMNS),
                    "partial_commit_allowed": False,
                },
            )

        live_by_id = {row.id: row for row in live}
        updated = 0
        for plan in plan_rows:
            live_row = live_by_id[plan.product_id]
            payload = plan_row_to_update_payload(plan)
            assert_payload_content_only(payload)
            # Prove immutable identity fields are unchanged in this writer path.
            if live_row.sku != plan.site_sku:
                raise ApplyAbort("sku_drift_before_write")
            cursor.execute(
                UPDATE_CONTENT_SQL,
                (
                    payload["name"],
                    payload["short_description"],
                    payload["description"],
                    json.dumps(payload["specifications"], ensure_ascii=False),
                    payload["meta_title"],
                    payload["meta_description"],
                    plan.product_id,
                    plan.site_sku,
                    live_row.name,
                    live_row.short_description,
                    live_row.description,
                    live_row.specifications,
                    live_row.meta_title,
                    live_row.meta_description,
                ),
            )
            if cursor.rowcount != 1:
                raise ApplyAbort(f"update_rowcount_mismatch:{plan.product_id}:{cursor.rowcount}")
            updated += 1

        # Post-apply verification: re-read and confirm content fields.
        after = {row.id: row for row in rows_from_db(cursor, product_ids, for_update=False)}
        for plan in plan_rows:
            got = after[plan.product_id]
            if got.sku != plan.site_sku:
                raise ApplyAbort(f"post_apply_sku_changed:{plan.product_id}")
            if got.slug != live_by_id[plan.product_id].slug:
                raise ApplyAbort(f"post_apply_slug_changed:{plan.product_id}")
            if got.name != plan.proposed_name:
                raise ApplyAbort(f"post_apply_name_mismatch:{plan.product_id}")
            if got.short_description != plan.proposed_short_description:
                raise ApplyAbort(f"post_apply_short_mismatch:{plan.product_id}")

        conn.commit()
        return ApplyRunResult(
            mode="apply",
            production_apply_executed=True,
            aborted=False,
            plan_rows=len(plan_rows),
            stale_guard=guard.as_dict(),
            backup_path=backup_path,
            backup_sha256=backup_sha,
            rollback_sql_path=rollback_path,
            updated_count=updated,
            dry_run_lines=dry_lines,
            transaction_safeguards={
                "single_transaction": True,
                "for_update_lock": True,
                "post_write_verification": True,
                "mutable_columns": list(MUTABLE_COLUMNS),
                "forbidden_columns": list(FORBIDDEN_MUTATION_COLUMNS),
                "partial_commit_allowed": False,
            },
        )
    except Exception:
        conn.rollback()
        raise


def duplicate_groups(values: list[str]) -> int:
    counter = Counter(v for v in values if v)
    return sum(1 for _value, count in counter.items() if count > 1)


def writer_contract_summary() -> dict[str, Any]:
    return {
        "mutable_columns": list(MUTABLE_COLUMNS),
        "forbidden_payload_fields": list(FORBIDDEN_PAYLOAD_FIELDS),
        "forbidden_mutation_columns": list(FORBIDDEN_MUTATION_COLUMNS),
        "default_mode": "DRY_RUN",
        "shopmill_dependency": False,
        "uses_shopmill_authority": False,
        "whole_field_specs_replace": True,
        "production_gates": [
            "--apply",
            "--confirm-production-write",
            "--confirm-plan-sha256",
            f"{ALLOW_ENV}=1",
            f"{CATEGORY_ENV}=B",
        ],
        "allow_env": ALLOW_ENV,
        "category_env": CATEGORY_ENV,
        "prod_host_marker": PROD_HOST_MARKER,
    }


def build_plan_from_evidence(
    *,
    evidence_dir: Path,
    snapshot_csv: Path,
    allowlist_csv: Path,
    priority_csv: Path | None = None,
) -> dict[str, Any]:
    """Construct immutable plan candidates from reconstruction evidence."""
    allowlist_ids = load_allowlist_ids(allowlist_csv)
    snap = {r["sku"]: r for r in csv.DictReader(snapshot_csv.open(encoding="utf-8-sig"))}
    content = list(csv.DictReader((evidence_dir / "wave1_new_content_dry_run.csv").open(encoding="utf-8-sig")))
    mapping = {
        r["site_sku"]: r
        for r in csv.DictReader((evidence_dir / "wave1_official_mapping.csv").open(encoding="utf-8-sig"))
    }
    identity = {
        r["site_sku"]: r
        for r in csv.DictReader((evidence_dir / "wave1_identity_review.csv").open(encoding="utf-8-sig"))
    }
    priority: dict[str, str] = {}
    if priority_csv and priority_csv.exists():
        for row in csv.DictReader(priority_csv.open(encoding="utf-8-sig")):
            priority[row["sku"]] = row.get("priority_class") or ""

    excluded_partial: list[dict[str, Any]] = []
    excluded_ambiguous: list[dict[str, Any]] = []
    excluded_material: list[dict[str, Any]] = []
    excluded_manual_title: list[dict[str, Any]] = []
    title_review: list[dict[str, Any]] = []
    plan_rows: list[dict[str, Any]] = []

    ready_input = 0
    for row in content:
        sku = row["site_sku"]
        pid = int(row["product_id"])
        completeness = row["completeness"]
        match_class = row["match_class"]
        live = snap[sku]
        mapped = mapping[sku]

        if completeness == "OFFICIAL_PARTIAL":
            excluded_partial.append({"product_id": pid, "sku": sku, "reason": "OFFICIAL_PARTIAL"})
            continue
        if completeness == "MANUAL_OFFICIAL_REVIEW" or match_class == "AMBIGUOUS":
            excluded_ambiguous.append(
                {"product_id": pid, "sku": sku, "reason": completeness or match_class, "match_class": match_class}
            )
            continue
        if completeness != ALLOWED_COMPLETENESS:
            continue
        ready_input += 1
        if pid not in allowlist_ids:
            raise ApplyAbort(f"ready_product_outside_allowlist:{pid}")
        if match_class not in ALLOWED_MATCH_CLASSES:
            excluded_ambiguous.append({"product_id": pid, "sku": sku, "reason": match_class})
            continue
        if not mapped.get("source_id"):
            raise ApplyAbort(f"missing_official_source:{sku}")

        official_model = mapped.get("official_model") or sku
        if norm_code(sku) != norm_code(official_model):
            raise ApplyAbort(f"ready_sku_model_mismatch:{sku}:{official_model}")

        proposed_name, title_class = build_proposed_title(
            site_sku=sku,
            official_model=official_model,
            official_product_name=mapped.get("official_product_name") or "",
            current_name=live["name"],
        )
        title_review.append(
            {
                "product_id": pid,
                "sku": sku,
                "current_name": live["name"],
                "proposed_name": proposed_name,
                "official_model": official_model,
                "source": mapped.get("source_id") or "",
                "page": mapped.get("source_page") or "",
                "reason": identity.get(sku, {}).get("identity_class") or "",
                "title_class": title_class,
            }
        )
        if title_class == "MATERIAL_IDENTITY_CHANGE":
            excluded_material.append(title_review[-1])
            continue
        if title_class == "MANUAL_TITLE_REVIEW":
            excluded_manual_title.append(title_review[-1])
            continue

        specs_obj = customer_facing_specifications(row.get("specifications_json") or "{}")
        proposed_specs = json.dumps(specs_obj, ensure_ascii=False, sort_keys=True)
        short = row.get("short_description") or ""
        desc = row.get("description") or ""
        meta_t = row.get("meta_title") or ""
        meta_d = row.get("meta_description") or ""
        # Ensure title model order appears in SEO too.
        if sku not in meta_t:
            meta_t = f"{proposed_name}"[:60]
        if sku not in meta_d:
            meta_d = f"{proposed_name}"[:155]

        for field_name, text in [
            ("short", short),
            ("desc", desc),
            ("meta_t", meta_t),
            ("meta_d", meta_d),
            ("name", proposed_name),
            ("specs", proposed_specs),
        ]:
            assert_no_shopmill(text, context=f"{sku}:{field_name}")

        plan_rows.append(
            {
                "product_id": pid,
                "site_sku": sku,
                "current_name": live["name"],
                "proposed_name": proposed_name,
                "current_short_description": live.get("short_description") or "",
                "current_short_description_hash": content_hash(live.get("short_description")),
                "proposed_short_description": short,
                "current_description": live.get("description") or "",
                "current_description_hash": content_hash(live.get("description")),
                "proposed_description": desc,
                "current_specifications": live.get("specifications") or "",
                "current_specifications_hash": content_hash(live.get("specifications")),
                "proposed_specifications": proposed_specs,
                "current_meta_title": live.get("meta_title") or "",
                "proposed_meta_title": meta_t,
                "current_meta_description": live.get("meta_description") or "",
                "current_meta_description_hash": content_hash(live.get("meta_description")),
                "proposed_meta_description": meta_d,
                "official_model": official_model,
                "official_product_name": mapped.get("official_product_name") or "",
                "official_source_id": mapped.get("source_id") or "",
                "official_source_page": mapped.get("source_page") or "",
                "official_fact_count": int(row.get("official_fact_count") or 0),
                "mapping_class": match_class,
                "title_class": title_class,
                "completeness": completeness,
                "priority_class": priority.get(sku, ""),
                "expected_updated_at": live.get("updated_at") or "",
            }
        )

    # Validate each assembled row through the same gates as APPLY.
    validated = [PlanRow(**{k: r[k] for k in PlanRow.__dataclass_fields__ if k in r}) for r in plan_rows]
    for row in validated:
        validate_proposed_content(row)

    title_changes = sum(1 for r in plan_rows if r["current_name"] != r["proposed_name"])
    title_unchanged = len(plan_rows) - title_changes
    dup_short = duplicate_groups([r["proposed_short_description"] for r in plan_rows])
    dup_desc = duplicate_groups([r["proposed_description"] for r in plan_rows])
    dup_meta_t = duplicate_groups([r["proposed_meta_title"] for r in plan_rows])
    dup_meta_d = duplicate_groups([r["proposed_meta_description"] for r in plan_rows])

    blockers = [r for r in plan_rows if r.get("priority_class") == "BLOCKS_CONVERSION"]
    # Staged first cohort: blockers first, then fill to 40 (or all if <40).
    recommended_n = len(plan_rows) if len(plan_rows) <= 40 else 40
    if len(blockers) >= 20 and len(plan_rows) > 50:
        recommended_n = 40
    if len(plan_rows) <= 30:
        recommended_n = len(plan_rows)

    def sort_key(item: dict[str, Any]) -> tuple:
        is_blocker = 0 if item.get("priority_class") == "BLOCKS_CONVERSION" else 1
        return (is_blocker, -int(item.get("official_fact_count") or 0), item["site_sku"])

    recommended = sorted(plan_rows, key=sort_key)[:recommended_n]

    return {
        "ready_input": ready_input,
        "plan_rows": plan_rows,
        "recommended_first_apply": recommended,
        "excluded_partial": excluded_partial,
        "excluded_ambiguous": excluded_ambiguous,
        "excluded_material": excluded_material,
        "excluded_manual_title": excluded_manual_title,
        "title_review": title_review,
        "stats": {
            "PLAN_ROWS": len(plan_rows),
            "TITLE_CHANGES": title_changes,
            "TITLE_UNCHANGED": title_unchanged,
            "TITLE_MANUAL_REVIEW_EXCLUDED": len(excluded_manual_title),
            "MATERIAL_IDENTITY_CHANGE": len(excluded_material),
            "SAFE_IDENTITY_CORRECTION": sum(
                1 for r in plan_rows if r["title_class"] == "SAFE_IDENTITY_CORRECTION"
            ),
            "DUPLICATE_SHORT_DESCRIPTION_GROUPS": dup_short,
            "DUPLICATE_DESCRIPTION_GROUPS": dup_desc,
            "DUPLICATE_META_TITLE_GROUPS": dup_meta_t,
            "DUPLICATE_META_DESCRIPTION_GROUPS": dup_meta_d,
            "RECOMMENDED_FIRST_APPLY_COUNT": recommended_n,
            "OFFICIAL_PARTIAL": len(excluded_partial),
            "AMBIGUOUS": len(excluded_ambiguous),
        },
        "writer_contract": writer_contract_summary(),
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = fieldnames or list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


__all__ = [
    "ALLOWED_COMPLETENESS",
    "ALLOWED_MATCH_CLASSES",
    "ApplyAbort",
    "ApplyRunResult",
    "FORBIDDEN_PAYLOAD_FIELDS",
    "LiveContentProduct",
    "MUTABLE_COLUMNS",
    "PlanRow",
    "WAVE1_ALLOWLIST_COUNT",
    "apply_plan",
    "assert_payload_content_only",
    "assert_production_apply_authorized",
    "build_plan_from_evidence",
    "build_proposed_title",
    "connect_runtime_db",
    "content_hash",
    "customer_facing_specifications",
    "load_allowlist_ids",
    "load_and_validate_plan",
    "normalize_database_url",
    "plan_row_to_update_payload",
    "sha256_file",
    "stale_guard",
    "validate_proposed_content",
    "write_csv",
    "write_pre_apply_backup",
    "writer_contract_summary",
]
