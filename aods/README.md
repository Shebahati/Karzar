# AODS — AI-Orchestrated Development System

**Status:** **Accepted.** Binding process system per Architecture Board minute ۱۴۰۵/۰۵/۰۸
(see [`90-governance/DELIVERABLES-AND-ADOPTION.md`](90-governance/DELIVERABLES-AND-ADOPTION.md) §4).
**Version:** 1.0.0 · **Accepted:** ۱۴۰۵/۰۵/۰۸ (2026-07-30)

AODS is the operating system for AI-assisted development in this repository. It defines how a change is
specified, executed, validated, recorded, and approved — so that an agent running in **Cursor Auto Mode**,
with no memory of prior conversations and no human watching, can either produce a governed, mergeable
change or **stop safely with a precise question**.

It governs *process*. It does not decide *what* Karzar builds — that authority belongs to the Architecture
Board (`docs/architecture/`) and the PMO (`project-management/`), and AODS defers to both.

---

## Run it

The validators are stdlib-only Python 3 and need no installation:

```bash
# Full picture, including known debt
python3 aods/tools/aods_validate.py --all

# Blocking view: known debt suppressed via the baseline
python3 aods/tools/aods_validate.py

# One gate
python3 aods/tools/aods_validate.py --gate registry

# Machine-readable
python3 aods/tools/aods_validate.py --all --json

# What gates exist
python3 aods/tools/aods_validate.py --list-gates
```

Expect failures on the current tree. That is the point: the gates report the repository's real state, and
they independently confirm `CR-004`, `CR-007`, and `CR-012`, and one of them discovered `CR-023`.

---

## Read it in this order

The numeric directory prefixes are the reading order — each layer depends on the one above it.

| # | Read | Answers |
|---|---|---|
| 0 | [`AODS-CHARTER.md`](AODS-CHARTER.md) | What is this, what does it promise, what would make it a failure? |
| 1 | [`10-repository-intelligence/`](10-repository-intelligence/) | What is actually true in this repo? Which document wins? What contradicts what? |
| 2 | [`20-lifecycle/`](20-lifecycle/) | In what order does work happen, and what blocks what? |
| 3 | [`30-roles/`](30-roles/) | Who (which bounded identity) does each thing? |
| 4 | [`40-artifacts/`](40-artifacts/) | What gets produced, and what is it called? |
| 5 | [`50-ai-execution/`](50-ai-execution/) | How does the model execute a task without drifting? |
| 6 | [`60-human/`](60-human/) | What must the human physically do, keystroke by keystroke? |
| 7 | [`70-prompts/`](70-prompts/) | The executable instruction set — 11 real prompts, one mandatory template. |
| 8 | [`80-validation/`](80-validation/) | How do we know a stage is genuinely done? |
| 9 | [`90-governance/`](90-governance/) | Who decides, what are the risks, how does knowledge move, how does this pack evolve? |

Machine-readable state lives in [`registry/`](registry/); the validators live in [`tools/`](tools/).

---

## If you have five minutes

Read these four things:

1. [`AODS-CHARTER.md`](AODS-CHARTER.md) §1.7 — the twelve principles and the specific mechanism that
   enforces each one.
2. [`10-repository-intelligence/AUTHORITY-MODEL.md`](10-repository-intelligence/AUTHORITY-MODEL.md) §3 —
   the precedence ladder, i.e. which document wins when two disagree.
3. [`10-repository-intelligence/CONFLICT-REGISTER.md`](10-repository-intelligence/CONFLICT-REGISTER.md)
   §Summary — 23 recorded contradictions in the repository, none silently resolved.
4. [`90-governance/DELIVERABLES-AND-ADOPTION.md`](90-governance/DELIVERABLES-AND-ADOPTION.md) §6 — the
   nine next actions for the human operator, in order.

---

## If you are an agent about to execute a task

You are in Auto Mode. You have no memory. Do this:

1. Read [`50-ai-execution/CURSOR-AUTO-MODE-STRATEGY.md`](50-ai-execution/CURSOR-AUTO-MODE-STRATEGY.md).
2. Find the prompt for your task archetype under [`70-prompts/`](70-prompts/). Do not improvise a prompt.
3. Load **only** the context the prompt lists. The forbidden-context list in
   [`50-ai-execution/CONTEXT-MANAGEMENT.md`](50-ai-execution/CONTEXT-MANAGEMENT.md) is binding —
   `frontend/AI_CONTEXT.md` in particular contains roughly a thousand lines of confirmed-false architecture
   claims and must never enter your context.
4. Edit only files inside your node's `allowed_paths`.
5. Run `python3 aods/tools/aods_validate.py` before you claim completion.
6. **Never** push, merge, deploy, mark a document `Accepted`, or write to a production database.
7. If anything is ambiguous, **halt** with a numbered blocker. Halting is a success state; guessing is not.

---

## The three things this pack is trying to fix

Grounded in the audit, not in general principle:

**No enforcement.** The repository has roughly 140 markdown documents and three overlapping governance
systems (PMO, Architecture Board, audit function), and not one validator. AODS adds runnable gates rather
than a fourth system.

**No context discipline.** Agents currently load whatever seems relevant, including documents known to
contain false claims. AODS declares, per prompt, exactly what may and may not be read.

**No machine-checkable notion of authority.** "Which document wins" was answerable only by asking the
owner. AODS ranks every document by class and rank in
[`registry/document-registry.yaml`](registry/document-registry.yaml), and a gate checks that every markdown
file in the repository is classified.

---

## Known limits

Stated up front, because a governance pack that claims completeness is the first one to be disbelieved.

- **This pack is `Accepted` (۱.۰.۰)** as of ۸ مرداد ۱۴۰۵ — see
  [`90-governance/BOARD-MINUTE-AODS-ACCEPTANCE.md`](90-governance/BOARD-MINUTE-AODS-ACCEPTANCE.md).
  Canon Lock row still depends on merging PR #125 (`CR-001`).
- **Its Canon Lock foundation is still unmerged.** The Wave-1 Canon Lock layer lives on PR #125, so
  many citations here do not resolve on `main` (`CR-001`). `--gate links` reports this explicitly instead
  of quietly passing.
- **One human holds every role.** Separation of duties is separation in *time and artifact*, not in person.
  [`90-governance/GOVERNANCE.md`](90-governance/GOVERNANCE.md) §8 lists exactly what that cannot protect
  against.
- **Checkpoint completion is self-reported.** No system inside the repository can prove a human actually
  performed the listed steps.
- **Open issues are marked, not resolved.** Every document ends with an open-issues table requiring a human
  decision. They are deliberately left open rather than assumed away.
