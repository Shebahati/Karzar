# Storefront agent instructions

Follow root `AGENTS.md` and `.cursor/rules/karzar-storefront.mdc`.

Before Storefront changes, inspect the relevant implementation and existing tests; do not assume framework APIs from training data.

Validation baseline:
- `npm run lint`
- `npm run typecheck`
- `npm test`
- `npm run build`
- relevant Playwright/E2E for the changed user flow

For mobile interaction work, test representative viewports and actual hit targets/behavior; screenshots alone are not acceptance evidence.

Do not mix Storefront fixes with Admin, backend, dependency upgrades, or unrelated cleanup unless the Issue explicitly requires it.
