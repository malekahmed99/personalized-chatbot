"""
routers/auth.py — Authentication endpoints.

POST /register  — Create a new user account.
POST /login     — Authenticate; issue JWT access token + httpOnly refresh cookie.
POST /refresh   — Issue a new access token from a valid refresh cookie.
POST /logout    — Clear the refresh cookie, return 204.
"""
from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import (
    REFRESH_COOKIE_NAME,
    create_token,
    decode_token,
    hash_password,
    set_refresh_cookie,
    verify_password,
)
from core.database import get_db
from models.user import User
from schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter()

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterIn,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Create a new user account.
    Returns 409 Conflict if the identifier is already taken.
    """
    existing = await db.execute(
        select(User).where(User.identifier == body.identifier)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this identifier already exists.",
        )

    user = User(
        identifier=body.identifier,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
async def login(
    body: LoginIn,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Authenticate a user.
    On success: returns a short-lived JWT access token in the body, and sets a
    long-lived refresh token as an httpOnly cookie.
    Returns 401 without specifying which field was wrong (security best practice).
    """
    result = await db.execute(
        select(User).where(User.identifier == body.identifier)
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_expires = timedelta(minutes=settings.access_token_expire_minutes)
    refresh_expires = timedelta(days=settings.refresh_token_expire_days)

    access_token = create_token({"sub": str(user.id)}, access_expires)
    refresh_token = create_token({"sub": str(user.id), "type": "refresh"}, refresh_expires)

    set_refresh_cookie(response, refresh_token)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }


@router.post("/refresh", response_model=TokenOut)
async def refresh_token(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Issue a new access token using the httpOnly refresh cookie.
    Returns 401 if the cookie is missing, expired, or tampered with.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if refresh_token is None:
        raise credentials_exception

    try:
        user_id = decode_token(refresh_token, require_refresh=True)
    except ValueError:
        raise credentials_exception

    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    access_expires = timedelta(minutes=settings.access_token_expire_minutes)
    new_access_token = create_token({"sub": str(user.id)}, access_expires)

    # Rotate the refresh token
    refresh_expires = timedelta(days=settings.refresh_token_expire_days)
    new_refresh_token = create_token({"sub": str(user.id), "type": "refresh"}, refresh_expires)
    set_refresh_cookie(response, new_refresh_token)

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    """
    Clear the httpOnly refresh cookie.
    """
    response.delete_cookie(key=REFRESH_COOKIE_NAME, httponly=True, samesite="lax")
