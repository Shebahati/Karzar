# Phase 2C Authoritative Discovery Summary

> **Coverage: LIVE_DB_AUTHORITATIVE** — live read-only SQL export (`karzar_staging`, 6536 non-deleted).
> Historical `STALE_STATUS_MASTER_PARTIAL` artifacts (2026-09-24 status master) remain for provenance only.

## Live export

- Path: `/tmp/karzar-p2c-live-products.csv` (manifest: `LIVE_EXPORT_MANIFEST.json`)
- SHA256: `067bd90c2e5710406814b657c75a095b11cee72510b4ac53795ce005b97b79ba`
- Rows: **6536** (matches live `deleted_at IS NULL` count)
- Read-only proof: `transaction_read_only=on` (`LIVE_DB_BASELINE.json`)

## Existing canonical `manufacturer_code`

- Live non-null: **0** (column unset on all non-deleted products)
- `REVIEW_EXISTING_CANONICAL_LIVE.csv`: empty

## Primary classification (live)

| State | Count |
|-------|------:|
| BACKFILL_EXACT | 1737 |
| HOLD_WEAK_EVIDENCE | 2407 |
| HOLD_IDENTITY_CONFLICT | 2089 |
| HOLD_BRAND_AMBIGUOUS | 295 |
| HOLD_DUPLICATE_IDENTITY | 8 |
| MANUAL_REVIEW | 0 |
| HOLD_MISSING | 0 |
| REVIEW_EXISTING_CANONICAL | 0 |

**Reconciliation:** PASS (6536 = sum)

## BACKFILL_EXACT cohort (owner review; not applied)

- Artifact: `BACKFILL_EXACT_LIVE.csv`
- SHA256: `38fbeee64bdb8f4b14a38dfe80937bf46f247b28344b2608889cc08e5efdf64d`
- Tier 1: 817 | Tier 2: 882 | Tier 3: 38
- Top brands: INSIZE (817), Dasqua (640), TERMA (242), ASTPOWER (38)
- All rows carry Tier 1–3 `SOURCE_AUTHORITY_REGISTRY.csv` linkage + source SHA256

## Source authority

- Root: `/home/shebahati/KaZar/Product and Data Complete`
- Registry rows (Tier 1–3): 2316 (`SOURCE_AUTHORITY_REGISTRY.csv`)
- File hashes: `SOURCE_HASHES.sha256`

## Safety

- **DISCOVERY ONLY — NO APPLY**
- manufacturer_code writes: **0**
- `--apply`: rejected (discovery script)

## Machine-readable

- `PHASE2C_AUTHORITATIVE_DISCOVERY.json`
- `*_LIVE.csv` classification shards
