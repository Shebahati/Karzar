---
id: GOV-address-review
version: 0.1.0
archetype: GOV
role: ROLE-BE-IMPL
capability_class: CODE-GEN
reasoning_depth: R2
decision_ceiling: D1
lifecycle_state: Draft
parameters:
  - NODE_ID
  - ORIGINAL_NODE_ID
  - REVIEW_COMMENTS_PATH
  - ALLOWED_PATHS
context_tiers:
  T1: ["{{REVIEW_COMMENTS_PATH}}"]
  T2: ["aods/reports/tasks/{{ORIGINAL_NODE_ID}}.md"]
  T3: []
forbidden_context:
  - frontend/AI_CONTEXT.md
  - frontend/BACKEND_NON_COMPLIANCE.md
  - frontend/BACKEND_HANDOFF.md
  - docs/FRONTEND_IMPLEMENTATION_GUIDE.md
  - docs/GO_LIVE_EXECUTION_PLAN.md
  - docs/audits/v1/
  - docs/audits/v2/SCORECARD-AFTER-REMEDIATION.md
  - docs/archive/AI_CONTEXT-2026-07-11.md
gates: [lint, types, test, allowlist, citation]
produces: [CODE-DIFF, TASK-RECORD]
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

Address every review comment in `{{REVIEW_COMMENTS_PATH}}` for node `{{ORIGINAL_NODE_ID}}`, changing
nothing the reviewer did not ask about.

**You are not continuing a conversation.** There is no session to resume. The review comments file and
the original task record are your entire knowledge of what came before.

## 3. ALLOWED SCOPE

You may create or modify ONLY these paths:

```
{{ALLOWED_PATHS}}
aods/reports/tasks/{{NODE_ID}}.md
```

`{{ALLOWED_PATHS}}` must be **identical to or narrower than** the original node's allow-list. A review
comment cannot widen scope. If addressing a comment requires a file outside it, HALT (E4).

## 4. FORBIDDEN SCOPE

| Path | Reason |
|------|--------|
| Anything outside the original node's allow-list | A review is a correction, not a new mandate |
| `aods/reports/tasks/{{ORIGINAL_NODE_ID}}.md` | The original record is history; write a **new** record instead |
| `{{REVIEW_COMMENTS_PATH}}` | Never edit the review you were given |
| `tests/**` unless the original node was a `TEST` node | Archetype boundaries still apply |

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
| 1 | T2 | `aods/reports/tasks/{{ORIGINAL_NODE_ID}}.md` | FULL | What was done, what was decided, what was declared out of scope |
| 2 | T2 | The original node's context set, as listed in that record | Same depths | You must re-read it; you do not remember it |
| 3 | T1 | `{{REVIEW_COMMENTS_PATH}}` | FULL | **The comments you must address, and the only mandate for change** |

If any T1 input is missing, unreadable, or does not contain the section named: HALT (E1).

Input 2 is mandatory and easy to skip. The original governing specification must be re-read in full;
a fix applied without the spec in context is how a review comment gets satisfied literally while the
requirement gets broken.

## 7. ARCHITECTURE RULES

| # | Rule | Citation |
|---|------|----------|
| 1 | The original node's architecture rules still apply in full. A review comment does not suspend them. | The original prompt |
| 2 | Address exactly the comments given. Do not implement an improvement the reviewer merely hinted at. | `aods/50-ai-execution/AI-EXECUTION-MODEL.md` §9 |
| 3 | If a comment conflicts with an accepted specification, the specification wins — report the conflict. | `aods/10-repository-intelligence/AUTHORITY-MODEL.md` |
| 4 | A new task record is written; the original is never edited. | `aods/40-artifacts/ARTIFACT-ARCHITECTURE.md` §4 |

If the TASK appears to require violating one of these, HALT (E2) and report the conflict.

Rule 3 is worth dwelling on. A reviewer is human and can be wrong, and in this project the reviewer is
also the person who accepted the spec. If a comment asks for behaviour the accepted spec forbids, silently
complying replaces a reviewed decision with an unreviewed one. Report it and let the human choose.

## 8. FILE MODIFICATION RULES

- **Modify:** only what a specific numbered comment requires.
- **Never delete** any file.
- **Never** make an unrequested improvement while you are in the file.
- **Never** reformat code you are not otherwise changing.
- **Never** edit the review comments or the original task record.
- **Never** revert an earlier accepted change unless a comment asks for it.
- Keep the follow-up diff small enough that the reviewer can verify it against their comments alone.

## 9. TASK

1. Enumerate the comments from `{{REVIEW_COMMENTS_PATH}}` as `RC-1`, `RC-2`, … Include every comment,
   even ones you believe are already satisfied.
2. Classify each: `ACTIONABLE` / `ALREADY-SATISFIED` (with evidence) / `CONFLICTS-WITH-SPEC` (with
   citations) / `OUT-OF-SCOPE` (needs its own node) / `UNCLEAR` (needs the reviewer).
3. Re-read the original governing specification from the original context set.
4. Implement every `ACTIONABLE` comment. Nothing else.
5. For `ALREADY-SATISFIED`, cite the `path:line` proving it — do not just assert it.
6. For `CONFLICTS-WITH-SPEC`, do **not** implement. Report the conflict with both citations.
7. For `UNCLEAR`, do **not** guess. HALT (E3) if it blocks; otherwise report it and continue with the rest.
8. Run all gates from the original node.
9. Write a new task record mapping every `RC-n` to its outcome and the diff hunk addressing it.

## 10. EXPECTED OUTPUTS

1. Code changes confined to `{{ALLOWED_PATHS}}`.
2. A new task record at `aods/reports/tasks/{{NODE_ID}}.md` containing the `RC-n` → outcome table.
3. A response following OUTPUT FORMAT (§14).

## 11. VALIDATION CHECKLIST

| # | Command | Expected |
|---|---------|----------|
| 1 | Every gate command from the original node's prompt | All the same expectations as the original |
| 2 | `git diff --name-only` | A subset of `{{ALLOWED_PATHS}}` |
| 3 | `git diff --stat` | Small — proportional to the comment count, not a rewrite |
| 4 | `python3 aods/tools/aods_validate.py --gate allowlist --node {{NODE_ID}}` | Exit 0 |
| 5 | `git diff -- aods/reports/tasks/{{ORIGINAL_NODE_ID}}.md {{REVIEW_COMMENTS_PATH}}` | **Empty** — history untouched |
| 6 | Count of `RC-n` in your record vs comments in the source | Equal — no comment silently dropped |

If a command cannot be run in this environment, say so explicitly in the task record and
mark the criterion UNVERIFIED. Never assert an unrun command passed.

## 12. STOPPING CONDITIONS

Halt immediately, using the HALT FORMAT, if any of these is true:

1. `{{REVIEW_COMMENTS_PATH}}` or the original task record does not exist. (E1)
2. The original task record does not list its context set, so you cannot reconstruct what the original
   node knew. (E1 — the record is defective; report it.)
3. A comment is unclear and blocks the rest. (E3)
4. A comment conflicts with an accepted specification. (E2)
5. A comment requires a file outside the original allow-list. (E4)
6. A comment requires a new dependency or a contract change. (E3)
7. Two attempts have failed. (E5)
8. Any `{{PLACEHOLDER}}` remains unfilled. (E1)

## 13. FAILURE HANDLING

- Attempt 1 fails → re-read the specific comment and the spec; try ONE alternative.
- Attempt 2 fails → HALT with both attempts documented.
- A third strategy is forbidden.
- **Never** rewrite the original implementation wholesale because two comments were awkward. A rewrite
  discards the review that has already happened and forces a full re-review.
- **Never** mark a comment addressed without a diff hunk or a citation to point at.
- If a comment reveals that the original specification was wrong, that is a `SPEC` node and a `D3`+
  decision — report it, do not absorb it.

## 14. OUTPUT FORMAT

Respond in exactly this structure:

```
## RESTATE
Governing authority:
  - {{REVIEW_COMMENTS_PATH}} — comments RC-1..RC-n
  - <original governing spec> (<path>:<line>) — <re-read and restated>
    [resolves on merge base: YES/NO]
Original node: {{ORIGINAL_NODE_ID}}, allow-list: <copied from its record>
My allow-list is identical or narrower: <YES/NO>
Comment classification:
  RC-1: <ACTIONABLE | ALREADY-SATISFIED (path:line) | CONFLICTS-WITH-SPEC (citations) |
         OUT-OF-SCOPE (node) | UNCLEAR>
  RC-2: ...
Not specified, and I will therefore NOT invent:
  - <any hint not stated as a requirement>

## PLAN
Files I will change (must be a subset of ALLOWED SCOPE):
  1. <path> — addresses RC-<n>
Files I will NOT change although related:
  1. aods/reports/tasks/{{ORIGINAL_NODE_ID}}.md — history, never edited
  2. <anything a hint suggested but no comment required>

## ACT
<the edits>

## VERIFY
<verbatim command output for every item in §11>

## RECORD
Task record written to: aods/reports/tasks/{{NODE_ID}}.md
RC-n → outcome table: <n> actionable addressed, <n> already satisfied,
<n> conflicts reported, <n> out-of-scope deferred, <n> unclear

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
