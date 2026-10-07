# Sellability Wave A — Stock Authority (2026-10-07)

Read-only construction of future availability APPLY candidates for the frozen **580** CURRENT_ONLY_AVAILABILITY cohort from merged Global Root-Cause Audit (#461).

```text
STRICT_AVAILABLE_CANDIDATES = 0
SELLABILITY_APPLY_AUTHORIZED = NO
```

## Start here

1. [`FINAL_REPORT.md`](FINAL_REPORT.md)  
2. [`INSIZE_WAVE_A_SUMMARY.md`](INSIZE_WAVE_A_SUMMARY.md)  
3. [`STOCK_SOURCE_ACQUISITION_REQUESTS.csv`](STOCK_SOURCE_ACQUISITION_REQUESTS.csv)  
4. [`WAVE_A_STOCK_AUTHORITY_MATRIX.csv`](WAVE_A_STOCK_AUTHORITY_MATRIX.csv) (580 rows)

## Safety

```text
PRODUCTION_MUTATION = NO
DATABASE_MUTATION = NO   (transaction_read_only=on)
HESABFA_MUTATION = NO
AVAILABILITY_APPLY = NO
DEPLOYMENT = NO
```

## Headline

| Metric | Value |
|--------|------:|
| Frozen cohort | 580 |
| Still ONLY_AVAILABILITY (live) | 580 |
| Strict APPLY candidates | 0 |
| Aging review AVAILABLE | 0 |
| Authoritative UNAVAILABLE (matched) | 468 |
| Normalized AVAILABLE (non-strict) | 18 |

Primary blocker: **no CURRENT_ENOUGH dated stock authority**. INSIZE workbook semantics are clear but year/date unproven; Dasqua adapter source is STALE (2026-05-02).

## Out of scope

No `is_available` APPLY, no price/image/active mutation, no Wave D execution, no Hesabfa writes.
