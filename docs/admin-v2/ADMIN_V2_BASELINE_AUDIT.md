# ADMIN V2 baseline audit (2026-10-24)

- **Verified origin/main SHA:** `dff7824b11f9fdb22bbe3cd5baf894a436b9e4e4`
- **Worktree:** `/home/shebahati/Projects/Karzar-admin-v2-base`

| Feature | Branch | PR |
|---------|--------|-----|
| A Fulfillment | feat/admin-v2-order-fulfillment | #553 |
| B Attribution | feat/admin-v2-order-attribution | #555 |
| C Dark mode | feat/admin-v2-dark-mode | pending |
| D Brand pricing | feat/admin-v2-brand-bulk-pricing | #554 |


## Dark mode coverage matrix (partial pass)

| Surface | Light | Dark | System | Notes |
|---------|-------|------|--------|-------|
| Login | pass | pass | pass | semantic `bg-card` |
| Dashboard shell (header/sidebar) | pass | pass | pass | tokens applied |
| Orders list/detail | pass | pass | pass | prior PR + tokens |
| Reports | pass | pass | pass | uses theme tables |
| Catalog editors | partial | partial | partial | major `bg-white` → `bg-card` |
| Hero Studio preview | n/a | n/a | n/a | intentional storefront colors |
| Invoices PDF chrome | partial | partial | partial | card tokens |
| CMS/static/home editors | partial | partial | partial | card tokens |

Remaining: date pickers/toasts/mobile nav need spot-check; run `npm run build` after `npm ci` in admin-panel.
