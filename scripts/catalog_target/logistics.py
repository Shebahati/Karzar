"""Offline logistics package validation — no DB / API / Postex calls.

Authority: docs/catalog/LOGISTICS_AUTHORITY.md
Storage alignment: PR #311 product fields (*_cm, shipping_is_*, weight_grams).
"""

from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping

ValidationStatus = Literal["READY", "INCOMPLETE", "INVALID", "UNKNOWN", "BLOCKED"]
SourceClass = Literal[
    "OFFICIAL_MANUFACTURER",
    "DISTRIBUTOR",
    "MANUAL_MEASUREMENT",
    "CONTROLLED_ESTIMATION",
]

ALLOWED_SOURCES: frozenset[str] = frozenset(
    {
        "OFFICIAL_MANUFACTURER",
        "DISTRIBUTOR",
        "MANUAL_MEASUREMENT",
        "CONTROLLED_ESTIMATION",
    }
)
SHIPPING_CLASSES: frozenset[str] = frozenset({"parcel", "freight_only"})

# Reasonable ranges for industrial parcel tooling (not Postex API limits).
WEIGHT_MIN_G = Decimal("1")
WEIGHT_MAX_G = Decimal("50000")  # 50 kg soft ceiling for parcel path review
DIM_MIN_CM = Decimal("0.1")
DIM_MAX_CM = Decimal("200")

BOOL_TRUE = frozenset({"1", "true", "t", "yes", "y", "بله"})
BOOL_FALSE = frozenset({"0", "false", "f", "no", "n", "خیر"})


@dataclass
class LogisticsRow:
    sku: str
    product_id: str | None = None
    shipping_class: str | None = None
    weight_grams: Decimal | None = None
    package_length_cm: Decimal | None = None
    package_width_cm: Decimal | None = None
    package_height_cm: Decimal | None = None
    shipping_is_fragile: bool | None = None
    shipping_is_liquid: bool | None = None
    source: str | None = None
    source_date: str | None = None
    raw: dict[str, str] = field(default_factory=dict)


@dataclass
class LogisticsValidation:
    sku: str
    product_id: str | None
    status: ValidationStatus
    reasons: list[str]
    shipping_class: str | None
    weight_grams: str | None
    package_length_cm: str | None
    package_width_cm: str | None
    package_height_cm: str | None
    shipping_is_fragile: bool | None
    shipping_is_liquid: bool | None
    source: str | None
    source_date: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _blank(value: object | None) -> bool:
    if value is None:
        return True
    return str(value).strip() == ""


def _parse_decimal(raw: object | None) -> Decimal | None:
    if _blank(raw):
        return None
    text = str(raw).strip().replace(",", "")
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        raise ValueError(f"non_numeric:{text}")


def _parse_bool(raw: object | None) -> bool | None:
    if _blank(raw):
        return None
    key = str(raw).strip().lower()
    if key in BOOL_TRUE:
        return True
    if key in BOOL_FALSE:
        return False
    raise ValueError(f"non_boolean:{raw}")


def _norm_header(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


HEADER_ALIASES: dict[str, str] = {
    "sku": "sku",
    "product_id": "product_id",
    "id": "product_id",
    "shipping_class": "shipping_class",
    "weight_grams": "weight_grams",
    "weight": "weight_grams",
    "package_length_cm": "package_length_cm",
    "package_width_cm": "package_width_cm",
    "package_height_cm": "package_height_cm",
    "length_cm": "package_length_cm",
    "width_cm": "package_width_cm",
    "height_cm": "package_height_cm",
    "length_mm": "length_mm",
    "width_mm": "width_mm",
    "height_mm": "height_mm",
    "package_length_mm": "length_mm",
    "package_width_mm": "width_mm",
    "package_height_mm": "height_mm",
    "shipping_is_fragile": "shipping_is_fragile",
    "shipping_is_liquid": "shipping_is_liquid",
    "fragile": "shipping_is_fragile",
    "liquid": "shipping_is_liquid",
    "source": "source",
    "source_date": "source_date",
}


def mm_to_cm(mm: Decimal) -> Decimal:
    """Convert millimetres to centimetres; ceil to whole cm for package_builder parity."""
    if mm <= 0:
        return mm
    return Decimal(str(math.ceil(float(mm / Decimal("10")))))


def normalize_intake_mapping(row: Mapping[str, object]) -> dict[str, object]:
    out: dict[str, object] = {}
    for key, value in row.items():
        canon = HEADER_ALIASES.get(_norm_header(str(key)))
        if canon:
            out[canon] = value
    return out


def row_from_mapping(raw: Mapping[str, object]) -> LogisticsRow:
    m = normalize_intake_mapping(raw)
    length = _parse_decimal(m.get("package_length_cm"))
    width = _parse_decimal(m.get("package_width_cm"))
    height = _parse_decimal(m.get("package_height_cm"))
    if length is None and not _blank(m.get("length_mm")):
        length = mm_to_cm(_parse_decimal(m.get("length_mm")) or Decimal("0"))
    if width is None and not _blank(m.get("width_mm")):
        width = mm_to_cm(_parse_decimal(m.get("width_mm")) or Decimal("0"))
    if height is None and not _blank(m.get("height_mm")):
        height = mm_to_cm(_parse_decimal(m.get("height_mm")) or Decimal("0"))

    sku = str(m.get("sku") or "").strip()
    pid = m.get("product_id")
    shipping_class = m.get("shipping_class")
    source = m.get("source")
    return LogisticsRow(
        sku=sku,
        product_id=None if _blank(pid) else str(pid).strip(),
        shipping_class=None if _blank(shipping_class) else str(shipping_class).strip().lower(),
        weight_grams=_parse_decimal(m.get("weight_grams")),
        package_length_cm=length,
        package_width_cm=width,
        package_height_cm=height,
        shipping_is_fragile=_parse_bool(m.get("shipping_is_fragile")),
        shipping_is_liquid=_parse_bool(m.get("shipping_is_liquid")),
        source=None if _blank(source) else str(source).strip().upper(),
        source_date=None if _blank(m.get("source_date")) else str(m.get("source_date")).strip(),
        raw={str(k): "" if v is None else str(v) for k, v in raw.items()},
    )


def validate_logistics_row(row: LogisticsRow) -> LogisticsValidation:
    reasons: list[str] = []
    parse_invalid = False

    if not row.sku:
        reasons.append("missing_sku")
        parse_invalid = True

    sc = row.shipping_class
    if sc is None:
        reasons.append("missing_shipping_class")
    elif sc not in SHIPPING_CLASSES:
        reasons.append("invalid_shipping_class")
        parse_invalid = True

    # Weight
    w = row.weight_grams
    if w is None:
        reasons.append("missing_weight")
    else:
        if w != w.to_integral_value():
            # Allow .00 but flag non-integer grams as invalid for READY
            if w % 1 != 0:
                reasons.append("weight_not_integer_grams")
                parse_invalid = True
        if w <= 0:
            reasons.append("invalid_weight_non_positive")
            parse_invalid = True
        elif w < WEIGHT_MIN_G or w > WEIGHT_MAX_G:
            reasons.append("weight_out_of_reasonable_range")
            parse_invalid = True

    for label, value in (
        ("length", row.package_length_cm),
        ("width", row.package_width_cm),
        ("height", row.package_height_cm),
    ):
        if value is None:
            reasons.append(f"missing_{label}")
        elif value <= 0:
            reasons.append(f"invalid_{label}_non_positive")
            parse_invalid = True
        elif value < DIM_MIN_CM or value > DIM_MAX_CM:
            reasons.append(f"{label}_out_of_reasonable_range")
            parse_invalid = True

    if row.shipping_is_fragile is None:
        reasons.append("missing_fragile")
    if row.shipping_is_liquid is None:
        reasons.append("missing_liquid")

    if row.source is None:
        reasons.append("missing_source")
    elif row.source not in ALLOWED_SOURCES:
        reasons.append("invalid_source")
        parse_invalid = True
    elif row.source == "CONTROLLED_ESTIMATION":
        reasons.append("controlled_estimation_requires_owner_approval")
        # Still READY-eligible structurally; APPLY gate must check approval separately.
        # Do not mark INVALID solely for estimation class.

    if row.source_date is None:
        reasons.append("missing_source_date")

    def _fmt(v: Decimal | None) -> str | None:
        return None if v is None else format(v, "f")

    base = LogisticsValidation(
        sku=row.sku,
        product_id=row.product_id,
        status="UNKNOWN",
        reasons=reasons,
        shipping_class=sc,
        weight_grams=_fmt(w),
        package_length_cm=_fmt(row.package_length_cm),
        package_width_cm=_fmt(row.package_width_cm),
        package_height_cm=_fmt(row.package_height_cm),
        shipping_is_fragile=row.shipping_is_fragile,
        shipping_is_liquid=row.shipping_is_liquid,
        source=row.source,
        source_date=row.source_date,
    )

    if sc == "freight_only" and not parse_invalid:
        # Freight is an intentional non-Postex path when class is valid.
        freight_ok_reasons = {
            "missing_weight",
            "missing_length",
            "missing_width",
            "missing_height",
            "missing_fragile",
            "missing_liquid",
            "missing_source",
            "missing_source_date",
            "controlled_estimation_requires_owner_approval",
        }
        if all(r in freight_ok_reasons or r.startswith("missing_") for r in reasons) or not reasons:
            base.status = "BLOCKED"
            base.reasons = ["freight_only"] + [r for r in reasons if r != "missing_shipping_class"]
            return base

    if parse_invalid or any(
        r.startswith("invalid_") or r.endswith("_out_of_reasonable_range") or r == "weight_not_integer_grams"
        for r in reasons
    ):
        base.status = "INVALID"
        return base

    required_ready = {
        "missing_shipping_class",
        "missing_weight",
        "missing_length",
        "missing_width",
        "missing_height",
        "missing_fragile",
        "missing_liquid",
        "missing_source",
        "missing_source_date",
    }
    missing = [r for r in reasons if r in required_ready]
    if sc == "parcel" and not missing and not parse_invalid:
        # Strip advisory estimation note from blocking
        advisory = [r for r in reasons if r == "controlled_estimation_requires_owner_approval"]
        base.reasons = advisory
        base.status = "READY"
        return base

    if not reasons:
        base.status = "UNKNOWN"
        return base

    if all(r.startswith("missing_") or r == "controlled_estimation_requires_owner_approval" for r in reasons):
        if all(r.startswith("missing_") for r in reasons if r != "controlled_estimation_requires_owner_approval"):
            # All missing → UNKNOWN; partial missing → INCOMPLETE
            present_any = any(
                [
                    w is not None,
                    row.package_length_cm is not None,
                    row.package_width_cm is not None,
                    row.package_height_cm is not None,
                    row.shipping_is_fragile is not None,
                    row.shipping_is_liquid is not None,
                    row.source is not None,
                ]
            )
            base.status = "INCOMPLETE" if present_any else "UNKNOWN"
            return base
        base.status = "INCOMPLETE"
        return base

    base.status = "INCOMPLETE"
    return base


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def validate_file_rows(rows: Iterable[Mapping[str, object]]) -> list[LogisticsValidation]:
    results: list[LogisticsValidation] = []
    for raw in rows:
        try:
            row = row_from_mapping(raw)
        except ValueError as exc:
            sku = str(normalize_intake_mapping(raw).get("sku") or "")
            results.append(
                LogisticsValidation(
                    sku=sku,
                    product_id=None,
                    status="INVALID",
                    reasons=[str(exc)],
                    shipping_class=None,
                    weight_grams=None,
                    package_length_cm=None,
                    package_width_cm=None,
                    package_height_cm=None,
                    shipping_is_fragile=None,
                    shipping_is_liquid=None,
                    source=None,
                    source_date=None,
                )
            )
            continue
        results.append(validate_logistics_row(row))
    return results


def summarize(results: list[LogisticsValidation]) -> dict[str, Any]:
    counts: dict[str, int] = {
        "READY": 0,
        "INCOMPLETE": 0,
        "INVALID": 0,
        "UNKNOWN": 0,
        "BLOCKED": 0,
    }
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    return {
        "row_count": len(results),
        "status_counts": counts,
        "ready_percent": round(100.0 * counts["READY"] / len(results), 2) if results else 0.0,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_authority_csv(path: Path, results: list[LogisticsValidation]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "product_id",
        "sku",
        "shipping_class",
        "weight_grams",
        "package_length_cm",
        "package_width_cm",
        "package_height_cm",
        "shipping_is_fragile",
        "shipping_is_liquid",
        "source",
        "source_date",
        "validation_status",
        "reasons",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for r in results:
            writer.writerow(
                {
                    "product_id": r.product_id or "",
                    "sku": r.sku,
                    "shipping_class": r.shipping_class or "",
                    "weight_grams": r.weight_grams or "",
                    "package_length_cm": r.package_length_cm or "",
                    "package_width_cm": r.package_width_cm or "",
                    "package_height_cm": r.package_height_cm or "",
                    "shipping_is_fragile": "" if r.shipping_is_fragile is None else str(r.shipping_is_fragile),
                    "shipping_is_liquid": "" if r.shipping_is_liquid is None else str(r.shipping_is_liquid),
                    "source": r.source or "",
                    "source_date": r.source_date or "",
                    "validation_status": r.status,
                    "reasons": "|".join(r.reasons),
                }
            )
