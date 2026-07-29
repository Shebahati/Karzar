---
id: TEST-from-spec
version: 0.1.0
archetype: TEST
role: ROLE-QA
capability_class: TEST-SYNTH
reasoning_depth: R2
decision_ceiling: D1
lifecycle_state: Draft
parameters:
  - NODE_ID
  - SPEC_PATH
  - SPEC_SECTION
  - TEST_FILE
  - IMPL_NODE_ID
context_tiers:
  T1: ["{{SPEC_PATH}}"]
  T2: [tests/conftest.py, "{{TEST_FILE}}", docs/TESTING.md]
  T3: [tests/]
forbidden_context:
  - frontend/AI_CONTEXT.md
  - frontend/BACKEND_NON_COMPLIANCE.md
  - frontend/BACKEND_HANDOFF.md
  - docs/GO_LIVE_EXECUTION_PLAN.md
  - docs/audits/v1/
  - docs/audits/v2/SCORECARD-AFTER-REMEDIATION.md
gates: [test, coverage, allowlist, citation]
produces: [TEST-REPORT, CODE-DIFF, TASK-RECORD]
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

Write tests that map one-to-one onto the acceptance criteria in `{{SPEC_PATH}}` §{{SPEC_SECTION}},
without changing any production code.

## 3. ALLOWED SCOPE

You may create or modify ONLY these paths:

```
{{TEST_FILE}}
aods/reports/tests/{{NODE_ID}}.md
aods/reports/tasks/{{NODE_ID}}.md
```

## 4. FORBIDDEN SCOPE

| Path | Reason |
|------|--------|
| `app/**` | **Absolute.** If a test cannot pass without changing production code, either the code is wrong (a finding) or the test is wrong (your error). Changing the code here would hide which |
| `alembic/**` | Schema work is a separate node |
| `tests/conftest.py` | Shared fixtures affect every test; changing it is a separate node |
| Other test files | One test file per node |
| `pyproject.toml`, `pytest.ini` | Marker and threshold changes are `D4` |
| `docs/**` | Separate `DOC` node |

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

**Additionally forbidden for this node:** the implementation diff from `{{IMPL_NODE_ID}}`.

Write tests from the **specification**, not from the code. A test derived from the implementation
asserts that the code does what it does — which is always true and detects nothing. This is the
single most common way test suites become expensive decoration. You may read the function
*signatures* you must call; you must not read their bodies to decide what to assert.

## 6. INPUTS

Read these files, in this order, to this depth. Read NOTHING else.

| # | Tier | Path | Depth | Why you need it |
|---|------|------|-------|-----------------|
| 1 | T3 | A sibling test file in `tests/` | FULL | Fixture usage, client construction, assertion style |
| 2 | T2 | `tests/conftest.py` | FULL | Available fixtures — use them; do not build your own DB session |
| 3 | T2 | `docs/TESTING.md` | FULL | Markers, the coverage gate, and how CI runs the suite |
| 4 | T2 | `{{TEST_FILE}}` | FULL if it exists | Do not duplicate existing coverage |
| 5 | T1 | `{{SPEC_PATH}}` | §{{SPEC_SECTION}} FULL | **The acceptance criteria you are encoding** |

If any T1 input is missing, unreadable, or does not contain the section named: HALT (E1).

## 7. ARCHITECTURE RULES

| # | Rule | Citation |
|---|------|----------|
| 1 | Every test names the acceptance criterion it covers, in its docstring, with the spec `path:line`. | `aods/20-lifecycle/WORKFLOW-GRAPH.md` — `TEST` node acceptance |
| 2 | The coverage gate is enforced at **68%** (`pyproject.toml` `fail_under`, and `--cov-fail-under=68` in CI). Prose in `README.md` and `docs/TESTING.md` states other numbers — those are stale (`CR-003`). Never lower the gate. | `pyproject.toml`; `.github/workflows/backend-ci.yml` |
| 3 | Use the declared pytest markers; do not invent a new marker. | `docs/TESTING.md` |
| 4 | Tests must be deterministic: fixed seeds, no reliance on wall-clock time, no network calls, no ordering dependence between tests. | `docs/TESTING.md` |
| 5 | Never assert behaviour the spec does not state. An over-specified test blocks legitimate future change. | `{{SPEC_PATH}}` |

If the TASK appears to require violating one of these, HALT (E2) and report the conflict.

## 8. FILE MODIFICATION RULES

- **Create/modify:** only `{{TEST_FILE}}` and the two report files.
- **Never delete** any file, and never delete or weaken an existing test.
- **Never** mark a test `xfail` or `skip` to make the suite green. If a test legitimately cannot run,
  HALT and explain.
- **Never** edit production code, not even a one-character fix. Report it instead.
- **Never** add a dependency, including a test helper library.
- **Never** widen an assertion (`assert x` instead of `assert x == 3`) to make it pass.
- Test names must describe the criterion, e.g. `test_unknown_slug_returns_404`.

## 9. TASK

1. Extract every acceptance criterion from `{{SPEC_PATH}}` §{{SPEC_SECTION}} and number them.
2. For each criterion, write at least one test. Cover the success path **and** every error/edge case
   the spec names — not-found, empty, unauthorised, invalid input.
3. In each test's docstring, cite the criterion: `Covers AC-<n> ({{SPEC_PATH}}:<line>)`.
4. If this node accompanies a bug fix, write the regression test so that it **fails before the fix**
   and passes after. State in the task record that you verified the pre-fix failure — a regression
   test never seen to fail is not known to test anything.
5. Run the suite. Record actual output.
6. Produce a coverage map in `aods/reports/tests/{{NODE_ID}}.md`: criterion → test name → result.
7. If a test fails because the **implementation** is wrong, do not fix the implementation. Record it
   as a finding, leave the test failing, and HALT (E2) with the discrepancy between spec and code.
   That halt is a valuable result: it means the spec and the code disagree and a human must decide which is right.

## 10. EXPECTED OUTPUTS

1. Tests in `{{TEST_FILE}}`.
2. A coverage map at `aods/reports/tests/{{NODE_ID}}.md`.
3. A task record at `aods/reports/tasks/{{NODE_ID}}.md`.
4. A response following OUTPUT FORMAT (§14).

## 11. VALIDATION CHECKLIST

| # | Command | Expected |
|---|---------|----------|
| 1 | `pytest {{TEST_FILE}} -v` | Every new test passes, or a documented spec/code discrepancy is reported |
| 2 | `pytest -q` | No previously passing test now fails |
| 3 | `pytest --cov=app --cov-fail-under=68` | Exit 0 |
| 4 | `pytest {{TEST_FILE}} -p no:randomly -q` then again | Same result both runs — determinism check |
| 5 | `git diff --name-only` | Only `{{TEST_FILE}}` and the two report files |
| 6 | `git diff -- app/` | **Empty.** Any output is a scope violation |
| 7 | `grep -c "Covers AC-" {{TEST_FILE}}` | ≥ the number of acceptance criteria |
| 8 | `grep -n "xfail\|@pytest.mark.skip" {{TEST_FILE}}` | No output |

If a command cannot be run in this environment, say so explicitly in the task record and
mark the criterion UNVERIFIED. Never assert an unrun command passed.

## 12. STOPPING CONDITIONS

Halt immediately, using the HALT FORMAT, if any of these is true:

1. `{{SPEC_PATH}}` does not exist or lacks §{{SPEC_SECTION}}. (E1)
2. The spec has no falsifiable acceptance criteria. (E1 — the spec is the defect; `HC-01` should have
   caught this. Report it rather than inventing criteria.)
3. A criterion cannot be tested without changing production code. (E2)
4. A test fails because the implementation contradicts the spec. (E2 — report the discrepancy; do not
   adjust either side.)
5. The coverage gate cannot be met without testing code unrelated to this spec. (E4 — separate node.)
6. A required fixture does not exist in `conftest.py`. (E4 — fixture changes are a separate node.)
7. Two attempts have failed. (E5)
8. Any `{{PLACEHOLDER}}` remains unfilled. (E1)

## 13. FAILURE HANDLING

- Attempt 1 fails → check your test's assumptions against the spec; try ONE alternative approach.
- Attempt 2 fails → HALT with both attempts and exact output.
- A third strategy is forbidden.
- **The forbidden repair path:** editing `app/**` so a test passes. If you find yourself considering it,
  the correct action is always HALT (E2).
- If the suite is flaky, do not retry until green. Report the flakiness — a flaky test is a defect that
  a retry conceals.

## 14. OUTPUT FORMAT

Respond in exactly this structure:

```
## RESTATE
Governing authority:
  - {{SPEC_PATH}} §{{SPEC_SECTION}} (<path>:<line>) — acceptance criteria:
      AC-1: <criterion>  (line <n>)
      AC-2: <criterion>  (line <n>)
    [resolves on merge base: YES/NO]  [status: Accepted? YES/NO]
Constraints I must not violate:
  - Coverage gate 68% (pyproject.toml:<line>) — never lowered
  - No production code changes
  - Determinism: fixed seeds, no network, no time dependence
I did NOT read the implementation diff from {{IMPL_NODE_ID}}: CONFIRMED
Not specified, and I will therefore NOT assert:
  - <behaviour the spec is silent on>

## PLAN
Files I will change (must be a subset of ALLOWED SCOPE):
  1. {{TEST_FILE}} — tests for AC-1..AC-n
  2. aods/reports/tests/{{NODE_ID}}.md — coverage map
Files I will NOT change although related:
  1. app/** — forbidden absolutely
  2. tests/conftest.py — shared fixtures, separate node

## ACT
<the tests>

## VERIFY
<verbatim command output for every item in §11>

## RECORD
Task record written to: aods/reports/tasks/{{NODE_ID}}.md
Criterion → test map: aods/reports/tests/{{NODE_ID}}.md
Criteria covered: <n>/<total>

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
