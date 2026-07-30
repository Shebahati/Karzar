# Task record — GOV-2026-07-30-cr005-tx-ownership

| Field | Value |
|-------|-------|
| **NODE_ID** | GOV-2026-07-30-cr005-tx-ownership |
| **PROMPT** | aods/70-prompts/gov/GOV-pmo-sync.prompt.md (+ checkout slice IMPL) |
| **TASK_ID** | NONE — CR-008 |
| **CHANGE_CLASS** | C5 + C3 (behaviour-preserving commit hoist) |
| **ARCHETYPE** | GOV / IMPL |
| **STATUS** | COMPLETE — CR-005 CLOSED Option A (first slice) |
| **Date** | 2026-07-30 |
| **HC** | HC-03 Option A |

## Goal

Close conflict CR-005 under Option A; land first BE-01 slice for `checkout_service`
(submit_checkout already flush-only; hoist submit_contact commit to endpoint); **D20**.

## Files changed

1. `app/services/checkout_service.py` — `submit_contact` → `flush`
2. `app/api/endpoints/storefront_content.py` — `contact_us` owns `commit`
3. `docs/ARCHITECTURE.md` — remediation progress note
4. `aods/10-repository-intelligence/CONFLICT-REGISTER.md`
5. `project-management/DECISIONS.md` (**D20**)
6. `project-management/CHANGELOG.md`
7. `project-management/DONE.md`
8. `aods/reports/tasks/GOV-2026-07-30-cr005-tx-ownership.md`

## Residual

otp/cart/product/brand/category/idempotency/hesabfa service commits — separate IMPL nodes.

## Verify

```text
AODS validation — 8 gate(s), base=origin/main
  PASS  registry / links / pmo / prompts / graph / naming / ingestion-boundary
  SKIP  openapi — ModuleNotFoundError: No module named 'fastapi'
RESULT: PASS — 0 new findings, 0 baselined
EXIT:0

pytest (local): blocked — same missing fastapi in env; rely on CI lint/test on PR.
Contact tests exist: tests/test_storefront.py, test_g_content_audit.py, test_p3_security.py
```
