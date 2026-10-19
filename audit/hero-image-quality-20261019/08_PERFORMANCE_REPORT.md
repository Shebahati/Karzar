# 08 — Performance report (evidence repair)

## Hero image delivery (first slide, 1920×1080 @2 DPR)

| | Before (`before-main`) | After (`after-fix`) |
|---|--:|--:|
| Hero requests on first paint | 1 | 1 |
| First hero URL | `/_next/image` w=1920 q=90 | Static `/calibrated-20261018/H01-...desktop...webp` |
| `naturalWidth` (H01) | 1920 | 3840 |

Committed metrics: `browser-capture/before-main/1920x1080@2_H01.json`, `browser-capture/after-fix/1920x1080@2_H01.json`.

## LCP (local lab, Chrome, fresh context per run)

Full attribution: `lcp-comparison/before-main.json`, `lcp-comparison/after-fix.json`.

| | Before | After |
|---|--:|--:|
| Median LCP (ms) | 1776 (range 1684–1972) | 1700 (range 1652–1820) |
| LCP element | `H1` in `campaign-hero-copy-stack` | Same |
| `lcpIsHeroImage` | false (5/5 runs) | false (5/5 runs) |

LCP timing is **not** attributed to the hero background image in either build. Hero sharpness evidence is `naturalWidth` + static URL vs optimizer cap.

## Regression guard

```bash
# With `next start` on :3000
node scripts/hero-quality-browser-audit.mjs before-main   # swap to pre-fix build first
node scripts/validate-hero-capture.mjs ../../audit/.../before-main
node scripts/hero-lcp-comparison.mjs before-main
```
