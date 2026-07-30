# Wave-1 Documentation Promotion Record

**Status:** Completed (into this repository)  
**Date:** ۱۴۰۵/۰۵/۰۷ (2026-07-29)  
**Board:** Architecture Board · Signed: محمد شباهتی / Mohammad Shebahati  
**Minute:** موج ۱ قفل EPIC 1 — تصمیم **الف** · Topic 5 تصمیم **ج** (promote now)  
**SoR update:** ۱۴۰۵/۰۵/۰۸ (2026-07-30) — AODS `CR-009` Option B (binding SoR = this Git tree only)

---

## What was promoted

Historically copied from a local authoring tree `Website/docs/` into the canonical Git docs
(now at repository root `docs/`, formerly described as `Website/backend/docs/`):

| Area | Paths under `docs/` |
|------|----------------------|
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

## Canonical vs authoring (after `CR-009` Option B)

| Role | Path |
|------|------|
| **Canonical (normative Wave-1 + AODS)** | This repository: `docs/architecture/CANON-LOCK.md`, promoted siblings, and `aods/` |
| **Unpromoted drafts outside Git** | Historical local `Website/docs/` — **not** Authoring SoR; **not** citeable for merge criteria until Board promotes files into this repo (`CR-009` B). Importing that tree remains future **Option A**. |

Edits to Wave-1 **Accepted** criteria MUST land in this repository. Do not treat an external mirror as authoritative.

---

## Git next step (human)

Wave-1 promotion is on `main`. Further pack promotions require Board minute + Canon Lock row updates in the same change set.
