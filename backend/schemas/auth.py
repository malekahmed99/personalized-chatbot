"""
schemas/auth.py — Pydantic schemas for authentication endpoints.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class RegisterIn(BaseModel):
    """Request body for POST /api/auth/register."""
    identifier: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=6)


class LoginIn(BaseModel):
    """Request body for POST /api/auth/login."""
    identifier: str
    password: str


class TokenOut(BaseModel):
    """Response body for login and token refresh."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


class UserOut(BaseModel):
    """Public representation of a user. Never includes password_hash."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identifier: str
    created_at: datetime
