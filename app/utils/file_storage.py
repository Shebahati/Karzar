"""Local filesystem storage for admin product image uploads."""

from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import UploadFile

from app.core.constants import ALLOWED_IMAGE_URL_EXTENSIONS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_ROOT = PROJECT_ROOT / "data" / "uploads"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _safe_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_IMAGE_URL_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_IMAGE_URL_EXTENSIONS))
        raise ValueError(f"Unsupported image type. Allowed extensions: {allowed}")
    return suffix


async def save_product_image_upload(product_id: int, upload: UploadFile) -> str:
    """Persist an uploaded image and return its public URL path."""
    if not upload.filename:
        raise ValueError("Uploaded file must have a filename")
    extension = _safe_extension(upload.filename)
    content = await upload.read()
    if not content:
        raise ValueError("Uploaded file is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("Uploaded file exceeds the 5 MB size limit")

    target_dir = UPLOAD_ROOT / "products" / str(product_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{secrets.token_hex(8)}{extension}"
    target_path = target_dir / filename
    target_path.write_bytes(content)
    return f"/static/uploads/products/{product_id}/{filename}"
