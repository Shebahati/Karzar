# Wave-1 Documentation Promotion Record

**Status:** Completed (local tree)  
**Date:** ۱۴۰۵/۰۵/۰۷ (2026-07-29)  
**Board:** Architecture Board · Signed: محمد شباهتی / Mohammad Shebahati  
**Minute:** موج ۱ قفل EPIC 1 — تصمیم **الف** · Topic 5 تصمیم **ج** (promote now)

---

## What was promoted

From authoring tree `Website/docs/` → canonical repo docs `Website/backend/docs/`:

| Area | Paths under `backend/docs/` |
|------|------------------------------|
| Canon Lock | `architecture/CANON-LOCK.md` |
| Bible | `architecture/karzar-knowledge-platform-master-architecture.md` |
| ADR-010 / ADR-012 | `architecture/adr/` |
| RFC-004 / RFC-005 + index/template | `architecture/rfc/` |
| IA (EPIC 1 scope) | `architecture/information-architecture/` |
| Developer Standards | `development/standards/` |
| Git workflow | `development/git-development-workflow.md` |
| Ingestion policy | `architecture/data-ingestion-policy.md` |

**Not promoted:** Proposed packs (Domain, PIM, KG, AI, Search, Roadmap full, other ADRs/RFCs), audits, prompts.

---

## Canonical vs authoring (after promotion)

| Role | Path |
|------|------|
| **Canonical (normative Wave-1)** | `backend/docs/architecture/CANON-LOCK.md` and promoted siblings |
| **Authoring / extended packs** | `Website/docs/` (still holds Proposed packs + audits) |

Edits to Wave-1 **Accepted** criteria SHOULD land first in `backend/docs/` (or be copied in the same change set). Authoring tree files keep a promotion banner pointing here.

---

## Git next step (human)

Files are on disk under `backend/`. Commit/PR on branch `docs/*` when ready — **not auto-committed** by this promotion step unless Board requests commit separately.

Suggested commit subject:

```text
docs: promote Wave-1 Canon Lock (Accepted) into backend/docs
```
