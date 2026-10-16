"""
FastAPI Dependencies
Auth middleware, rate limiting, and common dependency injection.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db
from app.services.auth_service import AuthService

security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    Dependency to extract and verify the current user ID from JWT token.
    """
    token = credentials.credentials
    payload = AuthService.verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identifier",
        )

    return user_id


async def get_optional_user_id(
    authorization: Optional[str] = Header(None),
) -> Optional[str]:
    """
    Optional auth dependency - extracts user ID if token present.
    Used for endpoints that work both authenticated and unauthenticated.
    """
    if not authorization:
        return None

    try:
        token = authorization.replace("Bearer ", "")
        payload = AuthService.verify_token(token)
        if payload:
            return payload.get("sub")
    except Exception:
        pass
    return None


async def get_client_info(
    user_agent: Optional[str] = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
) -> dict:
    """Extract client info from request headers."""
    return {
        "user_agent": user_agent,
        "ip_address": x_forwarded_for.split(",")[0].strip()
        if x_forwarded_for
        else None,
    }