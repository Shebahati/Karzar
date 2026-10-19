# 08 — Performance report

## Hero transferred bytes (H01 desktop, representative)

| Path | Bytes | Notes |
|------|------:|-------|
| Before: `/_next/image` w=1920 q=90 | ~247,178 | JPEG re-encode, capped width |
| After: static WebP master | 493,628 | Full 3840×2160 lossy WebP |
| Before: `/_next/image` w=640 | ~40,251 | Used on narrow viewports |

## LCP / first hero

- First slide still `priority` + `fetchPriority=high`; now fetches **one** full master instead of optimizer negotiation.
- **Trade-off:** ~+250 KB on large desktop LCP vs capped optimizer asset — justified for perceptual sharpness on 2× displays.

## Duplicate downloads

- HTML after fix: **0** `/_next/image` references for calibrated paths on `/` (local production server probe).
- Carousel non-active slides: still lazy via picture loading rules (unchanged).

## Regression

- No new dependencies. No global optimizer disable.
