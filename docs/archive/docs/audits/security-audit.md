# Phase 4 — Security Audit (OWASP-oriented)

**Date:** 2026-07-25 · **Auditors:** Security Engineer, Staff Backend Engineer, Principal Reviewer
**Scope:** AuthN/Z, session/cookie handling, secrets management, SSRF/injection surfaces, middleware, rate limiting, OWASP Top 10 mapping.
**Method:** Full read of `core/security.py`, `security_middleware.py`, `auth_cookies.py`, `payment_url.py`, `utils/image_validation.py`, `utils/otp_hash.py`, `rate_limit.py`, `request_throttle.py`, `.gitignore`, git-tracked-file scan; endpoint auth spot checks in Phase 3.

---

## 1. What is genuinely good (verified)

1. **No secrets in git.** Tracked matches are only `.env*.example`/templates; `.gitignore` covers `.env*`, `.deploy-secrets`, `.env.staging.generated`, frontend `.env*`, `*.pem` — twice, belt-and-braces.
2. **Secrets fail fast at boot** — placeholder `SECRET_KEY`s, weak PINs, OTP echo, wildcard CORS, mock payments are *unbootable* in production (`config.py` validators).
3. **Session design is above average for this stack:** short-lived HS256 access token + `token_version` revocation; opaque refresh tokens hashed (SHA-256) with rotation; HttpOnly cookies path-scoped (`/api/v1` access, `/api/v1/auth` refresh), `Secure` derived from env, SameSite validated to `lax|strict|none` with safe fallback.
4. **Step-up authorization for destructive admin ops** — separate token type, 5-minute expiry, DB-enforced single-use `jti`, subject binding to the authenticated admin, timing-safe PIN compare.
5. **Layered abuse controls:** failure-counting limiter for auth (fails **closed** on Redis outage) plus per-IP request throttles for contact/checkout/tracking/PLP; body-size middleware; TrustedHost + proxy-header trust configured.
6. **SSRF guard exists and is thoughtful** — blocks credentials-in-URL, non-http(s) schemes, literal private/reserved IPv4+IPv6 ranges, metadata hostnames, `.local`/`.localhost` suffixes, malformed IPv4-lookalikes.
7. **Payment redirect URLs are allowlisted** (Zarinpal hosts + configured callback hosts only) — blocks open-redirect via payment flow.
8. **Security headers on every response** (nosniff, DENY frames, referrer policy, permissions policy, restrictive CSP for the API origin).

## 2. Findings

### SEC-01 — SSRF guard checks the hostname string, not what it resolves to
- **Severity:** Medium · **Category:** SSRF (OWASP A10:2021) · **Location:** `app/utils/image_validation.py:40–58`
- **Evidence:** `_hostname_is_blocked` blocks literal IPs and known-internal names, but a public domain whose DNS A/AAAA record points at `127.0.0.1`/`10.x` (DNS rebinding or attacker-controlled domain) passes validation. Server-side fetching of stored image URLs happens in mirror/materialize scripts and any future thumbnail pipeline.
- **Risk:** An admin-supplied (or compromised-admin) image URL becomes an internal port scanner / metadata reader when the server fetches it. Mitigated today because fetching is admin-triggered and the VPS has no cloud metadata service — but the guard's *intent* is defense-in-depth and it has this known bypass.
- **Recommendation:** At fetch time, resolve the hostname and re-validate every resolved address against `_PRIVATE_NETWORKS` (and pin the resolved IP for the actual connection, e.g. httpx transport with resolved address). Keep the URL-time check as a fast-fail.
- **Alternative:** Route server-side fetches through an egress proxy with an IP-level blocklist.
- **Effort:** S–M · **Priority:** P2

### SEC-02 — Body-size limit trusts Content-Length only
- **Severity:** Low–Medium · **Category:** DoS hardening · **Location:** `core/security_middleware.py:18–33`
- **Evidence:** Requests without `Content-Length` (chunked transfer) bypass the check entirely; the middleware never counts streamed bytes.
- **Mitigation in place:** Nginx sits in front in staging/production and buffers/limits (`client_max_body_size`) — **verify** this directive exists in the deployed nginx config; if absent, the bypass is live.
- **Recommendation:** Confirm/set `client_max_body_size 2m;` in nginx; optionally wrap `receive` to enforce a hard cap in-app.
- **Effort:** S · **Priority:** P2 (verification), P3 (in-app cap)

### SEC-03 — One shared step-up PIN for all super-admins
- **Severity:** Medium · **Category:** AuthZ / accountability · **Location:** `settings.ADMIN_STEP_UP_PIN`, `core/security.py:118–123`
- **Evidence:** A single env-stored plaintext PIN authorizes destructive actions for every super-admin (two accounts now exist). Audit logs attribute the *user*, but the *knowledge factor* is shared — no per-person revocation, rotation requires telling everyone.
- **Recommendation:** Per-admin hashed PIN column (bcrypt) or TOTP; keep env PIN as documented break-glass only.
- **Effort:** M · **Priority:** P2

### SEC-04 — OTP hashes are unsalted, unkeyed SHA-256 of a 6-digit space
- **Severity:** Low–Medium · **Category:** Cryptographic storage · **Location:** `app/utils/otp_hash.py`
- **Evidence:** `sha256(code)` over ~10⁶ possible codes is reversible in milliseconds if `otp_codes` rows leak. Mitigations: 120 s expiry, attempt rate limiting, rows are short-lived.
- **Recommendation:** `HMAC-SHA256(code, SECRET_KEY-derived pepper)` — one-line change, removes offline enumeration entirely.
- **Effort:** S · **Priority:** P2

### SEC-05 — CSRF protection relies solely on SameSite=Lax
- **Severity:** Low–Medium · **Category:** CSRF (OWASP A01) · **Location:** cookie auth path (`auth_cookies.py`, `deps.py` accepts cookie on all state-changing routes)
- **Evidence:** No CSRF token or Origin/Referer verification; `AUTH_COOKIE_SAMESITE` is configurable and `none` is an accepted value — if ever set to `none` (e.g. for a cross-subdomain admin), every state-changing endpoint becomes CSRF-able.
- **Current exposure:** With `lax` (default) cross-site POSTs don't carry cookies → effectively protected today.
- **Recommendation:** Add an Origin-header check middleware for cookie-authenticated non-GET requests (cheap, no token plumbing); reject `samesite=none` in config validation unless a CSRF token is implemented.
- **Effort:** S · **Priority:** P2

### SEC-06 — JWTs lack `iss`/`aud`; access & step-up share one signing key
- **Severity:** Low · **Category:** Token hygiene · **Location:** `core/security.py`
- **Evidence:** Type confusion is prevented only by the `type` claim check (currently done everywhere — verified `deps.py:52`, `verify_step_up_token:95`). No audience separation for future services.
- **Recommendation:** Add `iss="karzar-api"`, `aud` per token class, verify on decode. · **Effort:** S · **Priority:** P3

### SEC-07 — CORS: explicit origins but wildcard methods/headers with credentials
- **Severity:** Low · **Location:** `main.py:94–100`
- **Evidence:** `allow_methods=["*"], allow_headers=["*"]` with `allow_credentials=True` when origins are pinned. Spec-compliant and origin-restricted, but broader than needed (e.g. `X-Step-Up-Token` is the only custom header required).
- **Recommendation:** Enumerate needed methods/headers. · **Effort:** S · **Priority:** P4

### SEC-08 — Mock admin credential hint is a tracked file
- **Severity:** Info · **Location:** `frontend/admin-panel/src/lib/mock-credentials.ts`
- **Evidence:** Mock phone/password hint (`Admin@123456`) is committed; comment claims dynamic import keeps it out of live bundles. Risk is not the file itself but pattern-copying: if any real environment ever seeds this password, it's public.
- **Recommendation:** Verify no seeded account uses it (staging DB check); keep.
- **Effort:** S · **Priority:** P4

### SEC-09 — Credentials shared through chat/ops channels need rotation discipline
- **Severity:** Medium (process) · **Category:** Secrets lifecycle
- **Evidence:** During this project's operation, a super-admin password and Hesabfa API credentials transited chat in plaintext; the same PIN/password patterns repeat across environments.
- **Recommendation:** Rotate the super-admin password and Hesabfa `loginToken` now that setup is complete; adopt a password manager for the two-person team; document rotation steps in `docs/OPERATIONS.md`.
- **Effort:** S · **Priority:** P1 (operational, not code)

### SEC-10 — Upload directory served without content-type hardening review
- **Severity:** Low · **Location:** `main.py:112–114` (`/static/uploads` StaticFiles)
- **Evidence:** Files land under `data/uploads` and are served by Starlette `StaticFiles`; `X-Content-Type-Options: nosniff` is set globally (good). SVG is an allowed extension (`constants.py`) — stored/served SVG can carry scripts; combined with URL-sourced images this is a stored-XSS vector *if* ever rendered same-origin in admin.
- **Recommendation:** Drop `.svg` from `ALLOWED_IMAGE_URL_EXTENSIONS` for product images, or serve uploads with `Content-Security-Policy: sandbox` / `Content-Disposition: attachment` for SVG.
- **Effort:** S · **Priority:** P2

## 3. OWASP Top 10 (2021) mapping

| Risk | Status |
|---|---|
| A01 Broken Access Control | **Good** — role deps + ownership checks + step-up; CSRF gap noted (SEC-05). |
| A02 Cryptographic Failures | **Mostly good** — bcrypt passwords, hashed refresh/OTP; OTP unsalted (SEC-04). |
| A03 Injection | **Good** — SQLAlchemy parameterized throughout; ILIKE escaped on search path (partial on spec filters, BE-05). |
| A04 Insecure Design | **Good** — idempotency, ledgers, fail-closed limits; shared PIN is the design smell (SEC-03). |
| A05 Security Misconfiguration | **Strong** — boot-time validators are best-in-class for this size. |
| A06 Vulnerable Components | **Not audited here** — no automated dependency scanning found (see DevOps phase; `pip-audit`/`npm audit` absent from CI). |
| A07 Identification & AuthN Failures | **Good** — rate limits, OTP expiry, rotation, revocation. |
| A08 Software & Data Integrity | **Fair** — no dependency pinning review, no SBOM; CI deploys from self-hosted runner (DevOps phase). |
| A09 Logging & Monitoring | **Fair** — request-ID logging exists; no security-event alerting. |
| A10 SSRF | **Fair** — guard present with DNS-resolution gap (SEC-01). |

## 4. Self-challenge

- Attempted to find a privilege-escalation path from B2C → admin: all admin routers depend on `get_current_super_admin`; user-role mutation endpoint (`users.py`) requires super-admin; registration is disabled. None found.
- Attempted token-type confusion (step-up as access, access as step-up): both verifiers check `type`. Blocked.
- Attempted payment open-redirect: gateway URL allowlisted; callback redirects only to configured URLs. Blocked.
- Attempted ILIKE injection via search: escaped with explicit escape char. Blocked (spec filters remain unescaped but parameterized — robustness, not injection).
- Not tested live: nginx `client_max_body_size` (SEC-02 verification), staging TLS config, Redis exposure (compose review in DevOps phase).

## 5. Scores

| Category | Score | Justification |
|---|---|---|
| Authentication | **8/10** | Rotation, revocation, OTP hygiene, fail-closed limits; minor JWT claim gaps. |
| Authorization | **7.5/10** | Role deps + step-up single-use are strong; shared PIN and CSRF-by-config caveat. |
| Secrets management | **7.5/10** | Clean repo, boot validators; process-level rotation debt (SEC-09). |
| Input/output handling | **7/10** | Parameterized SQL, escaped search, SSRF guard; DNS gap, SVG, spec-filter caps. |
| **Security overall** | **7.5/10** | Clearly designed by someone who cared; remaining items are sharpening, not rescue. |
