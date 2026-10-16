"""
Transaction Model
Records all M-Pesa and manual payment transactions.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Float, Enum as SQLEnum,
    Text, Integer, ForeignKey
)
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    EXPIRED = "expired"


class TransactionType(str, enum.Enum):
    MPESA = "mpesa"
    BANK = "bank"
    MANUAL = "manual"
    AGENT = "agent"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Transaction Details
    transaction_type = Column(
        SQLEnum(TransactionType), default=TransactionType.MPESA, nullable=False
    )
    status = Column(
        SQLEnum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False
    )
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="KES")

    # M-Pesa Specific
    merchant_request_id = Column(String(100), unique=True, nullable=True)
    checkout_request_id = Column(String(100), unique=True, nullable=True)
    mpesa_receipt_number = Column(String(100), unique=True, nullable=True)
    phone_number = Column(String(15), nullable=False)

    # SHA Reference
    paybill_number = Column(String(20), default="200222")
    account_reference = Column(String(50), nullable=False)  # National ID

    # Metadata
    result_code = Column(Integer, nullable=True)
    result_description = Column(Text, nullable=True)
    failure_reason = Column(Text, nullable=True)

    # Timestamps
    transaction_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="transactions")

    def __repr__(self):
        return (
            f"<Transaction {self.mpesa_receipt_number or self.id} "
            f"KES {self.amount}>"
        )