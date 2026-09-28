"""Shared business constants used across backend and frontend contract."""

# Iranian Rial conversion: all API prices are in Tomans; gateway expects Rials.
TOMAN_TO_RIAL: int = 10

# Default VAT *placeholder* for new products via Product create schema / admin form.
# This is NOT proven authoritative embedded-VAT metadata for Hesabfa.
# ORM/DB server_default remains 0 for rows that omit the column (imports/scripts).
# Customer payable MUST ignore this field (base_price is final). Do not mass-normalize.
DEFAULT_TAX_PERCENT: int = 9

# Product image constraints (URL-based uploads in admin panel).
MAX_PRODUCT_IMAGES: int = 10
# SVG intentionally excluded (SEC-21): scriptable markup must not be stored as product media.
ALLOWED_IMAGE_URL_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".webp", ".gif"}
)
