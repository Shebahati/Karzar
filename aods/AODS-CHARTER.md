# AODS Charter — AI-Orchestrated Development System

**Document ID:** `AODS-CHARTER`
**Document type:** Process / methodology standard (Plane B — design intent)
**Status:** **Proposed** — NOT binding until Architecture Board acceptance
**Version:** 0.1.0
**Date:** 2026-07-29
**Repo:** `https://github.com/Shebahati/Karzar` (checkout role: `Website/backend`)
**Owner (proposed):** Platform / Staff Engineering (logical role)
**Acceptance authority:** Architecture Board (Mohammad Shebahati)

> **Status honesty (mandatory).** Per [`docs/architecture/adr/README.md` §2](../docs/architecture/adr/README.md) and
> [`docs/development/standards/documentation-citation-rules.md`](../docs/development/standards/documentation-citation-rules.md),
> only the Architecture Board may set a document to **Accepted**, and *"silent status upgrades in PRs without Board minute are
> non-compliant."* This charter therefore ships as **Proposed**. It describes how work *should* be executed and provides
> runnable tooling, but it **MUST NOT** be cited as sole merge criteria until a Board minute adds it to
> [`docs/architecture/CANON-LOCK.md`](../docs/architecture/CANON-LOCK.md).
>
> Adoption path and the exact human steps to accept it: [`90-governance/DELIVERABLES-AND-ADOPTION.md`](90-governance/DELIVERABLES-AND-ADOPTION.md).

---

## 1. System Overview

### 1.1 Purpose

AODS is the **operating system for AI-assisted software engineering in the Karzar repository**. It converts an
ad-hoc, human-supervised, chat-driven development style into a **deterministic, auditable, reproducible pipeline**
in which an AI agent running in **Cursor Auto Mode** — with no memory, no supervision, and no conversational
repair — can be handed a task and produce a mergeable, governed change, or **stop safely**.

AODS does not decide *what* Karzar builds. It decides *how* any build is executed, validated, recorded, and approved.

### 1.2 Vision

> Every change to Karzar is produced by a **named role**, executing a **versioned prompt**, against an **explicit
> context set**, bounded by an **allow-list of files**, gated by **objective validation**, traceable to an
> **authoritative specification**, and approved by a **human at a defined checkpoint**.

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
- The prompt library, context assembly rules, and Auto Mode safety protocol.
- Role definitions, artifact definitions, validation gates, and human checkpoints.
- Runnable validators under [`aods/tools/`](tools/).

**Out of scope (explicitly)**

| Not in scope | Why | Where it lives instead |
|---|---|---|
| Product requirements / feature decisions | AODS is process, not product | `docs/architecture/`, PMO |
| Architectural decisions | Board authority, not process authority | ADR / RFC packs |
| Task scheduling, sprints, status | Already owned | `project-management/` (PMO) |
| Changing application code behaviour | This charter is process-only | Feature PRs |
| Re-scoring engineering quality | Audit authority | `docs/audits/v2/` |
| Accepting any document | Board authority | Board minute + Canon Lock row |

### 1.5 Success criteria

AODS is working when **all** of the following are objectively true. Each is measurable by a command or a query.

| ID | Success criterion | Measurement |
|----|-------------------|-------------|
| S-01 | Every merged PR in AODS scope cites its governing authority | `aods/tools/aods_validate.py --gate citation` on the PR body |
| S-02 | No merged change touches files outside its task's declared allow-list | Diff vs `allowed_paths` in the task record |
| S-03 | Zero unregistered markdown documents (every doc has a declared authority class) | `--gate registry` |
| S-04 | Zero broken internal documentation links | `--gate links` |
| S-05 | PMO status is consistent across `tasks.json` and all mirrors | `--gate pmo` |
| S-06 | `openapi/v1.json` matches the running app on every merge | `--gate openapi` |
| S-07 | Every prompt in the library declares context, allow-list, and stop conditions | `--gate prompts` |
| S-08 | Every conflict in the conflict register has a named owner and a decision or an explicit defer | Manual read of `CONFLICT-REGISTER.md`; no `owner: UNASSIGNED` rows |
| S-09 | An Auto Mode agent can complete a task with no clarifying question, or halts with a numbered blocker | Task outcome is `COMPLETE` or `HALTED(reason)`, never `PARTIAL` |
| S-10 | Re-running the same task prompt on the same input commit produces an equivalent diff | Determinism spot-check, quarterly |

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

The twelve founding principles are only real if something enforces them. This table is the spine of AODS;
every later document elaborates one row.

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

These are findings from the audit in [`10-repository-intelligence/REPOSITORY-AUDIT.md`](10-repository-intelligence/REPOSITORY-AUDIT.md).
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
3. **AODS never becomes a second PMO.** It references `project-management/exports/tasks.json`; it never forks task state.
4. **Every gate has a command.** No prose-only gates.
5. **Every prompt is a file under version control.** No prompt lives only in a chat.
6. **No agent pushes, merges, or deploys.** Per `docs/development/git-development-workflow.md` §6: *"No automatic push from agents; human approves push."*
7. **Conflicts are reported, never silently resolved.** The conflict register is append-only; entries are closed by a human decision with a date.

---

## 4. Document map

| Required capability | Document |
|---|---|
| System overview (this) | `AODS-CHARTER.md` |
| Repository intelligence | [`10-repository-intelligence/REPOSITORY-AUDIT.md`](10-repository-intelligence/REPOSITORY-AUDIT.md) |
| Authority hierarchy & conflict strategy | [`10-repository-intelligence/AUTHORITY-MODEL.md`](10-repository-intelligence/AUTHORITY-MODEL.md) |
| Open conflicts requiring human decision | [`10-repository-intelligence/CONFLICT-REGISTER.md`](10-repository-intelligence/CONFLICT-REGISTER.md) |
| Project lifecycle | [`20-lifecycle/PROJECT-LIFECYCLE.md`](20-lifecycle/PROJECT-LIFECYCLE.md) |
| Workflow DAG | [`20-lifecycle/WORKFLOW-GRAPH.md`](20-lifecycle/WORKFLOW-GRAPH.md) |
| Timeline / critical path | [`20-lifecycle/TIMELINE-GRAPH.md`](20-lifecycle/TIMELINE-GRAPH.md) |
| Roles | [`30-roles/ROLE-ARCHITECTURE.md`](30-roles/ROLE-ARCHITECTURE.md) |
| Artifacts | [`40-artifacts/ARTIFACT-ARCHITECTURE.md`](40-artifacts/ARTIFACT-ARCHITECTURE.md) |
| Naming | [`40-artifacts/NAMING-CONVENTIONS.md`](40-artifacts/NAMING-CONVENTIONS.md) |
| AI execution model | [`50-ai-execution/AI-EXECUTION-MODEL.md`](50-ai-execution/AI-EXECUTION-MODEL.md) |
| Cursor Auto Mode strategy | [`50-ai-execution/CURSOR-AUTO-MODE-STRATEGY.md`](50-ai-execution/CURSOR-AUTO-MODE-STRATEGY.md) |
| Context management | [`50-ai-execution/CONTEXT-MANAGEMENT.md`](50-ai-execution/CONTEXT-MANAGEMENT.md) |
| Model capability strategy | [`50-ai-execution/MODEL-CAPABILITY-STRATEGY.md`](50-ai-execution/MODEL-CAPABILITY-STRATEGY.md) |
| Human intervention | [`60-human/HUMAN-INTERVENTION-MODEL.md`](60-human/HUMAN-INTERVENTION-MODEL.md) |
| Prompt library | [`70-prompts/PROMPT-LIBRARY-ARCHITECTURE.md`](70-prompts/PROMPT-LIBRARY-ARCHITECTURE.md) |
| Validation | [`80-validation/VALIDATION-FRAMEWORK.md`](80-validation/VALIDATION-FRAMEWORK.md) |
| Risk | [`90-governance/RISK-REGISTER.md`](90-governance/RISK-REGISTER.md) |
| Knowledge flow | [`90-governance/KNOWLEDGE-FLOW.md`](90-governance/KNOWLEDGE-FLOW.md) |
| Governance | [`90-governance/GOVERNANCE.md`](90-governance/GOVERNANCE.md) |
| Deliverables & adoption | [`90-governance/DELIVERABLES-AND-ADOPTION.md`](90-governance/DELIVERABLES-AND-ADOPTION.md) |
| Machine-readable registries | [`registry/`](registry/) |
| Validators | [`tools/`](tools/) |
