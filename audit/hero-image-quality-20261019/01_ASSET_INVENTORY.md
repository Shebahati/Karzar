# 01 — Asset inventory (H01–H05 calibrated campaign)

**Baseline:** `origin/main` @ PR #536 merge (`ae77eb9b`)  
**Owner package:** `/home/shebahati/Projects/Karzar/karzar_hero_calibrated_pack.zip`  
**Package SHA256:** `53ac343f47fccaf35cb042b61ade969ab92be13dc38ea848d45dc11bcee6c562`

## Provenance

All ten committed WebP files are **byte-identical** to the approved zip WebP entries (SHA256 match). GitHub carries the **approved export bytes**, not a second re-encode in-repo.

## Per-asset table

| File | Git introducing commit | Dimensions | Aspect | Bytes | SHA256 (first 16) | WebP | Alpha |
|------|------------------------|------------|--------|-------|-------------------|------|-------|
| `H01-special-offers-desktop-16x9.webp` | `f5a84c3cab02` | 3840×2160 | 1.7778 | 493,628 | `06a20fe863f6b296…` | lossy VP8 | no |
| `H01-special-offers-mobile-4x3.webp` | `f5a84c3cab02` | 2880×2160 | 1.3333 | 494,548 | `6002caa232f6449d…` | lossy VP8 | no |
| `H02-measuring-tools-desktop-16x9.webp` | `f5a84c3cab02` | 3840×2160 | 1.7778 | 498,784 | `c201c158eeaffe1c…` | lossy VP8 | no |
| `H02-measuring-tools-mobile-4x3.webp` | `f5a84c3cab02` | 2880×2160 | 1.3333 | 492,444 | `489523f28812ccfc…` | lossy VP8 | no |
| `H03-inserts-turning-tools-desktop-16x9.webp` | `f5a84c3cab02` | 3840×2160 | 1.7778 | 284,840 | `f341195fd2e71433…` | lossy VP8 | no |
| `H03-inserts-turning-tools-mobile-4x3.webp` | `f5a84c3cab02` | 2880×2160 | 1.3333 | 287,304 | `04fa8cb9d6330a1a…` | lossy VP8 | no |
| `H04-end-mills-desktop-16x9.webp` | `f5a84c3cab02` | 3840×2160 | 1.7778 | 315,784 | `dfe377179f3cf9d7…` | lossy VP8 | no |
| `H04-end-mills-mobile-4x3.webp` | `f5a84c3cab02` | 2880×2160 | 1.3333 | 310,422 | `3e6f4649de7fd268…` | lossy VP8 | no |
| `H05-industrial-machines-desktop-16x9.webp` | `f5a84c3cab02` | 3840×2160 | 1.7778 | 272,744 | `37137cb2fde670fc…` | lossy VP8 | no |
| `H05-industrial-machines-mobile-4x3.webp` | `f5a84c3cab02` | 2880×2160 | 1.3333 | 279,968 | `26095380cefa28f1…` | lossy VP8 | no |

## Declared vs measured

- Desktop masters: **3840×2160 (16:9)** — confirmed.
- Mobile masters: **2880×2160 (4:3)** — confirmed; separate compositions (not desktop crops).

## ICC / EXIF

- No EXIF orientation tags observed via Pillow decode.
- `exiftool` not available in audit environment; no embedded ICC profile surfaced in Pillow metadata.

## Zip also contains matching JPG intermediates

Used only for export comparison; production references WebP paths under `calibrated-20261018/`.
