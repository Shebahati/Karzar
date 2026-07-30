# Developer Standards Pack — Karzar

**Status:** **Accepted** (Wave-1 EPIC-1 Canon Lock)  
**Parents:** Git workflow · Development lifecycle · Ingestion policy · ADR/RFC packs  
**Repo:** `https://github.com/Shebahati/Karzar.git` · Primary checkout: `backend/`

### Board Acceptance (Wave 1)

| Field | Value |
|-------|-------|
| **Accepted on** | ۱۴۰۵/۰۵/۰۷ (2026-07-29) |
| **Board** | Architecture Board |
| **Signed** | محمد شباهتی / Mohammad Shebahati |
| **Minute** | موج ۱ قفل EPIC 1 — تصمیم **الف** |
| **Scope** | Binding engineering DoD / PR checklist / citation rules for all PRs; enrichment and Alembic discipline. |

## Files

| File | Role |
|------|------|
| [`karzar-developer-standards.md`](./karzar-developer-standards.md) | Primary |
| [`definition-of-done.md`](./definition-of-done.md) | DoD checklists by PR type |
| [`pr-checklist.md`](./pr-checklist.md) | PR gate checklist |
| [`documentation-citation-rules.md`](./documentation-citation-rules.md) | When to cite Bible/ADR/RFC |
| [`local-development-and-enrichment.md`](./local-development-and-enrichment.md) | Local baseline + Category A |
| [`alembic-and-schema-change-rules.md`](./alembic-and-schema-change-rules.md) | Schema discipline |
| [`api-change-rules.md`](./api-change-rules.md) | API contracts |
| [`frontend-change-rules.md`](./frontend-change-rules.md) | Storefront / SEO URLs |
| [`testing-and-verification.md`](./testing-and-verification.md) | Test expectations |
| [`security-and-secrets.md`](./security-and-secrets.md) | Secrets & safety |

**Hard rules:** No production enrichment · `KARZAR_API_BASE` local for Category A · Alembic for schema · PRs cite ADR/RFC when relevant · No app code mutation in this prompt.
