"""
Main API Router
Aggregates all route modules under versioned prefixes.
"""

from fastapi import APIRouter
from app.api.v1 import auth, penalty, payment, reminder, users

api_router = APIRouter()

# Health check
@api_router.get("/health", tags=["health"])
async def health_check():
    """API health check endpoint."""
    return {
        "status": "healthy",
        "service": "SHA Reminder & Penalty Estimation System",
        "version": "1.0.0",
    }

# V1 API Routes
api_router.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
api_router.include_router(penalty.router, prefix="/api/v1/penalty", tags=["Penalty"])
api_router.include_router(payment.router, prefix="/api/v1/payments", tags=["Payments"])
api_router.include_router(reminder.router, prefix="/api/v1/reminders", tags=["Reminders"])