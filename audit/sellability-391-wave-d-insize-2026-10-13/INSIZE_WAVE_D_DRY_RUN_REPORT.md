# INSIZE Wave D dry-run report (#391)

**Snapshot UTC:** 2026-10-13T20:20:11Z
**Status:** `READY_FOR_OWNER_WAVE_D_APPLY_AUTHORIZATION`

## CI gate (PR #488)

- Expected HEAD: `10c2e53615aef70824be251a52d28340b06961ad`
- Actual HEAD: `10c2e53615aef70824be251a52d28340b06961ad`
- CI: `PASS` — all reported checks pass

## Source freshness

- SHA256: `beb549109165a1fd0d156af8d9b8a9622eb3a04e7fc92b07c548993ee98669cf` (verified: `True`)
- source_date: **2026-09-02** — Jalali 1405-06-11 (11 Shahrivar 1405) → Gregorian 2026-09-02 via independent calendar conversion; filename '11 شهریور' supplies month/day; year from Jalali 1405 campaign context. Workbook OOXML core modified 2026-09-03T13:20:55Z corroborates early-September snapshot (metadata reference only — not used as source_date or received_at).
- Age at execution: **41** days → **AGING_BUT_USABLE**

## Production recheck

- `transaction_read_only=on`
- Allowlist size: **10** (immutable)
- Production rows returned: **10**
- Production gate: **PASS**

## Source recheck

- Source gate: **PASS**
- Identity: governed EXACT / INSIZE_TRAILING_A_IDENTITY only
- Availability: `وضعیت` → AVAILABLE and `موجودی کل` > 5

## Price safety

- **No price APPLY.** Mutation scope: `is_available` false→true only.
- `8601-100`: source `قیمت دلاری` may be `#N/A`; non-blocking when site `base_price > 0`.

## Dry-run delta

| Metric | Value |
|--------|------:|
| Planned rows | 10 |
| Inserts | 0 |
| Deletes | 0 |
| Price changes | 0 |
| Activation changes | 0 |
| Image changes | 0 |
| Identity changes | 0 |
| Availability false→true | 10 |

## Sellable projection

- Before (fresh census): **717**
- Delta (if all gates pass): **+10**
- After: **727**

## Safety

```text
PRODUCTION_MUTATION=NO
DATABASE_MUTATION=NO
AVAILABILITY_APPLY=NO
PRICE_APPLY=NO
DEPLOYMENT=NO
```

## Blockers

- (none)
