# Hero copy composition — LOCAL_BUILD_EVIDENCE

**Branch:** `fix/storefront-hero-copy-composition`  
**Type:** LOCAL_BUILD_EVIDENCE (production standalone)

## Change summary

Desktop campaign hero copy uses a shared safe shell (`campaign-hero-desktop-copy-shell`) with header clearance, horizontal `clamp(2rem, 5vw, 6rem)` padding, and a right-aligned RTL copy column (`max-width: min(520px, 38vw)`). Per-slide `top-[NN%]` absolute positioning removed.

## Capture

```bash
# After production build + standalone serve (see PR #495 audit README for serve steps)
node audit/hero-copy-composition-2026-10-14/capture-screenshots.mjs
```

Artifacts: `desktop-1366-H01.png` … `H05`, `desktop-1920-*`, `mobile-390-*`, `tablet-1023-*`, `metrics.json`.

## Desktop blackout

**DESKTOP_BLACKOUT** remains a separate known issue; not claimed fixed here.
