# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
import bcrypt  # این بار مستقیماً از خود bcrypt استفاده می‌کنیم
from app.core.config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """بررسی می‌کند که آیا پسورد وارد شده با هشِ داخل دیتابیس همخوانی دارد یا خیر"""
    # bcrypt برای مقایسه نیاز دارد که رشته‌ها به بایت (utf-8) تبدیل شوند
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )

def get_password_hash(password: str) -> str:
    """تبدیل پسورد خام به رشته‌ای غیرقابل بازگشت (هش)"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')  # در دیتابیس به صورت رشته ذخیره می‌کنیم

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """تولید توکن JWT برای کاربری که با موفقیت لاگین کرده است"""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt