import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, cast
from jose import JWTError, jwt
from passlib.context import CryptContext

from .database_utils import get_user_profile
from .config import UserProfile

# --- Configuration ---

_INSECURE_DEFAULT = "a_very_insecure_default_secret_key_for_dev_only"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", _INSECURE_DEFAULT)
if SECRET_KEY == _INSECURE_DEFAULT:
    import sys
    # Allow insecure default only when running locally (no RENDER_EXTERNAL_URL set)
    if os.getenv("RENDER_EXTERNAL_URL"):
        raise RuntimeError(
            "FATAL: JWT_SECRET_KEY is not set or is using the insecure default. "
            "Set a strong random value via: openssl rand -hex 32"
        )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 8)))

# We aren't using passwords yet, but this is the standard way to set it up.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --- Token Creation ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a new JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# --- Token Verification and User Retrieval ---

class AuthException(Exception):
    """Custom exception for authentication errors."""
    def __init__(self, detail: str):
        self.detail = detail

# At the top of the file
from typing import Optional, Dict, Any, cast

# ...

def get_current_active_user(token: str) -> UserProfile:
    """
    Decodes the JWT token, validates it, and fetches the user's profile.
    This function will be used as a FastAPI dependency.
    """
    if not token:
        raise AuthException(detail="Authentication token is missing.")
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email_from_token: Optional[str] = payload.get("sub")
        if email_from_token is None:
            raise AuthException(detail="Invalid token: Subject (email) missing.")
        
        email: str = email_from_token.lower()

    except JWTError:
        raise AuthException(detail="Invalid token: Could not validate credentials.")

    user_profile = get_user_profile(email)
    if user_profile is None:
        raise AuthException(detail="Invalid token: User not found.")
    
    return user_profile