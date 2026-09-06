# AODS Charter — AI-Orchestrated Development System

**Document ID:** `AODS-CHARTER`
**Document type:** Process / methodology standard (Plane B — design intent)
**Status:** **Accepted** — binding process standard
**Version:** 1.1.0
**Date:** 2026-07-29
**Accepted on:** ۱۴۰۵/۰۵/۰۸ (2026-07-30) — AODS 1.0.0 pack
**Operating model amended on:** ۱۴۰۵/۰۶/۱۵ (2026-09-06) — simplified on-demand model
**Accepted by:** Mohammad Shebahati / محمد شباهتی (Architecture Board)
**Repo:** `https://github.com/Shebahati/Karzar` (checkout role: `Website/backend`)
**Owner:** Platform / Staff Engineering (logical role)
**Acceptance authority:** Architecture Board (Mohammad Shebahati)

> **Acceptance record (1.0.0).** Per [`docs/architecture/adr/README.md` §2](../docs/architecture/adr/README.md) and
> [`docs/development/standards/documentation-citation-rules.md`](../docs/development/standards/documentation-citation-rules.md),
> only the Architecture Board may set a document to **Accepted**. This charter was accepted by Board minute on
> **۸ مرداد ۱۴۰۵ (2026-07-30)**, signed **Mohammad Shebahati / محمد شباهتی**. The minute is
> [`90-governance/BOARD-MINUTE-AODS-ACCEPTANCE.md`](90-governance/BOARD-MINUTE-AODS-ACCEPTANCE.md).

> **Operating-model amendment (HC-14).** Architecture Board minute
> [`90-governance/BOARD-MINUTE-AODS-SIMPLIFICATION.md`](90-governance/BOARD-MINUTE-AODS-SIMPLIFICATION.md)
> on **۱۵ شهریور ۱۴۰۵ (2026-09-06)** (PR #271) supersedes the 1.0.0 *orchestration procedure* as current
> executable process. The 1.0.0 acceptance is preserved as historical provenance. Current authorities:
> this Charter’s **current operating model**, [`README.md`](README.md), and retained validator / registry
> controls. Archived 1.0.0 artifacts under `docs/archive/` are evidence, not current procedure.
> `CR-024` is **CLOSED**.

---

## Current operating model (Board-approved, ۱۴۰۵/۰۶/۱۵)

AODS remains Karzar’s governance and integrity system. It operates as a **minimal, on-demand control layer**.
It does not decide *what* Karzar builds. It constrains *how* changes are authorized, checked, and recorded.

**Current procedure**

- Specification outranks implementation for *requirements* (Φ3). Code, OpenAPI, and Alembic are evidence of implemented state.
- Ambiguity must not be guessed through; report conflicts and halt.
- Scope is a safety boundary (one concern; explicit allowlist).
- Evidence backs completion claims.
- Human authority controls Accepted / Binding status changes.
- Production mutation requires explicit authorization.
- Retained machine gates: registry, links, naming, OpenAPI, ingestion-boundary (`README.md`); citation where applicable.
- GitHub Issues / PRs are the operational work-status system.

**Retired as current procedure** (historical 1.0.0 orchestration; preserved under `docs/archive/`):

- mandatory named-role ceremony
- mandatory versioned prompt per task
- mandatory task graph
- prompt-library execution protocol
- PMO mirror synchronization
- mandatory full AODS context loading
- task-record ceremony as a universal requirement

Sections below that describe the 1.0.0 pipeline are **historical design**. They are not current executable
procedure unless restated in this section.

---

## 1. System Overview

### 1.1 Purpose

AODS is the governance and integrity layer for AI-assisted work in the Karzar repository. Under the current
Board-approved model it is an **on-demand control layer**: agents follow Accepted Canon, halt on conflict,
and run the retained validators when the change can break them.

**Historical 1.0.0 design intent** (not current ceremony): convert ad-hoc chat-driven work into a
deterministic Auto Mode pipeline that produces a mergeable change or stops safely.

AODS does not decide *what* Karzar builds.

### 1.2 Vision (historical 1.0.0)

> Every change to Karzar is produced by a **named role**, executing a **versioned prompt**, against an **explicit
> context set**, bounded by an **allow-list of files**, gated by **objective validation**, traceable to an
> **authoritative specification**, and approved by a **human at a defined checkpoint**.

That 1.0.0 vision is superseded as *current procedure* by the current operating model above. Allowlists,
objective validation, specification traceability, and human acceptance remain in force.

The repository, not the conversation, holds the state. Any operator — human or model — can resume any task from
the repository alone.

### 1.3 Core philosophy

| # | Belief | Consequence for the system |
|---|--------|----------------------------|
| Φ1 | **The model is a stateless worker, not a colleague.** | Every prompt is self-contained. Nothing relies on prior turns. |
| Φ2 | **Ambiguity is the defect.** | Ambiguity is resolved by writing a specification, never by model inference. |
| Φ3 | **Specification outranks code.** | Code is *evidence of* the spec (Plane C), never the spec itself (Canon C0). |
| Φ4 | **Trust is manufactured by evidence, not by assertion.** | A stage is complete when a machine-checkable artifact says so. |
| Φ5 | **Scope is a security boundary.** | An agent that may edit any file will eventually edit the wrong file. |
| Φ6 | **Stopping is a success state.** | A task that halts with a precise question outperforms a task that guesses. |
| Φ7 | **Governance must be cheap enough to actually run.** | Every gate has a command. If a gate has no command, it is a wish, not a gate. |

### 1.4 Scope

**In scope**

- The full lifecycle from requirement intake to post-deploy verification, for all four surfaces:
  FastAPI backend (`app/`), Storefront (`frontend/Storefront/`), admin panel (`frontend/admin-panel/`),
  and data/catalog pipelines (`scripts/`, `alembic/`).
- Document authority, conflict resolution, and drift detection across the ~140 markdown documents in the repo.
- Historical 1.0.0: prompt library, context assembly, Auto Mode protocol, role/artifact definitions (now archived).
- Current: validation gates that still have commands, human acceptance of Accepted/Binding, production-mutation approval.
- Runnable validators under [`aods/tools/`](tools/).

**Out of scope (explicitly)**

| Not in scope | Why | Where it lives instead |
|---|---|---|
| Product requirements / feature decisions | AODS is process, not product | `docs/architecture/`, PMO |
| Architectural decisions | Board authority, not process authority | ADR / RFC packs |
| Task scheduling, sprints, status | Already owned | GitHub Issues / PRs (current); archived PMO mirrors are evidence |
| Changing application code behaviour | This charter is process-only | Feature PRs |
| Re-scoring engineering quality | Audit authority | `docs/audits/v2/` |
| Accepting any document | Board authority | Board minute + Canon Lock row |

### 1.5 Success criteria

AODS is working when **all** of the following are objectively true. Each is measurable by a command or a query.

| ID | Success criterion | Measurement |
|----|-------------------|-------------|
| S-01 | Every merged PR in AODS scope cites its governing authority | `aods/tools/aods_validate.py --gate citation` on the PR body |
| S-02 | *(historical 1.0.0)* No merged change touches files outside its task's declared allow-list | Diff vs `allowed_paths` in the task record — not a current universal ceremony |
| S-03 | Zero unregistered markdown documents (every doc has a declared authority class) | `--gate registry` *(current)* |
| S-04 | Zero broken internal documentation links | `--gate links` *(current; active docs)* |
| S-05 | *(historical 1.0.0)* PMO status is consistent across `tasks.json` and all mirrors | `--gate pmo` — retired as current procedure; status = GitHub Issues / PRs |
| S-06 | `openapi/v1.json` matches the running app on every merge | `--gate openapi` *(current)* |
| S-07 | *(historical 1.0.0)* Every prompt in the library declares context, allow-list, and stop conditions | `--gate prompts` — retired as current procedure |
| S-08 | Every conflict in the conflict register has a named owner and a decision or an explicit defer | Manual read of `CONFLICT-REGISTER.md`; no `owner: UNASSIGNED` rows *(current)* |
| S-09 | Halt on ambiguity rather than guessing | Current rule; 1.0.0 Auto Mode `COMPLETE`/`HALTED` ceremony is not required |
| S-10 | *(historical 1.0.0)* Re-running the same task prompt on the same input commit produces an equivalent diff | Determinism spot-check — not a current universal ceremony |

### 1.6 Failure criteria (system is failing — stop and repair AODS itself)

| ID | Failure signal | Severity |
|----|----------------|----------|
| F-01 | A PR merges citing a document that does not exist on `main` | **Critical** — auditability void (this has already happened; see `CR-001`) |
| F-02 | Two documents both marked authoritative give contradictory instructions and no conflict record exists | **Critical** |
| F-03 | An agent silently edited a file outside its allow-list and it merged | **Critical** |
| F-04 | A gate is documented but has no runnable command | **High** — the gate is fiction |
| F-05 | A validator is disabled or baselined without a dated entry and owner | **High** |
| F-06 | The prompt library and the actual prompts used in practice diverge | **High** |
| F-07 | An agent produced a "done" claim not backed by an artifact | **High** |
| F-08 | Human checkpoint was recorded as done without the operator performing the listed steps | **Critical** — governance theatre |
| F-09 | AODS documents grow stale (>1 wave behind Canon Lock) | **Medium** |

### 1.7 Operating principles → enforcement mapping

The twelve founding principles are only real if something enforces them. **Current enforcement** is the
retained validator / registry surface plus human acceptance rules in the current operating model.
The 1.0.0 mapping below is **historical design** where it names prompts, task-graph, TASK-RECORD, or
PMO nodes.

| # | Principle | Concrete enforcement in this system |
|---|-----------|-------------------------------------|
| 1 | **Deterministic** | Prompts are versioned files, not typed text. Context sets are enumerated by path. Task records pin the base commit. Temperature-sensitive freedom is removed by allow-lists and output contracts. |
| 2 | **Auditable** | Every task emits a `TASK-RECORD` artifact; every PR cites authority IDs; every gate emits a JSON report under `aods/reports/`. |
| 3 | **Reproducible** | `WORKFLOW-GRAPH.md` node specs + `registry/task-graph.yaml` + prompt files are sufficient to re-execute without tacit knowledge. |
| 4 | **Incremental** | Hard ceilings: one node = one prompt = one concern; PR budget ≤ 400 changed lines / ≤ 15 files (§ Naming & Governance), else split. |
| 5 | **Atomic** | Node specs forbid multi-responsibility nodes; `IMPL` nodes are separate from `TEST`, `DOC`, and `PMO` nodes. |
| 6 | **Context-controlled** | `CONTEXT-MANAGEMENT.md` defines tiered context budgets and a *forbidden context* list per prompt (e.g. `frontend/AI_CONTEXT.md` is banned). |
| 7 | **Human-governed** | `HUMAN-INTERVENTION-MODEL.md` defines 14 checkpoints with literal keystroke-level steps. AI proposes; the Board accepts. |
| 8 | **Architecture-first** | `ARCH-GATE` blocks any `IMPL` node whose governing ADR/RFC is not `Accepted` in Canon Lock. |
| 9 | **Documentation-first** | Every implementation prompt begins with a mandatory `READ` phase and a `RESTATE` output block proving the docs were read. |
| 10 | **Specification-driven** | The authority model ranks specifications above code; drift is a defect in the *code*, unless an ADR supersedes. |
| 11 | **Validation-first** | Every node declares acceptance criteria *before* execution; `aods_validate.py` is the arbiter. |
| 12 | **Fail-safe** | Every prompt has explicit `STOP CONDITIONS` and a `HALT` output format. Uncertainty escalates; it never improvises. |

---

## 2. Why this repository needs AODS (evidence, not opinion)

These are findings from the audit in [`docs/archive/aods/10-repository-intelligence/REPOSITORY-AUDIT.md`](../docs/archive/aods/10-repository-intelligence/REPOSITORY-AUDIT.md).
They justify the design and are the reason certain controls exist.

| Evidence | Control it justifies |
|----------|----------------------|
| PR #127 merged citing `docs/architecture/CANON-LOCK.md`, which exists only on unmerged branch `docs/wave1-canon-lock-promote` (PR #125) | Citation gate must verify the cited path **resolves on the merge base** (`CR-001`) |
| `frontend/AI_CONTEXT.md` carries an obsolete banner but retains ~1,000 lines of confirmed-false architecture claims | **Forbidden-context list** — this file must never enter an agent's context (`CR-015`) |
| 18 scripts default `KARZAR_API_BASE` to `https://api.karzartools.com/api/v1` while ADR-012 bans production defaults | Ingestion gate on `scripts/**` (`CR-004`) |
| 6 of 14 PMO progress files are divergent duplicates at two paths; the Cursor rule does not say which path is canonical | PMO consistency validator + canonicalisation decision (`CR-007`) |
| Coverage gate stated as 62% / 67% / 67% / 68% in four documents | Single-source numeric facts; doc-reconciliation node (`CR-003`) |
| `openapi/v1.json` is a committed snapshot with **no** CI verification | `OPENAPI-GATE` (`CR-012`) |
| `SCORECARD-AFTER-REMEDIATION.md` self-certifies 9.0/10 against a 5.7/10 audit, with no independent re-audit | Self-certification is not evidence; audit role separation (`CR-006`) |
| ~11% of commits carry a task ID although the PMO daily checklist mandates it | Traceability gate, and an honest lowering of ceremony where it is not enforceable |
| Canon Lock lists ≥7 binding documents that do not exist in the repo | Link-integrity gate (`CR-010`) |
| `Website/docs/` is the declared "authoring SoR" but is **outside** the Git repository | Unversioned-authority escalation (`CR-009`) |
| Two parallel governance systems (PMO checkpoint vs Architecture Board EPIC-1) with no cross-reference; EPIC-1 PRs #126/#127 have no PMO task ID | Authority model must separate *planning* authority from *criteria* authority (`CR-008`) |

**Conclusion.** The repository does not suffer from lack of documentation — it has ~140 markdown documents and three
overlapping governance systems. It suffers from **absence of enforcement**: no validator, no context discipline, and
no machine-checkable definition of "which document wins". AODS supplies exactly that, and deliberately adds no
fourth governance system: it *operationalises* the two that the owner already declared authoritative.

---

## 3. Non-negotiable invariants

Any future change to AODS must preserve these. Breaking one is a redesign, not an edit.

1. **AODS never grants itself authority.** Only a Board minute + a Canon Lock row makes any document binding.
2. **AODS never becomes a second architecture bible.** It references ADR/RFC/IA; it never restates their decisions.
3. **AODS never becomes a second status system.** Current operational status is GitHub Issues / PRs. Archived PMO mirrors are evidence, not a live dual ledger.
4. **Every *current* gate has a command.** No prose-only gates. Retired 1.0.0 gates are not re-imposed by this invariant.
5. **Prompts are not a universal requirement.** The archived prompt library is historical evidence. Agents follow this Charter, Canon Lock, and `README.md`.
6. **No agent pushes, merges, or deploys to production without explicit human authorization.** Per `docs/development/git-development-workflow.md` §6.
7. **Conflicts are reported, never silently resolved.** The conflict register is append-only; entries are closed by a human decision with a date.

---

## 4. Document map

**Current authorities:** this Charter (current operating model), [`README.md`](README.md), [`registry/`](registry/),
[`tools/`](tools/), [`10-repository-intelligence/CONFLICT-REGISTER.md`](10-repository-intelligence/CONFLICT-REGISTER.md),
and Accepted/Binding rows in [`docs/architecture/CANON-LOCK.md`](../docs/architecture/CANON-LOCK.md).

The archive paths below are **historical 1.0.0 design**, not current executable procedure.

| Required capability | Document |
|---|---|
| System overview (this) | `AODS-CHARTER.md` |
| Repository intelligence | [`docs/archive/aods/10-repository-intelligence/REPOSITORY-AUDIT.md`](../docs/archive/aods/10-repository-intelligence/REPOSITORY-AUDIT.md) |
| Authority hierarchy & conflict strategy | [`docs/archive/aods/10-repository-intelligence/AUTHORITY-MODEL.md`](../docs/archive/aods/10-repository-intelligence/AUTHORITY-MODEL.md) |
| Open conflicts requiring human decision | [`10-repository-intelligence/CONFLICT-REGISTER.md`](10-repository-intelligence/CONFLICT-REGISTER.md) |
| Project lifecycle | [`docs/archive/aods/20-lifecycle/PROJECT-LIFECYCLE.md`](../docs/archive/aods/20-lifecycle/PROJECT-LIFECYCLE.md) |
| Workflow DAG | [`docs/archive/aods/20-lifecycle/WORKFLOW-GRAPH.md`](../docs/archive/aods/20-lifecycle/WORKFLOW-GRAPH.md) |
| Timeline / critical path | [`docs/archive/aods/20-lifecycle/TIMELINE-GRAPH.md`](../docs/archive/aods/20-lifecycle/TIMELINE-GRAPH.md) |
| Roles | [`docs/archive/aods/30-roles/ROLE-ARCHITECTURE.md`](../docs/archive/aods/30-roles/ROLE-ARCHITECTURE.md) |
| Artifacts | [`docs/archive/aods/40-artifacts/ARTIFACT-ARCHITECTURE.md`](../docs/archive/aods/40-artifacts/ARTIFACT-ARCHITECTURE.md) |
| Naming | [`docs/archive/aods/40-artifacts/NAMING-CONVENTIONS.md`](../docs/archive/aods/40-artifacts/NAMING-CONVENTIONS.md) |
| AI execution model | [`docs/archive/aods/50-ai-execution/AI-EXECUTION-MODEL.md`](../docs/archive/aods/50-ai-execution/AI-EXECUTION-MODEL.md) |
| Cursor Auto Mode strategy | [`docs/archive/aods/50-ai-execution/CURSOR-AUTO-MODE-STRATEGY.md`](../docs/archive/aods/50-ai-execution/CURSOR-AUTO-MODE-STRATEGY.md) |
| Context management | [`docs/archive/aods/50-ai-execution/CONTEXT-MANAGEMENT.md`](../docs/archive/aods/50-ai-execution/CONTEXT-MANAGEMENT.md) |
| Model capability strategy | [`docs/archive/aods/50-ai-execution/MODEL-CAPABILITY-STRATEGY.md`](../docs/archive/aods/50-ai-execution/MODEL-CAPABILITY-STRATEGY.md) |
| Human intervention | [`docs/archive/aods/60-human/HUMAN-INTERVENTION-MODEL.md`](../docs/archive/aods/60-human/HUMAN-INTERVENTION-MODEL.md) |
| Prompt library | [`docs/archive/aods/70-prompts/PROMPT-LIBRARY-ARCHITECTURE.md`](../docs/archive/aods/70-prompts/PROMPT-LIBRARY-ARCHITECTURE.md) |
| Validation | [`docs/archive/aods/80-validation/VALIDATION-FRAMEWORK.md`](../docs/archive/aods/80-validation/VALIDATION-FRAMEWORK.md) |
| Risk | [`docs/archive/aods/90-governance/RISK-REGISTER.md`](../docs/archive/aods/90-governance/RISK-REGISTER.md) |
| Knowledge flow | [`docs/archive/aods/90-governance/KNOWLEDGE-FLOW.md`](../docs/archive/aods/90-governance/KNOWLEDGE-FLOW.md) |
| Governance | [`docs/archive/aods/90-governance/GOVERNANCE.md`](../docs/archive/aods/90-governance/GOVERNANCE.md) |
| Deliverables & adoption | [`docs/archive/aods/90-governance/DELIVERABLES-AND-ADOPTION.md`](../docs/archive/aods/90-governance/DELIVERABLES-AND-ADOPTION.md) |
| Machine-readable registries | [`registry/`](registry/) |
| Validators | [`tools/`](tools/) |
