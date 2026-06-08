"""
Authentication Service
Handles OTP verification, phone registration, and JWT token management.
"""

import uuid
import random
from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.core.config import settings
from app.models.user import User, UserRole, UserStatus
from app.schemas.user import UserCreate, UserResponse


class AuthService:
    """Service for user authentication and registration."""

    @staticmethod
    def generate_otp(length: int = 5) -> str:
        """Generate a 5-digit OTP code."""
        return str(random.randint(10000, 99999))[:length]

    @staticmethod
    def create_access_token(
        user_id: str,
        role: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create a JWT access token."""
        to_encode = {
            "sub": user_id,
            "role": role,
            "type": "access",
        }
        expire = datetime.utcnow() + (
            expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        to_encode["exp"] = expire
        to_encode["iat"] = datetime.utcnow()
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            return payload
        except JWTError as e:
            logger.warning(f"Token verification failed: {e}")
            return None

    @staticmethod
    async def register_user(
        db: AsyncSession,
        user_data: UserCreate,
    ) -> Tuple[User, str]:
        """
        Register a new user with phone number and national ID.
        Returns (user, otp_code).
        """
        # Check if user already exists
        existing = await db.execute(
            select(User).where(
                (User.phone_number == user_data.phone_number)
                | (User.national_id == user_data.national_id)
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(
                "A user with this phone number or national ID already exists."
            )

        # Create user
        otp = AuthService.generate_otp()
        user = User(
            id=uuid.uuid4(),
            national_id=user_data.national_id,
            phone_number=user_data.phone_number,
            full_name=user_data.full_name,
            email=user_data.email,
            role=UserRole.INDIVIDUAL,
            status=UserStatus.PENDING,
            contribution_amount=settings.SHA_MINIMUM_CONTRIBUTION,
            preferred_language=user_data.preferred_language,
            otp_secret=otp,
            otp_expiry=datetime.utcnow() + timedelta(
                minutes=settings.OTP_EXPIRY_MINUTES
            ),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(
            f"User registered: {user.phone_number} (ID: {user.national_id})"
        )
        return user, otp

    @staticmethod
    async def verify_otp(
        db: AsyncSession,
        phone_number: str,
        otp_code: str,
    ) -> Optional[User]:
        """Verify OTP code for phone verification."""
        query = select(User).where(User.phone_number == phone_number)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("User not found")

        if user.is_phone_verified:
            raise ValueError("Phone number already verified")

        if user.otp_secret != otp_code:
            user.failed_login_attempts += 1
            await db.commit()
            raise ValueError("Invalid OTP code")

        if user.otp_expiry and user.otp_expiry < datetime.utcnow():
            raise ValueError("OTP has expired. Please request a new one.")

        # Mark phone as verified and activate account
        user.is_phone_verified = True
        user.status = UserStatus.ACTIVE
        user.otp_secret = None
        user.otp_expiry = None
        user.failed_login_attempts = 0
        await db.commit()
        await db.refresh(user)

        logger.info(f"Phone verified: {phone_number}")
        return user

    @staticmethod
    async def request_new_otp(
        db: AsyncSession,
        phone_number: str,
    ) -> str:
        """Request a new OTP code."""
        query = select(User).where(User.phone_number == phone_number)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("User not found")

        otp = AuthService.generate_otp()
        user.otp_secret = otp
        user.otp_expiry = datetime.utcnow() + timedelta(
            minutes=settings.OTP_EXPIRY_MINUTES
        )
        await db.commit()

        logger.info(f"New OTP sent to: {phone_number}")
        return otp

    @staticmethod
    async def get_user_by_phone(
        db: AsyncSession,
        phone_number: str,
    ) -> Optional[User]:
        """Find user by phone number."""
        query = select(User).where(User.phone_number == phone_number)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_user_profile(
        db: AsyncSession,
        user_id: str,
        update_data: dict,
    ) -> Optional[User]:
        """Update user profile information."""
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return None

        for key, value in update_data.items():
            if value is not None and hasattr(user, key):
                setattr(user, key, value)

        user.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(user)
        return user