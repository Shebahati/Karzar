---
id: GOV-pmo-sync
version: 0.1.0
archetype: GOV
role: ROLE-PMO
capability_class: STRUCTURED-EXTRACT
reasoning_depth: R1
decision_ceiling: D1
lifecycle_state: Draft
parameters:
  - NODE_ID
  - TASK_ID
  - NEW_STATUS
  - NEW_PROGRESS
  - PR_LINK
  - NOTE
context_tiers:
  T1: [.cursor/rules/pmo-living-system.mdc]
  T2: [project-management/exports/tasks.json, project-management/PROJECT_STATUS.md, project-management/CHANGELOG.md]
  T3: [project-management/sprints/]
forbidden_context:
  - frontend/AI_CONTEXT.md
  - frontend/BACKEND_NON_COMPLIANCE.md
  - frontend/BACKEND_HANDOFF.md
  - docs/GO_LIVE_EXECUTION_PLAN.md
  - docs/audits/v1/
  - docs/audits/v2/SCORECARD-AFTER-REMEDIATION.md
gates: [pmo, links, allowlist]
produces: [TASK-ENTRY, TASK-RECORD]
supersedes: null
---

## 1. AUTO MODE PROTOCOL — READ FIRST, OBEY EXACTLY

You are executing a single AODS node in Cursor Auto Mode. You have no memory of prior
sessions and there will be no follow-up conversation. This file is your entire brief.

HARD PROHIBITIONS (violating any one makes your output non-compliant and it will be discarded):
1. Do NOT modify, create, or delete any file outside ALLOWED SCOPE below.
2. Do NOT read any file listed under FORBIDDEN CONTEXT.
3. Do NOT refactor, reformat, rename, or "clean up" anything not required by the TASK.
4. Do NOT add, remove, or upgrade any dependency. That is a D3 decision — HALT instead.
5. Do NOT run git push, git merge, git rebase, git reset --hard, or any deploy command.
6. Do NOT invent a requirement. Every requirement you implement must be citable as path:line.
7. Do NOT claim a command passed without pasting its actual output.
8. Do NOT continue past a STOPPING CONDITION. Halting is a successful outcome.
9. Do NOT change a public contract (API response, DB schema, URL) unless the TASK says so.
10. Do NOT attempt a third strategy. Two attempts, then HALT.

REQUIRED PHASE ORDER: READ → RESTATE → PLAN → ACT → VERIFY → RECORD.
You MUST emit the RESTATE and PLAN blocks before your first edit.

IF ANYTHING IS UNCLEAR: halt using the HALT FORMAT. Do not guess. Do not pick the most
likely interpretation. An unclear specification is a defect in the specification, and
reporting it is the highest-value thing you can do in this run.

If any `{{PLACEHOLDER}}` below is still literally present, HALT immediately with trigger E1.

## 2. PURPOSE

Record the status change of `{{TASK_ID}}` to `{{NEW_STATUS}}` consistently across every PMO surface the
living-PMO rule requires, leaving all of them in agreement.

## 3. ALLOWED SCOPE

You may create or modify ONLY these paths:

```
project-management/exports/tasks.json
project-management/PROJECT_STATUS.md
project-management/CHANGELOG.md
project-management/DONE.md
project-management/sprints/SPRINT_*.md
project-management/**/*_PROGRESS.md
aods/reports/tasks/{{NODE_ID}}.md
```

Only the files actually affected by `{{TASK_ID}}` — not every file matching these globs.

## 4. FORBIDDEN SCOPE

| Path | Reason |
|------|--------|
| `app/**`, `frontend/**`, `alembic/**`, `scripts/**` | This node records status; it does not change behaviour |
| `docs/**` | Documentation is a separate `DOC` node |
| `.cursor/rules/pmo-living-system.mdc` | Changing the rule that governs you is `D4` (`CR-007`) |
| `aods/registry/**` | AODS state is a different `GOV` node |
| Any task entry other than `{{TASK_ID}}` | One task per node; touching a neighbour's status is undetectable drift |

Deleting any file is forbidden in every archetype. Supersede instead.

## 5. FORBIDDEN CONTEXT

Do NOT read these files. They are stale, superseded, or known to contain false claims,
and reading them causes hallucinated requirements:

| Path | Why |
|------|-----|
| `frontend/AI_CONTEXT.md` | ~1,000 lines of confirmed-false architecture claims (CR-015) |
| `frontend/BACKEND_NON_COMPLIANCE.md` | Obsolete gap ledger; presents resolved issues as open (CR-015) |
| `frontend/BACKEND_HANDOFF.md` | Same class of staleness (CR-015) |
| `docs/GO_LIVE_EXECUTION_PLAN.md` | Pre-launch plan contradicted by the live site (CR-014) |
| `docs/audits/v1/**` | Superseded by the v2 audit generation |
| `docs/audits/v2/SCORECARD-AFTER-REMEDIATION.md` | Self-certified 9.0 against a 5.7 audit (CR-006) |

## 6. INPUTS

Read these files, in this order, to this depth. Read NOTHING else.

| # | Tier | Path | Depth | Why you need it |
|---|------|------|-------|-----------------|
| 1 | T3 | `project-management/sprints/SPRINT_*.md` | The active sprint | Where the task's checkbox lives |
| 2 | T2 | `project-management/exports/tasks.json` | The `{{TASK_ID}}` entry | Current status, progress, and the entry's field set |
| 3 | T2 | `project-management/PROJECT_STATUS.md` | The `{{TASK_ID}}` rows | Mirrored status |
| 4 | T2 | `project-management/CHANGELOG.md` | Last 20 lines | The entry format to match |
| 5 | T1 | `.cursor/rules/pmo-living-system.mdc` | FULL | **The binding list of surfaces that must be updated** |

If any T1 input is missing, unreadable, or does not contain the section named: HALT (E1).

## 7. ARCHITECTURE RULES

| # | Rule | Citation |
|---|------|----------|
| 1 | Every meaningful status change updates: the `tasks.json` entry, `PROJECT_STATUS.md`, the active sprint file, the relevant `*_PROGRESS.md`, `CHANGELOG.md`, and — when done — `DONE.md` with task ID and PR link. | `.cursor/rules/pmo-living-system.mdc` |
| 2 | AODS never forks PMO state. `tasks.json` is the PMO's source of truth; the markdown files mirror it. | `aods/AODS-CHARTER.md` §3 invariant 3 |
| 3 | `CHANGELOG.md` and `DONE.md` are append-only. | `.cursor/rules/pmo-living-system.mdc` |
| 4 | Progress is a measured claim, not an impression. `100` requires the acceptance criteria to be met and the PR merged. | `project-management/exports/tasks.json` `dod` field |
| 5 | Do not invent a task. If `{{TASK_ID}}` does not exist, creating it is a planning decision, not a bookkeeping one. | `aods/30-roles/ROLE-ARCHITECTURE.md` |

If the TASK appears to require violating one of these, HALT (E2) and report the conflict.

## 8. FILE MODIFICATION RULES

- **Modify:** only the `{{TASK_ID}}` entry and its mirrors.
- **Never** touch another task's status, progress, or notes.
- **Never** reformat `tasks.json`. Preserve key order, indentation, and Unicode (Persian text must not
  be escaped to `\uXXXX` — that would rewrite the whole file and bury your one-line change).
- **Never delete** any file or any historical entry.
- **Never** set `progress: 100` unless `{{NEW_STATUS}}` is `done` **and** the PR is merged.
- **Never** resolve the duplicate-progress-file question. Six `*_PROGRESS.md` pairs exist at two paths
  and diverge (`CR-007`). Update **both** copies identically and record that you did. Choosing a
  canonical path is a human decision (`HC-04`).
- Keep `as_of` in `tasks.json` current if the file's convention requires it.

## 9. TASK

1. Locate the `{{TASK_ID}}` entry in `tasks.json`. If absent, HALT (E1).
2. Set `status` to `{{NEW_STATUS}}` and `progress` to `{{NEW_PROGRESS}}`.
3. Append to the entry's `notes`: `{{NOTE}}` and `{{PR_LINK}}`. Do not overwrite existing notes.
4. Update the matching checkbox/row in `PROJECT_STATUS.md`.
5. Update the checkbox in the active sprint file.
6. Update the relevant `*_PROGRESS.md`. If two copies exist (root and `progress/`), update **both**
   identically and note it — see §8.
7. Append a `CHANGELOG.md` entry in the file's existing format, dated, referencing `{{TASK_ID}}` and `{{PR_LINK}}`.
8. If `{{NEW_STATUS}}` is `done`, append to `DONE.md` with the task ID and PR link.
9. Verify consistency with the gate. Every surface must agree; a partial update is the exact defect
   this node exists to prevent.

## 10. EXPECTED OUTPUTS

1. Consistent status across every surface named in §7 rule 1.
2. A task record at `aods/reports/tasks/{{NODE_ID}}.md` listing every file touched and, for the
   duplicate progress files, confirmation that both copies were updated.
3. A response following OUTPUT FORMAT (§14).

## 11. VALIDATION CHECKLIST

| # | Command | Expected |
|---|---------|----------|
| 1 | `python3 -c "import json;json.load(open('project-management/exports/tasks.json'))"` | No error — JSON is still valid |
| 2 | `python3 aods/tools/aods_validate.py --gate pmo` | Exit 0 — all surfaces agree |
| 3 | `git diff --stat project-management/exports/tasks.json` | A small diff (a few lines), not a whole-file rewrite |
| 4 | `git grep -c "{{TASK_ID}}" -- project-management/` | Appears in every required surface |
| 5 | `git diff project-management/CHANGELOG.md \| grep '^-'` | Only the diff header — append-only |
| 6 | `git diff --name-only` | Only paths inside ALLOWED SCOPE |
| 7 | `git diff -- app/ frontend/ docs/` | **Empty** |
| 8 | `python3 aods/tools/aods_validate.py --gate links` | Exit 0 |

If a command cannot be run in this environment, say so explicitly in the task record and
mark the criterion UNVERIFIED. Never assert an unrun command passed.

Item 3 matters more than it looks. A JSON re-serialisation that escapes Persian text or reorders keys
produces a 1,000-line diff in which a reviewer cannot see the one field you meant to change.

## 12. STOPPING CONDITIONS

Halt immediately, using the HALT FORMAT, if any of these is true:

1. `{{TASK_ID}}` does not exist in `tasks.json`. (E1 — creating a task is a planning decision.)
2. `{{NEW_STATUS}}` is not one of the status values already used in the file. (E1)
3. `{{NEW_PROGRESS}}` is `100` but `{{NEW_STATUS}}` is not `done`, or no PR link was supplied. (E2)
4. The two copies of a `*_PROGRESS.md` file diverge so much that updating both identically is impossible
   without choosing a winner. (E3 — `CR-007`, `HC-04`. **Do not pick a winner.**)
5. The task's acceptance criteria are not met but `{{NEW_STATUS}}` is `done`. (E2 — report the gap.)
6. The `--gate pmo` validator still fails after your update for reasons pre-dating your change.
   (E4 — report the pre-existing inconsistency; do not fix unrelated tasks here.)
7. Two attempts have failed. (E5)
8. Any `{{PLACEHOLDER}}` remains unfilled. (E1)

## 13. FAILURE HANDLING

- Attempt 1 fails → re-read the rule's list of surfaces; try ONE alternative.
- Attempt 2 fails → HALT with both attempts documented.
- A third strategy is forbidden.
- **Never** mark something done to make a board look better.
- **Never** silently delete one of the duplicate progress files, however obviously redundant it appears.
  That is `CR-007`, and it belongs to a human.
- If `--gate pmo` reports failures on **other** tasks, list them in the task record as pre-existing debt.
  Do not fix them: a status change you did not verify is a fabricated status.

## 14. OUTPUT FORMAT

Respond in exactly this structure:

```
## RESTATE
Governing authority:
  - .cursor/rules/pmo-living-system.mdc (<path>:<line>) — surfaces that must be updated: <list>
    [resolves on merge base: YES/NO]
Constraints I must not violate:
  - tasks.json is the PMO source of truth; markdown mirrors it
  - CHANGELOG/DONE append-only
  - progress 100 only when done AND merged
  - Update BOTH copies of duplicated *_PROGRESS.md (CR-007); do not pick a canonical path
Current state of {{TASK_ID}}: status=<...> progress=<...>
Target state: status={{NEW_STATUS}} progress={{NEW_PROGRESS}}
Acceptance criteria met: <YES/NO — evidence>

## PLAN
Files I will change (must be a subset of ALLOWED SCOPE):
  1. project-management/exports/tasks.json — the {{TASK_ID}} entry only
  2. project-management/PROJECT_STATUS.md — the {{TASK_ID}} row
  3. project-management/sprints/SPRINT_<nn>.md — the checkbox
  4. project-management/<X>_PROGRESS.md AND project-management/progress/<X>_PROGRESS.md — both copies
  5. project-management/CHANGELOG.md — appended
  6. project-management/DONE.md — appended (only if status=done)
Files I will NOT change although related:
  1. Other task entries — one task per node
  2. .cursor/rules/pmo-living-system.mdc — D4

## ACT
<the edits>

## VERIFY
<verbatim command output for every item in §11>

## RECORD
Task record written to: aods/reports/tasks/{{NODE_ID}}.md
Duplicate progress files updated identically: <YES, both paths listed | N/A>
Pre-existing PMO inconsistencies found (not fixed here): <list, or "none">

STATUS: COMPLETE
```

On halt, replace everything from `## ACT` onward with:

```
STATUS: HALTED
NODE: {{NODE_ID}}
TRIGGER: <E1|E2|E3|E4|E5>
BLOCKER:
  1. <what is unknown or conflicting>
     EVIDENCE: <path>:<line> says X; <path>:<line> says Y
     OPTIONS:
       A) <option> — consequence
       B) <option> — consequence
     RECOMMENDATION: <A|B> because <reason grounded in a cited authority>
     DECISION REQUIRED FROM: <role / HC-nn>
WORK COMPLETED BEFORE HALT: <files touched, or "none">
STATE OF REPOSITORY: <clean | uncommitted changes listed>
RESUME INSTRUCTIONS: <what a future stateless agent needs to continue>
```
