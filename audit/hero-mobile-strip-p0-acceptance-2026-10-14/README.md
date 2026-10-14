# Hero mobile strip P0 — LOCAL_BUILD_EVIDENCE

**Type:** `LOCAL_BUILD_EVIDENCE` (not production/staging)  
**Git SHA:** `203995fddf7725e61953a5ccd050baf9dd7a1f74`  
**PR:** [#495](https://github.com/Shebahati/Karzar/pull/495)  
**Captured:** 2026-10-14

## Build & serve

| Item | Value |
|------|--------|
| Build | `cd frontend/Storefront && NEXT_PUBLIC_USE_MOCK=true NEXT_PUBLIC_MOCK_LATENCY_MS=0 NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1 NEXT_PUBLIC_SITE_URL=https://www.karzartools.com npm run build` |
| Serve | `cd frontend/Storefront/.next/standalone && cp -r ../static .next/static && cp -r ../../public public && PORT=3098 HOSTNAME=127.0.0.1 node server.js` |
| Base URL | `http://127.0.0.1:3098/` |
| Runner | `node audit/hero-mobile-strip-p0-acceptance-2026-10-14/run-acceptance.mjs` |

Splash suppressed via `sessionStorage['karzar-splash-seen']=1` before navigation.  
`SPLASH_VISIBLE=NO` on all sessions; H01 title + hero `img.naturalWidth>0` confirmed on 390×844.

## Summary metrics (`metrics.json`)

| Metric | Result |
|--------|--------|
| `STALE_SLIDE_RETURN_COUNT` | **0** |
| `STALE_SLIDE_RETURN_FRAMES` | **0** |
| `MAX_SETTLED_HERO_HEIGHT_DELTA` | **0** px |
| `MAX_NEXT_SECTION_Y_DELTA` | **0** px |
| `CTA_CLIP_COUNT` | **0** |
| `SIZER_IMAGE_REQUESTS` | **0** |
| `HORIZONTAL_OVERFLOW` | **0** (document width ≤ viewport) |

`DARK_FLASH_COUNT`, `WHITE_FLASH_COUNT`, `FINGER_LIFT_SNAP_COUNT`, `MEDIA_CLIP_COUNT`, `PAGE_VERTICAL_JUMP_COUNT` are not frame-sampled in this harness; no obvious flashes/jumps in `390x844-forward-3cycles.webm` spot review.

## Artifacts

- `390x844-forward-3cycles.webm` — 3× H01→…→H01 forward + reverse cycle (CDP touch swipes)
- `measurements.csv` — per-settle hero bottom / next-section Y for all viewports
- `H03-rest-390x844.png`, `mid-h02-h03-390.png`, `mid-h03-h04-390.png`
- `static-1023x768.png`, `static-1024x768.png`, `static-1366x768.png` (breakpoint + desktop spot)

## Adjacent panel geometry (H02↔H03)

During mid-swipe, compact media bottom Y can differ between co-visible panels (~56px in metrics) while **outer hero height stays fixed** (`maxHeroHeightDelta=0`). Mid-transition screenshots look coherent (no jagged page jump). **Visual verdict: PASS.**

## Desktop

`static-1366x768.png` captured. **DESKTOP_BLACKOUT** remains a known separate issue (not validated/fixed here).

## Owner follow-up

Post-deploy production/staging 390×844 recording still required for merge sign-off.
