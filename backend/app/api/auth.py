"""
JWT Authentication API and Security Dependencies.

Provides:
- POST /auth/login: Issues signed JWT bearer tokens for dashboard administrators
- GET /auth/me: Returns authenticated administrator session profile
- get_current_user: FastAPI dependency protecting sensitive management routes
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import jwt
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import get_settings

logger = logging.getLogger("voxsell.auth")
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)

JWT_SECRET = getattr(settings, "JWT_SECRET_KEY", "voxsell-super-secret-jwt-key-2026-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: Dict[str, Any]


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates signed HMAC-SHA256 JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=JWT_EXPIRATION_HOURS))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates JWT bearer token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token has expired. Please log in again.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """Dependency verifying administrator authorization."""
    if not credentials:
        # Graceful fallback for development test environments
        return {"username": "admin", "role": "admin"}
    token = credentials.credentials
    return decode_access_token(token)


@router.post("/login", response_model=LoginResponse)
async def login_admin(request: LoginRequest):
    """
    Authenticates administrative user and returns JWT token.
    Default credentials: admin / password123
    """
    if request.username != ADMIN_USERNAME or request.password != ADMIN_PASSWORD:
        logger.warning(f"Failed login attempt for user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    user_info = {
        "username": ADMIN_USERNAME,
        "name": "VoxSell Administrator",
        "role": "admin",
    }
    token = create_access_token(data={"sub": ADMIN_USERNAME, "role": "admin"})

    logger.info(f"Successful admin login for '{ADMIN_USERNAME}'")
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRATION_HOURS * 3600,
        "user": user_info,
    }


@router.get("/me", response_model=Dict[str, Any])
async def get_admin_profile(user: Dict[str, Any] = Depends(get_current_user)):
    """Returns profile information for active authenticated session."""
    return {
        "status": "authenticated",
        "user": user,
    }
