---
id: IMPL-frontend-route
version: 0.1.0
archetype: IMPL
role: ROLE-FE-IMPL
capability_class: CODE-GEN
reasoning_depth: R2
decision_ceiling: D2
lifecycle_state: Draft
parameters:
  - NODE_ID
  - SPEC_PATH
  - SPEC_SECTION
  - ROUTE_PATH
  - APP_DIR
  - ALLOWED_PATHS
context_tiers:
  T1: ["{{SPEC_PATH}}", docs/architecture/adr/ADR-010-seo-url-contract.md]
  T2: [docs/architecture/information-architecture/url-map.md, "{{APP_DIR}}"]
  T3: [docs/FRONTEND_INTEGRATION.md]
forbidden_context:
  - frontend/AI_CONTEXT.md
  - frontend/BACKEND_NON_COMPLIANCE.md
  - frontend/BACKEND_HANDOFF.md
  - docs/FRONTEND_IMPLEMENTATION_GUIDE.md
  - docs/GO_LIVE_EXECUTION_PLAN.md
  - docs/audits/v1/
  - docs/audits/v2/SCORECARD-AFTER-REMEDIATION.md
gates: [types, lint, test, allowlist, citation]
produces: [CODE-DIFF, TASK-RECORD]
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

Implement the Next.js route `{{ROUTE_PATH}}` exactly as specified in `{{SPEC_PATH}}` §{{SPEC_SECTION}},
using only data the backend already returns.

## 3. ALLOWED SCOPE

You may create or modify ONLY these paths:

```
{{ALLOWED_PATHS}}
```

## 4. FORBIDDEN SCOPE

| Path | Reason |
|------|--------|
| `app/**` (backend) | Different surface, different role. If the API lacks a field, HALT — do not work around it |
| `package.json`, lockfiles | Dependency changes are D3 → HALT |
| `next.config.*`, `tailwind.config.*` | Build/config changes affect every route |
| `middleware.ts` | Redirect and rewrite behaviour is contract-visible (ADR-010) — separate node |
| Other routes under `{{APP_DIR}}` | One route per node |
| `docs/**` | Separate `DOC` node |
| Shared UI components not named in ALLOWED SCOPE | Changing a shared component affects pages you are not testing |

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

**This list matters more here than anywhere else.** Three of the six forbidden files live under
`frontend/` and describe the frontend's relationship to the backend in terms that are no longer
true. An agent implementing a frontend route is exactly the audience they will mislead.

## 6. INPUTS

Read these files, in this order, to this depth. Read NOTHING else.

| # | Tier | Path | Depth | Why you need it |
|---|------|------|-------|-----------------|
| 1 | T3 | `docs/FRONTEND_INTEGRATION.md` | §the relevant endpoint | How the app calls the API; the response shapes |
| 2 | T2 | A sibling route under `{{APP_DIR}}` | FULL | The conventions for data fetching, metadata, loading and error states |
| 3 | T2 | `docs/architecture/information-architecture/url-map.md` | FULL | The canonical URL for this page; do not invent a path |
| 4 | T1 | `docs/architecture/adr/ADR-010-seo-url-contract.md` | §3 | **Binding URL contract** — canonical paths and redirect rules |
| 5 | T1 | `{{SPEC_PATH}}` | §{{SPEC_SECTION}} FULL | The page contract: sections, fields, metadata, empty states |

If any T1 input is missing, unreadable, or does not contain the section named: HALT (E1).

## 7. ARCHITECTURE RULES

| # | Rule | Citation |
|---|------|----------|
| 1 | The canonical URL shape is fixed by the SEO URL contract. Do not create, alias, or guess a route path. | `docs/architecture/adr/ADR-010-seo-url-contract.md` §3 |
| 2 | Render only fields the API actually returns. Never fabricate a field, and never compute a business value the backend owns. | `{{SPEC_PATH}}` §{{SPEC_SECTION}} |
| 3 | Every page must define its metadata (title, description, canonical) — this is an SEO-first storefront. | `{{SPEC_PATH}}`; SEO tasks in `project-management/exports/tasks.json` |
| 4 | TypeScript strictness must hold; `tsc --noEmit` is a CI gate. No `any`, no `@ts-ignore`. | `.github/workflows/frontend-ci.yml` |
| 5 | Persian is the primary content language; the layout is RTL. Do not introduce hard-coded English user-facing strings. | Storefront convention |
| 6 | Core Web Vitals are a tracked objective (`PERF-001`). Do not add client-side data fetching where a server component suffices. | `project-management/exports/tasks.json` `PERF-001` |

If the TASK appears to require violating one of these, HALT (E2) and report the conflict.

## 8. FILE MODIFICATION RULES

- **Create:** only files named in ALLOWED SCOPE, following the Next.js App Router file conventions
  (`page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx`).
- **Modify:** only the route you were given.
- **Never delete** any file.
- **Never move or rename** any file — route paths are a public contract.
- **Never edit a shared component** to fit this page. If a shared component is not adequate, HALT (E4)
  and propose a separate node; changing it silently affects pages this node does not test.
- **Never add a dependency**, including a "tiny" utility.
- **Never disable a lint rule** or add `@ts-ignore`.
- Match the sibling route's data-fetching pattern exactly. Consistency beats your preference.

## 9. TASK

1. Confirm the canonical path for this page in the URL map, and that `{{ROUTE_PATH}}` matches it.
   If they differ, HALT (E2) — the URL contract wins over the parameter.
2. Create the route with the file structure the sibling route uses.
3. Fetch data server-side using the documented endpoint. Handle: success, empty result, and not-found.
4. Return the correct status behaviour for a missing resource (a 404, not an empty page) — a soft-404
   is an SEO defect on an SEO-first storefront.
5. Define page metadata per the spec, including the canonical URL.
6. Render exactly the sections the spec lists, in the spec's order.
7. Where the spec is silent on presentational detail (spacing, which existing card component),
   follow the sibling route and log the choice under §Decisions. That is your D2 ceiling.
8. Where the spec is silent on **behaviour** (what happens when a list is empty, whether a section is
   omitted or shown empty), HALT (E3). Behaviour is contract.

## 10. EXPECTED OUTPUTS

1. Code changes confined to `{{ALLOWED_PATHS}}`.
2. A task record at `aods/reports/tasks/{{NODE_ID}}.md`.
3. A response following OUTPUT FORMAT (§14).

You do **not** produce: tests, redirects/middleware, sitemap entries, or documentation. Separate nodes.

## 11. VALIDATION CHECKLIST

| # | Command | Expected |
|---|---------|----------|
| 1 | `cd {{APP_DIR}}/../.. && npx tsc --noEmit` | Exit 0 |
| 2 | `npm run lint` (in the app directory) | Exit 0 |
| 3 | `npm run build` | Succeeds — a route that type-checks can still fail to build |
| 4 | `npx vitest run` | All pass |
| 5 | `git diff --name-only` | Only paths inside `{{ALLOWED_PATHS}}` |
| 6 | `grep -rn "any\b\|@ts-ignore\|eslint-disable" <changed files>` | No output |
| 7 | `python3 aods/tools/aods_validate.py --gate allowlist --node {{NODE_ID}}` | Exit 0 |

If a command cannot be run in this environment, say so explicitly in the task record and
mark the criterion UNVERIFIED. Never assert an unrun command passed.

## 12. STOPPING CONDITIONS

Halt immediately, using the HALT FORMAT, if any of these is true:

1. `{{SPEC_PATH}}` does not exist or lacks §{{SPEC_SECTION}}. (E1)
2. `{{SPEC_PATH}}` or `ADR-010` does not resolve on the merge base. (E2 — `CR-001` failure mode.)
3. The spec's status is not `Accepted`. (E2)
4. `{{ROUTE_PATH}}` contradicts the URL map or ADR-010. (E2)
5. **The API does not return a field the page requires.** (E4 — this needs a backend node. Do NOT
   compute it client-side, do NOT call a second endpoint to synthesise it, do NOT hard-code it.)
6. The spec is silent on a behavioural detail. (E3)
7. A shared component would have to change. (E4)
8. A new dependency would be needed. (E3)
9. Two attempts have failed. (E5)
10. Any `{{PLACEHOLDER}}` remains unfilled. (E1)

Condition 5 is the most likely halt for this archetype and the most valuable. The historical failure
pattern in this repository is a frontend that papers over backend gaps, then documents the gap in a
ledger nobody updates — which is how `frontend/BACKEND_NON_COMPLIANCE.md` came to exist and rot.

## 13. FAILURE HANDLING

- Attempt 1 fails → read the actual error; try ONE alternative strategy.
- Attempt 2 fails → HALT with both attempts and their exact errors.
- A third strategy is forbidden.
- If the build fails for a reason unrelated to your change, say so and stop; do not "fix" unrelated code.
- If a type error originates in an API response type you did not author, HALT (E4) rather than casting.
- Never satisfy a type checker with `as unknown as T`.

## 14. OUTPUT FORMAT

Respond in exactly this structure:

```
## RESTATE
Governing authority:
  - {{SPEC_PATH}} §{{SPEC_SECTION}} (<path>:<line>) — <required sections/fields>
    [resolves on merge base: YES/NO]  [status: Accepted? YES/NO]
  - ADR-010 §3 (<path>:<line>) — canonical URL shape is <...>
    [resolves on merge base: YES/NO]
Constraints I must not violate:
  - Canonical URL from the URL map (<path>:<line>)
  - Render only fields the API returns
  - Metadata + canonical required
  - tsc strict, no any/@ts-ignore
API fields this page requires, and where each comes from:
  - <field> ← <endpoint> (docs/FRONTEND_INTEGRATION.md:<line>)  [available: YES/NO]
Not specified, and I will therefore NOT invent:
  - <gap> → <halting? yes/no, and why>

## PLAN
Files I will change (must be a subset of ALLOWED SCOPE):
  1. <path> — <why>
Files I will NOT change although related:
  1. middleware.ts — redirects are a separate node
  2. shared components — changing them affects untested pages
  3. tests/** — separate TEST node

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
