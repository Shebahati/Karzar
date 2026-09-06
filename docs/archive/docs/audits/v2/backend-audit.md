# Phase — Backend API & Business Logic Audit (v2, strict)

**Date:** 2026-07-25 · **Auditors:** Staff Backend Engineer team (hostile due-diligence mode)
**Baseline:** v1 report `docs/audits/backend-audit.md` (same date, pre-strict pass)
**Branch:** `docs/engineering-audit-2026-07` @ `66e9ae9` (post `chore/clear-hesabfa-admin-reads` merge, PR #55)

---

## 1. Scope & method

Read in full: `app/main.py`, `app/core/{config,security,rate_limit,request_throttle,security_middleware,distributed_lock,startup}.py`, `app/api/deps.py`, all 19 endpoint modules under `app/api/endpoints/`, `app/services/{payment_flow_service,payment_service,checkout_service,cart_service,order_service,order_expiry_service,otp_service,auth_token_service,sms_service,notification_service,product_service,product_review_service,stock_ledger_service}.py`, `app/services/hesabfa/{client,invoices}.py` (others skimmed), `app/crud/{commerce,idempotency,refresh_tokens,otp,platform}.py` (product/content skimmed), `app/utils/{jsonb_filters,file_storage,image_validation,otp_hash,tracking_code}.py`.

Static analysis only (grep, `git log`, `pytest --collect-only` → **242 tests collected**; server not run). Every commit site quantified (`rg 'db\.commit\(\)'` → **73 call sites**). Route table extracted from `app/api/v1/__init__.py:21–31` + endpoint decorators (**95 v1 routes in code**) and diffed against `openapi/v1.json` (**87 routes; last regenerated 2026-07-18 @ `335a1cb`, endpoints last changed 2026-07-25**).

Not verifiable offline: live Zarinpal refund API contract (BE-31), live DB `tax_percent` distribution (BE-09 remediation input), Redis/production env values.

---

## 2. v1 critique

**All ten v1 findings (BE-01…BE-10) re-verified and still present — none fixed.** Current locations cited in §4. v1's factual claims held up almost everywhere; specific corrections:

1. **BE-04 imprecision.** v1 claimed "`UserCreate` has no max_length gate on password ≤72". In fact `password: Field(..., min_length=8, max_length=128)` exists (`app/schemas/auth.py:81`). The substantive point stands (128 > 72, so bcrypt still silently truncates 73–128-char passwords), but the evidence as written was wrong.
2. **v1 was too generous about the payment path** ("the strongest code in the repo", refund described as working). Strict review found a **High-severity refund state-machine bug** (BE-20): refunding a shipped/delivered order performs the gateway refund and then crashes on an illegal `→cancelled` transition, rolling back the DB after money moved. v1's own self-challenge tested callback/verify but never exercised refund against non-PAID *order statuses*.
3. **v1 missed three concurrency defects** in the flows it praised: the expiry-sweep lost-update race (BE-21), the unlocked callback verify path (BE-22), and gateway/Hesabfa HTTP calls executed while holding row locks (BE-24).
4. **v1 missed the single biggest latency hazard**: bcrypt running synchronously on the event loop (BE-23) — despite explicitly discussing bcrypt truncation in BE-04.
5. **v1's "no retry mechanism" (BE-07) understated the config trap**: `HESABFA_TEST_MODE` defaults to `true` (`config.py:73`) and no validator forces it off in production, so invoices are silently skipped until someone remembers a flag (documented in HESABFA.md step 7, but unenforced).
6. v1 scores: Backend 7.0 and Performance 6.0 were **modestly generous**; with a High correctness bug in the flagship flow and systemic loop-blocking, v2 re-scores below (§6).

What v1 got right and we confirm: oversell prevention via `FOR UPDATE` + line merging (`checkout_service.py:62–65`), payment-init idempotency reserve/finalize (`payment.py:165–189, 234–243`; `crud/idempotency.py:50–70`), fail-closed rate limiting (`rate_limit.py:109–111`), uniform error envelope (`main.py:233–257`), ledger never mutating `stock_quantity` (`stock_ledger_service.py` — append-only).

---

## 3. Route inventory summary

95 routes under `/api/v1` (+ 4 system routes `/`, `/api/v1`, `/health`, `/ready`; `/metrics` conditional). Registration: `app/api/v1/__init__.py:21–31`, `app/main.py:110`.

| Group (prefix) | Routes | Auth level |
|---|---|---|
| `/auth` (11) | register, login, me, change-password, refresh, logout, password-reset ×2, verify-pin, otp ×2 | Public (register 403-gated by `ALLOW_PUBLIC_REGISTER`); me/change-password/logout = user; verify-pin = super_admin |
| `/products` catalog (5) | list, statistics, sku/{sku}, {id}, {id}/related | Public w/ optional JWT; **statistics = super_admin** |
| `/products` admin (9) | create, update, delete, restore, stock get, availability PUT, stock/adjust (deprecated), bulk/stock-adjust, change-log | super_admin; delete/restore + step-up |
| `/products` images (4) | add (URL or multipart), delete, set-primary, reorder | super_admin |
| `/products` reviews (2) | list comments (public), create comment | create = authenticated user |
| `/categories` (10) | list, tree, slug, spec-labels, spec-filter-options, spec-templates, create, update, image upload, delete | Reads public; writes super_admin; delete + step-up |
| `/brands` (6) | list, slug, create, update, logo upload, delete | Reads public; writes super_admin; delete + step-up |
| `/cart` (5) | get, upsert item, delete item, clear, merge | Optional JWT or `X-Cart-Token` (≥32 chars); merge = authenticated |
| `/orders` (7) | me, track/{code}, admin list, admin detail, status PATCH, quote, archive | me = user; track = public (IP-throttled); rest super_admin; cancel-status + step-up; archive + step-up |
| `/payments` (4) | init, callback GET, verify, refund | init = authenticated owner (optional-JWT with in-handler 401); callback/verify = public capability (authority) + per-order throttle; refund = super_admin + step-up |
| storefront (8) | checkout, contact, blog ×2, articles ×2, hero-slides, nav-groups | Public; checkout/contact IP-throttled |
| `/cms` (14) | articles CRUD, hero-slides CRUD, product-comments list/delete, nav-groups GET/PUT, contact-submissions | super_admin; deletes + step-up |
| `/users` (5) | list, audit-logs, get, patch, delete | super_admin; patch/delete + step-up |
| `/hesabfa` (5) | status, mappings/sync, items/push, stock/sync (deprecated no-op), sales-summary | super_admin |

**No route was found missing auth it plainly needs.** Public surface is deliberate (catalog, tracking, callback-by-capability, checkout). Weakest public spots: order-ID enumeration via `payments/init` response-code oracle (BE-30) and unthrottled-per-IP OTP request (BE-26).

---

## 4. Findings register

### Re-verified v1 findings (unchanged unless noted)

#### BE-01 — Transaction boundaries are owned by nobody *(still open)*
- **Severity:** High · **Category:** Correctness/Maintainability · **Location:** repo-wide, 73 `db.commit()` sites: endpoints ≈40 (`payment.py` 8, `cms.py` 8, `products_images.py` 5, `order.py` 5, `checkout.py` 5, `auth.py` 5, `users.py` 2, `products_reviews.py` 1, `hesabfa.py` 1) and services ≈26 (`product_service.py` 7, `otp_service.py` 4, `category_service.py` 4, `cart_service.py` 4, `brand_service.py` 4, `checkout_service.py:180`, `idempotency_service.py` 1, `hesabfa/item_push.py` 1), plus `core/startup.py` 2, `main.py` 1.
- **Evidence:** `submit_checkout` ends with `await db.flush()` (`checkout_service.py:156`, caller commits at `checkout.py:132`) while sibling `submit_contact` commits internally (`checkout_service.py:180`). `product_service.create_product_with_validation` commits **twice** mid-function (`product_service.py:34,41`).
- **Why problematic / Risk / Impact:** unchanged from v1 — composed services produce partial commits under failure; the double-commit in product create means a Hesabfa push failure leaves the product committed but the change-log/mapping half-applied. Blocks unit-of-work testing. **Business impact:** ghost/partial records in exactly the admin+commerce flows the two-person team debugs by hand.
- **Root cause:** no stated convention. **Recommendation:** endpoints own transactions; services flush-only; enforce with ruff ban on `db.commit` under `app/services/`. **Alternative:** document transactional-entrypoint services. **Effort:** M · **Priority:** P1 · **Dependencies:** none.

#### BE-02 — Payment callback commits on unknown exceptions and swallows them *(still open, verbatim)*
- **Severity:** Medium (raised toward High in combination with BE-22) · **Category:** Correctness · **Location:** `app/api/endpoints/payment.py:281–286`.
- **Evidence:** `except Exception: await db.commit(); return RedirectResponse(...failure...)` — no logging, no rollback, bare `Exception`.
- **Why problematic:** programming errors and infra failures commit whatever partial state the session holds (e.g. `payment_status=FAILED` set at `payment_flow_service.py:143` before a crash in ledger write) and vanish behind a clean redirect. Root cause: copy of the expected-failure path without narrowing. **Risk:** silent data corruption + zero forensics on the money path. **Recommendation:** catch `(PaymentGatewayError, PaymentVerifyFailedError, ValueError)` for commit-and-redirect; bare `Exception` → `rollback()` + `logger.exception` + redirect. **Effort:** S · **Priority:** P1.

#### BE-03 — Gateway timeout marked FAILED, not UNKNOWN *(still open)*
- **Severity:** Medium · **Category:** Business logic · **Location:** `app/services/payment_flow_service.py:142–146`.
- **Evidence:** `except (PaymentGatewayError, PaymentGatewayTimeoutError, PaymentVerifyFailedError): order.payment_status = FAILED; record_payment_failed(...); raise`.
- Retry still works (status stays `pending_payment`; Zarinpal code 101 accepted as success at `payment_service.py:130`), but reconciliation overcounts failures and admin/customer see "ناموفق" for money that may have been captured. **Recommendation:** distinct `unknown`/`pending_verify` ledger status for timeouts. **Effort:** S–M · **Priority:** P2.

#### BE-04 — JWT hygiene gaps *(still open; v1 evidence corrected)*
- **Severity:** Medium · **Category:** Security-adjacent · **Location:** `app/core/security.py:44–51` (access claims: no `iss`/`aud`), `:69–76` (step-up, same `SECRET_KEY`), `:79–89` (`decode_token` raises HTTP 401 from core layer), `:82` (algorithms pinned to `settings.ALGORITHM` only — good).
- **Correction vs v1:** password IS capped at 128 (`schemas/auth.py:81`) — still above bcrypt's 72-byte truncation, so the truncation issue stands with corrected evidence. Also noted: `deps.py:52` accepts tokens with **no `type` claim** (`payload.get("type") not in (None, "access")`) — any signed claim-less JWT is a valid access token; tighten to require `type == "access"`. **Recommendation:** add `iss`/`aud` + verification, cap password at 72, require explicit `type`, move HTTP raising to deps layer. **Effort:** S · **Priority:** P2.

#### BE-05 — Spec-filter values unescaped and uncapped *(still open, verbatim)*
- **Severity:** Low · **Category:** Robustness · **Location:** `app/utils/jsonb_filters.py:82` (`accessor.astext.ilike(f"%{value}%")`, also sqlite branch `:73`); no filter-count/value-length caps in `merge_spec_filters` (`:138–147`) or `parse_spec_prefixed_params` (`:115–135`).
- Catalog search path escapes correctly (`crud/product.py:199–203` uses `escape_ilike_pattern`) — the inconsistency is confirmed. PLP throttle (`products_catalog.py:107–122`) bounds abuse only when a `search`/`filters`/`spec_` param is present. **Recommendation:** reuse `escape_ilike_pattern`; cap ≤8 filters, ≤64 chars/value. **Effort:** S · **Priority:** P2.

#### BE-06 — Shared step-up PIN; register toggle *(still open)*
- **Severity:** Low/Medium · **Category:** AuthN design · **Location:** `app/api/endpoints/auth.py:110–118` (register 403 gate), `app/core/security.py:118–123` (single env PIN, timing-safe), `config.py:87–92` (6–12 chars, weak-PIN denylist `:188–196`).
- Unchanged: one shared PIN for all super-admins → no attribution, coordinated rotation. **Recommendation:** per-admin hashed PIN or TOTP. **Effort:** M · **Priority:** P2.

#### BE-07 — Hesabfa: no retry/backoff, no re-push job *(still open post-merge)*
- **Severity:** Low→**Medium** (re-scored) · **Category:** Integration robustness · **Location:** `app/services/hesabfa/client.py:66–98` (single attempt, no backoff/circuit breaker; new `httpx.AsyncClient` per call `:72`), `invoices.py:207–214` (failure recorded on `hesabfa_invoice_records`, nothing re-pushes), `main.py:32–52` (only background job is order expiry).
- **Re-scored because:** the deploy plan (HESABFA.md step 7) makes invoice push the *only* bridge to accounting once the gateway is live, and `HESABFA_TEST_MODE=true` default (`config.py:73`) + no production validator means a config oversight silently drops **all** invoices, not just transient failures. **Recommendation:** periodic re-push of `status IN ('pending','failed')` records + admin visibility + validator warning when `HESABFA_ENABLED=true && HESABFA_TEST_MODE=true` in production. **Effort:** M · **Priority:** P2.

#### BE-08 — In-memory rate limiter fallback *(still open; mitigation intact)*
- **Severity:** Low · **Category:** Security ops · **Location:** `app/core/rate_limit.py:39–69`; hardened-mode Redis requirement `config.py:228–232`; fail-closed `rate_limit.py:109–111`.
- v1's recommendation (startup warning when in-memory limiter is active) remains unimplemented. **Effort:** S · **Priority:** P3.

#### BE-09 — Tax default divergence 9 vs 0 *(still open, verbatim)*
- **Severity:** Low–Medium · **Category:** Consistency · **Location:** `app/core/constants.py:7` (`DEFAULT_TAX_PERCENT: int = 9`), `app/schemas/product.py:55–56` (schema default 9), `app/db/models/product.py:170–172` (`default=Decimal("0.0"), server_default="0"`).
- API-created products get 9%; ORM/scripts/SQL-created products get 0%. Checkout prices tax from `product.tax_percent` (`checkout_service.py:93–94`), so orders diverge silently by creation path — with ~5,900 imported products this is live mispricing risk, not theoretical. **Recommendation:** pick one default, enforce in a single place, audit live distribution. **Effort:** S · **Priority:** P2.

#### BE-10 — Inline expiry sweeps in hot paths *(still open)*
- **Severity:** Low · **Category:** Performance · **Location:** `app/services/checkout_service.py:59–60`, `app/api/endpoints/payment.py:191`; background worker `main.py:32–52` with distributed lock (`distributed_lock.py:27–37`, note: **fails open** on Redis error `:35–37`).
- Now compounded by BE-21: more concurrent sweep executions = more chances to hit the lost-update race. **Recommendation:** worker owns expiry; inline call scoped to the current order only. **Effort:** S · **Priority:** P3 (P2 if BE-21 not fixed).

---

### New findings (v2)

#### BE-20 — Refund of a shipped/delivered order: gateway refunds, DB rolls back, retry double-refunds
- **Severity:** **High** · **Category:** Business logic / money-path correctness · **Location:** `app/api/endpoints/payment.py:393–404` + `app/services/order_service.py:44–51` (transition table).
- **Evidence:** refund endpoint, after a **successful** gateway refund, runs:

```397:404:app/api/endpoints/payment.py
        if order.status != OrderStatus.CANCELLED.value:
            await transition_order_status(
                db,
                order,
                OrderStatus.CANCELLED.value,
                actor="admin",
                event_description="سفارش پس از بازپرداخت لغو شد",
            )
```

  `ALLOWED_TRANSITIONS` permits `cancelled` only from `pending_payment`, `paid`, `processing` (`order_service.py:35–47`); from `shipped` only `delivered` is legal, from `delivered` nothing (`:48–51`). `transition_order_status` raises `ValueError` (`:145–146`) which is **not caught** (the surrounding `try` at `payment.py:388–391` only covers the gateway call).
- **Why problematic:** for an order in `shipped`/`delivered` — precisely the states where real-world refunds happen — the gateway refund executes, then the endpoint 500s via the global handler and the session (holding `payment_status=REFUNDED`, ledger row, audit) is rolled back. DB still says `paid`; money already left the gateway. An admin retry passes the `payment_status == PAID` guard (`payment.py:372`) and calls the gateway **again**. Additionally, when the gateway declines (`result.success == False`), the endpoint returns **200** with unchanged state and `refund_id=None` (`payment.py:423–429`) instead of a 4xx/5xx.
- **Root cause:** refund flow was only tested against `paid` orders (see `tests/test_f_payment_audit.py` scope in API_CHANGELOG); state machine has no refund-from-fulfilment path.
- **Risk:** double refund attempts, permanent gateway/DB divergence. **Business impact:** direct money loss / manual reconciliation with Zarinpal; destroyed audit trail for the exact action step-up auth was built to protect. **Technical impact:** unrecoverable state without SQL surgery.
- **Recommendation:** (1) persist `payment_status=REFUNDED` + ledger **before** or independent of the status transition and commit immediately after gateway success; (2) add legal `shipped/delivered → cancelled(refunded)` transitions or a dedicated `refunded` terminal state; (3) map declined refunds to 502 with error envelope. **Alternative:** forbid refunds unless `status in (paid, processing)` — smaller but blocks legitimate refunds. **Effort:** M · **Priority:** **P0** (must fix before gateway goes live) · **Dependencies:** none.

#### BE-21 — Expiry sweep can overwrite a just-paid order with CANCELLED (lost-update race)
- **Severity:** High (low probability, high impact) · **Category:** Concurrency · **Location:** `app/services/order_expiry_service.py:29–40` (select without `FOR UPDATE`/`SKIP LOCKED`), `order_service.py:161–166` (paid-guard reads stale in-session state), `main.py:40–43` (worker), plus inline invocations (BE-10).
- **Evidence:** sweep loads `pending_payment` orders unlocked, then `transition_order_status` sets `order.status = CANCELLED` and flushes. If a concurrent `/payments/verify` holds the row lock (`get_order_by_payment_authority_for_update`, `payment.py:310`) and commits `PAID`, the sweep's UPDATE blocks, then applies over it — its in-memory guards (`payment_status != PAID`, `can_transition(pending_payment→cancelled)`) were evaluated pre-commit of the other transaction. Result: `status=cancelled`, `payment_status=paid`, return-movement ledger rows written for a paid order (`order_service.py:171–176`).
- **Why problematic:** the race window is the whole verify round-trip (gateway call up to 12 s under BE-24) every sweep tick (60 s) for orders near the 30-minute cutoff — the exact "user pays at the last minute" scenario. Distributed lock failing open (`distributed_lock.py:35–37`) multiplies concurrent sweeps during Redis incidents.
- **Root cause:** sweep written as read-then-write without row locks; guards trust the session snapshot.
- **Risk:** paid order auto-cancelled; customer charged, order dead. **Business impact:** direct revenue/trust incident, support escalation. **Technical impact:** ledger contains both sale and return rows for a paid order.
- **Recommendation:** `SELECT … FOR UPDATE SKIP LOCKED` in the sweep and re-check `status`/`payment_status` after lock acquisition; or a single guarded `UPDATE … WHERE status='pending_payment' AND payment_status='unpaid' AND created_at < cutoff RETURNING id`. **Alternative:** compare-and-swap on `status` in `transition_order_status`. **Effort:** S–M · **Priority:** P1 · **Dependencies:** touches BE-10.

#### BE-22 — GET /payments/callback verifies without the row lock POST /verify uses
- **Severity:** Medium · **Category:** Concurrency / idempotency · **Location:** `app/api/endpoints/payment.py:262` (`get_order_by_payment_authority` — no `FOR UPDATE`; contrast `:310` `_for_update`), Hesabfa check-then-insert `services/hesabfa/invoices.py:86–104`.
- **Evidence:** two concurrent callbacks (user double-redirect, or callback + client-side verify) both read `payment_status != PAID`, both call gateway verify (second gets Zarinpal 101 = success, `payment_service.py:130`), both run `transition_order_status(PAID)` + `record_payment_verified` + `maybe_create_invoice_after_payment`. The invoice record existence check is not concurrency-safe → duplicate ledger rows and potentially **two Hesabfa invoices** for one order. One of the two `transition_order_status` calls raises `ValueError("Order is already in status 'paid'")` (`order_service.py:142–143`) — which the callback's bare `except Exception` (BE-02) then **commits and hides**.
- **Root cause:** lock added to `/verify` (per v1 note) but never mirrored to the older callback path.
- **Risk:** duplicate financial records; misleading failure redirect for a successful payment. **Recommendation:** use `get_order_by_payment_authority_for_update` in the callback; make invoice-record creation race-safe (unique constraint on `order_id` + `ON CONFLICT`). Also: the 429 raised by `_check_public_verify_rate_limit` (`payment.py:266`) returns a JSON error to a browser mid-redirect — redirect to the failure URL instead. **Effort:** S · **Priority:** P1 · **Dependencies:** BE-02 fix makes the swallowed transition error visible.

#### BE-23 — bcrypt runs synchronously on the event loop
- **Severity:** Medium · **Category:** Async hygiene / performance · **Location:** `app/core/security.py:17–29` (`bcrypt.checkpw`/`hashpw`, no executor); call sites in async handlers: `auth.py:170` (login verify), `:137` (register hash), `:212,224` (change-password), `otp_service.py:55` (OTP auto-provision hash), `:130` (reset confirm), `core/startup.py:46`.
- **Evidence:** no `to_thread`/`run_in_executor` anywhere in `app/` (grep verified). Each bcrypt call blocks the worker's event loop for ~100–300 ms.
- **Why problematic:** on a single VPS with a handful of uvicorn workers, a modest burst of logins/OTP-verifies serializes *all* traffic — catalog, checkout, payment callbacks — behind password hashing. It is also a cheap DoS lever: the login endpoint throttles per-username (`auth.py:155–160`), not per-IP, so rotating usernames keeps hashing on every request (each miss costs a `checkpw` only when the user exists; registration/OTP provision paths always hash).
- **Root cause:** sync library used directly in async handlers. **Risk:** p99 latency collapse under auth load. **Business impact:** storefront-wide slowdowns that look like "the server is flaky". **Recommendation:** wrap hash/verify in `asyncio.to_thread(...)` (bcrypt releases the GIL), or move to `argon2-cffi` with an executor. **Alternative:** dedicated threadpool sized to CPU. **Effort:** S · **Priority:** P1.

#### BE-24 — External HTTP calls executed while holding DB row locks
- **Severity:** Medium · **Category:** Concurrency / performance · **Location:** checkout: product locks acquired `checkout_service.py:65`, gateway init called `:146` (timeout 12 s, `config.py:61`); payment verify: order lock `payment.py:310` → gateway verify `payment_flow_service.py:138–141` → Hesabfa invoice (contact ensure + item mapping + invoice save, ≥3 sequential calls, 15 s timeout each, `invoices.py:121–194`) all before commit.
- **Why problematic:** every product in a checkout stays `FOR UPDATE`-locked for the full gateway round-trip — concurrent checkouts sharing any product serialize behind it; a slow gateway turns into a sitewide checkout stall. When `HESABFA_ENABLED=true` + `TEST_MODE=false`, a paid verify can hold the order lock ~45 s worst-case while the customer stares at a spinner (and the public-verify throttle window burns).
- **Root cause:** single-transaction convenience. **Recommendation:** commit order creation before gateway init (order is already retriable via authority reuse `payment_flow_service.py:80–85`); move Hesabfa invoice push out of the verify transaction into a queued/deferred job (aligns with BE-07 re-push job). **Effort:** M · **Priority:** P2 · **Dependencies:** BE-01 (transaction ownership), BE-07.

#### BE-25 — Refresh-token rotation has no reuse detection
- **Severity:** Medium · **Category:** AuthN design · **Location:** `app/services/auth_token_service.py:37–47`; `app/crud/refresh_tokens.py:28–36` (revoked tokens filtered out, so a replayed rotated token is indistinguishable from garbage).
- **Evidence:** `rotate_refresh_token` revokes the presented row and issues a new one; presenting an already-revoked hash returns `None` → generic 401. No "revoked token seen ⇒ revoke all user sessions" logic, no audit event, and old-token rows are never purged.
- **Why problematic:** rotation's main security payoff *is* reuse detection: if a token is stolen and both attacker and victim rotate, the system should kill the family. Here the attacker who rotates first simply wins the session silently for up to `REFRESH_TOKEN_EXPIRE_DAYS=7`.
- **Recommendation:** keep a lookup that includes revoked rows; on revoked-token presentation, `revoke_all_refresh_tokens_for_user` + bump `token_version` + audit log. **Effort:** S · **Priority:** P2.

#### BE-26 — OTP: no per-IP budget (SMS cost/harassment), 5-digit code, unsalted SHA-256 at rest
- **Severity:** Medium · **Category:** AuthN / abuse economics · **Location:** `app/api/endpoints/auth.py:374–392` (throttle key `otp_request:{phone}` only), `otp_service.py:19–20` (`secrets.randbelow(100000):05d` — 5 digits), `utils/otp_hash.py:6–7` (plain `sha256(code)`).
- **Evidence:** the send-counting design is good (`auth.py:382–383` counts successes), but the budget is per-**target-phone**: one IP can request OTPs for unlimited *distinct* numbers — 10 SMS per victim per 5 min, unbounded aggregate SMS spend once a paid provider (Kavenegar/Faraz) is live. Public contact/checkout/tracking all have per-IP throttles (`config.py:103–110`); OTP does not. Brute-force math is acceptable (10 verify attempts per 300 s vs 120 s expiry ⇒ ≤ ~10/100,000 per code) but a 5-digit space is below the 6-digit norm and the at-rest hash of a 100k-value space is reversible instantly by anyone with DB read access (rainbow of 100k SHA-256s).
- **Recommendation:** add `enforce_public_throttle(scope="otp", per-IP)` on `/auth/otp/request` (and password-reset request); go to 6 digits; hash as `HMAC(SECRET_KEY, phone + code)`. **Effort:** S · **Priority:** P1 (cost exposure activates the day SMS provider goes live).

#### BE-27 — Startup catalog seeding is not environment-gated
- **Severity:** Medium-Low · **Category:** Correctness / ops · **Location:** `app/main.py:59` (`bootstrap_catalog_seed()` unconditional), `app/core/startup.py:57–116`.
- **Evidence:** on any boot where `SELECT ... FROM categories LIMIT 1` is empty, the app seeds Persian categories, three brands and a **purchasable** product `DEV-CHECKOUT-001` at 250,000 T (`startup.py:94–115`) — in every `APP_ENV`.
- **Why problematic:** a production boot against a fresh/restored-empty DB (bad restore, wrong DSN) silently manufactures a sellable SKU; combined with mock payments being production-forbidden, the order would still be created (inquiry lane needs no payment). Root cause: dev convenience shipped in the app lifecycle instead of a script/fixture. **Recommendation:** gate on `settings.DEBUG or APP_ENV == "development"`. **Effort:** S · **Priority:** P2.

#### BE-28 — Body-size limit contradicts upload limit; Content-Length-only enforcement; sync file writes
- **Severity:** Medium-Low · **Category:** Validation / async hygiene · **Location:** `config.py:113` + `.env.example:101` (`MAX_REQUEST_BODY_BYTES=1_048_576`), `utils/file_storage.py:14` (`MAX_UPLOAD_BYTES = 5MB`), `security_middleware.py:19–25` (header-trusting check), `file_storage.py:29` (full read into memory), `:44` (`Path.write_bytes` — blocking IO in async def).
- **Evidence:** the middleware 413s anything with `Content-Length > 1 MB`, so the advertised 5 MB image upload (product/brand/category) fails for any real photo >1 MB unless ops silently raised the env var; conversely a client omitting/lying about `Content-Length` (chunked) bypasses the middleware entirely and `upload.read()` buffers whatever arrives. Upload content is validated by extension only (`file_storage.py:17–22`) — no magic-byte sniff (served with global `nosniff`, `main.py:158`, so exploitability is low).
- **Recommendation:** raise `MAX_REQUEST_BODY_BYTES` for upload routes (or exempt them) and enforce a streaming read cap; `await asyncio.to_thread(target_path.write_bytes, content)`; add magic-byte check. **Effort:** S · **Priority:** P2.

#### BE-29 — Checkout quantity/items unbounded (cart caps at 999, checkout doesn't)
- **Severity:** Low · **Category:** Validation · **Location:** `app/schemas/storefront.py:121` (`quantity: int = Field(..., ge=1)` — no `le`), `:156` (`items: min_length=1`, no `max_length`); contrast `app/schemas/cart.py:24` (`ge=0, le=999`).
- **Evidence/Risk:** direct `POST /checkout` with `quantity: 10**9` passes validation → grotesque `estimated_total`, ledger rows with absurd magnitudes, gateway `amount` int that Zarinpal will reject *after* the order row exists. The 1 MB body cap bounds item-count abuse but not quantity. **Recommendation:** mirror cart caps (`le=999`, `max_length=100`). **Effort:** S · **Priority:** P2.

#### BE-30 — payments/init leaks order existence to unauthenticated callers; anonymous idempotency scope
- **Severity:** Low · **Category:** AuthZ / info disclosure · **Location:** `app/api/endpoints/payment.py:193–208` (order fetched and 404/403-differentiated **before** the 401 auth check), `:162` (guest scope literal `payment_init:anonymous` shared by all anonymous callers).
- **Evidence:** unauthenticated caller distinguishes: 404 = no such order, 403 `GUEST_ORDER_NOT_PAYABLE` = guest order exists, 401 = user-owned order exists — a sequential-ID oracle. The shared anonymous idempotency scope also lets any anonymous caller who knows a key fetch another guest's cached init response (needs key knowledge; low).
- **Recommendation:** check auth first (401 before order lookup); scope guest idempotency by cart-token fingerprint as checkout does (`checkout.py:40–42`). **Effort:** S · **Priority:** P3.

#### BE-31 — Zarinpal refund integration is likely wrong and demonstrably untested against the live API
- **Severity:** Medium (latent — provider not live) · **Category:** Integration · **Location:** `app/services/payment_service.py:137–165`, esp. `:147` (`refund_url = ZARINPAL_VERIFY_URL.replace("verify.json", "refund.json")`) and `:144` (`"session_id": ref_id` with `merchant_id` auth).
- **Evidence:** the refund URL is fabricated by string-replacing the verify URL; Zarinpal's v4 refund API lives on a different host and authenticates with a personal access token, not `merchant_id` (cannot be verified offline — flagged as unverifiable, but nothing in the repo/tests exercises a real refund; `tests/test_f_payment_audit.py` uses the mock).
- **Risk:** first production refund fails (best case: `PaymentGatewayError` → clean 502) or behaves unexpectedly; combined with BE-20 the failure modes compound. **Recommendation:** verify against Zarinpal docs/sandbox before go-live; isolate refund behind a feature flag until proven. **Effort:** S–M · **Priority:** P1 gate item for gateway go-live.

#### BE-32 — Admin user PATCH: super-admin demotion allowed; email unvalidated
- **Severity:** Low · **Category:** AuthZ hygiene · **Location:** `app/api/endpoints/users.py:181–199` (only *promotion to* super_admin blocked; a super_admin + step-up can demote the *other* super_admin), `app/schemas/user_admin.py:32` (`email: str | None = Field(None, max_length=255)` — no `EmailStr`).
- With exactly two admins, mutual demotion is a plausible foot-gun/insider risk (delete is blocked `users.py:226–231`, demote is not). **Recommendation:** block role changes *of* super_admins via API symmetric to promotion; use `EmailStr`. **Effort:** S · **Priority:** P3.

#### BE-33 — Deprecated stock-quantity surface and dead code still shipped
- **Severity:** Low · **Category:** Code quality / API hygiene · **Location:**
  - `POST /products/{id}/stock/adjust` deprecated-flagged (`products_admin.py:263–309`) but `POST /products/bulk/stock-adjust` is **not** marked deprecated (`:312–334`) though it maps to the same availability toggle (`product_service.py:261–278`);
  - statistics still return `total_stock_value` / `total_stock_quantity` (`products_catalog.py:235–236`);
  - cart response exposes `stock_quantity` (`cart_service.py:44`, `schemas/cart.py`);
  - dead: `extract_stored_authority` (`payment_service.py:183–191`, zero references — grep verified) despite API_CHANGELOG listing note-parsing as *Removed*; `ProductService.get_low_stock_products` (`product_service.py:213–224`, `del threshold` legacy shim);
  - `crud/platform.py` is a clean re-export shim (`:1–33`) — acceptable, not duplication.
- **Recommendation:** mark bulk adjust deprecated, drop stock fields from cart/statistics payloads (coordinate with admin FE), delete dead functions. **Effort:** S · **Priority:** P3.

#### BE-34 — Catch-all handlers log without stack traces
- **Severity:** Low · **Category:** Error handling / observability · **Location:** ~34 `logger.error/warning(f"...")` sites without `exc_info` (grep), e.g. `products_catalog.py:213, 269, 301`, `products_admin.py:67,114,147,177,210,255,304`; only 8 `logger.exception`/`exc_info=True` sites repo-wide (`main.py`, hesabfa modules, `notification_service`, `product_service`).
- **Why problematic:** the broad `except Exception → api_error(500)` pattern in product/category/brand endpoints intercepts before the global handler (`main.py:247–257`, which *does* log `exc_info=True`), so production 500s in the catalog surface leave only `Error retrieving products: <str(e)>` — undiagnosable. **Recommendation:** replace with `logger.exception`, or drop the redundant catch-alls and let the global handler work. **Effort:** S · **Priority:** P2.

#### BE-35 — Full category-table load + metadata build on every product read
- **Severity:** Low (perf) · **Category:** Performance · **Location:** `app/api/endpoints/product_common.py:30–32` (`get_all_categories` per request), called from PLP list (`products_catalog.py:194`), PDP (`:297`), SKU (`:265`), related (`:316`), and every admin write response (`:44`).
- No caching layer anywhere (grep `cache|lru|ttl` over category service/utils: nothing). With a stable ~3-level tree this is a per-request query + O(categories) Python build on the hottest endpoints, plus PLP allows `limit=1000` full summaries unthrottled when no search param is present (`products_catalog.py:65,107–122`). **Recommendation:** small TTL cache (30–60 s) keyed on categories `max(updated_at)`, or precomputed metadata invalidated on category writes; drop anonymous PLP `limit` ceiling to ≤100. **Effort:** S–M · **Priority:** P2.

#### BE-36 — Order status transitions: no locking for admin updates; SMS inside the transaction
- **Severity:** Low · **Category:** Concurrency / side-effect ordering · **Location:** `order.py:262` (`get_order_by_id` — no `FOR UPDATE` before PATCH), `order_service.py:194–198` (`notify_order_status_change` awaited before `flush`/commit — SMS fires even if the commit later fails; also adds SMS-provider latency inside payment-verify's locked transaction via `transition_order_status` at `payment_flow_service.py:150`).
- Two concurrent admin PATCHes can both pass `can_transition` on stale reads (last write wins, both SMS sent). **Recommendation:** `FOR UPDATE` in the PATCH path; move notifications post-commit (collect events, send after). **Effort:** S–M · **Priority:** P3.

---

## 5. Doc-drift table (mandatory check)

| Doc | Claim | Reality (code) | Verdict |
|---|---|---|---|
| `openapi/v1.json` (regen 2026-07-18, `335a1cb`) | 87 operations | **95 routes** in code (endpoints last touched 2026-07-25). Missing: `PUT /products/{id}/availability`, `POST /brands/{id}/logo`, `POST /categories/{id}/image`, all 5 `/hesabfa/*`, `GET/PUT /cms/nav-groups`, `GET /nav-groups/` | **Stale — 11 routes missing** |
| `README.md:285–288` | Cart: `GET /cart/`, `POST /cart/items`, `PATCH /cart/items/{id}` | Actual: `GET /cart` (no slash — `redirect_slashes=False` at `main.py:81` makes `/cart/` a 404), `PUT /cart/items`, `DELETE /cart/items/{id}` (`cart.py:59–126`) | **Wrong methods & path** |
| `README.md` API section | No mention of availability endpoint, hesabfa, nav-groups | Routes exist | Stale (additive) |
| `docs/API_CONTRACT.md:30–41` | Endpoint map modules | **No Hesabfa row at all**; storefront row omits `/nav-groups/`; Users row omits delete + audit-logs | **Drift** |
| `docs/API_CONTRACT.md:57` | `POST /cart/merge` → raw JSON array | `response_model=list[CartResponse]` (`cart.py:129`) ✓ | OK |
| `docs/API_CHANGELOG.md` | "New endpoint ⇒ record here" (policy `:14`) | nav-groups (PR #51), category image (PR #49), brand logo, availability PUT — **no entries** | **Policy violated by its own repo** |
| `docs/API_CHANGELOG.md:115` | note-parsing "Removed" | `extract_stored_authority` still defined (`payment_service.py:183–191`, dead) | Cosmetic drift |
| `docs/BACKEND_CHANGES.md:59` | "Images are URL-based only (no blob storage)" | Multipart upload + local blob storage exist (`products_images.py:60–88`, `file_storage.py`) | **Contradicts code** |
| `docs/BACKEND_CHANGES.md:60` vs `:101–103` | "No status history table exists" vs "history exposed as timeline" | `OrderStatusEvent` table + timeline exist | Internally contradictory / stale |
| `docs/BACKEND_CHANGES.md:96` | "160 passed" | 242 tests collected today | Stale |
| `docs/HESABFA.md` | Scope table, env vars, admin API table, no-admin-reads, item-push-on-save | Matches `hesabfa.py:44–154`, `invoices.py`, `product_service.py:37–47`, `config.py:65–84` — including the deprecated `/stock/sync` no-op and null Hesabfa fields in sales-summary | **Accurate** (best-maintained doc). Only gap: step 7 ("TEST_MODE=false when gateway live") is unenforced by config validation (see BE-07) |

Spot-checked ≥15 endpoints against docs/snapshot: auth (register/login/refresh/otp×2), cart ×4, orders (track/me/status), payments ×4, products (list/detail/sku/statistics/availability), hesabfa ×5, cms nav-groups ×2. Verdict: **HESABFA.md trustworthy; openapi snapshot and README/API_CONTRACT materially stale.** Regeneration is one command (documented at `API_CONTRACT.md:48`) — this is process failure, not effort.

---

## 6. Scores (0–10, strict)

| Category | v1 | v2 | Delta justification |
|---|---|---|---|
| **Backend** | 7.0 | **6.25** | −0.75. The architecture v1 praised is real (idempotency, capability-based verify, fail-closed limits, coherent availability pivot, 242 collected tests), but strict review found a P0 money-path bug v1 missed (BE-20), two concurrency defects in flagship flows (BE-21, BE-22), missing rotation-reuse detection (BE-25), and **zero of ten v1 findings fixed** since v1 — including both P1s. A 7 implies the core flows can be trusted under concurrency and failure; BE-20/21/22 show they cannot yet. Not lower because: blast radius of each fix is small (S–M), authz surface is clean (§3), validation/envelope discipline is genuinely good, and the ledger/idempotency substrate makes the fixes easy to verify. |
| **Backend Performance** | 6.0 | **5.5** | −0.5. v1's score already priced in the JSONB scans and inline sweeps; v2 adds event-loop blocking bcrypt on every auth op (BE-23), external HTTP under row locks in checkout/verify (BE-24), per-request category-table loads on the hottest endpoints with no caching anywhere (BE-35), sync file writes (BE-28), and an anonymous `limit=1000` PLP. Nothing here is exotic to fix, and the DB layer itself (selectinload, count+page pattern) is reasonable — hence 5.5, not lower. |

---

## 7. Self-review

- **Did we try to break the refund path both ways?** Yes: paid→refund works; shipped/delivered→refund produces the BE-20 rollback-after-gateway-refund sequence; declined refund returns 200. Traced the exact exception path (`ValueError` from `order_service.py:145–146` not covered by `payment.py:388–391`).
- **Is BE-21 real under Postgres semantics?** The sweep's plain SELECT takes no row lock; its later UPDATE blocks on verify's `FOR UPDATE` and proceeds after commit with guards already evaluated. Lost-update is textbook. Probability is low (60 s ticks × verify round-trip window × orders at the 30-min boundary) — severity kept High on impact, flagged as low-likelihood.
- **Steelman for BE-23:** bcrypt cost may be tuned low; still 50–100 ms+ default cost on a small VPS, and the pattern (no executor anywhere) is verified by grep, not assumption.
- **What we could NOT verify (honesty list):** Zarinpal refund endpoint correctness (BE-31 — external API, gateway not live); live `tax_percent` distribution (BE-09); production `.env` values (`MAX_REQUEST_BODY_BYTES`, Redis, `TRUSTED_PROXIES`); Hesabfa API behavior beyond client code; whether admin FE still calls deprecated stock routes.
- **Where v2 may itself be too harsh:** BE-27 requires an empty production DB (operational error precondition); BE-30 order-ID oracle leaks existence only, not contents; BE-26 SMS-cost abuse requires a live paid SMS provider (today `console` in non-prod). Each is priced accordingly (P2/P3), not inflated.
- **Checked v1's positive claims before repeating them:** oversell FOR UPDATE (`checkout_service.py:65`), duplicate-line merge (`:31–36`), OTP hashed at rest (`crud/otp.py:26` — though see BE-26 on hash strength), step-up single-use JTI (`crud/idempotency.py:112–125`), search-path ILIKE escaping (`crud/product.py:199–203`). All confirmed.
