# Risk Register

**Document ID:** `AODS-RISK`
**Status:** Proposed
**Version:** 0.1.0
**Date:** 2026-07-29
**Scope:** Risks to the *development process*. Product and business risks belong to the PMO; infrastructure
incidents belong to `docs/OPERATIONS.md`.

---

## 1. How this register differs from the conflict register

| | Conflict register | Risk register |
|---|---|---|
| Records | A contradiction that **exists now** | A failure that **could occur** |
| Evidence | Two citations that disagree | A mechanism and a likelihood |
| Closed by | A human decision (`HC-03`) | A control that reduces exposure |
| Lifecycle | Append-only, resolved once | Living; re-scored as controls land |

A risk that has already materialised is not a risk — it is a conflict or an incident. Several entries below are
scored high precisely because the repository shows the failure has *already happened at least once*.

---

## 2. Scoring

Likelihood × Impact, both 1–5. **Exposure = L × I.** Scores are judgement, so each carries its reasoning; a number
without reasoning is unarguable and therefore useless.

| Exposure | Band | Response |
|----------|------|----------|
| 20–25 | **Critical** | Must have a mechanical control before dependent work proceeds |
| 12–19 | **High** | Mechanical control required this wave |
| 6–11 | **Medium** | Control or accepted with a named owner |
| 1–5 | **Low** | Monitor |

---

## 3. Register

### `R-001` — Agent edits files outside its task scope

| Field | Value |
|-------|-------|
| **Mechanism** | Auto Mode has repository-wide write access and no supervision. "Related" files invite opportunistic edits. |
| **L** | 5 — near-certain over many tasks without a control |
| **I** | 4 — a silent unrelated change can reach production via an approved PR |
| **Exposure** | **20 — Critical** |
| **Controls** | `allowed_paths` per node; `--gate allowlist`; prompt prohibition #1; task record § "Files actually changed" with conformance verdict |
| **Residual** | An operator who omits `--node` gets a skip, not a failure (`OI-V2`) |
| **Owner** | Prompt Engineer role |
| **Recovery** | `git revert` the merge; the task record's declared allow-list identifies exactly which hunks were illegitimate |

### `R-002` — Agent implements a hallucinated requirement

| Field | Value |
|-------|-------|
| **Mechanism** | A specification gap is filled by inference. The output looks confident and passes review because it is plausible. |
| **L** | 5 — this repository contains a 1,052-line document of confirmed-false claims that reads authoritatively |
| **I** | 5 — wrong behaviour with no trace back to a decision; discovered months later |
| **Exposure** | **25 — Critical** |
| **Controls** | `RESTATE` block requiring `path:line` per requirement; `Assumptions` section expected empty; `forbidden_context` deny-list; halt trigger `E3`; `--gate citation` |
| **Residual** | A fabricated *quotation* of a real file passes the path check. Mitigated by `HC-05` step 3 verifying quotes |
| **Owner** | Documentation Architect role |
| **Recovery** | Trace via the task record; if no citation exists, the change is unauthorised and reverted |

### `R-003` — A merged PR cites a document that does not exist on `main`

| Field | Value |
|-------|-------|
| **Mechanism** | Governing documents live on a feature branch; a PR cites them; review checks the working tree, not the merge base |
| **L** | 5 — **already occurred**: PR #127 merged citing `CANON-LOCK.md` (`CR-001`) |
| **I** | 5 — auditability void; nobody can reconstruct what criteria the change was judged against |
| **Exposure** | **25 — Critical** |
| **Controls** | `--gate citation` resolves each path with `git cat-file -e <base>:<path>`; `registry` gate cross-checks `on_main`; `links` gate reports unmerged targets distinctly |
| **Residual** | The gate is not yet required in CI, and no PR template forces the `Authority:` line (`CR-018`) |
| **Owner** | Architecture Board |
| **Recovery** | Merge PR #125 (`HC-02`), which retroactively resolves the citation |

### `R-004` — Merging to `main` deploys to the live site unintentionally

| Field | Value |
|-------|-------|
| **Mechanism** | `deploy-staging.yml` triggers on push to `main` for `app/**`, `alembic/**` and others; staging is the **same VPS** as production |
| **L** | 4 — every qualifying merge does this by design |
| **I** | 5 — customer-visible, and there is no separate environment to catch it first |
| **Exposure** | **20 — Critical** |
| **Controls** | The danger box in `HC-07` with a pre-merge path check and backup requirement. **Prose only** — the trigger still exists (`CR-011`) |
| **Residual** | High. This is the largest unmitigated risk in the register |
| **Owner** | DevOps / owner |
| **Recovery** | Revert to the recorded pre-merge SHA and re-deploy; `HC-07` step 3b requires saving it beforehand |

### `R-005` — Catalog data written to production by a routine script

| Field | Value |
|-------|-------|
| **Mechanism** | 18 scripts default `KARZAR_API_BASE` to `https://api.karzartools.com/api/v1`. Running one without setting the variable writes to the live catalog |
| **L** | 4 — the failure mode is the default path |
| **I** | 5 — customer-visible wrong product data; selective reversal is hard |
| **Exposure** | **20 — Critical** |
| **Controls** | `--gate ingestion-boundary`; `KNOW` prompt hard stops; `HC-09` target verification; `ADR-012` |
| **Residual** | The gate now detects all 18, but the defaults themselves are unchanged (`CR-004`); detection is not remediation |
| **Owner** | Backend Architect |
| **Recovery** | Restore from the backup taken before the run; if none, reconstruct from the source extract's provenance record |

### `R-006` — Specification and code drift apart silently

| Field | Value |
|-------|-------|
| **Mechanism** | Code changes without the spec; or a spec is amended without the code. Nothing compares them |
| **L** | 4 — observed: services call `db.commit()` against documented rule BE-01 (`CR-021`) |
| **I** | 4 — the spec stops being usable as a source of truth, which collapses principle 10 |
| **Exposure** | **16 — High** |
| **Controls** | `--gate openapi` for the API surface; `HC-05` step 8 greps for BE-01 violations; `DOC` nodes required after `IMPL`; `TEST` nodes written from spec, not code |
| **Residual** | Only the API surface has a mechanical drift check. Internal rules rely on review |
| **Owner** | System Architect |
| **Recovery** | Decide which side is right (`HC-03`), then fix the other; never assume the code is correct |

### `R-007` — Governance documents contradict each other

| Field | Value |
|-------|-------|
| **Mechanism** | Three parallel governance systems (PMO, Architecture Board, Audit) with no precedence rule |
| **L** | 5 — **already occurred** 22 times (`CR-001`…`CR-022`) |
| **I** | 3 — work stalls or proceeds on the wrong basis, but is usually recoverable |
| **Exposure** | **15 — High** |
| **Controls** | Authority model precedence ladder; document registry with classes and ranks; conflict register; `AUD-doc-conflict-scan` prompt |
| **Residual** | The ladder itself is `Proposed` until `HC-02` ratifies it |
| **Owner** | Architecture Board |
| **Recovery** | `HC-03` per conflict |

### `R-008` — Context truncation loses the specification mid-task

| Field | Value |
|-------|-------|
| **Mechanism** | The window fills; the model silently drops earlier content and does not report it |
| **L** | 3 — the governing docs here are small (`ARCHITECTURE.md` 91 lines, `API_CONTRACT.md` 78), which lowers this materially |
| **I** | 4 — implementation proceeds against a half-remembered spec |
| **Exposure** | **12 — High** |
| **Controls** | Tiered budgets with ≥25% headroom; T1 loaded last; `RESTATE` as a detector; two-large-document ceiling; node splitting |
| **Residual** | Behavioural, not mechanical. Detected only via a visibly thin `RESTATE` |
| **Owner** | Prompt Engineer |
| **Recovery** | Re-execute with a narrower node; never continue from a partial understanding |

### `R-009` — Agent claims validation passed without running it

| Field | Value |
|-------|-------|
| **Mechanism** | The model optimises for a finished-looking response; "tests should pass" is cheap and looks complete |
| **L** | 4 |
| **I** | 4 — a broken change merges with a green-looking record |
| **Exposure** | **16 — High** |
| **Controls** | Prompt prohibition #7; task record must contain verbatim output; `HC-05` step 4 rejects on "should pass"; **the reviewer re-runs the gates independently** |
| **Residual** | Fabricated output is possible in principle (`OI-V6`); independent re-running is the real control |
| **Owner** | QA role |
| **Recovery** | Re-run the gates; if they fail, the record was false — treat the whole task record as unreliable and re-execute |

### `R-010` — Migration applied that cannot be reversed

| Field | Value |
|-------|-------|
| **Mechanism** | An empty or untested `downgrade()`, or a destructive operation approved without noticing |
| **L** | 2 — `HC-08` is a strong procedure |
| **I** | 5 — potential data loss on a live catalog |
| **Exposure** | **10 — Medium** |
| **Controls** | `IMPL-schema-migration` prompt requires up/down/up locally; `HC-08` requires a verified backup, a recorded pre-head, a rollback command, and a destructive-operation grep |
| **Residual** | `G-18` is not in CI — it runs only at `HC-08`, so it depends on the human performing it |
| **Owner** | Database Architect / owner |
| **Recovery** | Restore the pre-migration backup; the rollback command is recorded in the PR body by procedure |

### `R-011` — Line-number citations drift as documents change

| Field | Value |
|-------|-------|
| **Mechanism** | AODS relies on `path:line` citations. Editing a document shifts every line below the edit; the citation still resolves but now points elsewhere |
| **L** | 4 — inevitable as documents evolve |
| **I** | 2 — usually caught because the quoted text no longer matches |
| **Exposure** | **8 — Medium** |
| **Controls** | Citations pair the line with the quoted text, so a mismatch is visible; `HC-01` step 3 and `HC-05` verify quotes rather than line numbers |
| **Residual** | Accepted. `--gate links` catches vanished files, not shifted lines (`OI-C2`) |
| **Owner** | Documentation Architect |
| **Recovery** | Re-locate by quoted text (`git grep`), then correct the line |

### `R-012` — PMO state diverges across its mirrors

| Field | Value |
|-------|-------|
| **Mechanism** | Six surfaces must be updated per status change; six `*_PROGRESS.md` pairs exist at two paths with no canonical one |
| **L** | 5 — **already occurred**: six divergent pairs (`CR-007`) |
| **I** | 2 — misleading status, rarely damaging to code |
| **Exposure** | **10 — Medium** |
| **Controls** | `--gate pmo` detects divergence and orphan task IDs; `GOV-pmo-sync` prompt updates both copies and refuses to pick a winner |
| **Residual** | Cannot be fixed by an agent — canonicalisation is `HC-04` |
| **Owner** | PMO role |
| **Recovery** | `HC-04` decides the canonical path; merge content; update the Cursor rule |

### `R-013` — Quality is self-certified rather than measured

| Field | Value |
|-------|-------|
| **Mechanism** | The party doing the work also scores it. `SCORECARD-AFTER-REMEDIATION.md` claims 9.0/10 across all categories against an audit measuring 5.7 |
| **L** | 4 — **already occurred** (`CR-006`) |
| **I** | 3 — decisions made against a false quality picture |
| **Exposure** | **12 — High** |
| **Controls** | Audit generations are separate; role separation forbids the implementer from re-scoring; `AUD` prompts require a shown command per number; scorecard is on the forbidden-context list |
| **Residual** | With one operator, genuine independence is unavailable (`OI-H1`) |
| **Owner** | Architecture Board |
| **Recovery** | An independent audit generation supersedes; never edit a past scorecard |

### `R-014` — Operator bypasses AODS by typing an ad-hoc request

| Field | Value |
|-------|-------|
| **Mechanism** | Prompt files require effort; typing a request does not. No task record, no allow-list, no gates |
| **L** | 4 — the convenient path is the likely path |
| **I** | 3 — one ungoverned change; the system still holds for the rest |
| **Exposure** | **12 — High** |
| **Controls** | Always-on Cursor rule as a safety floor (forbidden context, no push, halt-instead-of-guess); making prompts genuinely easier to use than typing |
| **Residual** | High and structural. Advisory only |
| **Owner** | Owner |
| **Recovery** | None needed if the change is reviewed at `HC-05`; the loss is traceability, not correctness |

### `R-015` — AODS itself becomes stale documentation

| Field | Value |
|-------|-------|
| **Mechanism** | The system is 20+ documents describing a process. If practice diverges, AODS joins the pile of authoritative-sounding stale docs it was built to fix |
| **L** | 3 |
| **I** | 4 — self-defeating, and it would add a fourth governance system in effect |
| **Exposure** | **12 — High** |
| **Controls** | Registries are machine-checked against reality (`--gate registry`, `--gate graph`); failure criterion `F-06`; `HC-14` on every amendment; `F-09` flags AODS >1 wave behind Canon Lock |
| **Residual** | Prose documents cannot be validated against practice by a script |
| **Owner** | Project Architect role |
| **Recovery** | Re-audit AODS against actual merged PRs; quarantine any part that is not being followed rather than pretending it is |

### `R-016` — Dependency drift introduced by an agent

| Field | Value |
|-------|-------|
| **Mechanism** | An agent adds a package to solve a problem; it works locally and breaks CI or production |
| **L** | 2 — prompts forbid it explicitly and it is a `D3` halt |
| **I** | 3 |
| **Exposure** | **6 — Medium** |
| **Controls** | Prompt prohibition #4; lockfiles and `requirements*.txt` outside every `IMPL` allow-list; Dependabot handles upgrades separately |
| **Residual** | Low |
| **Owner** | Backend / Frontend Architect |
| **Recovery** | Revert; re-solve without the dependency, or raise an ADR |

### `R-017` — Repeated work because prior findings were lost

| Field | Value |
|-------|-------|
| **Mechanism** | No model memory. A finding not written to an artifact is discovered again at full cost |
| **L** | 4 |
| **I** | 2 — wasted effort, not incorrect output |
| **Exposure** | **8 — Medium** |
| **Controls** | Mandatory task record with "Discovered but NOT fixed"; conflict register; `DONE.md`; `AUD` nodes must check for a prior record first |
| **Residual** | Depends on records being written even for trivially successful tasks |
| **Owner** | Knowledge Engineer |
| **Recovery** | Search task records by node ID before starting any audit |

### `R-018` — Model capability shortfall on high-stakes nodes

| Field | Value |
|-------|-------|
| **Mechanism** | Auto Mode chooses the model. A weaker model on an `R4` specification node produces plausible, subtly wrong architecture |
| **L** | 3 |
| **I** | 4 — a wrong spec propagates into every implementation node beneath it |
| **Exposure** | **12 — High** |
| **Controls** | Model-independent prompts, so a shortfall surfaces as a gate failure rather than silent quality loss; `HC-01` on every spec; `R4` nodes may not produce code |
| **Residual** | Capability class is advisory in Auto Mode (`OI-M1`) |
| **Owner** | Project Architect |
| **Recovery** | Re-execute the node; consider pinned-model execution outside Auto Mode for `R4` work |

---

## 4. Exposure summary

| Risk | Exposure | Band | Mechanical control? |
|------|----------|------|--------------------|
| `R-002` hallucinated requirement | 25 | Critical | Partial |
| `R-003` citation to unmerged doc | 25 | Critical | **Yes** (`G-07`) |
| `R-001` out-of-scope edit | 20 | Critical | **Yes** (`G-08`) |
| `R-004` accidental live deploy | 20 | Critical | **No — prose only** |
| `R-005` production data write | 20 | Critical | Partial (`G-10`, 15/18) |
| `R-006` spec/code drift | 16 | High | Partial (`G-09`) |
| `R-009` false validation claim | 16 | High | Partial |
| `R-007` contradictory governance | 15 | High | Partial |
| `R-008` context truncation | 12 | High | No |
| `R-013` self-certified quality | 12 | High | No |
| `R-014` AODS bypass | 12 | High | No |
| `R-015` AODS goes stale | 12 | High | Partial |
| `R-018` capability shortfall | 12 | High | No |
| `R-010` irreversible migration | 10 | Medium | `HC-08` only |
| `R-012` PMO divergence | 10 | Medium | **Yes** (`G-03`) |
| `R-011` line citations drift | 8 | Medium | No |
| `R-017` repeated work | 8 | Medium | No |
| `R-016` dependency drift | 6 | Medium | Partial |

**The register's headline finding:** `R-004` is Critical and has **no mechanical control at all**. Its only defence
is a warning box that a human must read before every merge. Resolving `CR-011` — removing the push trigger from
`deploy-staging.yml` — is the single highest-value change available in this repository, and it is a small diff.

---

## 5. Recovery playbook index

| Situation | First action | Document |
|-----------|-------------|----------|
| Out-of-scope change merged | `git revert` the merge commit | `HC-07` recorded SHA |
| Wrong data in production catalog | Restore the pre-run backup | `HC-09` step 6; `scripts/backup_db.sh` |
| Migration must be undone | `alembic downgrade <pre-head>` | `HC-08` step 6–7 |
| Deploy broke the live site | Revert to the noted SHA and re-deploy | `HC-11` step 3; `HC-12` step 8 |
| Two documents contradict | Open a `CR-nnn`; halt dependent nodes | `CONFLICT-REGISTER.md` |
| Agent halted mid-task | Read `RESUME INSTRUCTIONS`; re-execute with the full context set | `AI-EXECUTION-MODEL.md` §5.2 |
| Gate fails on pre-existing debt | Baseline it with a `CR` reference; do not widen scope | `VALIDATION-FRAMEWORK.md` §5 |
| A gate is producing false positives | Fix the gate, record the reasoning | `VALIDATION-FRAMEWORK.md` §7 |

---

## 6. Open issues

| ID | Issue | Needs |
|----|-------|-------|
| `OI-R1` | Scores are one person's judgement with no calibration data. | Re-score after one wave using observed incidents rather than estimates. |
| `OI-R2` | `R-004` has no mechanical control, and the fix touches a deploy workflow — the riskiest file to change. | `HC-14` plus a deliberate test of the change on a non-`main` branch before merging it. |
| `OI-R3` | Five risks (`R-008`, `R-013`, `R-014`, `R-011`, `R-018`) have no mechanical control and probably cannot have one. | Accept explicitly, with the owner named, rather than leaving them looking mitigated. |
