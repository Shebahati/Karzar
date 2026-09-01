# HUMAN IMPLEMENTATION AUTHORIZATION — KARZAR LOCAL CHANGE BATCH V1

You are operating in Cursor Auto mode inside the Karzar repository. Execute this instruction once, locally, as one bounded implementation followed by one review and one final report. Do not create a recursive audit/correction loop and do not ask for a second approval gate.

This instruction is the explicit human authorization for the changes below. Use the repository's current risk-based workflow. Do **not** run the legacy mandatory AODS kickoff, prompt-selection ceremony, node/task/PMO/registry synchronization, or recursive audit workflow. Read relevant repository instructions and source code, but do not let obsolete orchestration prevent this bounded local implementation.

## Non-negotiable boundaries

- Work only in the currently opened local Karzar repository/worktree.
- Do not push, deploy, open a PR, call SSH, alter a server, or modify production/staging infrastructure.
- Do not call the live Hesabfa API or any other live write API.
- Do not commit unless the human asks in a later instruction.
- Preserve all existing user changes, including unrelated modified/untracked files.
- Never run destructive Git/file commands such as `git reset`, `git clean`, checkout/restore of user files, rebase, or blanket deletion.
- Do not stash or rewrite unrelated work to manufacture a clean tree.
- Do not delete orders, payments, products, categories, users, carts, remote ids, accounting records, or historical integration records.
- Do not hardcode fake statistics, fake sales, placeholder API results, invented Enamad identifiers, or guessed category mappings.
- Do not replace real API failures with silent zero/empty responses.
- Do not pause after planning. After read-only preflight, emit a concise RESTATE and PLAN, then implement. Pause only for a genuinely impossible local prerequisite; otherwise complete all unblocked work and list a narrowly defined blocker in the final report.

## Source package

The repository root must contain:

- `karzar-site-change-pack-v1/CONTENT_AND_RULES.md`
- `karzar-site-change-pack-v1/TARGET_TAXONOMY.md`
- `karzar-site-change-pack-v1/assets/heroes/desktop/*.png`
- `karzar-site-change-pack-v1/assets/heroes/mobile/*.png`
- `karzar-site-change-pack-v1/enamad-snippet.html` (official snippet supplied by the human)

Treat `CONTENT_AND_RULES.md` and `TARGET_TAXONOMY.md` as authoritative product/content specifications. Read both completely before editing.

If `enamad-snippet.html` is absent, complete every other task and implement the footer slot/component without fabricating an identifier or validation URL; report only the missing official snippet as a final blocker.

## Phase 0 — read-only preflight

1. Run `git status --short --branch` and record the current branch and pre-existing changes.
2. Locate and read applicable `AGENTS.md`, `.cursor` rules/skills, project README, package manifests, Python configuration, Docker/Compose files, environment examples, migration conventions, test commands, frontend architecture, backend architecture, admin routes, and current Hesabfa integration.
3. Identify the actual Storefront/admin/backend roots. Do not assume paths when the repository provides them.
4. Trace before editing:
   - hero slide data/component/assets and responsive CSS;
   - shared navigation/footer/contact configuration and JSON-LD;
   - About and Contact pages;
   - product availability/image fields and every public product-list query;
   - category schema, slugs, product assignments, filters and sitemap generation;
   - admin dashboard sales calculation;
   - open orders and quotes APIs plus frontend consumers;
   - customer/user APIs and admin authorization;
   - cart persistence and conversion to orders;
   - all Hesabfa clients, hooks, signals, tasks, schedules, webhooks and mappings.
5. Capture focused baseline tests/behavior where practical. Do not run a broad expensive suite before targeted work.

## Phase 1 — import and implement the six art-directed heroes

Use all six desktop/mobile pairs defined in `CONTENT_AND_RULES.md` and no rejected/intermediate images.

1. Copy source masters into the repository's canonical public asset structure with stable descriptive names.
2. Use the project's existing image pipeline. Generate WebP/AVIF derivatives if the existing stack supports them; keep appropriate fallbacks.
3. Implement art direction with `<picture>/<source media>` or the framework's equivalent so mobile loads the mobile asset and desktop loads the desktop asset. Do not merely crop the desktop image on mobile.
4. Keep all copy, logo, category controls and CTA buttons as accessible HTML. Never place UI text into image pixels.
5. Resolve existing category/discount routes from repository data. Do not invent slugs.
6. Preserve the current slider's useful behavior while fixing responsive layout. Use one semantic H1 for the page; slide headings after the primary heading must respect heading hierarchy.
7. First visible hero: eager/high-priority load. Other slides: lazy/deferred where the framework permits. Set intrinsic dimensions/aspect ratio and responsive `sizes` to prevent layout shift.
8. Ensure overlays maintain readable contrast without crushing image detail. Avoid a blanket opacity that makes every image muddy.
9. Respect `prefers-reduced-motion`; stop or simplify autoplay/transition accordingly.
10. Ensure touch/swipe/arrows/dots and focus states remain usable if those controls already exist.

Responsive acceptance viewports:

- mobile: 320×568, 360×800, 390×844, 412×915, 430×932;
- tablet: 768×1024;
- desktop: 1024×768, 1280×720, 1440×900, 1920×1080.

At every viewport: no horizontal overflow, no clipped headline/CTA, no navigation collision, no important tool cropped, no category-control collision, no unreadable contrast, and no cumulative layout shift introduced by missing image dimensions.

## Phase 2 — public content, navigation, About, Contact and Enamad

1. Apply the global label changes `درباره` → `درباره ما` and `تماس` → `تماس با ما` wherever those are navigation labels. Do not rename routes just for visible copy.
2. Rebuild the About page using the exact approved content in `CONTENT_AND_RULES.md`.
3. Remove the whole statistics/brand-overview block and the whole history/timeline section. Remove no global authenticity promise; only the numerical About card is removed.
4. Use the existing official Karzar logo opposite the About H1 on desktop and stacked cleanly on mobile.
5. Apply landline/mobile information globally from the authoritative spec, including correct `tel:` links and structured data. Preserve email, address, map, social links and support form.
6. Add the official Enamad badge to the footer using the exact human-supplied snippet. Make it keyboard accessible, responsive, visually integrated, and linked to official validation. Do not alter its official validation target, id, code or required attributes. If the snippet uses unsafe/deprecated markup, wrap it minimally without changing its verification semantics.

## Phase 3 — public product visibility and ordering

Implement the exact rules in sections 5 and 6 of `CONTENT_AND_RULES.md`.

1. Determine the canonical two-state availability field/enum. Do not derive stock from price.
2. Make availability the primary ordering partition on every public product list; apply the user's selected sort within each partition.
3. Implement this at the server/query/service layer so pagination does not put unavailable products before available products on later pages.
4. Hide products without a valid real public image from all public rendering/SEO surfaces while preserving them in DB/admin.
5. Centralize the public-image eligibility predicate/query helper to prevent drift among endpoints.
6. Add regression tests for pagination, each supported sort, available/unavailable ties, missing image, placeholder image, direct product access, related products, sitemap, and restoration of visibility after adding an image.

## Phase 4 — website taxonomy and safe local migration

Implement the taxonomy in `TARGET_TAXONOMY.md`, maximum depth four.

1. Audit current categories and actual products first.
2. Reuse existing categories/ids whose semantics already match. Do not blindly delete and recreate the tree.
3. Categories are product/operation concepts; keep brands/specifications as filters.
4. Create only branches that have products; keep empty future branches out of public navigation.
5. Migrate deterministic current categories and product assignments to the closest defensible target nodes.
6. Preserve one canonical product URL and breadcrumb. Add permanent redirects for changed public category slugs/URLs using the project's routing/redirect mechanism.
7. Never hide or delete a product because automatic classification is ambiguous. Preserve it under the nearest defensible broad/legacy category and write a focused CSV to `work/reports/catalog-taxonomy-unresolved.csv` with product id, title, old category, proposed candidates and reason.
8. Ensure category pages, counts, filters, sitemap, breadcrumbs and admin category selection use the resulting tree.
9. Add cycle prevention, max-depth validation, unique/stable slug behavior, and migration rollback according to project conventions.
10. Add tests for tree depth, redirects, category counts, product assignment, hidden no-image products, and public navigation.

## Phase 5 — admin functional corrections

### Sales metric

- Trace and repair the real calculation. It must represent net successfully paid website sales only.
- Do not hardcode zero. With current production-equivalent site data it should naturally be zero because the website has no completed sale.
- Exclude Hesabfa turnover, quotes, abandoned carts, failed/unpaid/cancelled orders, refunds as required, seed/test fixtures and unrelated accounting data.
- Add service/API/UI tests.

### Open orders and quotes

- Repair backend and frontend contracts together.
- Use canonical workflow enums for open vs terminal states.
- Correct loading, empty, error and stale-state behavior; surface genuine errors.
- Add contract/regression tests for counts and list contents.
- Move both menu entries under `فروش و مالی` without breaking routes or deep links.

### Users versus customers

- Inspect actual behavior rather than guessing.
- If `مشتریان` includes every registered user including zero-order accounts, retain it and make coverage/count labeling explicit; do not create a duplicate module.
- Otherwise add a secure `کاربران` API/page/menu entry listing all registered website accounts regardless of orders, and retain `مشتریان` for order/customer analytics.
- Never expose password/token/secret fields. Enforce existing admin permissions.

### Abandoned carts

- Implement the exact authenticated-user, non-empty, ≥24-hour inactive, non-converted, non-cleared rule from `CONTENT_AND_RULES.md`.
- Add `سبدهای رهاشده` as a separate page under `فروش و مالی`, not as an order status.
- Show customer, item count, current value, last activity and safe detail view using existing data only.
- Do not add tracking, guest fingerprinting, automated messages, or external marketing calls.
- Add timezone-safe query/API/UI tests and ensure conversion to an order immediately removes the cart from this view.

## Phase 6 — disable Hesabfa safely and add independent mapping metadata

1. Inventory all integration entry points and choose one central, explicit feature flag/config gate such as the existing canonical setting or `HESABFA_SYNC_ENABLED` if no equivalent exists.
2. Default local/example configuration to disabled. Do not commit real secrets and do not overwrite a user's secret-bearing `.env` file.
3. While disabled, prevent every scheduled/manual/event-driven product, category, inventory, price, customer, order and invoice synchronization call before network transmission.
4. Preserve integration implementation, credentials schema, historical logs, remote ids and mappings. Do not remove or null remote ids.
5. Do not send remote delete/deactivate calls. Existing products/categories in Hesabfa must remain unchanged.
6. Ensure scheduled jobs/workers do not repeatedly fail/noise while disabled; use a clear skipped/disabled result and safe logs without secrets.
7. Preserve webhook security. If inbound webhooks exist, follow current contract and choose a safe disabled response without mutating local/remote data; do not weaken signature verification.
8. Add local mapping persistence:
   - each website category: zero/one default Hesabfa category reference;
   - many website categories may reference the same Hesabfa category;
   - optional product-level override;
   - product override wins;
   - mapping changes while disabled cause no network request.
9. Reuse existing tables/fields when possible. If schema changes are required, create reversible migrations and admin controls consistent with project conventions.
10. Do not alter the website taxonomy to mirror Hesabfa and do not alter Hesabfa categories.
11. Do not activate live Hesabfa products in this execution. Produce no live dry-run that requires remote access. Record this as intentionally deferred external work, not an implementation failure.
12. Add tests proving disabled mode performs zero outbound calls and zero destructive side effects while preserving ids/mappings.

## Phase 7 — coherent admin UI/UX redesign

Do this after functional fixes so visuals do not mask broken behavior.

1. Derive tokens from the existing storefront: Karzar red, graphite/neutral palette, typography, radii, spacing, elevation, focus treatment and official logo.
2. Build/reuse a small admin design system rather than page-specific duplicated CSS: shell, sidebar, header, breadcrumbs, cards, KPI cards, tables, filters, forms, buttons, status badges, tabs, empty/loading/error states, dialogs, pagination and toasts.
3. Apply it coherently to all existing admin routes, including the corrected sales/finance pages, users/customers, carts and category mapping surfaces.
4. Keep the admin operational and information-dense; do not turn it into a marketing page.
5. Desktop-first but responsive: usable at 1280/1440/1920, tablet, and mobile emergency workflows. Tables must have an intentional responsive/scroll strategy, not clipped columns.
6. Preserve keyboard navigation, visible focus, semantic headings/landmarks, labels, contrast and RTL behavior.
7. Preserve route behavior, permissions and functionality. Do not replace real controls with decorative mockups.

## Phase 8 — targeted validation, one review, and local startup

Run targeted checks first, then the smallest appropriate broader gates already defined by the repository.

Required validation areas:

- backend unit/integration/API tests for product queries, categories, metrics, orders, quotes, users, carts and Hesabfa disabled mode;
- frontend/admin unit/component tests where present;
- typecheck and lint for touched packages;
- production builds for storefront and admin;
- migration validation/rollback check in a disposable local/test DB using repository conventions—never production data;
- responsive visual/e2e checks for the specified hero viewports and key About/Contact/admin pages;
- focused security check for admin authorization, PII fields, webhook verification and absence of secrets;
- `git diff --check` and one final focused diff review.

Then start the local development stack so the human can inspect it:

1. Detect and use the repository's documented local setup (Compose/dev scripts/package scripts). Do not invent commands before inspection.
2. Use only local/development configuration and databases. Never point local services to production/staging DB, Redis, object storage, payment, Hesabfa or other write services.
3. Apply required migrations to the local development DB without wiping existing local user data.
4. Start backend, storefront and admin in non-blocking/background mode using the project's supported method.
5. Verify health endpoints/pages and report exact local URLs and ports.
6. If a missing local dependency or environment value prevents startup, complete code/tests/builds that do not require it and report the one exact command/value needed. Do not request or print secrets.

## Final response format — once only

Return one concise but complete report containing:

1. pre-existing worktree state and confirmation it was preserved;
2. implementation summary grouped by Storefront, Catalog, Admin, and Hesabfa;
3. whether `مشتریان` included zero-order registered users and what you implemented;
4. actual root cause of the zero-sales/open-orders/open-quotes issues;
5. database migrations and rollback notes;
6. files changed/added, grouped by subsystem;
7. exact tests/typechecks/lints/builds run with pass/fail counts;
8. local URLs for storefront, admin and API plus process/container status;
9. unresolved taxonomy CSV count, if any;
10. narrowly defined remaining blockers only;
11. confirmation: no commit, push, deploy, SSH, server mutation, live Hesabfa call, or remote deletion occurred.

Do not launch another review/correction cycle after this report.
