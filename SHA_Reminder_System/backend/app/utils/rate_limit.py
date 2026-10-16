"""
Minimal in-memory sliding-window rate limiter (per process).
Good enough for a single-instance free-tier deploy; swap for Redis if scaled out.
"""

import time
from collections import defaultdict, deque
from typing import Callable, Deque, Dict

from fastapi import HTTPException, Request, status

from app.core.config import settings

_hits: Dict[str, Deque[float]] = defaultdict(deque)


def client_ip(request: Request) -> str:
    """Best-effort client IP. Uses the right-most X-Forwarded-For entry, which is
    the one appended by our own proxy (left-most entries are client-controlled)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(key: str, limit: int, window_seconds: int = 60) -> None:
    """Raise 429 if `key` exceeded `limit` hits in the last `window_seconds`."""
    now = time.monotonic()
    hits = _hits[key]
    while hits and now - hits[0] > window_seconds:
        hits.popleft()
    if len(hits) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please slow down and try again shortly.",
        )
    hits.append(now)
    if len(_hits) > 10000:  # bound memory
        for k in [k for k, v in _hits.items() if not v]:
            del _hits[k]


def rate_limit(scope: str, limit: int = 0, window_seconds: int = 60) -> Callable:
    """FastAPI dependency factory: per-IP limit for a named scope."""

    async def dependency(request: Request) -> None:
        check_rate_limit(
            f"{scope}:{client_ip(request)}",
            limit or settings.RATE_LIMIT_PER_MINUTE,
            window_seconds,
        )

    return dependency
