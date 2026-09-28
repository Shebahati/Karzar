"""Read-only classification of Hesabfa item activation for site products.

Dry-run never calls Hesabfa ``item/save`` and never writes the database.
Future APPLY is refused: repository evidence does not prove whether
``item/save`` merges or replaces prices and stock.

Identity is site ``Product.sku`` ↔ Hesabfa ``ProductCode``. Duplicate or
conflicting matches are ``AMBIGUOUS`` and are not repaired here.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import TextClause

from app.services.hesabfa.item_lifecycle import hesabfa_item_should_be_active
from app.services.hesabfa.mapping import _normalize_sku

# item/save posts the supplied object (app/services/hesabfa/client.py). The
# repository never states whether omitted fields are preserved. Shell payloads
# send sellPrice/buyPrice 0 and omit quantity, and the client docstring only
# says create defaults stock to 0. That is not proof an update keeps existing
# prices or warehouse quantities, so activation APPLY must not be implemented.
ITEM_SAVE_CONTRACT = "UNKNOWN"
ACTIVATION_APPLY_STATUS = "BLOCKED_PENDING_API_CONFIRMATION"
ITEM_SAVE_CONTRACT_EVIDENCE = (
    "Official Hesabfa item/save docs (https://www.hesabfa.com/help/api/item) "
    "say an existing code edits the item, name and itemType are required, and "
    "buyPrice/sellPrice are optional. Stock is not an item/save field. The "
    "page does not say whether an update replaces omitted fields or whether "
    "explicit buyPrice=0 and sellPrice=0 overwrite existing prices. "
    "Repository inference is not a proven contract. "
    "Activation APPLY stays BLOCKED_PENDING_API_CONFIRMATION."
)

ACTIONS = (
    "NOOP_ALREADY_ACTIVE",
    "ACTIVATE_EXISTING",
    "CREATE_MISSING_ACTIVE",
    "LINK_EXISTING",
    "ERROR",
    "AMBIGUOUS",
)

STALE_MAPPING_REASONS = frozenset(
    {
        "mapping_code_mismatch",
        "mapping_product_code_mismatch",
        "mapping_sku_mismatch",
        "mapping_remote_missing",
    }
)

CSV_COLUMNS = (
    "site_product_id",
    "sku",
    "site_is_active",
    "site_is_available",
    "site_price_present",
    "hesabfa_mapping_present",
    "hesabfa_item_present",
    "hesabfa_code",
    "hesabfa_product_code",
    "hesabfa_active_current",
    "desired_hesabfa_active",
    "action",
    "reason",
)

ARTIFACT_NAMES = (
    "summary.json",
    "reconciliation.csv",
    "errors.csv",
    "ambiguous.csv",
)


class ActivationApplyBlocked(RuntimeError):
    """Raised when activation APPLY is requested. No Hesabfa write is attempted."""

    code = ACTIVATION_APPLY_STATUS


def refuse_activation_apply() -> None:
    """Fail closed before any Hesabfa or database write.

    The future apply path, once the item/save contract is proven, must be
    idempotent and lookup-first: preserve remote prices, stock, warehouses,
    invoices, contacts, and categories; never create a second item for an
    existing ProductCode; never mutate the site product. Until then this
    function is the only apply entry point.
    """
    raise ActivationApplyBlocked(ITEM_SAVE_CONTRACT_EVIDENCE)


class ReadOnlyStatementRejected(RuntimeError):
    """Dry-run SQL guard rejected a non-SELECT statement."""


class SupportsExecute(Protocol):
    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any: ...


@dataclass
class DryRunSession:
    """Session wrapper that allows SELECT only and counts rejected writes."""

    inner: SupportsExecute
    database_writes: int = 0

    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
        self._assert_select(statement)
        return await self.inner.execute(statement, *args, **kwargs)

    async def commit(self) -> None:
        self.database_writes += 1
        raise ReadOnlyStatementRejected("dry-run forbids database commit")

    async def flush(self) -> None:
        self.database_writes += 1
        raise ReadOnlyStatementRejected("dry-run forbids database flush")

    def add(self, _obj: object) -> None:
        self.database_writes += 1
        raise ReadOnlyStatementRejected("dry-run forbids database add")

    def _assert_select(self, statement: Any) -> None:
        if isinstance(statement, Select):
            return
        if isinstance(statement, TextClause):
            sql = " ".join(str(statement).strip().lower().split())
            if sql.startswith("select"):
                return
            # Session controls that enforce read-only. They are not data writes.
            if sql in {
                "set transaction read only",
                "show transaction_read_only",
                "pragma query_only = on",
                "pragma query_only = off",
                "pragma query_only",
            }:
                return
        self.database_writes += 1
        raise ReadOnlyStatementRejected("dry-run forbids non-SELECT SQL")


@dataclass
class DryRunHesabfaClient:
    """Read-only Hesabfa facade. Write methods increment a counter and raise."""

    inner: Any
    remote_writes: int = 0

    async def get_items(self, **kwargs: Any) -> Any:
        return await self.inner.get_items(**kwargs)

    async def save_item(self, *_args: Any, **_kwargs: Any) -> Any:
        self.remote_writes += 1
        raise RuntimeError("dry-run forbids item/save")

    async def save_contact(self, *_args: Any, **_kwargs: Any) -> Any:
        self.remote_writes += 1
        raise RuntimeError("dry-run forbids contact/save")

    async def save_invoice(self, *_args: Any, **_kwargs: Any) -> Any:
        self.remote_writes += 1
        raise RuntimeError("dry-run forbids invoice/save")


@dataclass(frozen=True)
class SiteProductView:
    id: int
    sku: str
    is_active: bool
    is_available: bool
    price_present: bool


@dataclass(frozen=True)
class MappingView:
    product_id: int
    sku: str
    hesabfa_code: str
    hesabfa_product_code: str | None


@dataclass(frozen=True)
class ReconciliationRow:
    site_product_id: int
    sku: str
    site_is_active: bool
    site_is_available: bool
    site_price_present: bool
    hesabfa_mapping_present: bool
    hesabfa_item_present: bool
    hesabfa_code: str
    hesabfa_product_code: str
    hesabfa_active_current: bool | None
    desired_hesabfa_active: bool
    action: str
    reason: str

    def as_csv(self) -> dict[str, str]:
        active = ""
        if self.hesabfa_active_current is True:
            active = "true"
        elif self.hesabfa_active_current is False:
            active = "false"
        return {
            "site_product_id": str(self.site_product_id),
            "sku": self.sku,
            "site_is_active": _bool_text(self.site_is_active),
            "site_is_available": _bool_text(self.site_is_available),
            "site_price_present": _bool_text(self.site_price_present),
            "hesabfa_mapping_present": _bool_text(self.hesabfa_mapping_present),
            "hesabfa_item_present": _bool_text(self.hesabfa_item_present),
            "hesabfa_code": self.hesabfa_code,
            "hesabfa_product_code": self.hesabfa_product_code,
            "hesabfa_active_current": active,
            "desired_hesabfa_active": _bool_text(self.desired_hesabfa_active),
            "action": self.action,
            "reason": self.reason,
        }


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def parse_remote_active(item: Mapping[str, Any]) -> bool | None:
    """Read Hesabfa Active/active without guessing when the field is absent."""
    for key in ("Active", "active"):
        if key not in item or item[key] is None:
            continue
        value = item[key]
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and value in (0, 1):
            return bool(value)
        if isinstance(value, str):
            token = value.strip().lower()
            if token in {"true", "1"}:
                return True
            if token in {"false", "0"}:
                return False
    return None


def _remote_code(item: Mapping[str, Any]) -> str:
    return str(item.get("Code") or item.get("code") or "").strip()


def _remote_product_code(item: Mapping[str, Any]) -> str:
    return str(item.get("ProductCode") or item.get("productCode") or "").strip()


def index_remote_by_product_code(
    items: Iterable[Mapping[str, Any]],
) -> dict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for item in items:
        key = _normalize_sku(_remote_product_code(item))
        if key:
            grouped[key].append(item)
    return grouped


def _row(
    product: SiteProductView,
    *,
    mapping_present: bool,
    item_present: bool,
    hesabfa_code: str,
    hesabfa_product_code: str,
    active_current: bool | None,
    action: str,
    reason: str,
) -> ReconciliationRow:
    if action not in ACTIONS:
        raise ValueError(f"unknown reconciliation action {action}")
    return ReconciliationRow(
        site_product_id=product.id,
        sku=product.sku,
        site_is_active=bool(product.is_active),
        site_is_available=bool(product.is_available),
        site_price_present=bool(product.price_present),
        hesabfa_mapping_present=mapping_present,
        hesabfa_item_present=item_present,
        hesabfa_code=hesabfa_code,
        hesabfa_product_code=hesabfa_product_code,
        hesabfa_active_current=active_current,
        desired_hesabfa_active=hesabfa_item_should_be_active(product),
        action=action,
        reason=reason,
    )


def classify_product(
    product: SiteProductView,
    mappings: Sequence[MappingView],
    remote_matches: Sequence[Mapping[str, Any]],
    *,
    duplicate_site_sku: bool = False,
    foreign_code_owners: Sequence[int] = (),
) -> ReconciliationRow:
    """Classify one non-deleted site product. Does not write anywhere."""
    sku_norm = _normalize_sku(product.sku)
    product_mappings = [row for row in mappings if row.product_id == product.id]
    mapping = product_mappings[0] if len(product_mappings) == 1 else None
    item_present = len(remote_matches) >= 1

    def finish(
        action: str,
        reason: str,
        *,
        code: str = "",
        product_code: str = "",
        active_current: bool | None = None,
        mapping_present: bool | None = None,
    ) -> ReconciliationRow:
        return _row(
            product,
            mapping_present=(
                bool(product_mappings) if mapping_present is None else mapping_present
            ),
            item_present=item_present,
            hesabfa_code=code,
            hesabfa_product_code=product_code,
            active_current=active_current,
            action=action,
            reason=reason,
        )

    if not sku_norm:
        return finish("ERROR", "empty_sku")
    if duplicate_site_sku:
        return finish("AMBIGUOUS", "duplicate_site_sku")
    if len(product_mappings) > 1:
        return finish("AMBIGUOUS", "duplicate_local_mappings")
    if len(remote_matches) > 1:
        return finish("AMBIGUOUS", "duplicate_remote_product_code")

    remote = remote_matches[0] if len(remote_matches) == 1 else None
    remote_code = _remote_code(remote) if remote else ""
    remote_pc = _remote_product_code(remote) if remote else ""
    active_current = parse_remote_active(remote) if remote else None
    if remote is not None and not remote_code:
        return finish(
            "ERROR",
            "remote_code_missing",
            product_code=remote_pc,
            active_current=active_current,
        )

    if mapping is not None:
        if _normalize_sku(mapping.sku) != sku_norm:
            return finish(
                "AMBIGUOUS",
                "mapping_sku_mismatch",
                code=mapping.hesabfa_code,
                product_code=mapping.hesabfa_product_code or "",
            )
        mapped_pc = _normalize_sku(mapping.hesabfa_product_code or mapping.sku)
        if mapping.hesabfa_product_code and mapped_pc != sku_norm:
            return finish(
                "AMBIGUOUS",
                "mapping_product_code_mismatch",
                code=mapping.hesabfa_code,
                product_code=mapping.hesabfa_product_code or "",
            )
        if remote is None:
            return finish(
                "ERROR",
                "mapping_remote_missing",
                code=mapping.hesabfa_code,
                product_code=mapping.hesabfa_product_code or "",
            )
        if mapping.hesabfa_code != remote_code:
            return finish(
                "AMBIGUOUS",
                "mapping_code_mismatch",
                code=mapping.hesabfa_code,
                product_code=remote_pc,
                active_current=active_current,
            )

    if remote is not None and foreign_code_owners:
        return finish(
            "AMBIGUOUS",
            "hesabfa_code_owned_by_other_product",
            code=remote_code,
            product_code=remote_pc,
            active_current=active_current,
        )

    if remote is None:
        return finish("CREATE_MISSING_ACTIVE", "")

    if active_current is None:
        return finish(
            "ERROR",
            "remote_active_unknown",
            code=remote_code,
            product_code=remote_pc,
        )

    if mapping is None and active_current is True:
        return finish(
            "LINK_EXISTING",
            "",
            code=remote_code,
            product_code=remote_pc,
            active_current=True,
        )
    if mapping is None and active_current is False:
        return finish(
            "ACTIVATE_EXISTING",
            "link_and_activate",
            code=remote_code,
            product_code=remote_pc,
            active_current=False,
        )
    if active_current is True:
        return finish(
            "NOOP_ALREADY_ACTIVE",
            "",
            code=remote_code,
            product_code=remote_pc,
            active_current=True,
        )
    return finish(
        "ACTIVATE_EXISTING",
        "",
        code=remote_code,
        product_code=remote_pc,
        active_current=False,
    )


def classify_catalog(
    products: Sequence[SiteProductView],
    mappings: Sequence[MappingView],
    remote_items: Sequence[Mapping[str, Any]],
    *,
    duplicate_skus: set[str] | None = None,
) -> list[ReconciliationRow]:
    """Classify products in deterministic id order. Pure function."""
    remote_index = index_remote_by_product_code(remote_items)
    owners: dict[str, list[int]] = defaultdict(list)
    for mapping in mappings:
        code = (mapping.hesabfa_code or "").strip()
        if code:
            owners[code].append(mapping.product_id)
    if duplicate_skus is None:
        counts: dict[str, int] = defaultdict(int)
        for product in products:
            key = _normalize_sku(product.sku)
            if key:
                counts[key] += 1
        duplicate_skus = {key for key, count in counts.items() if count > 1}

    rows: list[ReconciliationRow] = []
    for product in sorted(products, key=lambda row: row.id):
        sku_norm = _normalize_sku(product.sku)
        matches = remote_index.get(sku_norm, [])
        foreign: list[int] = []
        if len(matches) == 1:
            code = _remote_code(matches[0])
            foreign = [pid for pid in owners.get(code, []) if pid != product.id]
        rows.append(
            classify_product(
                product,
                mappings,
                matches,
                duplicate_site_sku=sku_norm in duplicate_skus,
                foreign_code_owners=foreign,
            )
        )
    return rows


def summarize(
    rows: Sequence[ReconciliationRow],
    *,
    population_total: int,
    remote_writes: int = 0,
    database_writes: int = 0,
) -> dict[str, Any]:
    """Aggregate the required dry-run counters. Counts describe ``rows`` only."""

    def count(predicate: Any) -> int:
        return sum(1 for row in rows if predicate(row))

    would_link = count(
        lambda row: row.action == "LINK_EXISTING"
        or (row.action == "ACTIVATE_EXISTING" and row.reason == "link_and_activate")
    )
    return {
        "DRY_RUN": True,
        "REMOTE_WRITES": remote_writes,
        "DATABASE_WRITES": database_writes,
        "ITEM_SAVE_CONTRACT": ITEM_SAVE_CONTRACT,
        "ACTIVATION_APPLY": ACTIVATION_APPLY_STATUS,
        "TOTAL_SITE_NON_DELETED": population_total,
        "SCANNED": len(rows),
        "SCAN_COMPLETE": len(rows) == population_total,
        "MAPPED": count(lambda row: row.hesabfa_mapping_present),
        "REMOTE_MATCHED": count(
            lambda row: row.hesabfa_item_present
            and row.reason != "duplicate_remote_product_code"
        ),
        "REMOTE_ALREADY_ACTIVE": count(lambda row: row.hesabfa_active_current is True),
        "REMOTE_INACTIVE": count(lambda row: row.hesabfa_active_current is False),
        "REMOTE_ACTIVE_UNKNOWN": count(lambda row: row.reason == "remote_active_unknown"),
        "REMOTE_MISSING": count(lambda row: not row.hesabfa_item_present),
        "MAPPING_MISSING_REMOTE_FOUND": count(
            lambda row: (not row.hesabfa_mapping_present)
            and row.action in {"LINK_EXISTING", "ACTIVATE_EXISTING"}
        ),
        "MAPPING_STALE": count(lambda row: row.reason in STALE_MAPPING_REASONS),
        "AMBIGUOUS": count(lambda row: row.action == "AMBIGUOUS"),
        "ERRORS": count(lambda row: row.action == "ERROR"),
        "WOULD_ACTIVATE": count(lambda row: row.action == "ACTIVATE_EXISTING"),
        "WOULD_CREATE": count(lambda row: row.action == "CREATE_MISSING_ACTIVE"),
        "WOULD_LINK": would_link,
        "AMBIGUITY_BREAKDOWN": ambiguity_breakdown(rows),
        "ERROR_BREAKDOWN": error_breakdown(rows),
        "COHORTS": cohort_counts(rows),
    }


_AMBIGUITY_LABELS = {
    "duplicate_site_sku": "DUPLICATE_SITE_SKU",
    "duplicate_remote_product_code": "DUPLICATE_REMOTE_PRODUCT_CODE",
    "duplicate_local_mappings": "DUPLICATE_LOCAL_MAPPING",
    "mapping_sku_mismatch": "MAPPING_SKU_MISMATCH",
    "mapping_product_code_mismatch": "MAPPING_PRODUCT_CODE_MISMATCH",
    "mapping_code_mismatch": "MAPPING_CODE_MISMATCH",
    "hesabfa_code_owned_by_other_product": "HESABFA_CODE_OWNED_BY_OTHER_PRODUCT",
}

_ERROR_LABELS = {
    "empty_sku": "EMPTY_SKU",
    "mapping_remote_missing": "MAPPING_REMOTE_MISSING",
    "remote_active_unknown": "REMOTE_ACTIVE_UNKNOWN",
    "remote_code_missing": "REMOTE_CODE_MISSING",
    "pagination_error": "PAGINATION_ERROR",
    "api_read_error": "API_READ_ERROR",
}


def _samples(rows: Sequence[ReconciliationRow], *, limit: int = 20) -> list[dict[str, Any]]:
    return [
        {"site_product_id": row.site_product_id, "sku": row.sku}
        for row in sorted(rows, key=lambda item: item.site_product_id)[:limit]
    ]


def ambiguity_breakdown(rows: Sequence[ReconciliationRow]) -> dict[str, Any]:
    """Group AMBIGUOUS rows by reason. Does not repair identity."""
    grouped: dict[str, list[ReconciliationRow]] = defaultdict(list)
    for row in rows:
        if row.action != "AMBIGUOUS":
            continue
        label = _AMBIGUITY_LABELS.get(row.reason, "OTHER_AMBIGUITY")
        grouped[label].append(row)
    labels = list(_AMBIGUITY_LABELS.values()) + ["OTHER_AMBIGUITY"]
    return {
        label: {"count": len(grouped.get(label, [])), "samples": _samples(grouped.get(label, []))}
        for label in labels
    }


def error_breakdown(rows: Sequence[ReconciliationRow]) -> dict[str, Any]:
    """Group ERROR rows by reason. Does not repair them."""
    grouped: dict[str, list[ReconciliationRow]] = defaultdict(list)
    for row in rows:
        if row.action != "ERROR":
            continue
        label = _ERROR_LABELS.get(row.reason, "OTHER_ERROR")
        grouped[label].append(row)
    labels = list(_ERROR_LABELS.values()) + ["OTHER_ERROR"]
    return {
        label: {"count": len(grouped.get(label, [])), "samples": _samples(grouped.get(label, []))}
        for label in labels
    }


def cohort_counts(rows: Sequence[ReconciliationRow]) -> dict[str, int]:
    """Read-only migration cohorts. Missing remote items are not inactive."""

    def n(predicate: Any) -> int:
        return sum(1 for row in rows if predicate(row))

    def inactive_remote(row: ReconciliationRow) -> bool:
        return row.hesabfa_active_current is False

    def missing(row: ReconciliationRow) -> bool:
        return not row.hesabfa_item_present

    return {
        "SITE_INACTIVE__HF_ACTIVE": n(
            lambda row: (not row.site_is_active) and row.hesabfa_active_current is True
        ),
        "SITE_INACTIVE__HF_INACTIVE": n(lambda row: (not row.site_is_active) and inactive_remote(row)),
        "SITE_UNAVAILABLE__HF_INACTIVE": n(
            lambda row: (not row.site_is_available) and inactive_remote(row)
        ),
        "SITE_UNPRICED__HF_INACTIVE": n(
            lambda row: (not row.site_price_present) and inactive_remote(row)
        ),
        "SITE_ACTIVE__HF_MISSING": n(lambda row: row.site_is_active and missing(row)),
        "SITE_INACTIVE__HF_MISSING": n(lambda row: (not row.site_is_active) and missing(row)),
    }


def remote_inventory_stats(items: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Counts for a complete item/getItems read. No secrets."""
    codes: set[str] = set()
    product_codes: list[str] = []
    blank = 0
    for item in items:
        code = _remote_code(item)
        if code:
            codes.add(code)
        product_code = _normalize_sku(_remote_product_code(item))
        if not product_code:
            blank += 1
        else:
            product_codes.append(product_code)
    grouped: dict[str, int] = defaultdict(int)
    for product_code in product_codes:
        grouped[product_code] += 1
    return {
        "UNIQUE_CODE": len(codes),
        "UNIQUE_PRODUCT_CODE": len(grouped),
        "BLANK_PRODUCT_CODE": blank,
        "DUPLICATE_PRODUCT_CODE_GROUPS": sum(1 for count in grouped.values() if count > 1),
    }


def assert_dry_run_safe(*, remote_writes: int, database_writes: int) -> None:
    if remote_writes != 0 or database_writes != 0:
        raise RuntimeError(
            f"dry-run safety violated remote_writes={remote_writes} "
            f"database_writes={database_writes}"
        )


def write_artifacts(
    directory: Path,
    rows: Sequence[ReconciliationRow],
    summary: Mapping[str, Any],
) -> None:
    """Write the reconciliation report. Refuses if the summary recorded writes."""
    assert_dry_run_safe(
        remote_writes=int(summary["REMOTE_WRITES"]),
        database_writes=int(summary["DATABASE_WRITES"]),
    )
    directory.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows, key=lambda row: row.site_product_id)
    _write_csv(directory / "reconciliation.csv", ordered)
    _write_csv(
        directory / "errors.csv",
        [row for row in ordered if row.action == "ERROR"],
    )
    _write_csv(
        directory / "ambiguous.csv",
        [row for row in ordered if row.action == "AMBIGUOUS"],
    )
    payload = dict(summary)
    (directory / "summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines: list[str] = []
    for name in ARTIFACT_NAMES:
        digest = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (directory / "sha256sums.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: Sequence[ReconciliationRow]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.as_csv())


def rows_from_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


async def fetch_catalog_page(
    session: SupportsExecute,
    *,
    after_id: int,
    batch_size: int,
) -> tuple[int, list[SiteProductView], list[MappingView], set[str]]:
    """SELECT non-deleted products and mappings. Caller must be read-only."""
    from sqlalchemy import func, select

    from app.db.models.hesabfa import HesabfaItemMapping
    from app.db.models.product import Product

    total = (
        await session.execute(
            select(func.count(Product.id)).where(Product.deleted_at.is_(None))
        )
    ).scalar_one()
    sku_rows = (
        await session.execute(
            select(Product.sku).where(Product.deleted_at.is_(None))
        )
    ).all()
    counts: dict[str, int] = defaultdict(int)
    for (sku,) in sku_rows:
        key = _normalize_sku(sku)
        if key:
            counts[key] += 1
    duplicate_skus = {key for key, count in counts.items() if count > 1}

    product_rows = (
        await session.execute(
            select(
                Product.id,
                Product.sku,
                Product.is_active,
                Product.is_available,
                Product.base_price,
            )
            .where(Product.deleted_at.is_(None), Product.id > after_id)
            .order_by(Product.id.asc())
            .limit(batch_size)
        )
    ).all()
    products = [
        SiteProductView(
            id=int(row.id),
            sku=str(row.sku),
            is_active=bool(row.is_active),
            is_available=bool(row.is_available),
            price_present=row.base_price is not None,
        )
        for row in product_rows
    ]
    mapping_rows = (await session.execute(select(HesabfaItemMapping))).scalars().all()
    mappings = [
        MappingView(
            product_id=int(row.product_id),
            sku=str(row.sku),
            hesabfa_code=str(row.hesabfa_code),
            hesabfa_product_code=row.hesabfa_product_code,
        )
        for row in mapping_rows
    ]
    return int(total), products, mappings, duplicate_skus


async def enforce_database_read_only(session: SupportsExecute) -> str:
    """Start a database-enforced read-only transaction.

    PostgreSQL: ``SET TRANSACTION READ ONLY`` then ``SHOW transaction_read_only``.
    SQLite tests: ``PRAGMA query_only=ON``. Other dialects fail closed.
    Call this before catalog SELECTs and roll the transaction back afterward.
    """
    from sqlalchemy import text

    bind = _session_bind(session)
    dialect = bind.dialect.name if bind is not None else ""
    if dialect == "postgresql":
        await session.execute(text("SET TRANSACTION READ ONLY"))
        shown = (await session.execute(text("SHOW transaction_read_only"))).scalar_one()
        if str(shown).strip().lower() != "on":
            raise RuntimeError(f"PostgreSQL transaction_read_only is {shown!r}")
        return "postgresql:transaction_read_only=on"
    if dialect == "sqlite":
        await session.execute(text("PRAGMA query_only = ON"))
        flag = (await session.execute(text("PRAGMA query_only"))).scalar_one()
        if int(flag) != 1:
            raise RuntimeError(f"SQLite query_only is {flag!r}")
        return "sqlite:query_only=1"
    raise RuntimeError(f"no database-enforced read-only mode for dialect {dialect or 'unknown'}")


def _session_bind(session: SupportsExecute) -> Any:
    inner = getattr(session, "inner", session)
    bind = getattr(inner, "bind", None)
    if bind is None:
        get_bind = getattr(inner, "get_bind", None)
        if callable(get_bind):
            bind = get_bind()
    return bind


async def release_database_read_only(session: SupportsExecute, mode: str) -> None:
    """End the read-only transaction. SQLite query_only is cleared so the pooled connection is usable.

    Rollback goes to the real session. ``DryRunSession.rollback`` is not used:
    that method counts a database write and raises.
    """
    from sqlalchemy import text

    if mode.startswith("sqlite"):
        await session.execute(text("PRAGMA query_only = OFF"))
    target = getattr(session, "inner", session)
    rollback = getattr(target, "rollback", None)
    if rollback is not None:
        await rollback()


async def fetch_catalog_snapshot(session: SupportsExecute) -> dict[str, Any]:
    """Load the non-deleted catalog once. Caller must already be read-only."""
    from sqlalchemy import and_, case, func, select

    from app.db.models.hesabfa import HesabfaItemMapping
    from app.db.models.product import Product

    non_deleted = Product.deleted_at.is_(None)
    baseline_row = (
        await session.execute(
            select(
                func.count(Product.id),
                func.coalesce(func.sum(case((non_deleted, 1), else_=0)), 0),
                func.coalesce(func.sum(case((Product.deleted_at.is_not(None), 1), else_=0)), 0),
                func.coalesce(
                    func.sum(case((and_(non_deleted, Product.is_active.is_(True)), 1), else_=0)),
                    0,
                ),
                func.coalesce(
                    func.sum(case((and_(non_deleted, Product.is_active.is_(False)), 1), else_=0)),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case((and_(non_deleted, Product.is_available.is_(True)), 1), else_=0)
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case((and_(non_deleted, Product.is_available.is_(False)), 1), else_=0)
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(case((and_(non_deleted, Product.base_price.is_not(None)), 1), else_=0)),
                    0,
                ),
                func.coalesce(
                    func.sum(case((and_(non_deleted, Product.base_price.is_(None)), 1), else_=0)),
                    0,
                ),
            )
        )
    ).one()
    baseline = {
        "TOTAL_PRODUCTS": int(baseline_row[0]),
        "TOTAL_NON_DELETED": int(baseline_row[1]),
        "TOTAL_SOFT_DELETED": int(baseline_row[2]),
        "NON_DELETED_ACTIVE": int(baseline_row[3]),
        "NON_DELETED_INACTIVE": int(baseline_row[4]),
        "NON_DELETED_AVAILABLE": int(baseline_row[5]),
        "NON_DELETED_UNAVAILABLE": int(baseline_row[6]),
        "NON_DELETED_PRICED": int(baseline_row[7]),
        "NON_DELETED_UNPRICED": int(baseline_row[8]),
    }
    product_rows = (
        await session.execute(
            select(
                Product.id,
                Product.sku,
                Product.is_active,
                Product.is_available,
                Product.base_price,
            )
            .where(non_deleted)
            .order_by(Product.id.asc())
        )
    ).all()
    products = [
        SiteProductView(
            id=int(row.id),
            sku=str(row.sku),
            is_active=bool(row.is_active),
            is_available=bool(row.is_available),
            price_present=row.base_price is not None,
        )
        for row in product_rows
    ]
    if len(products) != baseline["TOTAL_NON_DELETED"]:
        raise RuntimeError(
            "catalog snapshot count mismatch "
            f"rows={len(products)} TOTAL_NON_DELETED={baseline['TOTAL_NON_DELETED']}"
        )
    counts: dict[str, int] = defaultdict(int)
    for product in products:
        key = _normalize_sku(product.sku)
        if key:
            counts[key] += 1
    duplicate_skus = {key for key, count in counts.items() if count > 1}
    mapping_rows = (await session.execute(select(HesabfaItemMapping))).scalars().all()
    mappings = [
        MappingView(
            product_id=int(row.product_id),
            sku=str(row.sku),
            hesabfa_code=str(row.hesabfa_code),
            hesabfa_product_code=row.hesabfa_product_code,
        )
        for row in mapping_rows
    ]
    return {
        "baseline": baseline,
        "products": products,
        "mappings": mappings,
        "duplicate_skus": duplicate_skus,
    }


async def load_remote_items(client: DryRunHesabfaClient, *, page_size: int = 100) -> Any:
    """Page every item/getItems row. Never calls a write method.

    Raises if fetched rows do not equal reported TotalCount.
    """
    from app.services.hesabfa.item_push import paginate_get_items

    page = await paginate_get_items(client, page_size=page_size)
    if client.remote_writes != 0:
        raise RuntimeError("remote item load performed a write")
    return page
