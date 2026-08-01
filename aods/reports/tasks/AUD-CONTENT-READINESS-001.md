# Task record — AUD-CONTENT-READINESS-001

| Field | Value |
|-------|-------|
| NODE_ID | AUD-CONTENT-READINESS-001 |
| Archetype | AUD |
| Prompt | aods/70-prompts/audit/AUD-repository-scan.prompt.md |
| Date | 2026-07-30 |
| TASK_ID | NONE — CR-008 (spans SEO-003/CAT-002/KB-001/SEO-008/FE-002) |
| Change class | C0 |
| Scope lock | Definition A (human-approved) |
| Allowlist writes | `aods/reports/audits/AUD-CONTENT-READINESS-001.md`, `aods/reports/tasks/AUD-CONTENT-READINESS-001.md` |

## Inputs read

- `aods/10-repository-intelligence/AUTHORITY-MODEL.md` (FULL — authority classes / evidence)
- `aods/10-repository-intelligence/REPOSITORY-AUDIT.md` (SKIM — content §2.3, PMO open tasks, gaps G-01/G-07)
- `aods/registry/document-registry.yaml` (classification for scope docs)
- SCAN_SCOPE paths listed in the audit report

## Outputs

- Findings: `aods/reports/audits/AUD-CONTENT-READINESS-001.md`
- This task record

## Validation notes

- `gh pr view 90` failed (network reset) → PR #90 state marked UNVERIFIABLE in audit.
- Production/live DB counts not queried (ADR-012 / no prod) → product-count Unknowns.
- `python3 aods/tools/aods_validate.py --gate links` and `--gate registry` run at VERIFY; paste in agent VERIFY block.

## Status

COMPLETE (report-only; no subject files modified)
