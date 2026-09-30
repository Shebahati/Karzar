# Phase 2A — Manufacturer identity summary

**Status:** PARTIAL census (public/active snapshot; full non-deleted DB not available in this environment)  
**Generated from:** `scripts/audit_manufacturer_code_phase2a.py --force-snapshot`  
**Canonical column:** `products.manufacturer_code` (nullable, no backfill, no unique)

## Entry / safety

- PR #399 merged into main (`f47d421…`) — ancestor of Phase 2A base.
- Zero production/staging mutation.
- Zero product rename / SKU / slug / price / availability changes.
- Zero manufacturer_code backfill (`BACKFILL_EXACT = 0`).

## Schema

| Item | Value |
|------|-------|
| Column | `products.manufacturer_code` |
| Type | `String(255)` / `varchar(255)` |
| Nullable | YES |
| Unique | NO |
| Indexes | `ix_products_manufacturer_code` (non-unique); `ix_products_brand_id_manufacturer_code` (non-unique) |
| Alembic | `u4v5w6x7y8z9` |
| Local proof | upgrade → downgrade → re-upgrade → `alembic current = u4v5w6x7y8z9` |

## Census (PARTIAL — n=1368 public/active snapshot)

| Metric | Count |
|--------|------:|
| Total rows in snapshot | 1368 |
| Active | 1368 |
| Inactive | 0 |
| With Product Type (API-visible) | 0 |
| Canonical `manufacturer_code` populated | 0 |
| SOURCE_STRUCTURED_CANDIDATE | 175 |
| TITLE_CANDIDATE | 598 |
| SKU_ONLY_CANDIDATE | 193 |
| CONFLICT | 402 |
| MISSING | 0 |

Historical full-catalog scale (taxonomy Phase 0B read-only, dated): live ≈ 6536. Full DB census remains required before Phase 2C APPLY.

## Backfill readiness (candidates only)

| Action | Count |
|--------|------:|
| BACKFILL_EXACT | **0** |
| MANUAL_REVIEW | 394 |
| HOLD_WEAK_EVIDENCE | 572 |
| HOLD_IDENTITY_CONFLICT | 402 |
| HOLD_MISSING | 0 |
| HOLD_BRAND_AMBIGUOUS | 0 |

## Collisions

- Brand+candidate collision groups: 2 (includes historical **ASTPOWER / TU-DR230** — product ids 3411|3409).
- Reversed title vs SKU Order-No conflicts: **402** (Mitutoyo + INSIZE classes where `مدل A-B` disagrees with SKU `B-A`). OEM Order No. must outrank title/SKU heuristics in Phase 2C.

## API / engine

- Admin detail read: `manufacturer_code`, `product_type_id`.
- Storefront: left null.
- Create/Update: no write field; first canonical writer deferred to Phase 2C + `record_product_change`.
- Naming HIGH requires both `product_type_governed` and `manufacturer_code_governed`.

## Artifacts

- `FULL_PRODUCT_IDENTITY_CENSUS.csv`
- `MANUFACTURER_CODE_BACKFILL_CANDIDATES.csv`
- `MANUFACTURER_CODE_COLLISIONS.csv`
- `LEGACY_IDENTITY_FIELD_MATRIX.md`
- `IMPORTER_MANUFACTURER_CODE_MATRIX.md`
- `PHASE2A_SUMMARY.json`

## Next phase (Owner approval required)

**Phase 2B only** — naming engine hardening + search/admin preview.  
Do not start Phase 2C backfill without explicit Owner authorization.
