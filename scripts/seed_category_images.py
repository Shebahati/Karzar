#!/usr/bin/env python3
"""Download category card images and attach them to Category.image_url.

Curated Wikimedia Commons photos of machining tools — matched by root id / Persian
name. Prefer accurate category-themed imagery (never random Wikipedia page thumbs).

After download, each image is padded (~16% margin) so object-contain inside a
rounded square never clips tool tips/corners. PNG preferred when under the upload
cap; otherwise JPEG q=95 with no chroma subsampling (no subject downscale).

Run on the API host / inside the API container (needs DB + writable uploads):

  python scripts/seed_category_images.py
  python scripts/seed_category_images.py --dry-run
  python scripts/seed_category_images.py --force
  python scripts/seed_category_images.py --ids 1,7,9 --force
  python scripts/seed_category_images.py --roots-only
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
# Extra canvas margin so object-contain + rounded overflow never clips tips/corners.
PAD_RATIO = 0.16
MIN_PAD_PX = 48
JPEG_QUALITY = 95

# Seed catalog root ids (scripts/seed_categories.py).
ROOT_IDS: frozenset[int] = frozenset({1, 2, 3, 4, 5, 6, 7, 8, 9})

# Direct Commons image URLs keyed by category id (preferred).
CURATED_BY_ID: dict[int, list[str]] = {
    # ابزارگیر — loaded tool assemblies / collet
    1: [
        "https://upload.wikimedia.org/wikipedia/commons/1/12/Tool-Assemblies-Loaded.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/4/4e/R8_Collet_with_end_mill.png",
    ],
    # ابزار اینسرتی — indexable face mill with inserts
    2: [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/Carbide_tipped_face_mill_%283%29.jpg/960px-Carbide_tipped_face_mill_%283%29.jpg",
    ],
    # اینسرت — tungsten carbide inserts
    3: [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/7/72/Tungsten_carbide_inserts.jpg/960px-Tungsten_carbide_inserts.jpg",
    ],
    # ابزار انگشتی — end mills
    4: [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/MillingCutterSlotEndMillBallnose.jpg/960px-MillingCutterSlotEndMillBallnose.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/b/ba/End_Mills_and_Drill_Bit.jpg/960px-End_Mills_and_Drill_Bit.jpg",
    ],
    # مته — drill bits (1920px thumb: full original is >5MB seed cap)
    5: [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d9/Drill_bits_2017_G1.jpg/1920px-Drill_bits_2017_G1.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/b/ba/End_Mills_and_Drill_Bit.jpg",
    ],
    # قلاویز — near-square tap photos so object-contain fills the card
    6: [
        "https://upload.wikimedia.org/wikipedia/commons/9/9b/Spiral_point_tap.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/f/fe/Tarauds_-_Mobilier_national.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/9/96/Machine-screw-tap-1.JPG",
    ],
    # اندازه گیری — full-res caliper originals (no 960px downscale)
    7: [
        "https://upload.wikimedia.org/wikipedia/commons/5/5c/2020_Suwmiarka_cyfrowa.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/9/94/Messschieber.jpg",
    ],
    # ابزار گیرشی — lathe chuck
    8: [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Lathe_Chuck.jpg/960px-Lathe_Chuck.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/FourJawChuckIndependent.jpg/960px-FourJawChuckIndependent.jpg",
    ],
    # دستگاه‌های صنعتی — CNC milling
    9: [
        "https://upload.wikimedia.org/wikipedia/commons/a/a7/CNC_Milling.png",
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
    "ابزار گیرشی": CURATED_BY_ID[8],
    "دستگاه‌های صنعتی": CURATED_BY_ID[9],
    "دستگاه های صنعتی": CURATED_BY_ID[9],
    # Useful mid-level themes (optional when --include-mid)
    "کولت": [
        "https://upload.wikimedia.org/wikipedia/commons/4/4e/R8_Collet_with_end_mill.png",
    ],
    "کولیس": [
        "https://upload.wikimedia.org/wikipedia/commons/9/94/Messschieber.jpg",
    ],
    "میکرومتر": [
        "https://upload.wikimedia.org/wikipedia/commons/5/5c/2020_Suwmiarka_cyfrowa.jpg",
    ],
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
        resp = await client.get(url, follow_redirects=True, timeout=30.0)
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


def pad_for_card_frame(
    content: bytes,
    *,
    pad_ratio: float = PAD_RATIO,
) -> tuple[bytes, str]:
    """Expand canvas with margin so rounded card clips never cut the tool.

    Prefers lossless PNG for smaller / alpha images when under the upload cap;
    otherwise high-quality JPEG (q=95, no chroma subsampling) — never downscales.
    """
    im = Image.open(BytesIO(content))
    im = ImageOps.exif_transpose(im)
    has_alpha = im.mode in {"RGBA", "LA"} or (
        im.mode == "P" and "transparency" in im.info
    )

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

    if has_alpha:
        im = im.convert("RGBA")
        w, h = im.size
        pad = max(int(max(w, h) * pad_ratio), MIN_PAD_PX)
        canvas = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
        canvas.paste(im, (pad, pad), im)
        data = _encode_png(canvas)
        if len(data) <= MAX_BYTES:
            return data, ".png"
        bg = _edge_rgb(im)
        flat = Image.new("RGB", canvas.size, bg)
        flat.paste(canvas, mask=canvas.split()[-1])
        data = _encode_jpeg(flat)
    else:
        im = im.convert("RGB")
        w, h = im.size
        pad = max(int(max(w, h) * pad_ratio), MIN_PAD_PX)
        bg = _edge_rgb(im)
        canvas = Image.new("RGB", (w + 2 * pad, h + 2 * pad), bg)
        canvas.paste(im, (pad, pad))
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
                    content, ext = pad_for_card_frame(content)
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
