# Issue #391 — INSIZE Wave A Final Report

**Status:** READY_FOR_OWNER_WAVE_D_ALLOWLIST_REVIEW  
**Snapshot UTC:** 2026-10-13T20:02:07Z  
**origin/main:** `4786f75dee175bbc72fa6a518927ffb12d3bccc4`  
**Strict unlock candidates:** 10  
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
| **Strict unlock** | **10** |

## Historical reproducibility (Wave A 2026-10-07)

| Metric | 2026-10-07 | Fresh |
|--------|----------:|------:|
| INSIZE cohort | 476 | 476 |
| Exact matched | 475 | 475 |
| AVAILABLE | 10 | 10 |
| UNAVAILABLE | 465 | 465 |
| NOT_FOUND | 1 | 1 |
| STRICT | 0 | 10 |

## SOURCE_SEMANTICS

- `وضعیت` → AVAILABLE/UNAVAILABLE; `موجودی کل` reported separately (not used to infer status).
- `source_date` **2026-09-02** → freshness **AGING_BUT_USABLE** (41 days); `SOURCE_AUTHORITY_VALID=YES`.
- Owner confirms workbook prices are final/current; this audit does **not** APPLY price changes.
- See [`SOURCE_SEMANTICS.json`](SOURCE_SEMANTICS.json).

## Price N/A vs AVAILABLE

1 cohort row(s) with source AVAILABLE but missing/`#N/A` `قیمت دلاری` — see [`INSIZE_PRICE_NA_AVAILABILITY_NOTE.md`](INSIZE_PRICE_NA_AVAILABILITY_NOTE.md) if present.

## Commercial delta

| Field | Value |
|-------|------:|
| SELLABLE_BEFORE | 717 |
| FINAL_SOURCE_AVAILABLE_STRICT_CANDIDATES | 10 |
| PROJECTED_SELLABLE_AFTER_WAVE_D | 727 |
| SOURCE_AVAILABLE_UPPER_BOUND | 727 |
| THEORETICAL_INSIZE_COHORT_UPPER_BOUND | 1193 |

Full detail: [`COMMERCIAL_DELTA.json`](COMMERCIAL_DELTA.json).

## Owner decision

**AUTHORIZE_WAVE_D_ALLOWLIST_REVIEW**
