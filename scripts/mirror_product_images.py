#!/usr/bin/env python3
"""Download remote product images into local uploads and rewrite DB URLs.

Run inside the API container or on the VPS with DB env loaded:
  docker compose ... exec -T app python scripts/mirror_product_images.py
"""

from __future__ import annotations

import asyncio
import hashlib
import mimetypes
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.database import async_session_maker
from app.db.models.product import ProductImage

UPLOAD_ROOT = Path(__file__).resolve().parents[1] / "data" / "uploads" / "products"
PUBLIC_PREFIX = "/static/uploads/products"
USER_AGENT = (
    "Mozilla/5.0 (compatible; KarzarImageMirror/1.0; +https://www.karzartools.com)"
)


def _ext_from_url_or_ct(url: str, content_type: str | None) -> str:
    path = urlparse(url).path
    suffix = Path(path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return suffix
    if content_type:
        guess = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guess == ".jpe":
            return ".jpg"
        if guess:
            return guess
    return ".jpg"


def _public_base() -> str:
    import os

    return os.getenv("PUBLIC_ASSET_BASE", "https://api.karzartools.com").rstrip("/")


async def mirror_one(
    client: httpx.AsyncClient,
    image: ProductImage,
    *,
    dry_run: bool,
) -> str:
    url = (image.image_url or "").strip()
    if not url.startswith("http"):
        return "skip_non_http"
    if "/static/uploads/" in url and "karzartools.com" in url:
        return "skip_local"

    dest_dir = UPLOAD_ROOT / str(image.product_id)
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]

    try:
        resp = await client.get(url, follow_redirects=True)
        if resp.status_code != 200 or not resp.content:
            return f"http_{resp.status_code}"
        ext = _ext_from_url_or_ct(url, resp.headers.get("content-type"))
        filename = f"{digest}{ext}"
        dest = dest_dir / filename
        public_url = f"{_public_base()}{PUBLIC_PREFIX}/{image.product_id}/{filename}"
        if dry_run:
            return f"would_mirror->{public_url}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(resp.content)
        image.image_url = public_url
        return "mirrored"
    except Exception as exc:  # noqa: BLE001 — batch job; continue
        return f"error:{type(exc).__name__}"


async def main() -> int:
    dry_run = "--dry-run" in sys.argv
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    stats: dict[str, int] = {}

    async with async_session_maker() as session:
        result = await session.execute(select(ProductImage).order_by(ProductImage.id))
        images = list(result.scalars().all())
        print(f"found {len(images)} product_images (dry_run={dry_run})")

        limits = httpx.Limits(max_connections=8, max_keepalive_connections=4)
        async with httpx.AsyncClient(
            timeout=45.0,
            headers={"User-Agent": USER_AGENT},
            limits=limits,
        ) as client:
            for image in images:
                status = await mirror_one(client, image, dry_run=dry_run)
                stats[status] = stats.get(status, 0) + 1
                if stats.get("mirrored", 0) % 25 == 0 and status == "mirrored":
                    await session.commit()
                    print(f"… mirrored {stats['mirrored']}")

        if not dry_run:
            await session.commit()

    print("done", stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
