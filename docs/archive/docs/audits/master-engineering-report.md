# Karzar — Master Engineering Report

**Date:** 2026-07-25 · **Basis:** 8 completed audit phases (see files in this folder)
**Repository:** Karzar monorepo — FastAPI backend, Next.js storefront + admin panel, PostgreSQL/Redis, single-VPS Docker deployment
**Live context:** ~5,900 products, 40 brands, 159 categories, live at karzartools.com

---

## 1. Executive Summary

Karzar is **substantially better engineered than a typical two-person e-commerce
build at this stage** — and simultaneously **one disk failure away from losing
everything**.

The code shows a consistent security- and correctness-first culture: boot-time
configuration validators that make weak production configs unbootable, a payment
pipeline with row locking, idempotency keys, allowlisted redirects and
append-only ledgers, hashed OTPs and refresh tokens, a real backend test suite
(242 tests, enforced 62% coverage floor), and a storefront with correct
SSR/SEO plumbing and RTL/Persian done properly.

The risks are concentrated **not in the code but around it**: backups are stored
on the same disk they protect (P0), every merge to `main` deploys directly to
the live customer site with no pre-production soak, the deploy runner is an
unmonitored single point of failure, there is zero alerting, and the two
frontends — the platform's entire write-path UI — have effectively no tests.
Inside the code, the systemic weaknesses are inconsistent transaction ownership
(commits scattered across endpoints *and* services), order lines that don't
snapshot product data (an accounting-integrity gap for a business reconciling
with Hesabfa), and a catalog search/filter layer that will not survive a 10×
catalog without index work.

**One sentence:** ship the offsite backup and monitoring this week, fix the five
P1 code items this month, and this platform is credibly production-grade for
years; skip them, and the strengths won't matter.

## 2. Overall Engineering Score

| Category | Score | Source phase |
|---|---|---|
| Architecture | 7.5 | Phase 1 |
| Backend | 7.0 | Phase 3 |
| Frontend (storefront) | 7.5 | Phase 5 |
| Frontend (admin) | 6.5 | Phase 6 |
| Database | 7.0 | Phase 2 |
| Performance | 6.0 | Phases 2/3/5 |
| Security | 7.5 | Phase 4 |
| UX | 7.5 | Phase 5 |
| UI consistency | 7.0 | Phases 5/6 |
| SEO | 6.5 | Phase 5 |
| Accessibility | 7.0 (provisional) | Phase 5 |
| DevOps | 5.5 | Phase 7 |
| Testing | 6.0 | Phase 8 |
| Developer Experience | 7.5 | Phase 8 |
| Maintainability | 6.5 | Phases 1/8 |
| Scalability | 6.0 | Phases 2/7 |
| Documentation | 7.0 | Phases 1/8 |
| **Overall Engineering** | **6.8 / 10** | weighted toward operational risk |

The overall score is deliberately pulled below the code-quality average by the
DevOps/DR posture: engineering excellence includes what happens when the disk
dies, and today the answer is "everything is gone."

## 3. Consolidated Issue Register (deduplicated, prioritized)

45 distinct findings were identified across phases; duplicates merged
(e.g. order-snapshot appears in Phases 1+2 → one issue). Full details with
evidence, root cause, alternatives and effort live in the phase reports; IDs
below reference them.

### P0 — Critical (do this week)

| # | Issue | ID | Effort |
|---|---|---|---|
| 1 | Backups stored on same VPS disk; no offsite copy, no restore drills | OPS-02 | S |

### P1 — High (do this month)

| # | Issue | ID | Effort |
|---|---|---|---|
| 2 | No pre-production environment; "staging" deploys the live site on every merge; add smoke-gate + rollback | OPS-01 | S–M |
| 3 | Zero alerting/observability (uptime, 5xx, worker heartbeat, payment failures) | OPS-07 | M |
| 4 | Order items don't snapshot product name/SKU/tax — accounting integrity | DB-01/ARCH-06 | S |
| 5 | Transaction ownership anarchy: commits in both endpoints and services | BE-01 | M |
| 6 | Payment callback commits on unexpected exceptions and swallows them silently | BE-02 | S |
| 7 | Frontend test coverage ≈ 0 across both apps | QA-01/FE-A-01 | M |
| 8 | No frontend typecheck/lint gate on PRs (breaks discovered at deploy time) | OPS-04 | S |
| 9 | Deploy runner offline = silent deploy freeze; no health alert | OPS-03 | S |
| 10 | No Product/Offer/Breadcrumb JSON-LD on 5,900 PDPs | FE-S-01 | S–M |
| 11 | Rotate credentials that transited chat during setup (admin password, Hesabfa token); adopt a password manager | SEC-09 | S |
| 12 | README/API docs still describe quantity-based inventory the business abandoned | ARCH-03 | S |

### P2 — Medium (this quarter)

| # | Issue | ID |
|---|---|---|
| 13 | Gateway timeout marked as payment FAILED (should be UNKNOWN, retryable) | BE-03 |
| 14 | Lifecycle statuses stored as unconstrained text (orders, payments, movements) | DB-02 |
| 15 | JSONB spec filters bypass the GIN index (seq scans; rewrite to `@>` containment) | DB-03 |
| 16 | Search is `ILIKE '%…%'` with no pg_trgm index; no Persian char normalization (ی/ي، ک/ك) | DB-04 |
| 17 | "Priced ⇔ available" invariant enforced only by one-off scripts | DB-05 |
| 18 | Spec template JSONB has no versioning; global skeleton wrong for most categories | DB-08 |
| 19 | DB pool budget (20+10 per worker) can exceed Postgres max_connections | DB-09 |
| 20 | SSRF guard checks hostname literal, not resolved IPs (DNS rebinding gap) | SEC-01 |
| 21 | Body-size limit bypassable via chunked encoding — verify nginx `client_max_body_size` | SEC-02 |
| 22 | Shared step-up PIN across all super-admins (no attribution/rotation) | SEC-03/BE-06 |
| 23 | OTP hashes unsalted SHA-256 over 10⁶ space → use HMAC pepper | SEC-04 |
| 24 | CSRF depends solely on SameSite=lax; `none` is configurable without a token | SEC-05 |
| 25 | SVG allowed as product image extension (stored-XSS vector) | SEC-10 |
| 26 | Hesabfa invoice failures have no retry/re-push job — silent invoice loss | BE-07 |
| 27 | Background jobs live inside API process; no heartbeat | ARCH-01 |
| 28 | `scripts/` mixes pricing business logic with one-off crawlers, untested | ARCH-02 |
| 29 | Tax default divergence: constant says 9%, model default 0 | BE-09 |
| 30 | Spec-filter input not escaped/capped (robustness, minor DoS amplifier) | BE-05 |
| 31 | Product URLs are ID-only despite slugs existing (SEO) | FE-S-02 |
| 32 | Catalog PLP client-rendered only; server-prefetch page 1 | FE-S-03 |
| 33 | No dependency vulnerability scanning (pip/npm/actions) | OPS-05 |
| 34 | Run axe/keyboard accessibility pass on megamenu, filters, checkout, OTP login | FE-S-07 |
| 35 | Admin host lacks noindex/X-Robots-Tag + defense-in-depth on login | FE-A-03 |
| 36 | No E2E golden-path test (browse→cart→mock-pay→track) | QA-03 |
| 37 | Coverage gate dark zones: Hesabfa error paths, scripts excluded | QA-02 |

### P3 / P4 — Low (opportunistic)

Housekeeping indexes (DB-06), category self-loop CHECK (DB-07), email partial
unique (DB-11), alembic compare flags (DB-10), JWT iss/aud (SEC-06/BE-04),
CORS header narrowing (SEC-07), dev deps in prod image (OPS-06), migration-race
note (OPS-08), inline expiry sweeps in hot paths (BE-10), in-memory limiter
startup warning (BE-08), sitemap lastmod (FE-S-04), hardcoded site origin
(FE-S-05), static-vs-CMS articles (ARCH-04/FE-S-06), version identity (ARCH-08),
venv/naming hygiene (ARCH-07), test file naming (QA-04), ruff on scripts
(QA-05), admin middleware presence-check (FE-A-02), async-state consistency in
older admin tables (FE-A-04), web-vitals reporting (FE-S-08), mock-credentials
verification (SEC-08/FE-A-05).

## 4. Technical Debt Report

- **Deliberate, documented debt (healthy):** crud compat shims, `redirect_slashes=False` workaround, phase-named test files, single `product.router` aggregator. All documented in `ARCHITECTURE.md` — pay down opportunistically.
- **Accidental debt (needs owners):** `scripts/` sprawl with pricing logic (largest cluster), spec-template/JSONB drift, transaction-ownership inconsistency, stock-quantity legacy surface (deprecated column + endpoints + docs after the binary-availability pivot).
- **Debt interest currently being paid:** deploy-time discovery of frontend type errors; manual reconciliation of Hesabfa invoice failures; every doc reader mis-learning inventory semantics.

## 5–15. Roadmaps

### Refactoring roadmap (order matters)
1. Transaction ownership convention + lint enforcement (BE-01) — unblocks safe service composition.
2. Order-item snapshot migration (DB-01) — before order volume grows.
3. Scripts consolidation into `app/imports/` with tested price/markup helpers (ARCH-02).
4. Status CHECK constraints + enum policy doc (DB-02).
5. Job runner extraction (ARCH-01) — enables Hesabfa retry job (BE-07).

### Architecture roadmap
- Q3: job process split; real staging stack; version-from-git.
- Q4: import pipeline framework; spec-template versioning (DB-08); consider read-replica-ready session split only if traffic demands.

### Performance roadmap
- Now: pg_trgm indexes + Persian normalization (DB-04); pool budget fix (DB-09).
- Next: JSONB `@>` filter rewrite + hot-key expression indexes (DB-03); PLP server prefetch (FE-S-03); web-vitals monitoring (FE-S-08).
- Later: image CDN/caching review; Redis response caching for PLP facets.

### Security roadmap
- Week 1: rotate chat-transited secrets (SEC-09); nginx body-size verify (SEC-02); drop SVG (SEC-10).
- Month 1: OTP HMAC pepper (SEC-04); Origin-check middleware for cookie auth (SEC-05); SSRF resolve-time validation (SEC-01).
- Quarter: per-admin step-up credential (SEC-03); dependency scanning (OPS-05); JWT claims (SEC-06).

### UX roadmap
- Accessibility live pass (FE-S-07) → fix list; standardize async states in admin (FE-A-04); checkout error-message audit in Persian; empty-state copy review.

### SEO roadmap
- Product/Offer/Breadcrumb/Organization JSON-LD (FE-S-01) — highest ROI item in the entire report relative to effort.
- Slugged product URLs with 301s (FE-S-02); PLP SSR (FE-S-03); real sitemap lastmod (FE-S-04); staging noindex verification (FE-S-05); Search Console monitoring after each.

### DevOps roadmap
- Week 1: offsite backups + restore drill (OPS-02); runner heartbeat alert (OPS-03); uptime monitor + Sentry (OPS-07).
- Month 1: frontend CI gate (OPS-04); rename deploy-staging → deploy-live + smoke gate (OPS-01); Dependabot (OPS-05).
- Quarter: real staging environment; Prometheus/Grafana; image slimming (OPS-06).

## 16. Estimated implementation timeline

| Wave | Contents | Calendar (2-person team, ~50% allocation) |
|---|---|---|
| Wave 0 | P0 + SEC-09 + OPS-03 + OPS-07(min) | 1 week |
| Wave 1 | Remaining P1 (items 2–12) | 3–4 weeks |
| Wave 2 | P2 items 13–25 (integrity+security) | 4–6 weeks |
| Wave 3 | P2 items 26–37 (perf+SEO+testing) | 4–6 weeks |
| Wave 4 | P3/P4 opportunistic | ongoing |

## 17. Recommended implementation order

Wave 0 exactly as listed → then within Wave 1: OPS-04 (CI gate) *before* QA-01
(tests need the gate to matter), DB-01 *before* order volume grows, BE-01/BE-02
together (same code region), FE-S-01 anytime (independent).

## 18. Risks if nothing is changed

1. **Total data loss** on single disk failure (backups co-located) — existential.
2. **Silent production breakage** — no staging, no alerts, no frontend CI: the next regression is discovered by a customer.
3. **Accounting drift** — mutable order lines + unretried Hesabfa invoices compound into un-reconcilable books.
4. **Payment-state confusion** — timeout-as-failure misreports revenue events.
5. **Search collapse at scale** — seq-scan search/filters degrade UX as the catalog grows past ~20k SKUs.
6. **SEO ceiling** — without structured data the 5,900-product catalog competes with one hand tied.

## 19. Strengths of the project

1. Boot-time production-config validation (best-in-class for project size).
2. Payment pipeline: locking, idempotency, ledgers, allowlists, capability-token verify.
3. Session/auth architecture incl. the admin panel's memory+HttpOnly token client.
4. Risk-weighted backend test suite with an enforced coverage floor.
5. Correct SSR/hydration + complete metadata/sitemap/robots plumbing, native RTL.
6. Disciplined DB patterns: partial unique indexes, tz-aware triggers, hashed secrets at rest, `selectinload` hygiene.
7. Documentation culture (architecture, contracts, operations, refactor maps — and honest comments).
8. Scripted operations: bootstrap, deploy, smoke, restore, backup-cron installers.

## 20. Weaknesses of the project

1. Disaster-recovery posture (same-disk backups, no drills).
2. No environment separation; live site is the test bed.
3. Zero alerting/monitoring.
4. Frontend testing void.
5. Transaction-boundary inconsistency.
6. Catalog search/filter scalability.
7. Scripts folder as an unmanaged business-logic dump.
8. Single shared admin PIN; secrets-rotation discipline.

---

## Final question: *"What would senior engineers from Google, Shopify, Stripe, Cloudflare and Microsoft criticize first?"*

**The Stripe engineer** would go straight to `payment.py:281` — *"you catch bare
`Exception`, commit the transaction, and redirect the customer to a failure page
without logging. And a gateway timeout writes `failed` to your books. In
payments, unknown is a first-class state; you don't have it."* Then they'd
grudgingly admit the idempotency-reservation pattern is better than most
Series-B startups'.

**The Shopify engineer** would ask one question: *"When a merchant renames a
product, what happens to last month's invoices?"* — and the order-snapshot gap
(DB-01) plus the unretried Hesabfa pushes (BE-07) would be their whole review.
Commerce platforms live and die on order-line immutability. They'd also flag
5,900 PDPs with zero Product schema as leaving money on the table.

**The Google engineer (SRE hat)** wouldn't read the code at all. *"Where are
your backups? Same disk. Where's your alerting? Nowhere. What's your staging
environment? Production. This conversation is over until those change."* —
and they would be right to stop there. (The Google search-quality person would
add: client-rendered category pages and ID-only URLs throttle your crawl
efficiency.)

**The Cloudflare engineer** would probe the edges: the chunked-encoding
body-size bypass, the SSRF guard that trusts DNS, SVG uploads, and the single
VPS with no DDoS story in front of an Iranian e-commerce site. They'd
compliment the fail-closed rate limiter — most people fail open.

**The Microsoft engineer** would talk about sustainability: *"242 backend tests
and one frontend test means your quality culture has a hemisphere missing. Your
transaction semantics are whatever each file's author felt that day. And 35
scripts own your pricing. This is maintainable by exactly the two people who
wrote it — which is fine until it isn't."*

**Common thread:** none of them would call the code bad — several parts they
would call genuinely good. Every first criticism lands on the **operational
shell around the code**: recovery, environments, monitoring, and the frontend
testing void. That is where "world-class" is currently decided, and it is
almost all cheap to fix.
