"""OTP code hashing helpers."""

import hashlib


def hash_otp_code(code: str) -> str:
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()
