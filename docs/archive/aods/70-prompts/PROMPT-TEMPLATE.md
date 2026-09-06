# Prompt Template (mandatory)

**Document ID:** `AODS-PROMPT-TEMPLATE`
**Status:** **Accepted**
**Version:** 1.0.0
**Date:** 2026-07-29

Every prompt in [`aods/70-prompts/`](.) is an instantiation of this template. Sections may be *filled differently*;
they may not be *omitted*. `python3 aods/tools/aods_validate.py --gate prompts` enforces presence and order.

The canonical `AUTO MODE PROTOCOL` text is §1 below. It is copied verbatim into every prompt; `--gate prompts`
compares it byte-for-byte, so a drifted copy is a lint failure rather than a silent weakening.

---

## Template

Copy everything between the two `TEMPLATE` markers.

<!-- TEMPLATE:BEGIN -->

````markdown
---
id: <ARCHETYPE>-<concern-kebab>
version: 0.1.0
archetype: <AUD|SPEC|IMPL|TEST|KNOW|DOC|GOV|REL>
role: <ROLE-ID from aods/registry/role-registry.yaml>
capability_class: <DEEP-REASON|LARGE-CORPUS|ARCH-REVIEW|CODE-GEN|STRUCTURED-EXTRACT|TEST-SYNTH|DOC-WRITE>
reasoning_depth: <R1|R2|R3|R4>
decision_ceiling: <D0|D1|D2>
lifecycle_state: Draft
parameters:
  - NODE_ID
  - <others>
context_tiers:
  T1: []   # governing specs — never summarised, section-scoped
  T2: []   # structural docs + code to modify
  T3: []   # reference only
forbidden_context:
  - frontend/AI_CONTEXT.md
  - frontend/BACKEND_NON_COMPLIANCE.md
  - frontend/BACKEND_HANDOFF.md
  - docs/FRONTEND_IMPLEMENTATION_GUIDE.md
  - docs/GO_LIVE_EXECUTION_PLAN.md
  - docs/audits/v1/
  - docs/audits/v2/SCORECARD-AFTER-REMEDIATION.md
gates: []
produces: [TASK-RECORD]
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

<One sentence. One responsibility. Imperative. Measurable end state.>

## 3. ALLOWED SCOPE

You may create or modify ONLY these paths:

```
{{ALLOWED_PATHS}}
```

Anything else — including files you believe are related — is out of scope.

## 4. FORBIDDEN SCOPE

You must NOT touch these, for the stated reasons:

| Path | Reason |
|------|--------|
| `<path>` | `<reason>` |

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
| 1 | T3 | `<path>` | SKIM | reference pattern |
| 2 | T2 | `<path>` | §`<section>` | structure/conventions |
| 3 | T1 | `<path>` | §`<section>` FULL | **defines correctness** |

If any T1 input is missing, unreadable, or does not contain the section named: HALT (E1).

## 7. ARCHITECTURE RULES

These constraints must not be violated. Each is cited; verify each yourself.

| # | Rule | Citation |
|---|------|----------|
| 1 | `<rule>` | `<path>:<line>` |

If the TASK appears to require violating one of these, HALT (E2) and report the conflict.

## 8. FILE MODIFICATION RULES

- **Create:** only files explicitly named in ALLOWED SCOPE.
- **Modify:** only within ALLOWED SCOPE, and only lines required by the TASK.
- **Never delete** any file.
- **Never move or rename** any file (it breaks inbound citations).
- **Never edit** lockfiles, `requirements*.txt`, `package.json`, `.github/**`, or `alembic/**`
  unless ALLOWED SCOPE names them explicitly.
- **Never reformat** untouched lines. Keep the diff minimal — a reviewer must be able to read it.
- Match the surrounding code's existing style, even if you would write it differently.

## 9. TASK

<The parameterised goal. Explicit. Numbered if multi-step within the single responsibility.>

## 10. EXPECTED OUTPUTS

1. `<artifact>` at `<path>`
2. A task record at `aods/reports/tasks/{{NODE_ID}}.md` following
   `aods/40-artifacts/ARTIFACT-ARCHITECTURE.md` §4.
3. A response following OUTPUT FORMAT (§14).

## 11. VALIDATION CHECKLIST

Run every command. Paste the real output into the task record. Do not summarise, do not
predict, do not write "should pass".

| # | Command | Expected |
|---|---------|----------|
| 1 | `<command>` | `<expected result>` |

If a command cannot be run in this environment, say so explicitly in the task record and
mark the criterion UNVERIFIED. Never assert an unrun command passed.

## 12. STOPPING CONDITIONS

Halt immediately, using the HALT FORMAT, if any of these is true:

1. A T1 input is missing, or does not contain the cited section. (E1)
2. Two inputs contradict each other on a point material to the TASK. (E2)
3. The TASK requires a decision above ceiling `<CEILING>`. (E3)
4. The work requires editing a path outside ALLOWED SCOPE. (E4)
5. Two attempts have failed. (E5)
6. A cited governing document does not resolve on the current merge base. (E2 — this is the
   CR-001 failure; it is never acceptable to proceed.)
7. Any `{{PLACEHOLDER}}` remains unfilled. (E1)

## 13. FAILURE HANDLING

- Attempt 1 fails → diagnose from the actual error output; try ONE alternative strategy.
- Attempt 2 fails → HALT. Document both attempts, the exact errors, and what you ruled out.
- A third strategy is forbidden.
- Never make a change whose purpose is to make a gate pass rather than to make the code correct.
- Never weaken, skip, or baseline a gate. That is a human decision.

## 14. OUTPUT FORMAT

Respond in exactly this structure:

```
## RESTATE
Governing authority:
  - <ID> §<n> (<path>:<line>) — <constraint in your own words>
    [resolves on merge base: YES/NO]
Constraints I must not violate:
  - <rule> (<path>:<line>)
Not specified, and I will therefore NOT invent:
  - <gap> → <halting? yes/no, and why>

## PLAN
Files I will change (must be a subset of ALLOWED SCOPE):
  1. <path> — <why>
Files I will NOT change although related:
  1. <path> — <why not, and follow-up node if needed>

## ACT
<the edits>

## VERIFY
<verbatim command output for every item in §11>

## RECORD
Task record written to: aods/reports/tasks/{{NODE_ID}}.md

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
````

<!-- TEMPLATE:END -->

---

## Rationale for the fixed order

The section order is not stylistic. It follows the order in which the agent needs each piece, so that a truncation
event loses the least valuable content first.

| Position | Section | Why here |
|----------|---------|----------|
| 1 | Protocol | Must survive truncation from the top; sets prohibitions before any temptation |
| 2 | Purpose | Frames everything after it |
| 3–5 | Scope, forbidden scope, forbidden context | Boundaries **before** inputs, so the agent knows the limits while reading |
| 6 | Inputs | Ordered T3 → T1 so governing specs land last (`CONTEXT-MANAGEMENT.md` §4) |
| 7 | Architecture rules | Immediately after inputs, while the citations are fresh |
| 8 | File modification rules | Last constraint layer before the task |
| 9 | Task | Adjacent to the specs it depends on |
| 10–11 | Outputs, validation | Defines "done" before work starts (validation-first) |
| 12–13 | Stop, failure | At the end, where the agent will be when things go wrong |
| 14 | Output format | Final position = maximum recency for the response shape |

Placing scope (§3–5) *before* inputs (§6) is deliberate. If boundaries came after the inputs, the agent would have
already formed a plan involving out-of-scope files, and the constraint would arrive as an obstacle to work around
rather than a frame to work within.
