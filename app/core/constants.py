"""Shared business constants used across backend and frontend contract."""

# Iranian Rial conversion: all API prices are in Tomans; gateway expects Rials.
TOMAN_TO_RIAL: int = 10

# Default VAT rate for *new* products created via the Product create schema / admin form.
# This is accounting metadata embedded in the gross catalog price — it must NEVER be
# added on top of base_price at checkout or payment. ORM/DB server_default remains 0
# for rows that omit the column (imports/scripts); do not mass-normalize live catalog.
DEFAULT_TAX_PERCENT: int = 9

# Product image constraints (URL-based uploads in admin panel).
MAX_PRODUCT_IMAGES: int = 10
# SVG intentionally excluded (SEC-21): scriptable markup must not be stored as product media.
ALLOWED_IMAGE_URL_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".webp", ".gif"}
)
