# Naming Conventions

**Document ID:** `AODS-NAMING`
**Status:** Proposed (see [`../AODS-CHARTER.md`](../AODS-CHARTER.md) status honesty note)
**Version:** 0.1.0
**Date:** 2026-07-29
**Required by:** AODS charter § "Deterministic" and § "Auditable"

---

## 1. Why naming is a control, not cosmetics

In a stateless Auto Mode agent, **the filename is the primary retrieval key**. The agent does not remember that
`ADR-010` is about SEO URLs; it finds out by globbing `docs/architecture/adr/ADR-010-*.md`. Naming therefore does
three jobs that would otherwise require memory:

| Job | Mechanism |
|-----|-----------|
| **Addressability** — a prompt can name a document it has never seen | Deterministic path + ID pattern |
| **Authority signalling** — the agent knows a doc's weight before reading it | Directory position + ID prefix map to authority class in [`../registry/document-registry.yaml`](../registry/document-registry.yaml) |
| **Machine validation** — a validator can assert "every X is named Y" | Regex per artifact class (§8) |

**Governing constraint.** These conventions **codify what the repository already does**; they do not re-christen
existing files. Where the repo is internally inconsistent, the inconsistency is recorded as a conflict (`CR-002`
branch naming, `CR-007` PMO paths) and left for human decision — renaming files to satisfy a *Proposed* document
would be AODS granting itself authority, which charter invariant #1 forbids.

---

## 2. Universal rules

| # | Rule | Rationale |
|---|------|-----------|
| N-01 | ASCII only in filenames and directory names. Persian/Arabic script belongs in file *content*, never in paths. | Persian filenames break `git` on some Windows/macOS locales and are unquotable in shell gates. Repository content is bilingual; its paths are not. |
| N-02 | No spaces. Word separator is `-` (hyphen) for documents, `_` for PMO ledgers (existing convention), `_` for Python modules. | Hyphens are shell-safe; the split is not aesthetic, it is "match the neighbourhood" (§3). |
| N-03 | Case is **significant and fixed per class** (§3). Never rely on case-insensitive equivalence. | macOS/Windows checkouts are case-insensitive; two files differing only in case cannot coexist. |
| N-04 | Identifiers are `PREFIX-nnn`, zero-padded to **3 digits**. | Matches existing `tasks.json` (`SEO-001`, `PMO-001`) and Canon Lock (`ADR-010`, `RFC-004`). Sorting is lexicographic and therefore also numeric up to 999. |
| N-05 | An ID, once issued, is **never reused and never renumbered** — even if the artifact is deleted. | Superseded IDs are cited by merged PRs and audit reports; renumbering silently invalidates history. |
| N-06 | Version tokens use SemVer `MAJOR.MINOR.PATCH` in front-matter, **not** in filenames. | `spec-v2-final-FINAL.md` is how specification drift starts. Git holds versions; the file holds the current truth. |
| N-07 | Dates are `YYYY-MM-DD` (Gregorian/ISO 8601) in filenames and front-matter. Jalali dates may appear in prose alongside, never alone. | The repo mixes both (checkpoint "31 Shahrivar" vs `as_of: 2026-07-28`). Machine fields must be one calendar; ISO sorts. |
| N-08 | No `final`, `new`, `old`, `copy`, `v2`, `temp`, `wip`, `backup`, `latest` in any committed filename. | Every one of these is a lie within a month. Supersession is expressed by front-matter `superseded_by` + a registry row. |

### 2.1 Reserved words that trigger a validation failure

`aods_validate.py --gate naming` fails on any tracked file matching, case-insensitively:

```
(^|[-_.])(final|latest|new|old|copy|copy\d*|temp|tmp|wip|backup|bak|draft\d+|untitled|v\d+)([-_.]|$)
```

Exception: `openapi/v1.json` and `/api/v1/` are **path-version contracts** mandated by `docs/API_CHANGELOG.md`
(API versioning policy) — the validator carries these as named allow-list entries, not as a general `v\d+` pardon.

---

## 3. Case and separator by artifact class

The repository already uses three distinct styles. Fighting that would create churn without benefit; the rule is
**match the neighbourhood**, and the neighbourhood is defined here so an agent never has to guess.

| Class | Location | Style | Example (real) |
|-------|----------|-------|----------------|
| Governing decision (ADR/RFC) | `docs/architecture/adr/`, `docs/architecture/rfc/` | `ID-kebab-case.md`, ID uppercase | `ADR-010-seo-url-contract.md` |
| Canon / architecture root docs | `docs/architecture/` | `SCREAMING-KEBAB.md` for canon, `kebab-case.md` for supporting | `CANON-LOCK.md`, `data-ingestion-policy.md` |
| Developer standards | `docs/development/standards/` | `kebab-case.md` | `pr-checklist.md` |
| Top-level contracts & guides | `docs/` | `SCREAMING_SNAKE.md` | `API_CONTRACT.md`, `ARCHITECTURE.md` |
| PMO ledgers | `project-management/` | `SCREAMING_SNAKE.md` | `PROJECT_STATUS.md`, `SEO_PROGRESS.md` |
| PMO sprints | `project-management/sprints/` | `SPRINT_NN.md` | `SPRINT_04.md` |
| Audit evidence | `docs/audits/<generation>/` | `kebab-case.md` or `SCREAMING-KEBAB.md` (both present) | `master-engineering-report-v2.md`, `REMEDIATION-TO-9.md` |
| AODS documents | `aods/<NN>-<area>/` | `SCREAMING-KEBAB.md` | `AUTHORITY-MODEL.md` |
| AODS prompts | `aods/70-prompts/<archetype>/` | `<ARCH>-<slug>.prompt.md` | `IMPL-frontend-route.prompt.md` |
| AODS registries | `aods/registry/` | `kebab-case.yaml` | `document-registry.yaml` |
| AODS tools | `aods/tools/` | `snake_case.py` | `aods_validate.py` |
| AODS reports | `aods/reports/<kind>/` | `<TASK-ID>.json` / `<TASK-ID>.md` | `SEO-005.json` |
| Python modules | `app/`, `scripts/` | `snake_case.py` | `product_service.py` |
| Alembic migrations | `alembic/versions/` | `<rev>_<snake_summary>.py` (tool-generated) | as generated |
| React components | `frontend/*/src/` | `PascalCase.tsx` | `ProductCard.tsx` |
| Next.js routes | `frontend/*/src/app/` | Framework-mandated (`page.tsx`, `[slug]/`) | `brands/[slug]/page.tsx` |

> **Open issue `OI-N1`.** `docs/` mixes `SCREAMING_SNAKE.md` (older, e.g. `API_CONTRACT.md`) with `kebab-case.md`
> (Canon Lock era). Both are recorded above as legitimate. A future Board decision may unify them; until then the
> agent rule is: **new docs under `docs/architecture/` or `docs/development/` use kebab/SCREAMING-KEBAB per the table;
> never rename an existing document as a side effect of another task.** Renames break every inbound citation.

---

## 4. Identifier registry — prefixes and their owners

Every ID prefix in use, its meaning, its issuing authority, and where the counter lives. **An agent must never
invent a new prefix**; that is a `D4` decision (see [`../30-roles/ROLE-ARCHITECTURE.md`](../30-roles/ROLE-ARCHITECTURE.md))
requiring the Board.

### 4.1 Product / delivery IDs (owner: PMO, counter: `project-management/exports/tasks.json`)

| Prefix | Domain | In use |
|--------|--------|--------|
| `PMO` | Project-management system itself | `PMO-001` |
| `SEO` | Search/discoverability work | `SEO-001`…`SEO-004` |
| `CAT` | Catalog / taxonomy / product data | `CAT-001`…`CAT-003` |
| `UX` | Storefront user experience | `UX-001`, `UX-002` |
| `PERF` | Performance / Core Web Vitals | `PERF-001` |
| `SEC` | Security hygiene | `SEC-001` |
| `BE` | Backend engineering | `BE-001` |
| `FE` | Frontend engineering | `FE-001` |
| `KB` | Knowledge base / content platform | `KB-001` |
| `REL` | Release / deployment | `REL-001` |
| `TD` | Tech debt | `TD-001` |
| `OPS` | Operations / infrastructure | `OPS-001` |
| `AODS` | AODS adoption work (**new, introduced by this pack**) | `AODS-001` |

Next free number per prefix = `max(existing) + 1`. The validator `--gate pmo` enforces uniqueness and that every ID
cited in markdown exists in `tasks.json` (this is how orphan IDs were found — see `CR-016`).

### 4.2 Governance IDs (owner: Architecture Board)

| Prefix | Artifact | Counter |
|--------|----------|---------|
| `ADR-nnn` | Architecture Decision Record | `docs/architecture/adr/README.md` index |
| `RFC-nnn` | Request for Comments (design proposal) | `docs/architecture/rfc/rfc-index.md` |
| `EPIC-n` | Delivery epic (Board-level) | `docs/architecture/CANON-LOCK.md` |
| `C-n` | Canon criterion (binding rule inside Canon Lock) | `docs/architecture/CANON-LOCK.md` |

> ADR numbering is **not contiguous** on `main` — `ADR-010` and `ADR-012` exist on the Canon Lock branch, `ADR-011`
> was not found in either tree. Recorded as `CR-010` (dangling/missing canon references). Gaps are permitted by
> N-05; what is *not* permitted is silently reusing `ADR-011` for something new.

### 4.3 AODS-internal IDs (owner: this pack)

| Prefix | Artifact | Counter |
|--------|----------|---------|
| `CR-nnn` | Conflict Register entry | [`../10-repository-intelligence/CONFLICT-REGISTER.md`](../10-repository-intelligence/CONFLICT-REGISTER.md) — append-only |
| `R-nnn` | Risk Register entry | [`../90-governance/RISK-REGISTER.md`](../90-governance/RISK-REGISTER.md) |
| `HC-nn` | Human Checkpoint | [`../60-human/HUMAN-INTERVENTION-MODEL.md`](../60-human/HUMAN-INTERVENTION-MODEL.md) |
| `G-nn` | Validation Gate | [`../80-validation/VALIDATION-FRAMEWORK.md`](../80-validation/VALIDATION-FRAMEWORK.md) |
| `L0`…`L18` | Lifecycle stage | [`../20-lifecycle/PROJECT-LIFECYCLE.md`](../20-lifecycle/PROJECT-LIFECYCLE.md) |
| `ROLE-*` | Role identity | [`../registry/role-registry.yaml`](../registry/role-registry.yaml) |
| `ART-*` | Artifact type | [`ARTIFACT-ARCHITECTURE.md`](ARTIFACT-ARCHITECTURE.md) |
| `D0`…`D5` | Decision ceiling level | [`../30-roles/ROLE-ARCHITECTURE.md`](../30-roles/ROLE-ARCHITECTURE.md) |
| `OI-<x>n` | Open issue raised inside an AODS document | The document itself, prefixed by its area letter |
| `S-nn` / `F-nn` | Success / failure criterion | [`../AODS-CHARTER.md`](../AODS-CHARTER.md) |

---

## 5. Task node names in the workflow graph

Workflow nodes are **not** the same objects as PMO tasks: one PMO task expands to many nodes. Node ID grammar:

```
<TYPE>-<slug>-<nnn>
 │       │       └── 3-digit sequence, unique within type
 │       └────────── lowercase kebab, ≤ 4 words, names the concern
 └────────────────── node archetype (see registry/task-graph.yaml)
```

| Type | Concern | Example |
|------|---------|---------|
| `AUD` | Audit / read-only investigation | `AUD-brandhub-gap-001` |
| `SPEC` | Write or amend a specification | `SPEC-brand-hub-contract-001` |
| `IMPL` | Change code | `IMPL-brand-hub-endpoint-001` |
| `TEST` | Add or change tests | `TEST-brand-hub-api-001` |
| `KNOW` | Knowledge/data ingestion & extraction | `KNOW-insize-catalog-001` |
| `DOC` | Change documentation | `DOC-api-contract-sync-001` |
| `GOV` | Governance / registry / PMO mutation | `GOV-pmo-canonicalise-001` |
| `REL` | Release / deploy activity | `REL-wave-a1-001` |

**Binding rule.** A node's `TYPE` determines its default `allowed_paths`. `IMPL` may not edit `docs/**`; `DOC` may
not edit `app/**`. This is the mechanical expression of atomicity (charter principle 5) and the primary defence
against Auto Mode's "helpfully fixed the docs too" failure. Cross-type work = two nodes = two PRs, or one PR with
both node records attached.

---

## 6. Branch naming

> **Conflict `CR-002` is unresolved.** `docs/development/git-development-workflow.md` and `docs/CONTRIBUTING.md`
> prescribe different grammars, and 20+ live branches follow neither consistently. AODS **does not pick a winner.**
> Recorded, escalated to `HC-04`.

Until the Board decides, the rule an agent follows is **conservative and non-committal**:

1. Read `docs/development/git-development-workflow.md` on the current merge base.
2. Use the pattern it states.
3. If the pattern cannot be determined from that file, **HALT** and cite `CR-002`. Do not invent.

Observed live prefixes, for recognition only (not endorsement): `chore/`, `docs/`, `feat/`, `fix/`, `dependabot/`,
`cursor/`. Cloud-agent branches carry a mandated `cursor/<descriptive-name>-<run>` shape imposed by the execution
platform, which is **outside** repository convention and must not be cited as precedent for human branches.

---

## 7. Commit and PR naming

**Commits** — Conventional Commits, as already practised on `main`:

```
<type>(<scope>): <imperative summary ≤ 72 chars>

<body: why, not what>

Task: <PMO-ID>            # required when a PMO task exists
Node: <NODE-ID>           # required when executed under AODS
Authority: <ADR/RFC/spec IDs cited>
```

`type` ∈ `feat|fix|docs|chore|refactor|test|perf|build|ci|revert`. `scope` is the surface: `backend`, `storefront`,
`admin`, `catalog`, `pmo`, `aods`, `ci`.

> Reality check: only ~11% of existing commits carry a task ID, despite the PMO daily checklist requiring it. AODS
> makes the trailer **required for AODS-executed nodes only** — where it can actually be enforced by the node's own
> gate — rather than declaring a repo-wide rule that history shows will not be honoured. Pretending otherwise would
> create failure criterion **F-04** (a gate that is a wish).

**PRs** — `<type>(<scope>): <summary>` matching the lead commit. The body follows
`docs/development/standards/pr-checklist.md`, which mandates authority citation; `--gate citation` checks that each
cited path resolves **on the merge base** (the check whose absence produced `CR-001`).

---

## 8. Machine-checkable patterns

Implemented by `aods_validate.py --gate naming`. Anchored, `re`-compatible, stdlib only.

| Target | Pattern |
|--------|---------|
| ADR file | `^docs/architecture/adr/ADR-\d{3}-[a-z0-9]+(-[a-z0-9]+)*\.md$` |
| RFC file | `^docs/architecture/rfc/RFC-\d{3}-[a-z0-9]+(-[a-z0-9]+)*\.md$` |
| Sprint file | `^project-management/sprints/SPRINT_\d{2}\.md$` |
| PMO progress ledger | `^project-management/(progress/)?[A-Z][A-Z0-9_]*_PROGRESS\.md$` |
| AODS document | `^aods/(\d{2}-[a-z-]+/)?[A-Z][A-Z0-9-]*\.md$` |
| AODS prompt | `^aods/70-prompts/[a-z-]+/(AUD\|SPEC\|IMPL\|TEST\|KNOW\|DOC\|GOV\|REL)-[a-z0-9-]+\.prompt\.md$` |
| AODS registry | `^aods/registry/[a-z0-9-]+\.(yaml\|json)$` |
| AODS tool | `^aods/tools/[a-z0-9_]+\.py$` |
| PMO task ID | `^(PMO\|SEO\|CAT\|UX\|PERF\|SEC\|BE\|FE\|KB\|REL\|TD\|OPS\|AODS)-\d{3}$` |
| Node ID | `^(AUD\|SPEC\|IMPL\|TEST\|KNOW\|DOC\|GOV\|REL)-[a-z0-9]+(-[a-z0-9]+)*-\d{3}$` |
| Conflict ID | `^CR-\d{3}$` |
| Python module | `^[a-z_][a-z0-9_]*\.py$` |
| React component | `^[A-Z][A-Za-z0-9]*\.tsx$` |

Directories excluded from all naming gates (third-party or framework-owned): `node_modules/`, `.venv/`, `.git/`,
`alembic/versions/`, `frontend/*/src/app/**` (Next.js file-router conventions), `.next/`, `__pycache__/`, `htmlcov/`.

---

## 9. Directory numbering inside `aods/`

Directories carry a two-digit prefix so that `ls` order equals reading order — an agent that lists the tree gets the
intended sequence without a manifest.

| Prefix | Area | Stability |
|--------|------|-----------|
| `00` (root files) | Charter, README | Rare change |
| `10-repository-intelligence` | Audit, authority, conflicts | Living (conflicts change often) |
| `20-lifecycle` | Lifecycle, workflow DAG, timeline | Stable |
| `30-roles` | Role architecture | Stable |
| `40-artifacts` | Artifacts, naming | Stable |
| `50-ai-execution` | Execution model, Auto Mode, context, models | Living (model landscape moves) |
| `60-human` | Human checkpoints | Stable |
| `70-prompts` | Prompt library | Living (most-changed area) |
| `80-validation` | Validation framework | Living |
| `90-governance` | Risk, knowledge flow, governance, adoption | Living |
| `registry/` | Machine-readable state | Living, validated |
| `tools/` | Validators | Living |
| `reports/` | Generated evidence | Append-only |

Gaps are intentional (`45`, `55`, `65`… are free) so a new area can be inserted without renumbering — renumbering
would break every inbound relative link, which is precisely what `--gate links` exists to catch.

---

## 10. Supersession naming

When a document is replaced, **do not rename or delete it.** Do all four:

1. Add front-matter to the old document: `status: Superseded`, `superseded_by: <ID>`, `superseded_on: YYYY-MM-DD`.
2. Add a first-line banner: `> **SUPERSEDED YYYY-MM-DD by [<ID>](<relative-path>).** Retained for audit history.`
3. Set the registry row's `class` to `HISTORICAL` (or `QUARANTINED` if actively misleading) in
   [`../registry/document-registry.yaml`](../registry/document-registry.yaml).
4. If misleading to an agent, set `forbidden_context: true` — the mechanism applied to `frontend/AI_CONTEXT.md`
   (`CR-015`), whose banner alone proved insufficient because the false body text remained readable.

Rationale: a deleted document leaves dangling citations in merged PRs and audit reports, which is unauditable. A
renamed document is worse — the old path 404s while the content still exists, so a reader cannot tell whether the
decision was reversed or merely moved.

---

## 11. Checklist — naming a new artifact

- [ ] Class identified in §3; case and separator taken from the row, not from preference.
- [ ] ID prefix already exists in §4 (if not: **HALT**, `D4` Board decision).
- [ ] Number is `max + 1` for that prefix, zero-padded to 3.
- [ ] No reserved word from §2.1.
- [ ] No version token in the filename; version is in front-matter.
- [ ] Path matches the §8 regex for its class.
- [ ] Registry row added in `document-registry.yaml` (governance-relevant markdown only).
- [ ] Inbound links added from the parent index document — an unlinked document is invisible to a stateless agent.
- [ ] `python3 aods/tools/aods_validate.py --gate naming --gate links --gate registry` passes.
