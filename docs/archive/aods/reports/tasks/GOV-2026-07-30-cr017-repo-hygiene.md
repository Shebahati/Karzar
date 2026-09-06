# Task record — GOV-2026-07-30-cr017-repo-hygiene

| Field | Value |
|-------|-------|
| **NODE_ID** | GOV-2026-07-30-cr017-repo-hygiene |
| **PROMPT** | aods/70-prompts/gov/GOV-pmo-sync.prompt.md |
| **TASK_ID** | NONE — CR-008 (no PMO task; conflict-register close) |
| **CHANGE_CLASS** | C5 |
| **ARCHETYPE** | GOV |
| **STATUS** | COMPLETE — CR-017 CLOSED Option B |
| **Date** | 2026-07-30 |
| **HC** | HC-03 (human chose Option B) |

## Goal

Close AODS `CR-017` under HC-03 **Option B**: policy/defer deletes — acknowledge residual branch/worktree
debt; refresh hangover to cite live `git branch -r --no-merged origin/main` and `git worktree list`
instead of missing `docs/audits/worktree-cleanup-execution-plan.md`; record **D17**; mirror CHANGELOG/DONE.
No mass deletes / worktree remove in this node.

## Live measurement (this checkout, 2026-07-30)

| Command | Result |
|---------|--------|
| `git branch -r --no-merged origin/main \| wc -l` | 62 |
| `git worktree list \| wc -l` | 1 (primary on `main`) |

## Files changed

1. `aods/10-repository-intelligence/CONFLICT-REGISTER.md` — summary → CLOSED; DECISION append; register changelog
2. `docs/development/git-development-workflow.md` — hangover + Worktrees Cleanup row (live-command cites)
3. `project-management/DECISIONS.md` — **D17**
4. `project-management/CHANGELOG.md` — append
5. `project-management/DONE.md` — append
6. `aods/reports/tasks/GOV-2026-07-30-cr017-repo-hygiene.md` — this record

## Non-goals (honoured)

- No `git push` / merge / rebase / reset --hard / deploy
- No unilateral destructive git (`worktree remove`, `branch -D`)
- No mass-rename `feat/*`
- No `app/` / `frontend/` / `alembic/` / `scripts/` behaviour changes
- CONFLICT-REGISTER evidence paragraphs not rewritten (DECISION + status only)
- Did not invent `worktree-cleanup-execution-plan.md`
- No commit / push in this node
- `tasks.json` untouched (`TASK_ID: NONE`)

## Verify

```text
$ python3 aods/tools/aods_validate.py
AODS validation — 8 gate(s), base=origin/main
  PASS  registry             194 checked
  PASS  links                194 checked
  PASS  pmo                  28 checked
  PASS  prompts              11 checked
  PASS  graph                25 checked
  PASS  naming               862 checked
  SKIP  openapi              cannot import app.main — dependencies not installed; run with requirements.txt installed (File "/home/moahmmad/Projects/Karzar-clean/Karzar/app/main.py", line 7, in <module> | from fastapi import FastAPI, Request, status | ModuleNotFoundError: No module named 'fastapi')
  PASS  ingestion-boundary   42 checked

RESULT: PASS — 0 new findings, 0 baselined
EXIT:0
```

## Debt noticed (not fixed — outside allow-list)

- `project-management/TECH_DEBT.md` still lists open CR-017 checkbox (58 branches / 45 worktrees)
- CONFLICT-REGISTER orphans table still lists `worktree-cleanup-execution-plan.md` as referenced by git-development-workflow (evidence row; not rewritten)
- 62 unmerged remotes remain (acknowledged residual under Option B)
