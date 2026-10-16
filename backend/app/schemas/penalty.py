"""
Pydantic schemas for Penalty Calculator operations.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class PenaltyCalculateRequest(BaseModel):
    """Schema for penalty calculation request."""
    missed_months: int = Field(..., ge=1, le=24, description="Number of months missed")
    monthly_contribution: float = Field(
        300.0, ge=300.0, description="Monthly SHA contribution amount"
    )
    calculate_offline: bool = Field(
        False, description="Flag if calculated offline"
    )

    @validator("missed_months")
    def validate_missed_months(cls, v):
        if v < 1:
            raise ValueError("Missed months must be at least 1")
        return v


class MonthBreakdown(BaseModel):
    """Per-month breakdown of penalty calculation."""
    month_number: int
    month_name: str
    contribution_due: float
    penalty_applied: float
    running_total: float


class PenaltyCalculateResponse(BaseModel):
    """Schema for penalty calculation response."""
    user_id: Optional[str] = None
    calculation_id: str

    # Input Summary
    missed_months: int
    monthly_contribution: float

    # Results
    total_contributions_due: float
    penalty_amount: float
    penalty_rate_applied: float
    total_amount_due: float

    # Breakdown
    months_breakdown: Optional[List[MonthBreakdown]] = None

    # Metadata
    calculation_date: datetime
    is_offline: bool

    # Formula reference
    formula_reference: str = (
        "Penalty = Σ(monthly_contribution × 0.02 × months_late) "
        "per the SHA Tariff Registry. Rate: 2% per month late."
    )

    class Config:
        from_attributes = True


class PenaltyBreakdown(BaseModel):
    """Detailed breakdown for display in mobile app."""
    calculation_id: str
    table_headers: List[str] = [
        "Mwezi (Month)", "Kiasi (Amount)", "Adhabu (Penalty)", "Jumla (Total)"
    ]
    rows: List[dict]
    total_owed: float
    total_penalty: float
    grand_total: float


class PenaltyHistoryResponse(BaseModel):
    """Schema for listing past penalty calculations."""
    calculations: List[PenaltyCalculateResponse]
    total_count: int
    page: int
    page_size: int