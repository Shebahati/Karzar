# KARZAR SELLABILITY — WAVE A STOCK AUTHORITY FINAL REPORT

**Status:** COMPLETE (read-only)  
**Entry:** PR #461 MERGED @ `1451b8e42406ba93704a891f5edde74f370a5497`  
**Branch:** `audit/sellability-wave-a-stock-authority`  
**Live snapshot UTC:** 2026-10-07T12:26:26Z  
**transaction_read_only:** on  
**SELLABILITY_APPLY_AUTHORIZED:** **NO**  
**STRICT_AVAILABLE_CANDIDATES:** **0**

---

## Verdict

Wave A **cannot** safely unlock sellability from evidence already on disk.

- INSIZE distributor workbook has clear `وضعیت` semantics and 475/476 exact governed matches, but **source year/date remains UNPROVEN** → freshness UNKNOWN → not strict.  
- DASQUA Owner-adapter PDF is authority-valid but **STALE** (source_date 2026-05-02).  
- ASTPOWER / SAN OU / Mitutoyo lack stock authority (price/catalog only).  
- TERMA adapter exists but source_date UNPROVEN; exclusions remain.  
- Hesabfa `last_stock` mapped for 478/580 but semantics **UNPROVEN** → not used.

**Next step:** acquire prioritized fresh supplier stock sources (`STOCK_SOURCE_ACQUISITION_REQUESTS.csv`). Do **not** start Wave D.

---

## Cohort freeze & drift

| Metric | Count |
|--------|------:|
| Frozen ONLY_AVAILABILITY | 580 |
| Still ONLY_AVAILABILITY (live RO) | 580 |
| Became sellable | 0 |
| New blocker | 0 |
| Deleted | 0 |
| Identity drift | 0 |

Lineage: **329** HISTORICAL_330_MEMBER + **251** NEW_ONLY_AVAILABILITY_SINCE_WAVE0 (329+251=580; 1 of historical 330 is outside this 580 — already sellable since baseline).

## Brands

| Brand | Cohort |
|-------|-------:|
| INSIZE | 476 |
| ASTPOWER | 53 |
| SAN OU | 24 |
| DASQUA | 22 |
| TERMA | 4 |
| Mitutoyo | 1 |

## Normalized results (580)

| Class | Count |
|-------|------:|
| AVAILABLE | 18 |
| UNAVAILABLE | 468 |
| UNKNOWN | 94 |
| CONFLICT | 0 |
| **Total** | **580** |

AVAILABLE breakdown: INSIZE 10 + DASQUA 8 (none CURRENT_ENOUGH).

## Strict / aging

| Set | Count |
|-----|------:|
| STRICT_AVAILABLE_CANDIDATES | 0 |
| AGING_AVAILABLE_REVIEW | 0 |
| Future Wave D design eligible | NO (candidate count 0) |
| Mutation performed | NO |

## +100 / +500

| Question | Answer |
|----------|--------|
| +100 now? | **NO** (strict=0) |
| +500 now? | **NO** (strict=0) |
| After acquisition | up to +580 theoretical; INSIZE fresh dated export is the +100/+500 path |

## Hesabfa

| Field | Value |
|-------|-------|
| Queried | YES |
| Exact mapped | 478 |
| Stock semantics | UNPROVEN |
| Usable as availability authority | **NO** |

## Historical 330 crosscheck

| Outcome | Count |
|---------|------:|
| Total historical membership | 330 |
| In current 580 | 329 |
| Now sellable (in this live probe) | 0 of the 329 |
| Strict AVAILABLE | 0 |
| Aging AVAILABLE | 0 |
| Authoritative UNAVAILABLE | 218 |
| UNKNOWN / source-required oriented | 94+ |

## Source acquisition priorities

1. INSIZE — fresh dated inventory (CODE + وضعیت + source_date) — 476  
2. ASTPOWER — stock list (not price PDF) — 53  
3. SAN OU — stock authority ≠ price list — 24  
4. DASQUA — refresh inventory (current PDF STALE) — 22  
5. TERMA — dated inventory — 4  
6. Mitutoyo — supplier stock — 1  

## Artifacts

Directory: `audit/sellability-wave-a-stock-authority-2026-10-07/`  
Authority matrix rows: 580  
Strict candidate rows: 0  
See `SHA256SUMS.txt`.
