# 12 — Evidence repair (PR #539 review)

## Why prior evidence was rejected

Independent review at HEAD `ea470b1148a706635ee38b0e5de11441a54cea07` found two capture defects:

### Invalid screenshots (splash, not hero)
Committed PNGs showed the white Karzar first-visit splash instead of the campaign hero region, including:
- `05_BEFORE_AFTER_DESKTOP/before_1440x900@2_H01.png`
- `05_BEFORE_AFTER_DESKTOP/after_1440x900@2_H01.png`
- `06_BEFORE_AFTER_MOBILE/after_390x844@3_H01.png`

**Root cause:** `gotoHomeReady` treated `.karzar-splash` count `0` during React `boot` (before the overlay mounted) as “splash dismissed”, then captured while the splash was still visible.

### Incorrect slide identity in metadata
`hero-quality-browser-audit.mjs` called `page.goto('/')` inside the H01–H05 loop, resetting carousel state. JSON examples:
- `browser-capture/**/1920x1080@2_H03.json` — H02 artwork
- `browser-capture/**/1920x1080@2_H05.json` — H02 artwork
- `browser-capture/**/390x844@3_H03.json` — H02 artwork

## Corrected capture lifecycle

Implemented in `frontend/Storefront/scripts/hero-audit-lib.mjs` and mirrored in `e2e/hero-image-quality-audit.spec.ts`:

1. Wait until `sessionStorage['karzar-splash-seen'] === '1'` **and** `.karzar-splash` is absent **and** `style[data-karzar-splash-boot]` is absent (no boot-phase false positive).
2. Assert hero region visible; assert expected Persian heading per slide.
3. Assert `currentSrc` contains the expected H01–H05 calibrated asset and image is decoded.
4. `elementFromPoint` check — no splash/fixed overlay over hero center.
5. One homepage navigation per viewport; advance carousel with `ArrowLeft` and wait for `currentSrc` change between slides.

Validation gate: `node scripts/validate-hero-capture.mjs <dir>` (25 PNG + JSON).

## Replacement evidence (this repair)

| Artifact | Location |
|----------|----------|
| Before matrix (optimizer, 25) | `browser-capture/before-main/{viewport}_{H01..H05}.{png,json}` |
| After matrix (`unoptimized` static WebP, 25) | `browser-capture/after-fix/{viewport}_{H01..H05}.{png,json}` |
| Owner comparison sheets | Regenerated via `scripts/hero-sync-comparison-assets.mjs` → `05_BEFORE_AFTER_DESKTOP/`, `06_BEFORE_AFTER_MOBILE/` |

Mandatory viewports: 390×844@3, 1023×900@2, 1024×768@2, 1440×900@2, 1920×1080@2.

## LCP attribution (corrected)

See `lcp-comparison/before-main.json` and `lcp-comparison/after-fix.json` (5 cold contexts each, median + min/max).

| | Before (optimizer) | After (static WebP) |
|--|--:|--:|
| Median LCP element | `H1` (`campaign-hero-copy-stack`) | `H1` (`campaign-hero-copy-stack`) |
| `lcpIsHeroImage` (all runs) | `false` | `false` |
| Median LCP time (ms) | 1776 | 1700 |
| Hero `naturalWidth` @2 | 1920 | 3840 |
| Hero URL | `/_next/image` w=1920 | `/calibrated-20261018/H01-...webp` |

**Conclusion:** Measured LCP is the hero **heading**, not the background image. Do not use LCP timing alone as proof of hero-image performance improvement; use hero request URL, transfer size, and `naturalWidth` vs DPR demand.

## Invalid files superseded

Do not use pre-repair `browser-capture/**` JSON/PNG or comparison sheets that relied on per-slide `goto('/')` or splash-unsafe waits. The matrices above replace them.
