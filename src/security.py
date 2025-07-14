import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import AUTH_DB_PATH # We might need this later
from .database_utils import get_user_profile

# --- Configuration ---

# This should be a long, random string. You can generate one with:
# openssl rand -hex 32
# It's best practice to load this from an environment variable, not hardcode it.
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "a_very_insecure_default_secret_key_for_dev_only")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8 # 8 hours

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

def get_current_active_user(token: str) -> Dict[str, Any]:
    """
    Decodes the JWT token, validates it, and fetches the user's profile.
    This function will be used as a FastAPI dependency.
    """
    if not token:
        raise AuthException(detail="Authentication token is missing.")
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise AuthException(detail="Invalid token: Subject (email) missing.")
    except JWTError:
        raise AuthException(detail="Invalid token: Could not validate credentials.")

    user_profile = get_user_profile(email)
    if user_profile is None:
        raise AuthException(detail="Invalid token: User not found.")
    
    return user_profile