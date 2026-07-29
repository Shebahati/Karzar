---
id: AUD-doc-conflict-scan
version: 0.1.0
archetype: AUD
role: ROLE-DOC-ARCH
capability_class: LARGE-CORPUS
reasoning_depth: R3
decision_ceiling: D0
lifecycle_state: Draft
parameters:
  - NODE_ID
  - TOPIC
  - DOC_SET
context_tiers:
  T1: [aods/10-repository-intelligence/AUTHORITY-MODEL.md]
  T2: [aods/registry/document-registry.yaml, aods/10-repository-intelligence/CONFLICT-REGISTER.md]
  T3: []
forbidden_context:
  - frontend/AI_CONTEXT.md
  - frontend/BACKEND_NON_COMPLIANCE.md
  - frontend/BACKEND_HANDOFF.md
  - docs/GO_LIVE_EXECUTION_PLAN.md
  - docs/audits/v1/
  - docs/audits/v2/SCORECARD-AFTER-REMEDIATION.md
gates: [links]
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

Find every contradiction between documents on the topic `{{TOPIC}}` and report them as evidence-backed
findings, without resolving any of them.

## 3. ALLOWED SCOPE

You may create or modify ONLY these paths:

```
aods/reports/audits/{{NODE_ID}}.md
aods/reports/tasks/{{NODE_ID}}.md
```

This is a **read-only investigation**. You must not change any document you are auditing,
even if a fix looks trivial and obvious. Fixing is a different archetype (`DOC`) and requires
a human decision on which side of the contradiction is correct.

## 4. FORBIDDEN SCOPE

| Path | Reason |
|------|--------|
| Every path other than the two in ALLOWED SCOPE | This node produces findings, not fixes |
| `aods/10-repository-intelligence/CONFLICT-REGISTER.md` | Appending here is a `GOV` node after human triage; you propose entries in your report instead |
| `app/**`, `frontend/**`, `scripts/**` | Not an implementation node |

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

**Exception for this node only:** if `{{TOPIC}}` is *itself* about one of these documents (for example, auditing
whether `AI_CONTEXT.md` should be deleted), you may read it **solely to quote it as evidence**. You must not treat
any statement in it as true. State this exception explicitly in your RESTATE block.

## 6. INPUTS

Read these files, in this order, to this depth. Read NOTHING else.

| # | Tier | Path | Depth | Why you need it |
|---|------|------|-------|-----------------|
| 1 | T2 | `aods/registry/document-registry.yaml` | FULL | Authority class of every document — determines which side of a conflict outranks the other |
| 2 | T2 | `aods/10-repository-intelligence/CONFLICT-REGISTER.md` | SKIM headings | Avoid re-reporting an existing conflict |
| 3 | T1 | `aods/10-repository-intelligence/AUTHORITY-MODEL.md` | FULL | The precedence ladder and what "conflict" formally means |
| 4 | T2 | `{{DOC_SET}}` | FULL | The documents to compare |

If any T1 input is missing, unreadable, or does not contain the section named: HALT (E1).

## 7. ARCHITECTURE RULES

| # | Rule | Citation |
|---|------|----------|
| 1 | You report conflicts; you never resolve them | `aods/AODS-CHARTER.md` §3 invariant 7 |
| 2 | Every finding must cite `path:line` on both sides | `aods/10-repository-intelligence/AUTHORITY-MODEL.md` — evidence requirement |
| 3 | Code is Plane C (as-built evidence), not a specification | `aods/10-repository-intelligence/AUTHORITY-MODEL.md` — planes model |
| 4 | A document's authority comes from its registry class, not its tone or filename | `aods/registry/document-registry.yaml` |

If the TASK appears to require violating one of these, HALT (E2) and report the conflict.

## 8. FILE MODIFICATION RULES

- **Create:** only the two files in ALLOWED SCOPE.
- **Modify:** nothing else. This node is read-only with respect to the repository under audit.
- **Never delete** any file.
- **Never move or rename** any file.
- **Never "helpfully" correct** a typo, a broken link, or a stale number in a document you are auditing.
  Record it as a finding. An audit that edits its subject destroys the evidence.

## 9. TASK

For the topic `{{TOPIC}}`, across the document set `{{DOC_SET}}`:

1. Extract every **normative statement** on the topic. A normative statement says what must, should, or will be
   true — thresholds, paths, names, obligations, prohibitions. Ignore descriptive prose.
2. For each statement record: the exact quote, `path:line`, and the document's authority class from the registry.
3. Group statements that address the same question.
4. Within each group, identify contradictions. Two statements contradict when they cannot both be honoured.
5. For each contradiction, determine which document outranks the other **per the precedence ladder** — and state
   whether the ladder actually resolves it or leaves it genuinely open.
6. Check whether an equivalent entry already exists in the conflict register. If so, reference the `CR-nnn` and
   note whether your evidence changes it.
7. Separately list **silent gaps**: questions on this topic that no document answers. A gap is not a conflict, and
   conflating the two produces a register nobody trusts.

Distinguish clearly throughout between what you **observed** (a quote at a line) and what you **inferred**.

## 10. EXPECTED OUTPUTS

1. `aods/reports/audits/{{NODE_ID}}.md` containing:
   - A findings table: `#`, `question`, `doc A + line + class`, `doc B + line + class`, `contradiction?`,
     `ladder resolves?`, `existing CR-nnn`
   - A verbatim-quote appendix for every cited line
   - A gaps table: `#`, `unanswered question`, `who should answer it`
   - A proposed conflict-register entry for each **new** contradiction, in the register's existing format
2. A task record at `aods/reports/tasks/{{NODE_ID}}.md`.
3. A response following OUTPUT FORMAT (§14).

## 11. VALIDATION CHECKLIST

| # | Command | Expected |
|---|---------|----------|
| 1 | `python3 aods/tools/aods_validate.py --gate links` | Exit 0 — your new report's links resolve |
| 2 | For each cited line: `sed -n '<line>p' <path>` | Output matches your quoted text exactly |
| 3 | `git status --short` | Only the two ALLOWED SCOPE files appear |
| 4 | `grep -c "^| " aods/reports/audits/{{NODE_ID}}.md` | Non-zero — findings table is populated |

Item 2 is not optional and not a formality. A fabricated line citation is the highest-severity
defect this node can produce, because every downstream decision would inherit it.

If a command cannot be run in this environment, say so explicitly in the task record and
mark the criterion UNVERIFIED. Never assert an unrun command passed.

## 12. STOPPING CONDITIONS

Halt immediately, using the HALT FORMAT, if any of these is true:

1. `{{DOC_SET}}` names a path that does not exist. (E1)
2. The topic requires reading a FORBIDDEN CONTEXT file and §5's exception does not apply. (E1)
3. `{{DOC_SET}}` exceeds 8 documents or 3,000 total lines — the corpus will not fit reliably; ask for a split. (E4)
4. A cited line number cannot be verified against the file. (E1 — do not guess the line)
5. Two attempts have failed. (E5)
6. Any `{{PLACEHOLDER}}` remains unfilled. (E1)

## 13. FAILURE HANDLING

- Attempt 1 fails → diagnose from the actual error output; try ONE alternative strategy.
- Attempt 2 fails → HALT. Document both attempts, the exact errors, and what you ruled out.
- A third strategy is forbidden.
- If you cannot decide whether two statements contradict, record it as `contradiction? UNCERTAIN` with your
  reasoning. Uncertainty recorded is useful; uncertainty resolved by coin-flip is not.
- Never reduce the finding count to make the report look tidier.

## 14. OUTPUT FORMAT

Respond in exactly this structure:

```
## RESTATE
Governing authority:
  - AUTHORITY-MODEL precedence ladder (aods/10-repository-intelligence/AUTHORITY-MODEL.md:<line>)
    — <the ladder in your own words>
    [resolves on merge base: YES/NO]
Constraints I must not violate:
  - Report, never resolve (aods/AODS-CHARTER.md:<line>)
  - Do not edit any audited document
Not specified, and I will therefore NOT invent:
  - <gap> → <halting? yes/no, and why>
Forbidden-context exception invoked: <NO | YES, for path X, quoted as evidence only>

## PLAN
Files I will change:
  1. aods/reports/audits/{{NODE_ID}}.md — the findings
  2. aods/reports/tasks/{{NODE_ID}}.md — the task record
Files I will NOT change although related:
  1. <every audited document> — audits do not edit their subject
  2. aods/10-repository-intelligence/CONFLICT-REGISTER.md — appending is a GOV node after triage

## ACT
<the report content>

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
