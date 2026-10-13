# NEEDS_MOBILE_ART — Heroes Reborn 5 compact band

Approved desktop masters: `frontend/Storefront/public/images/hero/reborn-5/*-native-lossless.webp`.

## Layout contract (code ↔ art)

Compact layout (`max-width: 1023px`) is a **stack**:

1. **Media band** — full viewport width, height from `aspect-ratio` (`compactAspect` in `hero-campaign-layout.ts`). Copy never overlays this band.
2. **Copy panel** — solid `#121212` block below the band (title, subtitle, CTAs).

**Interim production:** `*-1280.webp` files are **landscape** derivatives of the desktop composition. They are shown with `object-cover` inside the **landscape** media band only. This is a crop compromise, not portrait acceptance.

**Portrait acceptance:** ship **portrait** masters at the dimensions below. When wired in `hero-campaign-five.ts`, `compactAspect` must switch to `3/4` (portrait) for that slide so art is **not** cropped into a landscape cover box.

| Slide | ID | Interim band (landscape, current) | Portrait deliverable (required) | Required visible group |
| --- | --- | --- | --- | --- |
| H01 | `slide_h01_special_offers` | **1280 × 960** (4∶3) | **1280 × 1707** (3∶4) | Measuring + cutting tools (drill, caliper, end-mill box) |
| H02 | `slide_h02_measuring` | **1280 × 960** (4∶3) | **1280 × 1707** (3∶4) | Caliper, micrometer, indicator |
| H03 | `slide_h03_inserts` | **1280 × 853** (3∶2) | **1280 × 1707** (3∶4) | Mounted holder + four loose inserts |
| H04 | `slide_h04_endmills` | **1280 × 960** (4∶3) | **1280 × 1707** (3∶4) | Varied end mills |
| H05 | `slide_h05_machines` | **1280 × 800** (16∶10) | **1280 × 1707** (3∶4) | Tapping machine head/chuck/tap, arm, workholding |

Constants in code: `COMPACT_BAND_ART_WIDTH_PX`, `COMPACT_BAND_PORTRAIT_ASPECT`, `COMPACT_BAND_PORTRAIT_HEIGHT_PX` (`hero-campaign-layout.ts`).

## Safe zones (portrait deliverables)

- **Format:** WebP, sRGB, no transparency required.
- **Canvas:** 1280 × 1707 px (3∶4). Do not letterbox inside a landscape frame.
- **Product safe area:** keep the required visible group inside the central **1152 × 1536** px region (64 px inset on all sides).
- **Bottom edge:** reserve **96 px** minimum clear of critical product geometry (compact band sits above the copy panel; a soft gradient may sit on the band bottom only).
- **Focal:** match `mobileFocal` in `hero-campaign-five.ts` per slide when framing the hero product group.

## Wiring after approval

1. Add portrait WebP under `public/images/hero/reborn-5/` (e.g. `H03-inserts-mobile-portrait.webp`).
2. Point `mobileImage` at the new file in `hero-campaign-five.ts`.
3. Set `compactAspect` for that slide to `3/4` (portrait) in `compactAspectFor()` — **never** use portrait files with the interim landscape aspects (4∶3, 3∶2, 16∶10).

Do not mirror, stretch, or substitute product geometry.
