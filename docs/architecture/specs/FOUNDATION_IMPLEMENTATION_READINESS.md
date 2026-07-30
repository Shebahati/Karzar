---
id: FOUNDATION-IMPLEMENTATION-READINESS
version: 0.1.0
status: Proposed
date: 2026-07-30
governing_parents:
  - docs/architecture/specs/FULL_PLATFORM_ARCHITECTURE_AUDIT.md
  - docs/architecture/specs/FOUNDATION_ARCHITECTURE_REVIEW.md
  - docs/architecture/CANON-LOCK.md
owner: Principal Software Architect
task_id: KB-001
---

# Foundation Implementation Readiness

**Status:** Proposed  
**Question:** After the Knowledge Foundation + this completion pack, can engineering **safely** implement each layer?  
**Answer shape:** Ready / Ready with gates / Not ready — with explicit missing items.

---

## 1. Executive readiness scorecard

| Workstream | Ready to implement? | Gate |
|------------|---------------------|------|
| Logical architecture / planning | **Yes** | Treat docs as Proposed until Board Accept |
| Database models (knowledge tables) | **Ready with gates** | Board Accept SPECs (UD-06) + storage ADR (UD-05) + no dual-write without Property gate |
| API layer (`/knowledge/*`) | **Ready with gates** | Same + OpenAPI additive contract RFC |
| Admin knowledge management | **Ready with gates** | Property steward roles; UD-01 Manufacturer |
| Import pipeline formalization | **Ready with gates** | Keep ADR-012; maps in Git; no prod Category A |
| AI agents (enrichment assist) | **Partial** | Allow suggest/draft only; Evidence≈0 blocks generative RAG |
| SEO entity pages (new hubs) | **Not ready** for Type/Application hubs | UD-04 + thin-content policy; EPIC-1 hubs already shippable/shipped |
| KB-001 graph seed (minimal) | **Ready with gates** | Registry subset + edge storage decision; no second Category DAG |

**Bottom line:** Engineering may **plan and spike behind feature flags** using these SPECs, but **must not** treat them as Canon Lock merge criteria until Board Accept. Schema PRs need explicit ADR/RFC Accepted for storage choices.

---

## 2. Document coverage checklist

| Need | Document | Status |
|------|----------|--------|
| Repo ground truth | `FULL_PLATFORM_ARCHITECTURE_AUDIT.md` | Present Proposed |
| Foundation critique | `FOUNDATION_ARCHITECTURE_REVIEW.md` | Present |
| Entity ER | `SPEC-domain-model.md` | Present |
| Commerce≠Knowledge | Foundation PKE SPEC | Present |
| Taxonomy model | Foundation taxonomy SPEC | Present |
| Taxonomy seed | `SPEC-industrial-taxonomy-master-seed.md` | Present |
| Property system | `SPEC-property-dictionary-system.md` | Present |
| Graph model | Foundation KG SPEC | Present |
| Relation registry | `SPEC-knowledge-graph-registry.md` | Present |
| Import playbook | Foundation playbook | Present |
| Transform mechanics | `SPEC-data-transformation-architecture.md` | Present |
| Target blueprint / PDP | `KNOWLEDGE_PLATFORM_TARGET_ARCHITECTURE.md` | Present |
| Ingestion boundary | ADR-012 + policy | **Accepted/Binding** |
| URL contract | ADR-010 | **Accepted** |

---

## 3. Workstream detail

### 3.1 Database models

**Can implement?** Conditionally.

| Allowed now (after Board + ADR) | Forbidden now |
|---------------------------------|---------------|
| Edge projection tables for KB-001 subset | Dropping `products.specifications` |
| TaxonomyNode tables | Second `categories` DAG |
| Property Definition tables (read model) | Enabling dual-write without Property governance Accept |
| Manufacturer table | Silent Brand row splits without UD-01 |

**Missing before “safe DDL”:**  
1. UD-05 storage ADR (relational edges vs hybrid)  
2. UD-02 PKE identity ADR  
3. UD-06 Canon Accept of SPEC pack  
4. Migration plan artifact (AODS `MIGRATION-PLAN`) per change

### 3.2 API layer

**Can implement?** Conditionally — additive `/api/v1/knowledge/*` per Phase 2.

**Missing:**  
- Concrete OpenAPI RFC for v1 knowledge resources  
- AuthZ matrix for steward vs admin vs public read  
- Pagination/neighborhood query SLAs for dense edges

### 3.3 Admin knowledge management

**Can implement?** Conditionally after Dictionary seed + roles.

**Missing:**  
- UX contracts (page SPECs) for Fact editor / edge review  
- Steward role mapping in `users` roles (may need product decision)  
- Manufacturer admin flows (UD-01)

### 3.4 Import pipeline

**Can implement?** Yes for **formalizing maps + stages** around existing scripts (Category A local).

**Missing for “platform pipeline”:**  
- Shared job runner in-app (Phase 2 jobs module)  
- Review queue productization (XF-Q1)  
- Enforced AI deny in code (today policy-only)

**Never missing:** ADR-012 remain binding.

### 3.5 AI agents

| Capability | Ready? |
|------------|--------|
| Classify into closed taxonomy labels | Yes with Medium review |
| Draft modules/FAQs | Yes with Medium review (UD-08) |
| Suggest similar/links | Yes asserted-only |
| Invent specs/standards/prices | **No — forbidden** |
| Generative customer RAG | **No** — Evidence≈0; Bible P4; AI pack not Accepted |

### 3.6 SEO pages

| Page | Ready? |
|------|--------|
| PDP slug / Category / Brand hubs | **Yes** (largely shipped) — enhance with knowledge modules when Facts exist |
| Type / Application / Industry hubs | **No** until UD-04 |
| Facet hubs | **No** — forbidden by ADR-010 §8 |

---

## 4. Explicit still-missing architecture (after this pack)

| Gap | Severity | Notes |
|-----|----------|-------|
| Accepted storage ADR for edges/Facts | **Blocker for DDL** | UD-05 |
| Board Accept of SPEC pack | **Blocker for Canon citations** | UD-06 |
| Manufacturer migration decision | High | UD-01 |
| PKE ID scheme | High | UD-02 |
| Property Dictionary v0 seed data file | Medium | UD-03 — SPEC exists, data file not authored |
| Knowledge hub URL RFC | Medium | UD-04 |
| OpenAPI knowledge contract RFC | Medium | Before public API |
| Admin UX SPECs | Medium | Before large admin build |
| Search architecture pack | Low near-term | Phase 2 FTS first; enterprise search pack absent |
| Evidence corpus plan at scale | High for AI | PDFs historically empty |

These are **identified explicitly** so engineering does not invent them mid-IMPL.

---

## 5. Safe implementation sequence (planning)

1. Board review / Accept SPECs (UD-06) → Canon Lock rows  
2. ADR: edge + Fact storage (UD-05); ADR: Manufacturer (UD-01); ADR: PKE id (UD-02)  
3. KB-001: project Article↔Product↔Category edges (registry subset)  
4. Git Property Dictionary v0 (metrology) + mapping tables — **no dual-write**  
5. Taxonomy seed load (draft nodes) + classification maps for one brand  
6. Admin read-only Knowledge views → then assert/publish Facts  
7. PDP consume published Facts behind flag  
8. Only then RFC for dual-write / broader hubs  

---

## 6. Readiness decisions (Proposed)

| ID | Decision |
|----|----------|
| **RD-1** | Completion pack closes *logical* foundation gaps for planning |
| **RD-2** | Coding knowledge DDL without UD-05/UD-06 is **non-compliant** with architecture-first process |
| **RD-3** | Script-stage formalization under ADR-012 may proceed as Category A local work citing playbook/transform SPECs as Proposed guidance — not as Canon — until Accept |
| **RD-4** | No second commerce taxonomy in any IMPL |

---

## 7. Validation statement

This readiness review does **not** authorize:

- Setting document Status to Accepted  
- Production enrichment  
- Dependency changes  
- Inventing ADR-001…009 historical text  

---

## 8. Summary answers

| Question | Answer |
|----------|--------|
| Database models? | **After** Board Accept + storage/identity ADRs |
| API layer? | **After** those + additive OpenAPI RFC |
| Admin KM? | **After** Dictionary seed + roles + UD-01 |
| Import pipeline? | **Yes** to formalize locally under ADR-012; platform jobs later |
| AI agents? | **Assist only**; no invent; no RAG yet |
| SEO pages? | **Enhance existing hubs/PDP**; new knowledge hubs blocked on UD-04 |
