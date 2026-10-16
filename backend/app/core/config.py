"""
Application Configuration Module
Centralizes all environment variables and settings for the SHA system.
"""

from pydantic_settings import BaseSettings
from typing import Optional, List
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Main application settings loaded from environment variables."""

    # App Metadata
    APP_NAME: str = "SHA Reminder & Penalty Estimation System"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = (
        "Digital platform for managing SHA contributions, "
        "estimating penalties, and tracking healthcare eligibility."
    )
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALLOW_INSECURE_DEFAULTS: bool = os.getenv(
        "ALLOW_INSECURE_DEFAULTS", "false"
    ).lower() == "true"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    OTP_EXPIRY_MINUTES: int = 5
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://sha_user:sha_pass@localhost:5432/sha_db"
    )
    DATABASE_URL_SYNC: str = os.getenv(
        "DATABASE_URL_SYNC",
        "postgresql://sha_user:sha_pass@localhost:5432/sha_db"
    )

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Celery
    CELERY_BROKER_URL: str = os.getenv(
        "CELERY_BROKER_URL", "redis://localhost:6379/0"
    )
    CELERY_RESULT_BACKEND: str = os.getenv(
        "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
    )

    # M-Pesa Daraja API
    MPESA_CONSUMER_KEY: str = os.getenv("MPESA_CONSUMER_KEY", "")
    MPESA_CONSUMER_SECRET: str = os.getenv("MPESA_CONSUMER_SECRET", "")
    MPESA_PASSKEY: str = os.getenv("MPESA_PASSKEY", "")
    MPESA_BUSINESS_SHORTCODE: str = os.getenv(
        "MPESA_BUSINESS_SHORTCODE", "174379"
    )
    MPESA_PAYBILL: str = "200222"
    MPESA_ENVIRONMENT: str = os.getenv(
        "MPESA_ENVIRONMENT", "sandbox"
    )  # sandbox or production
    # Shared secret Safaricom must echo back as ?token=... on the callback URL.
    MPESA_CALLBACK_SECRET: str = os.getenv("MPESA_CALLBACK_SECRET", "")
    MPESA_CALLBACK_URL: str = os.getenv(
        "MPESA_CALLBACK_URL",
        "https://your-domain.com/api/v1/payments/callback"
    )

    # Africa's Talking SMS
    AT_API_KEY: str = os.getenv("AT_API_KEY", "")
    AT_USERNAME: str = os.getenv("AT_USERNAME", "sandbox")
    AT_SENDER_ID: str = os.getenv("AT_SENDER_ID", "")

    # SHA Official Parameters
    SHA_MINIMUM_CONTRIBUTION: float = 300.0  # KES for informal sector
    SHA_PAYMENT_DEADLINE_DAY: int = 9  # 9th of each month
    SHA_LATE_PENALTY_RATE: float = 0.02  # 2% per month late
    SHA_MAX_PENALTY_MONTHS: int = 12  # Max months for penalty calculation

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:5173",
        "https://sha-reminder.vercel.app",
    ]

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 20

    # External APIs
    SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL", None)
    SUPABASE_KEY: Optional[str] = os.getenv("SUPABASE_KEY", None)

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Never sign tokens with an empty key: in insecure/dev mode fall back to a
# random per-process key (tokens are invalidated on restart).
if not settings.SECRET_KEY and settings.ALLOW_INSECURE_DEFAULTS:
    import secrets as _secrets

    settings.SECRET_KEY = _secrets.token_urlsafe(48)
