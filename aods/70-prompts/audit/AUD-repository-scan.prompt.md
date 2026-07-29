---
id: AUD-repository-scan
version: 0.1.0
archetype: AUD
role: ROLE-DOC-ARCH
capability_class: LARGE-CORPUS
reasoning_depth: R3
decision_ceiling: D0
lifecycle_state: Draft
parameters:
  - NODE_ID
  - SCAN_SCOPE
context_tiers:
  T1: [aods/10-repository-intelligence/AUTHORITY-MODEL.md]
  T2: [aods/registry/document-registry.yaml, aods/10-repository-intelligence/REPOSITORY-AUDIT.md]
  T3: []
forbidden_context:
  - frontend/AI_CONTEXT.md
  - frontend/BACKEND_NON_COMPLIANCE.md
  - frontend/BACKEND_HANDOFF.md
  - docs/FRONTEND_IMPLEMENTATION_GUIDE.md
  - docs/GO_LIVE_EXECUTION_PLAN.md
  - docs/audits/v1/
  - docs/audits/v2/SCORECARD-AFTER-REMEDIATION.md
gates: [links, registry]
produces: [AUDIT-FINDINGS, TASK-RECORD]
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

Produce a measured, evidence-cited inventory of `{{SCAN_SCOPE}}`, distinguishing what is observed from
what is claimed — and changing nothing.

## 3. ALLOWED SCOPE

You may create or modify ONLY these paths:

```
aods/reports/audits/{{NODE_ID}}.md
aods/reports/tasks/{{NODE_ID}}.md
```

## 4. FORBIDDEN SCOPE

| Path | Reason |
|------|--------|
| Everything else | This node is read-only. An audit that modifies its subject destroys its own evidence |
| `aods/registry/**` | Registry updates are a `GOV` node after human triage |
| `aods/10-repository-intelligence/CONFLICT-REGISTER.md` | You propose entries in your report; appending is a `GOV` node |

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

**Exception:** if the scan's purpose is to inventory these files themselves (for example, to count how
many false claims remain in `AI_CONTEXT.md` before deleting it), you may read them **only** to quote
them as evidence, never as truth. Declare the exception in RESTATE.

## 6. INPUTS

Read these files, in this order, to this depth. Read NOTHING else.

| # | Tier | Path | Depth | Why you need it |
|---|------|------|-------|-----------------|
| 1 | T2 | `aods/10-repository-intelligence/REPOSITORY-AUDIT.md` | SKIM the relevant section | What is already known — avoid re-deriving it and avoid contradicting it silently |
| 2 | T2 | `aods/registry/document-registry.yaml` | FULL | Existing classifications |
| 3 | T1 | `aods/10-repository-intelligence/AUTHORITY-MODEL.md` | FULL | Authority classes and the evidence standard |
| 4 | T2 | `{{SCAN_SCOPE}}` | As the scope requires | The subject of the scan |

If any T1 input is missing, unreadable, or does not contain the section named: HALT (E1).

## 7. ARCHITECTURE RULES

| # | Rule | Citation |
|---|------|----------|
| 1 | Every number in your report must come from a command you ran, and you must show the command. | `aods/10-repository-intelligence/AUTHORITY-MODEL.md` — measured, not copied |
| 2 | Distinguish **observed** (a command's output, a quoted line) from **inferred** (your conclusion) in every finding. | `aods/50-ai-execution/AI-EXECUTION-MODEL.md` §4 `R3` |
| 3 | Report; do not resolve, and do not fix. | `aods/AODS-CHARTER.md` §3 invariant 7 |
| 4 | A document's claim about itself is not evidence. Verify against the artifact it describes. | `aods/AODS-CHARTER.md` §2 (`CR-006`) |
| 5 | Unknowns are a required output. An audit with no "unknowns" section is claiming omniscience. | `aods/10-repository-intelligence/REPOSITORY-AUDIT.md` structure |

If the TASK appears to require violating one of these, HALT (E2) and report the conflict.

Rule 4 is the lesson of `CR-006`: a scorecard in this repository asserts 9.0/10 across all categories
while the audit it derives from measured 5.7/10. Self-description is a claim, not a measurement.

## 8. FILE MODIFICATION RULES

- **Create:** only the two report files.
- **Modify:** nothing else, ever.
- **Never delete** any file.
- **Never** fix a broken link, a stale number, or a typo you find. Record it.
- **Never** update the registry to match what you found. Propose the change in your report.
- Every table row that states a quantity must carry the command that produced it.

## 9. TASK

For `{{SCAN_SCOPE}}`:

1. **Inventory.** Enumerate what exists, with counts, using explicit commands. Show each command and
   its output. Examples of the form expected:

   ```bash
   git ls-files '*.md' | wc -l
   git ls-files 'scripts/*.py' | wc -l
   git branch -r | wc -l
   ```
2. **Classify.** For each document in scope, state its authority class from the registry, or `UNREGISTERED`.
3. **Verify claims.** For each self-descriptive claim (a status, a percentage, a "complete" marker),
   check it against the artifact it describes. Record `CONFIRMED` / `CONTRADICTED` / `UNVERIFIABLE`
   with evidence.
4. **Measure enforcement.** For each documented rule in scope, determine whether anything enforces it:
   a CI job, a validator, a pre-commit hook, or nothing. "Documented but unenforced" is the single most
   useful finding class in this repository.
5. **Find gaps.** List what a reader would expect to exist and does not.
6. **List unknowns.** What you could not determine, and what would be needed to determine it.
7. **Propose, do not act.** For each finding, name the node type that would address it and the human
   checkpoint required, if any.

## 10. EXPECTED OUTPUTS

1. `aods/reports/audits/{{NODE_ID}}.md` containing: a measurement table (each row with its command), a
   classification table, a claim-verification table, an enforcement table, a gap list, an unknowns list,
   and proposed follow-up nodes.
2. A task record at `aods/reports/tasks/{{NODE_ID}}.md`.
3. A response following OUTPUT FORMAT (§14).

## 11. VALIDATION CHECKLIST

| # | Command | Expected |
|---|---------|----------|
| 1 | `python3 aods/tools/aods_validate.py --gate links` | Exit 0 |
| 2 | `python3 aods/tools/aods_validate.py --gate registry` | Exit 0 |
| 3 | `git status --short` | Only the two report files |
| 4 | Re-run every measurement command in your report | Same numbers — reproducibility check |
| 5 | For each quoted line: `sed -n '<line>p' <path>` | Matches your quotation exactly |
| 6 | `grep -n "Unknowns" aods/reports/audits/{{NODE_ID}}.md` | Present and non-empty |

If a command cannot be run in this environment, say so explicitly in the task record and
mark the criterion UNVERIFIED. Never assert an unrun command passed.

Item 4 is the reproducibility requirement made concrete: another operator running your commands must
get your numbers, or the audit is an opinion.

## 12. STOPPING CONDITIONS

Halt immediately, using the HALT FORMAT, if any of these is true:

1. `{{SCAN_SCOPE}}` is not defined precisely enough to enumerate (e.g. "the codebase"). (E1 — ask for
   a path set or a question.)
2. The scope requires reading FORBIDDEN CONTEXT and §5's exception does not apply. (E1)
3. The scope exceeds what can be measured reliably in one execution — more than ~40 files needing full
   reads, or more than ~5,000 lines. (E4 — request a split.)
4. A measurement command is unavailable in this environment and no substitute exists. (E1 — do not
   estimate a number.)
5. A finding would require changing a file to confirm. (E4 — that is an experiment, not an audit.)
6. Two attempts have failed. (E5)
7. Any `{{PLACEHOLDER}}` remains unfilled. (E1)

## 13. FAILURE HANDLING

- Attempt 1 fails → narrow the scope or change the measurement approach; try ONE alternative.
- Attempt 2 fails → HALT with both attempts and what you did measure.
- A third strategy is forbidden.
- **Never estimate a count.** If you cannot measure it, it belongs in Unknowns. An estimated number in
  an audit becomes a cited fact within one PR.
- **Never** soften a finding because it implies a lot of work.
- **Never** omit a finding because it contradicts an existing AODS document. If your evidence contradicts
  `REPOSITORY-AUDIT.md`, report the contradiction — the audit may be stale, and that is worth knowing.

## 14. OUTPUT FORMAT

Respond in exactly this structure:

```
## RESTATE
Governing authority:
  - AUTHORITY-MODEL (aods/10-repository-intelligence/AUTHORITY-MODEL.md:<line>) — authority classes
    and the evidence standard, in your own words
    [resolves on merge base: YES/NO]
Constraints I must not violate:
  - Every number comes from a shown command
  - Observed vs inferred, distinguished per finding
  - Report only; never fix
  - Self-description is not evidence (CR-006)
Scope I will measure: {{SCAN_SCOPE}}
Forbidden-context exception invoked: <NO | YES, for path X, quoted as evidence only>

## PLAN
Files I will change:
  1. aods/reports/audits/{{NODE_ID}}.md
  2. aods/reports/tasks/{{NODE_ID}}.md
Measurement commands I will run:
  1. <command> — <what it establishes>
Files I will NOT change although related:
  1. Everything in {{SCAN_SCOPE}} — audits do not edit their subject
  2. aods/registry/** — registry updates are a GOV node

## ACT
<the report>

## VERIFY
<verbatim command output for every item in §11>

## RECORD
Task record written to: aods/reports/tasks/{{NODE_ID}}.md
Findings: <n> confirmed, <n> contradicted, <n> unverifiable
Documented-but-unenforced rules found: <n>
Unknowns: <n>
Proposed follow-up nodes: <list>

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
