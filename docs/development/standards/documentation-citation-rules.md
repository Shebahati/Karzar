# Documentation Citation Rules

**Status:** **Accepted** (Wave-1 · part of Developer Standards)  
**Canon Lock SoT for “what binds today”:** [`docs/architecture/CANON-LOCK.md`](../../architecture/CANON-LOCK.md)

---

## Canon Lock first (Wave-1 operating rule)

Before citing anything else:

1. Open [`CANON-LOCK.md`](../../architecture/CANON-LOCK.md).  
2. Find the **Accepted** or **Binding** row that matches the change.  
3. Cite those paths/IDs in the PR.  
4. Proposed/Draft packs may be mentioned as design context — they do **not** replace Wave-1 Accepted criteria.  
5. Do **not** treat audits as license to skip ingestion or URL contracts.

**EPIC 1 / URL / SEO PRs MUST cite:** ADR-010 · RFC-004 and/or RFC-005 · relevant IA file · and reference Canon Lock Wave-1.  
**Enrichment / importer PRs MUST cite:** ADR-012 · `data-ingestion-policy.md`.

---

## When citations are required in PRs

| Change touches… | Cite at least |
|-----------------|---------------|
| **Anything in Wave-1 scope** | Matching rows in **CANON-LOCK** (Accepted/Binding) |
| SoT planes / ingestion env | ADR-012 (**Accepted**) · `data-ingestion-policy.md` · ADR-001 if planes narrative |
| Product identity / SKU / slug fields | ADR-002 · ADR-010 if public URL |
| Specs storage / JSONB / Facts direction | ADR-003 · ADR-004 · RFC-001/003 as relevant (**not** Wave-1 unlock) |
| FA/EN keys / Property dictionary | ADR-004 · ADR-011 · RFC-007 · property-governance |
| URLs / redirects / hubs | **ADR-010** · **RFC-004/005** · IA url-map / epic1-ia-readiness |
| Graph overlay | ADR-005 · RFC-002 · knowledge-graph pack |
| AI / RAG / vectors | ADR-009 · RFC-006 (generative still gated) |
| Schema migration policy | Alembic standards · lifecycle standard |
| Architecture narrative | Master Bible (**Accepted**) + Canon Lock — Bible does not override binding ingestion |

---

## How to cite

In PR body (minimum template):

```text
Canon Lock: docs/architecture/CANON-LOCK.md (Wave-1)
Refs: ADR-010, RFC-004
Packs: docs/architecture/information-architecture/epic1-ia-readiness.md
Baseline: EPIC0 slug uniqueness = 0 dups (no invented metrics)
```

Prefer links to `docs/architecture/...` paths. Do not paste entire ADR bodies.

---

## Plane discipline (Canon C0)

| Plane | May cite as | Must not treat as |
|-------|-------------|-------------------|
| A — catalog pipeline + Git | SoT for transforms | “Docs author approved the SKU” |
| B — architecture docs | Decision/design intent | Runtime product Approver |
| C — DB/API | As-built verification | Permanent architecture without ADR |

---

## Status honesty

- Proposed/Draft docs may guide design; **Accepted** docs (listed in Canon Lock) bind implementation priority.  
- Do not upgrade Status in the same PR as feature work without Board minute **and** Canon Lock row update.  
- Audits are evidence — not policy licenses to skip ingestion rules.
