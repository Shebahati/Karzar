# Board agenda — Day 2 Knowledge Architecture Accept (draft for Owner)

**Session:** Day-2 Board block (from Day-1 Topic 2 prep)  
**Date proposed:** 2026-08-01 (or next Owner slot)  
**Attendees:** Mohammad Shebahati (Architecture Board / Owner) · Cursor (recorder)  
**Parents on `main`:** `docs/architecture/specs/**` (merged #168) · summary FA · Canon Lock / ADR-010 / ADR-012  
**Non-goal of this meeting:** writing code, CAT-002 QA, dual-write enablement, RAG

---

## 0. Opening (5 min)

**One-line frame:**  
Commerce SoR stays; knowledge is an overlay; no second storefront Category DAG; merge of SPECs ≠ Accept.

**Evidence already on `main`:**
- Pack path: `docs/architecture/specs/`
- Persian one-pager: `docs/architecture/specs/KNOWLEDGE_PLATFORM_ARCHITECTURE_SUMMARY_FA.md`
- Merge: PR #168 @ `7d7883a` (2026-08-01)

---

## 1. UD-06 — Canon Accept of SPEC pack (20 min) — CRITICAL

**Question:** Do we Accept the knowledge foundation + completion SPECs into Canon Lock as binding criteria for knowledge work?

| Option | Meaning | Consequence |
|--------|---------|-------------|
| **A — Accept pack** | Add Canon Lock rows for the SPEC pack (or named subset) | KB-001 IMPL may cite SPECs as merge criteria |
| **B — Accept subset only** | e.g. Entity + Taxonomy + KG registry + Playbook; defer seed/target/readiness | Narrower canon; less risk |
| **C — Keep Proposed** | Usable for planning only; not merge criteria | IMPL must wait or proceed only as non-Canon spike |

**Cursor recommendation:** **A** for the core SPECs; seed/audit/summary may stay REFERENCE/PROPOSED if Board wants thinner Canon.

**If A/B:** same commit must add Canon Lock rows + Board minute (AODS rule).

---

## 2. UD-05 — Edge/Fact storage (10 min)

| Option | Choice |
|--------|--------|
| **A (recommended)** | Postgres relational edge + fact tables only (Phase 2 overlay) |
| **B** | Postgres now + optional graph engine later (explicit non-goal for KB-001) |
| **C** | Defer — blocks DDL |

**Recommendation:** **A** (B as future note only).

---

## 3. UD-02 — PKE identity (10 min)

| Option | Choice |
|--------|--------|
| **A (recommended for wave-1)** | PKE link = `products.id` (1:1) |
| **B** | New UUID `knowledge_entity_id` from day one |
| **C** | Defer |

**Recommendation:** **A**; revisit 1:N SKU packs later.

---

## 4. UD-03 — Property Dictionary seed scope (5 min)

| Option | Choice |
|--------|--------|
| **A (recommended)** | Metrology only first |
| **B** | All L1 commerce domains at once |
| **C** | Defer dictionary entirely until after KB-001 edges |

**Recommendation:** **A**.

---

## 5. UD-08 — AI FA prose publish (5 min)

| Option | Choice |
|--------|--------|
| **A (recommended)** | Never auto-publish customer-facing FA AI prose |
| **B** | Auto-publish with banner |
| **C** | Defer policy |

**Recommendation:** **A**.

---

## 6. Explicit Defer block (5 min) — vote as a bundle

| ID | Topic | Proposed disposition |
|----|-------|----------------------|
| **UD-01** | Manufacturer ≠ Brand migration | **Defer** until after KB-001 edge slice |
| **UD-04** | Type/Application indexable hubs | **Defer** (ADR-010 facet risk) |
| **UD-07** | Move pack into reserved `domain/`/`pim/`/`knowledge-graph/` paths | **Defer** (keep `specs/` for now) |
| Dual-write JSONB↔Facts | Board gate separate | **Defer** |
| Generative RAG | Evidence≈0 | **Blocked** |

---

## 7. OI-KF-04 — Phase1–3 legacy docs (10 min)

`docs/KNOWLEDGE_PLATFORM_PHASE{1,2,3}_*.md` vs new `docs/architecture/specs/`.

| Option | Choice |
|--------|--------|
| **A (recommended)** | Supersede for planning: specs pack is the living Proposed/Accepted path; Phase docs = HISTORICAL/orientation |
| **B** | Separately Accept Phase 2 only |
| **C** | Leave unresolved (keeps agent confusion) |

**Recommendation:** **A** + short Canon/registry note.

---

## 8. KB-001 wave-1 scope freeze (10 min)

**In scope after Accept:**
- Project edges: `PRODUCT_BELONGS_TO_CATEGORY`, `PRODUCT_BRANDED_AS`, `ARTICLE_EXPLAINS_PRODUCT`
- Queryable read path + tests
- No second Category DAG

**Out of scope:**
- Full Property dual-write
- Public Application hubs
- Admin PIM suite
- RAG

Vote: **Freeze Yes/No**.

---

## 9. Close (5 min)

Produce:
1. Board minute (Jalali + Gregorian, signature, scope)
2. Canon Lock row updates if UD-06 = A/B
3. PMO note on KB-001 unblocked for IMPL planning / ADR drafting
4. Next engineering node: ADR storage + PKE identity (or combined thin ADR)

---

## Pre-filled recommended ballot (for fast meeting)

| Item | Vote |
|------|------|
| UD-06 | A — Accept core pack |
| UD-05 | A — Postgres tables |
| UD-02 | A — `products.id` |
| UD-03 | A — Metrology first |
| UD-08 | A — No AI auto-publish FA |
| UD-01/04/07 + dual-write + RAG | Defer / Blocked |
| OI-KF-04 | A — Supersede phases for living path |
| KB-001 scope freeze | Yes |

Owner may change any row in session; Cursor records final votes only.
