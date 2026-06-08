"""
Authentication API Routes
Handles user registration, OTP verification, and token management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db
from app.schemas.user import UserCreate, UserResponse, VerifyOTP, UserLogin
from app.services.auth_service import AuthService
from app.services.sms_service import SMSService
from app.utils.dependencies import get_client_info

router = APIRouter()


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
        await SMSService.send_otp(user.phone_number, otp)

        logger.info(f"User registered: {user.phone_number}")
        return {
            "success": True,
            "message": "Registration successful. Check SMS for OTP.",
            "data": {
                "user_id": str(user.id),
                "phone_number": user.phone_number,
                "otp_sent": True,
            },
        }
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

    try:
        otp = await AuthService.request_new_otp(db, phone_number)
        await SMSService.send_otp(phone_number, otp)
        return {
            "success": True,
            "message": "New OTP sent successfully.",
        }
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
    try:
        user = await AuthService.get_user_by_phone(db, login_data.phone_number)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Send OTP for login
        otp = await AuthService.request_new_otp(db, login_data.phone_number)
        await SMSService.send_otp(user.phone_number, otp)

        return {
            "success": True,
            "message": "OTP sent to your phone.",
            "data": {"user_id": str(user.id)},
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        )