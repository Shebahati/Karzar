# 08 — Performance report (updated)

## Initial page load — hero requests (1920×1080 @2 DPR)
Measured via `scripts/hero-quality-browser-audit.mjs` + committed JSON under `browser-capture/`.

| | Before | After |
|---|--:|--:|
| Hero requests on first paint | 1 | 1 |
| Downloads all 5 slides upfront | No | No |
| First hero URL type | `/_next/image` w=1920 q=90 | Static `/calibrated-20261018/H01-...desktop...webp` |
| Approx. first hero bytes | ~247 KB (decoded 1920×1080 JPEG) | ~494 KB (3840×2160 WebP) |

## Retina effective resolution (after fix)
- 1920×1080 @2: `naturalWidth` 3840 (H01) — matches physical demand (~3840px).
- Before: `naturalWidth` 1920 on optimizer URL — 2× upscale in CSS.

## Cache behavior
- Static WebP: standard browser cache + `Cache-Control` from Next static file serving.
- Before: `/_next/image` cache with `minimumCacheTTL` 30d — different cache key per width/quality.

## LCP (local lab, same machine)
See `initial-load-1920.json` — element size identical; startTime within noise. **Production LCP should be validated post-deploy** due to larger transfer.

## Regression guard
Run `node scripts/hero-quality-browser-audit.mjs` after changes; assert `uniqueCalibratedUrls.length <= 2` on first paint (desktop + optional prefetch).
