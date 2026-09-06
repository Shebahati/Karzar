# Phase — Security Audit (v2, strict / defensive posture)

**Date:** 2026-07-25 · **Auditors:** Security Engineer team (hostile due-diligence mode, defensive framing)
**Baseline:** v1 report `docs/audits/security-audit.md` (same date; overall 7.5)
**Branch:** `docs/engineering-audit-2026-07` @ `66e9ae9` (+ untracked v2 corpus)
**Method:** Full re-read of `app/core/{security,security_middleware,rate_limit,auth_cookies,config,payment_url}.py`, `app/utils/{image_validation,otp_hash,file_storage}.py`, `app/api/deps.py`, `app/api/endpoints/auth.py`, `app/services/otp_service.py`, `app/main.py` middleware/headers, `SECURITY.md`, `.env.example`, `.gitignore`, `.dockerignore`, `Dockerfile`, `docker-compose*.yml`, `deploy/staging/nginx/karzar.conf.template`, `.github/dependabot.yml`, `backend-ci.yml`. Static analysis only.

**Wording note:** This report uses defensive-engineering language (hardening, misconfiguration, input-validation gaps, secret hygiene, least privilege). It does not provide offensive guidance.

---

## 1. Scope & what is genuinely good (re-verified)

1. **Boot-time harden validators** reject weak `SECRET_KEY` placeholders, weak step-up PINs (fixed denylist), `OTP_DEV_ECHO`, wildcard CORS, missing Redis under harden mode; production additionally rejects `DEBUG`, empty `TRUSTED_HOSTS`, `ENFORCE_HTTPS=False`, mock payment, console SMS, and API docs (`config.py:138–150`, `:185–233`).
2. **Session design is above average:** short-lived HS256 access + `token_version` revocation; opaque refresh tokens hashed (SHA-256) with rotation; HttpOnly cookies path-scoped (`/api/v1` access, `/api/v1/auth` refresh); `Secure` derived from env; SameSite validated (`auth_cookies.py:15–68`; `deps.py:84–91`).
3. **Step-up authorization** for destructive admin ops: separate token `type`, 5-minute expiry, DB-enforced single-use `jti`, subject binding, timing-safe PIN compare (`security.py:64–123`; `deps.py:119–158`).
4. **Auth failure limiter fails closed** on Redis check errors (`rate_limit.py:109–111`).
5. **Payment redirect host allowlist** (`payment_url.py:10–65`); URL-time SSRF hostname/IP/metadata blocks (`image_validation.py:9–74`).
6. **Security headers** on every response (`main.py:157–163`); public register gated by default (`ALLOW_PUBLIC_REGISTER=False`, `config.py:93`; `auth.py:113–118`).
7. **Dependabot is present** (v1 missed this): `.github/dependabot.yml` covers pip, github-actions, and both frontend npm trees weekly.

---

## 2. Critique of the v1 report

### 2.1 What v1 got right
All of SEC-01…SEC-10 themes remain present. Boot validators, fail-closed rate limiting, cookie path split, payment allowlist, and step-up jti binding are correctly praised.

### 2.2 What v1 got wrong
1. **OTP “~10⁶ / 6-digit”** — false. Generator is **5 digits** (`00000`–`99999`): `otp_service.py:19–20` (`secrets.randbelow(100000)`). Space ≈ **10⁵**. SEC-04 severity must rise.
2. **“No Dependabot / supply-chain absent”** — **false**. Dependabot exists; what remains missing is `pip-audit` / `npm audit` in CI.
3. **nginx body-size “unknown”** — template sets `client_max_body_size 12m` (`deploy/staging/nginx/karzar.conf.template:44`). Live application still ops-verify only; in-app Content-Length-only gap remains.
4. **Overall 7.5 / Auth 8** — too generous under acquisition-bar grading given 5-digit unsalted OTP, SVG+StaticFiles, CSRF with no Origin check, gitignore gaps, and an example PIN that passes the weak-PIN validator.

### 2.3 What v1 missed (SEC-20+)
OTP entropy width; extension-only upload validation; Redis published without auth on base compose; unauthenticated `/metrics` when enabled; `.gitignore`/`.dockerignore` secret-pattern gaps; `ALLOW_PUBLIC_REGISTER` not production-hardened (staging template enables it); dual token delivery (JSON body + cookies); runtime image installing `requirements-dev.txt` on root Dockerfile; example PIN footgun; bootstrap admin password unvalidated; timing oracle on password-reset; localhost always allowed in payment URL allowlist; inactive-user oracle after correct password.

---

## 3. Findings register

### Re-verified v1 findings

#### SEC-01 — SSRF guard checks hostname string, not resolved addresses
- **Severity:** Medium · **Category:** Input validation / outbound hardening · **Location:** `app/utils/image_validation.py:40–74`
- **Evidence:** `_hostname_is_blocked` inspects literal hostname/IP and known-internal names; public DNS names that resolve to RFC1918/link-local/metadata are not re-checked at fetch time.
- **Why / Risk / Impact:** Incomplete defense-in-depth for any server-side fetch of stored image URLs (mirror/materialize scripts, future thumbnails). Admin-triggered today; VPS has no cloud metadata service — blast radius bounded but guard intent unmet.
- **Root cause:** Validation stops at parse-time string checks.
- **Recommended:** At fetch time resolve A/AAAA, re-validate against `_PRIVATE_NETWORKS`, pin IP for the connection. **Alternative:** Egress proxy with IP deny list. **Effort:** S–M · **Priority:** P2 · **Dependencies:** fetch code paths.

#### SEC-02 — Body-size limit trusts `Content-Length` only
- **Severity:** Low–Medium · **Category:** Hardening / availability · **Location:** `app/core/security_middleware.py:18–33`
- **Evidence:** Absent `Content-Length` → middleware calls `call_next` with no byte accounting. Nginx template caps at 12m (`karzar.conf.template:44`); app default `MAX_REQUEST_BODY_BYTES=1_048_576` (`config.py:113`) vs upload allow 5 MB (`file_storage.py:14`) inconsistent.
- **Recommended:** Confirm live nginx directive; wrap receive stream with hard cap. **Effort:** S · **Priority:** P2 (verify) / P3 (in-app).

#### SEC-03 — One shared step-up PIN for all super-admins
- **Severity:** Medium · **Category:** Least privilege / accountability · **Location:** `config.py:87–92`; `security.py:118–123`; `auth.py:349–356`
- **Evidence:** Single plaintext `ADMIN_STEP_UP_PIN`; timing-safe compare; no per-admin factor.
- **Recommended:** Per-admin hashed PIN or TOTP; env PIN as break-glass only. **Effort:** M · **Priority:** P2.

#### SEC-04 — OTP hashes are unsalted SHA-256 over a **5-digit** space *(severity)*
- **Severity:** Medium (raised from Low–Medium) · **Category:** Cryptographic storage · **Location:** `app/utils/otp_hash.py:6–7`; `app/services/otp_service.py:19–20`; `app/crud/otp.py:26,43`
- **Evidence:** `sha256(code)` over `randbelow(100000)` → **100 000** codes. Mitigations: short TTL, attempt limits — insufficient if rows leak.
- **Why / Risk:** Offline precomputation of the entire code space is trivial; combined with OTP auto-provision of B2C users (`otp_service.py:52–62`) this is account-takeover surface.
- **Recommended:** HMAC-SHA256 with SECRET_KEY-derived pepper **and** 6+ digit (or alphanumeric) codes. **Effort:** S · **Priority:** **P1** · **Dependencies:** SEC-20.

#### SEC-05 — CSRF protection relies solely on SameSite; no Origin middleware
- **Severity:** Medium (config-dependent; Low with default `lax`) · **Category:** Session integrity / misconfiguration · **Location:** `auth_cookies.py:27–31,34–38`; `deps.py:24–40`; `security_middleware.py` (body+HTTPS only — no Origin check)
- **Evidence:** `AUTH_COOKIE_SAMESITE` accepts `none`; cookie auth on state-changing routes; contract doc confirms SameSite+CORS only.
- **Recommended:** Origin allowlist middleware for cookie-auth non-safe methods; reject `samesite=none` unless CSRF token implemented. **Effort:** S · **Priority:** P2.

#### SEC-06 — JWTs lack `iss`/`aud`; access & step-up share signing key
- **Severity:** Low · **Category:** Token hygiene · **Location:** `security.py:44–51,69–75,79–82`; `deps.py:52–58` (`type in (None, "access")` accepts missing type)
- **Recommended:** Add `iss`/`aud` per class; require `type=="access"` strictly. **Effort:** S · **Priority:** P3.

#### SEC-07 — CORS wildcard methods/headers with credentials
- **Severity:** Low · **Category:** Misconfiguration · **Location:** `main.py:94–100`
- **Recommended:** Enumerate methods + needed headers (`Authorization`, `Content-Type`, `X-Step-Up-Token`, `X-Request-ID`, `Idempotency-Key`). **Effort:** S · **Priority:** P4.

#### SEC-08 — Mock admin credential hint is tracked
- **Severity:** Info · **Category:** Secret hygiene · **Location:** `frontend/admin-panel/src/lib/mock-credentials.ts:5–8`
- **Recommended:** Verify no real environment seeds `Admin@123456`. **Effort:** S · **Priority:** P4.

#### SEC-09 — Credentials shared through chat/ops channels (process)
- **Severity:** Medium (process) · **Category:** Secrets lifecycle
- **Evidence:** Operational (v1); not re-proven in code this pass.
- **Recommended:** Rotate super-admin password + Hesabfa tokens; password manager; document rotation in `OPERATIONS.md`. **Effort:** S · **Priority:** P1.

#### SEC-10 — Uploads served via StaticFiles; SVG allowed
- **Severity:** Medium (raised from Low when combined with SEC-21) · **Category:** Input/output handling · **Location:** `app/core/constants.py:11–13`; `main.py:112–114`; `file_storage.py:17–44`
- **Evidence:** `.svg` in `ALLOWED_IMAGE_URL_EXTENSIONS`; uploads saved by extension; served at `/static/uploads`.
- **Recommended:** Drop `.svg` from product image allowlists; or serve with `Content-Disposition: attachment` / sandbox CSP. **Effort:** S · **Priority:** P2.

---

### New findings (v2)

#### SEC-20 — OTP entropy is only 5 digits (~10⁵)
- **Severity:** Medium–High · **Category:** Authentication strength · **Location:** `app/services/otp_service.py:19–20`
- **Evidence:** `return f"{secrets.randbelow(100000):05d}"`
- **Why / Risk / Impact:** Online guessing is rate-limited, but offline/DB-leak scenarios (SEC-04) become catastrophic; SMS OTP UX commonly assumes 6 digits. Storefront account takeover → fraudulent inquiry/orders.
- **Root cause:** Generator width chosen without entropy review.
- **Recommended:** Minimum 6 digits (or alphanumeric); keep rate limits; pair with peppered hash (SEC-04). **Alternative:** Longer opaque codes. **Effort:** S · **Priority:** **P1** · **Dependencies:** SMS template length.

#### SEC-21 — Upload validation is extension-only (no magic/MIME enforcement)
- **Severity:** Medium · **Category:** Input validation · **Location:** `app/utils/file_storage.py:17–34`
- **Evidence:** Only `Path(filename).suffix` checked; bytes written as-is.
- **Recommended:** Verify magic bytes / decode with Pillow (raster only); reject SVG. **Effort:** S–M · **Priority:** P2 · **Dependencies:** SEC-10.

#### SEC-22 — Redis has no auth; base compose publishes Redis/Postgres to host
- **Severity:** Medium (dev/default); staging binds loopback · **Category:** Least privilege / network exposure · **Location:** `docker-compose.yml:35–68`; Redis client `rate_limit.py:88–92` (host/port only); staging override `docker-compose.staging.yml:24–30`
- **Evidence:** Base maps `"6379:6379"` and `"5435:5432"`; no `requirepass` / `REDIS_PASSWORD`.
- **Recommended:** Redis AUTH + app password; loopback binds in base compose; Redis only on internal Docker network in prod. **Effort:** S · **Priority:** P2.

#### SEC-23 — `/metrics` is unauthenticated when enabled
- **Severity:** Low–Medium · **Category:** Information exposure · **Location:** `main.py:102–108`; staging forces `ENABLE_METRICS: "true"` (`docker-compose.staging.yml:17`)
- **Evidence:** Instrumentator exposes `/metrics` with no auth; nginx API `location /` proxies broadly.
- **Recommended:** Scrape only on loopback/private network; nginx `allow`/`deny`. **Effort:** S · **Priority:** P3.

#### SEC-24 — `.gitignore` / `.dockerignore` secret-pattern gaps
- **Severity:** Medium · **Category:** Secret hygiene · **Location:** `.gitignore:7–10,47–48,65–69`; `.dockerignore:1–24`
- **Evidence:** Ignores `.env`, `.env.local`, `.env.*.local`, `.env.staging.generated`, `.deploy-secrets` — but **not** `.env.production` / `.env.staging` generically; root `*.pem` not ignored (only `frontend/**/*.pem`); `.dockerignore` omits `.deploy-secrets` / `.env.staging.generated`.
- **Recommended:** Ignore `.env.*` except `*.example`/`*.template`; ignore `*.pem`; dockerignore secrets files. **Effort:** S · **Priority:** **P1**.

#### SEC-25 — `ALLOW_PUBLIC_REGISTER` not production-hardened; staging template enables it
- **Severity:** Medium · **Category:** Misconfiguration / auth gate · **Location:** `config.py:93,185–233` (no check); `auth.py:113–118`; `deploy/staging/.env.staging.template:51` → `true`
- **Recommended:** Fail boot in production unless explicitly justified; set staging template `false`. **Effort:** S · **Priority:** P2.

#### SEC-26 — Dual token delivery (JSON body + HttpOnly cookies)
- **Severity:** Low–Medium · **Category:** Session design · **Location:** `auth_cookies.py:2–4,46–68`; `auth.py:187–190,410–417`
- **Evidence:** Login/OTP/refresh return tokens in body **and** set cookies.
- **Why:** Any XSS or careless client storage of body tokens bypasses HttpOnly benefit.
- **Recommended:** Cookie-only for browsers; omit refresh from JSON for cookie clients (contract versioning). **Effort:** M · **Priority:** P3 · **Dependencies:** frontend auth contract.

#### SEC-27 — Root Dockerfile installs `requirements-dev.txt` into runtime image
- **Severity:** Low · **Category:** Hardening / supply-chain surface · **Location:** `Dockerfile:18–20,37–38`
- **Note:** Live staging path uses `Dockerfile.staging` (prod-only) — root Dockerfile still wrong for local/alt builds.
- **Recommended:** Runtime install prod requirements only. **Effort:** S · **Priority:** P3.

#### SEC-28 — Example PIN that **passes** the weak-PIN validator
- **Severity:** Medium · **Category:** Secret hygiene / misconfiguration · **Location:** `.env.example:119` `ADMIN_STEP_UP_PIN=8472916350`; denylist `config.py:188–196` includes `84729101` but **not** `8472916350`
- **Evidence:** With `.env.example`’s `DEBUG=False` + Redis set, this PIN boots under harden mode. Teams copying the example into production-like envs share a public PIN.
- **Recommended:** Use a placeholder that **fails** the validator; expand denylist; document. **Effort:** S · **Priority:** **P1**.

#### SEC-29 — Bootstrap admin password not strength-validated
- **Severity:** Medium · **Category:** Authentication / secret hygiene · **Location:** `.env.example:96–97`; `startup.py:19–54`; no validator in `config.py`
- **Evidence:** `INITIAL_SUPER_ADMIN_PASSWORD=change-me-admin-password` accepted and persisted on first boot.
- **Recommended:** Reject weak bootstrap passwords under harden/production; force rotation flag. **Effort:** S · **Priority:** P2.

#### SEC-30 — No automated vulnerability scanning in CI (Dependabot ≠ audit gate)
- **Severity:** Medium · **Category:** Vulnerable components / supply chain · **Location:** `.github/workflows/backend-ci.yml` (ruff/mypy/pytest only); `.github/dependabot.yml` (present)
- **v1/devops drift:** OPS-05 “no Dependabot” was incorrect.
- **Recommended:** Non-blocking then blocking `pip-audit`; npm audit in frontend CI. **Effort:** S · **Priority:** P2.

#### SEC-31 — Password-reset request timing can enumerate phones
- **Severity:** Low · **Category:** Identification failures · **Location:** `auth.py:292–309`; `otp_service.py:82–107`
- **Evidence:** Unknown phone → fast generic success; known phone → SMS path (slower) before success. Body is enumeration-safe; timing may not be.
- **Recommended:** Constant-time path (always enqueue / fixed delay). **Effort:** S–M · **Priority:** P3.

#### SEC-32 — `payment_url` always allows `localhost` / `127.0.0.1`
- **Severity:** Low · **Category:** Redirect hardening · **Location:** `payment_url.py:40–41,56–58`
- **Evidence:** Local hosts allowed regardless of `APP_ENV`. Practical risk low today (URLs built internally).
- **Recommended:** Allow localhost only when `PAYMENT_PROVIDER=="mock"` or non-production. **Effort:** S · **Priority:** P4.

#### SEC-33 — Inactive-user oracle after correct password on login
- **Severity:** Low · **Category:** Identification · **Location:** `auth.py:170–184`
- **Evidence:** Wrong password → generic 401; correct password + inactive → distinct 403 `"Inactive user account"`.
- **Recommended:** Same generic unauthorized message (still rate-limit). **Effort:** S · **Priority:** P4.

---

## 4. Doc-drift table

| Doc / artifact | Claim | Reality | Verdict |
|---|---|---|---|
| `SECURITY.md` | Disclosure + never commit secrets | Thin policy-only; no CSRF/OTP/PIN claims | Accurate (limited) |
| `README.md:514–523` | “Input validation and sanitization”; “Environment-based secrets (never committed)” | SVG/extension-only uploads; gitignore gaps; example PIN/password footguns | **Overstated** |
| README ~485 | “weak PIN values rejected when DEBUG=False” | True for fixed denylist; **false** for `.env.example` PIN `8472916350` | **Drift** |
| Auth cookie contract | CSRF = SameSite + CORS | Matches code (no Origin middleware) | Accurate |
| v1 + devops “no Dependabot” | Absent | `.github/dependabot.yml` exists | **v1 wrong** |
| v1 OTP “6-digit / 10⁶” | — | 5-digit / 10⁵ | **v1 wrong** |
| Staging template | — | `ALLOW_PUBLIC_REGISTER=true`; mock payment + console SMS allowed outside production | Footgun |

---

## 5. OWASP-oriented mapping (defensive)

| Theme | Status | Mapped findings |
|---|---|---|
| Access control / session | Role deps + step-up jti solid; CSRF secondary control missing; register flag not production-locked | SEC-05, SEC-25, SEC-26 |
| Cryptographic failures | bcrypt OK; OTP unkeyed + low entropy; shared plaintext PIN | SEC-04, SEC-20, SEC-03, SEC-28 |
| Injection | Parameterized SQL good (unchanged from v1) | — |
| Insecure design | Shared PIN; dual token channels; OTP auto-provision | SEC-03, SEC-26, SEC-20 |
| Security misconfiguration | Strong boot validators; CORS wildcards; metrics open; Redis publish; staging register=true | SEC-07, SEC-22, SEC-23, SEC-25, SEC-28 |
| Vulnerable components | Dependabot present; no CI audit | SEC-30, SEC-27 |
| Identification & authentication | Rate limits good; OTP entropy weak; timing/oracle nits | SEC-20, SEC-31, SEC-33, SEC-29 |
| Software & data integrity | Wide image COPY; no SBOM/audit gate | SEC-27, SEC-30 |
| Logging & monitoring | Request IDs + optional metrics; metrics unauthenticated | SEC-23 |
| SSRF / unsafe outbound | URL checks present; no resolve-time pinning | SEC-01 |
| Input validation / unsafe outputs | SVG + extension-only uploads + StaticFiles | SEC-10, SEC-21 |
| Secret hygiene | Examples + gitignore/dockerignore gaps | SEC-24, SEC-28, SEC-29, SEC-09 |

---

## 6. Scores (0–10, strict)

| Category | v1 | v2 | Delta justification |
|---|---|---|---|
| Authentication | 8.0 | **6.5** | −1.5. 5-digit OTP + unsalted hash; dual token body; bootstrap password unchecked; inactive oracle. Fail-closed limiter and refresh rotation keep it above 6. |
| Authorization | 7.5 | **6.5** | −1.0. Step-up/jti still strong; shared PIN + CSRF config hole + register flag not production-enforced. |
| Secrets management | 7.5 | **6.0** | −1.5. Boot validators excellent, but example PIN footgun, gitignore/dockerignore gaps, Redis unauthenticated, process rotation debt. |
| Input/output handling | 7.0 | **5.5** | −1.5. SSRF DNS gap, SVG+static, extension-only uploads, CL-only body limit. |
| **Security overall** | **7.5** | **6.0** | **−1.5**. Designed with care, but OTP entropy + upload/SVG + CSRF/secret footguns prevent a “good” band under acquisition-bar review. Not lower because privilege-escalation path B2C→admin was not found, payment allowlist holds, and harden validators are best-in-class for project size. |

---

## 7. Self-review

- **OTP width verified** at `otp_service.py:20` — not inferred from docs.
- **Dependabot verified** on disk (and present on `origin/main` lineage).
- **nginx body-size** verified in template; live Certbot-managed conf not inspected from VPS.
- **Privilege escalation B2C→admin:** re-checked role deps + user mutation endpoints — none found without super-admin.
- **Token-type confusion:** both verifiers check `type` (with the `None`-as-access caveat in deps — SEC-06).
- **Unverified live:** production PIN value, whether `8472916350` is deployed, Redis exposure on the VPS, HSTS state, actual `/metrics` reachability behind HTTPS.
- **Where v2 may be harsh:** SEC-32 localhost allowlist has low practical risk today; SEC-33 inactive oracle requires a valid password first. Priced as P4.
