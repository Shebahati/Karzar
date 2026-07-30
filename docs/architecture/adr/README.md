# Architecture Decision Records (ADR)

**Parent:** [`../karzar-knowledge-platform-master-architecture.md`](../karzar-knowledge-platform-master-architecture.md)  
**Status of this pack:** Mixed — **ADR-010 and ADR-012 Accepted** (Wave-1 ۱۴۰۵/۰۵/۰۷ · Mohammad Shebahati); remaining ADRs still Proposed pending later Board waves  
**Baseline:** `karzar_db` · **5901** active products · Alembic `c4d5e6f7a8b9` · Tag `KARZAR-BASELINE-20260728`  
**Canon:** Consistency Canon C0–C10 in `docs/prompts/karzar-enterprise-architecture-prompts.md`

---

## 1. Purpose — ADR vs Bible vs RFC vs Audit

| Artifact | Role |
|----------|------|
| **Master Architecture Bible** | Orientation hub; indexes decisions; Planes A/B/C |
| **ADR** | Durable *decision* record (options, choice, consequences, gates) |
| **RFC** | Change *proposal / rollout plan* (Prompt 10); cites ADRs |
| **Audit / Report** | Measurement evidence only — not policy |

**Flow:** Idea → RFC → ADR (if durable decision) → Implementation PR → Audit

---

## 2. Lifecycle states

| Status | Meaning | Who may set |
|--------|---------|-------------|
| **Proposed** | Authored; not yet Board-ratified (default for this pack) | Platform Architect |
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

## 4. Index

| ID | Title | Status | Epic impact | Depends on | RFC follow-ups |
|----|-------|--------|-------------|------------|----------------|
| [ADR-001](./ADR-001-source-of-truth-planes.md) | Source of Truth Planes | Proposed | All | Ingestion ADR-001 narrative | — |
| [ADR-002](./ADR-002-product-identity.md) | Product Identity | Proposed | 1+ | ADR-001 | RFC-004 |
| [ADR-003](./ADR-003-product-specifications-storage.md) | Product Specifications Storage | Proposed | 2–3 | ADR-002 | RFC-001, RFC-003 |
| [ADR-004](./ADR-004-jsonb-strategy-and-fa-en-mapping.md) | JSONB Strategy & FA/EN Mapping | Proposed | 3 | ADR-003, EPIC0 | RFC-001, RFC-007 |
| [ADR-005](./ADR-005-knowledge-graph.md) | Knowledge Graph | Proposed | 4 | ADR-001, ADR-004 | RFC-002 |

KG architecture pack (Prompt 5): [`../knowledge-graph/`](../knowledge-graph/README.md) — Style A Fact nodes; logical-first.
| [ADR-006](./ADR-006-category-taxonomy.md) | Category Taxonomy | Proposed | 1–3 | ADR-002 | — |
| [ADR-007](./ADR-007-search-strategy.md) | Search Strategy | Proposed | 1, 5 | ADR-002 | RFC-006 |
| [ADR-008](./ADR-008-evidence-and-documents.md) | Evidence & Documents | Proposed | 2, 5 | ADR-003 | RFC-001 |
| [ADR-009](./ADR-009-ai-retrieval-gates.md) | AI Retrieval Gates | Proposed | 5 | ADR-008, ADR-004 | RFC-006 |
| [ADR-010](./ADR-010-seo-url-contract.md) | SEO URL Contract | **Accepted** | **1** | ADR-002 | RFC-004, RFC-005 |
| [ADR-011](./ADR-011-property-dictionary-governance.md) | Property Dictionary Governance | Proposed | 3 | ADR-004 | RFC-007 |
| [ADR-012](./ADR-012-ingestion-boundary-local-vs-production.md) | Ingestion Boundary | **Accepted** | All writes | Ingestion policy | — |

---

## 5. Contribution rules

1. One decision per ADR.  
2. ≥2 considered options + explicit Decision using MUST/SHOULD/MAY.  
3. MUST NOT order schema migration by ADR alone (RFC + Alembic PR).  
4. MUST NOT weaken ADR-012 or contradict EPIC 0 frozen metrics.  
5. Supersede with a new ADR ID rather than rewriting Accepted history silently.

---

## 6. How implementation MUST cite ADRs

PRs and RFCs that touch meaning, URLs, specs, ingestion, search, or AI MUST list relevant `ADR-NNN` IDs in the description. EPIC 1 URL work MUST cite **ADR-010** (+ ADR-002). Enrichment scripts MUST cite **ADR-012**. Spec dual-write MUST cite **ADR-003/004**.

---

## 7. Open questions (pack-level)

1. Numeric thresholds for ADR-009 Gate B (mapping coverage) and Gate C (Evidence coverage).  
2. MPN first-class field timing (ADR-002 principle only).  
3. Physical graph store (ADR-005 logical-first).  
4. Board calendar for moving Proposed → Accepted.

---

## Cross-cutting rules (R1–R8)

See Prompt 2: JSONB operational until mapping+RFC (R1); Evidence empty blocks RAG (R2); ADR-010 EPIC1-ready without Facts (R3); ADR-012 inviolable (R4); KG logical-first (R5); slug=URL identity, SKU=commerce identity (R6); shared baseline numbers (R7); no unresolved ADR↔ADR conflicts (R8).
