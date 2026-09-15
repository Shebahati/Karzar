"""Price and availability authority proposals (no registry changes)."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

from zcc_ir_catalog.models import SourceProduct


@dataclass
class CommerceRow:
    source_url: str
    observed_price: str | None
    price_status: str | None
    observed_availability: str | None
    currency: str | None
    flags: list[str]

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["flags"] = list(self.flags)
        return data


def analyze_prices(products: list[SourceProduct]) -> tuple[list[CommerceRow], dict[str, Any]]:
    rows: list[CommerceRow] = []
    zero = invalid = ok = 0
    currencies = Counter()
    for product in products:
        flags: list[str] = []
        if product.price_status != "ok":
            invalid += 1
            flags.append("price_not_ok")
        elif product.price_normalized in {None, "", "0"}:
            zero += 1
            flags.append("zero_or_missing_price")
        else:
            ok += 1
        if product.price_currency:
            currencies[product.price_currency] += 1
        rows.append(
            CommerceRow(
                source_url=product.source_url,
                observed_price=product.price_normalized,
                price_status=product.price_status,
                observed_availability=product.availability_normalized,
                currency=product.price_currency,
                flags=flags,
            )
        )
    rows.sort(key=lambda r: r.source_url)
    proposal = {
        "document": "ZCC_IR_PRICE_AUTHORITY_PROPOSAL",
        "recommendation_status": "INSUFFICIENT_EVIDENCE",
        "rationale": (
            "zcc.ir prices are WooCommerce IRR observations only. "
            "39 zero/invalid prices and mixed retail semantics require owner rules before any price writes."
        ),
        "currency": dict(currencies),
        "counts": {"price_ok": ok, "price_invalid": invalid, "zero_or_missing": zero},
        "rules_required": [
            "Never import price=0 as a Karzar selling price",
            "SOURCE_VALUE_OBSERVED;AUTHORITY_NOT_YET_APPROVED remains until owner approves",
        ],
        "authority_boundary": "CONTENT_ONLY_SOURCE until DECISION 4",
    }
    if ok > 0 and zero > 0:
        proposal["recommendation_status"] = "APPROVE_WITH_RULES"
    return rows, proposal


def analyze_availability(products: list[SourceProduct]) -> tuple[list[CommerceRow], dict[str, Any]]:
    rows: list[CommerceRow] = []
    avail = Counter(product.availability_normalized or "unknown" for product in products)
    proposal = {
        "document": "ZCC_IR_AVAILABILITY_AUTHORITY_PROPOSAL",
        "recommendation_status": "INSUFFICIENT_EVIDENCE",
        "observed_semantics": dict(avail),
        "stock_quantity_visible": False,
        "binary_availability_only": True,
        "rationale": (
            "Source communicates coarse in-stock/out-of-stock style signals only. "
            "Product page existence must not imply warehouse stock."
        ),
        "authority_boundary": "No availability writes in Phase 2",
    }
    for product in products:
        rows.append(
            CommerceRow(
                source_url=product.source_url,
                observed_price=product.price_normalized,
                price_status=product.price_status,
                observed_availability=product.availability_normalized,
                currency=product.price_currency,
                flags=[],
            )
        )
    rows.sort(key=lambda r: r.source_url)
    if avail.get("available") or avail.get("unavailable"):
        proposal["recommendation_status"] = "APPROVE_WITH_RULES"
    return rows, proposal
