# Canon Lock Index — Karzar

**Document type:** Binding criteria index (not a second architecture bible)  
**Status:** **Accepted** (Wave-1 EPIC-1 Canon Lock)  
**Location:** Canonical copy in this repository (`docs/architecture/CANON-LOCK.md`)  
**Purpose:** Single answer to: *What is mandatory criteria for work today?*

> **Promotion record:** see [`PROMOTION-WAVE1.md`](./PROMOTION-WAVE1.md).  
> **SoR rule (AODS `CR-009` Option B, 2026-07-30):** Binding merge criteria live **only** in this Git
> repository. Paths outside the checkout (including historical `Website/docs/`) are **not** Authoring SoR
> for agents or PR review and MUST NOT be cited as merge criteria until Board promotes them into this tree.

> If a document is **not** listed here as **Accepted** or **Binding**, it MUST NOT alone be used as merge criteria for EPIC 1 work — unless Architecture Board later adds it to this index.
> If a listed path is marked **not in this repository**, it is **not** Binding until promoted — do not invent its contents.

---

## Board Acceptance (Wave 1)

| Field | Value |
|-------|-------|
| **Accepted on** | ۱۴۰۵/۰۵/۰۷ (2026-07-29) |
| **Board** | Architecture Board |
| **Signed** | محمد شباهتی / Mohammad Shebahati |
| **Minute** | موج ۱ قفل EPIC 1 — تصمیم **الف** |
| **Scope** | Lock Wave-1 documents as binding criteria; defer non–EPIC-1 packs |

---

## 1. Accepted — Wave 1 (binding criteria)

| Document | Path | Status | Since | Signed | Mandatory for |
|----------|------|--------|-------|--------|----------------|
| Master Architecture Bible (Canonical) | [`karzar-knowledge-platform-master-architecture.md`](./karzar-knowledge-platform-master-architecture.md) | **Accepted** | ۱۴۰۵/۰۵/۰۷ | Mohammad Shebahati | Architecture-aligned work; orientation hub (Plane B) |
| ADR-010 — SEO URL Contract | [`adr/ADR-010-seo-url-contract.md`](./adr/ADR-010-seo-url-contract.md) | **Accepted** | ۱۴۰۵/۰۵/۰۷ | Mohammad Shebahati | Any URL / PDP / Brand Hub / canonical / JSON-LD change |
| ADR-012 — Ingestion Boundary | [`adr/ADR-012-ingestion-boundary-local-vs-production.md`](./adr/ADR-012-ingestion-boundary-local-vs-production.md) | **Accepted** | ۱۴۰۵/۰۵/۰۷ | Mohammad Shebahati | Any enrichment / importer / catalog write path |
| RFC-004 — Slug Migration & Redirects | [`rfc/RFC-004-slug-migration-and-redirects.md`](./rfc/RFC-004-slug-migration-and-redirects.md) | **Accepted** | ۱۴۰۵/۰۵/۰۷ | Mohammad Shebahati | EPIC 1 PDP slug + 301 implementation PRs |
| RFC-005 — Brand Hub Launch | [`rfc/RFC-005-brand-hub-launch.md`](./rfc/RFC-005-brand-hub-launch.md) | **Accepted** | ۱۴۰۵/۰۵/۰۷ | Mohammad Shebahati | EPIC 1 Brand Hub implementation PRs |
| Developer Standards pack | [`../development/standards/README.md`](../development/standards/README.md) | **Accepted** | ۱۴۰۵/۰۵/۰۷ | Mohammad Shebahati | All PRs (DoD, checklist, citation, Alembic, local enrich) |
| Developer Standards (primary) | [`../development/standards/karzar-developer-standards.md`](../development/standards/karzar-developer-standards.md) | **Accepted** | ۱۴۰۵/۰۵/۰۷ | Mohammad Shebahati | Same as pack |
| IA pack (EPIC 1 scope) | [`information-architecture/README.md`](./information-architecture/README.md) | **Accepted** | ۱۴۰۵/۰۵/۰۷ | Mohammad Shebahati | EPIC 1 routes, hubs, page types, indexation honesty |
| IA primary | [`information-architecture/karzar-information-architecture.md`](./information-architecture/karzar-information-architecture.md) | **Accepted** | ۱۴۰۵/۰۵/۰۷ | Mohammad Shebahati | Same (EPIC 1 surfaces) |
| EPIC 1 IA Readiness | [`information-architecture/epic1-ia-readiness.md`](./information-architecture/epic1-ia-readiness.md) | **Accepted** | ۱۴۰۵/۰۵/۰۷ | Mohammad Shebahati | EPIC 1 delivery checklist |
| Brand Hub page contract | [`information-architecture/brand-hub-page-contract.md`](./information-architecture/brand-hub-page-contract.md) | **Accepted** | 2026-07-30 | Mohammad Shebahati | SEO-008 / Brand Hub `/brands/{slug}` IMPL (Q1–Q5 = D21) |

---

## Board Acceptance (Knowledge Foundation — Day 2)

| Field | Value |
|-------|-------|
| **Accepted on** | ۱۴۰۵/۰۵/۱۰ (2026-08-01) — ۱۰ مرداد ۱۴۰۵ |
| **Board** | Architecture Board |
| **Signed** | محمد شباهتی / Mohammad Shebahati |
| **Minute** | [`../../aods/90-governance/BOARD-MINUTE-KNOWLEDGE-FOUNDATION-ACCEPT-2026-08-01.md`](../../aods/90-governance/BOARD-MINUTE-KNOWLEDGE-FOUNDATION-ACCEPT-2026-08-01.md) |
| **Scope** | Accept core knowledge SPEC pack + ADR-013/014; freeze KB-001 to three projection edges; defer dual-write / RAG / UD-01/04/07; OI-KF-04 supersede Phase1–3 for living path |

## 1c. Accepted — Knowledge Foundation (binding criteria)

| Document | Path | Status | Since | Signed | Mandatory for |
|----------|------|--------|-------|--------|----------------|
| Knowledge Foundation Specs Pack (index) | [`specs/README.md`](./specs/README.md) | **Accepted** | ۱۴۰۵/۰۵/۱۰ | Mohammad Shebahati | Knowledge / KB-001 planning & IMPL citation |
| Product Knowledge Entity Model | [`specs/SPEC-product-knowledge-entity-model.md`](./specs/SPEC-product-knowledge-entity-model.md) | **Accepted** | ۱۴۰۵/۰۵/۱۰ | Mohammad Shebahati | Commerce vs PKE separation; identity hooks |
| Industrial Taxonomy Model | [`specs/SPEC-industrial-taxonomy-model.md`](./specs/SPEC-industrial-taxonomy-model.md) | **Accepted** | ۱۴۰۵/۰۵/۱۰ | Mohammad Shebahati | Multi-dim taxonomy; **no** second Category DAG |
| Knowledge Graph Model | [`specs/SPEC-knowledge-graph-model.md`](./specs/SPEC-knowledge-graph-model.md) | **Accepted** | ۱۴۰۵/۰۵/۱۰ | Mohammad Shebahati | Overlay nodes/edges/provenance |
| Product Import & Enrichment Playbook | [`specs/SPEC-product-import-enrichment-playbook.md`](./specs/SPEC-product-import-enrichment-playbook.md) | **Accepted** | ۱۴۰۵/۰۵/۱۰ | Mohammad Shebahati | Enrichment stages; AI limits (with ADR-012) |
| Domain Model | [`specs/SPEC-domain-model.md`](./specs/SPEC-domain-model.md) | **Accepted** | ۱۴۰۵/۰۵/۱۰ | Mohammad Shebahati | Logical ER commerce+knowledge |
| Property Dictionary System | [`specs/SPEC-property-dictionary-system.md`](./specs/SPEC-property-dictionary-system.md) | **Accepted** | ۱۴۰۵/۰۵/۱۰ | Mohammad Shebahati | Definitions/templates/Facts; dual-write still gated |
| Knowledge Graph Registry | [`specs/SPEC-knowledge-graph-registry.md`](./specs/SPEC-knowledge-graph-registry.md) | **Accepted** | ۱۴۰۵/۰۵/۱۰ | Mohammad Shebahati | Official relation vocabulary; KB-001 edge freeze |
| Data Transformation Architecture | [`specs/SPEC-data-transformation-architecture.md`](./specs/SPEC-data-transformation-architecture.md) | **Accepted** | ۱۴۰۵/۰۵/۱۰ | Mohammad Shebahati | Mapping/provenance/rollback mechanics |
| ADR-013 — Knowledge Edge/Fact Storage | [`adr/ADR-013-knowledge-edge-fact-storage.md`](./adr/ADR-013-knowledge-edge-fact-storage.md) | **Accepted** | ۱۴۰۵/۰۵/۱۰ | Mohammad Shebahati | Postgres overlay storage for edges/Facts |
| ADR-014 — PKE Identity | [`adr/ADR-014-product-knowledge-entity-identity.md`](./adr/ADR-014-product-knowledge-entity-identity.md) | **Accepted** | ۱۴۰۵/۰۵/۱۰ | Mohammad Shebahati | Wave-1 PKE join = `products.id` |

**Board policy from the same minute (not separate docs):** UD-03 metrology-first dictionary seed; UD-08 never auto-publish customer-facing FA AI prose; KB-001 freeze = `PRODUCT_BELONGS_TO_CATEGORY`, `PRODUCT_BRANDED_AS`, `ARTICLE_EXPLAINS_PRODUCT` only.

---

## Board Acceptance (ADR-015 Hybrid Product Type Clarification)

| Field | Value |
|-------|-------|
| **Accepted on** | ۱۴۰۵/۰۵/۱۱ (2026-08-02) — ۱۱ مرداد ۱۴۰۵ |
| **Board** | Karzar Architecture Board |
| **Signed** | محمد شباهتی / Mohammad Shebahati |
| **Minute** | [`../../aods/90-governance/BOARD-MINUTE-ADR-015-HYBRID-PRODUCT-TYPE-CLARIFICATION.md`](../../aods/90-governance/BOARD-MINUTE-ADR-015-HYBRID-PRODUCT-TYPE-CLARIFICATION.md) |
| **Meeting** | `AB-ADR-015-2026-08-02` |
| **Ballot** | Option **A** — Accept Hybrid clarification |
| **Scope** | Primary Wave-1 Product Type = nullable `products.product_type_id`; `PRODUCT_CLASSIFIED_AS` secondary/multi-dimensional; same Product Type identity; PKE = `products.id`; Category commerce-only; no graph DB; no dual-write; no bulk JSONB migration; Prompt 13 owns taxonomy bridge |

## 1d. Accepted — Product Type engineering classification

| Document | Path | Status | Since | Signed | Mandatory for |
|----------|------|--------|-------|--------|----------------|
| ADR-015 — Product Type engineering classification | [`adr/ADR-015-product-type-engineering-classification.md`](./adr/ADR-015-product-type-engineering-classification.md) | **Accepted** | ۱۴۰۵/۰۵/۱۱ | Mohammad Shebahati | Product Type runtime (KB-PT-01+); Hybrid FK vs taxonomy; engineering classification SoT |
| Board minute — ADR-015 Hybrid clarification | [`../../aods/90-governance/BOARD-MINUTE-ADR-015-HYBRID-PRODUCT-TYPE-CLARIFICATION.md`](../../aods/90-governance/BOARD-MINUTE-ADR-015-HYBRID-PRODUCT-TYPE-CLARIFICATION.md) | **Accepted** | ۱۴۰۵/۰۵/۱۱ | Mohammad Shebahati | Evidence for ADR-015 Accept; KB-PT-01 unblock |

**Note:** `SPEC-canonical-product-type-model.md` remains **Proposed** implementation contract under Accepted ADR-015 (not itself Canon until separately Accepted if Board requires).

---

## Board Acceptance (AODS process system)

| Field | Value |
|-------|-------|
| **Accepted on** | ۱۴۰۵/۰۵/۰۸ (2026-07-30) — ۸ مرداد ۱۴۰۵ |
| **Board** | Architecture Board |
| **Signed** | محمد شباهتی / Mohammad Shebahati |
| **Minute** | [`aods/90-governance/BOARD-MINUTE-AODS-ACCEPTANCE.md`](../../aods/90-governance/BOARD-MINUTE-AODS-ACCEPTANCE.md) (lands with PR #128) |
| **Scope** | Adopt AODS (`aods/`) as the binding process system for how changes are executed, validated, recorded, and approved |

## 1b. Accepted — Process (AODS)

| Document | Path | Status | Since | Signed | Mandatory for |
|----------|------|--------|-------|--------|----------------|
| AODS Charter | [`../../aods/AODS-CHARTER.md`](../../aods/AODS-CHARTER.md) | **Accepted** | ۱۴۰۵/۰۵/۰۸ | Mohammad Shebahati | Process execution: roles, prompts, gates, human checkpoints; all Auto Mode work |
| AODS pack (root) | [`../../aods/`](../../aods/) | **Accepted** | ۱۴۰۵/۰۵/۰۸ | Mohammad Shebahati | Same — full pack under `aods/` version 1.0.0 |


---

## 2. Binding operational (pre-Wave-1; still mandatory)

These were already normative. Wave 1 does **not** weaken them.

| Document | Path | Status | Mandatory for |
|----------|------|--------|----------------|
| Data ingestion policy | [`data-ingestion-policy.md`](./data-ingestion-policy.md) | **Binding** | Importers, enrichment Category A/B/C |
| Git development workflow | [`../development/git-development-workflow.md`](../development/git-development-workflow.md) | **Binding** | Branch / PR workflow |

> **Removed from Binding rows (AODS `CR-009`/`CR-010`, 2026-07-30):**  
> `docs/development/development-lifecycle-standard.md` and  
> `docs/audits/repository-governance-final-lock.md` were listed as Binding/evidence but **are not present**
> in this repository. They MUST NOT be cited as merge criteria until Board promotes them here. Residual
> dangling citations elsewhere remain `CR-010` until cleared.

---

## 3. Explicitly NOT locked as Wave-1 merge criteria

Still **Proposed / Draft** in Board intent — and, under `CR-009` Option B, **most of these packs are not in
this Git checkout**. They may **not** be cited, invented, or used as merge criteria until Board promotes
concrete files into this repository and adds Accepted/Binding rows above.

| Area | Path / IDs | In this repo? | Note |
|------|------------|---------------|------|
| ADR-001 … ADR-009, ADR-011 | `docs/architecture/adr/` | **No** (010, 012, **013**, **014** + README present) | Reserved historical IDs still not citeable/inventable; wave-1 knowledge storage/identity = ADR-013/014 |
| RFC-001, 002, 003, 006, 007 | `docs/architecture/rfc/` | **No** (only 004, 005 + index/template) | Not citeable until promoted |
| Reserved packs `domain/` / `pim/` / `knowledge-graph/` | respective dirs | **No** (UD-07 deferred) | Living Accepted path = `docs/architecture/specs/` core pack (§1c) |
| Taxonomy master seed / audit / target / readiness / FA summary | `docs/architecture/specs/` (named files) | **Yes** | Remain **Proposed / REFERENCE** — not merge criteria alone |
| Phase1–3 knowledge docs | `docs/KNOWLEDGE_PLATFORM_PHASE*.md` | **Yes** | **HISTORICAL** after OI-KF-04 — do not use as living SoT |
| Enterprise AI | `docs/architecture/ai/` | **No** | Generative blocked until pack exists + Gate C |
| Enterprise Search | `docs/architecture/search/` | **No** | Not citeable until promoted |
| Repo Governance v2 | `docs/governance/repository/` | **No** | Not citeable until promoted |
| Enterprise Roadmap | `docs/roadmap/enterprise/` | **No** | Not citeable until promoted |
| Dual-write enablement | RFC-001/003 path | **No** | **Deferred** — separate Board gate (Day-2 minute) |
| Generative RAG | ADR-009 Gates A–D | **No** | **Deferred / blocked** while Evidence≈0 (Day-2 minute) |

---

## 4. Evidence only (not policy)

| Kind | Path | Rule |
|------|------|------|
| EPIC 0 / repository audits present under `docs/audits/` | only files that **exist** in this checkout | Measure reality; do not invent missing audit paths; do not edit upward to look healthier |

Missing historical audit filenames cited in older prose are **not** evidence and are tracked under `CR-010` until removed or promoted.

---

## 5. How to use this index (daily)

1. Before starting work: find the row that matches your change type.  
2. Open the Accepted/Binding document and follow it.  
3. In the PR: cite the IDs/paths from this index — enforced via [`pr-checklist.md`](../development/standards/pr-checklist.md) and [`documentation-citation-rules.md`](../development/standards/documentation-citation-rules.md).  
4. Do **not** upgrade any other doc to Accepted inside a feature PR — only Board + update to this file.  
5. When Board Accepts a later wave: add rows here in the same commit as the Status upgrade.

**Operating rule (Wave-1):** Missing Canon citation on URL/SEO/enrich PRs is an **explicit PR fail**.

---

## 6. Change control for this file

| Action | Who |
|--------|-----|
| Add/remove Accepted rows | Architecture Board only (minute + signature) |
| Fix broken links / typos | Docs PR; no Status change |
| Self-Accept of new packs in a feature PR | **Forbidden** |

---

## 7. Pointers

- Bible § P9: Repo governance ≠ Project governance  
- Developer Standards: [`../development/standards/`](../development/standards/)  
- Next program step after this lock: enforce citation on every PR (Wave-1 operating rule), then implement EPIC 1
