"""Password hashing, JWT access tokens, and step-up authentication tokens."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.core.errors import ErrorCode, api_error

STEP_UP_TOKEN_TYPE = "step_up"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Constant-time bcrypt password comparison."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    """Hash a plaintext password with a freshly generated bcrypt salt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def create_access_token(
    subject: Union[str, Any],
    *,
    token_version: int = 0,
    expires_delta: timedelta | None = None,
) -> str:
    """Issue a short-lived bearer token for API authentication."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
        "ver": token_version,
        "iat": datetime.now(timezone.utc).timestamp(),
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token() -> str:
    """Issue an opaque refresh token stored hashed server-side."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """One-way hash for refresh token persistence."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_step_up_token(subject: Union[str, Any]) -> tuple[str, int]:
    """Issue a scoped token authorizing destructive admin operations."""
    expires_in = settings.STEP_UP_TOKEN_EXPIRE_MINUTES * 60
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.STEP_UP_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": STEP_UP_TOKEN_TYPE,
    }
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, expires_in


def decode_token(token: str) -> dict:
    """Decode and verify a JWT; raises 401 on signature or expiry failure."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise api_error(
            401,
            error_code=ErrorCode.UNAUTHORIZED,
            message="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def verify_step_up_token(token: str) -> dict:
    """Validate token type and subject for step-up authorization."""
    payload = decode_token(token)
    if payload.get("type") != STEP_UP_TOKEN_TYPE:
        raise api_error(
            403,
            error_code=ErrorCode.STEP_UP_INVALID,
            message="Invalid step-up token",
        )
    subject = payload.get("sub")
    if not subject:
        raise api_error(
            403,
            error_code=ErrorCode.STEP_UP_INVALID,
            message="Invalid step-up token subject",
        )
    return payload


def verify_admin_pin(pin: str) -> bool:
    """Compare submitted PIN against configured value using timing-safe digest."""
    configured_pin = settings.ADMIN_STEP_UP_PIN
    if not configured_pin:
        return False
    return secrets.compare_digest(pin, configured_pin)
