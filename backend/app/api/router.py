"""
Main API Router
Aggregates all route modules under versioned prefixes.
"""

from fastapi import APIRouter
from app.api.v1 import auth, penalty, payment, reminder, users

api_router = APIRouter()

health_payload = {
    "status": "healthy",
    "service": "sha-pay",
    "version": "1.0.0",
}


@api_router.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint (aliased at /api/v1/health for tooling)."""
    return health_payload


@api_router.get("/api/v1/health", tags=["health"])
async def health_check_v1():
    """Health check endpoint (versioned alias used by scripts/docs)."""
    return health_payload


# V1 API Routes
api_router.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
api_router.include_router(penalty.router, prefix="/api/v1/penalty", tags=["Penalty"])
api_router.include_router(payment.router, prefix="/api/v1/payments", tags=["Payments"])
api_router.include_router(reminder.router, prefix="/api/v1/reminders", tags=["Reminders"])
