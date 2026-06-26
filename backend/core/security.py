from datetime import datetime, timedelta, timezone
import uuid
import bcrypt
from jose import JWTError, jwt
from core.config import settings

# Name of the httpOnly cookie used to store the refresh token.
REFRESH_COOKIE_NAME = "refresh_token"

def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

def create_token(data: dict, expires_delta: timedelta) -> str:
    """Sign a JWT with the configured SECRET_KEY."""
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

def set_refresh_cookie(response, token: str) -> None:
    """Attach the refresh token as an httpOnly cookie."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,         # Not accessible from JavaScript
        secure=False,          # Set to True in production (requires HTTPS)
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
    )

def decode_token(token: str, require_refresh: bool = False) -> uuid.UUID:
    """
    Decodes a JWT token and returns the user UUID.
    Raises ValueError if invalid, expired, or wrong type.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        if require_refresh and payload.get("type") != "refresh":
            raise ValueError("Token is not a refresh token")
            
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise ValueError("Token missing sub claim")
        return uuid.UUID(user_id_str)
    except JWTError as e:
        raise ValueError(f"JWT Error: {str(e)}")
