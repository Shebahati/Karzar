# CI risk classification

Single source of truth:

- Policy: `policy.json`
- Interpreter: `scripts/ci/classify_changes.py` (default-deny: unknown paths → **FULL**)

## Risk tiers

| Tier | Meaning |
|------|---------|
| R0 | Docs/audit/aods registry governance only — required checks skip Postgres, Redis, Playwright |
| R1 | One stack, light work — no backend integration DB |
| R2 | Backend code — full pytest with `--cov-fail-under=68` |
| R3 | Critical paths (payment/auth/deploy/migrations/apply scripts) — strong backend + OpenAPI + targeted frontend/e2e |
| FULL | Conservative (workflows, unknown paths, `ci:full` label, nightly regression) |

## Escape hatches

- PR label **`ci:full`** — forces FULL tier (never reduces checks).
- Workflow **`CI Full Regression`** — `workflow_dispatch` or nightly schedule.

## Required checks (Protect main)

Job **names** stay stable: `aods`, `lint`, `test`, `storefront`, `admin-panel`, `storefront-e2e`, `Collaborator Scope Gate`, `workflow-lint`. Skipped work is an explicit step, not a missing check.

Auto-merge: repository `allow_auto_merge` is documented in `docs/OPERATIONS.md`; remain **disabled** until owner enables with these gates unchanged.
