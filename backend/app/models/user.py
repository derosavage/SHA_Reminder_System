"""
User Model
Stores SHA contributor information and authentication details.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Float, Enum as SQLEnum,
    Text, Integer
)
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum
from app.utils.time import utcnow


class UserRole(str, enum.Enum):
    INDIVIDUAL = "individual"
    AGENT = "agent"
    ADMIN = "admin"
    SACCO = "sacco"
    HOSPITAL = "hospital"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"
    DELETED = "deleted"


class User(Base):
    __tablename__ = "users"

    # NOTE: IDs are stored as string UUIDs to match the app architecture
    # (JWT sub claims, str(user.id), and API params are all strings).
    # String(36) works identically on SQLite and PostgreSQL.
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    national_id = Column(String(20), unique=True, nullable=False, index=True)
    phone_number = Column(String(15), unique=True, nullable=False, index=True)
    full_name = Column(String(200), nullable=True)
    email = Column(String(200), nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.INDIVIDUAL, nullable=False)
    status = Column(SQLEnum(UserStatus), default=UserStatus.PENDING, nullable=False)

    # SHA Details
    sha_number = Column(String(50), unique=True, nullable=True)
    is_verified = Column(Boolean, default=False)
    contribution_amount = Column(Float, default=300.0)  # KES
    last_contribution_date = Column(DateTime, nullable=True)
    eligibility_status = Column(String(20), default="inactive")

    # Auth
    hashed_password = Column(String(255), nullable=True)
    is_phone_verified = Column(Boolean, default=False)
    otp_secret = Column(String(100), nullable=True)
    otp_expiry = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)

    # Preferences
    preferred_language = Column(String(10), default="sw")  # sw or en
    sms_notifications = Column(Boolean, default=True)
    push_notifications = Column(Boolean, default=False)
    reminder_day = Column(Integer, default=5)  # Day of month to remind

    # Timestamps
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    last_login_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    transactions = relationship("Transaction", back_populates="user", lazy="dynamic")
    penalty_calculations = relationship(
        "PenaltyCalculation", back_populates="user", lazy="dynamic"
    )
    reminder_logs = relationship("ReminderLog", back_populates="user", lazy="dynamic")

    def __repr__(self):
        return f"<User {self.phone_number} ({self.national_id})>"

    @property
    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.status == UserStatus.ACTIVE and self.deleted_at is None

    @property
    def is_locked(self) -> bool:
        """Check if account is temporarily locked."""
        if self.locked_until and self.locked_until > utcnow():
            return True
        return False