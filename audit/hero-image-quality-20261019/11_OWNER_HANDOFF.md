# 11 — Owner handoff (draft PR)

## Draft PR scope
- **Only** calibrated hero **delivery** fix (`unoptimized` static WebP for `calibrated-20261018/` paths).
- **No** changes to image bytes, PR #537 merchandising, or database code.

## Initial load verification (1920×1080 @2, cold navigation)
| Metric | Before (optimizer) | After (static WebP) |
|--------|-------------------:|--------------------:|
| Hero image HTTP requests on first paint | 1 | 1 |
| Unique calibrated/hero URLs | 1 (`/_next/image` w=1920) | 1 (H01 desktop WebP master) |
| All five slides downloaded? | **No** | **No** |
| First hero transfer (H01 desktop) | ~247 KB (1920×1080 JPEG via optimizer) | ~494 KB (3840×2160 WebP master) |
| LCP element reported size (lab) | 88,976 px² | 88,976 px² |
| LCP startTime (lab) | ~1612 ms | ~1572 ms |

Evidence: `browser-capture/before-main/initial-load-1920.json`, `browser-capture/after-fix/initial-load-1920.json`.

## Responsive boundary (H01)
- **1023×900 @2:** mobile WebP, `naturalWidth` 2880 (`1023x900@2_H01.json`).
- **1024×768 @2:** desktop WebP, `naturalWidth` 3840 (`1024x768@2_H01.json`).

## Screenshots (committed — not local-only)
- Desktop/mobile before/after: `05_BEFORE_AFTER_DESKTOP/`, `06_BEFORE_AFTER_MOBILE/`
- Full matrix JSON+PNG: `browser-capture/before-main/`, `browser-capture/after-fix/`

## H03–H05 source reassessment (visual, not file-size inference)
Independent 1200×800 center crops at native resolution: `H03-H05_visual_reassessment/`.
Visual review: insert/end-mill/machine **geometry and edges remain credible** at 100% crop; some slides show **softer micro-contrast** than H01–H02 consistent with **export grading**, not upscaling or wrong dimensions. **No SOURCE_QUALITY_BLOCKER** — optional owner re-export at higher WebP quality if desired; **assets unchanged in this PR**.

## Remaining limitations
- Lab LCP uses local `next start`; production CDN/cache may differ.
- Carousel adjacent-slide preload (handoff) may fetch **next** slide after interaction — not on initial load.
- Hero quality matrix is Chrome headless (`channel: chrome`), not owner monitor calibration.

## Recommendation
**CONDITIONALLY ACCEPT DIRECTION** — merge draft after owner visual sign-off on committed screenshots; monitor LCP bytes on production RUM.
