"""Safe read-only source opens and review derivative generation."""

from __future__ import annotations

import hashlib
import io
import os
import stat as stat_mod
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageOps
from scripts.image_audit.contracts import MAX_HASH_STREAM_CHUNK, MAX_IMAGE_PIXELS
from scripts.image_audit.storage import (
    assert_no_symlink_ancestors,
    assert_real_directory_no_symlink,
)

from .contracts import (
    PREVIEW_JPEG_QUALITY,
    PREVIEW_MAX_EDGE,
    THUMB_MAX_EDGE,
    ReviewError,
)
from .prescreen import compute_prescreen

O_RDONLY = getattr(os, "O_RDONLY", 0)
O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


def _validate_relative_components(storage_root: Path, relative_path: str) -> Path:
    if not relative_path or relative_path.startswith("/") or "\\" in relative_path:
        raise ReviewError("storage", f"invalid relative path: {relative_path!r}")
    parts = [p for p in relative_path.split("/") if p]
    if any(p in {".", ".."} for p in parts):
        raise ReviewError("storage", f"path traversal rejected: {relative_path!r}")
    current = storage_root
    for part in parts:
        current = current / part
        try:
            st = current.lstat()
        except OSError as e:
            raise ReviewError("storage", f"lstat failed for {current}") from e
        if stat_mod.S_ISLNK(st.st_mode):
            raise ReviewError("storage", f"symlink rejected at {current}")
        if not (stat_mod.S_ISDIR(st.st_mode) or stat_mod.S_ISREG(st.st_mode)):
            raise ReviewError("storage", f"non-regular entry rejected at {current}")
    return storage_root.joinpath(*parts)


def open_validated_source_fd(
    storage_root: Path,
    relative_path: str,
    *,
    expected_sha256: str,
) -> tuple[int, dict[str, Any]]:
    """Open source with O_RDONLY|O_NOFOLLOW, verify fstat+sha256; caller must close fd."""
    assert_real_directory_no_symlink(storage_root, label="storage-root")
    assert_no_symlink_ancestors(storage_root, label="storage-root")
    path = _validate_relative_components(storage_root, relative_path)
    try:
        fd = os.open(str(path), O_RDONLY | O_NOFOLLOW)
    except OSError as e:
        raise ReviewError("storage", f"open nofollow failed: {relative_path}") from e
    try:
        st = os.fstat(fd)
        if stat_mod.S_ISLNK(st.st_mode) or not stat_mod.S_ISREG(st.st_mode):
            raise ReviewError("storage", f"source is not a regular file: {relative_path}")
        h = hashlib.sha256()
        while True:
            chunk = os.read(fd, MAX_HASH_STREAM_CHUNK)
            if not chunk:
                break
            h.update(chunk)
        digest = h.hexdigest()
        if digest.lower() != expected_sha256.lower():
            raise ReviewError(
                "storage",
                f"source SHA-256 mismatch for {relative_path}: {digest} != {expected_sha256}",
            )
        os.lseek(fd, 0, os.SEEK_SET)
        meta = {"byte_size": int(st.st_size), "sha256": digest.lower()}
        return fd, meta
    except Exception:
        os.close(fd)
        raise


def _pillow_from_fd(fd: int) -> Image.Image:
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    dup = os.dup(fd)
    try:
        with os.fdopen(dup, "rb") as fp:
            data = fp.read()
    except Exception:
        try:
            os.close(dup)
        except OSError:
            pass
        raise
    bio = io.BytesIO(data)
    im = Image.open(bio)
    im.load()
    return im


def _fit_within(im: Image.Image, max_edge: int) -> Image.Image:
    oriented = ImageOps.exif_transpose(im)
    w, h = oriented.size
    longest = max(w, h)
    if longest <= max_edge:
        return oriented.copy()
    scale = max_edge / float(longest)
    nw = max(1, int(round(w * scale)))
    nh = max(1, int(round(h * scale)))
    return oriented.resize((nw, nh), Image.Resampling.LANCZOS)


def _has_meaningful_alpha(im: Image.Image) -> bool:
    if im.mode in {"RGBA", "LA"}:
        alpha = im.getchannel("A")
        extrema = alpha.getextrema()
        return extrema[0] < 255
    if im.mode == "P" and "transparency" in im.info:
        return True
    return False


def _checkerboard(size: tuple[int, int], cell: int = 8) -> Image.Image:
    w, h = size
    board = Image.new("RGB", (w, h), (220, 220, 220))
    draw = ImageDraw.Draw(board)
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            if ((x // cell) + (y // cell)) % 2 == 0:
                draw.rectangle([x, y, x + cell - 1, y + cell - 1], fill=(180, 180, 180))
    return board


def generate_derivatives(
    storage_root: Path,
    *,
    relative_path: str,
    expected_sha256: str,
    preview_dir: Path,
    thumb_dir: Path,
) -> dict[str, Any]:
    """Create preview + thumb outside storage; never write beside source."""
    fd, src_meta = open_validated_source_fd(
        storage_root, relative_path, expected_sha256=expected_sha256
    )
    try:
        im = _pillow_from_fd(fd)
    finally:
        os.close(fd)

    oriented = ImageOps.exif_transpose(im)
    prescreen = compute_prescreen(oriented)

    asset_id = expected_sha256.lower()
    preview = _fit_within(oriented, PREVIEW_MAX_EDGE)
    thumb = _fit_within(oriented, THUMB_MAX_EDGE)

    use_png = _has_meaningful_alpha(oriented)
    if use_png:
        preview_name = f"{asset_id}.png"
        thumb_name = f"{asset_id}.png"
        preview_buf = io.BytesIO()
        preview.save(preview_buf, format="PNG", optimize=True)
        preview_bytes = preview_buf.getvalue()
        # thumb with checkerboard under transparency
        rgba = thumb.convert("RGBA")
        base = _checkerboard(rgba.size)
        composed = Image.alpha_composite(base.convert("RGBA"), rgba)
        thumb_buf = io.BytesIO()
        composed.convert("RGB").save(thumb_buf, format="JPEG", quality=PREVIEW_JPEG_QUALITY, optimize=True)
        # keep PNG thumb for transparency fidelity when alpha meaningful
        thumb_png = io.BytesIO()
        thumb.save(thumb_png, format="PNG", optimize=True)
        thumb_bytes = thumb_png.getvalue()
        thumb_format = "PNG"
        preview_format = "PNG"
    else:
        preview_name = f"{asset_id}.jpg"
        thumb_name = f"{asset_id}.jpg"
        rgb_preview = preview.convert("RGB")
        rgb_thumb = thumb.convert("RGB")
        preview_buf = io.BytesIO()
        rgb_preview.save(preview_buf, format="JPEG", quality=PREVIEW_JPEG_QUALITY, optimize=True)
        preview_bytes = preview_buf.getvalue()
        thumb_buf = io.BytesIO()
        rgb_thumb.save(thumb_buf, format="JPEG", quality=PREVIEW_JPEG_QUALITY, optimize=True)
        thumb_bytes = thumb_buf.getvalue()
        thumb_format = "JPEG"
        preview_format = "JPEG"

    preview_path = preview_dir / preview_name
    thumb_path = thumb_dir / thumb_name
    if preview_path.exists() or thumb_path.exists():
        raise ReviewError("output", f"derivative collision for asset {asset_id}")
    preview_path.write_bytes(preview_bytes)
    thumb_path.write_bytes(thumb_bytes)

    return {
        "source_sha256": src_meta["sha256"],
        "preview_filename": preview_name,
        "thumb_filename": thumb_name,
        "preview_sha256": hashlib.sha256(preview_bytes).hexdigest(),
        "thumb_sha256": hashlib.sha256(thumb_bytes).hexdigest(),
        "preview_width": preview.width,
        "preview_height": preview.height,
        "thumb_width": thumb.width,
        "thumb_height": thumb.height,
        "preview_format": preview_format,
        "thumb_format": thumb_format,
        "generation_parameters": {
            "preview_max_edge": PREVIEW_MAX_EDGE,
            "thumb_max_edge": THUMB_MAX_EDGE,
            "jpeg_quality": PREVIEW_JPEG_QUALITY,
            "exif_orientation_applied": True,
            "crop": False,
            "watermark_obscured": False,
        },
        "prescreen": prescreen,
        "width": oriented.width,
        "height": oriented.height,
        "alpha_present": prescreen["alpha_present"],
    }
