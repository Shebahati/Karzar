# Board Minute — Knowledge Foundation Canon Accept (Day 2)

**Document ID:** `BOARD-MINUTE-KNOWLEDGE-FOUNDATION-ACCEPT-2026-08-01`  
**Document type:** Board minute / acceptance evidence  
**Status:** **Accepted** (this *is* the minute)  
**Version:** 1.0.0  
**Date (Gregorian):** 2026-08-01  
**Date (Jalali):** ۱۴۰۵/۰۵/۱۰ (۱۰ مرداد ۱۴۰۵)  
**Board:** Architecture Board  
**Signed:** Mohammad Shebahati / محمد شباهتی  
**Recorder:** Cursor  
**Parents:** Day-1 Topic 2 agenda + Owner vote A (`aods/reports/tasks/GOV-2026-08-01-day1-topic2-board-agenda.md`, `…-day1-topic2-session.md` §D) · Owner order «روز ۱ بسته + روز ۲ الان»

---

## Decision

**Accept the knowledge foundation core SPEC pack into Canon Lock as binding criteria for knowledge-platform work**, and record the Day-2 ballot below.

| Field | Value |
|-------|-------|
| **Decision ID** | Knowledge Wave — Day-2 Board Accept |
| **Outcome** | **Accepted** (core pack) + storage/identity ADRs |
| **Effective** | Upon merge of the acceptance commit to `main` |
| **Does not authorize** | Knowledge DDL/API without citing Accepted SPECs + ADR-013/014; dual-write; RAG; production enrichment (ADR-012 unchanged) |

---

## Ballot (final)

Authority: Owner accepted the recommended ballot on Day-1 Topic 2 (vote **A**, 2026-08-01) and ordered Day-2 execution the same day.

| Item | Vote | Disposition |
|------|------|-------------|
| **UD-06** Canon Accept | **A** | Accept **core** SPEC pack (listed below). Seed / audit / target / readiness / FA summary remain **Proposed / REFERENCE** (not merge criteria alone). |
| **UD-05** Edge/Fact storage | **A** | Postgres relational edge + fact tables only (Phase 2 overlay). Optional graph engine = explicit non-goal for KB-001. → **ADR-013** |
| **UD-02** PKE identity | **A** | Wave-1 PKE link = `products.id` (1:1). Revisit 1:N SKU packs later. → **ADR-014** |
| **UD-03** Dictionary seed | **A** | Metrology / Measurement domain first |
| **UD-08** AI FA prose | **A** | Never auto-publish customer-facing FA AI prose |
| **UD-01** Manufacturer ≠ Brand migration | **Defer** | After KB-001 edge slice |
| **UD-04** Type/Application hubs | **Defer** | ADR-010 facet risk |
| **UD-07** Promote to reserved `domain/`/`pim/`/`knowledge-graph/` | **Defer** | Keep living path under `docs/architecture/specs/` |
| Dual-write JSONB↔Facts | **Defer** | Separate Board gate |
| Generative RAG | **Blocked** | Evidence≈0 |
| **OI-KF-04** Phase1–3 docs | **A** | Supersede for living planning path: `docs/architecture/specs/` (+ this minute’s Accepted set) wins; Phase docs = **HISTORICAL / orientation** |
| **KB-001 scope freeze** | **Yes** | Only projection edges: `PRODUCT_BELONGS_TO_CATEGORY`, `PRODUCT_BRANDED_AS`, `ARTICLE_EXPLAINS_PRODUCT` + queryable read path + tests; no second Category DAG |

---

## Scope accepted (Canon Lock rows)

| Document | Path |
|----------|------|
| Knowledge Foundation Specs Pack (index) | `docs/architecture/specs/README.md` |
| Product Knowledge Entity Model | `docs/architecture/specs/SPEC-product-knowledge-entity-model.md` |
| Industrial Taxonomy Model | `docs/architecture/specs/SPEC-industrial-taxonomy-model.md` |
| Knowledge Graph Model | `docs/architecture/specs/SPEC-knowledge-graph-model.md` |
| Product Import & Enrichment Playbook | `docs/architecture/specs/SPEC-product-import-enrichment-playbook.md` |
| Domain Model | `docs/architecture/specs/SPEC-domain-model.md` |
| Property Dictionary System | `docs/architecture/specs/SPEC-property-dictionary-system.md` |
| Knowledge Graph Registry | `docs/architecture/specs/SPEC-knowledge-graph-registry.md` |
| Data Transformation Architecture | `docs/architecture/specs/SPEC-data-transformation-architecture.md` |
| ADR-013 — Knowledge Edge/Fact Storage | `docs/architecture/adr/ADR-013-knowledge-edge-fact-storage.md` |
| ADR-014 — Product Knowledge Entity Identity | `docs/architecture/adr/ADR-014-product-knowledge-entity-identity.md` |

**Explicitly not Accepted by this minute** (remain Proposed / REFERENCE / evidence):

- `SPEC-industrial-taxonomy-master-seed.md`
- `FULL_PLATFORM_ARCHITECTURE_AUDIT.md`
- `FOUNDATION_ARCHITECTURE_REVIEW.md`
- `KNOWLEDGE_PLATFORM_TARGET_ARCHITECTURE.md`
- `FOUNDATION_IMPLEMENTATION_READINESS.md`
- `KNOWLEDGE_PLATFORM_ARCHITECTURE_SUMMARY_FA.md`
- `docs/KNOWLEDGE_PLATFORM_PHASE{1,2,3}_*.md` (superseded for living path — historical)

---

## Canon Lock instruction

In the **same commit** as status upgrades:

1. Add Board Acceptance block **Knowledge Foundation (Day 2)** to `docs/architecture/CANON-LOCK.md`.
2. Add Accepted rows for every path in “Scope accepted” above.
3. Update §3 “Explicitly NOT locked” so Domain / KG / Property rows no longer claim “not in this repo” for the Accepted SPEC paths (seed/target packs may remain Proposed).

---

## Consequences for engineering

**Unblocked (planning / IMPL prep citing Canon):**

- KB-001 wave-1: three projection edges + queryable read + tests
- Property Dictionary **metrology-first** seed design (Facts dual-write still gated)
- ADR-013/014 cited on knowledge storage/identity PRs

**Still forbidden / blocked:**

- Second storefront Category DAG
- Dual-write JSONB↔Facts without separate Board gate
- Generative RAG
- AI auto-publish of customer-facing FA prose
- Category A production enrichment (ADR-012)
- Inventing reserved ADR-001…009/011 text; this minute adds **new** ADR-013/014 only

---

## Evidence

- This file
- Day-1 close: `aods/reports/tasks/GOV-2026-08-01-day1-close.md`
- Day-1 Topic 2 vote A (recommended ballot)
- SPEC + ADR status flips + Canon Lock rows in the acceptance commit
- Registry class/status updates for Accepted paths
- Phase1–3 supersession banners (OI-KF-04)
