# TASK-RECORD · KB-PT-00B

| Field | Value |
|-------|-------|
| Task ID | KB-PT-00B |
| Title | Record Board clarification for Hybrid Product Type architecture |
| Change class | C5 — Governance-affecting |
| Role executed as | R-SYS-ARCH (recording Board decision supplied by human) |
| Base | `origin/main` @ PR #193 Product Type contract |
| Branch | `docs/adr-015-board-clarification` |
| Attempts | 2 (draft pending → Board Option A recorded) |
| Outcome | COMPLETE — Board Option A Accepted; KB-PT-01 may start after merge |

## Human Board decision (supplied in Cursor — not fabricated)

| Field | Value |
|-------|-------|
| Decision | **Option A — Accept Hybrid clarification** |
| Conditions | None beyond normative constraints in the minute |
| Meeting | `AB-ADR-015-2026-08-02` |
| Board | Karzar Architecture Board |
| Attendees | محمد شباهتی — Mohammad Shebahati (sole member) |
| Quorum | Satisfied |
| Signatory | محمد شباهتی — Mohammad Shebahati |
| Date Gregorian | 2026-08-02 |
| Date Jalali | ۱۴۰۵/۰۵/۱۱ (1405-05-11) |

## Conflict clarified

Primary Wave-1 `products.product_type_id` vs Accepted taxonomy `PRODUCT_CLASSIFIED_AS`-centric wording → **Hybrid**: FK primary; CLASSIFIED_AS secondary; same Product Type identity.

## Minute path

`aods/90-governance/BOARD-MINUTE-ADR-015-HYBRID-PRODUCT-TYPE-CLARIFICATION.md` — **Accepted** v1.0.0

## Files changed (acceptance pass)

- Board minute (Accepted)
- ADR-015 → **Accepted** + Board Acceptance block
- `docs/architecture/CANON-LOCK.md` §1d
- `SPEC-industrial-taxonomy-model.md` v0.1.1 §7.1
- Master KB §12.1 KB-PT-01 unblocked
- SPEC-canonical-product-type-model (gate/status honesty; remains Proposed)
- Registry (ADR-015 + minute CANON/accepted; SPEC remains PROPOSED)
- PMO KB-PT-00B done/100
- ADR README

## Registry transitions

| ID | Before | After |
|----|--------|-------|
| ADR-015 | PROPOSED/proposed | **CANON/accepted** |
| BOARD-MINUTE-ADR-015-HYBRID-PT | PROPOSED/proposed | **CANON/accepted** (`on_main=false` until merge) |
| SPEC-CANONICAL-PRODUCT-TYPE | PROPOSED | PROPOSED (unchanged class) |
| SPEC-TAXONOMY-MODEL | CANON/accepted | CANON/accepted (notes §7.1) |

## ADR / Canon / Master KB

| Artifact | Status |
|----------|--------|
| ADR-015 | **Accepted** |
| Product Type SPEC | **Proposed** (under Accepted ADR-015) |
| Industrial Taxonomy | **Accepted** + §7.1 Hybrid amendment |
| CANON-LOCK | ADR-015 + minute rows added |
| Master KB gate | **KB-PT-01 may start** after merge |

## Exact next step

Human commit/PR/merge of `docs/adr-015-board-clarification`, then:

**KB-PT-01 — Product Type core table and nullable Product FK**
