# Codex runbook

This runbook summarizes, but does not amend, the AODS rules. Use the cited
source for the binding text.

## Bounded workflow

1. Confirm location, branch, merge-base reference, and clean status.
2. State the goal, non-goals, explicit path allowlist, and source citations.
3. Obtain the required human approval before a write.
4. Make one bounded execution only; retain user changes and stay in scope.
5. Perform one review: targeted validation first, diff integrity, and allowlist
   verification. Do not recursively audit or auto-correct findings.
6. Report actual outputs, changed files, and any deliberately unfixed debt.

The normal AODS kickoff protocol is in
`.cursor/rules/aods-kickoff-gate.mdc:23-58`; one node has one role, concern,
and allowlist under `.cursor/skills/karzar-aods-operator/SKILL.md:109-130`.

## Non-negotiable safeguards

- Trace requirements to `path:line` on `origin/main`; halt on ambiguity or
  authority conflict (`.cursor/rules/aods-auto-mode.mdc:35-59`).
- Do not read the quarantined documents named in
  `.cursor/rules/aods-auto-mode.mdc:12-21`.
- Do not push, merge, rebase, deploy, use production, change dependencies, or
  edit outside the declared allowlist (`.cursor/rules/aods-auto-mode.mdc:23-33`).
- Never claim validation passed without its actual output
  (`.cursor/rules/aods-auto-mode.mdc:62-70`).

## Verification

Run the smallest relevant test first. Avoid a full suite for documentation-only
work unless a binding rule requires it. Before handoff, count changed guide
lines, run `git diff --check`, compare `git diff --name-only` with the
allowlist, compare untracked files with
`git ls-files --others --exclude-standard`, and run
`python3 aods/tools/aods_validate.py` only when present and executable without
changing the environment.
