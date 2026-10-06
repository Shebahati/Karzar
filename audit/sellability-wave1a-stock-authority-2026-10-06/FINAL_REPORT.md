# Karzar Sellability Wave 1A — FINAL REPORT

## A. Status

`COMPLETE` — verdict `PARTIAL_AUTHORITY`

## B. Safety

```text
Production mutation: NO
Catalog APPLY: NO
Hesabfa mutation: NO
Deployment: NO
Wave 1B APPLY: NO
WAVE_1B_APPLY_AUTHORIZED=NO
OUT_OF_SCOPE=0
```

## C. Identity

```text
host: srv5944957438
database: karzar_staging
database_user: karzar_staging
database_server_addr: (empty inside docker exec; host/container/volume proven)
database_server_port: (empty inside docker exec)
APP_ENV: staging
KARZAR_DATA_PLANE: (unset)
KARZAR_ALLOW_PRODUCTION_WRITE: (unset)
Alembic: u4v5w6x7y8z9
DB container: lathe_postgres
volume: karzar_postgres_data
transaction_read_only: on
snapshot_utc: 2026-10-06T10:17:42Z
origin_main: 4e5056de100c1f8ceb2900deac40ee8efb24216a
PR #421: MERGED @ 4e5056de100c1f8ceb2900deac40ee8efb24216a
collector: local SSH read-only docker exec psql (Category A)
```

## D. Wave 0 Target Lock

```text
input: audit/sellability-wave0-2026-10-03/READY_EXCEPT_AVAILABILITY.csv
rows: 330
input_sha256: 5ede063d908e1f8f1a85486b9cb4b21832543a2ab8c62656e4569b5ac5c50bd3
sorted_product_id_sha256: 5dc3e6984661993c5832baa3c340e9ea9cd557822816f0197a290f011c15646a
sorted_sku_sha256: 70421d1f5ab11c89ce20dcd196600f7eac49e3da2f18603bd04e0f91411b4799
brands: INSIZE 226, ASTPOWER 53, SAN OU 24, Dasqua 22, TERMA 4, Mitutoyo 1
rebuild_from_production: NO
```

## E. Commercial Drift

| Class | Count |
| --- | ---: |
| CURRENT_STILL_ONLY_AVAILABILITY_BLOCKED | 329 |
| ALREADY_AVAILABLE | 0 |
| NO_LONGER_ACTIVE | 0 |
| NO_LONGER_PRICED | 0 |
| NO_LONGER_IMAGED | 0 |
| DELETED | 0 |
| IDENTITY_DRIFT | 1 |
| OTHER_GATE_DRIFT | 0 |

Manufacturer_code changes are not identity drift (Phase 2C). Price changes with
`base_price>0` are not disqualifying.

## F. Current Sellability Check

| Metric | Wave 0 | Current | Δ |
| --- | ---: | ---: | ---: |
| live | 6536 | 6536 | 0 |
| active | 1585 | 1585 | 0 |
| available | 3755 | 3756 | 1 |
| priced | 4552 | 4879 | 327 |
| imaged | 1464 | 1464 | 0 |
| visible | 1368 | 1368 | 0 |
| sellable | 716 | 717 | 1 |

Proven sellable delta: product_id `1789` / SKU `1114-150` moved
`is_available false→true` (still active+priced+imaged). Same row now has
`brand_id NULL` (empty brand vs historical INSIZE) → commercial drift class
`IDENTITY_DRIFT` (exactly one class). Global priced +327 is observed but not
attributed to a single mutation in this pass.

## G. Authority Policy (re-derived)

```text
PRICE AUTHORITY ≠ AVAILABILITY AUTHORITY
Site is_available is binary; warehouse counts are Hesabfa-only
Never infer AVAILABLE from price / row existence / is_active / prior is_available
Freshness: CURRENT_ENOUGH≤14d, AGING_BUT_USABLE≤45d, STALE>45d, UNKNOWN=no date
Identity: EXACT_MANUFACTURER_CODE | EXACT_SKU | EXACT_NORMALIZED_SKU |
          REGISTERED_BRAND_SPECIFIC_DETERMINISTIC_RULE only
```

Sources: `docs/catalog/SUPPLIER_STOCK_AUTHORITY.md`, `docs/COMMERCE.md`,
`docs/HESABFA.md`, `scripts/validate_supplier_stock.py`,
`scripts/map_supplier_stock.py`, `scripts/catalog_target/supplier_stock.py`,
`brand_source_inventory_adapters.py`, `insize_sales_activation*.py`.

## H. Source Inventory

See `SOURCE_INVENTORY.csv` / `SOURCE_MANIFEST.json`.

- INSIZE distributor xlsx: registered inventory authority; freshness `AGING_BUT_USABLE` (34d from 2026-09-02).
- DASQUA PDF + Owner adapter: registered; freshness `STALE` (157d from 2026-05-02).
- TERMA PDF + Owner adapter: registered; freshness `UNKNOWN` (no date).
- ASTPOWER: price/catalog files only → not stock authority.
- SAN OU: `STOCK_AUTHORITY_MISSING`.
- Mitutoyo: registered catalog-only → not stock authority.
- Raw supplier files are **not** committed.

## I. Stock Classes (330 targets)

| Class | Count |
| --- | ---: |
| AVAILABLE | 10 |
| UNAVAILABLE | 190 |
| UNKNOWN | 130 |
| CONFLICT | 0 |

## J. Brand Reconciliation

See per-brand CSVs and `BRAND_SUMMARY.csv`.

| Brand | Targets | AVAIL | UNAVAIL | UNKNOWN | CONFLICT | Future APPLY |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| INSIZE | 226 | 2 | 187 | 37 | 0 | 2 |
| ASTPOWER | 53 | 0 | 0 | 53 | 0 | 0 |
| SANOU | 24 | 0 | 0 | 24 | 0 | 0 |
| DASQUA | 22 | 8 | 0 | 14 | 0 | 0 |
| TERMA | 4 | 0 | 3 | 1 | 0 | 0 |
| MITUTOYO | 1 | 0 | 0 | 1 | 0 | 0 |

## K. Hesabfa Read-only

- Matched via Tag: 229/330
- Stock>0 among matched: 6
- Semantics: `HESABFA_STOCK_SEMANTICS_UNPROVEN`
- Details: `HESABFA_SEMANTICS_REPORT.md`, `HESABFA_READONLY_RECONCILIATION.csv`

## L. Future APPLY Candidates

`future_apply_candidate=YES` requires: historical cohort ∧ still unavailable ∧
live+active+priced+imaged ∧ stock AVAILABLE ∧ exact identity ∧ accepted freshness
∧ no conflict.

| Bucket | Count |
| --- | ---: |
| CURRENT_ENOUGH | 0 |
| AGING_BUT_USABLE | 2 |
| TOTAL | 2 |

Candidates:
- 2100 8601-100 INSIZE freshness=AGING_BUT_USABLE via EXACT_MANUFACTURER_CODE
- 4140 5042 INSIZE freshness=AGING_BUT_USABLE via EXACT_SKU

## M. Owner Decisions Required

See `OWNER_AUTHORITY_DECISIONS_REQUIRED.md`.

## N. Tooling Gaps

- Generic multi-brand `is_available` APPLY still not Owner-authorized.
- INSIZE trailing-A deterministic rule not registered.
- Hesabfa Stock→availability policy unset.
- ASTPOWER/SAN OU availability adapters missing.

## O. Wave 1B Design Gate

```text
VERDICT=PARTIAL_AUTHORITY
WAVE_1B_APPLY_AUTHORIZED=NO
```

Wave 1B design may proceed only for brands/sources with registered authority and
accepted freshness; APPLY remains blocked pending Owner authorization.

## P. Artifact Integrity

All files hashed in `SHA256SUMS.txt`.

## Q. Non-Goals Confirmed

No Production DB writes, no catalog APPLY, no Hesabfa writes, no deploy, no Wave 1B APPLY.

## R. Predicate Recap

```text
SELLABLE = deleted_at IS NULL AND is_active AND is_available
           AND base_price > 0 AND real image present
```

## S. Terminal Result Block

See repository PR description / agent return block
`KARZAR SELLABILITY WAVE 1A — STOCK AUTHORITY RESULT`.
