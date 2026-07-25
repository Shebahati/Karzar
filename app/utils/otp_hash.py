"""OTP code hashing helpers (HMAC-SHA256 with server pepper)."""

import hashlib
import hmac

from app.core.config import settings


def hash_otp_code(code: str) -> str:
    """Hash an OTP with HMAC-SHA256 using SECRET_KEY as pepper (SEC-04 / SEC-20)."""
    pepper = (settings.SECRET_KEY or "").encode("utf-8")
    return hmac.new(pepper, code.strip().encode("utf-8"), hashlib.sha256).hexdigest()
