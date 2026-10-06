# Karzar Sellability Wave 0 — FINAL REPORT

## A. Status

`COMPLETE`

## B. Safety

```text
Production mutation: NO
Catalog APPLY: NO
Hesabfa mutation: NO
Deployment: NO
```

## C. Identity

```text
host: srv5944957438
database: karzar_staging
database_user: karzar_staging
database_server_addr: 172.18.0.2/32
database_server_port: 5432
APP_ENV: staging
KARZAR_DATA_PLANE: (unset → default live per OPERATIONS.md / CR-011)
Alembic: u4v5w6x7y8z9
git_branch: UNKNOWN (VPS /opt/karzar/Karzar rev-parse unavailable in runner context)
git_sha: UNKNOWN (same)
origin_main: UNKNOWN (same)
collector_workflow: GitHub Actions run 37114760740 on self-hosted karzar-vps
DB container: lathe_postgres
volume: karzar_postgres_data
transaction_read_only: on
snapshot_utc: 2026-10-03T09:57:14Z
```

## D. Current Global Truth

| Metric | Count |
| --- | ---: |
| live | 6536 |
| active | 1585 |
| inactive | 4951 |
| available | 3755 |
| unavailable | 2781 |
| priced | 4552 |
| unpriced | 1984 |
| imaged | 1464 |
| unimaged | 5072 |
| visible | 1368 |
| sellable | 716 |
| non_sellable | 5820 |

## E. Sellability Predicate

Re-derived from current code (`app/utils/public_catalog.py`,
`app/services/cart_service.py`, `app/services/checkout_service.py`,
`docs/COMMERCE.md`):

```text
LIVE     = deleted_at IS NULL
ACTIVE   = LIVE AND is_active
AVAILABLE= LIVE AND is_available
PRICED   = LIVE AND base_price IS NOT NULL AND base_price > 0
IMAGED   = EXISTS non-placeholder product image URL
VISIBLE  = LIVE AND is_active AND IMAGED
SELLABLE = VISIBLE AND is_available AND PRICED
```

Material drift vs naive historical copy:
- Cart purchase lane checks `base_price is None` only (not `<= 0`).
- Checkout purchase requires `is_available`; cart add does not.
- Storefront visibility requires real image when
  `STOREFRONT_HIDE_IMAGELESS_PRODUCTS=True` (default).
- Production does not require on-disk materialization
  (`STOREFRONT_REQUIRE_MATERIALIZED_IMAGES` defaults with DEBUG).
- Wave 0 census keeps PRICED as `base_price > 0` for commercial readiness.

## F. Blocker Matrix

| Cohort | Count |
| --- | ---: |
| ACTIVE + IMAGE | 3038 |
| ACTIVE + AVAILABILITY + PRICE + IMAGE | 1647 |
| SELLABLE_NOW | 716 |
| ONLY_AVAILABILITY | 330 |
| AVAILABILITY + PRICE | 322 |
| AVAILABILITY + IMAGE | 217 |
| ACTIVE + AVAILABILITY + IMAGE | 169 |
| ACTIVE + AVAILABILITY | 82 |
| ACTIVE + AVAILABILITY + PRICE | 14 |
| ACTIVE + PRICE + IMAGE | 1 |

Block counts: 1=330, 2=3659, 3=184, 4=1647

Invariant check: SELLABLE + NON_SELLABLE = LIVE → 
`716 + 5820 = 6536` 
(OK)

## G. One-Field Unlocks

- ONLY_AVAILABILITY: 330
- ONLY_ACTIVE: 0
- ONLY_PRICE: 0
- ONLY_IMAGE: 0

READY_EXCEPT_AVAILABILITY brands:
- INSIZE | اینسایز: 226
- ASTPOWER | ای اس تی پاور: 53
- SAN OU | سانو: 24
- Dasqua | داسکوا: 22
- TERMA | ترما: 4
- Mitutoyo | میتوتویو: 1

## H. Two-Field Unlocks

- ACTIVE + IMAGE: 3038
- ACTIVE + AVAILABILITY: 82
- AVAILABILITY + PRICE: 322
- AVAILABILITY + IMAGE: 217
- ACTIVE + PRICE: 0
- PRICE + IMAGE: 0

## I. Three/Four-Field Products

- 3 blockers: 184
- 4 blockers: 1647

## J. Brand Matrix

Top brands by live count (see `KARZAR_BRAND_SELLABILITY.csv` for full):

| brand | live | sellable | only_avail | act+img | 3blk | 4blk | authority |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| ASTPOWER | ای اس تی پاور | 975 | 83 | 53 | 669 | 14 | 149 | PARTIAL_SOURCE |
| INSIZE | اینسایز | 872 | 159 | 226 | 0 | 102 | 127 | AUTHORITATIVE_SOURCE_AVAILABLE |
| Dasqua | داسکوا | 727 | 31 | 22 | 457 | 0 | 0 | AUTHORITATIVE_SOURCE_AVAILABLE |
| ZCC.CT | زد سی‌سی | 583 | 175 | 0 | 0 | 33 | 314 | PARTIAL_SOURCE |
| TIGER TEC | تایگرتک | 517 | 0 | 0 | 517 | 0 | 0 | NO_REGISTERED_SOURCE |
| YOWAX | یواکس | 353 | 0 | 0 | 350 | 0 | 3 | NO_REGISTERED_SOURCE |
| Chumpower | چام‌پاور | 347 | 0 | 0 | 315 | 0 | 32 | NO_REGISTERED_SOURCE |
| SAN OU | سانو | 317 | 22 | 24 | 63 | 14 | 157 | PARTIAL_SOURCE |
| TERMA | ترما | 312 | 177 | 4 | 131 | 0 | 0 | AUTHORITATIVE_SOURCE_AVAILABLE |
| Mitutoyo | میتوتویو | 304 | 69 | 1 | 105 | 15 | 73 | PARTIAL_SOURCE |
| [NO BRAND] | 295 | 0 | 0 | 7 | 0 | 288 | NO_REGISTERED_SOURCE |
| ASIMETO | آسیمتو | 235 | 0 | 0 | 0 | 0 | 235 | NO_REGISTERED_SOURCE |
| ET | ای تی | 227 | 0 | 0 | 221 | 0 | 6 | NO_REGISTERED_SOURCE |
| Mighty Seven | مایتی سون | 182 | 0 | 0 | 182 | 0 | 0 | NO_REGISTERED_SOURCE |
| Groz | گروز | 127 | 0 | 0 | 0 | 0 | 127 | NO_REGISTERED_SOURCE |
| Chagan | چاگان | 27 | 0 | 0 | 0 | 0 | 27 | NO_REGISTERED_SOURCE |
| SHAMS | شمس | 27 | 0 | 0 | 21 | 6 | 0 | PARTIAL_SOURCE |
| Winstar | وینستار | 21 | 0 | 0 | 0 | 0 | 21 | NO_REGISTERED_SOURCE |
| MPA | ام پی ای | 14 | 0 | 0 | 0 | 0 | 14 | NO_REGISTERED_SOURCE |
| Transmex | ترنمکس | 11 | 0 | 0 | 0 | 0 | 11 | NO_REGISTERED_SOURCE |
| 3Keego | کیگو | 10 | 0 | 0 | 0 | 0 | 10 | NO_REGISTERED_SOURCE |
| Vertex | ورتکس | 10 | 0 | 0 | 0 | 0 | 10 | NO_REGISTERED_SOURCE |
| Viyer | ویر | 9 | 0 | 0 | 0 | 0 | 9 | NO_REGISTERED_SOURCE |
| ZPS | زد پی‌اس | 6 | 0 | 0 | 0 | 0 | 6 | NO_REGISTERED_SOURCE |
| CP-GRAT | سی‌پی‌گرات | 4 | 0 | 0 | 0 | 0 | 4 | NO_REGISTERED_SOURCE |

## K. Authority Readiness

Confirmed policy:

```text
price != availability authority
catalog presence != availability
is_active != availability
historical is_available != proof of current physical stock
```

Stock freshness policy remains current:
- CURRENT_ENOUGH <= 14 days
- AGING_BUT_USABLE <= 45 days
- STALE > 45 days
- UNKNOWN missing/unparseable source_date

Wave 0 did **not** parse live supplier stock files on the VPS.
Near-sellable stock freshness is therefore `FRESHNESS_NOT_VALIDATED` at
SKU level (CURRENT_ENOUGH / AGING_BUT_USABLE / STALE unknown).

Evidence-quality clarification (not a Production recount):
- `REGISTERED_AVAILABILITY_AUTHORITY` = an Owner-confirmed / registered
  availability adapter or inventory-role source exists (see
  `docs/catalog/SUPPLIER_STOCK_AUTHORITY.md` §10 for
  `DASQUA_GOOGLE_DRIVE_INVENTORY_LIST` and `TERMA_GOOGLE_DRIVE_INVENTORY_LIST`).
- `FRESHNESS_NOT_VALIDATED` = Wave 0 did not run stock validate/map, so
  freshness class was not proven for any SKU.
- Do **not** read `STOCK_AUTHORITY_MISSING` for Dasqua/TERMA — those brands
  have registered availability adapters; only freshness was unvalidated here.

Brand-level authority is in `AUTHORITY_READINESS_BY_BRAND.csv`.

## L. Current vs Historical

Recomputed live from Production on `2026-10-03T09:57:14Z` against prior proven
snapshot `audit/product-status-2026-09-24/` (`2026-09-24T07:43:42Z`).
**Every compared commercial metric is identical (delta 0).** No material catalog
shift is evidenced for sellability predicates between those snapshots.

| metric | previous | current | delta | cause |
| --- | ---: | ---: | ---: | --- |
| live | 6536 | 6536 | +0 | UNCHANGED |
| active | 1585 | 1585 | +0 | UNCHANGED |
| available | 3755 | 3755 | +0 | UNCHANGED |
| priced | 4552 | 4552 | +0 | UNCHANGED |
| imaged | 1464 | 1464 | +0 | UNCHANGED |
| visible | 1368 | 1368 | +0 | UNCHANGED |
| sellable | 716 | 716 | +0 | UNCHANGED |
| non_sellable | 5820 | 5820 | +0 | UNCHANGED |
| 1_blocker | 330 | 330 | +0 | UNCHANGED |
| 2_blockers | 3659 | 3659 | +0 | UNCHANGED |
| 3_blockers | 184 | 184 | +0 | UNCHANGED |
| 4_blockers | 1647 | 1647 | +0 | UNCHANGED |
| only_availability | 330 | 330 | +0 | UNCHANGED |
| active_plus_image | 3038 | 3038 | +0 | UNCHANGED |
| availability_plus_price | 322 | 322 | +0 | UNCHANGED |
| availability_plus_image | 217 | 217 | +0 | UNCHANGED |
| active_plus_availability | 82 | 82 | +0 | UNCHANGED |

## M. Highest-Impact Next Waves

Ranked by evidence (not raw count alone). APPLY not authorized.

- **A_ONLY_AVAILABILITY**: n=330, complexity=LOW-MEDIUM, risk=HIGH if availability flipped without stock proof, MAX_THEORETICAL_UPLIFT=330
  brands: INSIZE | اینسایز:226; ASTPOWER | ای اس تی پاور:53; SAN OU | سانو:24; Dasqua | داسکوا:22; TERMA | ترما:4; Mitutoyo | میتوتویو:1
- **B_ACTIVATION_PLUS_AVAILABILITY**: n=82, complexity=MEDIUM, risk=MEDIUM-HIGH (inactive may be intentional hold), MAX_THEORETICAL_UPLIFT=82
  brands: ZCC.CT | زد سی‌سی:61; SAN OU | سانو:21
- **C_IMAGE_PLUS_ACTIVATION**: n=3038, complexity=HIGH, risk=MEDIUM (largest volume; image correctness critical), MAX_THEORETICAL_UPLIFT=3038
  brands: ASTPOWER | ای اس تی پاور:669; TIGER TEC | تایگرتک:517; Dasqua | داسکوا:457; YOWAX | یواکس:350; Chumpower | چام‌پاور:315; ET | ای تی:221; Mighty Seven | مایتی سون:182; TERMA | ترما:131; Mitutoyo | میتوتویو:105; SAN OU | سانو:63; SHAMS | شمس:21; [NO BRAND]:7
- **D_PRICE_PLUS_AVAILABILITY**: n=322, complexity=MEDIUM, risk=HIGH without dual authority, MAX_THEORETICAL_UPLIFT=322
  brands: INSIZE | اینسایز:258; Mitutoyo | میتوتویو:41; SAN OU | سانو:16; ASTPOWER | ای اس تی پاور:7
- **E_IMAGE_PLUS_AVAILABILITY**: n=217, complexity=MEDIUM-HIGH, risk=MEDIUM, MAX_THEORETICAL_UPLIFT=217
  brands: Dasqua | داسکوا:217
- **F_THREE_BLOCKERS**: n=184, complexity=HIGH, risk=HIGH, MAX_THEORETICAL_UPLIFT=184
  brands: see brand matrix three_blockers
- **G_FOUR_BLOCKERS**: n=1647, complexity=VERY HIGH, risk=VERY HIGH, MAX_THEORETICAL_UPLIFT=1647
  brands: see brand matrix four_blockers

## N. Tooling Gaps

- **availability_APPLY**: PARTIAL — INSIZE-only via scripts/insize_sales_activation.py (ALLOWED_APPLY_FIELDS={base_price,is_available}); generic sale_wave plan schema exists (data/templates/sale_wave_plan_schema.csv) with validate/map supplier stock CLIs, but no generic multi-brand owner-gated is_available APPLY path is registered as production-safe.
- **price_APPLY**: PARTIAL — INSIZE pilot APPLY exists; brand-specific TERMA/INSIZE workflows exist historically; no generic controlled multi-brand base_price APPLY for arbitrary sale waves.
- **activation_APPLY**: MISSING — is_active is in FORBIDDEN_APPLY_FIELDS for insize_sales_activation_lib.py; no generic controlled is_active activation tooling exists.
- **image_APPLY**: MISSING — no Wave-0-adjacent generic safe image-attachment APPLY for sale waves; image tooling is separate discovery/import planning.

## O. Proposed Wave 1 Scope

```text
candidate cohort: READY_EXCEPT_AVAILABILITY (ONLY_AVAILABILITY)
candidate count: 330
exact mutation field(s): is_available=true
authority required: CURRENT_ENOUGH or AGING_BUT_USABLE supplier stock
  authority with EXACT manufacturer SKU match; Hesabfa reconciliation
  where registered; brand allowlist starting with authority-ready brands
gates required:
  - production identity proof
  - read-only dry-run manifest
  - stock freshness class != STALE/UNKNOWN
  - no price/image/activation mutation in Wave 1
  - owner explicit WAVE_1_APPLY authorization
WAVE_1_APPLY_AUTHORIZED = NO
```

