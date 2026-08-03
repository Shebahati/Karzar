"""Image byte validation and presentation heuristics."""

from __future__ import annotations

import struct
from io import BytesIO

from .contracts import DiscoveryError

MIN_BYTES = 10 * 1024
MIN_DIM = 250


def detect_signature(data: bytes) -> tuple[str | None, str | None]:
    if len(data) < 12:
        return None, None
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg", "jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", "png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif", "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    return None, None


def looks_like_html(data: bytes) -> bool:
    head = data[:512].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html") or b"<html" in head[:200]


def _jpeg_size(data: bytes) -> tuple[int | None, int | None]:
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            return None, None
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", data[i + 5 : i + 9])
            return int(w), int(h)
        if marker in (0xD9, 0xDA):
            break
        length = struct.unpack(">H", data[i + 2 : i + 4])[0]
        i += 2 + length
    return None, None


def extract_dimensions(data: bytes, mime: str) -> tuple[int | None, int | None]:
    try:
        from PIL import Image  # type: ignore

        with Image.open(BytesIO(data)) as im:
            return int(im.width), int(im.height)
    except Exception:
        pass
    try:
        if mime == "image/jpeg":
            return _jpeg_size(data)
        if mime == "image/png" and len(data) >= 24:
            w, h = struct.unpack(">II", data[16:24])
            return int(w), int(h)
        if mime == "image/gif" and len(data) >= 10:
            w, h = struct.unpack("<HH", data[6:10])
            return int(w), int(h)
    except Exception:
        return None, None
    return None, None


def structural_verify(data: bytes, mime: str) -> None:
    """Reject truncated/corrupt images. Uses Pillow.verify when available."""
    try:
        from PIL import Image  # type: ignore

        with Image.open(BytesIO(data)) as im:
            im.verify()
        # verify() leaves image unusable; reopen for sanity
        with Image.open(BytesIO(data)) as im2:
            im2.load()
        return
    except Exception as e:
        # If Pillow missing, fall back to signature + SOF presence for JPEG
        if type(e).__name__ == "ModuleNotFoundError":
            pass
        else:
            raise DiscoveryError("image", "corrupt_image", f"structural verify failed: {e}") from e

    if mime == "image/jpeg":
        w, h = _jpeg_size(data)
        if w is None or h is None:
            raise DiscoveryError("image", "corrupt_image", "jpeg SOF missing or truncated")
    elif mime == "image/png":
        if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
            raise DiscoveryError("image", "corrupt_image", "malformed png")
        # Require IEND
        if b"IEND" not in data[-12:]:
            raise DiscoveryError("image", "corrupt_image", "png missing IEND")


def validate_image_bytes(
    data: bytes,
    *,
    content_type: str,
    final_url: str,
    min_bytes: int = MIN_BYTES,
    min_dim: int = MIN_DIM,
) -> tuple[str, str, int | None, int | None]:
    if looks_like_html(data) or "html" in (content_type or "") or "xml" in (content_type or ""):
        raise DiscoveryError("image", "invalid_content_type", f"HTML/XML body ctype={content_type}")
    mime, ext = detect_signature(data)
    if not mime or not ext:
        raise DiscoveryError("image", "invalid_image_signature", "unrecognized magic")
    if content_type and not content_type.startswith("image/") and content_type not in (
        "application/octet-stream",
        "",
    ):
        raise DiscoveryError("image", "invalid_content_type", f"content-type={content_type}")
    if len(data) == 0:
        raise DiscoveryError("image", "corrupt_image", "zero-byte")
    if len(data) < min_bytes:
        raise DiscoveryError("image", "image_too_small", f"byte_size={len(data)}")
    lower = final_url.lower()
    if any(x in lower for x in ("placeholder", "no-image", "image-not-found", "notfound")):
        raise DiscoveryError("image", "placeholder_detected", lower)
    structural_verify(data, mime)
    w, h = extract_dimensions(data, mime)
    if w is not None and h is not None and (w < min_dim or h < min_dim):
        raise DiscoveryError("image", "image_too_small", f"dimensions={w}x{h}")
    return mime, ext, w, h


def estimate_foreground_occupancy(
    *,
    data: bytes,
    width: int | None,
    height: int | None,
    byte_size: int,
) -> tuple[str, str]:
    note_parts: list[str] = []
    needs_review = False
    if width and height and width > 0 and height > 0:
        bpp = byte_size / (width * height)
        if bpp < 0.020:
            needs_review = True
            note_parts.append(f"low_bytes_per_pixel={bpp:.4f}")
    try:
        from PIL import Image  # type: ignore

        with Image.open(BytesIO(data)) as im:
            sample = im.convert("RGB").resize((min(100, im.width), min(100, im.height)))
            # Prefer get_flattened_data (Pillow ≥10.1); avoid deprecated Image.getdata().
            if hasattr(sample, "get_flattened_data"):
                flat = list(sample.get_flattened_data())
                pixels = list(zip(flat[0::3], flat[1::3], flat[2::3], strict=False))
            else:  # pragma: no cover — older Pillow fallback
                pixels = list(sample.getdata())  # type: ignore[attr-defined]
            if pixels:
                near_white = sum(1 for r, g, b in pixels if r >= 245 and g >= 245 and b >= 245)
                white_ratio = near_white / len(pixels)
                if white_ratio >= 0.72:
                    needs_review = True
                    note_parts.append(f"near_white_ratio={white_ratio:.3f}")
    except Exception:
        pass
    if needs_review:
        return "needs_presentation_review", ";".join(note_parts) or "sparse_or_whitespace_heavy"
    return "ok", ""
