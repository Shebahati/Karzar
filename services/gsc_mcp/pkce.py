from __future__ import annotations

import base64
import hashlib
import secrets
import string

_PKCE_CHARSET = string.ascii_letters + string.digits + "-._~"


def generate_code_verifier(length: int = 64) -> str:
    if length < 43 or length > 128:
        raise ValueError("code_verifier length must be between 43 and 128")
    return "".join(secrets.choice(_PKCE_CHARSET) for _ in range(length))


def code_challenge_s256(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
