# Full-screen five-hero layout restore (2026-10-13)

Local production-build evidence for PR restoring full-bleed campaign presentation.

```bash
cd frontend/Storefront && npm run build && npm run start -- -p 3010
node audit/hero-fullscreen-five-2026-10-13/fullbleed-probe.mjs
```

Regression guard: `imageWidth / heroWidth >= 0.98` on desktop viewports in `manifest.json`.
