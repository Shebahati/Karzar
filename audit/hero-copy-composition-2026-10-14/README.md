# Hero copy composition — LOCAL_BUILD_EVIDENCE

**Branch:** `fix/storefront-hero-copy-composition`  
**Type:** LOCAL_BUILD_EVIDENCE (production standalone)

## Change summary

Desktop campaign hero copy uses an **LTR positioning shell** (`dir="ltr"`) with `justify-end` so the block sits on the **physical right**, plus an inner **RTL copy column** (`dir="rtl"`). Header clearance + horizontal padding unchanged. Per-slide `top-[NN%]` absolute positioning removed.

Capture harness waits for expected slide titles (campaign pending/image load) and asserts physical geometry on 1366×768 (`physicalRightMargin` in **[48, 160]** px).

## Capture

```bash
# After production build + standalone serve (see PR #495 audit README for serve steps)
node audit/hero-copy-composition-2026-10-14/capture-screenshots.mjs
```

Artifacts: `desktop-1366-H01.png` … `H05`, `desktop-1920-*`, `mobile-390-*`, `tablet-1023-*`, `metrics.json`.

## Desktop blackout

**DESKTOP_BLACKOUT** remains a separate known issue; not claimed fixed here.
