# Context Management

**Document ID:** `AODS-CONTEXT`
**Status:** Proposed
**Version:** 0.1.0
**Date:** 2026-07-29
**Premise:** Context is a **budgeted, ordered, auditable input** — not "whatever the agent finds useful".

---

## 1. Why context is designed rather than discovered

In Auto Mode the agent assembles its own context unless told otherwise, and it assembles it differently on every run.
That single fact defeats determinism (charter principle 1), reproducibility (3), and context control (6)
simultaneously. AODS therefore treats the context set as **part of the task definition**, versioned in the prompt file.

Three properties follow:

| Property | Consequence |
|----------|-------------|
| **Enumerated** | Every context item is a path (optionally with a section anchor). No categories like "the API docs". |
| **Ordered** | Load order is specified, because position in the window changes influence (§4). |
| **Bounded** | A token budget per tier, with an explicit substitution strategy when a document exceeds it (§5). |

---

## 2. The four context tiers

Every path in a context set belongs to exactly one tier. The tier determines load order, budget share, and whether
it may be summarised.

| Tier | Name | Contents | May be summarised? | Load position |
|------|------|----------|--------------------|---------------|
| **T0** | **Protocol** | The Auto Mode preamble, allow-list, stop conditions, output contract | **Never** | First and last (bracketed) |
| **T1** | **Governing** | The ADRs/RFCs/specs that define correctness for this task | **Never** — only section-scoped | Late (immediately before the task statement) |
| **T2** | **Structural** | Architecture and convention docs; the code being modified | Yes, section-scoped | Middle |
| **T3** | **Reference** | Neighbouring code read for pattern-matching; test fixtures; API contract index | Yes, aggressively | Early (most truncation-tolerant) |

**T0 is bracketed** — the protocol and the allow-list appear at the very start *and* the output contract plus stop
conditions repeat at the very end. Rationale: these are the constraints whose loss is catastrophic and undetectable,
so they are the ones given redundancy against truncation from either direction.

**T1 is never summarised in full.** A summary of a specification is a new specification with no authority. Where a
governing document is large, the prompt cites **sections**, which is a subset (still authoritative) rather than a
paraphrase (not authoritative).

---

## 3. Token budgets

Budgets are expressed as a share of the usable window, not absolute tokens, so they survive model changes — the
model landscape moves faster than this document will.

| Tier | Share of usable window | Hard ceiling |
|------|------------------------|--------------|
| T0 Protocol | 5–8% | — (small and fixed, ~600–900 tokens) |
| T1 Governing | 20–30% | Never dropped; if it does not fit, **split the node** |
| T2 Structural | 30–40% | Max 2 documents >400 lines |
| T3 Reference | 10–20% | First to be cut |
| Headroom for the agent's own output + reasoning | ≥25% | Never encroach |

### 3.1 The headroom rule

At least a quarter of the window is reserved for the agent's reasoning and output. Filling the window with inputs is
a common own-goal: the agent then truncates its *own* plan, produces a partial diff, and reports success. If inputs
cannot fit in 75%, the node is too big — that is a graph defect, not a context defect.

### 3.2 Node-splitting triggers

| Trigger | Action |
|---------|--------|
| T1 alone exceeds 30% | Split by concern (e.g. separate the schema change from the endpoint change) |
| More than 2 large (>400-line) T2 documents needed | Produce a `*-SUMMARY.md` artifact first via a `DOC` node (§5) |
| More than 15 files in the allow-list | Split; also violates the PR budget |
| The task needs both backend and frontend context | Always two nodes — different roles, different allow-lists |

---

## 4. Load order and the recency argument

```
┌─ 1. T0  Auto Mode protocol + hard prohibitions
├─ 2. T0  ALLOWED PATHS / FORBIDDEN PATHS / FORBIDDEN CONTEXT
├─ 3. T3  Reference material (patterns, neighbours, fixtures)
├─ 4. T2  Structural docs + the code to be modified
├─ 5. T1  GOVERNING SPECIFICATIONS (sections, verbatim)
├─ 6. ──  GOAL + acceptance criteria
├─ 7. T0  STOP CONDITIONS + HALT FORMAT + OUTPUT CONTRACT
└─ 8. ──  "Begin with the RESTATE block."
```

**Rationale.** Attention concentrates at the window's edges. The two things that must never be lost are *what
correctness means* (T1) and *what the boundaries are* (T0), so T1 sits adjacent to the goal, and T0 occupies both
edges. Reference material (T3) — the most replaceable content and the most likely to inspire imitation-driven drift —
is placed in the middle where it has the least pull.

This ordering also produces a useful diagnostic: if the `RESTATE` block cites T3 patterns instead of T1
specifications, the agent has inverted its priorities and the task record shows it before any code is reviewed.

---

## 5. Summary artifacts for oversized documents

Real measurements from this repository (tracked markdown, largest first):

| Document | Lines | Handling |
|----------|-------|----------|
| `frontend/AI_CONTEXT.md` | 1,052 | **FORBIDDEN** — never loaded, never summarised (`CR-015`) |
| `docs/BACKEND_COMPREHENSIVE_AUDIT_PLAYBOOK.md` | 851 | Section-scoped only |
| `frontend/docs/audits/02-uiux-audit-en.md` | 689 | Section-scoped; `EVIDENCE` class |
| `frontend/BACKEND_NON_COMPLIANCE.md` | 647 | **FORBIDDEN** — obsolete gap ledger (`CR-015`) |
| `docs/KNOWLEDGE_PLATFORM_PHASE2_TARGET_ARCHITECTURE.md` | 632 | Needs a `SUMMARY` artifact |
| `README.md` | 572 | Section-scoped; never load whole |
| `docs/FRONTEND_IMPLEMENTATION_GUIDE.md` | 555 | Section-scoped |
| `docs/GO_LIVE_EXECUTION_PLAN.md` | 530 | `HISTORICAL` — excluded from context by default |
| `docs/FRONTEND_INTEGRATION.md` | 502 | Section-scoped |

Encouragingly, the *governing* documents are small: `docs/ARCHITECTURE.md` is 91 lines, `docs/API_CONTRACT.md` is 78,
and `CANON-LOCK.md` (on its branch) is 109. **T1 is cheap in this repository** — which means there is no legitimate
excuse for an agent to skip the specification on token grounds, and any prompt claiming otherwise is misconfigured.

### 5.1 Summary artifact contract

When a T2 document must be summarised, a `DOC` node produces `<name>-SUMMARY.md` beside it, and the summary must:

1. State its source path and the source's commit SHA at generation time.
2. Carry class `GENERATED` in the document registry, and `authority: none`.
3. Contain only claims traceable to the source, each with a section anchor.
4. Include a standing banner: `> Generated summary. NOT authoritative. Cite the source, never this file.`
5. Be regenerated when the source changes — staleness is detected by comparing the recorded SHA.

**Why summaries are not authoritative:** if a summary could be cited, the project would acquire a second, lossy
specification, which is exactly the failure that produced `frontend/AI_CONTEXT.md`. The summary exists to help an
agent *navigate* to the right section, not to replace it.

---

## 6. The forbidden-context list

The deny-list is a first-class control, not an afterthought. It is generated from
[`../registry/document-registry.yaml`](../registry/document-registry.yaml) — every row with `forbidden_context: true`.

| Path | Reason | Conflict |
|------|--------|----------|
| `frontend/AI_CONTEXT.md` | Obsolete banner, but ~1,000 lines of confirmed-false architecture claims that read as authoritative | `CR-015` |
| `frontend/BACKEND_NON_COMPLIANCE.md` | Gap ledger whose items are mostly resolved; presents fixed problems as open | `CR-015` |
| `frontend/BACKEND_HANDOFF.md` | Same class of staleness | `CR-015` |
| `docs/GO_LIVE_EXECUTION_PLAN.md` | Pre-launch plan contradicted by the live site; `HISTORICAL` | `CR-014` |
| `docs/audits/v1/**` | Superseded by v2 generation | — |
| `docs/audits/v2/SCORECARD-AFTER-REMEDIATION.md` | Self-certified 9.0 against a 5.7 audit; misleads about quality state | `CR-006` |

### 6.1 Why banners are insufficient

`frontend/AI_CONTEXT.md` already carries an "OBSOLETE AS SoT" banner and is still hazardous. An agent that reads
line 1 and then 1,000 lines of specific, confident, false technical detail will weight the detail over the
disclaimer — detail is actionable, a banner is not. The only reliable control is **non-ingestion**.

Retrieval-time exclusion is enforced three ways, because any single one can be bypassed:

1. Prompt-level `FORBIDDEN CONTEXT` block (per task).
2. Always-on Cursor rule listing the paths (covers ad-hoc requests).
3. `--gate prompts` fails any prompt file that names a forbidden path in its context set.

### 6.2 Adding to the list

A path may be added by any role that observes an agent being misled by it, but the entry must include: path, the
specific false claim observed, the date, and a conflict ID if a decision is needed about the document's fate.
Removing a path from the list is `D4` (Board) — de-quarantining a document is a claim that it is now trustworthy.

---

## 7. Persistent vs temporary knowledge

There is no model memory, so "persistent" means "in the repository".

| Knowledge kind | Where it persists | Lifetime | Read by |
|----------------|-------------------|----------|---------|
| Governing decisions | `docs/architecture/**` (ADR/RFC/Canon) | Permanent | Every task in scope |
| Conventions | `docs/development/standards/**` | Permanent | Every implementation task |
| System state | `aods/registry/*.yaml` | Living | Context assembly, gates |
| Task history / decisions | `aods/reports/tasks/<NODE-ID>.md` | Permanent (rolling archive) | Resumption, audit, dedup |
| Conflicts | `CONFLICT-REGISTER.md` | Append-only | Any agent hitting the same ambiguity |
| Progress | `project-management/**` | Living | Planning |
| Extracted data knowledge | `data/imports/**` + DB | Permanent | `KNOW` nodes |
| **A run's reasoning** | Nowhere | Dies with the run | Nobody |

The last row is the design's central admission. Anything an agent concluded that is not written to one of the rows
above **is gone**. This is why the task record is mandatory even for trivially successful tasks: the discovered-but-
not-fixed findings are otherwise lost, and the next agent re-discovers them at full cost. Loss of these findings is
weakness W9 (repeated work), and the task record is its only cure.

---

## 8. Context refresh strategy

| Situation | Action |
|-----------|--------|
| Task resumes after a halt | Re-read the full context set from scratch. Never trust the halt summary as a substitute for the specs. |
| Gate failed, retrying (attempt 2) | Keep context; add only the failing gate's output. Do not widen the context "to understand better" — that is how scope grows. |
| Base commit moved (upstream merged) | Abort and re-execute from the new base. A diff against a stale base is unreviewable. |
| Governing doc changed mid-task | Hard stop. Re-run `RESTATE` against the new version; if the requirement changed, the node's acceptance criteria may be invalid. |
| A summary artifact's source SHA differs | Regenerate the summary before use, or drop to section-scoped reads of the source. |
| Reviewer requests changes | New execution, new task record, same node ID with an attempt suffix. Not a continuation. |

**"Reviewer requests changes" deserves emphasis.** The natural move is to continue the conversation. In Auto Mode
there is no conversation to continue, so the review comment must be converted into a self-contained brief. The
prompt library provides `GOV-address-review.prompt.md` for exactly this, whose context set is: the review comments,
the diff, and the original node's context set.

---

## 9. Context assembly checklist (prompt author)

- [ ] Every T1 item cites a document that **resolves on the merge base** (the `CR-001` check).
- [ ] Every T1 item has a section anchor unless the document is <150 lines.
- [ ] No item is in the forbidden list (verified by `--gate prompts`).
- [ ] Load order follows §4 exactly.
- [ ] T2 large-document count ≤ 2.
- [ ] Total estimated input ≤ 75% of the usable window.
- [ ] Every item has a stated reason — an item without a reason is an item that should not be loaded.
- [ ] The code files in the allow-list are all present in the context set (you cannot safely edit what you have not read).
- [ ] Stop conditions include `E1` (missing context) with the specific paths that would trigger it.

---

## 10. Open issues

| ID | Issue | Needs |
|----|-------|-------|
| `OI-C1` | Cursor's actual usable window in Auto Mode is not published and varies by served model, so budgets are shares rather than token counts. | Accept; percentages are deliberately model-agnostic. Revisit if Cursor exposes the figure. |
| `OI-C2` | Section anchors (`§"Heading"`) are resolved by the agent's own search, which can match the wrong heading in documents with repeated headings. | Prefer `path:line-range` for critical T1 citations. Line ranges drift as documents change — the mitigation is that `--gate links` catches vanished anchors but **not** shifted line numbers. Residual risk, tracked as `R-011`. |
| `OI-C3` | No mechanism currently detects that a summary artifact is stale beyond comparing the recorded SHA by hand. | Add `--gate summaries` in a later wave; deliberately out of scope for the first validator set to keep it honest and small. |
