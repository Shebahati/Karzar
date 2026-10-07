# Global Sellability Root-Cause Audit (2026-10-07)

Read-only Production audit: one root-cause matrix row per live Product.

**Verdict:** `SELLABLE_NOW = 717` / `NON_SELLABLE = 5819` / `LIVE = 6536`  
**APPLY authorized:** **NO**

## Start here

1. [`FINAL_REPORT.md`](FINAL_REPORT.md) — executive answers  
2. [`CODE_SELLABILITY_CONTRACT.md`](CODE_SELLABILITY_CONTRACT.md) — code vs audit definitions  
3. [`GLOBAL_SELLABILITY_ROOT_CAUSE_MATRIX.csv`](GLOBAL_SELLABILITY_ROOT_CAUSE_MATRIX.csv) — per-product map  
4. [`REMEDIATION_WAVE_PLAN.md`](REMEDIATION_WAVE_PLAN.md) — designed waves only  

## Safety

```text
PRODUCTION_MUTATION = NO
DATABASE_MUTATION = NO   (transaction_read_only=on)
HESABFA_MUTATION = NO
DEPLOYMENT = NO
```

Identity: [`PRODUCTION_IDENTITY.json`](PRODUCTION_IDENTITY.json)

## Key cohorts

| Cohort | Count | File |
|--------|------:|------|
| CURRENT_ONLY_AVAILABILITY | 580 | `CURRENT_ONLY_AVAILABILITY.csv` |
| CURRENT_ONLY_ACTIVE/PRICE/IMAGE | 0 | header-only CSVs |
| Immediate evidence-complete unlocks | 0 | `IMMEDIATE_SELLABILITY_UNLOCK_CANDIDATES.csv` |
| Historical Wave 0 READY_EXCEPT_AVAILABILITY | 330 | `HISTORICAL_330_RECONCILIATION.csv` |

## Integrity

- Universe freeze SHA-256: `PRODUCT_UNIVERSE_FREEZE.sha256`  
- All artifact hashes: `SHA256SUMS.txt`  
- Blocker/root-cause math: `ROOT_CAUSE_RECONCILIATION.md`  
- Historical deltas: `HISTORICAL_RECONCILIATION.md`

## Out of scope

No Product/availability/price/image/Hesabfa mutation. No Wave 1B. No deploy.
