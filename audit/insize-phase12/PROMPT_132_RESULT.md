# PROMPT 132 RESULT — Compact change_reason contract for equivalent-facts

**STATUS:** READY_FOR_COMPACT_POLICY_MERGE  
**DATE:** 2026-09-26  
**MODE:** Governance / repository change only — **no** Live KB mutation  
**Branch:** `docs/kb-equivalent-facts-compact-reason`  
**Base:** `origin/main` @ `283f4f9dfb9b61c869de60f88bbac60e30685d33`

## PROBLEM

Prompt 131 pilot (1183-150) initially failed assignment because a long narrative `change_reason` exceeded `product_change_logs.reason` **varchar(255)**. Wave fields allow up to 4000 chars, but assignment uses the 255 limit.

## DECISION

Do **not** migrate / widen the column.

Define a compact structured runtime contract **≤255** characters, with recoverability spread across three layers:

| Layer | Role |
|-------|------|
| 1 Runtime `change_reason` | Compact operational index (`EQF …`) |
| 2 Evidence locator | Full `model_candidates` + `identity_state` + page/property |
| 3 Audit artifact | Full A–F / exclusion forensic reasoning |

Amended: `docs/architecture/PRODUCT_IDENTITY_EQUIVALENCE_POLICY.md` §8.

## RUNTIME LIMIT

| Field | Value |
|------|--------|
| change_reason type (assignment path) | `varchar(255)` (`product_change_logs.reason`) |
| Wave schema allowance | up to 4000 (still use compact form) |
| Migration required | **NO** |

## CONTRACT

```text
EQF sku=<db_sku> id=<product_id> cand=<suffix_set> pt=<PT_CODE> def=<id>v<ver> req=equal audit=<short_ref>
```

Required semantic fields preserved: identity state (`EQF`), DB SKU, product_id, residual candidates, PT, Definition pin, required-Facts equality, audit ref.

`cand=A|AWL` is suffix-only; full OEM codes remain in Evidence `model_candidates`.

## PILOT (1183-150)

```text
EQF sku=1183-150 id=1834 cand=A|AWL pt=POINT_CALIPER def=6v1 req=equal audit=P126/P130
```

| Metric | Value |
|--------|------:|
| Character count | **86** |
| UTF-8 bytes | 86 |
| Fits 255 | **YES** |

## REMAINING COHORT (12 + pilot = 13)

All compact reasons from Prompt 126 equivalent-facts set:

| Count | Value |
|------:|-------|
| Products | 13 |
| All ≤255 | **YES** |
| Longest | 1123-150 → **102** chars (`INSIDE_KNIFE_EDGE_CALIPER` + `def=pending`) |
| Shortest (runtime-ready) | 1183-150 → 86 |

Planning rows with `def=pending` are **planning-only**; runtime must substitute real Definition id/version after PT create.

Matrix: [`EQUIVALENT_FACTS_CHANGE_REASON_MATRIX.csv`](./EQUIVALENT_FACTS_CHANGE_REASON_MATRIX.csv).

## FILES

| Path | Change |
|------|--------|
| `docs/architecture/PRODUCT_IDENTITY_EQUIVALENCE_POLICY.md` | §8 three-layer + compact encoding + no-migration |
| `audit/insize-phase12/EQUIVALENT_FACTS_CHANGE_REASON_MATRIX.csv` | Compact reasons for 13 SKUs |
| `audit/insize-phase12/PROMPT_132_RESULT.md` | This result |
| `aods/registry/document-registry.yaml` | Register PROMPT_132 |

## VALIDATION

| Gate | Result |
|------|--------|
| AODS full (registry / links / naming / ingestion-boundary) | **PASS** |
| OpenAPI | SKIP locally (unchanged API surface) |


## SAFETY

DB / Wave / Product / Fact / Evidence writes: **NONE**  
Migration: **NO** · Deploy: **NO** · Ingestion of remaining 12: **NOT STARTED**

## VERDICT

**READY_FOR_COMPACT_POLICY_MERGE**

STOP.
