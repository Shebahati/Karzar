# Karzar Platform — Comprehensive Engineering Audit Plan

**Date:** 2026-07-25
**Scope:** Entire monorepo (`Shebahati/Karzar`) — backend, storefront, admin panel, database, infrastructure, processes.
**Posture:** Technical due-diligence style. Nothing assumed correct; everything verified against source.

---

## 1. System under audit (Phase 0 findings)

| Area | Technology | Size |
|------|-----------|------|
| Backend API | FastAPI (async), SQLAlchemy 2.0, Pydantic v2, Alembic | ~120 Python modules in `app/` |
| Storefront | Next.js (App Router), React 19, Tailwind, RTL Persian | `frontend/Storefront/` |
| Admin panel | Next.js, feature-sliced (`features/*`) | `frontend/admin-panel/` |
| Database | PostgreSQL 15 (JSONB specs, category tree), Redis | `alembic/versions/`, `app/db/models/` |
| Integrations | Hesabfa (accounting), Zarinpal + mock payments, OTP/SMS | `app/services/hesabfa/`, `payment_*` |
| Infra | Docker Compose on single VPS, self-hosted GH runner, staging≈production | `.github/workflows/`, `deploy/` |
| Ops scripts | ~35 import/seed/crawl scripts | `scripts/` |
| Tests | Pytest (~35 files, 62% coverage gate), Vitest on FE libs | `tests/`, `src/**/__tests__` |

Business context: Persian-language industrial tool supply (B2B/B2C). Inventory is
binary (available/unavailable) by business decision; warehouse counts live in
Hesabfa only. Payment gateway not yet live; orders include an inquiry flow.

## 2. Audit phases, order and rationale

Order principle: **foundation → data → logic → trust → experience → operations → quality**.
Architecture first because every later judgement depends on the intended structure.
Database before backend because commerce-logic defects are usually data-integrity
defects. Security after backend so the auditor knows the real entry points, not
the documented ones. Frontend after API contracts are understood. DevOps late
because it must validate what actually ships. Testing last of the domain phases
because it cross-checks every earlier finding ("is this risk covered by a test?").

| # | Phase | Report | Depends on |
|---|-------|--------|-----------|
| 1 | Architecture, repo structure, domain model, docs | `architecture-audit.md` | — |
| 2 | Database: models, migrations, integrity, indexing | `database-audit.md` | 1 |
| 3 | Backend: API, business logic, validation, integrations, concurrency, performance | `backend-audit.md` | 1, 2 |
| 4 | Security: OWASP Top 10, authn/authz, secrets, rate limiting, infra exposure | `security-audit.md` | 3 |
| 5 | Storefront: UX, UI consistency, accessibility (WCAG 2.2), SEO, semantic HTML, performance | `frontend-storefront-audit.md` | 1 |
| 6 | Admin panel: UX, workflows, code quality, state handling | `frontend-admin-audit.md` | 1 |
| 7 | DevOps/SRE: Docker, CI/CD, deploy, backups, observability, incident readiness | `devops-audit.md` | 1 |
| 8 | Testing, code quality, developer experience, documentation | `testing-quality-audit.md` | all |
| 9 | Master synthesis: merged findings, scores, roadmaps | `MASTER-ENGINEERING-REPORT.md` | 1–8 |

Phases 1–8 run as independent expert teams (parallel where dependencies allow);
each team is instructed to challenge assumptions and re-review its own report
before finishing. Phase 9 merges, deduplicates, resolves contradictions and
prioritizes.

## 3. Issue record format (mandatory for every finding)

Title · Severity (Critical/High/Medium/Low) · Category · Location (file:line) ·
Evidence · Why it is problematic · Root cause · Risk · Business impact ·
Technical impact · Recommended solution · Alternative solution · Estimated
effort (S/M/L/XL) · Priority (P0–P3) · Dependencies.

## 4. Scoring

Each phase scores its categories 0–10 with justification. The master report
aggregates: Architecture, Backend, Frontend, Database, Performance, Security,
UX, UI, SEO, Accessibility, DevOps, Testing, Developer Experience,
Maintainability, Scalability, Documentation, Overall Engineering.

## 5. Validation & checkpoints

- Every claim must cite a file path (and line where possible).
- Reports are re-read and self-challenged before being accepted.
- Contradictions between phase reports are resolved in the master report, not ignored.
- The audit is code-first; live-site observations are marked as such.

## 6. Deliverables

All reports land in `docs/audits/`. Final deliverable is
`MASTER-ENGINEERING-REPORT.md` with executive summary, scores, top issues by
priority, technical-debt register, and roadmaps (refactoring, architecture,
performance, security, UX, SEO, DevOps) plus an external-review verdict.
