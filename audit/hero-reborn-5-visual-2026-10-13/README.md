# Heroes Reborn 5 — visual evidence (PR #481)

Captured **2026-10-13** against local Storefront (`BASE_URL=http://127.0.0.1:3000`, `NEXT_PUBLIC_USE_MOCK=true`).

## Screenshots (25)

| Viewport | Files |
|----------|--------|
| 1920×1080 | `screenshots/1920x1080__h01-discounts.png` … `h05-machines.png` |
| 1440×900 | `screenshots/1440x900__*.png` |
| 1366×768 | `screenshots/1366x768__*.png` |
| 768×1024 | `screenshots/768x1024__*.png` |
| 390×844 | `screenshots/390x844__*.png` |

Slide order: H01 discounts → H02 metrology → H03 inserts → H04 endmills → H05 machines.

## Transition recordings

| File | Check |
|------|--------|
| `videos/desktop-1920x1080-forward-back.webm` | Forward through 5 titles, then 4× prev; ends on H01 (no blank frame in title sequence) |
| `videos/mobile-390x844-forward-back.webm` | Same sequence at 390×844 via nav buttons (`prefers-reduced-motion: reduce` for deterministic settle) |

## Layout / copy checks (`manifest.json`)

- **Titles:** 25/25 `titleMatch: true` (see `summary.allTitlesMatch`).
- **RTL copy block:** title `x` ≈ right third on desktop (e.g. 1920px: title right edge ~1805px).
- **Subtitles:** updated campaign copy present per slide (e.g. H01 «پیشنهادهای ویژه…», H02 «مجموعه‌ای متنوع از ابزارهای اندازه‌گیری…»).
- **Dock overlap:** `titleOverlapsOrb: false` on all desktop shots where orbs render (`summary.layoutOverlapFlags: 0`).

## Regenerate

```bash
cd frontend/Storefront && npm run dev   # :3000
node ../../audit/hero-reborn-5-visual-2026-10-13/capture-hero-evidence.mjs
```
