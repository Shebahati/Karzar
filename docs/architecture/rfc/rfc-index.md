# RFC Index — Karzar

**Status:** Mixed — **RFC-004 and RFC-005 Accepted** (Wave-1 ۱۴۰۵/۰۵/۰۷ · Mohammad Shebahati); remaining RFCs Draft pending later Board waves  
**Process SoT:** [`README.md`](./README.md)  
**Template:** [`RFC-TEMPLATE.md`](./RFC-TEMPLATE.md)

| ID | Title | Status | Primary Epic | Depends on | Blocks / enables |
|----|-------|--------|--------------|------------|------------------|
| [RFC-001](./RFC-001-move-jsonb-specs-toward-facts.md) | Move JSONB Specs toward Facts | Draft | 2–3 | ADR-003, ADR-004 | Enables RFC-003 dual-write path |
| [RFC-002](./RFC-002-knowledge-graph-introduction.md) | Knowledge Graph Introduction | Draft | 4 | ADR-005, Domain, KG pack | Graph overlay; not RAG |
| [RFC-003](./RFC-003-pim-dual-write-migration.md) | PIM Dual-write / Migration | Draft | 2–3 | RFC-001, RFC-007, ADR-011 | Spec SoT cutover |
| [RFC-004](./RFC-004-slug-migration-and-redirects.md) | Slug Migration & Redirects | **Accepted** | **1** | ADR-010 | PDP SEO; no Facts needed |
| [RFC-005](./RFC-005-brand-hub-launch.md) | Brand Hub Launch | **Accepted** | **1** | ADR-010, EPIC0 brands | Brand hubs; no Facts needed |
| [RFC-006](./RFC-006-vector-search-introduction.md) | Vector Search Introduction | Draft | 5+ | ADR-007, ADR-009 | Gated; Evidence/eval first |
| [RFC-007](./RFC-007-property-governance-rollout.md) | Property Governance Rollout | Draft | 3 | ADR-004, ADR-011 | Mapping MVP; dual-write still gated |

## Suggested review order for EPIC 1

1. RFC-004  
2. RFC-005  
3. (parallel docs) RFC-007 drafting for EPIC 3 readiness  

## Suggested review order for Facts path

1. RFC-007 (dictionary ops)  
2. RFC-001 (direction + read preference)  
3. RFC-003 (dual-write mechanics)  
4. RFC-002 (graph overlay when Facts exist)  
5. RFC-006 only after Gates A–D trajectory clear  

## Status legend

Draft → Review → Accepted → Implementing → Completed | Rejected | Deferred
