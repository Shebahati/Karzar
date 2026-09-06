# Board Minute — AODS Operating-Model Simplification (HC-14 / CR-024)

**Document ID:** `AODS-BOARD-MINUTE-003`
**Document type:** Board minute / acceptance evidence
**Status:** **Accepted** (this *is* the minute)
**Version:** 1.0.0
**Date (Gregorian):** 2026-09-06
**Date (Jalali):** ۱۴۰۵/۰۶/۱۵ (۱۵ شهریور ۱۴۰۵)
**Board:** Architecture Board / Owner
**Signed:** Mohammad Shebahati / محمد شباهتی

---

## Decision

**Accept the documentation consolidation in PR #271 and transition AODS from the original 1.0.0 orchestration model to the simplified on-demand operating model.**

| Field | Value |
|-------|-------|
| **Decision ID** | AODS simplification / `HC-14` |
| **Checkpoint** | `HC-14` |
| **Closes** | `CR-024` |
| **PR** | https://github.com/Shebahati/Karzar/pull/271 |
| **Outcome** | **Accepted** |
| **Effective** | Upon merge of this minute with the PR #271 Canon Lock / Charter amendment to `main` |
| **Previous status** | AODS pack **Accepted** in full as version **1.0.0** (۸ مرداد ۱۴۰۵ / 2026-07-30; minute `AODS-BOARD-MINUTE-001`) |

## What is current

AODS remains Karzar’s governance and integrity system. It now operates as a **minimal, on-demand control layer**.

Current authorities: [`../AODS-CHARTER.md`](../AODS-CHARTER.md) (current operating-model section), [`../README.md`](../README.md), and the retained validator / registry controls.

**Retained protections** (apply where the change can break them):

- authority / Canon discipline
- registry integrity
- active-document link integrity
- naming integrity
- OpenAPI drift detection
- ingestion-boundary enforcement
- citation validation where applicable
- explicit production-mutation approval boundaries
- conflict reporting instead of guessing
- human approval for Accepted / Binding status changes
- evidence preservation and traceability

**Operational work-status system:** GitHub Issues and pull requests.

## What is retired as current procedure

The original AODS 1.0.0 recurring orchestration is **superseded** as current executable procedure:

- mandatory named-role ceremony
- mandatory versioned prompt per task
- mandatory task graph
- prompt-library execution protocol
- PMO mirror synchronization
- mandatory full AODS context loading
- task-record ceremony as a universal requirement

AODS 1.0.0 acceptance is **preserved as historical provenance**. Orchestration artifacts remain under `docs/archive/` as historical / evidentiary material and are **not** current executable procedure. Archived files are not current authorities.

## Explicit non-decisions

This minute does **not** change application architecture, product behavior, commerce behavior, payment behavior, or production state.

| Surface | Mutation |
|---------|----------|
| `app/`, `alembic/`, frontend runtime `src/`, `openapi/` | **None** |
| Production API / database / deploy | **None** |

## Canon Lock instruction

Record this minute as the authority for the operating-model transition. Keep the ۸ مرداد ۱۴۰۵ AODS 1.0.0 rows as historical acceptance. Point **current** binding process at the Charter (amended operating model), `aods/README.md`, and retained validator / registry controls — not at archived 1.0.0 orchestration files.
