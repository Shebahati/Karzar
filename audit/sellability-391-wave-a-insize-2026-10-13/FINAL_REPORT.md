# Issue #391 — INSIZE Wave A Final Report

**Status:** BLOCKED_ON_FRESH_INSIZE_STOCK_AUTHORITY  
**Snapshot UTC:** 2026-10-13T19:26:59Z  
**origin/main:** `ab33f9183b4ae2f3c2c25defd3d5fb257aad63e4`  
**Strict unlock candidates:** 0  
**APPLY authorized:** NO

## Fresh census

| Metric | Count |
|--------|------:|
| Live | 6536 |
| Sellable | 717 |
| ONLY_AVAILABILITY | 580 |
| INSIZE ONLY_AVAILABILITY | 476 |

## INSIZE stock mapping (canonical workbook)

| Class | Count |
|-------|------:|
| Cohort | 476 |
| Exact matched | 475 |
| AVAILABLE (normalized) | 10 |
| UNAVAILABLE | 465 |
| UNKNOWN | 1 |
| **Strict unlock** | **0** |

## Historical reproducibility (Wave A 2026-10-07)

| Metric | 2026-10-07 | Fresh |
|--------|----------:|------:|
| INSIZE cohort | 476 | 476 |
| Exact matched | 475 | 475 |
| AVAILABLE | 10 | 10 |
| UNAVAILABLE | 465 | 465 |
| NOT_FOUND | 1 | 1 |
| STRICT | 0 | 0 |

## SOURCE_SEMANTICS

- `وضعیت` → AVAILABLE/UNAVAILABLE (quantity columns not used).
- Freshness **UNKNOWN** (`SOURCE_YEAR_UNPROVEN`); `SOURCE_AUTHORITY_VALID=NO` for strict APPLY.
- See [`SOURCE_SEMANTICS.json`](SOURCE_SEMANTICS.json).

## Commercial delta

See [`COMMERCIAL_DELTA.json`](COMMERCIAL_DELTA.json).

## Owner decision

**REQUEST_FRESH_INSIZE_STOCK_SOURCE**
