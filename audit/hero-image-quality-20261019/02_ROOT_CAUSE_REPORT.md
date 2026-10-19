# 02 — Root cause report

**Audit HEAD (implementation branch):** `ae77eb9b6f392b2391aa977256763cd533e0745a`  
**Worktree:** `/home/shebahati/Projects/Karzar-hero-quality-audit`  
**Branch:** `fix/hero-calibrated-delivery-quality-20261019` (isolated from PR #537)

## Ranked causes (evidence-backed)

### 1. Next.js Image optimizer capped hero width at 1920px (PRIMARY — delivery)

- `next.config.ts` `deviceSizes` ends at **1920** (`frontend/Storefront/next.config.ts:18`).
- Calibrated heroes declare **3840×2160** intrinsics (`hero-background-image.tsx`) but `getImageProps` srcsets cannot exceed configured device widths.
- **Measured:** `/_next/image?...&w=1920&q=90` for H01 desktop delivers **1920×1080 JPEG** (~247 KB), not the 3840×2160 WebP master (~494 KB).
- On **1920×1080 @ 2× DPR**, physical demand ≈ **3840px** width; browser received **1920px** → **2× upscaling** in CSS (`object-fit: cover`) → visible softness.

**Classification:** (E) browser scaling artifact **caused by** optimizer width cap + (C) secondary recompression (lossy WebP → lossy JPEG/AVIF at q=90).

### 2. Double lossy compression through `/_next/image` (SECONDARY — delivery)

- Committed assets are already lossy WebP exports from the owner pack.
- Optimizer re-encodes at `HERO_IMAGE_QUALITY = 90` (`cwv.ts`) with formats `avif`/`webp` preference (`next.config.ts:16`).
- Probe at w=1920 returned **JPEG** payload — additional generation loss vs static WebP master.

### 3. Heavier WebP compression on H03–H05 masters (TERTIARY — export)

- H01–H02 desktop ~**495 KB**; H03–H05 desktop **273–316 KB** at same 3840×2160 resolution.
- Laplacian-variance proxy on a fixed product crop (`source_sharpness_proxy.json`) is **lower on H03–H05** than H01–H02 at identical geometry — indicates **more aggressive export quantization**, not missing pixels.
- Zip JPG intermediates show the same pattern; WebP is not softer than JPG in pack.

**Classification:** (A)/(detail destruction from aggressive compression) at **source export** — **not fixable** by CSS or upscaling.

### 4. Desktop readability gradients (MINOR — composition)

- `campaign-hero-slide.tsx` stacks RTL-weighted gradient (up to **0.72** alpha), bottom dock gradient, and slide overlay at `opacity * 0.22`.
- Darkens right side by design; can read as “muddy” on already-soft imagery but is **not** the primary sharpness loss.

### Ruled out

- **Wrong files in git:** SHA256 matches owner zip.
- **Dimension lie:** files are true 3840/2880 masters.
- **Mobile/desktop swap at 1024:** `<picture>` uses `(max-width: 1023px)` mobile art; verified at 1023×900@2 → **2880×2160** mobile WebP; at 1024×768@2 → desktop **3840×2160** after fix.

## Correction applied

Serve calibrated campaign art **`unoptimized`** (static WebP URL) via `buildHeroBackgroundPictureSources` when both desktop and mobile paths are under `calibrated-20261018/`. Legacy v2 PNG heroes still use `/_next/image`.

See `09_IMPLEMENTATION_REPORT.md`.
