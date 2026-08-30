# Karzar — Codex guidance

This is a small, documentation-only bootstrap guide. It does not replace AODS.

## Start safely

1. Check `pwd`, branch, `HEAD`, `origin/main`, and `git status` before a write.
2. Preserve all existing user changes. If the worktree is dirty, do not edit a
   file that is already changed without explicit approval.
3. Declare one concern and an explicit path allowlist; do not edit outside it.
4. Read → RESTATE (goal, constraints, non-goals, allowlist) → PLAN → wait for
   approval before writing, per `.cursor/rules/aods-kickoff-gate.mdc:23-51`.

## AODS floor

- Cite requirements as `path:line` and verify cited authority exists on
  `origin/main` (`.cursor/rules/aods-auto-mode.mdc:35-43`).
- Stop and report ambiguity or conflicting authority; do not guess
  (`.cursor/rules/aods-auto-mode.mdc:45-59`).
- Do not push, merge, rebase, deploy, touch production, alter dependencies, or
  make out-of-scope edits (`.cursor/rules/aods-auto-mode.mdc:23-33`).
- Never read quarantined documents listed in
  `.cursor/rules/aods-auto-mode.mdc:12-21`.
- Before an AODS task, read `aods/CODEX-RUNBOOK.md` and its exact registered
  prompt. Do not substitute a related prompt; if none fits, halt and report.

## Execution and review

Use one kickoff, one bounded execution, and one review. Recursive audit or
correction loops are prohibited: report remaining issues instead. Run the most
targeted relevant check before any broader check. For a documentation-only
change, do not run a full test suite unless a binding repository rule requires
it.

Before completion, inspect `git diff --check`, verify tracked changes with
`git diff --name-only` and untracked files with
`git ls-files --others --exclude-standard` against the allowlist, report real
command output, and run
`python3 aods/tools/aods_validate.py` when the file exists and runs without an
environment change (`.cursor/rules/aods-auto-mode.mdc:62-70`).

## Admin panel

Read `frontend/admin-panel/AGENTS.md` before admin work. Its real package
scripts are `npm run lint`, `npm run typecheck`, `npm test`, and `npm run build`.
