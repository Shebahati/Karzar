# Karzar Sellability Wave 1A.1 — FINAL REPORT

## Status

`COMPLETE` — verdict `AUTHORITY_REFRESH_STILL_REQUIRED`

## Safety

```text
Production mutation: NO
Database mutation: NO
Catalog APPLY: NO
Hesabfa mutation: NO
Deploy: NO
APPLY AUTHORIZED: NO
OUT_OF_SCOPE=0
```

## Identity plane

```text
host: srv5944957438
database: karzar_staging
DB container: lathe_postgres
volume: karzar_postgres_data
transaction_read_only: on
alembic: u4v5w6x7y8z9
APP_ENV: staging
snapshot_utc: 2026-10-06T10:59:37Z
origin/main: 9fc607ab90170375069c0d5b11ec33f4f64ae9dd
PR #429: MERGED
collector: Category A local SSH read-only docker exec psql
```

## INSIZE trailing-A identity (Owner-closed)

Registered `INSIZE_TRAILING_A_IDENTITY` (`insize_trailing_a_identity/1.0.0`) in
`scripts/catalog_target/insize_trailing_a_identity.py` +
`docs/catalog/SUPPLIER_STOCK_AUTHORITY.md` §4. Unit tests: 9 OK.

| Metric | Count |
| --- | ---: |
| Prior UNKNOWN identity | 37 |
| Deterministically resolved | 36 |
| AVAILABLE (among resolved) | 8 |
| UNAVAILABLE (among resolved) | 28 |
| Still UNKNOWN | 1 |
| Collision / AMBIGUOUS | 0 |

Still UNKNOWN SKU: `1205-1502` (no workbook `XA`).

Availability still from workbook `وضعیت` only — identity rule does not invent stock.

## INSIZE source year / freshness

```text
SOURCE_YEAR_UNPROVEN
LATEST_AUTHORITATIVE_INSIZE_STOCK=2026-09-02  # claimed; year unproven
CURRENT_ENOUGH_SOURCE_AVAILABLE=NO
```

Primary SHA256 unchanged: `8cecb478a4e48166436b9c526ebace54430800925819e3e062e631ad56eee3a4`. No newer inventory authority by document date.

## Other brands

| Brand | Refresh result |
| --- | --- |
| DASQUA | Same SHA authority; still STALE (2026-05-02); DOCS 2026-07-25 copy identical |
| TERMA | Same SHA; source_date still unproven; freshness UNKNOWN |
| ASTPOWER | PRICE/CATALOG only; proposed decision doc; not registered |
| SAN OU | Price-List PDF found; proposed decision doc; not registered |
| MITUTOYO | Catalog only → `MITUTOYO_STOCK_AUTHORITY_MISSING` |
| Hesabfa | Semantics UNPROVEN; proposal only; no activation |

## Product 1789

`is_available` flipped by admin actor 3 on 2026-10-04 (logged). `brand_id` NULL
with **zero** brand change-log rows. Remediation recommended; **not performed**.

## Refreshed stock classes (330)

| Class | Count |
| --- | ---: |
| AVAILABLE | 18 |
| UNAVAILABLE | 218 |
| UNKNOWN | 94 |
| CONFLICT | 0 |

UNKNOWN reduction: 130 → 94 (Δ -36).

AVAILABLE freshness under unproven INSIZE year: CURRENT_ENOUGH=0,
AGING=0, STALE=8,
UNKNOWN=10.

## Strict future APPLY candidates

```text
CURRENT_ENOUGH AVAILABLE strict count: 0
```

Gate requires: still unavailable ∧ live+active+priced+imaged ∧ stock AVAILABLE ∧
exact identity ∧ CURRENT_ENOUGH ∧ no conflict. Freshness not CURRENT_ENOUGH for any
AVAILABLE row after year demotion / stale DASQUA / missing authorities.

## Wave 1B gate

```text
VERDICT=AUTHORITY_REFRESH_STILL_REQUIRED
READY_FOR_WAVE1B_DESIGN=NO
APPLY AUTHORIZED=NO
```

Wave 1B design should wait on: proven INSIZE year or newer CURRENT_ENOUGH stock,
DASQUA refresh, TERMA date, and/or Owner registration of ASTPOWER/SAN OU/Mitutoyo/
Hesabfa policies as applicable.

## Non-goals confirmed

No Production DB writes, no catalog APPLY, no Hesabfa writes, no deploy, Wave 1A
artifacts untouched.
