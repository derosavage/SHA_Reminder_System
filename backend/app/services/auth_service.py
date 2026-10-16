"""
Authentication Service
Handles OTP verification, phone registration, and JWT token management.
"""

import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.core.config import settings
from app.models.user import User, UserRole, UserStatus
from app.schemas.user import UserCreate, UserResponse
from app.utils.time import utcnow


MAX_OTP_ATTEMPTS = 5
OTP_LOCKOUT_MINUTES = 15
OTP_RESEND_COOLDOWN_SECONDS = 60


class AuthService:
    """Service for user authentication and registration."""

    @staticmethod
    def generate_otp(length: int = 5) -> str:
        """Generate a cryptographically secure 5-digit OTP code."""
        return f"{secrets.randbelow(10 ** length):0{length}d}"

    @staticmethod
    def _hash_otp(otp: str) -> str:
        """Hash an OTP using SHA-256 with a salt (never store plaintext)."""
        salt = settings.SECRET_KEY or "sha-otp"
        return hashlib.sha256(f"{salt}:{otp}".encode()).hexdigest()

    @staticmethod
    def _verify_otp(stored_hash: Optional[str], otp: str) -> bool:
        """Verify an OTP against its stored hash."""
        if not stored_hash:
            return False
        return secrets.compare_digest(
            stored_hash, AuthService._hash_otp(otp)
        )

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
        expire = utcnow() + (
            expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        to_encode["exp"] = expire
        to_encode["iat"] = utcnow()
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
            id=str(uuid.uuid4()),
            national_id=user_data.national_id,
            phone_number=user_data.phone_number,
            full_name=user_data.full_name,
            email=user_data.email,
            role=UserRole.INDIVIDUAL,
            status=UserStatus.PENDING,
            contribution_amount=settings.SHA_MINIMUM_CONTRIBUTION,
            preferred_language=user_data.preferred_language,
            otp_secret=AuthService._hash_otp(otp),
            otp_expiry=utcnow() + timedelta(
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

        # Same generic message for unknown users and bad codes (no enumeration).
        if not user:
            raise ValueError("Invalid OTP code")

        now = utcnow()
        if user.locked_until and user.locked_until > now:
            raise ValueError(
                "Too many failed attempts. Try again in a few minutes."
            )

        if not user.otp_secret:
            raise ValueError("No active OTP. Please request a new one.")

        if user.otp_expiry and user.otp_expiry < now:
            raise ValueError("OTP has expired. Please request a new one.")

        if not AuthService._verify_otp(user.otp_secret, otp_code):
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= MAX_OTP_ATTEMPTS:
                # Burn the OTP and lock the account so it can't be brute-forced.
                user.otp_secret = None
                user.otp_expiry = None
                user.failed_login_attempts = 0
                user.locked_until = now + timedelta(minutes=OTP_LOCKOUT_MINUTES)
            await db.commit()
            raise ValueError("Invalid OTP code")

        # Mark phone as verified and activate account
        user.is_phone_verified = True
        user.is_verified = True
        if user.status == UserStatus.PENDING:
            user.status = UserStatus.ACTIVE
        user.otp_secret = None
        user.otp_expiry = None
        user.failed_login_attempts = 0
        user.locked_until = None
        await db.commit()
        await db.refresh(user)

        logger.info(f"Phone verified: {phone_number}")
        return user

    @staticmethod
    async def request_new_otp(
        db: AsyncSession,
        phone_number: str,
    ) -> Optional[str]:
        """Request a new OTP code. Returns None if the phone is unknown."""
        query = select(User).where(User.phone_number == phone_number)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return None

        now = utcnow()
        if user.locked_until and user.locked_until > now:
            raise ValueError(
                "Too many failed attempts. Try again in a few minutes."
            )
        if user.otp_expiry:
            sent_at = user.otp_expiry - timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
            if (now - sent_at).total_seconds() < OTP_RESEND_COOLDOWN_SECONDS:
                raise ValueError(
                    "Please wait a minute before requesting another OTP."
                )

        otp = AuthService.generate_otp()
        user.otp_secret = AuthService._hash_otp(otp)
        user.otp_expiry = now + timedelta(
            minutes=settings.OTP_EXPIRY_MINUTES
        )
        user.failed_login_attempts = 0
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

        user.updated_at = utcnow()
        await db.commit()
        await db.refresh(user)
        return user