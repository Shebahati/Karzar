"""Shared business constants used across backend and frontend contract."""

# Iranian Rial conversion: all API prices are in Tomans; gateway expects Rials.
TOMAN_TO_RIAL: int = 10

# Default VAT rate for new products (Iran standard VAT is 9%).
DEFAULT_TAX_PERCENT: int = 9

# Product image constraints (URL-based uploads in admin panel).
MAX_PRODUCT_IMAGES: int = 10
ALLOWED_IMAGE_URL_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
)
