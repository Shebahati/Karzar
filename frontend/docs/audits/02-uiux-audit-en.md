# UI / UX & User-Flow Audit — Detailed English Technical Report

**Date:** 17 July 2026  
**Scope:** `karzar-frontend/Storefront` + `karzar-frontend/admin-panel`  
**Method:** Static code audit of App Router pages, view components, forms, empty/error/loading states, navigation shells, and end-to-end flows. Not a live browser session.  
**Companion:** Simple Persian summary → `02-uiux-audit-fa.md`

**Severity scale**
| Level | Meaning |
|-------|---------|
| **Critical** | Blocks trust, dead-ends money flow, or fabricates success |
| **High** | Major friction, incomplete primary journey, or serious ambiguity |
| **Medium** | Recoverable confusion / missing polish / incomplete secondary path |
| **Low** | Nice-to-have consistency / visual / a11y |

---

## 0. Architecture & mental model

| App | Primary routes |
|-----|----------------|
| Storefront | `/`, `/catalog`, `/product/[id]`, `/cart`, `/quote`, `/checkout` (+ success/callback/failed), `/login`, `/account/orders`, `/blog`, `/blog/[slug]`, `/contact`, `/about` |
| Admin | `/login`, `/`, catalog CRUD, `/orders`, `/orders/[id]`, `/quotes`, `/customers`, `/cms/*`, `/reports`, `/documents`, `/settings` |

**Core commerce model:** two lanes  
1. **Purchase lane** — priced SKUs → `/cart` → checkout `mode=purchase` → payment  
2. **Inquiry lane** — unpriced SKUs → `/quote` → checkout `mode=inquiry` (quote / pre-invoice)

Implemented across `TwoLaneActions`, Zustand cart store, `CartView`, `CheckoutView`. This model is a **strength**; most UX debt is incomplete feedback, missing pagination, thin account area, and a few fake successes.

RTL: `lang="fa" dir="rtl"` on Storefront root. Admin also Persian RTL.

---

## 1. Cross-cutting findings

| Sev | Category | Finding | Evidence / impact |
|-----|----------|---------|-------------------|
| High | Incomplete | No app-level `error.tsx` / `not-found.tsx` in either app | Users see Next defaults on crashes / bad URLs |
| Medium | Weak | Placeholder contact identity (`support@karzar.example`, `۰۲۱-۱۲۳۴۵۶۷۸`, generic map) | Trust damage on Contact + Footer |
| Medium | Weak | Picsum fallbacks when product images missing | Looks unfinished in production |
| Low | RTL | Breadcrumbs use `ChevronLeft`; category crumbs often **not links** | Navigation dead text |
| Low | Strength | `tnum`, `toPersianDigits`, `formatToman` widely used | Keep consistent on all money/qty |

---

# PART A — STOREFRONT FLOWS

---

## A1. Home (`/`)

### Incomplete
| Sev | Issue | Detail |
|-----|-------|--------|
| High | “پیشنهادهای ویژه” is not a discount API feed | Loads `sort: "newest"` then client-filters `discount_percent`; carousel can be silently empty |
| Medium | Empty CMS hero → `Hero` returns `null` | First viewport collapses; brand-forward hero missing |
| Low | Stats strip static | Marketing OK if labeled; currently reads as “facts” |

### Weak
| Sev | Issue |
|-----|-------|
| Medium | Trust chips overlaid on hero media compete with CMS CTA |
| Low | Brand strip is text-only (no logos) — weak B2B brand recognition |

### Improvements
- Dedicated discounted-products query/sort; empty state with CTA to `/catalog`
- Brand fallback hero when no slides (logo + one H1 + one CTA)
- Move trust claims below fold into FeatureStrip / WhyKarzar

### UI design suggestions
- Full-bleed CMS hero as the brand plane; avoid badge clutter on media
- Carousel: skeleton → empty message (never silent blank grid)
- Prefer industrial / workshop photography as section anchors over more stat chips

---

## A2. Catalog & search (`/catalog`)

### Incomplete
| Sev | Issue | Detail |
|-----|-------|--------|
| **Critical** | **No pagination / infinite scroll** | Always `limit: 24`; `meta.total_count` shown but unreachable |
| High | Empty state has no “clear filters” action | Copy only |
| High | **No mobile search** | Header search `hidden md:flex`; bottom nav lacks search |
| Medium | No dedicated fetch-error state | Loading/empty only |
| Medium | Search lacks results chrome | No “results for X”, clear-search chip |

### Weak
| Sev | Issue |
|-----|-------|
| Medium | Slug→ID resolve failures swallowed — filter appears “applied” in URL but ignored |
| Low | H1 always “فروشگاه ابزار” — ignores active category/brand/search |

### Improvements
- Pagination or load-more bound to `meta`
- Mobile sticky search or drawer synced to `?search=`
- Active filter chips + clear-all on empty
- Debounced search / recent queries

### UI design suggestions
- Dense B2B toolbar: result count + sort + chips on one sticky row
- Keep 2-col mobile grid; surface technical_specs as removable chips under H1
- Spec filters are a V1 strength — make them visible when active

---

## A3. Product detail (`/product/[id]`)

### Incomplete
| Sev | Issue | Detail |
|-----|-------|--------|
| **Critical** | SMS quick-inquiry is **fake** | Phone length ≥10 → `setDone(true)`; no API |
| High | Add-to-cart/quote has **no toast/sheet/CTA** | Only badge count changes |
| High | Heart on `ProductCard` decorative | Implies wishlist without behavior |
| Medium | Rating hardcoded `۴.۷` | Ignores real comment ratings |
| Medium | “Related articles” reuses global articles section | Not product-scoped |
| Low | Breadcrumb segments not clickable | |

### Weak
| Sev | Issue |
|-----|-------|
| High | Long two-lane CTA labels wrap badly on mobile; mental model unexplained once |
| Medium | Always-on “۷ روز ضمانت بازگشت” may be policy-false per SKU |
| Medium | Comments require login but no login link — muted text only |
| Low | Gallery lacks zoom/lightbox |

### Improvements
- Wire or remove SMS inquiry — never fabricate success
- Post-add confirmation sheet: lane, qty, go to cart/quote/checkout
- Average rating from comments; hide stars if none
- Sticky mobile buy bar above bottom nav

### UI design suggestions
- Split price/availability from qty+CTA; SMS as text link if retained
- For inquiry SKUs, match `/quote` visual token (neutral/dark primary)
- Show lead time / qty nuance for `low_stock`, not badge-only

---

## A4. Cart (`/cart`)

### Incomplete
| Sev | Issue |
|-----|-------|
| High | “خالی کردن” clears with **no confirm** |
| Medium | No line stock revalidation before checkout — stale Zustand risk |
| Medium | Summary is subtotal only — no shipping/tax/discount lines (even zero) |
| Low | No cross-sell on empty/full cart |

### Weak
| Sev | Issue |
|-----|-------|
| Medium | CTA “ادامه فرآیند خرید” vague vs “تکمیل خرید / پرداخت” |

### Improvements
- Confirm clear; undo snackbar on remove
- Unit price + line total + SKU under title
- Soft gate when lines become unavailable

### UI design suggestions
- Desktop: lines left, sticky summary right; primary red CTA + secondary continue shopping
- Ensure last CTA clear of mobile bottom nav (`pb-24` pattern)

---

## A5. Quote basket (`/quote`)

### Incomplete
| Sev | Issue |
|-----|-------|
| Medium | Mobile bottom nav “استعلام” has **no badge** (cart does) |
| Low | Restored-inquiry banner cannot be permanently dismissed |

### Weak
| Sev | Issue |
|-----|-------|
| Medium | Footer “استعلام قیمت” links to `/catalog` **not** `/quote` |
| Low | Dual baskets unexplained — cognitive load |

### Improvements
- First-add explainer: “این کالا قیمت ثابت ندارد…”
- Badge on mobile quote tab
- Fix footer link

### UI design suggestions
- Quote page header stripe using same token as inquiry CTA
- After restore, pulse primary CTA toward submit inquiry

---

## A6. Checkout (`/checkout`)

### Incomplete
| Sev | Issue | Detail |
|-----|-------|--------|
| **Critical** | Test OTP shown in UI | `کد تست: 11111` in auth step copy |
| High | Stepper step 3 (“done”) never activates in-place | Redirect to gateway/success — progress lies |
| High | Order created + payment init fails | Error only; **no tracking code + retry pay**; cart may remain |
| Medium | Form `defaultValues` set once | Post-OTP `customer` may not populate name/phone without remount |
| Medium | Province/city free-text | Error-prone Iranian addresses |
| Low | Suspense fallback empty Container | Blank flash |

### Weak
| Sev | Issue |
|-----|-------|
| High | Purchase forces login — messaging abrupt for guests arriving from cart |
| Medium | “جمع کل” and “مبلغ قابل پرداخت” identical with no fee line |
| Medium | Back from details always returns to auth even if already logged in |

### Improvements
- Gate test OTP behind `USE_MOCK` / env — never production
- On payment-init failure: show tracking + “پرداخت مجدد”
- Collapse stepper for logged-in users (already skip to details if token — extend)
- Address book / last shipping for returning users

### UI design suggestions
- Mobile: collapsible order summary above form (“اقلام N”)
- Purchase CTA label: «انتقال به درگاه پرداخت»
- Inquiry: keep company + note; optional preferred contact window later

---

## A7. Payment callback / failed / success

### Incomplete
| Sev | Issue |
|-----|-------|
| High | Callback depends on `sessionStorage` pending order — new tab / cleared storage = weak recovery |
| Medium | Unpaid purchase success copy “سفارش ثبت شد” ambiguous vs awaiting payment |
| Medium | Inquiry success CTA → `/quote` (empty after clear) — wrong next step |
| Low | Failed page structure OK |

### Weak
| Sev | Issue |
|-----|-------|
| Medium | “سفارش‌های من” uses Call icon — wrong metaphor |
| Low | Fallback ref `KZ-000000` if missing — fake chrome |

### Improvements
- Persist pending payment by authority server-side or durable storage
- Success: copy tracking, share, continue shopping
- Inquiry success: track/contact CTAs, not empty quote basket

### UI design suggestions
- Keep motion + timeline; add printable B2B receipt block
- Failed: real support phone once configured

---

## A8. Auth / OTP (`/login`)

### Incomplete
| Sev | Issue | Detail |
|-----|-------|--------|
| **Critical** | **`?next=` ignored** | `api-client` / MyOrders redirect to `/login?next=…` but success always `router.push("/")` |
| High | No `?expired=1` banner | Admin login has this; storefront does not |
| Medium | No profile completion after first OTP | Name empty until checkout |
| Medium | “قوانین و مقررات” → `/about` | Not a legal page |

### Weak
| Sev | Issue |
|-----|-------|
| Medium | Phone field centered + tracking-widest + start icon — awkward RTL |
| Low | OTP boxes `dir="ltr"` — correct; unify with checkout single-field OTP |

### Improvements
- Honor safe relative `next` paths
- Soft prompt for `full_name` after first login
- Full-OTP paste support

### UI design suggestions
- Centered card + subtle industrial texture (avoid purple AI clichés)
- Unify OTP UX between login and checkout

---

## A9. Account / orders (`/account/orders`)

### Incomplete
| Sev | Issue |
|-----|-------|
| **Critical** | Account = orders list only | No profile, addresses, inquiries, tickets; logout mainly desktop header |
| High | “جزئیات” → `/checkout/success?ref=…` | Reuses celebration success UI for historical orders; no `/account/orders/[id]` |
| Medium | Unauth `return null` while redirecting | Blank flash |
| Medium | No status/mode filters | Purchase vs inquiry unlabeled |

### Weak
| Sev | Issue |
|-----|-------|
| High | Header shows user name as if full account → only orders |
| Medium | Mobile: no logout in account/bottom nav |

### Improvements
- Account hub: سفارش‌ها / استعلام‌ها / پروفایل / خروج
- Dedicated order detail with `OrderTimeline` without success hero
- Mode badge, payment status, item count, first-item thumbnail

---

## A10. Blog / Contact / About / Shell

### Blog
| Sev | Category | Issue |
|-----|----------|-------|
| Medium | Incomplete | List: skeletons but **no empty state** for `[]` |
| Medium | Incomplete | No fetch error state |
| Low | Improvement | Tag filters; ensure article related-products from CMS are rendered |

### Contact
| Sev | Category | Issue |
|-----|----------|-------|
| High | Incomplete | Success UI exists; **no submit error handling** |
| Medium | Weak | Placeholder phone/email/map |
| Low | Improvement | Copy ticket code button |

### About
| Sev | Category | Issue |
|-----|----------|-------|
| Low | Weak | Fine as marketing; incorrectly reused as Terms |
| Low | UI | Inset hero OK for About; keep brand dominant |

### Navigation shell
| Sev | Category | Issue |
|-----|----------|-------|
| High | Incomplete | Mobile: no search, no logout, blog/about/contact only in footer |
| Medium | Weak | Dual cart icons unlabeled; Document icon for quote may confuse |
| Medium | Weak | Mega menu vs mobile category depth parity |
| Low | Improvement | Keyboard/focus for mega menu |

---

# PART B — ADMIN PANEL FLOWS

---

## B1. Login

| Sev | Category | Issue |
|-----|----------|-------|
| **Critical** | Incomplete | Mock credentials printed in UI (`09120000000 / Admin@123456`) |
| High | Incomplete | Phone prefilled with mock number |
| Medium | Weak | Password optional when local setting disables require-password — dangerous if mis-shipped |
| Medium | Weak | Logo is letter “ک” — weaker than Storefront `Logo` |
| Low | Strength | `next` redirect works (parity target for storefront) |

**UI:** Full-bleed muted workshop behind compact form; strip emoji from dashboard welcome for professional ops tone.

---

## B2. Dashboard

| Sev | Category | Issue |
|-----|----------|-------|
| High | Incomplete | Stats from **products sample only** — no pending orders/revenue/open inquiries |
| High | Weak | “ارزش موجودی” sums `base_price` without qty — misleading |
| Medium | Weak | OOS list not linked to product edit |
| Medium | Improvement | Surface Reports’ “نیازمند اقدام” on dashboard |

---

## B3. Products / categories

| Sev | Category | Issue |
|-----|----------|-------|
| High | Incomplete | Product list `limit: 50` — same pagination gap |
| Medium | Incomplete | Heavy create/edit — no wizard, draft, or “view on storefront” |
| Medium | Weak | “فیلتر پیشرفته” overclaims (search/category/brand only) |
| Low | Strength | Soft-delete + restore bin + step-up PIN |
| Medium | Improvement | Category columns UX solid; brands modal discoverability low |

**UI:** Thumbnail column; sticky edit header; explicit toggle «قیمت‌گذاری / استعلامی» instead of “empty price = inquiry” only as hint.

---

## B4. Orders / quotes / refunds

### Strengths
- Detail workflow: status stepper, invoice, ship dialog, quote dialog, cancel/refund + `StepUpDialog`
- Quotes page separates inquiry mode well when used

### Gaps
| Sev | Category | Issue |
|-----|----------|-------|
| High | Improvement | Force `mode=purchase` on `/orders` or tabs خرید/استعلام |
| Medium | Incomplete | No dedicated refunds queue — only from order panel |
| Medium | Weak | Refund is full-order only — no partial amount UI |
| Medium | Weak | Empty state doesn’t distinguish filters vs truly empty |
| Medium | Improvement | Customer phone → call / link to `/customers/[id]`; SLA age on quotes |
| Low | Incomplete | Detail not-found is plain text |

---

## B5. Customers / CMS

| Sev | Category | Issue |
|-----|----------|-------|
| Medium | Incomplete | No create-customer (OK if OTP-only — say so in empty state) |
| Medium | Improvement | List: LTV / last order date |
| Low | Weak | Step-up on save needs copy explaining why |
| **High** | Incomplete | Contacts: list-only — no read/replied/archive |
| **High** | Incomplete | Comments: delete-only — no approve/reject; storefront publishes immediately |
| Medium | Weak | Comments filter by raw product ID not name |
| Medium | Improvement | Hero preview matching storefront overlays |

---

## B6. Reports / Documents / Settings

| Sev | Category | Issue |
|-----|----------|-------|
| High | Weak | Reports = client aggregate `limit: 200` — **not analytics** |
| **Critical** | Incomplete | Documents 100% mock — upload/download stubs |
| High | Weak | Settings in `localStorage` — shop name/phone/inquiry flag **do not drive Storefront** |
| Medium | Improvement | Missing shipping fees, gateway status, SMS provider health |

**Recommendation:** Remove Documents from nav or label «به‌زودی»; implement server settings or stop implying global control.

---

## B7. Admin shell

| Sev | Category | Issue |
|-----|----------|-------|
| Medium | Improvement | Verify mobile sidebar drawer collapse (`ps-72`) |
| Medium | Weak | No jump-to-order-by-tracking command |
| Low | a11y | Prefer visible labels on icon-only controls |

---

# PART C — RTL / Persian checklist

| Topic | Status | Notes |
|-------|--------|-------|
| `dir="rtl"` / `lang="fa"` | Good | Storefront |
| Logical props (`ps`/`pe`/`start`/`end`) | Mostly good | |
| Digits / تومان | Mostly good | Enforce everywhere |
| OTP LTR digits | Intentional | Unify patterns |
| Phone fields | Mixed | Prefer `dir="ltr"` + `text-start` |
| Chevron “next” | Review | Left in RTL often OK; validate with users |
| Tone | B2B industrial | Avoid dashboard emoji; avoid purple/glow AI defaults |

---

# PART D — Priority roadmap

### P0 — Critical
1. Honor storefront login `?next=`  
2. Remove test OTP from checkout UI (env-gate)  
3. Remove or wire fake SMS inquiry  
4. Catalog (+ admin product list) pagination  
5. Strip admin mock credentials from non-dev builds  
6. Don’t ship Documents as real nav — or label coming soon  

### P1 — High
7. Account hub + real order detail (not success page)  
8. Add-to-cart feedback; mobile search  
9. Payment-init failure recovery with tracking + retry  
10. Contact form error state; CMS contacts/comments depth  
11. Settings/backend sync or honest labeling; dashboard order KPIs  
12. Fix footer inquiry link → `/quote`  

### P2 — Medium
13. Real discount feed; real PDP rating; remove or implement wishlist  
14. Address picker; clear-cart confirm; quote mobile badge  
15. Orders list mode tabs; real reports API  
16. Blog/catalog empty & error states  

---

# PART E — What’s already strong

- Clear **two-lane** commerce (priced vs inquiry) with separate baskets  
- Guest **cannot** pay for purchase without OTP/login  
- Payment verify callback with loading / success / failed  
- Success **OrderTimeline** pattern  
- Admin fulfillment: ship / quote / cancel / refund + step-up PIN  
- Catalog filters (category, brand, country, price, stock, technical specs) unusually complete for V1  
- Thoughtful Persian numeric formatting  
- Soft-delete products + deleted bin  

---

# PART F — Suggested design system directions (UI)

1. **Tokens:** Define industrial palette (steel, oil-blue or deep green accent — not purple-indigo). CSS variables for surface, ink, accent, danger, inquiry-neutral.  
2. **Type:** Keep expressive Persian display for brand moments; UI body with strong numeral (`tnum`) support. Avoid Inter/Roboto defaults if introducing new faces.  
3. **Composition:** Home first viewport = brand + one headline + one sentence + one CTA group + full-bleed hero — already close; remove overlay chips.  
4. **Cards:** Prefer list/table density for admin; storefront cards OK for PLP but avoid card-in-card nesting.  
5. **Motion:** 2–3 intentional motions only (hero crossfade, success check, add-to-cart sheet) — not ambient glow noise.  
6. **Admin density:** Ops-first tables, sticky action columns, status badge color map per `OrderStatus`.  
7. **Empty states:** Illustration-light, one sentence, one primary action (clear filters / go catalog / create product).  

---

*Audit based on component and route source in this workspace. Backend constraints (stock checks, comment visibility rules) may add further UX constraints not visible in FE alone.*

---

# PART G — Specialist redesign appendix (deep design system, flows, visual bugs)

> Expert addendum: beyond issue inventory. Industrial B2B tools brand (Karzar red `#C22026`, Persian RTL, dual purchase/RFQ lanes). File-level proposals map to current Storefront + admin-panel code.

---

## G1. Brand diagnosis

The token layer is coherent and **not** generic purple. The UI still reads as a **soft consumer glass shell** (glassmorphism, primary glow, mid-gray type, pink accent washes) rather than a workshop-grade procurement tool.

| Problem | Files | User effect |
|---------|-------|-------------|
| `--foreground` mid-gray (~31% / `#4F4F4F`) | both `globals.css` | Titles/prices lack authority; dense tables under-contrast |
| `--primary` ≡ `--destructive` (same red) | both `globals.css` | Cancel/errors look like brand CTAs |
| `--accent` washed pink | both `globals.css` | Retail “candy” selected states |
| `shadow-primary-glow` on primary buttons | `tailwind.config.ts`, `button.tsx` | Soft SaaS glow vs industrial honesty |
| `bg-hero-glow` radial red | `globals.css`, home/about | Decorative fog, no product atmosphere |
| Hero inset `rounded-3xl` + on-image trust pills | `home/hero.tsx`, `page.tsx` | First viewport is card clutter, not brand plane |
| Admin “ک” tile vs Storefront PNG logo | `sidebar.tsx`, `login-form.tsx` vs `logo.tsx` | Split brand identity |
| IRANYekan loaded 300–700 but UI mostly `font-bold` | headers, filters, badges | Hierarchy collapses into one shouty register |
| Storefront `rounded-xl` vs admin `rounded-lg` | buttons | Two surface languages for one brand |

**North star:** brushed steel, packing-label typography, 8–10px radii, hairline rules. **Red = brand & go.** **Steel/ink = structure & RFQ.** **Oxide = danger.** No perpetual glow; no purple gradients.

---

## G2. Design-system changes (do first — unlocks every screen)

1. Add `--ink` (~12–16% lightness) for titles and prices; keep muted for captions only.  
2. Split destructive from primary (cooler rust/oxide or charcoal + red text).  
3. Retune accent to cool steel (`~210 12% 94%`); red only for active/purchase.  
4. Remove default button glow; use flat soft shadow or 1px inset edge.  
5. Type roles: `display` / `title` / `body` / `meta` / `price` (tabular + ink). Default weight **500**; bold for page titles + primary CTAs only.  
6. Unify radii to ~8–10px across apps.  
7. Header: near-opaque `bg-card/95` + 1px hairline — retire glass for chrome.  
8. Replace hero red radial with graphite grain / workshop photo wash or nothing.

---

## G3. Component redesigns (visually weak or buggy)

### Logo — `Storefront/.../logo.tsx` (+ admin parity)
- Promote wordmark “کارزار”; demote “ابزار صنعتی” to footer-only or smaller.  
- Replace admin letter tile with the same logo asset.

### SiteHeader — `site-header.tsx`
- Labels under dual-lane icons: «سبد» / «استعلام»; distinct badge tones (red vs steel).  
- Mobile search entry (icon → full-width overlay) — bottom nav has none.  
- Logged-in control → «سفارش‌ها» or account sheet — not a fake full profile.

### MobileBottomNav — `mobile-bottom-nav.tsx`
- Badge on استعلام; optional search affordance.  
- Active = ink bar + red icon; reduce label boldness.  
- Category sheet OK; add clear path to `/catalog`.

### SiteFooter — `site-footer.tsx`
- Fix «استعلام قیمت» → `/quote` (currently `/catalog`).  
- Real contact or omit placeholders; drop heart emoji copyright line; collapse pill trust cluster to one quiet line.

### Home — `hero.tsx` + `page.tsx` + strips
- Edge-to-edge / less “card hero”; **remove on-image Shield/Time pills** (FeatureStrip already repeats trust).  
- One CMS CTA; secondary catalog only if needed.  
- Push FeatureStrip + HomeStatsStrip below fold; hide empty “پیشنهادهای ویژه”.  
- Delete or honesty-label vanity `+۵۰۰` stats (`home-stats-strip.tsx`).

### ProductCard + TwoLaneActions — `product-card.tsx`, `two-lane-actions.tsx`
- Remove decorative Heart or wire wishlist.  
- Neutral silhouette placeholder (brand/SKU initials) — never picsum.  
- Quote CTA: steel outline + Document icon (match `/quote`), not near-black fill.  
- Post-add: toast/sheet «به سبد اضافه شد» / «به استعلام اضافه شد» + deep link.  
- Sticky mobile PDP buy bar (price + primary CTA).  
- Kill fake SMS inquiry success or replace with real callback request.

### Catalog — `catalog-view.tsx`, `filter-panel.tsx`, `mobile-filter-drawer.tsx`
- One sticky filter column with hairline dividers — stop per-group `rounded-2xl shadow-soft` card lasagna.  
- Sticky results bar: count · active chips · clear · sort.  
- Empty state: one-click clear all filters.  
- Price inputs `dir="ltr"` + تومان hint; apply on blur/Enter.  
- **RTL bug:** drawer animates `x: "-100%"` while panel is `start-0` — in RTL start is right; use `+100%` or `dir`-aware motion.  
- Audit `.shimmer` `translateX(-100%)` and `marquee-rtl` keyframes under `[dir=rtl]`.

### Cart / Checkout — `cart-view.tsx`, `checkout-view.tsx`, `auth-step.tsx`
- CTAs: «تکمیل خرید و پرداخت» / «ثبت درخواست پیش‌فاکتور» / «انتقال به درگاه پرداخت».  
- Cross-lane banner when the other basket has items.  
- Stepper: 2 real steps, or step 3 explicitly “redirecting to gateway”.  
- Errors use destructive token — not `text-primary`.  
- Env-gate test OTP copy; unify OTP boxes `dir="ltr"` across login + checkout.  
- Payment-init failure: show tracking + retry pay.

### Buttons / badges
| | Unify to |
|--|----------|
| Primary | Flat, no glow, shared radius |
| Outline / RFQ | Steel ring |
| Status badges | `rounded-md` (keep pills only for marketing chips) |

---

## G4. User-flow redesign maps (as-is → to-be)

### Priced purchase
**As-is:** Cluttered home → catalog (24, no pagination) → silent quick-add → vague cart CTA → OTP → details → gateway / weak fail recovery.  
**To-be:** Calm home (hero + categories) → catalog chips + load-more → confirmation sheet → clear pay CTA → auth only if needed → address → gateway → fail path with tracking + retry.

### RFQ / inquiry
**As-is:** Dark card CTA → quote basket → celebration success → empty quote CTA.  
**To-be:** Steel RFQ chrome end-to-end → one-line pre-invoice explainer → success with copy tracking + «پیگیری استعلام» → optional draft in account.

### Mobile shop
**As-is:** No search; account = orders only; quote tab unbadged.  
**To-be:** Search in chrome; account hub tabs Orders | Quotes | Profile | Logout; quote badge.

### Admin ops
**As-is:** Product-count dashboard; strong order detail but no global “needs action” queue; Documents/Settings overclaim.  
**To-be:** Dashboard = action queue (paid awaiting process, open inquiries, critical stock, failed payments) → deep link → keep stepper + `OrderActionPanel` as visual anchor (ink border, not faint primary tint).  
**Shell bugs:** `layout.tsx` always `lg:ps-72` while collapsed sidebar is ~90px → dead gutter; sidebar `translate-x-10` is physical-X fragile in RTL — prefer width/opacity; remove decorative notification dot or wire inbox; remove login mock credentials from non-dev UI.

---

## G5. Microcopy / IA table

| Current | Where | Proposed |
|---------|-------|----------|
| ادامه فرآیند خرید | cart | تکمیل خرید و پرداخت |
| افزودن به سبد استعلام / پیش‌فاکتور | PDP | افزودن به استعلام |
| خوش آمدید 👋 | admin dashboard | امروز — صف اقدامات |
| ارزش موجودی (پایه) | dashboard | Remove or honest label until `/products/statistics` |
| قوانین → `/about` | login | Real terms page or remove |
| فوتر استعلام → catalog | footer | → `/quote` |
| Rating ۴.۷ fixed | PDP | Hide until real average |
| حساب من → orders only | header | Account hub |

First-run dual-lane tip (once): «خرید آنی برای کالاهای قیمت‌دار · استعلام برای کالاهای سازمانی».

---

## G6. Motion & feedback (industrial restraint)

Ship **only** 2–3 intentional motions:
1. Add-to-lane sheet/toast ~180ms (mobile bottom / desktop top).  
2. Checkout step crossfade ~200ms; linear stepper fill.  
3. Success checkmark spring once; rest of success page static (B2B receipt).  

Also: brief badge scale pulse on count change; extend existing `useMotionSafe` to drawers/success.  
Avoid: continuous glow, emoji entrances, marquee as primary motion, sidebar neon pulses.

---

## G7. Redesign execution order

| Priority | Surface | Why first |
|----------|---------|-----------|
| **P0** | Tokens + Button/Badge (`globals.css`, both `button.tsx`/`badge.tsx`) | Unlocks every screen; ink/destructive/glow/radius |
| **P0** | Home hero + above-fold | Brand first impression |
| **P0** | ProductCard + TwoLaneActions | Dual-lane is the product differentiator |
| **P1** | Catalog chrome + RTL drawer | Highest B2B buyer usage |
| **P1** | Header / bottom nav / Logo parity | Discoverability + mobile search |
| **P1** | Cart + Checkout CTAs / stepper / errors | Conversion + trust |
| **P2** | Admin shell width/collapse + dashboard queue | Daily operator friction |
| **P2** | Order detail densification | Workflow already strong |
| **P3** | Footer / About / marketing | Lower conversion impact |
| **P3** | Success / account hub polish | After purchase path is clear |

---

## G8. Visual / interaction bug checklist (must close)

- [ ] Mobile filter drawer RTL slide direction (`mobile-filter-drawer.tsx`)  
- [ ] Shimmer + marquee RTL (`globals.css`, `tailwind.config.ts`)  
- [ ] Admin layout padding vs collapsed sidebar (`layout.tsx`, `sidebar.tsx`)  
- [ ] Footer inquiry link → `/quote`  
- [ ] Test OTP string in checkout UI  
- [ ] Fake SMS inquiry success on PDP  
- [ ] Picsum placeholders  
- [ ] Hardcoded PDP rating  
- [ ] Storefront login ignores `?next=`  
- [ ] Catalog (and admin product list) pagination / load-more  
- [ ] Contact form error state  
- [ ] Clear-cart confirm  

---

## G9. Definition of done for a “smooth” dual-lane experience

A buyer can: find via search on mobile → understand priced vs RFQ in one glance → add with confirmation → finish checkout without seeing test codes or fake SMS → recover from payment-init failure with a tracking code → open a real order detail (not the celebration page) from account.  
An operator can: open the panel to a **queue**, not vanity KPIs → act on order/quote with the existing step-up flows → never confuse Documents/Settings for live storefront config until backend exists.

---

*Persian summary of this appendix: end of `02-uiux-audit-fa.md`. Related API-backed UX needs: end of `01-api-gaps-*.md`.*
