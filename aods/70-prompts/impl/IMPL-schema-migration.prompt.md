---
id: IMPL-schema-migration
version: 0.1.0
archetype: IMPL
role: ROLE-DB-ARCH
capability_class: CODE-GEN
reasoning_depth: R2
decision_ceiling: D2
lifecycle_state: Draft
parameters:
  - NODE_ID
  - SPEC_PATH
  - SPEC_SECTION
  - CHANGE_SUMMARY
  - ALLOWED_PATHS
context_tiers:
  T1: ["{{SPEC_PATH}}", docs/architecture/adr/]
  T2: [docs/ARCHITECTURE.md, app/db/, alembic/env.py]
  T3: [alembic/versions/]
forbidden_context:
  - frontend/AI_CONTEXT.md
  - frontend/BACKEND_NON_COMPLIANCE.md
  - frontend/BACKEND_HANDOFF.md
  - docs/FRONTEND_IMPLEMENTATION_GUIDE.md
  - docs/GO_LIVE_EXECUTION_PLAN.md
  - docs/audits/v1/
  - docs/audits/v2/SCORECARD-AFTER-REMEDIATION.md
gates: [lint, types, migration-updown, allowlist, citation]
produces: [MIGRATION, TASK-RECORD]
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

Produce one reversible Alembic migration implementing `{{CHANGE_SUMMARY}}` as specified in
`{{SPEC_PATH}}` §{{SPEC_SECTION}}, and the matching SQLAlchemy model change — nothing else.

**This node's output cannot be applied by you.** A human must perform `HC-08` before the
migration touches any database. Your job ends at a reviewed, locally tested file.

## 3. ALLOWED SCOPE

You may create or modify ONLY these paths:

```
{{ALLOWED_PATHS}}
```

Normally: one new file in `alembic/versions/` plus the model module in `app/db/`.

## 4. FORBIDDEN SCOPE

| Path | Reason |
|------|--------|
| Any existing file in `alembic/versions/` | Editing an applied migration silently desynchronises every environment that already ran it |
| `alembic/env.py` | Configuration change, not a schema change |
| `app/api/**`, `app/services/**` | Consuming the new schema is a separate `IMPL` node |
| `tests/**` | Separate `TEST` node |
| `docs/**` | Separate `DOC` node |
| `scripts/**` | Data backfill is a separate, explicitly authorised `KNOW` node (`HC-09`) |

Deleting any file is forbidden in every archetype. Supersede instead.

## 5. FORBIDDEN CONTEXT

Do NOT read these files. They are stale, superseded, or known to contain false claims,
and reading them causes hallucinated requirements:

| Path | Why |
|------|-----|
| `frontend/AI_CONTEXT.md` | ~1,000 lines of confirmed-false architecture claims (CR-015) |
| `frontend/BACKEND_NON_COMPLIANCE.md` | Obsolete gap ledger; presents resolved issues as open (CR-015) |
| `frontend/BACKEND_HANDOFF.md` | Same class of staleness (CR-015) |
| `docs/FRONTEND_IMPLEMENTATION_GUIDE.md` | Self-declares primary frontend authority but frozen at 2026-07-13; reports a since-fixed OTP bug as open (CR-015) |
| `docs/GO_LIVE_EXECUTION_PLAN.md` | Pre-launch plan contradicted by the live site (CR-014) |
| `docs/audits/v1/**` | Superseded by the v2 audit generation |
| `docs/audits/v2/SCORECARD-AFTER-REMEDIATION.md` | Self-certified 9.0 against a 5.7 audit (CR-006) |

## 6. INPUTS

Read these files, in this order, to this depth. Read NOTHING else.

| # | Tier | Path | Depth | Why you need it |
|---|------|------|-------|-----------------|
| 1 | T3 | Two recent files in `alembic/versions/` | FULL | The house style for revision headers, batch mode, and naming |
| 2 | T2 | `app/db/` model module being changed | FULL | Current column definitions and relationships |
| 3 | T2 | `docs/ARCHITECTURE.md` | §layered architecture | Where models sit and what may depend on them |
| 4 | T1 | `docs/development/standards/alembic-and-schema-change-rules.md` | FULL | **The binding rules for schema change in this repo** |
| 5 | T1 | `{{SPEC_PATH}}` | §{{SPEC_SECTION}} FULL | The required schema shape |

If any T1 input is missing, unreadable, or does not contain the section named: HALT (E1).

Input 4 lives in the Canon Lock pack. If it does not resolve on your merge base, HALT (E2) — see §12.2.

## 7. ARCHITECTURE RULES

| # | Rule | Citation |
|---|------|----------|
| 1 | Every migration implements **both** `upgrade()` and `downgrade()`. A `pass` downgrade is not acceptable. | `docs/development/standards/alembic-and-schema-change-rules.md` |
| 2 | Exactly one Alembic head after your change. | `alembic heads` must print one line |
| 3 | Additive-first: prefer adding a nullable column over altering or dropping. Destructive operations require explicit spec authorisation. | `docs/development/standards/alembic-and-schema-change-rules.md` |
| 4 | The model definition and the migration must agree. A migration that diverges from the model produces an autogenerate diff forever after. | `docs/ARCHITECTURE.md` |
| 5 | No data migration inside a schema migration unless the spec says so; backfills are separate and authorised. | `ADR-012` ingestion boundary |

If the TASK appears to require violating one of these, HALT (E2) and report the conflict.

## 8. FILE MODIFICATION RULES

- **Create:** exactly one new migration file. Let Alembic generate the revision id; do not hand-write one.
- **Modify:** only the model module(s) named in ALLOWED SCOPE.
- **Never edit an existing migration.** If a previous migration is wrong, the fix is a new migration.
- **Never delete** any file.
- **Never** set `down_revision` by guessing. Derive it from `alembic heads`.
- **Never** use `op.execute()` with raw SQL unless the operation cannot be expressed in Alembic's API,
  and then explain why in the migration's docstring.
- **Never** drop a column, table, constraint, or index unless `{{SPEC_PATH}}` explicitly authorises it
  and names the data being discarded.
- Include a docstring stating what changes, why, and whether it is destructive.

## 9. TASK

1. Determine the current head: `alembic heads`. Record it — it becomes your `down_revision`.
2. Change the SQLAlchemy model to the shape required by `{{SPEC_PATH}}` §{{SPEC_SECTION}}.
3. Generate the migration with autogenerate, then **read every line it produced**. Autogenerate
   routinely emits spurious operations (type reflections, server defaults, index renames); delete
   any operation not required by this change and state in the docstring what you removed.
4. Write a real `downgrade()` that exactly reverses `upgrade()`.
5. Confirm additive-first. If the change is destructive, verify §7 rule 3 is satisfied by explicit
   spec authorisation; if it is not, HALT (E3).
6. Test locally: up, down, up (see §11). All three must succeed.
7. Record in the task record: the pre-change head, the new revision id, whether the migration is
   destructive, the exact rollback command, and any autogenerate noise you removed.

## 10. EXPECTED OUTPUTS

1. One new migration file in `alembic/versions/`.
2. The model change.
3. A task record at `aods/reports/tasks/{{NODE_ID}}.md` including the `HC-08` evidence fields:
   pre-change head, new revision, destructive yes/no, rollback command.
4. A response following OUTPUT FORMAT (§14).

You do **not** apply this to any server, take backups, or approve it. That is `HC-08`.

## 11. VALIDATION CHECKLIST

| # | Command | Expected |
|---|---------|----------|
| 1 | `alembic heads` | Exactly one head, and it is your new revision |
| 2 | `alembic upgrade head` | Succeeds |
| 3 | `alembic downgrade -1` | Succeeds — this is the reversibility proof |
| 4 | `alembic upgrade head` | Succeeds again |
| 5 | `alembic check` (if available in this version) | No pending model/schema divergence |
| 6 | `ruff check alembic app` | Exit 0 |
| 7 | `mypy app` | Exit 0 |
| 8 | `pytest -q -m "not slow"` | All pass |
| 9 | `grep -nE "drop_column\|drop_table\|drop_constraint\|alter_column" alembic/versions/<new>.py` | No output, **or** each hit is authorised by the spec and named in the docstring |
| 10 | `git diff --name-only` | Only paths inside `{{ALLOWED_PATHS}}` |

If a command cannot be run in this environment, say so explicitly in the task record and
mark the criterion UNVERIFIED. Never assert an unrun command passed.

Step 3 is the single most important command in this prompt. A migration that has never been
reversed locally is an unrecoverable production change waiting to happen.

## 12. STOPPING CONDITIONS

Halt immediately, using the HALT FORMAT, if any of these is true:

1. `{{SPEC_PATH}}` does not exist or lacks §{{SPEC_SECTION}}. (E1)
2. `docs/development/standards/alembic-and-schema-change-rules.md` does not resolve on the merge base.
   (E2 — the binding rules are unavailable, so the change cannot be governed; see `CR-001`.)
3. `alembic heads` shows more than one head **before** your change. (E2 — pre-existing branch in
   migration history; a human must merge heads first.)
4. `downgrade()` cannot be written to reverse the change (e.g. the change is inherently lossy). (E3)
5. The change is destructive and the spec does not explicitly authorise the data loss. (E3)
6. The change requires a data backfill. (E4 — separate authorised node.)
7. Autogenerate produced operations you cannot explain. (E1 — do not guess whether they are needed.)
8. Two attempts have failed. (E5)
9. Any `{{PLACEHOLDER}}` remains unfilled. (E1)

## 13. FAILURE HANDLING

- Attempt 1 fails → read the actual error; try ONE alternative strategy.
- Attempt 2 fails → HALT with both attempts and their exact errors.
- A third strategy is forbidden.
- If `downgrade` fails, **do not** simplify the downgrade to make it pass. A downgrade that does not
  restore the previous state is worse than an honest halt.
- If the local database is in a broken state after a failed attempt, say so in
  `STATE OF REPOSITORY` and stop. Do not try to repair a database you did not create.
- Never delete a migration file to "start over" — if it was committed, supersede it.

## 14. OUTPUT FORMAT

Respond in exactly this structure:

```
## RESTATE
Governing authority:
  - {{SPEC_PATH}} §{{SPEC_SECTION}} (<path>:<line>) — <required schema shape>
    [resolves on merge base: YES/NO]  [status: Accepted? YES/NO]
  - alembic-and-schema-change-rules.md (<path>:<line>) — <the rules in your own words>
    [resolves on merge base: YES/NO]
Constraints I must not violate:
  - Reversible: upgrade() and downgrade() both real
  - Single head
  - Additive-first unless the spec authorises destruction
Current head before my change: <revision>
Destructive: <YES/NO>
Not specified, and I will therefore NOT invent:
  - <gap> → <halting? yes/no, and why>

## PLAN
Files I will change (must be a subset of ALLOWED SCOPE):
  1. alembic/versions/<generated>.py — the migration
  2. app/db/<module>.py — the model
Files I will NOT change although related:
  1. app/api/**, app/services/** — consuming the schema is a separate node
  2. tests/** — separate TEST node
  3. Any existing migration — never edited

## ACT
<the edits, plus the autogenerate operations removed and why>

## VERIFY
<verbatim command output for every item in §11, especially up/down/up>

## RECORD
Task record written to: aods/reports/tasks/{{NODE_ID}}.md
HC-08 evidence: pre-head=<rev>, new-rev=<rev>, destructive=<Y/N>,
rollback=`alembic downgrade <pre-head>`

STATUS: COMPLETE — awaiting HC-08 human approval before any database is touched
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
STATE OF REPOSITORY: <clean | uncommitted changes listed | local DB state>
RESUME INSTRUCTIONS: <what a future stateless agent needs to continue>
```
