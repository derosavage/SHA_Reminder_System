"""
Pydantic schemas for M-Pesa payment transactions.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import re

from app.core.config import settings
from app.utils.phone import is_valid_kenyan_phone, normalize_phone_number


class MpesaSTKPushRequest(BaseModel):
    """Schema for initiating M-Pesa STK Push."""
    phone_number: str = Field(..., description="Customer phone number")
    amount: float = Field(
        ...,
        ge=settings.SHA_MINIMUM_CONTRIBUTION,
        description="Amount to pay in KES (SHA minimum contribution)",
    )
    account_reference: str = Field("", description="Ignored: server uses the logged-in user's National ID")
    transaction_desc: str = Field("SHA Payment", max_length=50)

    @validator("phone_number")
    def validate_phone(cls, v):
        v = normalize_phone_number(v)
        if not is_valid_kenyan_phone(v):
            raise ValueError(
                "Phone must be a valid Kenyan number (e.g., 0712345678)"
            )
        return v


class MpesaCallbackResponse(BaseModel):
    """Schema for M-Pesa callback data."""
    merchant_request_id: str
    checkout_request_id: str
    result_code: int
    result_description: str
    amount: Optional[float] = None
    mpesa_receipt_number: Optional[str] = None
    transaction_date: Optional[str] = None
    phone_number: Optional[str] = None


class TransactionCreate(BaseModel):
    """Schema for recording a transaction."""
    amount: float = Field(..., ge=10)
    phone_number: str
    account_reference: str
    transaction_type: str = "mpesa"


class TransactionResponse(BaseModel):
    """Schema for transaction API response."""
    id: str
    user_id: str
    transaction_type: str
    status: str
    amount: float
    currency: str
    mpesa_receipt_number: Optional[str]
    paybill_number: str
    account_reference: str
    phone_number: str
    transaction_date: datetime
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentConfirmation(BaseModel):
    """Schema for local payment confirmation (offline)."""
    local_id: str
    amount: float
    phone_number: str
    account_reference: str
    paybill: str = "200222"
    transaction_date: datetime
    status: str = "pending_sync"
    device_id: Optional[str] = None