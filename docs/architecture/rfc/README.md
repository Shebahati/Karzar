# RFC System — Karzar

**Status:** Proposed (process SoT for change proposals)  
**Parent:** Master Architecture Bible §17 · ADR pack · Data Governance  
**Output root:** `docs/architecture/rfc/`

## Purpose

RFCs propose **how** a significant change will be designed, rolled out, observed, and rolled back.  
ADRs record **what** durable architectural choice was made.  
PRs implement Accepted work. Audits measure outcomes.

```text
Idea → RFC (Draft→Accepted) → ADR (as needed) → Implementation → Audit / DQ re-measure
```

## When RFC vs ADR-only vs PR-only

| Situation | Artifact |
|-----------|----------|
| Cross-cutting rollout, migration, multi-epic change, production safety plan | **RFC required** |
| Single durable decision (storage, URL pattern, governance rule) without phased plan | **ADR** (may precede or follow RFC) |
| Localized bugfix / small feature within Accepted ADR/RFC envelope | **PR only** — cite ADR/RFC in PR |
| Measurement-only | **Audit** — not an RFC |

**Rule:** Do not duplicate full ADR text inside RFCs — **reference** ADRs as decision anchors (Canon C6).

## Lifecycle

| Status | Meaning | Who sets |
|--------|---------|----------|
| **Draft** | Authoring / this pack default | Author |
| **Review** | Circulating to reviewers | Author → Steward |
| **Accepted** | Board-approved to implement | Architecture Board |
| **Implementing** | Active engineering | Tech lead |
| **Completed** | Exit criteria met + audit note | Board / Decision Board |
| **Rejected** | Will not proceed | Board |
| **Deferred** | Parked with reopen criteria | Board |

RFCs in this prompt are **Draft**. MUST NOT self-mark Implemented/Completed.

## Naming & numbering

- Files: `RFC-NNN-kebab-case-title.md`
- IDs reserved in Bible §17: **RFC-001 … RFC-007**
- New RFCs: next free NNN; register in [`rfc-index.md`](./rfc-index.md)
- One primary change program per RFC; split if dual-write ≠ slug migration

## Owners & review SLA (defaults)

| Role | Duty |
|------|------|
| Author | Draft completeness vs template |
| Domain steward | Technical review ≤ **10 business days** |
| Architecture Board | Accept/Reject/Defer ≤ **15 business days** after Review |
| Security/Admin | Ingestion/prod safety review when Category B or IAM touched |

## Required sections

See [`RFC-TEMPLATE.md`](./RFC-TEMPLATE.md). Every RFC MUST include rollback, ingestion boundary, and KPIs.

## Citing EPIC 0 / DQ

- Cite frozen baselines from `docs/architecture/data-quality/baselines-epic0.md` or EPIC0 audits.  
- Do not invent improved metrics.  
- Map Observability section to DQ / Epic KPI bridge names where relevant.

## Production safety

- Default enrichment: **Category A local** (`data-ingestion-policy.md` wins).  
- Category B production requires ticket, backup, Board-visible plan inside RFC.  
- ADR-012 fail-closed remains binding.

## Index

| ID | Title | Status | Epic | Depends |
|----|-------|--------|------|---------|
| [RFC-001](./RFC-001-move-jsonb-specs-toward-facts.md) | Move JSONB Specs toward Facts | Draft | 2–3 | ADR-003/004 |
| [RFC-002](./RFC-002-knowledge-graph-introduction.md) | Knowledge Graph Introduction | Draft | 4 | ADR-005 |
| [RFC-003](./RFC-003-pim-dual-write-migration.md) | PIM Dual-write / Migration | Draft | 2–3 | RFC-001, ADR-011 |
| [RFC-004](./RFC-004-slug-migration-and-redirects.md) | Slug Migration & Redirects | Draft | **1** | ADR-010 |
| [RFC-005](./RFC-005-brand-hub-launch.md) | Brand Hub Launch | Draft | **1** | ADR-010 |
| [RFC-006](./RFC-006-vector-search-introduction.md) | Vector Search Introduction | Draft | 5+ | ADR-007/009 |
| [RFC-007](./RFC-007-property-governance-rollout.md) | Property Governance Rollout | Draft | 3 | ADR-011/004 |

Full index: [`rfc-index.md`](./rfc-index.md).
