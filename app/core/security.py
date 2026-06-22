# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

import bcrypt
from jose import JWTError, jwt

import secrets

from app.core.config import settings
from app.core.errors import ErrorCode, api_error

STEP_UP_TOKEN_TYPE = "step_up"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def create_access_token(subject: Union[str, Any], expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_step_up_token(subject: Union[str, Any]) -> tuple[str, int]:
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
    configured_pin = settings.ADMIN_STEP_UP_PIN
    if not configured_pin:
        return False
    return secrets.compare_digest(pin, configured_pin)
