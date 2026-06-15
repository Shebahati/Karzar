# app/api/endpoints/auth.py
from fastapi import APIRouter, HTTPException, status
from datetime import timedelta

from app.schemas.auth import TokenRequest, TokenResponse
from app.core.security import create_access_token
from app.core.config import settings

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get access token",
    tags=["Authentication"],
)
async def login(credentials: TokenRequest):
    """
    Login endpoint to get an access token.
    
    For this MVP, we accept any non-empty username.
    In production, validate against a database.
    """
    if not credentials.username or not credentials.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # In production, verify credentials against user database
    # For MVP, we just check if both are provided
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": credentials.username},
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
