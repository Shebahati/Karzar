<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

## Codex workflow

- Preserve the rule above; for Next.js code, read the relevant local Next guide
  before editing.
- Before a write, confirm Git status and work only inside an explicit path
  allowlist. Keep existing user changes intact.
- Use one kickoff, one bounded execution, and one review. Do not recursively
  audit or auto-correct unrelated findings.
- Run the smallest relevant check first: `npm run lint`, `npm run typecheck`,
  `npm test`, then `npm run build` only when the change warrants it.
- Before handoff, run `git diff --check`; compare tracked changes with
  `git diff --name-only` and untracked files with
  `git ls-files --others --exclude-standard` against the allowlist. Report real
  output and any unfixed issue.
- Do not install or update dependencies, change lockfiles, or edit files beyond
  the approved scope.
