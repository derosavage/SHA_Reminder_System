"""
Reminder Log Model
Tracks all SMS and notification reminders sent to users.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Enum as SQLEnum,
    Text, ForeignKey
)
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class ReminderType(str, enum.Enum):
    PAYMENT_DUE = "payment_due"
    PAYMENT_OVERDUE = "payment_overdue"
    PENALTY_WARNING = "penalty_warning"
    ELIGIBILITY_ALERT = "eligibility_alert"
    CONFIRMATION = "confirmation"
    GENERAL = "general"


class ReminderChannel(str, enum.Enum):
    SMS = "sms"
    PUSH = "push"
    WHATSAPP = "whatsapp"
    EMAIL = "email"


class ReminderLog(Base):
    __tablename__ = "reminder_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Reminder Details
    reminder_type = Column(
        SQLEnum(ReminderType), default=ReminderType.PAYMENT_DUE, nullable=False
    )
    channel = Column(
        SQLEnum(ReminderChannel), default=ReminderChannel.SMS, nullable=False
    )
    recipient = Column(String(100), nullable=False)  # Phone number or email
    message = Column(Text, nullable=False)
    message_sw = Column(Text, nullable=True)  # Swahili version

    # Status
    status = Column(String(20), default="pending")  # pending, sent, failed, delivered
    status_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False)

    # Metadata
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    scheduled_for = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="reminder_logs")

    def __repr__(self):
        return (
            f"<ReminderLog {self.reminder_type.value} -> "
            f"{self.recipient} [{self.status}]>"
        )