"""
Penalty Calculation Model
Records all penalty estimation calculations for audit and transparency.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Float, Integer, ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.utils.time import utcnow


class PenaltyCalculation(Base):
    __tablename__ = "penalty_calculations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Calculation Inputs
    missed_months = Column(Integer, nullable=False)
    monthly_contribution = Column(Float, default=300.0)
    months_considered = Column(Integer, nullable=False)

    # Calculation Results
    total_contributions_due = Column(Float, nullable=False)
    penalty_amount = Column(Float, nullable=False)
    penalty_rate_applied = Column(Float, default=0.02)  # 2% per month
    total_amount_due = Column(Float, nullable=False)

    # Breakdown (JSON for detailed per-month breakdown)
    calculation_breakdown = Column(JSON, nullable=True)

    # Metadata
    calculation_date = Column(DateTime, default=utcnow, nullable=False)
    is_offline = Column(DateTime, nullable=True)  # Timestamp if calculated offline
    device_id = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="penalty_calculations")

    def __repr__(self):
        return (
            f"<PenaltyCalculation {self.id} "
            f"Missed={self.missed_months}m "
            f"Penalty={self.penalty_amount:.2f} KES>"
        )