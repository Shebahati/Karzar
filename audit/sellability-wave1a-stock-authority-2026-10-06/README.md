# Sellability Wave 1A — Stock Authority Reconciliation

Date: 2026-10-06  
Status: `PARTIAL_AUTHORITY`  
`WAVE_1B_APPLY_AUTHORIZED=NO`

## Safety

- Production mutation: **NO**
- Catalog APPLY: **NO**
- Hesabfa mutation: **NO**
- Deployment: **NO**
- Wave 1B APPLY: **NO**

## Entry gate

- `origin/main` = `4e5056de100c1f8ceb2900deac40ee8efb24216a` (PR #421 MERGED)
- Wave 0 `READY_EXCEPT_AVAILABILITY.csv` = 330 rows; SHA256 verified via Wave 0 `SHA256SUMS.txt`

## Identity

See [`IDENTITY_PROBE.json`](./IDENTITY_PROBE.json). Host `srv5944957438`, DB
`karzar_staging`, container `lathe_postgres`, volume `karzar_postgres_data`,
`transaction_read_only=on`.

## Artifacts

All files in this directory plus [`SHA256SUMS.txt`](./SHA256SUMS.txt).

## Policy

Re-derived from `docs/catalog/SUPPLIER_STOCK_AUTHORITY.md`, `docs/COMMERCE.md`,
`docs/HESABFA.md`. **PRICE ≠ AVAILABILITY.**
