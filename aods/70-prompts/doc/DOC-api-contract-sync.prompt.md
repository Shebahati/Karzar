---
id: DOC-api-contract-sync
version: 0.1.0
archetype: DOC
role: ROLE-DOC-ARCH
capability_class: DOC-WRITE
reasoning_depth: R1
decision_ceiling: D1
lifecycle_state: Draft
parameters:
  - NODE_ID
  - IMPL_NODE_ID
  - CHANGE_SUMMARY
context_tiers:
  T1: [docs/API_CHANGELOG.md]
  T2: [docs/API_CONTRACT.md, openapi/v1.json, app/api/endpoints/]
  T3: []
forbidden_context:
  - frontend/AI_CONTEXT.md
  - frontend/BACKEND_NON_COMPLIANCE.md
  - frontend/BACKEND_HANDOFF.md
  - docs/FRONTEND_IMPLEMENTATION_GUIDE.md
  - docs/GO_LIVE_EXECUTION_PLAN.md
  - docs/audits/v1/
  - docs/audits/v2/SCORECARD-AFTER-REMEDIATION.md
gates: [openapi, links, allowlist, citation]
produces: [API-CONTRACT-UPDATE, TASK-RECORD]
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

Bring `docs/API_CONTRACT.md`, `docs/API_CHANGELOG.md`, and `openapi/v1.json` into agreement with the
API change made by `{{IMPL_NODE_ID}}` — documenting what the code does, changing no code.

## 3. ALLOWED SCOPE

You may create or modify ONLY these paths:

```
docs/API_CONTRACT.md
docs/API_CHANGELOG.md
openapi/v1.json
aods/reports/tasks/{{NODE_ID}}.md
```

## 4. FORBIDDEN SCOPE

| Path | Reason |
|------|--------|
| `app/**` | **Absolute.** If the documentation cannot describe the code accurately, the code may be wrong — report it, do not change it |
| `tests/**` | Separate `TEST` node |
| `frontend/**` | Different surface |
| Other docs under `docs/` | This node owns exactly the three API contract files |
| `docs/architecture/**` | Governing documents are Board-owned |

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
| 1 | T2 | The endpoint module changed by `{{IMPL_NODE_ID}}` | FULL | **The as-built truth.** Documentation describes code, so the code is the input here |
| 2 | T2 | `openapi/v1.json` | The affected paths | The current committed snapshot |
| 3 | T2 | `docs/API_CONTRACT.md` | FULL (78 lines) | The existing structure and the section to extend |
| 4 | T1 | `docs/API_CHANGELOG.md` | FULL | **The versioning policy** and the entry format you must match |

If any T1 input is missing, unreadable, or does not contain the section named: HALT (E1).

**Note on planes.** For this node only, code is the primary input — because a `DOC` node's job is to make
documentation match as-built reality. This does not make code the source of truth: if the code contradicts
an *accepted specification*, that is a defect in the code, and you report it rather than documenting it
as intended behaviour. See §12 condition 4.

## 7. ARCHITECTURE RULES

| # | Rule | Citation |
|---|------|----------|
| 1 | `openapi/v1.json` must be **regenerated from the app**, never hand-edited. A hand-edited snapshot is a lie that passes review. | `docs/API_CONTRACT.md` §OpenAPI regeneration |
| 2 | Path versioning policy: additive changes are non-breaking; changing or removing a field is breaking and needs a new version plus an ADR. | `docs/API_CHANGELOG.md` §versioning policy |
| 3 | Changelog entries are append-only and dated. Never rewrite a past entry. | `docs/API_CHANGELOG.md` |
| 4 | Document what the code **does**, not what you think it should do. Discrepancies with the spec are findings. | `aods/10-repository-intelligence/AUTHORITY-MODEL.md` — planes model |
| 5 | Numeric facts are single-sourced. Do not copy a coverage or count figure into prose; link to its source. | `aods/AODS-CHARTER.md` §2 (`CR-003`) |

If the TASK appears to require violating one of these, HALT (E2) and report the conflict.

## 8. FILE MODIFICATION RULES

- **Modify:** only the three files in ALLOWED SCOPE.
- **Never hand-edit `openapi/v1.json`.** Regenerate it with the documented command and commit the result
  verbatim. If the regeneration command is unavailable in this environment, HALT (E1) — do not approximate.
- **Never delete** any file.
- **Never rewrite** an existing changelog entry; append a new one.
- **Never reformat** the whole of `API_CONTRACT.md`. Touch only the section you are updating.
- **Never** document an endpoint that does not exist, or a field that is not returned.
- Match the existing entry format exactly — heading depth, date format, table columns.

## 9. TASK

1. Read the changed endpoint module and enumerate the actual surface: path, method, request shape,
   response fields with types and nullability, status codes.
2. Regenerate the OpenAPI snapshot using the command documented in `docs/API_CONTRACT.md`. Do not
   invent a command; if the documented one fails, report the failure.
3. Diff the regenerated snapshot against the committed one. Confirm the only differences are those
   caused by `{{CHANGE_SUMMARY}}`. **Unexpected differences are a finding** — they mean the snapshot
   was already stale, which is `CR-012` (no CI verification of this file). Report them; do not
   quietly absorb them into your commit.
4. Update `docs/API_CONTRACT.md`: add or amend the endpoint's row/section using the existing format.
5. Append a `docs/API_CHANGELOG.md` entry: date, change, breaking or non-breaking (per §7 rule 2),
   and the affected paths.
6. If the change is breaking and no ADR authorises it, HALT (E2) — a breaking change documented as
   routine is how a contract quietly breaks its consumers.
7. Report any discrepancy between the code and the governing spec in the task record.

## 10. EXPECTED OUTPUTS

1. Updated `docs/API_CONTRACT.md`, appended `docs/API_CHANGELOG.md`, regenerated `openapi/v1.json`.
2. A task record at `aods/reports/tasks/{{NODE_ID}}.md` listing: expected snapshot diffs, unexpected
   snapshot diffs (pre-existing drift), and any code/spec discrepancy.
3. A response following OUTPUT FORMAT (§14).

## 11. VALIDATION CHECKLIST

| # | Command | Expected |
|---|---------|----------|
| 1 | The documented OpenAPI regeneration command from `docs/API_CONTRACT.md` | Succeeds |
| 2 | `git diff --stat openapi/v1.json` | Only the expected paths changed |
| 3 | `python3 aods/tools/aods_validate.py --gate openapi` | Exit 0 — snapshot matches the app |
| 4 | `python3 aods/tools/aods_validate.py --gate links` | Exit 0 |
| 5 | `python3 -c "import json;d=json.load(open('openapi/v1.json'));print(len(d['paths']))"` | Path count as expected |
| 6 | `git diff --name-only` | Only the four ALLOWED SCOPE paths |
| 7 | `git diff -- app/ tests/` | **Empty** |
| 8 | `git diff docs/API_CHANGELOG.md \| grep '^-'` | Only the diff header — proves append-only |

If a command cannot be run in this environment, say so explicitly in the task record and
mark the criterion UNVERIFIED. Never assert an unrun command passed.

## 12. STOPPING CONDITIONS

Halt immediately, using the HALT FORMAT, if any of these is true:

1. The documented regeneration command does not exist or fails. (E1 — never hand-write the snapshot.)
2. The regenerated snapshot differs from the committed one in ways unrelated to `{{CHANGE_SUMMARY}}`,
   by more than a trivial amount. (E2 — pre-existing drift; a human must decide whether to absorb it
   here or in its own node. `CR-012`.)
3. The change is breaking and no accepted ADR authorises it. (E2)
4. The code contradicts an accepted specification. (E2 — documenting the code would enshrine the defect.)
5. `docs/API_CHANGELOG.md` has no format you can match unambiguously. (E1)
6. Documenting the change would require editing a governing document. (E4)
7. Two attempts have failed. (E5)
8. Any `{{PLACEHOLDER}}` remains unfilled. (E1)

## 13. FAILURE HANDLING

- Attempt 1 fails → re-read the documented command and the existing entry format; try ONE alternative.
- Attempt 2 fails → HALT with both attempts and exact output.
- A third strategy is forbidden.
- **Never** hand-edit `openapi/v1.json` to make the gate pass. That converts a detectable drift into an
  undetectable one, which is strictly worse than a red gate.
- **Never** change code to match documentation you have already written.
- If unsure whether a change is breaking, treat it as breaking and HALT. The cost of an unnecessary
  halt is one human read; the cost of an unannounced breaking change is a broken consumer.

## 14. OUTPUT FORMAT

Respond in exactly this structure:

```
## RESTATE
Governing authority:
  - docs/API_CHANGELOG.md §versioning policy (<path>:<line>) — <breaking vs non-breaking rule>
    [resolves on merge base: YES/NO]
  - docs/API_CONTRACT.md §OpenAPI regeneration (<path>:<line>) — regeneration command is `<cmd>`
Constraints I must not violate:
  - openapi/v1.json is generated, never hand-edited
  - Changelog is append-only
  - Document as-built behaviour, report spec discrepancies
As-built surface I observed in the code:
  - <METHOD> <path> → fields: <name:type:nullable>, statuses: <codes>
Change classification: <NON-BREAKING | BREAKING + authorising ADR>
Not specified, and I will therefore NOT invent:
  - <anything the code does not actually do>

## PLAN
Files I will change (must be a subset of ALLOWED SCOPE):
  1. openapi/v1.json — regenerated
  2. docs/API_CONTRACT.md — section for <endpoint>
  3. docs/API_CHANGELOG.md — appended entry
Files I will NOT change although related:
  1. app/** — documentation never edits code
  2. tests/** — separate TEST node

## ACT
<the edits>

## VERIFY
<verbatim command output for every item in §11>

## RECORD
Task record written to: aods/reports/tasks/{{NODE_ID}}.md
Expected snapshot diffs: <list>
Unexpected snapshot diffs (pre-existing drift, CR-012): <list, or "none">
Code/spec discrepancies found: <list, or "none">

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
