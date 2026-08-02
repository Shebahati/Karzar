# Architecture Decision Records (ADR)

**Parent:** [`../karzar-knowledge-platform-master-architecture.md`](../karzar-knowledge-platform-master-architecture.md)  
**Status of this pack:** Mixed — **ADR-010, ADR-012** Accepted (Wave-1 ۱۴۰۵/۰۵/۰۷); **ADR-013, ADR-014** Accepted (Knowledge Foundation Day-2 ۱۴۰۵/۰۵/۱۰ · Mohammad Shebahati); **ADR-015** Proposed (Product Type engineering classification · KB-PT-00). Reserved ADR-001…009/011 remain **not present** — do not invent (`CR-009`/`CR-010`)
**Baseline:** `karzar_db` · Tag `KARZAR-BASELINE-20260728`  
**Canon:** Binding criteria index [`../CANON-LOCK.md`](../CANON-LOCK.md) (Consistency Canon C0–C10 text is **not in this repo** until promoted)

---

## 1. Purpose — ADR vs Bible vs RFC vs Audit

| Artifact | Role |
|----------|------|
| **Master Architecture Bible** | Orientation hub; indexes decisions; Planes A/B/C |
| **ADR** | Durable *decision* record (options, choice, consequences, gates) |
| **RFC** | Change *proposal / rollout plan*; cites ADRs |
| **Audit / Report** | Measurement evidence only — not policy |

**Flow:** Idea → RFC → ADR (if durable decision) → Implementation PR → Audit

---

## 2. Lifecycle states

| Status | Meaning | Who may set |
|--------|---------|-------------|
| **Proposed** | Authored; not yet Board-ratified | Platform Architect |
| **Accepted** | Binding for implementation | Architecture Board |
| **Deprecated** | No longer preferred; still readable | Architecture Board |
| **Superseded** | Replaced by a newer ADR (link required) | Architecture Board |

Silent status upgrades in PRs without Board minute are **non-compliant**.

---

## 3. Naming & layout

- Files: `ADR-NNN-kebab-case-title.md`
- One decision per ADR
- Amend with dated notes; prefer Supersede over silent rewrite of history

---

## 4. Index — present in this repository

| ID | Title | Status | Epic impact | Notes |
|----|-------|--------|-------------|-------|
| [ADR-010](./ADR-010-seo-url-contract.md) | SEO URL Contract | **Accepted** | **1** | Cite for URL / PDP / Brand Hub / JSON-LD |
| [ADR-012](./ADR-012-ingestion-boundary-local-vs-production.md) | Ingestion Boundary | **Accepted** | All writes | Cite for enrichment / importers |
| [ADR-013](./ADR-013-knowledge-edge-fact-storage.md) | Knowledge Edge/Fact Storage | **Accepted** | KB / knowledge | Postgres overlay; no graph engine in KB-001 |
| [ADR-014](./ADR-014-product-knowledge-entity-identity.md) | PKE Identity | **Accepted** | KB / knowledge | Wave-1 PKE join = `products.id` |
| [ADR-015](./ADR-015-product-type-engineering-classification.md) | Product Type engineering classification | **Proposed** | KB / Product Type | Owner direction recorded; Board Accept not granted; Hybrid FK + taxonomy participation |

## 4b. Reserved IDs — **not in this repository** (do not cite / invent)

| ID | Intended title (historical) | Status intent |
|----|----------------------------|---------------|
| ADR-001 | Source of Truth Planes | Proposed — **not promoted** |
| ADR-002 | Product Identity | Proposed — **not promoted** |
| ADR-003 | Product Specifications Storage | Proposed — **not promoted** |
| ADR-004 | JSONB Strategy & FA/EN Mapping | Proposed — **not promoted** |
| ADR-005 | Knowledge Graph | Proposed — **not promoted** |
| ADR-006 | Category Taxonomy | Proposed — **not promoted** |
| ADR-007 | Search Strategy | Proposed — **not promoted** |
| ADR-008 | Evidence & Documents | Proposed — **not promoted** |
| ADR-009 | AI Retrieval Gates | Proposed — **not promoted** |
| ADR-011 | Property Dictionary Governance | Proposed — **not promoted** |

Until Board promotes a file into `docs/architecture/adr/`, agents MUST NOT invent its contents or use it as merge criteria (`CR-009` Option B / `CR-010`).

---

## 5. Contribution rules

1. One decision per ADR.  
2. ≥2 considered options + explicit Decision using MUST/SHOULD/MAY.  
3. MUST NOT order schema migration by ADR alone (RFC + Alembic PR).  
4. MUST NOT weaken ADR-012.  
5. Supersede with a new ADR ID rather than rewriting Accepted history silently.

---

## 6. How implementation MUST cite ADRs

PRs that touch URLs, SEO, or Brand Hub MUST cite **ADR-010**. Enrichment / importer / catalog write paths MUST cite **ADR-012**. Knowledge edge/Fact storage MUST cite **ADR-013**. PKE identity / product↔knowledge joins MUST cite **ADR-014**. Do not cite reserved IDs from §4b until those files exist in this repo.

---

## 7. Open questions (pack-level)

1. Board calendar for promoting reserved ADR-001…009/011 into this repository.  
2. Where Consistency Canon C0–C10 will live once promoted (inline in Canon Lock vs dedicated prompt pack).
