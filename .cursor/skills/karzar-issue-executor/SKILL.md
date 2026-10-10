---
name: karzar-issue-executor
description: Execute one Karzar GitHub Issue economically and with strict scope, safety, evidence, and CI discipline. Use for implementation work tied to a numbered Issue.
---

# Karzar Issue Executor

Use this workflow for exactly one GitHub Issue.

## 1. Preflight truth
- Read root `AGENTS.md` and the nearest nested `AGENTS.md`.
- Run `git fetch origin`.
- Record current `origin/main`.
- Read the Issue from GitHub (prefer `gh issue view <N> --json number,title,body,state,labels,url`).
- Identify explicit blockers/dependencies and out-of-scope items.
- Inspect worktree status. Do not destroy unrelated dirty work.
- Treat SHAs or status copied into the prompt as stale until re-attested.

## 2. Cost class
Classify the task before deep work:
- **S**: docs, mechanical tests, small CI/config/simple fix.
- **M**: normal frontend/backend implementation with bounded root-cause work.
- **H**: auth, payment, security boundary, concurrency, transaction semantics, or architecture ambiguity.

Use the cheapest adequate model. For H tasks, do cheap mapping first and escalate only for the hard reasoning/review portion.

## 3. Bounded exploration
Read only what is needed:
1. Issue and authority docs.
2. Relevant implementation files.
3. Existing tests for the affected flow.
4. Targeted search for direct call sites/ownership.

Avoid repeated full-repo scans and repeated summaries. If focused evidence is insufficient, return `BLOCKED_BY_MISSING_EVIDENCE`.

## 4. Scope fence
- One Issue = one branch/PR.
- No unrelated cleanup, dependency upgrades, refactors, deploys, production writes, catalog APPLY, or real payments unless the Issue and human authorization explicitly require them.
- If `origin/main` moves materially, return `TARGET_MOVED` and reassess before integration.

## 5. Implement and verify
- Reproduce first when fixing a defect.
- Make the smallest correct change.
- Add regression coverage for the defect/acceptance criterion.
- Run focused checks first, then the relevant package/full checks required by nested `AGENTS.md`.
- Run `python3 aods/tools/aods_validate.py` when repository governance/docs are affected.
- Never claim a skipped or flaky check as passing.

## 6. Stop boundary
Do not merge or deploy. Stop at PR-ready unless the human explicitly authorizes the next action.

## 7. Exit contract
Return only:
- `STATUS`
- `IDENTITY`
- `CHANGED_PATHS`
- `TESTS`
- `CI`
- `RISKS`
- `BLOCKERS`
- `PR`
- `NEXT_STEP`
- `SAFETY`

Keep evidence concise. Expand only when a failure, ambiguity, or review finding needs explanation.
