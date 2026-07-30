# Board Minute — AODS Phase 4 CI Enforcement (HC-14 / OI-GOV-05)

**Document ID:** `AODS-BOARD-MINUTE-002`
**Document type:** Board minute / acceptance evidence
**Status:** **Accepted** (this *is* the minute)
**Version:** 1.0.0
**Date (Gregorian):** 2026-07-30
**Date (Jalali):** ۱۴۰۵/۰۵/۰۸ (۸ مرداد ۱۴۰۵)
**Board:** Architecture Board
**Signed:** Mohammad Shebahati / محمد شباهتی

---

## Decision

**Enable Phase 4 — wire AODS validation gates into CI as a named required-check candidate.**

| Field | Value |
|-------|-------|
| **Decision ID** | `D12` (PMO) / Phase 4 Enforce |
| **Checkpoint** | `HC-14` |
| **Closes** | `OI-GOV-05` (wiring decision); advances `CR-012` from MITIGATED → CLOSED once merged |
| **Outcome** | **Accepted** |
| **Effective** | Upon merge of the Phase-4 CI commit to `main` |

## What is enforced

Workflow: `.github/workflows/backend-ci.yml` job name **`aods`**.

Command (baseline-aware — new findings fail; baselined debt does not):

```bash
python3 aods/tools/aods_validate.py
```

Gates covered on every PR/push to `main`: `registry`, `links`, `pmo`, `prompts`, `graph`, `naming`,
`openapi`, `ingestion-boundary`. Contextual gates (`citation`, `allowlist`) remain opt-in at node time.

## Branch protection note

Adding the GitHub Actions job is necessary but not sufficient. A repo admin must add **`aods`** to
required status checks on `main` (alongside `lint` / `test`) to satisfy `OI-GOV-02` mechanically.
Until then the job still runs and fails PRs visibly; it is not yet merge-blocking via branch rules.

**Apply (repo admin):**

```bash
bash scripts/ops_require_aods_status_check.sh
# or UI: https://github.com/Shebahati/Karzar/rules/19696648 → add context `aods`
```

**Update 2026-07-30:** Repo admin applied — Protect main now requires `lint` + `test` + `aods`
(strict). `OI-GOV-02` **CLOSED**. Verify: `bash scripts/ops_require_aods_status_check.sh --check`.

## Non-decisions

This minute originally deferred `OI-GOV-02`; that residual is now closed (see update above).
`CR-011` (staging≈prod) remains open.
