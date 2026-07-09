"""Validation helpers for product image URL endpoints."""

from urllib.parse import urlparse

from app.core.constants import ALLOWED_IMAGE_URL_EXTENSIONS, MAX_PRODUCT_IMAGES


def validate_product_image_url(image_url: str) -> str:
    """Ensure the image URL looks like a supported image resource."""
    normalized = image_url.strip()
    if not normalized:
        raise ValueError("image_url cannot be empty")

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("image_url must use http or https")

    path_lower = parsed.path.lower()
    if not any(path_lower.endswith(ext) for ext in ALLOWED_IMAGE_URL_EXTENSIONS):
        allowed = ", ".join(sorted(ALLOWED_IMAGE_URL_EXTENSIONS))
        raise ValueError(f"image_url must point to an image file ({allowed})")

    if len(normalized) > 500:
        raise ValueError("image_url exceeds maximum length of 500 characters")
    return normalized


def ensure_image_count_within_limit(current_count: int) -> None:
    if current_count >= MAX_PRODUCT_IMAGES:
        raise ValueError(f"A product may have at most {MAX_PRODUCT_IMAGES} images")
