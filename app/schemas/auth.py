# app/schemas/auth.py
from pydantic import BaseModel


class TokenRequest(BaseModel):
    """Request model for token generation."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Response model for token generation."""
    access_token: str
    token_type: str
    expires_in: int
