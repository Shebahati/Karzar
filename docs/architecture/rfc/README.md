# RFC System — Karzar

**Status:** Mixed — **RFC-004 and RFC-005 Accepted** (Wave-1 ۱۴۰۵/۰۵/۰۷ · Mohammad Shebahati); other RFC IDs reserved but **not present** in this repository  
**Parent:** Master Architecture Bible · ADR pack · Canon Lock  
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
| Single durable decision without phased plan | **ADR** (may precede or follow RFC) |
| Localized bug fix / small feature within Accepted ADR/RFC envelope | **PR only** — cite ADR/RFC in PR |
| Measurement-only | **Audit** — not an RFC |

**Rule:** Do not duplicate full ADR text inside RFCs — **reference** ADRs as decision anchors.

## Lifecycle

| Status | Meaning | Who sets |
|--------|---------|----------|
| **Draft** | Authoring | Author |
| **Review** | Circulating to reviewers | Author → Steward |
| **Accepted** | Board-approved to implement | Architecture Board |
| **Implementing** | Active engineering | Tech lead |
| **Completed** | Exit criteria met + audit note | Board |
| **Rejected** | Will not proceed | Board |
| **Deferred** | Parked with reopen criteria | Board |

MUST NOT self-mark Implemented/Completed without Board evidence.

## Naming & numbering

- Files: `RFC-NNN-kebab-case-title.md`
- New RFCs: next free NNN; register in [`rfc-index.md`](./rfc-index.md)
- One primary change program per RFC

## Owners & review SLA (defaults)

| Role | Duty |
|------|------|
| Author | Draft completeness vs template |
| Domain steward | Technical review ≤ **10 business days** |
| Architecture Board | Accept/Reject/Defer ≤ **15 business days** after Review |
| Security/Admin | Ingestion/prod safety review when Category B or IAM touched |

## Required sections

See [`RFC-TEMPLATE.md`](./RFC-TEMPLATE.md). Every RFC MUST include rollback, ingestion boundary, and KPIs.

## Citing baselines / DQ

Cite only DQ / EPIC0 files that **exist** in this checkout. Do not invent improved metrics. Historical path `docs/architecture/data-quality/baselines-epic0.md` is **not in this repository** (`CR-010`).

## Production safety

- Default enrichment: **Category A local** (`../data-ingestion-policy.md` wins).  
- Category B production requires ticket, backup, Board-visible plan inside RFC.  
- ADR-012 fail-closed remains binding.

## Index — present in this repository

| ID | Title | Status | Epic | Depends |
|----|-------|--------|------|---------|
| [RFC-004](./RFC-004-slug-migration-and-redirects.md) | Slug Migration & Redirects | **Accepted** | **1** | ADR-010 |
| [RFC-005](./RFC-005-brand-hub-launch.md) | Brand Hub Launch | **Accepted** | **1** | ADR-010 |

Full present+reserved index: [`rfc-index.md`](./rfc-index.md).

## Reserved IDs — **not in this repository** (do not cite / invent)

| ID | Intended title (historical) | Status intent |
|----|----------------------------|---------------|
| RFC-001 | Move JSONB Specs toward Facts | Draft — **not promoted** |
| RFC-002 | Knowledge Graph Introduction | Draft — **not promoted** |
| RFC-003 | PIM Dual-write / Migration | Draft — **not promoted** |
| RFC-006 | Vector Search Introduction | Draft — **not promoted** |
| RFC-007 | Property Governance Rollout | Draft — **not promoted** |
