---
id: KNOWLEDGE-PLATFORM-TARGET-ARCHITECTURE
version: 0.1.0
status: Proposed
date: 2026-07-30
governing_parents:
  - docs/architecture/karzar-knowledge-platform-master-architecture.md
  - docs/KNOWLEDGE_PLATFORM_PHASE2_TARGET_ARCHITECTURE.md
  - docs/architecture/information-architecture/karzar-information-architecture.md
  - docs/architecture/specs/SPEC-domain-model.md
owner: Principal Software Architect
task_id: KB-001
---

# Knowledge Platform Target Architecture

**Status:** Proposed  
**Purpose:** Connect Commerce + Knowledge + Taxonomy + Graph + CMS + SEO + AI into one implementation blueprint  
**Constraint:** Additive modular monolith; KG overlay; no cart SoR replacement (Phase 2 locked)

This document **complements** (does not replace) the Master Architecture Bible and Phase 2 module catalog.

---

## 1. Vision (operational)

KarzarTools target: Iranian industrial buyers and engineers get **trustworthy SKUs** and **reference-grade product knowledge** in one product experience — Grainger/RS/Mitutoyo-class depth — without breaking the commerce baseline.

---

## 2. Layered target system

```text
┌──────────────────────────────────────────────────────────────┐
│ Presentation                                                 │
│ Storefront: Commerce Axis + Knowledge Axis modules           │
│ Admin: Commerce ops + Knowledge/PIM/Graph consoles           │
└────────────────────────────┬─────────────────────────────────┘
                             │ /api/v1 + /api/v1/knowledge/*
┌────────────────────────────▼─────────────────────────────────┐
│ Application                                                  │
│ Existing routers (stable) + additive knowledge routers       │
└────────────────────────────┬─────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────┐
│ Domain services                                              │
│ Commerce services (unchanged ownership)                      │
│ Knowledge façade → Entity / Relation / Property / SEO engines│
└───────┬───────────────┬───────────────┬──────────────────────┘
        ▼               ▼               ▼
   Commerce SoR    Knowledge tables   Jobs / projections
   products…       Facts/Edges/…      (Postgres jobs first)
```

**Cite Phase 2:** engines never write price/stock; presentation never talks to engines directly.

---

## 3. How the planes connect

| Plane | Provides | Consumes |
|-------|----------|----------|
| **Commerce** | SKU, price, availability, inquire/buy, Category placement | Identity from catalog |
| **Knowledge (PKE)** | Meaning, model/MPN, lifecycle | Links to Product |
| **Taxonomy** | Domain/Family/Type/Application/Industry | Classification of PKE |
| **Property / Facts** | Governed specs + units | Templates bound to Types |
| **Graph** | Typed relationships | Registry vocabulary |
| **CMS** | Articles/Guides Expressions | Edges to PKE/Types |
| **SEO** | Canonical URLs, JSON-LD, hubs | Entity identity + published Facts only |
| **AI** | Classify/draft/suggest | Closed labels; no invent Facts/prices |
| **Ingestion** | Controlled writes | ADR-012 + transform architecture |

---

## 4. Target PDP composition (canonical story)

**URL:** `/product/{slug}` (ADR-010) — unchanged public identity.

```text
┌─────────────────────────────────────────────────────────────┐
│ HERO / COMMERCE                                             │
│ Brand · Name · SKU · Model                                  │
│ Price · Availability · CTA (buy / inquire)                  │
│ Trust: warranty · original · PDF slot                       │
├─────────────────────────────────────────────────────────────┤
│ KNOWLEDGE — Technical                                       │
│ Published Facts from Property Dictionary (compare-ready)    │
│ Honest empty if unpublished                                 │
├─────────────────────────────────────────────────────────────┤
│ KNOWLEDGE — Understanding                                   │
│ Modules: overview · how-to · applications · FAQ             │
├─────────────────────────────────────────────────────────────┤
│ KNOWLEDGE — Relationships                                   │
│ Compatible accessories · Alternatives · Similar             │
│ Standards / Certifications (Evidence-backed only)           │
│ Articles that explain                                       │
├─────────────────────────────────────────────────────────────┤
│ NAVIGATION EQUITY                                           │
│ Breadcrumbs: Home → Category Hub → Product                  │
│ Chips: Brand Hub · (future) Type/Application if authorized  │
└─────────────────────────────────────────────────────────────┘
```

| Section | Source plane |
|---------|--------------|
| Price / availability / CTA | Commerce Product |
| Brand link | Brand hub `/brands/{slug}` |
| Category crumb | Commerce Category |
| Spec table | Published Facts (JSONB transitional fallback) |
| Education | Knowledge Modules + Article edges |
| Related | Graph edges (not same-category heuristic alone) |
| JSON-LD | Product/Offer from commerce; additional types only from published knowledge |

**Anti-patterns:** inventing specs for SEO; treating facet URLs as entity hubs; hiding empty Document/Accessory slots (IA honesty).

---

## 5. Target Brand Hub & Category Hub

| Hub | Commerce face | Knowledge face |
|-----|---------------|----------------|
| `/brands/{slug}` | Brand-locked PLP | Story modules, coverage by Domain/Type (derived edges), documents |
| `/categories/{slug}` | Merchandising PLP | Optional intro from linked Domain/Family; spec filters from Definitions |

Tool Class / Application hubs: **Board-gated** (UD-04).

---

## 6. Target admin knowledge management

| Console | Capability |
|---------|------------|
| Property Dictionary | CRUD Definitions/Templates (steward) |
| Fact editor | Assert/publish with Evidence attach |
| Taxonomy | Node editor per dimension; commerce Category unchanged |
| Graph | Edge review queue; registry-constrained types |
| Import jobs | Dry-run / apply / quarantine UI |
| AI assist | Suggestions only; never silent publish High-risk |

---

## 7. Target API strategy

| Surface | Rule |
|---------|------|
| Existing `/api/v1/products|categories|brands|cms|…` | Stable contracts; gradual enrichment |
| Additive `/api/v1/knowledge/*` | Entities, relations, search, seo reports, graph neighborhood (Phase 2) |
| Dual-read specs | Prefer Facts when published coverage sufficient; else JSONB |

---

## 8. Target AI placement

```text
Import Classification ──AI suggest──► Review
Content Modules ──────AI draft─────► Review
Similar/Links ────────AI suggest───► Review
Facts / Standards / Prices ─────────► AI DENY invent
Generative RAG ─────────────────────► Blocked until Evidence corpus + ADR gates
```

---

## 9. Target SEO entity architecture

| Entity | URL class | Indexation |
|--------|-----------|------------|
| Product | `/product/{slug}` | Yes when active/quality bar |
| Category | `/categories/{slug}` | Yes |
| Brand | `/brands/{slug}` | Per Brand Hub contract |
| Article | `/blog/{slug}` → future Guides | Yes when published |
| Type / Application | TBD namespace | Only after UD-04 + thin-content policy |
| Facet combos | `/catalog?…` | noindex |

JSON-LD `@id` always matches canonical URL (ADR-010).

---

## 10. Scale posture

| Concern | Approach |
|---------|----------|
| 10³–10⁵ products | Relational SoR + indexed Facts |
| 10⁶ edges | Edge table + batched endpoints; optional graph engine later (UD-05) |
| New domains | Taxonomy seed + templates — no schema redesign |
| Compare | Shared Definition IDs across families |

---

## 11. Migration strangler (summary)

1. Ship projections (Category/Brand/Article edges) — KB-001  
2. Property Dictionary Git seed (metrology) — dual-write still gated  
3. Taxonomy nodes + classification maps  
4. Fact assert path (admin/import) beside JSONB  
5. PDP modules read Facts when published  
6. Board gate dual-write / JSONB de-emphasis  

---

## 12. Requirements

| ID | Criterion |
|----|-----------|
| **TGT-R1** | PDP story separates commerce vs knowledge contributions |
| **TGT-R2** | Preserves ADR-010 URL classes |
| **TGT-R3** | Additive knowledge API |
| **TGT-R4** | AI bounds explicit |
| **TGT-R5** | Aligns Phase 2 overlay + Bible non-goals |

---

## 13. Open questions

UD-04, UD-05, UD-06; plus admin UX prioritization vs Storefront module order.
