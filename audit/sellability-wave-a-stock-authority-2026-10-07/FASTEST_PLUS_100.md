# Fastest +100 Sellable — Wave A evidence

## Can we safely produce +100 Sellable now?

```text
NO
```

## Strict candidates available

```text
0
```

No product in the frozen 580 meets all strict gates:

`CURRENT_ENOUGH` + `SOURCE_AUTHORITY_VALID=YES` + exact identity + `AVAILABLE` + still ONLY_AVAILABILITY live gates.

## Blocker

| Brand | Near-miss | Blocker |
|-------|----------:|---------|
| INSIZE | 10 exact AVAILABLE | `SOURCE_YEAR_UNPROVEN` → freshness UNKNOWN |
| DASQUA | 8 adapter AVAILABLE | source_date 2026-05-02 → **STALE** (>45d) |
| Others | 0 AVAILABLE | no stock authority / price-only / catalog-only |

## Owner aging exception?

```text
YES_IF_OWNER_ACCEPTS_AGING_SOURCE
```

does **not** apply to INSIZE (UNKNOWN, not AGING) or DASQUA (STALE, not AGING).

Aging review candidates this Wave: **0**.

## What would unlock +100

A fresh **INSIZE** stock export with proven `source_date` ≤14 days that classifies ≥100 of the 476 cohort SKUs as موجود under exact/trailing-A identity.
