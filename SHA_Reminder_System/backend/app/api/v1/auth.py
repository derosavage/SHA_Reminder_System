"""
Authentication API Routes
Handles user registration, OTP verification, and token management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db
from app.core.config import settings
from app.schemas.user import UserCreate, UserResponse, VerifyOTP, UserLogin
from app.services.auth_service import AuthService
from app.services.sms_service import SMSService
from app.utils.dependencies import get_client_info
from app.utils.rate_limit import rate_limit, check_rate_limit

router = APIRouter(dependencies=[Depends(rate_limit("auth", 10))])


@router.post("/register", response_model=dict)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    client_info: dict = Depends(get_client_info),
):
    """Register a new user with phone number and National ID."""
    try:
        user, otp = await AuthService.register_user(db, user_data)

        # Send OTP via SMS (in production, actually send)
        sms_sent = await SMSService.send_otp(user.phone_number, otp)

        logger.info(f"User registered: {user.phone_number}")
        response = {
            "success": True,
            "message": "Registration successful. Check SMS for OTP.",
            "data": {
                "user_id": str(user.id),
                "phone_number": user.phone_number,
                "otp_sent": sms_sent,
            },
        }
        # DEVELOPMENT ONLY: expose OTP when SMS provider is not configured
        # so local testing remains possible. Gated behind ALLOW_INSECURE_DEFAULTS
        # (default true for development; production must set it to false).
        if settings.ALLOW_INSECURE_DEFAULTS and not sms_sent:
            response["data"]["debug_otp"] = otp
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/verify-otp", response_model=dict)
async def verify_otp(
    verification: VerifyOTP,
    db: AsyncSession = Depends(get_db),
):
    """Verify phone number with OTP code."""
    try:
        user = await AuthService.verify_otp(
            db, verification.phone_number, verification.otp_code
        )
        token = AuthService.create_access_token(
            user_id=str(user.id), role=user.role.value
        )
        return {
            "success": True,
            "message": "Phone verified successfully.",
            "data": {
                "access_token": token,
                "token_type": "bearer",
                "user_id": str(user.id),
                "role": user.role.value,
            },
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/resend-otp", response_model=dict)
async def resend_otp(
    phone_data: dict,
    db: AsyncSession = Depends(get_db),
):
    """Resend OTP verification code."""
    phone_number = phone_data.get("phone_number")
    if not phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is required",
        )

    check_rate_limit(f"otp:{phone_number}", 3, 600)
    try:
        otp = await AuthService.request_new_otp(db, phone_number)
        response = {
            "success": True,
            "message": "If the number is registered, a new OTP has been sent.",
        }
        if otp:
            sms_sent = await SMSService.send_otp(phone_number, otp)
            # DEVELOPMENT ONLY: expose OTP when SMS provider is not configured
            if settings.ALLOW_INSECURE_DEFAULTS and not sms_sent:
                response["debug_otp"] = otp
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=dict)
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """Login with phone number (sends OTP)."""
    check_rate_limit(f"otp:{login_data.phone_number}", 3, 600)
    try:
        # Identical response whether or not the number is registered, so the
        # endpoint can't be used to discover registered users.
        response = {
            "success": True,
            "message": "If the number is registered, an OTP has been sent.",
            "data": {},
        }
        otp = await AuthService.request_new_otp(db, login_data.phone_number)
        if otp:
            sms_sent = await SMSService.send_otp(login_data.phone_number, otp)
            # DEVELOPMENT ONLY: expose OTP when SMS provider is not configured
            if settings.ALLOW_INSECURE_DEFAULTS and not sms_sent:
                response["data"]["debug_otp"] = otp
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        )
