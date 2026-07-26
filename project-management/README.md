# Karzar Project Management Office (PMO)

**Single Source of Truth** for planning, tracking, and release readiness.

- **Deadline checkpoint:** 31 شهریور ۱۴۰۵ ≈ **2026-09-22**
- **As-of:** 2026-07-26
- **Machine SoT:** `exports/tasks.json` (update this first, then regenerate markdown if needed)
- **Human SoT:** this folder’s markdown checklists

## How agents must use this

1. Before coding: read `PROJECT_STATUS.md` + current `sprints/SPRINT_XX.md`
2. Pick a task ID from `exports/tasks.json` / `KANBAN_BOARD.md`
3. After finishing work: update task `status`/`progress`, then touch related `*_PROGRESS.md`, `CHANGELOG.md`, `DONE.md`
4. Never leave code shipped without PMO update (enforced by Cursor rule `.cursor/rules/pmo-living-system.mdc`)

## Layout

| Path | Role |
|------|------|
| `MASTER_ROADMAP.md` | Living outcomes to checkpoint |
| `PROJECT_STATUS.md` | Current truth |
| `EXECUTIVE_SUMMARY.md` | Hours/LOC realism for 31 Shahrivar |
| `exports/` | ClickUp / Taskulu / GitHub / JSON |
| `printable/` | Wall-track HTML (A4/A3) |
| `diagrams/` | Mermaid sources |
| `sprints/` | Sprint_00…04 |
| `progress/` | Domain progress ledgers |

## Progress (weighted by hours)

**~25%** of tracked backlog hours claimed · **300h** estimated · **170h** P0
