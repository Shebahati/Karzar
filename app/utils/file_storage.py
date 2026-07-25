"""Local filesystem storage for admin product/brand/category image uploads."""

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


async def _read_upload(upload: UploadFile) -> tuple[str, bytes]:
    if not upload.filename:
        raise ValueError("Uploaded file must have a filename")
    extension = _safe_extension(upload.filename)
    content = await upload.read()
    if not content:
        raise ValueError("Uploaded file is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("Uploaded file exceeds the 5 MB size limit")
    return extension, content


async def save_product_image_upload(product_id: int, upload: UploadFile) -> str:
    """Persist an uploaded image and return its public URL path."""
    extension, content = await _read_upload(upload)
    target_dir = UPLOAD_ROOT / "products" / str(product_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{secrets.token_hex(8)}{extension}"
    target_path = target_dir / filename
    target_path.write_bytes(content)
    return f"/static/uploads/products/{product_id}/{filename}"


async def save_brand_logo_upload(brand_id: int, upload: UploadFile) -> str:
    """Persist a brand logo and return its public URL path."""
    extension, content = await _read_upload(upload)
    target_dir = UPLOAD_ROOT / "brands" / str(brand_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"logo-{secrets.token_hex(8)}{extension}"
    target_path = target_dir / filename
    target_path.write_bytes(content)
    return f"/static/uploads/brands/{brand_id}/{filename}"


def save_brand_logo_bytes(brand_id: int, content: bytes, extension: str) -> str:
    """Persist raw logo bytes (for seed scripts) and return public URL path."""
    suffix = extension.lower() if extension.startswith(".") else f".{extension.lower()}"
    if suffix not in ALLOWED_IMAGE_URL_EXTENSIONS:
        raise ValueError(f"Unsupported image type: {suffix}")
    if not content:
        raise ValueError("Logo content is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("Logo exceeds the 5 MB size limit")
    target_dir = UPLOAD_ROOT / "brands" / str(brand_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"logo-{secrets.token_hex(8)}{suffix}"
    (target_dir / filename).write_bytes(content)
    return f"/static/uploads/brands/{brand_id}/{filename}"


async def save_category_image_upload(category_id: int, upload: UploadFile) -> str:
    """Persist a category card image and return its public URL path."""
    extension, content = await _read_upload(upload)
    target_dir = UPLOAD_ROOT / "categories" / str(category_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"image-{secrets.token_hex(8)}{extension}"
    target_path = target_dir / filename
    target_path.write_bytes(content)
    return f"/static/uploads/categories/{category_id}/{filename}"


def save_category_image_bytes(category_id: int, content: bytes, extension: str) -> str:
    """Persist raw category image bytes (for seed scripts) and return public URL path."""
    suffix = extension.lower() if extension.startswith(".") else f".{extension.lower()}"
    if suffix not in ALLOWED_IMAGE_URL_EXTENSIONS:
        raise ValueError(f"Unsupported image type: {suffix}")
    if not content:
        raise ValueError("Image content is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("Image exceeds the 5 MB size limit")
    target_dir = UPLOAD_ROOT / "categories" / str(category_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"image-{secrets.token_hex(8)}{suffix}"
    (target_dir / filename).write_bytes(content)
    return f"/static/uploads/categories/{category_id}/{filename}"
