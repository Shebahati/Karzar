"""Cryptographically opaque order tracking codes."""

import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import commerce as crud_commerce

_TRACKING_RANDOM_HEX_LEN = 6
_MAX_GENERATION_ATTEMPTS = 10


def generate_tracking_code(prefix: str) -> str:
    """Build a non-guessable tracking code such as ``KZ-A1B2C3D4E5F6``."""
    token = secrets.token_hex(_TRACKING_RANDOM_HEX_LEN).upper()
    return f"{prefix}{token}"


async def generate_unique_tracking_code(db: AsyncSession, prefix: str) -> str:
    """Return a tracking code that is not already present in ``orders``."""
    for _ in range(_MAX_GENERATION_ATTEMPTS):
        code = generate_tracking_code(prefix)
        existing = await crud_commerce.get_order_by_tracking_code(db, code)
        if existing is None:
            return code
    raise RuntimeError("Unable to generate a unique order tracking code")
