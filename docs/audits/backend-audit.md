# Phase 3 — Backend API & Business Logic Audit

**Date:** 2026-07-25 · **Auditors:** Staff Backend Engineer, Performance Engineer, Principal Reviewer
**Scope:** Endpoints (20 modules), services (18 + Hesabfa package), CRUD layer, error handling, validation, concurrency, integrations (payments, OTP/SMS, Hesabfa), rate limiting.
**Method:** Full read of `core/security.py`, `checkout_service.py`, `payment_flow_service.py`, `endpoints/payment.py`, `stock_ledger_service.py`, `core/rate_limit.py`, `jsonb_filters.py`, `deps.py`; structured skims of `auth.py`, Hesabfa client, constants.

---

## 1. What is genuinely good (verified)

1. **The payment path is the strongest code in the repo.** `POST /payments/init`
   implements real idempotency (reserve → execute → finalize, with 409 on
   concurrent same-key and cleanup on failure), row-locks the order
   (`get_order_by_id_for_update`), rate-limits per user, validates the outgoing
   gateway URL against an allowlist (`assert_allowed_payment_url`), and records
   every transition into an append-only `payment_transactions` ledger with IP.
   Verify is capability-based (authority token), re-entrant (already-paid
   short-circuit), and ownership-checked when a user is bound.
2. **Oversell is structurally prevented** — checkout takes `SELECT … FOR UPDATE`
   on all referenced products (`checkout_service.py:65`), merges duplicate
   lines before validation, blocks unpriced/unavailable SKUs in purchase lane
   with a Persian-clear error, and computes totals in `Decimal` with explicit
   tax handling.
3. **Auth machinery is layered correctly**: short-lived access JWT with
   `token_version` revocation, opaque refresh tokens stored hashed with
   rotation, OTP hashed at rest, step-up PIN → single-use `jti` persisted in
   DB, per-key failure rate limiting with success-clear semantics.
4. **Rate limiting fails closed** — on Redis outage `RedisRateLimiter` throttles
   for the full window rather than silently allowing brute force
   (`rate_limit.py:109–111`). A deliberate, documented security-over-availability
   trade-off.
5. **Error surface is uniform**: one envelope (`error_code/message/details`),
   normalized in global handlers; no stack traces to clients.
6. **The binary-availability pivot was implemented coherently**: stock ledger is
   append-only bookkeeping (`stock_ledger_service.py` never mutates
   `products.stock_quantity`), so purchases work with zero site stock — we
   specifically checked this failure hypothesis and it does not occur.

## 2. Findings

### BE-01 — Transaction boundaries are owned by nobody
- **Severity:** High · **Category:** Correctness/Maintainability · **Location:** repo-wide; counts: `endpoints/payment.py` 8 commits, `endpoints/cms.py` 8, `services/product_service.py` 7, `services/checkout_service.py:180`, `services/cart_service.py` 4, `services/category_service.py` 4 …
- **Evidence:** `await db.commit()` appears in both endpoint handlers **and** inside services. `submit_checkout` does not commit (caller does), while its sibling `submit_contact` commits internally — two functions in the same file with opposite contracts.
- **Why problematic:** Any composition of two services risks partial commits: if service A commits mid-flow and step B fails, the request returns 5xx with half the work persisted. This is exactly how ghost orders/duplicated side effects are born under load. It also blocks unit-of-work testing.
- **Root cause:** No stated convention; each feature chose locally.
- **Risk:** Data inconsistency under failure; hard-to-reproduce bugs. **Business impact:** order/payment anomalies erode trust precisely where the code is otherwise strongest.
- **Recommendation:** Adopt "endpoints own transactions" (or a UoW dependency that commits on success/rolls back on exception), migrate services to flush-only, enforce with a lint rule (`ruff` ban `db.commit` under `app/services/`).
- **Alternative:** Formalize the current split by documenting which services are transactional entrypoints — weaker but cheap.
- **Effort:** M · **Priority:** P1

### BE-02 — Payment callback commits on unknown exceptions
- **Severity:** Medium · **Category:** Correctness · **Location:** `endpoints/payment.py:281–286`
- **Evidence:** `except Exception: await db.commit(); return RedirectResponse(failure…)`.
- **Why problematic:** Committing after an *expected* verify failure persists the failed-payment ledger (intended). But a bare `Exception` also catches programming errors and infra failures, committing whatever partial state the session holds and masking the bug behind a clean redirect (no log either — the exception is swallowed silently).
- **Recommendation:** Catch the specific payment exceptions for the commit-and-redirect path; for unexpected exceptions, `rollback()`, log with `logger.exception`, then redirect to failure.
- **Effort:** S · **Priority:** P1

### BE-03 — `verify_order_payment` marks FAILED on gateway timeouts
- **Severity:** Medium · **Category:** Business logic · **Location:** `payment_flow_service.py:137–146`
- **Evidence:** On `PaymentGatewayTimeoutError` the order's `payment_status` is set to `failed` and a failure ledger row is written, then the exception re-raised.
- **Why problematic:** A timeout is *unknown outcome*, not failure. Zarinpal may have actually captured the payment; the user retries verify, and the guard `order.status != PENDING_PAYMENT` (line 127) still passes (status unchanged) so re-verify works — but `payment_status=failed` is now recorded and shown to admin/customer until a retry succeeds. Reconciliation reports will overcount failures.
- **Recommendation:** Introduce a distinct `unknown`/`pending_verify` transaction status for timeouts; only mark `failed` on explicit gateway rejection. Keep retry allowed.
- **Effort:** S–M · **Priority:** P2

### BE-04 — JWT hygiene gaps (shared secret, no issuer/audience, HS256 only)
- **Severity:** Medium · **Category:** Security-adjacent (full treatment in Phase 4) · **Location:** `core/security.py:32–89`
- **Evidence:** Access and step-up tokens signed with the same `SECRET_KEY`, no `iss`/`aud` claims, algorithm fixed HS256; `decode_token` raises HTTP exceptions from the core layer (layering leak). bcrypt silently truncates passwords >72 bytes (no length guard at schema level — verified `UserCreate` has no max_length gate on password ≤72).
- **Why problematic:** Step-up/access separation relies solely on the `type` claim — correct today because both verifiers check `type`, but one forgotten check reopens privilege confusion. No `aud` means any future second service sharing the secret accepts these tokens.
- **Recommendation:** Add `iss`/`aud` claims + verification now (cheap); cap password length at 72 in schema; move HTTP-error raising out of `core.security` into the dependency layer.
- **Effort:** S · **Priority:** P2

### BE-05 — Spec-filter values are unbounded user input into ILIKE
- **Severity:** Low · **Category:** Robustness · **Location:** `utils/jsonb_filters.py:82`
- **Evidence:** `accessor.astext.ilike(f"%{value}%")` — parameterized (no injection), but `%`/`_` wildcards in user values are **not** escaped here (unlike the catalog search path which uses `escape_ilike_pattern`), and there is no length cap on filter values or number of filter keys.
- **Why problematic:** Inconsistent escaping policy; a crafted long filter list amplifies the already-sequential JSONB scan (cheap DoS vector combined with DB-03 from the database audit; PLP throttle of 120/min bounds it somewhat).
- **Recommendation:** Reuse `escape_ilike_pattern`, cap filter count (e.g. 8) and value length (e.g. 64).
- **Effort:** S · **Priority:** P2

### BE-06 — Public registration toggle hides a dead code path, PIN is a shared secret
- **Severity:** Low/Medium · **Category:** AuthN design · **Location:** `endpoints/auth.py:110–131`, `core/security.py:118–123`
- **Evidence:** `/auth/register` exists but returns 403 unless `ALLOW_PUBLIC_REGISTER=true` (currently false → customers are created via OTP login flow). `ADMIN_STEP_UP_PIN` is a single shared PIN for all super-admins, compared timing-safe but stored plaintext in env, unrotatable per person.
- **Why problematic:** Shared PIN = no attribution (any super-admin action authorized by the same secret; two admins now exist), and revocation requires coordinated rotation.
- **Recommendation:** Per-admin PIN (hashed column on `users`) or TOTP for step-up; keep the env PIN only as break-glass.
- **Effort:** M · **Priority:** P2

### BE-07 — Hesabfa client duplicates settings resolution and lacks retry/backoff
- **Severity:** Low · **Category:** Integration robustness · **Location:** `services/hesabfa/client.py`
- **Evidence:** Thin httpx wrapper with timeout but no retry/backoff or circuit breaker; invoice push is "best-effort, never fails payment" (`payment_flow_service.py:161–162` — correct), but a transient Hesabfa outage silently drops invoices with only an `hesabfa_invoice_records.status` row.
- **Why problematic:** There is no retry mechanism that later re-pushes `status='pending'/'error'` invoice records — reconciliation is manual.
- **Recommendation:** Add a periodic re-push job for failed invoice records (fits the job-runner extraction, ARCH-01) + admin visibility of failed pushes.
- **Effort:** M · **Priority:** P2

### BE-08 — In-memory rate limiter fallback is multi-worker-unsafe by design
- **Severity:** Low (documented) · **Category:** Security ops · **Location:** `core/rate_limit.py:39–69`, guarded by config validator (Redis mandatory when `DEBUG=False`)
- **Evidence:** Per-process deque counters; config forbids running without Redis in hardened mode, so the hole is closed in production. Retained as a finding because a future config loosening silently reopens it.
- **Recommendation:** Log a prominent startup warning when the in-memory limiter is active outside tests.
- **Effort:** S · **Priority:** P3

### BE-09 — `DEFAULT_TAX_PERCENT = 9` vs model default `0`
- **Severity:** Low · **Category:** Consistency · **Location:** `core/constants.py` vs `db/models/product.py:170–172`
- **Evidence:** Constant declares Iran VAT 9% as default for new products; the ORM column defaults to `0`. Which one applies depends on the creation path (schema default vs model default vs import scripts).
- **Why problematic:** Checkout adds `line_total * tax_percent/100` — silently divergent tax treatment across products created via different paths misprices orders.
- **Recommendation:** Pick one default, enforce in the Pydantic create-schema, audit current distribution of `tax_percent` values in the live DB.
- **Effort:** S · **Priority:** P2

### BE-10 — Best-effort inline sweeps inside request handlers
- **Severity:** Low · **Category:** Performance · **Location:** `checkout_service.py:59–60`, `endpoints/payment.py:191`
- **Evidence:** `cancel_expired_pending_payment_orders(db)` runs inline during checkout and payment-init, in addition to the background worker.
- **Why problematic:** Adds latency and lock contention to the hottest user-facing flows; redundancy with the worker is harmless but the cost lands on user requests.
- **Recommendation:** Keep the worker as the owner; inline call can be scoped to *this order's* expiry only (or removed once worker health is monitored).
- **Effort:** S · **Priority:** P3

## 3. Self-challenge

- Tried to break checkout oversell with duplicate lines → `_merge_quantities` handles it; FOR UPDATE covers TOCTOU.
- Tried the "purchases fail at zero stock after availability pivot" hypothesis → disproved (ledger never mutates quantity; CHECK constraint untouched).
- Verified idempotency reservation actually commits before gateway call (yes — `db.commit()` at `payment.py:189`), so a crashed request leaves a reserved key that expires by TTL; acceptable, worst case = client retries with new key.
- Checked whether `payment_verify` allows cross-user probing: authority is unguessable gateway-issued, 404 on unknown; rate-limited per order. Acceptable.
- Unverified areas (flagged for later phases): SSRF guard implementation in `image_validation.py`, admin `users.py` mass-assignment surface, OTP resend cadence.

## 4. Scores

| Category | Score | Justification |
|---|---|---|
| API design & contracts | **7.5/10** | Uniform envelope, versioned prefix, OpenAPI accuracy fixes; some REST inconsistencies (query-param stock adjust). |
| Business logic correctness | **7/10** | Payment/checkout unusually rigorous; timeout-as-failure and tax-default divergence deduct. |
| Validation & input handling | **7/10** | Pydantic v2 everywhere, escaped search; spec-filter escaping/caps missing. |
| Concurrency & transactions | **6/10** | Row locks and idempotency excellent; commit-ownership anarchy is the systemic risk. |
| Integrations | **7/10** | Provider abstraction (mock/Zarinpal), fail-closed limits; missing retry/re-push for Hesabfa. |
| Backend overall | **7/10** | Production-grade core flows with a short list of sharp, fixable edges. |
