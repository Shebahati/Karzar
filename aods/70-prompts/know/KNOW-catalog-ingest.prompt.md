---
id: KNOW-catalog-ingest
version: 0.1.0
archetype: KNOW
role: ROLE-KNOW-ENG
capability_class: STRUCTURED-EXTRACT
reasoning_depth: R2
decision_ceiling: D1
lifecycle_state: Draft
parameters:
  - NODE_ID
  - SOURCE_PATH
  - SOURCE_CHECKSUM
  - BRAND
  - TARGET_SCHEMA_PATH
  - ALLOWED_PATHS
context_tiers:
  T1: [docs/architecture/data-ingestion-policy.md, docs/architecture/adr/ADR-012-ingestion-boundary-local-vs-production.md]
  T2: ["{{TARGET_SCHEMA_PATH}}", docs/SCRIPTS.md, docs/SEED_IMPORT.md]
  T3: [scripts/]
forbidden_context:
  - frontend/AI_CONTEXT.md
  - frontend/BACKEND_NON_COMPLIANCE.md
  - frontend/BACKEND_HANDOFF.md
  - docs/FRONTEND_IMPLEMENTATION_GUIDE.md
  - docs/GO_LIVE_EXECUTION_PLAN.md
  - docs/audits/v1/
  - docs/audits/v2/SCORECARD-AFTER-REMEDIATION.md
gates: [ingestion-boundary, lint, types, allowlist, citation]
produces: [KNOWLEDGE-EXTRACT, TASK-RECORD]
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

Extract `{{BRAND}}` product data from `{{SOURCE_PATH}}` into a schema-valid, provenance-stamped
structured extract — writing to a **local** target only.

## 3. ALLOWED SCOPE

You may create or modify ONLY these paths:

```
{{ALLOWED_PATHS}}
data/imports/{{BRAND}}/extracts/
aods/reports/tasks/{{NODE_ID}}.md
```

## 4. FORBIDDEN SCOPE — READ THIS TWICE

| Path / target | Reason |
|---------------|--------|
| **Any production API or database** | `ADR-012` forbids production defaults for routine work. A wrong write is visible to customers and hard to reverse selectively |
| `app/**` | Ingestion does not change application code |
| `alembic/**` | Schema changes are a separate node |
| Existing scripts in `scripts/` not named in ALLOWED SCOPE | 18 of them currently default to the production API (`CR-004`); do not imitate them |
| `.env`, `.deploy-secrets` | Credentials are `HC-10`, human-only |
| `docs/**` | Separate `DOC` node |

**The default-target trap.** Many scripts in this repository default `KARZAR_API_BASE` to
`https://api.karzartools.com/api/v1`. That default is a known BLOCKER-severity violation of `ADR-012`
(`CR-004`). If you write or modify a script, its default **must** be local, and it must fail loudly
rather than silently falling back to a remote base.

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
| 1 | T3 | One existing import script | FULL | The house pattern for argument parsing, dry-run, and reporting — **but not its default target** |
| 2 | T2 | `docs/SCRIPTS.md` | §the relevant script family | How scripts are expected to be invoked |
| 3 | T2 | `{{TARGET_SCHEMA_PATH}}` | FULL | The exact field names, types, and required-ness |
| 4 | T1 | `docs/architecture/adr/ADR-012-ingestion-boundary-local-vs-production.md` | FULL | **The binding boundary between local and production ingestion** |
| 5 | T1 | `docs/architecture/data-ingestion-policy.md` | FULL | How catalog data may enter each environment |
| 6 | T2 | `{{SOURCE_PATH}}` | As needed | The data to extract |

If any T1 input is missing, unreadable, or does not contain the section named: HALT (E1).

## 7. ARCHITECTURE RULES

| # | Rule | Citation |
|---|------|----------|
| 1 | Routine ingestion targets a **local** API/database. Production writes are a separate, explicitly authorised path. | `ADR-012`; `docs/architecture/data-ingestion-policy.md` |
| 2 | Ingestion is **idempotent**, keyed by source checksum. Re-running must not double-write. | `docs/architecture/data-ingestion-policy.md` |
| 3 | Every extracted record carries provenance: source path, source URL if any, checksum, retrieval date. | `docs/architecture/data-ingestion-policy.md` |
| 4 | Never invent a field value. A missing value is `null` with a recorded reason — never a plausible guess. | `{{TARGET_SCHEMA_PATH}}` |
| 5 | Extraction and loading are distinct steps. Produce the extract, validate it, and only then load. | `docs/SEED_IMPORT.md` |

If the TASK appears to require violating one of these, HALT (E2) and report the conflict.

Rule 4 is the defining constraint of this archetype. A hallucinated product specification is worse
than a missing one: a gap is visible and fixable, while a plausible wrong dimension propagates into
customer-facing pages and is effectively undetectable afterwards.

## 8. FILE MODIFICATION RULES

- **Create:** the extract file(s) under `data/imports/{{BRAND}}/extracts/`, and only scripts named
  in ALLOWED SCOPE.
- **Modify:** nothing else.
- **Never delete** any file, including a previous extract — extracts are provenance.
- **Never** hard-code a remote URL as a default.
- **Never** read credentials from any file, or accept them as a CLI argument.
- **Never** execute a load step against a target you have not printed and verified first.
- Any script you write must: require an explicit `--target` or read `KARZAR_API_BASE`, **fail with a
  non-zero exit** if it is unset (never fall back), support `--dry-run`, and print counts before and after.

## 9. TASK

1. Verify the source. Compute its checksum and compare to `{{SOURCE_CHECKSUM}}`:

   ```bash
   sha256sum {{SOURCE_PATH}}
   ```

   A mismatch is a hard stop — you would be extracting from a different document than the one authorised.
2. Print the resolved target and prove it is local:

   ```bash
   echo "target=${KARZAR_API_BASE:-UNSET}"
   ```

   If it is unset or contains `api.karzartools.com`, HALT (E2).
3. Extract records into the schema at `{{TARGET_SCHEMA_PATH}}`. For every field: either a value present
   in the source, or `null` with a reason. No inference, no unit conversion unless the schema specifies
   the unit, no "typical value for this product class".
4. Validate every record against the schema. Report the count of valid, invalid, and skipped records,
   with reasons.
5. Write the extract with a provenance header: source path, checksum, retrieval date, record count,
   extractor node ID.
6. Report anomalies: duplicate SKUs, out-of-range values, records whose fields conflict internally.
   Do not silently drop them.
7. **Stop before loading.** Loading requires `HC-09` human authorisation. Your output is a validated
   extract plus the exact command a human would run to load it.

## 10. EXPECTED OUTPUTS

1. A validated extract under `data/imports/{{BRAND}}/extracts/` with a provenance header.
2. A task record at `aods/reports/tasks/{{NODE_ID}}.md` including: source checksum, resolved target,
   counts (valid / invalid / skipped), anomaly list, and the proposed load command.
3. A response following OUTPUT FORMAT (§14).

You do **not** load data anywhere. That is `HC-09`.

## 11. VALIDATION CHECKLIST

| # | Command | Expected |
|---|---------|----------|
| 1 | `sha256sum {{SOURCE_PATH}}` | Matches `{{SOURCE_CHECKSUM}}` exactly |
| 2 | `echo "${KARZAR_API_BASE:-UNSET}"` | A local base (`127.0.0.1` or `localhost`), never `api.karzartools.com` |
| 3 | `python3 -c "import json,sys; d=json.load(open('<extract>')); print(len(d))"` | Record count matches your report |
| 4 | Schema validation of the extract (per `{{TARGET_SCHEMA_PATH}}`) | 100% of emitted records valid |
| 5 | `git diff --name-only` | Only paths inside ALLOWED SCOPE |
| 6 | `grep -rn "api.karzartools.com" <any script you created or modified>` | **No output** |
| 7 | `python3 aods/tools/aods_validate.py --gate ingestion-boundary` | Exit 0 |
| 8 | Run your script twice with `--dry-run` | Identical output — idempotence check |

If a command cannot be run in this environment, say so explicitly in the task record and
mark the criterion UNVERIFIED. Never assert an unrun command passed.

Items 2 and 6 are the two checks that prevent a customer-visible incident. Never mark either UNVERIFIED
and proceed — if you cannot verify the target, you must halt.

## 12. STOPPING CONDITIONS

Halt immediately, using the HALT FORMAT, if any of these is true:

1. `{{SOURCE_PATH}}` does not exist. (E1)
2. The source checksum does not match `{{SOURCE_CHECKSUM}}`. (E1 — **hard stop, no override.**)
3. `KARZAR_API_BASE` is unset, or resolves to a production host. (E2 — **hard stop, no override.**)
4. `ADR-012` or `data-ingestion-policy.md` does not resolve on the merge base. (E2 — the governing
   boundary is unavailable, so no ingestion may proceed; see `CR-001`.)
5. The source is missing a field the schema requires as non-nullable. (E3 — a human decides whether to
   relax the schema or reject the source. Never fabricate the value.)
6. More than 5% of records fail validation. (E3 — likely a wrong parser or wrong source.)
7. The extract would need to write outside ALLOWED SCOPE. (E4)
8. Two attempts have failed. (E5)
9. Any `{{PLACEHOLDER}}` remains unfilled. (E1)

## 13. FAILURE HANDLING

- Attempt 1 fails → inspect the actual source structure; try ONE alternative parsing strategy.
- Attempt 2 fails → HALT with both attempts, the observed source structure, and sample failing records.
- A third strategy is forbidden.
- **Never** loosen the schema to make validation pass.
- **Never** drop failing records silently to improve the success rate. Report them.
- **Never** point at production "just to check whether the field exists there".
- If the source is a scanned or image-based PDF where text extraction is unreliable, HALT and say so.
  Low-confidence extraction of technical specifications is worse than none.

## 14. OUTPUT FORMAT

Respond in exactly this structure:

```
## RESTATE
Governing authority:
  - ADR-012 (<path>:<line>) — <the local/production boundary in your own words>
    [resolves on merge base: YES/NO]  [status: Accepted? YES/NO]
  - data-ingestion-policy.md (<path>:<line>) — idempotence + provenance requirements
    [resolves on merge base: YES/NO]
Constraints I must not violate:
  - Local target only; fail loudly if unset
  - Never invent a field value
  - Idempotent, checksum-keyed
Source verification:
  - path: {{SOURCE_PATH}}
  - expected checksum: {{SOURCE_CHECKSUM}}
  - actual checksum:   <computed>       [MATCH: YES/NO]
Resolved target: <value>                [LOCAL: YES/NO]
Not specified, and I will therefore NOT invent:
  - <fields absent from the source> → null with reason

## PLAN
Files I will change (must be a subset of ALLOWED SCOPE):
  1. data/imports/{{BRAND}}/extracts/<file> — the extract
  2. <script path, if any> — extractor with a local-only default
Files I will NOT change although related:
  1. Existing scripts/** — many carry the CR-004 production default; not imitated, not fixed here
  2. app/**, alembic/** — not an implementation node

## ACT
<the extraction work>

## VERIFY
<verbatim command output for every item in §11>

## RECORD
Task record written to: aods/reports/tasks/{{NODE_ID}}.md
Records: valid=<n> invalid=<n> skipped=<n>
Anomalies: <count, listed in the record>
Proposed load command (for HC-09, NOT run by me):
  KARZAR_API_BASE=http://127.0.0.1:8000/api/v1 python3 <script> --input <extract> --dry-run

STATUS: COMPLETE — extract validated, awaiting HC-09 before any load
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
