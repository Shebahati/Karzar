# Karzar Platform — Engineering Audit v2 Plan (STRICT MODE)

**Date:** 2026-07-25
**Scope:** Entire monorepo (`Shebahati/Karzar`) — backend, storefront, admin panel, database, infrastructure, processes, **and all documentation as a first-class audit subject**.
**Posture:** Hostile due-diligence before a multi-million-dollar acquisition. A category earns a high score only with proof. Where v1 was generous, that is said explicitly and re-scored.
**Baseline:** v1 audit (2026-07-25, `docs/audits/`, overall 6.8/10) — treated as a baseline to beat *and* as an audit subject itself (missed findings, incorrect claims, generous scores).

---

## 1. What changed vs v1

| # | Change | Rationale |
|---|--------|-----------|
| 1 | **New dedicated phase: Documentation audit** (`documentation-audit.md`) | v1 scored Documentation 7.0 from two phases' side-glances without systematically verifying doc claims against code. The doc corpus is ~8,200 lines across 30+ files; README alone makes verifiable claims about security, performance, testing, and inventory semantics. Doc-vs-reality drift is now a mandatory finding class in *every* phase. |
| 2 | **Strictest grading** | v1 graded "for a two-person team at this stage." v2 grades against an acquisition bar: no benefit of the doubt, no "provisional" scores without evidence (v1's Accessibility 7.0 "provisional" is exactly the kind of ungrounded score v2 forbids). Every score must cite proof; every v1 delta must be justified. |
| 3 | **v1 reports are themselves audited** | Each phase reads its v1 counterpart and lists: (a) findings v1 missed, (b) claims v1 got wrong, (c) scores v1 inflated/deflated. |
| 4 | **Doc corpus enumerated up front** (see §3) | v1's plan never listed the docs; several (KNOWLEDGE_PLATFORM_*, BACKEND_COMPREHENSIVE_AUDIT_PLAYBOOK, frontend/BACKEND_NON_COMPLIANCE.md, frontend/docs/gaps/*) were never mentioned in any v1 report. |

## 2. System under audit (Phase 0 verification, re-confirmed for v2)

| Area | Technology | Size / location |
|------|-----------|-----------------|
| Backend API | FastAPI (async), SQLAlchemy 2.0 async, Pydantic v2, Alembic | 125 Python modules, ~15,400 LOC in `app/` |
| Storefront | Next.js App Router, React 19, Tailwind, RTL Persian | `frontend/Storefront/` |
| Admin panel | Next.js, feature-sliced | `frontend/admin-panel/` |
| Database | PostgreSQL 15 (JSONB specs, category tree), Redis | `alembic/versions/`, `app/db/models/` |
| Integrations | Hesabfa (accounting), Zarinpal + mock payment, OTP/SMS | `app/services/` |
| Infra | Docker Compose, single VPS, self-hosted runner; 3 workflows (`backend-ci`, `deploy-staging`, `deploy-production`) | `.github/workflows/`, `deploy/` |
| Ops scripts | 37 scripts incl. pricing/import/crawl/backup | `scripts/` |
| Docs | ~8,200 lines: root README + SECURITY.md, 22 files in `docs/`, 8 files in `frontend/` root, `frontend/docs/` (audits/deploy/gaps + auth contract), per-app READMEs, `openapi/v1.json`, `.env.example`s, v1 audit reports | everywhere |
| Repo state at audit | branch `docs/engineering-audit-2026-07` @ `66e9ae9` (v1 audit committed, **not merged to `origin/main`**, whose tip is `0cc782e`) | — |

Business context (unchanged): Persian-language industrial tool commerce (B2B/B2C), ~5,900 products / 40 brands / 159 categories, **binary availability** by business decision (counts live in Hesabfa), payment gateway not yet live, inquiry-order flow, live at karzartools.com + admin.karzartools.com.

## 3. Documentation corpus (mandatory reading, mapped to phases)

| Corpus | Primary phase | Also read by |
|--------|--------------|--------------|
| `README.md` (559 lines), `SECURITY.md` | Documentation | Security, Backend |
| `docs/API_CONTRACT.md`, `API_CHANGELOG.md`, `openapi/v1.json` | Documentation | Backend |
| `docs/ARCHITECTURE.md`, `BACKEND_STRUCTURE_REFACTOR_MAP.md`, `BACKEND_COMPREHENSIVE_AUDIT_PLAYBOOK.md`, `KNOWLEDGE_PLATFORM_PHASE{1,2,3}_*.md` | Architecture | Documentation |
| `docs/OPERATIONS.md`, `GO_LIVE_EXECUTION_PLAN.md`, `COLLABORATOR_DEPLOY.md`, workflow YAMLs, `deploy/` | DevOps | Documentation |
| `docs/HESABFA.md`, `SEED_IMPORT.md`, `BACKEND_CHANGES.md` | Backend | Documentation |
| `docs/TESTING.md`, `pytest.ini`, `pyproject.toml` | Testing | Documentation |
| `docs/FRONTEND_*.md`, `docs/LOCAL_DEV_FRONTEND.md`, `frontend/*.md` (8 files incl. `AI_CONTEXT.md` 1,044 lines, `BACKEND_NON_COMPLIANCE.md` 647 lines), `frontend/docs/**` (audits/deploy/gaps/auth-cookie contract), app READMEs, `AGENTS.md`/`CLAUDE.md` | Frontend phases | Documentation |
| `.env.example` files (root + both frontends) | Security | DevOps, Documentation |
| `docs/audits/*.md` (v1 reports, 9 files) | **every phase** (own counterpart) | Master |

**Drift rule:** every significant doc claim (a claim a reader would act on: security posture, inventory semantics, endpoints/schemas, deploy behavior, test counts, coverage numbers, env vars) must be verified against code and dated behavior. Unverifiable marketing claims ("production-ready", "comprehensive") are graded as documentation defects when contradicted by evidence.

## 4. Phase order and rationale

Same dependency spine as v1 (foundation → data → logic → trust → experience → operations → quality) — that ordering logic was sound — with two changes: the **Documentation phase runs early** (right after Architecture) because its drift findings feed every later phase's "docs say X, code does Y" checks; and phases run as parallel independent expert teams once shared Phase-0 context exists, since each writes to its own report and cross-phase contradictions are resolved only in the master report.

| # | Phase | Report (all under `docs/audits/v2/`) | v1 counterpart to critique |
|---|-------|--------------------------------------|---------------------------|
| 0 | Full repo + doc read-through (no conclusions) | — | — |
| 1 | This plan | `00-audit-plan-v2.md` | `00-audit-plan.md` |
| 2a | Architecture & repo structure | `architecture-audit.md` | same name |
| 2b | **Documentation (NEW)** | `documentation-audit.md` | none — synthesized from v1 scattered remarks |
| 2c | Database | `database-audit.md` | same name |
| 2d | Backend | `backend-audit.md` | same name |
| 2e | Security | `security-audit.md` | same name |
| 2f | Storefront (UX + WCAG 2.2 + SEO + semantic HTML + structured data) | `frontend-storefront-audit.md` | same name |
| 2g | Admin panel | `frontend-admin-audit.md` | same name |
| 2h | DevOps/SRE (Docker, CI/CD, backups, observability) | `devops-audit.md` | same name |
| 2i | Testing & quality (tests, SOLID/DRY/KISS/YAGNI, DX) | `testing-quality-audit.md` | same name |
| 3 | Master synthesis: dedupe, contradiction resolution, scores vs v1, roadmaps, external-reviewer verdict | `master-engineering-report-v2.md` | `master-engineering-report.md` |

Each phase self-reviews before finishing: "what did I miss? what did v1 miss? what would a hostile reviewer add?"

## 5. Issue record format (mandatory, unchanged from v1)

Title · Severity (Critical/High/Medium/Low) · Category · Location (file:line) · Evidence (quoted) · Why problematic · Root cause · Risk · Business impact · Technical impact · Recommended solution · Alternative · Effort (S/M/L/XL) · Priority (P0–P3) · Dependencies.

## 6. Scoring (0–10, strict)

Categories: Architecture, Backend, Frontend (split storefront/admin), Database, Performance, Security, UX, UI, SEO, Accessibility, DevOps, Testing, Developer Experience, Maintainability, Scalability, **Documentation**, Overall Engineering.

Strict rubric anchors: 9–10 = provably excellent, would pass FAANG/Stripe review with minor nits; 7–8 = solid with named, bounded gaps; 5–6 = works but with systemic weaknesses a due-diligence team would price in; 3–4 = material risk / partially broken; 0–2 = unfit. **Every score states the v1 score and justifies the delta.** "Provisional" scores are banned: if evidence is missing, score what the evidence supports and say what's unverified.

## 7. Rules of engagement

1. Cite file paths (+lines) for every claim; read files before judging them.
2. Challenge every architectural decision; hunt hidden coupling, hidden debt, scalability bottlenecks, future failure modes, hidden bugs. Never stop at the obvious.
3. Doc-vs-reality drift is a mandatory finding class in every phase.
4. Code-first; live-site checks optional and labeled as live observations.
5. Do NOT modify application code. Only write files under `docs/audits/v2/`.
6. After each phase, self-review the report for gaps before continuing.
7. Ship: docs-only branch → PR `docs(audits): strict v2 engineering audit incl. documentation review` → CI green → merge. Note: the v2 branch necessarily contains the unmerged v1 audit commit `66e9ae9` (also docs-only); the PR therefore delivers both audit generations to `main`.
