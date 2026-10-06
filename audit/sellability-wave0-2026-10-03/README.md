# Karzar Sellability Wave 0 — Production Read-Only Census — 2026-10-03

**STATUS:** `COMPLETE`  
**SNAPSHOT:** `2026-10-03T09:57:14Z`  
**PRODUCTION_IDENTITY_PROVEN:** `YES`  
**READ_ONLY_PROVEN:** `YES`  
**PRODUCTION_MUTATION:** `NO`

This directory is **immutable observational evidence** of a one-time Production
read-only sellability census. Counts describe the catalog **as of the snapshot
time**. Later repository or catalog changes do **not** revise these figures.

## Safety

```text
PRODUCTION_MUTATION = NO
HESABFA_MUTATION = NO
DEPLOYMENT = NO
CATALOG_APPLY = NO
WAVE_1_APPLY_AUTHORIZED = NO
```

- Original one-shot VPS workflow (`.github/workflows/sellability-wave0-census-readonly.yml`)
  and execution script (`scripts/audit_sellability_wave0_production_readonly.py`)
  were **intentionally removed** after evidence capture and must not be restored
  as current tooling
- Do **not** treat this snapshot as today's live catalog after further mutations
- Report recommendations are **observations**, not APPLY authorization
- `audit recommendation ≠ owner approval`

## Headline metrics (snapshot fact)

| Metric | Value |
|--------|------:|
| Live products | 6536 |
| Active | 1585 |
| Available | 3755 |
| Priced | 4552 |
| Imaged | 1464 |
| Visible | 1368 |
| Sellable | 716 |
| Non-sellable | 5820 |

All commercial headline metrics are **identical** to the prior proven snapshot
`audit/product-status-2026-09-24/` (2026-09-24T07:43:42Z). Delta = 0 across
live/active/available/priced/imaged/visible/sellable and all blocker cohorts
recomputed in this Wave 0 run.

## Authoritative entrypoints

| Artifact | Role |
|----------|------|
| [`FINAL_REPORT.md`](./FINAL_REPORT.md) | Human-readable Wave 0 report |
| [`SUMMARY.json`](./SUMMARY.json) | Machine-readable summary |
| [`IDENTITY_PROBE.json`](./IDENTITY_PROBE.json) | Production identity + read-only proof |
| [`KARZAR_SELLABILITY_MASTER.csv`](./KARZAR_SELLABILITY_MASTER.csv) | Full live product census |
| [`KARZAR_COMMERCIAL_BLOCKERS.csv`](./KARZAR_COMMERCIAL_BLOCKERS.csv) | Non-sellable blocker rows |
| [`KARZAR_BRAND_SELLABILITY.csv`](./KARZAR_BRAND_SELLABILITY.csv) | Brand commercial matrix |
| [`READY_EXCEPT_AVAILABILITY.csv`](./READY_EXCEPT_AVAILABILITY.csv) | Near-sellable (availability only) |
| [`SHA256SUMS.txt`](./SHA256SUMS.txt) | Integrity hashes |

## Does not authorize

- Product / price / availability / activation / image mutation
- Catalog APPLY
- Hesabfa mutation
- Production deploy
- Wave 1 sale activation
