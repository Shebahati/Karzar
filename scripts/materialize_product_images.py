#!/usr/bin/env python3
"""Download product_images HTTP URLs onto disk and rewrite DB URLs to PUBLIC_ASSET_BASE.

Unlike the old mirror helper, this does NOT skip api.karzartools.com URLs when the
local file is missing — remote URLs are treated as temporary fetch sources only.

Usage:
  .venv/bin/python scripts/materialize_product_images.py
  .venv/bin/python scripts/materialize_product_images.py --brand-ilike INSIZE
  .venv/bin/python scripts/materialize_product_images.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import mimetypes
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.database import async_session_maker
from app.db.models.product import Brand, Product, ProductImage

UPLOAD_ROOT = Path(__file__).resolve().parents[1] / "data" / "uploads" / "products"
PUBLIC_PREFIX = "/static/uploads/products"
USER_AGENT = (
    "Mozilla/5.0 (compatible; KarzarImageMaterialize/1.0; +https://www.karzartools.com)"
)


def _public_base() -> str:
    return os.getenv("PUBLIC_ASSET_BASE", "https://api.karzartools.com").rstrip("/")


def _ext_from_url_or_ct(url: str, content_type: str | None) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return suffix
    if content_type:
        guess = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guess == ".jpe":
            return ".jpg"
        if guess:
            return guess
    return ".jpg"


def _local_path_for_public_url(url: str) -> Path | None:
    """Map https://host/static/uploads/products/ID/file.jpg → data/uploads/products/ID/file.jpg"""
    parsed = urlparse(url)
    marker = "/static/uploads/products/"
    if marker not in parsed.path:
        return None
    rel = parsed.path.split(marker, 1)[1]
    return UPLOAD_ROOT / rel


async def materialize_one(
    client: httpx.AsyncClient,
    image: ProductImage,
    *,
    dry_run: bool,
) -> str:
    url = (image.image_url or "").strip()
    if not url.startswith("http"):
        return "skip_non_http"

    # Already our static URL and file present → done.
    existing = _local_path_for_public_url(url)
    if existing is not None and existing.is_file():
        return "skip_file_exists"

    # If URL is already our static path but file missing, download from that URL
    # into the exact path encoded in the URL.
    if existing is not None:
        dest = existing
        public_url = url.split("?")[0]
    else:
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
        dest_dir = UPLOAD_ROOT / str(image.product_id)
        # ext unknown until fetch; placeholder name updated after response
        dest = dest_dir / f"{digest}.bin"
        public_url = None  # set after we know ext

    try:
        resp = await client.get(url, follow_redirects=True)
        if resp.status_code != 200 or not resp.content:
            return f"http_{resp.status_code}"
        ext = _ext_from_url_or_ct(url, resp.headers.get("content-type"))
        if public_url is None:
            dest = UPLOAD_ROOT / str(image.product_id) / f"{digest}{ext}"
            public_url = f"{_public_base()}{PUBLIC_PREFIX}/{image.product_id}/{dest.name}"
        elif dest.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            dest = dest.with_suffix(ext)

        if dry_run:
            return f"would_write->{dest.name}"

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(resp.content)
        if image.image_url != public_url:
            image.image_url = public_url
            return "materialized_rewrote"
        return "materialized_same_url"
    except Exception as exc:  # noqa: BLE001
        return f"error:{type(exc).__name__}:{exc}"


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--brand-ilike", default=None, help="Filter by brand name ILIKE")
    parser.add_argument("--only-remote", action="store_true", help="Skip urls already on our host")
    args = parser.parse_args()

    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    stats: dict[str, int] = {}

    async with async_session_maker() as session:
        stmt = select(ProductImage).order_by(ProductImage.id)
        if args.brand_ilike:
            stmt = (
                select(ProductImage)
                .join(Product, Product.id == ProductImage.product_id)
                .join(Brand, Brand.id == Product.brand_id)
                .where(Brand.name.ilike(f"%{args.brand_ilike}%"))
                .where(Product.deleted_at.is_(None))
                .order_by(ProductImage.id)
            )
        result = await session.execute(stmt)
        images = list(result.scalars().unique().all())
        if args.only_remote:
            images = [
                img
                for img in images
                if "karzartools.com" not in (img.image_url or "")
                or _local_path_for_public_url(img.image_url or "") is None
                or not (_local_path_for_public_url(img.image_url or "") or Path()).is_file()
            ]

        print(f"candidates={len(images)} dry_run={args.dry_run}")
        limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
        async with httpx.AsyncClient(
            timeout=60.0,
            headers={"User-Agent": USER_AGENT},
            limits=limits,
        ) as client:
            for i, image in enumerate(images, 1):
                status = await materialize_one(client, image, dry_run=args.dry_run)
                stats[status] = stats.get(status, 0) + 1
                if i % 25 == 0:
                    if not args.dry_run:
                        await session.commit()
                    print(f"… {i}/{len(images)} {stats}")

        if not args.dry_run:
            await session.commit()

    print("done", stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
