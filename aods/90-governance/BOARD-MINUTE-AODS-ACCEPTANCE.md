# Board Minute — AODS Acceptance (HC-14 / D9)

**Document ID:** `AODS-BOARD-MINUTE-001`
**Document type:** Board minute / acceptance evidence
**Status:** **Accepted** (this *is* the minute)
**Version:** 1.0.0
**Date (Gregorian):** 2026-07-30
**Date (Jalali):** ۱۴۰۵/۰۵/۰۸ (۸ مرداد ۱۴۰۵)
**Board:** Architecture Board
**Signed:** Mohammad Shebahati / محمد شباهتی

---

## Decision

**Adopt the AI-Orchestrated Development System (`aods/`) as the binding process system for this repository.**

| Field | Value |
|-------|-------|
| **Decision ID** | `D9` (PMO) / Phase 3 Accept (AODS adoption) |
| **Checkpoint** | `HC-14` |
| **Outcome** | **Accepted in full** |
| **Pack version** | `1.0.0` |
| **Effective** | Upon merge of the acceptance commit to `main` (PR #128), with Canon Lock row recorded |

## Scope accepted

The full AODS pack delivered under `aods/` — charter, repository intelligence, lifecycle, roles, artifacts,
AI execution / Auto Mode strategy, human intervention model, prompt library, validation framework and
runnable validators, risk / knowledge-flow / governance / deliverables — is **binding process criteria**.

AODS governs *how* changes are executed, validated, recorded, and approved. It does **not** decide product
scope; Architecture Board Canon Lock and the PMO retain that authority. Precedence remains:

> runtime truth → Canon → operational policy → developer standards → plans → evidence

…with AODS providing the mechanical gates and role/prompt model that make that precedence enforceable.

## Explicit non-decisions (still open)

This minute does **not** close conflict-register rows other than enabling process authority. Still OPEN and
requiring separate Board/owner action: `CR-001` (merge Canon Lock PR #125), `CR-002`, `CR-003`, `CR-004`,
`CR-007`, `CR-011`, `CR-012`, `CR-015`, and remaining rows. Phase-4 CI enforcement of AODS gates remains a
separate `HC-14` decision (`OI-GOV-05`).

## Canon Lock instruction

Add a row to `docs/architecture/CANON-LOCK.md` (after PR #125 lands on `main`, or on that promotion branch
before merge):

| Document | Path | Status | Since | Signed | Mandatory for |
|----------|------|--------|-------|--------|----------------|
| AODS — AI-Orchestrated Development System | [`aods/AODS-CHARTER.md`](../../../aods/AODS-CHARTER.md) (pack root [`aods/`](../../../aods/)) | **Accepted** | ۱۴۰۵/۰۵/۰۸ | Mohammad Shebahati | Process execution: roles, prompts, gates, human checkpoints; all Auto Mode work |

## Evidence

- This file
- Document headers / registry flipped to `Accepted` / `1.0.0` in the same acceptance commit
- PMO: `D9` checked; `AODS-001` → `done`; `DONE.md` + `CHANGELOG.md` entry
- PR: https://github.com/Shebahati/Karzar/pull/128
