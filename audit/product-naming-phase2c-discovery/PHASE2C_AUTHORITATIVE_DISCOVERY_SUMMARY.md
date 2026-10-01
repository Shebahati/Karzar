# Phase 2C Authoritative Discovery Summary

> **Coverage: LIVE_DB_AUTHORITATIVE** — live read-only SQL export.
> Historical `STALE_STATUS_MASTER_PARTIAL` artifacts remain for provenance only.

- Export SHA256: `067bd90c2e5710406814b657c75a095b11cee72510b4ac53795ce005b97b79ba`
- Rows: **6536**
- Reconciliation: **PASS**
- BACKFILL_EXACT: **1350** (Tier 1–3 registry only)

## Primary classification

- BACKFILL_EXACT: 1350
- MANUAL_REVIEW: 0
- HOLD_WEAK_EVIDENCE: 2741
- HOLD_IDENTITY_CONFLICT: 2142
- HOLD_MISSING: 0
- HOLD_BRAND_AMBIGUOUS: 295
- HOLD_DUPLICATE_IDENTITY: 8
- REVIEW_EXISTING_CANONICAL: 0

## Safety

- DISCOVERY ONLY — no APPLY
- manufacturer_code writes: **0**
- `--apply`: rejected

