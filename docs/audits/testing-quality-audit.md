# Phase 8 — Testing, Code Quality & Developer Experience Audit

**Date:** 2026-07-25 · **Auditors:** QA Lead, Engineering Manager, Principal Reviewer
**Scope:** Backend test suite (36 files, 242 tests), coverage gates, lint/type tooling, frontend testing, DX/docs.

---

## 1. What is genuinely good (verified)

1. **The backend suite tests the right things.** File census shows dedicated
   suites for security/authz (`test_c_security_authz.py`, `test_p3_security.py`),
   payment flows incl. the Zarinpal provider and URL allowlist
   (`test_f_payment_audit.py`, `test_p0_payment.py`, `test_payment_url_allowlist.py`,
   `test_zarinpal_provider.py`), rate limiting (incl. a Redis-backed variant),
   contract tests (`test_p1_contract.py`, `test_p5_contract.py`), data quality,
   category tree edge cases (depth, delete-reassignment), JSONB filters, and
   even a performance smoke test. This is risk-weighted testing, not
   coverage theater.
2. **Coverage is a hard CI gate:** `--cov-fail-under=62` with `--maxfail=1`,
   plus ruff and mypy as separate gated jobs. Backend quality cannot silently
   regress below the line.
3. **Tooling is modern and consistent:** ruff + mypy (with config files
   path-filtered in CI), TS `strict: true` in both frontends, Pydantic v2 and
   SQLAlchemy 2.0 typed models throughout.
4. **Documentation for developers is unusually rich:** `ARCHITECTURE.md`,
   `API_CONTRACT.md`, `OPERATIONS.md`, `HESABFA.md`, go-live plan, refactor
   maps, plus per-feature frontend contracts.

## 2. Findings

### QA-01 — Frontend testing is absent (1 test file across two apps)
- **Severity:** High · **Category:** Testing · **Location:** `frontend/admin-panel` (1 test), `frontend/Storefront` (0 found)
- **Evidence:** 242 backend tests vs ~1 frontend test, while the frontends contain the checkout UX, cart math display, order state actions, and product editing — the surfaces where this week's regressions actually occurred.
- **Recommendation:** Vitest + Testing Library; first 10 tests: admin api-client refresh, order status actions, product form validation, storefront cart totals, checkout guard rails. Gate in the new frontend CI (OPS-04).
- **Effort:** M · **Priority:** P1

### QA-02 — 62% coverage gate has known dark zones
- **Severity:** Medium · **Category:** Testing depth
- **Evidence:** The gate passes with `app/services/hesabfa/*` partially covered (`test_hesabfa.py` exists but invoice retry/error paths are thin — cross-ref BE-07), and `scripts/` is excluded entirely despite carrying pricing logic (ARCH-02).
- **Recommendation:** Ratchet strategy: +2% per month until 75%; add unit tests for currency conversion/markup helpers when scripts are consolidated.
- **Effort:** ongoing · **Priority:** P2

### QA-03 — No E2E or smoke tests in CI for the user journey
- **Severity:** Medium · **Category:** Testing strategy
- **Evidence:** `smoke-staging.sh` exists but is manual/deploy-side; no Playwright/E2E covering: browse → add to cart → checkout (mock pay) → tracking. Backend contract tests approximate but don't exercise the real frontends.
- **Recommendation:** One Playwright spec for the golden path against the compose stack (mock payment provider makes this feasible in CI); run nightly, not per-PR, to keep CI fast.
- **Effort:** M · **Priority:** P2

### QA-04 — Test naming reveals accretion, not architecture
- **Severity:** Low · **Category:** Maintainability
- **Evidence:** `test_p0…p5_*` phase-numbered files coexist with domain-named ones (`test_orders.py`, `test_payments.py`); a newcomer cannot tell where a new payment test belongs.
- **Recommendation:** Fold phase-named files into domain modules opportunistically (no big-bang rename); adopt `tests/{domain}/` folders when files exceed ~40.
- **Effort:** S (policy) · **Priority:** P3

### QA-05 — mypy/ruff scope excludes `scripts/`
- **Severity:** Low · **Location:** CI runs `ruff check app tests` and `mypy app`
- **Evidence:** The 35-script folder with business logic is unlinted and untyped in CI.
- **Recommendation:** Add `ruff check scripts` (fix findings once), keep mypy exclusion until scripts consolidation.
- **Effort:** S · **Priority:** P3

## 3. Self-challenge

- Is 242 tests "a lot" or "a little"? For ~12k lines of backend application code with a 62% enforced floor, it is genuinely respectable — the criticism belongs on the frontend side, not the backend.
- Verified the coverage number is enforced (CI flag), not aspirational.
- Did not run the suite in this pass (avoids ~4-minute local run while auditing); recent CI history shows it green on main as of this week's merges.

## 4. Scores

| Category | Score | Justification |
|---|---|---|
| Backend testing | **7.5/10** | Risk-weighted suites + enforced coverage floor; Hesabfa/error-path thinness. |
| Frontend testing | **1.5/10** | Effectively none. |
| E2E/journey coverage | **3/10** | Manual smoke script only. |
| Code quality tooling | **8/10** | ruff/mypy/strict-TS all enforced where configured. |
| Developer experience | **7.5/10** | Docs are a real asset; venv sprawl and scripts folder drag. |
| Testing & quality overall | **6/10** | A strong backend culture that has not yet crossed the frontend boundary. |
