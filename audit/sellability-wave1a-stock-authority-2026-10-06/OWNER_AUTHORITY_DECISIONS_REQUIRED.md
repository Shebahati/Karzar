# Owner Authority Decisions Required — Wave 1A

Wave 1A is read-only. No APPLY is authorized. The following Owner decisions are
required before any Wave 1B design can promote availability flips.

## 1. INSIZE distributor year for `11 شهریور`

Filename lacks year. Wave 1A resolved Jalali **1405-06-11 → 2026-09-02**
(age 34d → `AGING_BUT_USABLE`) from 2026 operational context + control fixture.
Confirm or correct the year. If year is 1404, freshness becomes STALE and zero
AGING candidates remain from that date.

## 2. INSIZE trailing-A identity rule

37 INSIZE targets lack exact workbook identity.
Approximately 36 additional SKUs would match only via an unregistered `SKU`↔`SKU-A`
heuristic. **Not used.** Owner must accept a registered deterministic rule before
those can leave UNKNOWN.

## 3. DASQUA / TERMA freshness for APPLY

- DASQUA in-PDF date 1405/02/12 → `2026-05-02` → `STALE` (>45d).
  Adapter can classify AVAILABLE, but freshness blocks `future_apply_candidate`.
- TERMA has Owner inventory adapter but **no parseable source_date** → freshness UNKNOWN.

## 4. ASTPOWER / SAN OU / Mitutoyo stock authority

No Owner-confirmed availability authority for these Wave 0 brands in the 330 cohort
(ASTPOWER price/catalog ≠ stock; SAN OU missing; Mitutoyo catalog-only).

## 5. Hesabfa Stock semantics

See `HESABFA_SEMANTICS_REPORT.md`. Observed Stock cannot authorize APPLY until
Owner defines sellable-quantity semantics.

## 6. Wave 1B APPLY authorization

`WAVE_1B_APPLY_AUTHORIZED = NO` until Owner signs an explicit Wave 1B design +
allowlist after the above.
