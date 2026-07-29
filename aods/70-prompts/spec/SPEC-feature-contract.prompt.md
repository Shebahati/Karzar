---
id: SPEC-feature-contract
version: 0.1.0
archetype: SPEC
role: ROLE-SYS-ARCH
capability_class: DEEP-REASON
reasoning_depth: R4
decision_ceiling: D2
lifecycle_state: Draft
parameters:
  - NODE_ID
  - FEATURE_NAME
  - GOVERNING_ADR
  - SPEC_OUTPUT_PATH
context_tiers:
  T1: ["{{GOVERNING_ADR}}", docs/architecture/CANON-LOCK.md]
  T2: [docs/API_CONTRACT.md, docs/ARCHITECTURE.md, docs/architecture/information-architecture/]
  T3: [project-management/exports/tasks.json]
forbidden_context:
  - frontend/AI_CONTEXT.md
  - frontend/BACKEND_NON_COMPLIANCE.md
  - frontend/BACKEND_HANDOFF.md
  - docs/GO_LIVE_EXECUTION_PLAN.md
  - docs/audits/v1/
  - docs/audits/v2/SCORECARD-AFTER-REMEDIATION.md
gates: [links, registry, citation]
produces: [SPECIFICATION, TASK-RECORD]
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

Write the implementable specification for `{{FEATURE_NAME}}`, deriving every requirement from
`{{GOVERNING_ADR}}` and producing acceptance criteria a test can fail.

## 3. ALLOWED SCOPE

You may create or modify ONLY these paths:

```
{{SPEC_OUTPUT_PATH}}
aods/reports/tasks/{{NODE_ID}}.md
```

## 4. FORBIDDEN SCOPE

| Path | Reason |
|------|--------|
| `app/**`, `frontend/**`, `alembic/**`, `scripts/**` | **You write no code in this node.** Design and implementation in one execution destroys the review point where a wrong design is cheapest to fix |
| `{{GOVERNING_ADR}}` | You derive *from* the ADR; changing it is a `D4` Board decision |
| `docs/architecture/CANON-LOCK.md` | Only the Board adds rows (`HC-02`) |
| `tests/**` | Separate `TEST` node |
| `project-management/**` | Separate `GOV` node |

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
| 1 | T3 | `project-management/exports/tasks.json` | The relevant task entry | Existing acceptance criteria and scope already agreed |
| 2 | T2 | `docs/API_CONTRACT.md` | FULL (78 lines) | Response envelope and error shapes any new endpoint must reuse |
| 3 | T2 | `docs/ARCHITECTURE.md` | FULL (91 lines) | Layering and transaction rules the design must respect |
| 4 | T2 | `docs/architecture/information-architecture/url-map.md` | FULL | Canonical URLs, if the feature has pages |
| 5 | T1 | `docs/architecture/CANON-LOCK.md` | FULL | Which documents are binding, and their status |
| 6 | T1 | `{{GOVERNING_ADR}}` | FULL | **The decision you are specifying.** Every requirement must trace here |

If any T1 input is missing, unreadable, or does not contain the section named: HALT (E1).

## 7. ARCHITECTURE RULES

| # | Rule | Citation |
|---|------|----------|
| 1 | You may not make architectural decisions. If the ADR does not settle a design question, record it as an open question for the Board — do not decide it. | `aods/30-roles/ROLE-ARCHITECTURE.md` — ceiling `D2`; `D3`+ needs a human |
| 2 | The spec ships with `status: Proposed`. Only the Board sets `Accepted` (`HC-01`). | `docs/development/standards/documentation-citation-rules.md` |
| 3 | Every requirement must cite the ADR/RFC section it derives from. An uncited requirement is an invention. | `aods/AODS-CHARTER.md` §1.7 principle 10 |
| 4 | Reuse existing contracts (error envelope, pagination, URL shapes). Do not design a parallel convention. | `docs/API_CONTRACT.md`, `ADR-010` |
| 5 | The spec must state its **non-goals** explicitly. | `aods/60-human/HUMAN-INTERVENTION-MODEL.md` `HC-01` step 4 |

If the TASK appears to require violating one of these, HALT (E2) and report the conflict.

## 8. FILE MODIFICATION RULES

- **Create:** the spec at `{{SPEC_OUTPUT_PATH}}` and the task record.
- **Modify:** nothing else.
- **Never delete** any file.
- **Never** set `status: Accepted` on anything, including your own output.
- **Never** add a row to `CANON-LOCK.md`.
- **Never** write code, pseudocode-as-implementation, or migration SQL. Data shapes and field tables
  are specification; function bodies are not.
- Front-matter must include: `id`, `version`, `status: Proposed`, `date`, `governing_adr`, `owner`.

## 9. TASK

Write a specification for `{{FEATURE_NAME}}` containing, in this order:

1. **Purpose** — one paragraph: what problem this solves, for whom.
2. **Governing authority** — the ADR/RFC sections this derives from, with `path:line` for each.
3. **Non-goals** — what this explicitly does not cover. A spec without non-goals has undefined scope,
   and undefined scope is where implementation drift begins.
4. **Data contract** — every field: name, type, nullability, source, and example. For API responses,
   the complete payload shape. Mark each field with the ADR section requiring it.
5. **Behaviour** — the success path, then **every** error and edge case: not found, empty result,
   unauthorised, invalid input, and any domain-specific failure. State the status code for each.
6. **URL / route contract** — if applicable, the canonical path, and the redirect behaviour for any
   superseded path, consistent with `ADR-010`.
7. **Acceptance criteria** — numbered, each phrased so a test can fail it. Use the form
   *"Given X, when Y, then Z"*. Anything a test cannot falsify is not an acceptance criterion; move
   it to Purpose.
8. **Out-of-scope discoveries** — anything you found that needs its own spec or conflict entry.
9. **Open questions** — every design question the ADR does not settle, each with: the question, the
   options you can see, the consequence of each, and who must decide. **Do not answer them.**
10. **Implementation node breakdown** — the atomic nodes this spec will require (backend, frontend,
    migration, test, doc), so the graph can be populated without re-reading the spec.

Section 9 is the highest-value part of this node. A specification that quietly resolves ambiguity by
authorial choice transfers an undocumented decision into code, and no reviewer will ever see it happen.

## 10. EXPECTED OUTPUTS

1. The specification at `{{SPEC_OUTPUT_PATH}}`, `status: Proposed`.
2. A task record at `aods/reports/tasks/{{NODE_ID}}.md`.
3. A response following OUTPUT FORMAT (§14).

## 11. VALIDATION CHECKLIST

| # | Command | Expected |
|---|---------|----------|
| 1 | `python3 aods/tools/aods_validate.py --gate links` | Exit 0 — every link in the spec resolves |
| 2 | `python3 aods/tools/aods_validate.py --gate registry` | Exit 0 — the new spec has a registry row |
| 3 | `grep -n "^status:" {{SPEC_OUTPUT_PATH}}` | `status: Proposed` |
| 4 | For each cited ADR line: `sed -n '<line>p' {{GOVERNING_ADR}}` | Matches your quotation |
| 5 | `grep -c "Given .*when .*then" {{SPEC_OUTPUT_PATH}}` | Equals your acceptance-criteria count |
| 6 | `grep -n "Non-goals" {{SPEC_OUTPUT_PATH}}` | Present and non-empty |
| 7 | `git diff --name-only` | Only the spec and the task record |

If a command cannot be run in this environment, say so explicitly in the task record and
mark the criterion UNVERIFIED. Never assert an unrun command passed.

## 12. STOPPING CONDITIONS

Halt immediately, using the HALT FORMAT, if any of these is true:

1. `{{GOVERNING_ADR}}` does not exist. (E1)
2. `{{GOVERNING_ADR}}` does not resolve on the merge base — for example it exists only on the unmerged
   Canon Lock branch. (E2 — specifying against an unavailable decision is the `CR-001` failure.)
3. `{{GOVERNING_ADR}}` status is not `Accepted`. (E2 — architecture-first.)
4. The ADR leaves a **contract-shaping** question open (a field's existence, a URL shape, an auth model)
   such that no honest spec can be written without deciding it. (E3 — the ADR needs amending first.)
5. Two authoritative documents contradict each other on this feature. (E2 — conflict entry, then `HC-03`.)
6. The feature would require a decision above ceiling `D2`. (E3)
7. Two attempts have failed. (E5)
8. Any `{{PLACEHOLDER}}` remains unfilled. (E1)

## 13. FAILURE HANDLING

- Attempt 1 fails → try ONE alternative structure or scope reduction.
- Attempt 2 fails → HALT with both attempts documented.
- A third strategy is forbidden.
- If you cannot write a falsifiable acceptance criterion for a requirement, that requirement is
  underspecified: move it to Open questions rather than softening it into prose.
- Never pad the spec to look complete. A short spec with three sharp criteria and four honest open
  questions is more useful than a long one with twenty vague statements.
- Never resolve an open question because it is blocking you. Blocking is the correct outcome.

## 14. OUTPUT FORMAT

Respond in exactly this structure:

```
## RESTATE
Governing authority:
  - {{GOVERNING_ADR}} §<n> (<path>:<line>) — <the decision in your own words>
    [resolves on merge base: YES/NO]  [status: Accepted? YES/NO]
  - CANON-LOCK row for this ADR: <quoted row, or "ABSENT">
Constraints I must not violate:
  - No architectural decisions above D2 (aods/30-roles/ROLE-ARCHITECTURE.md:<line>)
  - Spec ships as Proposed (documentation-citation-rules.md:<line>)
  - Reuse existing envelope/URL conventions
Not specified, and I will therefore NOT invent:
  - <each contract-shaping gap> → <open question N, or halting>

## PLAN
Files I will change (must be a subset of ALLOWED SCOPE):
  1. {{SPEC_OUTPUT_PATH}} — the specification
  2. aods/reports/tasks/{{NODE_ID}}.md — the task record
Files I will NOT change although related:
  1. app/**, frontend/** — this node writes no code
  2. {{GOVERNING_ADR}} — Board-owned
  3. docs/architecture/CANON-LOCK.md — Board-owned (HC-02)

## ACT
<the specification>

## VERIFY
<verbatim command output for every item in §11>

## RECORD
Task record written to: aods/reports/tasks/{{NODE_ID}}.md
Open questions requiring HC-01/Board decision: <count>

STATUS: COMPLETE — spec is Proposed, awaiting HC-01
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
