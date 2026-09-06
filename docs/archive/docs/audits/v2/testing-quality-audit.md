# Phase — Testing, Code Quality & Developer Experience Audit (v2, strict)

**Date:** 2026-07-25 · **Auditors:** QA Lead / EM / Principal Reviewer (hostile due-diligence)
**Baseline:** v1 `docs/audits/testing-quality-audit.md` (overall 6.0; FE testing 1.5)
**Branch:** `docs/engineering-audit-2026-07` @ `66e9ae9`
**Method:** Backend test census (`tests/test_*.py`, `def test_` count), `pytest.ini` / `pyproject.toml` coverage+ruff+mypy, `docs/TESTING.md` vs tree, frontend Vitest+Playwright (committed, excl. `node_modules`), package.json scripts, CI gating cross-check with devops phase.

---

## 1. What is genuinely good (re-verified)

1. **Backend suite is risk-weighted:** authz, payments/Zarinpal/allowlist, rate limit (+ Redis), contracts, catalog/JSONB, Hesabfa basics, performance smoke — **33** files / **242** `test_*` functions (v1 said 36 files — off by 3).
2. **Hard coverage gate:** CI `--cov-fail-under=62`; `pyproject.toml` `[tool.coverage] fail_under = 62`.
3. **Frontend tooling now exists (v1 missed this):**
   - Storefront: `vitest.config.ts`, **8** `__tests__` files / **38** cases, `e2e/checkout-smoke.spec.ts`, `playwright.config.ts`
   - Admin: `vitest.config.ts`, **1** `__tests__` file / **5** cases, `e2e/admin-smoke.spec.ts`, `playwright.config.ts`
4. **TS `strict: true`** in both apps.
5. **Docs breadth** remains strong (`ARCHITECTURE`, `API_CONTRACT`, `OPERATIONS`, `HESABFA`, etc.) — accuracy graded in documentation phase.

### Frontend unit paths (Storefront)
`src/lib/__tests__/{validation,pending-payment,payment-url,feature-labels,idempotency}.test.ts`, `src/components/catalog/__tests__/catalog-params.test.ts`, `src/config/__tests__/nav-groups.test.ts`, `src/store/__tests__/cart-store.test.ts`.

### Admin unit path
`src/lib/__tests__/sanitize-next-path.test.ts` only.

---

## 2. Critique of the v1 report

| Issue | Verdict |
|---|---|
| “0 Storefront tests / 1 admin test” | **False.** 38+5 unit cases + 2 e2e specs tracked. |
| “No E2E” | **False for repo contents**; **true for CI/automation**. |
| “36 backend test files” | **Wrong** — 33 `tests/test_*.py`. |
| Overall 6.0 / FE 1.5 | FE score too low given foundation; overall still too high once ungated FE + TESTING.md staleness + toothless mypy priced. |
| DX 7.5 | Docs volume ≠ accuracy; TESTING.md lists nonexistent file. |

---

## 3. Findings register

### Re-verified / revised v1 findings

#### QA-01 — Frontend tests exist but are shallow and not CI-gated *(revised)*
- **Severity:** Medium–High · **Category:** Testing · **Location:** Storefront/admin Vitest + Playwright; **no** workflow runs them
- **Evidence:** v1 “absent” is false. Reality: 38+5 unit cases, mostly pure lib/store helpers. No admin api-client refresh, product form, or order-status action tests. Checkout e2e is mock-mode only (`playwright.config.ts` forces `NEXT_PUBLIC_USE_MOCK=true`).
- **Why / Impact:** Write-path UI regressions still reach live; foundation without enforcement is theater for branch protection.
- **Recommended:** Gate `npm test` + `lint` + `tsc --noEmit` in FE CI (OPS-04/25). Add Testing Library for checkout rails, admin order actions, api-client refresh. Keep Playwright nightly. **Effort:** M · **Priority:** **P1**.

#### QA-02 — 62% coverage gate with dark zones (hesabfa, scripts/)
- **Severity:** Medium · **Category:** Testing depth · **Location:** `pyproject.toml:16–18` `source = ["app"]` omits `scripts/`; `tests/test_hesabfa.py` thin vs `app/services/hesabfa/*` ≈1.1k LOC
- **Evidence:** Pricing logic in `scripts/reconcile_prices_availability.py` (rial÷10, markup CSVs) has **zero** test imports. Hesabfa happy-path covered; retry/error paths thin (cross-ref BE-07).
- **Recommended:** Ratchet +2%/month to 75%; unit-test extracted pricing helpers; expand Hesabfa failure/retry. **Effort:** ongoing · **Priority:** P2.

#### QA-03 — E2E exists locally but not in CI; no live-journey gate *(revised)*
- **Severity:** Medium · **Category:** Testing strategy · **Location:** Storefront/admin e2e specs; `smoke-staging.sh` (shell, not CI — see OPS-20)
- **Evidence:** Mock Playwright ≠ production payment path; workflows never call Playwright or full smoke script.
- **Recommended:** Nightly Playwright on mock; post-deploy hard smoke against live; optional compose golden path later. **Effort:** M · **Priority:** P2.

#### QA-04 — Test naming reveals accretion
- **Severity:** Low · **Category:** Maintainability · **Location:** `tests/test_p0_*`…`test_p5_*` alongside domain-named files
- **Recommended:** Fold opportunistically into domain modules / `tests/{domain}/`. **Effort:** S · **Priority:** P3.

#### QA-05 — mypy/ruff scope excludes `scripts/`
- **Severity:** Low · **Category:** Tooling scope · **Location:** `backend-ci.yml:77,81`; `pyproject.toml:28` `src = ["app", "tests"]`
- **Evidence:** 29 script modules with business logic unlinted/untyped in CI.
- **Recommended:** `ruff check scripts` after cleanup; defer mypy until consolidation. **Effort:** S · **Priority:** P3.

---

### New findings (v2)

#### QA-20 — `docs/TESTING.md` claims vs reality
- **Severity:** Medium · **Category:** Documentation / DX · **Location:** `docs/TESTING.md:38–45`
- **Evidence:** Lists `test_p5_e2e_checkout.py` — **file does not exist**. Guide omits frontend Vitest/Playwright entirely. Pre-commit config exists but is not enforced in GHA.
- **Why / Impact:** Newcomers chase ghosts; FE test commands undocumented in the testing SoT.
- **Recommended:** Fix table; add FE testing section; note CI does not run pre-commit or FE tests. **Effort:** S · **Priority:** P2.

#### QA-21 — No `typecheck` script; FE type safety only via `next build`
- **Severity:** Medium · **Category:** Code quality tooling · **Location:** Storefront/admin `package.json` scripts — no `typecheck` / `tsc --noEmit`
- **Evidence:** `strict: true` helps only when `tsc`/`next build` runs; PR CI never runs either for FE.
- **Recommended:** Add `"typecheck": "tsc --noEmit"`; gate in FE CI before deploy. **Effort:** S · **Priority:** **P1**.

#### QA-22 — mypy configured to ignore many real error classes
- **Severity:** Medium · **Category:** Type quality · **Location:** `pyproject.toml:41–50`
- **Evidence:** `disable_error_code` includes `arg-type`, `union-attr`, `assignment`, `call-arg`, etc.; `disallow_untyped_defs = false`. CI “mypy app” is a weak gate.
- **Recommended:** Remove disables incrementally; start with new modules `disallow_untyped_defs`. **Effort:** M · **Priority:** P2.

#### QA-23 — Admin panel unit coverage is a single sanitizer file
- **Severity:** Medium · **Category:** Frontend testing depth · **Location:** Only `sanitize-next-path.test.ts` (5 cases)
- **Evidence:** High-risk admin surfaces (session/refresh, product form, order status, step-up) untested at unit level; one e2e covers a thin path.
- **Recommended:** Priority tests: api-client refresh, product form validation, order status transitions, step-up PIN flows. **Effort:** M · **Priority:** **P1**.

#### QA-24 — Backend CI path-filter skips Python work on FE-only PRs without substituting FE tests
- **Severity:** Medium · **Category:** CI strategy · **Location:** `backend-ci.yml:58–61,115–118`
- **Evidence:** Skip lint/test when `backend != true`, printing success for required checks. By design for branch protection names — means FE-only merges can be all-green with **zero** automated test execution.
- **Recommended:** Separate required `frontend-lint` / `frontend-test` jobs; do not pretend backend skip equals quality. **Effort:** S · **Priority:** **P1**.

#### QA-25 — Coverage omit of `app/main.py` hides worker/lifespan risk
- **Severity:** Low · **Category:** Coverage dark zone · **Location:** `pyproject.toml:18` `omit = ["app/main.py"]`; order-expiry worker `main.py:32–68`
- **Evidence:** Background sweep failures only logged; no dedicated unit test of worker loop/lock interaction in main module.
- **Recommended:** Extract worker to testable module; or stop omitting main and test lifespan hooks. **Effort:** S · **Priority:** P3.

#### QA-26 — Backend money-path concurrency gaps untested (cross-ref BE-20/21/22)
- **Severity:** High · **Category:** Testing depth / correctness · **Location:** payment refund/callback/expiry suites
- **Evidence:** Backend audit found refund-after-fulfillment rollback (BE-20), expiry lost-update (BE-21), unlocked callback (BE-22). Existing payment tests cover happy paths and allowlists but not these failure modes under concurrency.
- **Why / Impact:** Flagship money path can regress without CI signal — the suite looks strong while missing the highest-severity defects.
- **Recommended:** Add regression tests for shipped→refund, concurrent verify+sweep, dual callback; make them required for coverage culture to be credible. **Effort:** M · **Priority:** **P0** (before gateway live) · **Dependencies:** BE-20/21/22 fixes.

---

## 4. Doc-drift table

| Doc | Claim | Reality | Verdict |
|---|---|---|---|
| `TESTING.md` layout table | Includes `test_p5_e2e_checkout.py` | File absent | **Drift** |
| `TESTING.md` | 62% gate, markers, Postgres/Redis CI | Matches `backend-ci.yml` | Accurate |
| `TESTING.md` | FE testing | Omitted entirely | Incomplete |
| `BACKEND_CHANGES.md:96` | “160 passed” | 242 collected | Stale |
| `API_CHANGELOG` | “160+ tests” historical | Acceptable as era note | OK |
| v1 QA-01 | 0 storefront / 1 admin | 38+5 + e2e | **v1 wrong** |

---

## 5. Scores (0–10, strict)

| Category | v1 | v2 | Delta justification |
|---|---|---|---|
| Backend testing | 7.5 | **6.5** | −1.0. Suite volume/risk-weighting real, but missing concurrency/refund regressions for P0 money-path bugs (QA-26) means the floor is less trustworthy than v1 claimed. Hesabfa/scripts/worker dark zones remain. |
| Frontend testing | 1.5 | **3.5** | +2.0. Vitest+Playwright present (v1 missed); shallow; admin nearly empty; not in CI. |
| E2E/journey coverage | 3.0 | **4.0** | +1.0. Mock Playwright specs exist; live smoke ungated. |
| Code quality tooling | 8.0 | **6.5** | −1.5. ruff/mypy/strict-TS present but mypy toothless; no FE typecheck script; scripts unscanned. |
| Developer experience | 7.5 | **6.5** | −1.0. Docs rich but TESTING.md wrong; FE commands undocumented in testing SoT. |
| **Testing & quality overall** | **6.0** | **5.5** | **−0.5**. Backend culture intact; FE foundation arrived without CI enforcement; money-path test gaps are the strict-mode deduction. |

---

## 6. Self-review

- 242 backend tests for this codebase size remains respectable; criticism shifted from “no FE tests” to “FE tests ungated + shallow” **and** “money-path concurrency untested.”
- Census is file/AST-based on committed tree; full pytest/vitest not re-executed this pass (consistent with v1 approach).
- Confirmed frontend test files are on the repo tree, not merely local dirty state.
- `test_p5_e2e_checkout.py` absence confirmed — TESTING.md is stale.
- QA-26 severity High is justified by BE-20 P0 status — a suite that doesn't catch double-refund risk cannot score 7.5 under acquisition bar.
