# Git Development Workflow

**Document type:** Branch governance standard  
**Migration ID:** `KARZAR-BASELINE-20260728-001`  
**Date:** 2026-07-29  
**Canonical repo:** `https://github.com/Shebahati/Karzar.git`  
**Primary checkout:** `/home/moahmmad/Projects/Karzar/Website/backend`  
**Owner:** Mohammad Shebahati

---

## Purpose

Governed development after production→local baseline: protect `main`, require PRs, separate schema (Alembic) and production deploy from day-to-day coding.

---

## Branch model

```
main
 │
 ├── feature/*     ← new capabilities
 ├── fix/*         ← bug fixes
 └── hotfix/*      ← urgent production fixes (from tagged main)
```

Optional prefixes also allowed: `chore/*`, `docs/*` (same PR rules).

**Legacy / carve-outs (`CR-002` Option A, 2026-07-30):** do not create new `feat/*` branches.
Existing remote `feat/*` names are grandfathered until deleted (no mass-rename). Cloud Agent
`cursor/*` is platform-imposed and allowed when the execution platform requires it.

### `main`

| Rule | Detail |
|------|--------|
| Role | Protected integration / release line |
| Direct commits | **Forbidden** for feature work |
| Updates | Merge via **PR only** |
| Protection | CI green · review · no force-push |
| Baseline tags | Annotated tags from `main` only |

### `feature/*`

- Branch from up-to-date `main`.
- One concern per branch / PR.
- Merge back to `main` via PR; delete branch after merge.

### `fix/*`

- Same as feature; reserved for defect correction.

### `hotfix/*`

- Branch from annotated production/baseline tag or current `main`.
- Minimal diff; expedited review still required.
- Back-merge to `main` if needed.

---

## Current migration hangover (temporary)

| Item | Value |
|------|-------|
| Primary checkout branch | `chore/phase9-align-origin-main` (= `origin/main` @ `6e56431`) |
| Blocker | Worktree `backend-stat-fix` holds local `main` (22 behind) |
| Worktrees | 45 — see `docs/audits/worktree-cleanup-execution-plan.md` |
| Target end-state | Primary on `main`; retire Phase 9 stand-in |

Until unlock: treat `chore/phase9-align-origin-main` as the stand-in for `main` content; still use feature branches for new work.

---

## Hard rules

1. **No direct development on `main`.** Always branch.
2. **PR required** for every change intended for `main`.
3. **Migration / baseline docs** changes reviewed like code (governance pack).
4. **Database schema changes require an Alembic migration** — no hand-edits to prod/local schema outside Alembic.
5. **Production deploy is separated from development:**
   - Develop & verify on local replica (`karzar_db`, API `127.0.0.1:8000`).
   - Promote: Git merge → local/staging verify → Alembic on target → production.
   - Never: local script → production DB/API without Category-B authorization.
6. **No automatic push** from agents; human approves push.
7. **Destructive git actions** (worktree remove, branch `-D`, reset) need a written plan + confirmation.
8. **Never commit** `.env`, dumps (`*.sql*`), archives (`*.tar.gz`), `uploads/`, `backups/`.

---

## Day-to-day flow

```
1. git fetch origin && git checkout main && git pull --ff-only   # after main unlocked
2. git checkout -b feature/<ticket>-short-name
3. Implement + test against local baseline (5901 / c4d5e6f7a8b9 starting point)
4. If schema: alembic revision + upgrade local only
5. Open PR → review → CI → merge
6. Deploy path separate from coding (ops runbook)
```

Catalog writers must use:

`KARZAR_API_BASE=http://127.0.0.1:8000/api/v1`

**Developer standards pack:** `docs/development/standards/` (DoD, PR checklist, Alembic/API/FE, enrichment) — **Accepted** Wave-1.

**Canon Lock (binding criteria index):** `docs/architecture/CANON-LOCK.md` — every `main`-bound PR in Wave-1 scope MUST cite relevant Accepted/Binding rows (see `pr-checklist.md` / `documentation-citation-rules.md`).
---

## Worktrees

| Rule | Detail |
|------|--------|
| Default | One primary tree on `main` |
| Extra | Only for concurrent PR isolation |
| Nested | Do not `git add` linked worktrees (e.g. `backend-pmo/`) from parent |
| Cleanup | Follow execution plan — confirm before remove |

---

## Baseline immutability

| Tag | Target | Status |
|-----|--------|--------|
| `KARZAR-BASELINE-20260728` | `6e56431` | Prepared — evidence note historically pointed at `docs/audits/baseline-tag-readiness.md` (**not in this repo** — `CR-010`) |

Rollback uses the tag for **code**; DB restore uses off-host dumps — not the tag alone.

---

## Repo boundary

| Path | Role |
|------|------|
| This repository (`Shebahati/Karzar` — `docs/`, `aods/`, `app/`, …) | **Sole source of record** for binding criteria, PRs, and agent context |
| Historical `Website/docs/` (outside this checkout) | **Not** Authoring SoR for merge criteria (`CR-009` Option B, 2026-07-30). May hold unpromoted drafts on a local machine only; promote into this repo before citing |
| `/home/moahmmad/Projects` | Unrelated local git — **not** Karzar remote |

---

## Related

In-repo (prefer these):

- [`docs/architecture/CANON-LOCK.md`](../architecture/CANON-LOCK.md)
- [`docs/architecture/PROMOTION-WAVE1.md`](../architecture/PROMOTION-WAVE1.md)
- [`docs/development/standards/`](standards/)

Paths formerly listed here but **not present** in this repository (do not cite until promoted — `CR-010`):

- `docs/development/local-baseline-environment.md`
- `docs/development/documentation-index.md`
- `docs/architecture/development-lifecycle-standard.md` / `docs/development/development-lifecycle-standard.md`
- `docs/audits/final-repository-state-audit.md`
- `docs/roadmap/post-migration-development-plan.md`
