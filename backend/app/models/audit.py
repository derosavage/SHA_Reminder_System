"""
Audit Log Model
Immutable audit trail for all system transactions and calculations.
Complies with Kenyan Data Protection Act 2019 and corruption prevention.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Enum as SQLEnum, Text, ForeignKey, JSON
)
from app.core.database import Base
import enum


class AuditAction(str, enum.Enum):
    USER_REGISTERED = "user_registered"
    USER_VERIFIED = "user_verified"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    PAYMENT_INITIATED = "payment_initiated"
    PAYMENT_COMPLETED = "payment_completed"
    PAYMENT_FAILED = "payment_failed"
    PENALTY_CALCULATED = "penalty_calculated"
    ELIGIBILITY_CHECKED = "eligibility_checked"
    REMINDER_SENT = "reminder_sent"
    SETTINGS_CHANGED = "settings_changed"
    ACCOUNT_DELETED = "account_deleted"
    DATA_EXPORTED = "data_exported"
    ADMIN_ACTION = "admin_action"


class AuditLog(Base):
    """Immutable audit log for all system events."""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    action = Column(SQLEnum(AuditAction), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True)  # e.g., "transaction", "user"
    resource_id = Column(String(100), nullable=True)   # ID of the affected resource

    # Details
    description = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)

    # Immutable timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return (
            f"<AuditLog {self.action.value} by {self.user_id} "
            f"at {self.timestamp}>"
        )