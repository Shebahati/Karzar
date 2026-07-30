# Karzar Developer Standards

**Document type:** Engineering Standards Pack (primary)  
**Status:** **Accepted** (Wave-1 EPIC-1 Canon Lock)  
**Version:** 0.1  
**Date:** 2026-07-29  
**Parents:** `git-development-workflow.md` · `development-lifecycle-standard.md` · `data-ingestion-policy.md` · ADR/RFC packs · Data Governance  
**Repo:** `https://github.com/Shebahati/Karzar.git` · Checkout: `Website/backend`

### Board Acceptance (Wave 1)

| Field | Value |
|-------|-------|
| **Accepted on** | ۱۴۰۵/۰۵/۰۷ (2026-07-29) |
| **Board** | Architecture Board |
| **Signed** | محمد شباهتی / Mohammad Shebahati |
| **Minute** | موج ۱ قفل EPIC 1 — تصمیم **الف** |
| **Scope** | Primary developer standards; PR gates must cite relevant Accepted ADR/RFC. |

---

## 0. Document Control

| Item | Value |
|------|-------|
| Owner | Platform / Staff Engineering (logical) |
| Change control | Docs-only in Prompt 11; no app/CI mutation here |
| Companions | `docs/development/standards/*` |

---

## 1. Purpose, Scope, Non-Goals

### Purpose

Make Architecture, ADRs, and RFCs **actionable in daily engineering**: how to start work, when to cite decisions, how to PR, how to touch schema/API/frontend/enrichment safely on the local baseline.

### Scope

Principles, workflow entry, DoD, PR gates, citation, local enrichment, Alembic, API/FE rules, testing, secrets.

### Non-Goals

- Refactoring application code or CI configs in this prompt  
- Accepting ADRs/RFCs by fiat  
- Weakening ingestion policy  
- Implementing EPIC 1 features here  

---

## 2. Engineering Principles

| ID | Principle |
|----|-----------|
| S1 | Small PRs — one concern per branch |
| S2 | Measure / cite before claiming (EPIC 0 / DQ; no invented metrics) |
| S3 | SoT citation — Plane A/B/C discipline (ADR-001) |
| S4 | Local first — Category A enrichment; production is not a sandbox |
| S5 | Schema via Alembic only |
| S6 | Architecture before cleverness — read Bible → ADR/RFC → Domain/IA when meaning/URLs change |
| S7 | Honest UI — empty PDF/accessories slots remain |
| S8 | FA pitfalls — display strings ≠ Property identity |
| S9 | Performance — principle-level budgets; no premature micro-opts |
| S10 | Repo lock intent — PR + protection; no force-push to main |

---

## 3. How to start work

```text
1. Read requirement / ticket
2. Skim Master Architecture Bible (orientation)
3. Open relevant ADR / RFC (Accepted preferred; Draft = design risk)
4. If meaning → Domain pack; if URLs → IA + ADR-010/RFC-004/005
5. If specs keys → Property governance + ADR-004
6. If AI → ADR-009 gates
7. Branch from mainline: feature/* | fix/* | hotfix/* | chore/* | docs/*
8. Implement on local baseline → test → PR with citations + rollback
```

Lifecycle normative path: Requirement → Architecture Decision → Git Branch → Code Review → Local Dev DB → Testing → Alembic (if needed) → Production Deploy (`development-lifecycle-standard.md`).

---

## 4. Branch naming

Align with `git-development-workflow.md`:

| Prefix | Use |
|--------|-----|
| `feature/*` | New capability |
| `fix/*` | Defect |
| `hotfix/*` | Urgent production |
| `chore/*` | Maintenance |
| `docs/*` | Documentation |

Do not open new `feat/*` branches (`CR-002` Option A). Historical `feat/*` remotes are grandfathered until deleted. `cursor/*` is a Cloud Agent carve-out only.

No direct development on `main`. Temporary Phase-9 stand-in may track main content until unlock — still branch for new work.

---

## 5. Environments & catalog mutation classes

See [`local-development-and-enrichment.md`](./local-development-and-enrichment.md).

| Class | Default |
|-------|---------|
| Read-only analytics | Allowed |
| Local API writes (Category A) | Allowed with versioned job |
| Production routine enrichment | **Forbidden** |
| Category B production | Ticket + backup + declaration only |

`KARZAR_API_BASE` for Category A = **local**.

---

## 6. Logging & observability (minimum)

- API: structured errors without secrets.  
- Enrichment: job id, git ref, env, counts, validation, errors.  
- Migrations: revision id applied, env.  
- SEO: monitor 301/404 rates post-deploy (ops).

---

## 7. Error handling & user impact

- Storefront: prefer clear empty/error states over silent omission of IA-required regions.  
- API: stable error codes; no partial success without documentation.  
- Enrichment: fail-closed on unexpected delta when supported.

---

## 8. i18n / FA pitfalls

- Persian labels are **aliases/display**, not separate Properties (ADR-004).  
- Do not ship UI that treats `دقت` and `accuracy` as different facets long-term.  
- Avoid hard-coding operational `top:*` into customer spec tables.

---

## 9. Performance budgets (principles)

- Optimize measured bottlenecks (PDP/hub TTFB, search p95) — not speculative memoization.  
- Hybrid/vector search follows RFC-006 gates; don’t add RAG latency for ungated demos.  
- Images: don’t load fake galleries.

---

## 10. Pack map

| Need | Doc |
|------|-----|
| DoD | [`definition-of-done.md`](./definition-of-done.md) |
| PR gate | [`pr-checklist.md`](./pr-checklist.md) |
| Citations | [`documentation-citation-rules.md`](./documentation-citation-rules.md) |
| Local / enrich | [`local-development-and-enrichment.md`](./local-development-and-enrichment.md) |
| Schema | [`alembic-and-schema-change-rules.md`](./alembic-and-schema-change-rules.md) |
| API | [`api-change-rules.md`](./api-change-rules.md) |
| Frontend | [`frontend-change-rules.md`](./frontend-change-rules.md) |
| Tests | [`testing-and-verification.md`](./testing-and-verification.md) |
| Secrets | [`security-and-secrets.md`](./security-and-secrets.md) |

---

## 11. Open Questions

1. CI template to auto-comment PR checklist?  
2. Required reviewers by path (`alembic/**`, `scripts/**`)?  
3. When Phase-9 stand-in retires — update this pack pointer only?

---

## 12. Acceptance Self-Check

| Check | Result |
|-------|--------|
| Eleven required files | Yes |
| DoD + PR checklist actionable | Yes |
| Ingestion boundary unavoidable | Yes |
| Alembic rules explicit | Yes |
| ADR/RFC citation required when relevant | Yes |
| No app/code/git mutation in this prompt | Yes |
| Next = Prompt 12 Repository Governance v2 | Yes |

### Quality bar Q1–Q6

**PASS**
