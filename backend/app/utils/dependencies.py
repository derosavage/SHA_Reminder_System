"""
FastAPI Dependencies
Auth middleware, rate limiting, language resolution, and common dependency
injection.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Header, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db
from app.core.i18n import (
    DEFAULT_LANGUAGE,
    coerce_language,
    parse_accept_language,
)
from app.models.user import User, UserStatus
from app.services.auth_service import AuthService

security = HTTPBearer()


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> str:
    """
    Dependency to extract and verify the current user ID from JWT token.
    """
    token = credentials.credentials
    payload = AuthService.verify_token(token)

    if payload is None:
        raise _unauthorized("Invalid or expired authentication token")

    if payload.get("type") not in (None, "access"):
        raise _unauthorized("Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise _unauthorized("Token missing user identifier")

    # A token stays valid for 120 minutes after it is issued, so an account
    # deleted or suspended in the meantime kept working. Confirm the account
    # still exists and is allowed to use the API.
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if (
        user is None
        or user.deleted_at is not None
        or user.status in (UserStatus.DELETED, UserStatus.SUSPENDED)
    ):
        raise _unauthorized("Account is no longer active")

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


async def get_request_language(
    lang: Optional[str] = Query(
        None, description="Explicit language override (sw or en)"
    ),
    accept_language: Optional[str] = Header(None),
    user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db),
) -> str:
    """
    Resolve the language a response should be written in.

    Priority: explicit ?lang= parameter, then the Accept-Language header,
    then the authenticated user's stored preference, then the default
    language. Unauthenticated requests simply skip the user preference.
    """
    explicit = coerce_language(lang, fallback="")
    if explicit:
        return explicit

    header_match = parse_accept_language(accept_language)
    if header_match:
        return header_match

    if user_id:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is not None:
            return coerce_language(
                user.preferred_language, fallback=DEFAULT_LANGUAGE
            )

    return DEFAULT_LANGUAGE