#!/usr/bin/env python3
"""Download category card images and attach them to Category.image_url.

Curated Wikimedia Commons catalog-quality photos of machining tools — matched by
root id / Persian name. Prefer clean studio / controlled-lighting shots that
harmonize with the Karzar storefront (steel neutrals, white/soft backgrounds).

Processing for the homepage 88×88 ``object-cover`` / ``rounded-xl`` tile:
  1. Extreme aspect ratios are center-cropped to square (optional bias).
  2. Remaining images are placed on a square canvas with adaptive margin so
     rounded overflow never clips tips/corners, while near-square catalog shots
     still fill the tile.
PNG preferred when under the upload cap; otherwise JPEG q=95, no chroma
subsampling (no destructive downscale below display×2–3x).

Run on the API host / inside the API container (needs DB + writable uploads):

  python scripts/seed_category_images.py
  python scripts/seed_category_images.py --dry-run
  python scripts/seed_category_images.py --force
  python scripts/seed_category_images.py --ids 1,7,9,154,165 --force
"""

from __future__ import annotations

import argparse
import asyncio
import mimetypes
import sys
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageOps
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.database import async_session_maker
from app.db.models.product import Category
from app.utils.file_storage import MAX_UPLOAD_BYTES, save_category_image_bytes

USER_AGENT = (
    "Mozilla/5.0 (compatible; KarzarCategoryImageBot/1.0; +https://www.karzartools.com)"
)
MIN_BYTES = 800
MAX_BYTES = MAX_UPLOAD_BYTES
# Extra canvas margin so object-cover + rounded overflow never clips tips/corners.
# Near-square sources use a tighter default so the subject fills the tile.
PAD_RATIO = 0.14
PAD_RATIO_NEAR_SQUARE = 0.08
PAD_RATIO_MODERATE = 0.11
NEAR_SQUARE_AR = 1.25
MODERATE_AR = 1.7
# Outside this range: center-crop to square before padding (fills 88px tiles).
CROP_OUTSIDE_AR = (0.55, 1.85)
MIN_PAD_PX = 40
JPEG_QUALITY = 95

# Live + seed catalog root ids (incl. لوازم جانبی / اینسرت when renumbered).
ROOT_IDS: frozenset[int] = frozenset({1, 2, 3, 4, 5, 6, 8, 9, 56, 81, 87, 154, 165})

# Optional horizontal/vertical crop bias (0=left/top … 1=right/bottom) when
# extreme-aspect sources are center-cropped to square.
CROP_BIAS_BY_ID: dict[int, float] = {
    56: 0.35,  # micrometer — keep frame + anvil in view
    5: 0.45,  # drill set packaging — favor bit window
}

# Direct Commons image URLs keyed by category id (preferred).
CURATED_BY_ID: dict[int, list[str]] = {
    # ابزارگیر — INT40 taper toolholder / face-mill arbor on studio gray
    1: [
        "https://upload.wikimedia.org/wikipedia/commons/2/23/MillingCutterCarbideTippedFaceMill-INT40.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/4/4e/R8_Collet_with_end_mill.png",
    ],
    # ابزار اینسرتی — indexable face mill with gold carbide inserts
    2: [
        "https://upload.wikimedia.org/wikipedia/commons/a/a7/Carbide_tipped_face_mill_%281%29.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/8/8e/Carbide_tipped_face_mill_%283%29.jpg",
    ],
    # اینسرت — tungsten carbide inserts on neutral ground (seed id 3 + live 165)
    3: [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/7/72/Tungsten_carbide_inserts.jpg/1920px-Tungsten_carbide_inserts.jpg",
    ],
    165: [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/7/72/Tungsten_carbide_inserts.jpg/1920px-Tungsten_carbide_inserts.jpg",
    ],
    # ابزار انگشتی — slot / ball-nose end mill catalog layout on gray
    4: [
        "https://upload.wikimedia.org/wikipedia/commons/e/e6/MillingCutterSlotEndMillBallnose.jpg",
    ],
    # مته — cobalt twist-drill set (catalog product photo, not rusty shop scatter)
    5: [
        "https://upload.wikimedia.org/wikipedia/commons/1/1a/2010-01-21_Craftsman_Professional_cobalt_drill_bit_set.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/e/e4/Group_of_drill_bits.jpg",
    ],
    # قلاویز — spiral-point machine tap macro (square-friendly, technical)
    6: [
        "https://upload.wikimedia.org/wikipedia/commons/9/9b/Spiral_point_tap.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/9/96/Machine-screw-tap-1.JPG",
    ],
    # اندازه گیری دقیق / CNC / آزمایشگاهی (promoted L1s)
    56: [
        "https://upload.wikimedia.org/wikipedia/commons/d/d9/Mahr_Micromar_40A_0%E2%80%9325_mm_Micrometer.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/5/5c/2020_Suwmiarka_cyfrowa.jpg",
    ],
    81: [
        "https://upload.wikimedia.org/wikipedia/commons/5/5c/2020_Suwmiarka_cyfrowa.jpg",
    ],
    87: [
        "https://upload.wikimedia.org/wikipedia/commons/d/d9/Mahr_Micromar_40A_0%E2%80%9325_mm_Micrometer.jpg",
    ],
    # ابزار گیرشی — square lathe chuck head-on
    8: [
        "https://upload.wikimedia.org/wikipedia/commons/d/d2/Lathe_Chuck.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/b/b6/Four_Jaw_Chuck_Independent.jpg",
    ],
    # اندازه گیری — legacy hub id (removed on live; keep for old DBs)
    7: [
        "https://upload.wikimedia.org/wikipedia/commons/d/d9/Mahr_Micromar_40A_0%E2%80%9325_mm_Micrometer.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/5/5c/2020_Suwmiarka_cyfrowa.jpg",
    ],
    # دستگاه‌های صنعتی — CNC bed mill product shot on white
    9: [
        "https://upload.wikimedia.org/wikipedia/commons/a/a6/Kent_USA_CNC_Bed_Mill_TW-32Qi.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/a/a7/CNC_Milling.png",
    ],
    # لوازم جانبی صنعتی — Mitutoyo dial indicator (studio gray)
    154: [
        "https://upload.wikimedia.org/wikipedia/commons/e/e0/DialTestIndicator2050-08.jpg",
    ],
}

# Fallback by normalized Persian name (for renamed roots or mid-level).
CURATED_BY_NAME: dict[str, list[str]] = {
    "ابزارگیر": CURATED_BY_ID[1],
    "ابزار اینسرتی": CURATED_BY_ID[2],
    "اینسرت": CURATED_BY_ID[3],
    "ابزار انگشتی": CURATED_BY_ID[4],
    "مته": CURATED_BY_ID[5],
    "قلاویز": CURATED_BY_ID[6],
    "اندازه گیری": CURATED_BY_ID[7],
    "اندازه‌گیری": CURATED_BY_ID[7],
    "اندازه گیری دقیق": CURATED_BY_ID[56],
    "اندازه‌گیری دقیق": CURATED_BY_ID[56],
    "CNC اندازه گیری": CURATED_BY_ID[81],
    "اندازه گیری آزمایشگاهی": CURATED_BY_ID[87],
    "ابزار گیرشی": CURATED_BY_ID[8],
    "دستگاه‌های صنعتی": CURATED_BY_ID[9],
    "دستگاه های صنعتی": CURATED_BY_ID[9],
    "لوازم جانبی صنعتی": CURATED_BY_ID[154],
    "لوازم جانبی": CURATED_BY_ID[154],
    # Useful mid-level themes (optional when --include-mid)
    "کولت": [
        "https://upload.wikimedia.org/wikipedia/commons/4/4e/R8_Collet_with_end_mill.png",
    ],
    "کولیس": [
        "https://upload.wikimedia.org/wikipedia/commons/5/5c/2020_Suwmiarka_cyfrowa.jpg",
    ],
    "میکرومتر": CURATED_BY_ID[56],
}


def _normalize_name(name: str) -> str:
    return (
        name.strip()
        .replace("\u200c", "")
        .replace("ي", "ی")
        .replace("ك", "ک")
    )


def _sniff_ext(content: bytes, url: str, content_type: str | None) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    if content[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    head = content.lstrip()[:200].lower()
    if head.startswith(b"<svg") or b"<svg" in head[:50]:
        return ".svg"
    path = urlparse(url).path
    suffix = Path(path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    if content_type:
        guess = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guess == ".jpe":
            return ".jpg"
        if guess in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}:
            return ".jpg" if guess == ".jpeg" else guess
    return None


async def _fetch(client: httpx.AsyncClient, url: str) -> tuple[bytes, str] | None:
    try:
        resp = await client.get(url, follow_redirects=True, timeout=60.0)
    except Exception:
        return None
    if resp.status_code != 200 or not resp.content:
        return None
    content = resp.content
    if len(content) < MIN_BYTES or len(content) > MAX_BYTES:
        return None
    ct = resp.headers.get("content-type", "")
    if "html" in ct.lower() and b"<svg" not in content[:500].lower():
        return None
    ext = _sniff_ext(content, url, ct)
    if not ext:
        return None
    return content, ext


def _edge_rgb(im: Image.Image) -> tuple[int, int, int]:
    """Average border colour so padded margins blend with the photo backdrop."""
    rgb = im.convert("RGB")
    w, h = rgb.size
    samples: list[tuple[int, int, int]] = []
    step = max(1, min(w, h) // 80)
    for x in range(0, w, step):
        samples.append(rgb.getpixel((x, 0)))
        samples.append(rgb.getpixel((x, h - 1)))
    for y in range(0, h, step):
        samples.append(rgb.getpixel((0, y)))
        samples.append(rgb.getpixel((w - 1, y)))
    r = sum(c[0] for c in samples) // len(samples)
    g = sum(c[1] for c in samples) // len(samples)
    b = sum(c[2] for c in samples) // len(samples)
    return (r, g, b)


def _adaptive_pad_ratio(width: int, height: int) -> float:
    """Tighter margin for near-square catalog shots; wider for long thin tools."""
    long_side = max(width, height)
    short_side = min(width, height) or 1
    aspect = long_side / short_side
    if aspect <= NEAR_SQUARE_AR:
        return PAD_RATIO_NEAR_SQUARE
    if aspect <= MODERATE_AR:
        return PAD_RATIO_MODERATE
    return PAD_RATIO


def _center_crop_square(im: Image.Image, *, bias: float = 0.5) -> Image.Image:
    """Crop extreme aspect ratios to square so object-cover tiles read full-bleed."""
    w, h = im.size
    ar = w / h if h else 1.0
    if CROP_OUTSIDE_AR[0] <= ar <= CROP_OUTSIDE_AR[1]:
        return im
    side = min(w, h)
    bias = max(0.0, min(1.0, bias))
    if w >= h:
        left = int((w - side) * bias)
        left = max(0, min(left, w - side))
        return im.crop((left, 0, left + side, side))
    top = int((h - side) * bias)
    top = max(0, min(top, h - side))
    return im.crop((0, top, side, top + side))


def pad_for_card_frame(
    content: bytes,
    *,
    pad_ratio: float | None = None,
    crop_bias: float = 0.5,
) -> tuple[bytes, str]:
    """Prepare a square master for rounded object-cover category tiles.

    Extreme aspect ratios are center-cropped (with optional bias) so the subject
    fills the 88×88 tile; otherwise the photo is letterboxed onto a square canvas
    with adaptive margin. Prefers PNG under the upload cap; else JPEG q=95.
    """
    im = Image.open(BytesIO(content))
    im = ImageOps.exif_transpose(im)
    im = _center_crop_square(im, bias=crop_bias)
    has_alpha = im.mode in {"RGBA", "LA"} or (
        im.mode == "P" and "transparency" in im.info
    )
    ratio = pad_ratio if pad_ratio is not None else _adaptive_pad_ratio(*im.size)

    def _encode_jpeg(rgb: Image.Image) -> bytes:
        out = BytesIO()
        rgb.save(
            out,
            format="JPEG",
            quality=JPEG_QUALITY,
            subsampling=0,
            optimize=True,
        )
        return out.getvalue()

    def _encode_png(img: Image.Image) -> bytes:
        out = BytesIO()
        img.save(out, format="PNG", optimize=True)
        return out.getvalue()

    def _square_canvas(
        src: Image.Image,
        *,
        mode: str,
        fill: tuple[int, ...] | int,
    ) -> Image.Image:
        w, h = src.size
        pad = max(int(max(w, h) * ratio), MIN_PAD_PX)
        side = max(w, h) + 2 * pad
        canvas = Image.new(mode, (side, side), fill)
        ox = (side - w) // 2
        oy = (side - h) // 2
        if mode == "RGBA" and src.mode == "RGBA":
            canvas.paste(src, (ox, oy), src)
        else:
            canvas.paste(src, (ox, oy))
        return canvas

    if has_alpha:
        im = im.convert("RGBA")
        canvas = _square_canvas(im, mode="RGBA", fill=(0, 0, 0, 0))
        data = _encode_png(canvas)
        if len(data) <= MAX_BYTES:
            return data, ".png"
        bg = _edge_rgb(im)
        flat = Image.new("RGB", canvas.size, bg)
        flat.paste(canvas, mask=canvas.split()[-1])
        data = _encode_jpeg(flat)
    else:
        im = im.convert("RGB")
        bg = _edge_rgb(im)
        canvas = _square_canvas(im, mode="RGB", fill=bg)
        # Large photos: JPEG only (PNG encode of multi‑MP canvases is slow / oversized).
        if canvas.width * canvas.height <= 2_500_000:
            data = _encode_png(canvas)
            if len(data) <= MAX_BYTES:
                return data, ".png"
        data = _encode_jpeg(canvas)

    if len(data) < MIN_BYTES or len(data) > MAX_BYTES:
        raise ValueError(
            f"padded image size {len(data)}B outside [{MIN_BYTES}, {MAX_BYTES}]"
        )
    return data, ".jpg"


def candidate_urls(category: Category, *, include_mid: bool) -> list[str]:
    urls: list[str] = []
    if category.id in CURATED_BY_ID:
        urls.extend(CURATED_BY_ID[category.id])
    name = _normalize_name(category.name)
    if name in CURATED_BY_NAME:
        for u in CURATED_BY_NAME[name]:
            if u not in urls:
                urls.append(u)
    if include_mid and category.parent_id is not None:
        for key, mid_urls in CURATED_BY_NAME.items():
            if key in name or name in key:
                for u in mid_urls:
                    if u not in urls:
                        urls.append(u)
    return urls


def _parse_id_list(raw: str | None) -> set[int] | None:
    if not raw:
        return None
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part:
            out.add(int(part))
    return out


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Replace existing images")
    parser.add_argument("--ids", help="Comma-separated category IDs (default: roots 1–9)")
    parser.add_argument(
        "--include-mid",
        action="store_true",
        help="Also seed mid-level categories with name-matched curated images",
    )
    args = parser.parse_args()

    only_ids = _parse_id_list(args.ids)
    roots_only = only_ids is None and not args.include_mid

    headers = {"User-Agent": USER_AGENT, "Accept": "image/*,*/*"}
    async with httpx.AsyncClient(headers=headers) as client:
        async with async_session_maker() as db:
            categories = list(
                (await db.execute(select(Category).order_by(Category.id))).scalars()
            )
            ok = skip = fail = 0

            for category in categories:
                if only_ids is not None and category.id not in only_ids:
                    continue
                if roots_only and category.parent_id is not None:
                    continue
                if roots_only and category.id not in ROOT_IDS:
                    # Still allow name-curated roots outside the fixed id set.
                    if not candidate_urls(category, include_mid=False):
                        continue

                urls = candidate_urls(category, include_mid=args.include_mid or only_ids is not None)
                if not urls:
                    if only_ids is not None or args.include_mid:
                        print(f"FAIL  {category.id} {category.name} (no curated source)")
                        fail += 1
                    continue

                if category.image_url and not args.force:
                    print(f"SKIP  {category.id} {category.name} (has image)")
                    skip += 1
                    continue

                print(f"FETCH {category.id} {category.name} …", flush=True)
                resolved: tuple[bytes, str, str] | None = None
                for url in urls:
                    got = await _fetch(client, url)
                    if got:
                        resolved = got[0], got[1], url
                        break
                if not resolved:
                    print(f"FAIL  {category.id} {category.name} (download failed)")
                    fail += 1
                    continue
                content, ext, source = resolved
                try:
                    bias = CROP_BIAS_BY_ID.get(category.id, 0.5)
                    content, ext = pad_for_card_frame(content, crop_bias=bias)
                except Exception as exc:
                    print(f"FAIL  {category.id} {category.name} (pad failed: {exc})")
                    fail += 1
                    continue
                if args.dry_run:
                    print(
                        f"OK    {category.id} {category.name} would save "
                        f"{len(content)}B {ext} (padded) from {source}"
                    )
                    ok += 1
                    continue
                path = save_category_image_bytes(category.id, content, ext)
                category.image_url = path
                await db.flush()
                print(
                    f"OK    {category.id} {category.name} -> {path} "
                    f"({len(content)}B padded {ext}, {source})"
                )
                ok += 1

            if not args.dry_run:
                await db.commit()
            print(f"\nDone: ok={ok} skip={skip} fail={fail}")
            return 0 if fail == 0 or ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
