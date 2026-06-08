"""
Pydantic schemas for M-Pesa payment transactions.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import re


class MpesaSTKPushRequest(BaseModel):
    """Schema for initiating M-Pesa STK Push."""
    phone_number: str = Field(..., description="Customer phone number")
    amount: float = Field(..., ge=10, description="Amount to pay in KES")
    account_reference: str = Field(..., description="National ID or SHA number")
    transaction_desc: str = Field("SHA Payment", max_length=50)

    @validator("phone_number")
    def validate_phone(cls, v):
        v = re.sub(r"\D", "", v)
        if v.startswith("0"):
            v = "254" + v[1:]
        elif v.startswith("+254"):
            v = v[1:]
        elif len(v) == 9:
            v = "254" + v
        if not v.startswith("254") or len(v) != 12:
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