# Task record — GOV-2026-07-30-cr020-bilingual-doc-pairs

| Field | Value |
|-------|-------|
| **NODE_ID** | GOV-2026-07-30-cr020-bilingual-doc-pairs |
| **PROMPT** | aods/70-prompts/gov/GOV-pmo-sync.prompt.md |
| **TASK_ID** | NONE — CR-008 (no PMO task; conflict-register close) |
| **CHANGE_CLASS** | C5 |
| **ARCHETYPE** | GOV |
| **STATUS** | COMPLETE — CR-020 CLOSED Option A |
| **Date** | 2026-07-30 |
| **HC** | HC-03 (human chose Option A; no settings path named) |

## Goal

Close AODS `CR-020` under HC-03 **Option A**: bilingual normative roles (EN contracts / FA operator
deploy); `translated_from` / `normative_role` headers; site-settings proposals marked **non-Canon**;
`DEPLOYMENT_en.md` aligned to one-VPS (`CR-011`); record **D18**; mirror CHANGELOG/DONE.

## Files changed

1. `aods/10-repository-intelligence/CONFLICT-REGISTER.md` — summary → CLOSED; DECISION append; changelog
2. `frontend/docs/gaps/01-fe-ahead-be-needed-en.md` — normative_role + non-Canon settings banner
3. `frontend/docs/gaps/01-fe-ahead-be-needed-fa.md` — companion + translated_from + non-Canon settings row
4. `frontend/docs/gaps/02-be-exists-fe-should-use-en.md` — normative_role + FA-ahead note
5. `frontend/docs/gaps/02-be-exists-fe-should-use-fa.md` — companion + translated_from
6. `frontend/docs/deploy/DEPLOYMENT_en.md` — one-VPS binding; split-host = optional growth
7. `frontend/docs/deploy/DEPLOYMENT_fa.md` — operator normative + CR-011 note
8. `project-management/DECISIONS.md` — **D18**
9. `project-management/CHANGELOG.md` — append
10. `project-management/DONE.md` — append (+ PR links for CR-017/019)
11. `aods/reports/tasks/GOV-2026-07-30-cr020-bilingual-doc-pairs.md` — this record

## Non-goals (honoured)

- No API implementation; no Accepted path for site-settings
- No CR-022 / CR-005 / app code
- CONFLICT-REGISTER evidence rows not rewritten (DECISION appended)
- No push / merge / deploy / commit in this node

## Verify

```text
AODS validation — 8 gate(s), base=origin/main
  PASS  registry             195 checked
  PASS  links                195 checked
  PASS  pmo                  28 checked
  PASS  prompts              11 checked
  PASS  graph                25 checked
  PASS  naming               863 checked
  SKIP  openapi              cannot import app.main — … ModuleNotFoundError: No module named 'fastapi'
  PASS  ingestion-boundary   42 checked

RESULT: PASS — 0 new findings, 0 baselined
EXIT:0
```
