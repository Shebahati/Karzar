# Karzar Taxonomy Phase 0B — Production Read-Only Census

**Snapshot:** `2026-09-27T10:06:26Z`  
**Historical status:** `COMPLETE`  
**Evidence class:** Immutable historical observation — **not** current live state  

This directory is **immutable historical evidence** of a one-time Production read-only taxonomy census. Counts below describe the catalog **as of the snapshot time**. Later repository or catalog changes do **not** revise these figures.

## Safety

- Production mutation: **NO**
- Transaction proven read-only: `transaction_read_only=on` (see `IDENTITY_PROBE.json`, `00-db-identity.txt`)
- No catalog / taxonomy / Hesabfa APPLY was performed
- Original one-shot VPS workflow and census script are **intentionally not retained** on `main`
- Do **not** rerun this historical audit as a current-state assertion

## Key historical counts (snapshot fact)

| Metric | Value |
|--------|------:|
| Live products | 6536 |
| Categories | 138 |
| L1 / L2 / L3 | 15 / 81 / 42 |
| Visible / Sellable | 1368 / 716 |
| Product Types | 37 |
| PT-assigned products | 527 |
| PT-missing products | 6009 |
| PT coverage | 8.063% |
| Knowledge Taxonomy nodes | 0 |
| Knowledge classification assignments | 0 |
| Hesabfa category codes populated | 0 / 138 |
| Megamenu groups | 6 |
| L1 represented exactly once | 15 / 15 |

## Major findings (historical)

- Numeric category IDs **33** and **34** were missing at snapshot but still referenced by **ACTIVE_IMPORT** paths
- Commerce Category stable semantic ID/code was **absent** at snapshot
- Product Type coverage was low (**8.063%**)
- Knowledge Taxonomy was empty (**0** nodes / **0** assignments)
- Hesabfa category mapping was absent (**0 / 138**)
- Megamenu structure: **15 / 15** L1 represented exactly once

## Authoritative entrypoints

| Artifact | Role |
|----------|------|
| [`14-phase0b-final-report.md`](./14-phase0b-final-report.md) | Human-readable Phase 0B result + artifact SHA-256 registry |
| [`SUMMARY.json`](./SUMMARY.json) | Machine-readable summary |
| [`IDENTITY_PROBE.json`](./IDENTITY_PROBE.json) | Production identity + read-only proof |
| `00`–`13` / CSVs | Detailed census tables |

## Relation to Taxonomy Phase 1A / 1B

This evidence informed Phase 1A Steward Freeze (PR #394) and supports Phase 1B **design drafting** only.

It does **not** authorize:

- Production Category mutation
- product reassignment / deletion
- taxonomy APPLY
- megamenu Production APPLY
- Product Type reassignment
- migration or deploy

Phase 1B gate (from merged Constitution pack): design drafting **YES** · Production APPLY **NO** · Auto-start **NO**.
