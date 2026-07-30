# Task record — GOV-2026-07-30-cr022-availability-semantics

| Field | Value |
|-------|-------|
| **NODE_ID** | GOV-2026-07-30-cr022-availability-semantics |
| **PROMPT** | aods/70-prompts/gov/GOV-pmo-sync.prompt.md |
| **TASK_ID** | NONE — CR-008 |
| **CHANGE_CLASS** | C5 |
| **ARCHETYPE** | GOV |
| **STATUS** | COMPLETE — CR-022 CLOSED Option A |
| **Date** | 2026-07-30 |
| **HC** | HC-03 Option A |

## Goal

Close AODS `CR-022` Option A: align `FRONTEND_INTEGRATION.md` to binary `is_available`;
deprecation note in `API_CHANGELOG.md`; **D19**; PMO mirrors. No qty&lt;10 behaviour; no admin bulk migrate.

## Files changed

1. `aods/10-repository-intelligence/CONFLICT-REGISTER.md`
2. `docs/FRONTEND_INTEGRATION.md`
3. `docs/API_CHANGELOG.md`
4. `project-management/DECISIONS.md` (**D19**)
5. `project-management/CHANGELOG.md`
6. `project-management/DONE.md`
7. `aods/reports/tasks/GOV-2026-07-30-cr022-availability-semantics.md`

## Non-goals (honoured)

- No app/alembic behaviour change
- No admin bulk-path migrate (follow-up IMPL)
- No invent qty&lt;10 `low_stock`

## Verify

```text
AODS validation — 8 gate(s), base=origin/main
  PASS  registry             196 checked
  PASS  links                196 checked
  PASS  pmo                  28 checked
  PASS  prompts              11 checked
  PASS  graph                25 checked
  PASS  naming               864 checked
  SKIP  openapi              cannot import app.main — … ModuleNotFoundError: No module named 'fastapi'
  PASS  ingestion-boundary   42 checked

RESULT: PASS — 0 new findings, 0 baselined
EXIT:0
```
