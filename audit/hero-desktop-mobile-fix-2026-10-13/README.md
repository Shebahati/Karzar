# Hero desktop/mobile fix — visual evidence

See [`NEEDS_MOBILE_ART.md`](NEEDS_MOBILE_ART.md) for remaining portrait asset work.

Captured against **production build** (`npm run build && npm run start`, `NEXT_PUBLIC_USE_MOCK=true`).

- **Motion:** `HERO_MOTION=no-preference` (normal transitions)
- **Viewports:** 1920×1080, 1440×900, 1366×768, 1363×936, 768×1024, 390×844, 360×800, 430×932
- **Slides:** 5 per viewport under `screenshots/{viewport}-slide-{1..5}.png`
- **Regenerate:** `BASE_URL=http://127.0.0.1:3000 node audit/hero-desktop-mobile-fix-2026-10-13/capture-hero-evidence.mjs`
