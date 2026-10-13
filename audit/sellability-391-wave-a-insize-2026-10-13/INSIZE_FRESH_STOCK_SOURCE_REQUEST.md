# INSIZE fresh stock source request (distributor)

Wave A strict unlock requires **proven calendar `source_date`** and authoritative `AVAILABLE` stock with freshness **not** `STALE` or `UNKNOWN` per `docs/catalog/SUPPLIER_STOCK_AUTHORITY.md` (`CURRENT_ENOUGH` ≤14 days or `AGING_BUT_USABLE` ≤45 days). A ≤14-day snapshot is preferred; 15–45 days is still usable under the current contract when date is proven.

## Please provide

1. Excel or CSV export of distributor inventory (same family as `موجودی توزیع کننده … 11 شهریور`).
2. Columns: **CODE** (manufacturer code), **وضعیت** (`موجود` / `نا موجود`), optional warehouse qty columns.
3. Explicit **calendar date** of the snapshot (Gregorian or Jalali with year) in the file or cover email.
4. Do **not** rely on filename month/day without year.

## Karzar will

- SHA256 the file, record manifest metadata, and rematch the **INSIZE ONLY_AVAILABILITY** cohort using governed identity only (`manufacturer_code`, exact SKU, `INSIZE_TRAILING_A_IDENTITY`).
- Produce a strict allowlist for Owner review before any `is_available` APPLY.

## Current blocker

Canonical workbook SHA `65a92337…` has clear `وضعیت` semantics but **SOURCE_YEAR_UNPROVEN** → freshness **UNKNOWN** → **0** strict candidates.
