# Karzar Product Status Audit — Production Read-Only Snapshot — 2026-09-24

**STATUS:** `COMPLETE`  
**SNAPSHOT:** `2026-09-24T07:43:42Z`  
**PRODUCTION_IDENTITY_PROVEN:** `YES`  
**READ_ONLY_PROVEN:** `YES`  
**PRODUCTION_MUTATION:** `NO`

This directory is **immutable historical observational evidence** of a one-time
Production read-only product-status audit. Counts below describe the catalog
**as of the snapshot time**. Later repository, catalog, taxonomy, or KB changes
do **not** revise these figures and may make today's live numbers different.

## Safety

- This preservation PR performs **no** Production query and **no** Production mutation
- Original one-shot VPS workflow (`.github/workflows/product-status-audit-readonly.yml`)
  and historical audit script (`scripts/audit_product_status_production_readonly.py`)
  were **intentionally removed** and must not be restored as current tooling
- Do **not** treat this snapshot as today's live catalog state
- Report recommendations are **historical observations**, not APPLY authorization
- `audit recommendation ≠ owner approval`

## Historical headline metrics (snapshot fact)

| Metric | Value |
|--------|------:|
| Live products | 6536 |
| Soft deleted | 1 |
| Active | 1585 |
| Available | 3755 |
| Priced | 4552 |
| Imaged | 1464 |
| Visible | 1368 |
| Sellable | 716 |
| Brandless | 295 |
| Categoryless | 0 |
| Image rows | 1492 |
| Product Type assigned | 15 |
| KB facts present | 15 |
| Required KB complete | 15 |
| Required KB evidenced | 15 |
| Legacy specs present | 6455 |

## Authoritative entrypoints

| Artifact | Role |
|----------|------|
| [`KARZAR_PRODUCT_STATUS_REPORT_2026-09-24.md`](./KARZAR_PRODUCT_STATUS_REPORT_2026-09-24.md) | Human-readable historical report |
| [`SUMMARY.json`](./SUMMARY.json) | Machine-readable summary |
| [`IDENTITY_PROBE.json`](./IDENTITY_PROBE.json) | Production identity + read-only proof |
| [`KARZAR_PRODUCT_STATUS_MASTER_2026-09-24.csv`](./KARZAR_PRODUCT_STATUS_MASTER_2026-09-24.csv) | Full product census |
| [`KARZAR_COMMERCIAL_GAPS_2026-09-24.csv`](./KARZAR_COMMERCIAL_GAPS_2026-09-24.csv) | Commercial gap cohort |
| [`KARZAR_TECHNICAL_GAPS_2026-09-24.csv`](./KARZAR_TECHNICAL_GAPS_2026-09-24.csv) | Technical gap cohort |
| [`KARZAR_BRAND_STATUS_2026-09-24.csv`](./KARZAR_BRAND_STATUS_2026-09-24.csv) | Brand status rollup |
| [`SHA256SUMS.txt`](./SHA256SUMS.txt) | Integrity hashes for preserved artifacts |

## Does not authorize

- Product / price / availability / activation mutation
- Catalog APPLY
- Hesabfa mutation
- Production deploy
- Rerunning this audit as a current-state assertion
