"""Ensure common image MIME types are registered for StaticFiles/FileResponse.

Starlette resolves ``Content-Type`` via ``mimetypes.guess_type``. Some runtime
MIME databases (notably slim container images) omit ``.webp``, which causes
``/static/uploads/**/*.webp`` to be served as ``application/octet-stream``.
"""

from __future__ import annotations

import mimetypes

# Extension → type. ``strict=True`` (default) keeps these in types_map.
_IMAGE_MIME_TYPES: tuple[tuple[str, str], ...] = (
    (".webp", "image/webp"),
    (".jpg", "image/jpeg"),
    (".jpeg", "image/jpeg"),
    (".png", "image/png"),
)


def ensure_image_static_mime_types() -> None:
    """Register image MIME types used by product/static upload serving."""
    for ext, mime in _IMAGE_MIME_TYPES:
        mimetypes.add_type(mime, ext)
